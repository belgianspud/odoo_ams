# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class MembershipUpgradeWizard(models.TransientModel):
    _name = 'ams.membership.upgrade.wizard'
    _description = 'Membership Upgrade Wizard'

    # Source membership information
    membership_id = fields.Many2one('ams.membership.base', 'Current Membership', required=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    current_product_id = fields.Many2one('product.product', 'Current Product', readonly=True)
    current_member_type_id = fields.Many2one('ams.member.type', 'Current Member Type', readonly=True)
    
    # Current membership details
    current_start_date = fields.Date('Current Start Date', readonly=True)
    current_end_date = fields.Date('Current End Date', readonly=True)
    current_paid_amount = fields.Float('Current Paid Amount', readonly=True)
    days_remaining = fields.Integer('Days Remaining', readonly=True)
    
    # Upgrade options
    upgrade_product_id = fields.Many2one('product.product', 'Upgrade To Product', required=True,
                                       domain="[('product_tmpl_id.is_subscription_product', '=', True)]")
    new_member_type_id = fields.Many2one('ams.member.type', 'New Member Type', readonly=True)
    
    # Pricing calculations
    original_price = fields.Float('Original Price', readonly=True)
    prorated_credit = fields.Float('Pro-rated Credit', readonly=True, 
                                 help="Credit for unused portion of current membership")
    upgrade_price = fields.Float('Upgrade Price', readonly=True)
    net_amount = fields.Float('Net Amount Due', readonly=True,
                            help="Amount due after applying credit")
    
    # Upgrade configuration
    upgrade_effective_date = fields.Date('Upgrade Effective Date', default=fields.Date.today, required=True)
    prorate_current = fields.Boolean('Pro-rate Current Membership', default=True,
                                   help="Calculate pro-rated credit for unused portion")
    prorate_upgrade = fields.Boolean('Pro-rate Upgrade', default=True,
                                   help="Pro-rate upgrade to match current membership end date")
    
    # Billing options
    create_sale_order = fields.Boolean('Create Sale Order', default=True,
                                     help="Create sale order for upgrade transaction")
    auto_confirm_order = fields.Boolean('Auto Confirm Order', default=False,
                                      help="Automatically confirm the sale order")
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms')
    
    # Notes and communication
    upgrade_reason = fields.Text('Upgrade Reason')
    send_confirmation_email = fields.Boolean('Send Confirmation Email', default=True)
    internal_notes = fields.Text('Internal Notes')
    
    # Computed fields
    upgrade_available = fields.Boolean('Upgrade Available', compute='_compute_upgrade_eligibility')
    eligibility_message = fields.Text('Eligibility Message', compute='_compute_upgrade_eligibility')

    @api.onchange('membership_id')
    def _onchange_membership_id(self):
        """Load current membership details"""
        if self.membership_id:
            membership = self.membership_id
            self.partner_id = membership.partner_id
            self.current_product_id = membership.product_id
            self.current_member_type_id = membership.member_type_id
            self.current_start_date = membership.start_date
            self.current_end_date = membership.end_date
            self.current_paid_amount = membership.paid_amount
            self.days_remaining = membership.days_remaining

    @api.onchange('upgrade_product_id')
    def _onchange_upgrade_product_id(self):
        """Calculate upgrade pricing when product changes"""
        if self.upgrade_product_id:
            product_tmpl = self.upgrade_product_id.product_tmpl_id
            self.new_member_type_id = product_tmpl.member_type_id
            self.original_price = self.upgrade_product_id.lst_price
            self._calculate_upgrade_pricing()

    @api.onchange('upgrade_effective_date', 'prorate_current', 'prorate_upgrade')
    def _onchange_upgrade_options(self):
        """Recalculate pricing when options change"""
        if self.upgrade_product_id:
            self._calculate_upgrade_pricing()

    def _calculate_upgrade_pricing(self):
        """Calculate upgrade pricing with pro-rating"""
        if not self.membership_id or not self.upgrade_product_id:
            return
        
        current_membership = self.membership_id
        upgrade_product = self.upgrade_product_id.product_tmpl_id
        
        # Calculate pro-rated credit for current membership
        if self.prorate_current and current_membership.end_date > self.upgrade_effective_date:
            total_days = (current_membership.end_date - current_membership.start_date).days
            remaining_days = (current_membership.end_date - self.upgrade_effective_date).days
            
            if total_days > 0:
                credit_ratio = remaining_days / total_days
                self.prorated_credit = current_membership.paid_amount * credit_ratio
            else:
                self.prorated_credit = 0.0
        else:
            self.prorated_credit = 0.0
        
        # Calculate upgrade price
        if self.prorate_upgrade and upgrade_product.enable_prorating:
            # Pro-rate upgrade to match current membership end date
            upgrade_end_date = current_membership.end_date
            self.upgrade_price = upgrade_product.calculate_prorated_price(
                self.upgrade_effective_date, 
                upgrade_end_date
            )
        else:
            self.upgrade_price = self.upgrade_product_id.lst_price
        
        # Calculate net amount
        self.net_amount = self.upgrade_price - self.prorated_credit

    @api.depends('membership_id', 'upgrade_product_id')
    def _compute_upgrade_eligibility(self):
        """Check if upgrade is eligible"""
        for wizard in self:
            if not wizard.membership_id or not wizard.upgrade_product_id:
                wizard.upgrade_available = False
                wizard.eligibility_message = _("Please select both current membership and upgrade product.")
                continue
            
            issues = []
            
            # Check membership status
            if wizard.membership_id.state not in ['active', 'grace']:
                issues.append(_("Current membership must be active or in grace period"))
            
            # Check if upgrade product allows upgrades
            upgrade_product = wizard.upgrade_product_id.product_tmpl_id
            current_product = wizard.current_product_id.product_tmpl_id
            
            if not upgrade_product.allow_upgrades:
                issues.append(_("Selected product does not allow upgrades"))
            
            # Check if current product allows upgrades to this product
            if current_product.upgrade_product_ids and upgrade_product not in current_product.upgrade_product_ids:
                issues.append(_("Current product cannot be upgraded to selected product"))
            
            # Check if it's actually an upgrade (higher price)
            if wizard.upgrade_product_id.lst_price <= wizard.current_product_id.lst_price:
                issues.append(_("Selected product is not a higher tier (consider downgrade instead)"))
            
            # Check multiple membership rules
            if upgrade_product.product_class == 'membership':
                settings = wizard.env['ams.settings'].search([('active', '=', True)], limit=1)
                if settings and not settings.allow_multiple_active_memberships:
                    # Check if member would have multiple memberships
                    existing_memberships = wizard.env['ams.membership.base'].search([
                        ('partner_id', '=', wizard.partner_id.id),
                        ('state', 'in', ['active', 'grace']),
                        ('product_id.product_tmpl_id.product_class', '=', 'membership'),
                        ('id', '!=', wizard.membership_id.id)
                    ])
                    if existing_memberships:
                        issues.append(_("Member cannot have multiple active memberships"))
            
            wizard.upgrade_available = len(issues) == 0
            wizard.eligibility_message = "\n".join(issues) if issues else _("Upgrade is available")

    def action_preview_upgrade(self):
        """Preview upgrade details before processing"""
        self.ensure_one()
        
        if not self.upgrade_available:
            raise UserError(self.eligibility_message)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upgrade Preview'),
            'res_model': 'ams.membership.upgrade.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'preview_mode': True},
        }

    def action_process_upgrade(self):
        """Process the membership upgrade"""
        self.ensure_one()
        
        if not self.upgrade_available:
            raise UserError(self.eligibility_message)
        
        try:
            # Create sale order if requested
            sale_order = None
            if self.create_sale_order:
                sale_order = self._create_upgrade_sale_order()
                
                if self.auto_confirm_order:
                    sale_order.action_confirm()
            
            # Process the upgrade
            new_membership = self._create_new_membership(sale_order)
            
            # Cancel/expire current membership
            self._process_current_membership()
            
            # Send confirmation email if requested
            if self.send_confirmation_email:
                self._send_upgrade_confirmation_email(new_membership)
            
            # Log the upgrade
            self._log_upgrade_activity(new_membership)
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Upgraded Membership'),
                'res_model': new_membership._name,
                'res_id': new_membership.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Upgrade processing failed: {str(e)}")
            raise UserError(_("Upgrade failed: %s") % str(e))

    def _create_upgrade_sale_order(self):
        """Create sale order for upgrade transaction"""
        self.ensure_one()
        
        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': f"Upgrade from {self.membership_id.name}",
            'order_type': 'upgrade',
            'original_membership_id': self.membership_id.id,
        }
        
        if self.payment_term_id:
            order_vals['payment_term_id'] = self.payment_term_id.id
        
        sale_order = self.env['sale.order'].create(order_vals)
        
        # Add upgrade product line
        upgrade_line_vals = {
            'order_id': sale_order.id,
            'product_id': self.upgrade_product_id.id,
            'product_uom_qty': 1,
            'price_unit': self.upgrade_price,
            'membership_start_date': self.upgrade_effective_date,
        }
        
        if self.prorate_upgrade:
            upgrade_line_vals.update({
                'is_prorated': True,
                'proration_details': _("Pro-rated upgrade to match current membership end date")
            })
        
        self.env['sale.order.line'].create(upgrade_line_vals)
        
        # Add credit line if there's a prorated credit
        if self.prorated_credit > 0:
            credit_line_vals = {
                'order_id': sale_order.id,
                'product_id': self.current_product_id.id,
                'name': f"Credit for unused portion of {self.current_product_id.name}",
                'product_uom_qty': 1,
                'price_unit': -self.prorated_credit,
            }
            self.env['sale.order.line'].create(credit_line_vals)
        
        return sale_order

    def _create_new_membership(self, sale_order=None):
        """Create new upgraded membership"""
        self.ensure_one()
        
        # Determine end date for new membership
        if self.prorate_upgrade:
            end_date = self.current_end_date  # Match current membership end date
        else:
            # Calculate new end date based on upgrade product
            end_date = self.upgrade_product_id.product_tmpl_id.calculate_membership_end_date(
                self.upgrade_effective_date
            )
        
        membership_vals = {
            'partner_id': self.partner_id.id,
            'product_id': self.upgrade_product_id.id,
            'member_type_id': self.new_member_type_id.id if self.new_member_type_id else False,
            'start_date': self.upgrade_effective_date,
            'end_date': end_date,
            'state': 'active',
            'original_price': self.original_price,
            'paid_amount': self.upgrade_price,
            'prorated_amount': self.upgrade_price if self.prorate_upgrade else 0.0,
            'is_upgrade': True,
            'previous_membership_id': self.membership_id.id,
            'sale_order_id': sale_order.id if sale_order else False,
            'notes': self.upgrade_reason or '',
        }
        
        # Get the appropriate model based on product class
        product_class = self.upgrade_product_id.product_tmpl_id.product_class
        membership_model = self.upgrade_product_id.product_tmpl_id.membership_model
        
        new_membership = self.env[membership_model].create(membership_vals)
        
        # Link memberships
        self.membership_id.next_membership_id = new_membership.id
        
        return new_membership

    def _process_current_membership(self):
        """Handle current membership when upgrading"""
        self.ensure_one()
        
        # Cancel current membership
        self.membership_id.write({
            'state': 'cancelled',
            'cancellation_date': self.upgrade_effective_date,
            'cancellation_reason': f"Upgraded to {self.upgrade_product_id.name}"
        })

    def _send_upgrade_confirmation_email(self, new_membership):
        """Send upgrade confirmation email"""
        # This would integrate with email templates
        # Placeholder implementation
        self.membership_id.message_post(
            body=_("Membership upgraded to %s. New membership: %s") % (
                self.upgrade_product_id.name, 
                new_membership.name
            ),
            message_type='notification'
        )

    def _log_upgrade_activity(self, new_membership):
        """Log upgrade activity"""
        self.membership_id.message_post(
            body=_("Membership upgraded to %s (ID: %s). Net amount: $%.2f") % (
                new_membership.name,
                new_membership.id,
                self.net_amount
            ),
            message_type='notification'
        )
        
        if self.internal_notes:
            new_membership.message_post(
                body=_("Upgrade notes: %s") % self.internal_notes,
                message_type='comment'
            )

    # Constraints
    @api.constrains('upgrade_effective_date')
    def _check_upgrade_effective_date(self):
        """Validate upgrade effective date"""
        for wizard in self:
            if wizard.upgrade_effective_date:
                if wizard.upgrade_effective_date < fields.Date.today():
                    raise ValidationError(_("Upgrade effective date cannot be in the past."))
                
                if wizard.membership_id and wizard.upgrade_effective_date > wizard.current_end_date:
                    raise ValidationError(_("Upgrade effective date cannot be after current membership end date."))

    @api.constrains('upgrade_product_id', 'current_product_id')
    def _check_upgrade_product(self):
        """Validate upgrade product selection"""
        for wizard in self:
            if wizard.upgrade_product_id and wizard.current_product_id:
                if wizard.upgrade_product_id == wizard.current_product_id:
                    raise ValidationError(_("Cannot upgrade to the same product."))