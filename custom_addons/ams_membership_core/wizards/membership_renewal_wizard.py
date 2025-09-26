# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipRenewalWizard(models.TransientModel):
    _name = 'ams.membership.renewal.wizard'
    _description = 'Membership Renewal Wizard'

    # Source membership information
    membership_id = fields.Many2one('ams.membership.base', 'Current Membership', required=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    member_type_id = fields.Many2one('ams.member.type', 'Member Type', readonly=True)
    
    # Current membership details
    current_start_date = fields.Date('Current Start Date', readonly=True)
    current_end_date = fields.Date('Current End Date', readonly=True)
    current_paid_amount = fields.Float('Current Paid Amount', readonly=True)
    days_remaining = fields.Integer('Days Remaining', readonly=True)
    is_expired = fields.Boolean('Is Expired', readonly=True)
    
    # Renewal configuration
    renewal_start_date = fields.Date('Renewal Start Date', required=True)
    renewal_end_date = fields.Date('Renewal End Date', readonly=True)
    renewal_period_type = fields.Selection([
        ('calendar', 'Calendar Year'),
        ('anniversary', 'Anniversary'),
        ('rolling', 'Rolling Period')
    ], string='Renewal Period Type', readonly=True)
    
    # Pricing and payment
    original_price = fields.Float('Original Price', readonly=True)
    renewal_price = fields.Float('Renewal Price', required=True)
    discount_amount = fields.Float('Discount Amount', default=0.0)
    final_price = fields.Float('Final Price', compute='_compute_final_price', store=True)
    
    # Renewal options
    auto_renewal_setup = fields.Boolean('Setup Auto-Renewal', default=False,
                                      help="Configure automatic renewal for future periods")
    early_renewal = fields.Boolean('Early Renewal', readonly=True,
                                  help="Renewal is being processed before expiration")
    grace_period_renewal = fields.Boolean('Grace Period Renewal', readonly=True,
                                        help="Renewal during grace period")
    
    # Billing options
    create_sale_order = fields.Boolean('Create Sale Order', default=True)
    auto_confirm_order = fields.Boolean('Auto Confirm Order', default=False)
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms')
    invoice_immediately = fields.Boolean('Create Invoice Immediately', default=False)
    
    # Member benefits and features
    maintain_benefits = fields.Boolean('Maintain Current Benefits', default=True, readonly=True)
    upgrade_available = fields.Boolean('Upgrade Available', compute='_compute_upgrade_options')
    available_upgrades = fields.Many2many('product.product', 'renewal_upgrade_rel',
                                        'wizard_id', 'product_id', 'Available Upgrades',
                                        compute='_compute_upgrade_options')
    
    # Communication and notes
    send_confirmation_email = fields.Boolean('Send Confirmation Email', default=True)
    send_welcome_back_email = fields.Boolean('Send Welcome Back Email', default=True)
    renewal_notes = fields.Text('Renewal Notes')
    internal_notes = fields.Text('Internal Notes')
    
    # Eligibility and validation
    renewal_eligible = fields.Boolean('Renewal Eligible', compute='_compute_renewal_eligibility')
    eligibility_message = fields.Text('Eligibility Message', compute='_compute_renewal_eligibility')
    warnings = fields.Text('Renewal Warnings', compute='_compute_renewal_warnings')
    
    # Multi-membership handling
    renew_all_memberships = fields.Boolean('Renew All Memberships', default=False,
                                         help="Renew all eligible memberships for this member")
    additional_membership_ids = fields.Many2many('ams.membership.base', 'renewal_additional_rel',
                                               'wizard_id', 'membership_id', 'Additional Memberships',
                                               domain="[('partner_id', '=', partner_id), ('can_be_renewed', '=', True), ('id', '!=', membership_id)]")

    @api.onchange('membership_id')
    def _onchange_membership_id(self):
        """Load membership details when membership changes"""
        if self.membership_id:
            membership = self.membership_id
            product_tmpl = membership.product_id.product_tmpl_id
            
            self.partner_id = membership.partner_id
            self.product_id = membership.product_id
            self.member_type_id = membership.member_type_id
            self.current_start_date = membership.start_date
            self.current_end_date = membership.end_date
            self.current_paid_amount = membership.paid_amount
            self.days_remaining = membership.days_remaining
            self.is_expired = membership.state in ['lapsed', 'expired']
            
            # Set renewal period type
            self.renewal_period_type = product_tmpl.get_effective_membership_period_type()
            
            # Calculate renewal dates
            self._calculate_renewal_dates()
            
            # Set renewal price
            self.original_price = self.product_id.lst_price
            self.renewal_price = self.product_id.lst_price
            
            # Determine renewal type
            today = fields.Date.today()
            self.early_renewal = membership.end_date > today
            self.grace_period_renewal = membership.state == 'grace'

    @api.onchange('renewal_start_date')
    def _onchange_renewal_start_date(self):
        """Recalculate renewal end date when start date changes"""
        if self.renewal_start_date and self.product_id:
            self._calculate_renewal_dates()

    def _calculate_renewal_dates(self):
        """Calculate renewal start and end dates"""
        if not self.product_id or not self.membership_id:
            return
        
        product_tmpl = self.product_id.product_tmpl_id
        
        # Default renewal start date
        if not self.renewal_start_date:
            if self.early_renewal:
                # Early renewal starts after current membership ends
                self.renewal_start_date = self.current_end_date + timedelta(days=1)
            else:
                # Immediate renewal
                self.renewal_start_date = fields.Date.today()
        
        # Calculate end date
        self.renewal_end_date = product_tmpl.calculate_membership_end_date(self.renewal_start_date)

    @api.depends('renewal_price', 'discount_amount')
    def _compute_final_price(self):
        """Calculate final price after discounts"""
        for wizard in self:
            wizard.final_price = wizard.renewal_price - wizard.discount_amount

    @api.depends('membership_id', 'partner_id')
    def _compute_renewal_eligibility(self):
        """Check renewal eligibility"""
        for wizard in self:
            if not wizard.membership_id:
                wizard.renewal_eligible = False
                wizard.eligibility_message = _("No membership selected")
                continue
            
            eligibility = wizard.membership_id.check_renewal_eligibility()
            wizard.renewal_eligible = eligibility.get('eligible', False)
            wizard.eligibility_message = '\n'.join(eligibility.get('issues', []))

    @api.depends('membership_id')
    def _compute_upgrade_options(self):
        """Calculate available upgrade options"""
        for wizard in self:
            if wizard.membership_id and wizard.product_id:
                current_product = wizard.product_id.product_tmpl_id
                upgrades = current_product.upgrade_product_ids.mapped('product_variant_ids')
                wizard.available_upgrades = [(6, 0, upgrades.ids)]
                wizard.upgrade_available = len(upgrades) > 0
            else:
                wizard.available_upgrades = [(5, 0, 0)]
                wizard.upgrade_available = False

    @api.depends('membership_id', 'early_renewal', 'grace_period_renewal')
    def _compute_renewal_warnings(self):
        """Generate renewal warnings"""
        for wizard in self:
            warnings = []
            
            if wizard.early_renewal:
                warnings.append(_("This is an early renewal. The new membership will start after the current one expires."))
            
            if wizard.grace_period_renewal:
                warnings.append(_("Member is currently in grace period. Renewal will restore active status."))
            
            if wizard.membership_id and wizard.membership_id.state == 'lapsed':
                warnings.append(_("Member is lapsed. Consider any reinstatement fees or requirements."))
            
            if wizard.partner_id:
                # Check for other expiring memberships
                other_expiring = wizard.env['ams.membership.base'].search([
                    ('partner_id', '=', wizard.partner_id.id),
                    ('state', 'in', ['active', 'grace']),
                    ('end_date', '<=', fields.Date.today() + timedelta(days=30)),
                    ('id', '!=', wizard.membership_id.id)
                ])
                
                if other_expiring:
                    warnings.append(_("Member has %d other memberships expiring soon. Consider renewing all.") % len(other_expiring))
            
            wizard.warnings = '\n'.join(warnings) if warnings else False

    def action_calculate_pricing(self):
        """Recalculate renewal pricing"""
        self.ensure_one()
        
        # Apply member discounts
        if self.partner_id.is_member:
            # Apply early renewal discount
            if self.early_renewal and self.days_remaining > 30:
                early_discount = self.renewal_price * 0.05  # 5% early renewal discount
                self.discount_amount = early_discount
        
        return {'type': 'ir.actions.do_nothing'}

    def action_preview_renewal(self):
        """Preview renewal details"""
        self.ensure_one()
        
        if not self.renewal_eligible:
            raise UserError(self.eligibility_message)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Preview'),
            'res_model': 'ams.membership.renewal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'preview_mode': True},
        }

    def action_process_renewal(self):
        """Process the membership renewal"""
        self.ensure_one()
        
        if not self.renewal_eligible:
            raise UserError(self.eligibility_message)
        
        try:
            memberships_to_renew = [self.membership_id]
            
            # Add additional memberships if selected
            if self.renew_all_memberships:
                memberships_to_renew.extend(self.additional_membership_ids)
            
            new_memberships = []
            sale_order = None
            
            # Create sale order if requested
            if self.create_sale_order:
                sale_order = self._create_renewal_sale_order(memberships_to_renew)
                
                if self.auto_confirm_order:
                    sale_order.action_confirm()
                    
                    if self.invoice_immediately:
                        invoices = sale_order._create_invoices()
                        for invoice in invoices:
                            invoice.action_post()
            
            # Process each membership renewal
            for membership in memberships_to_renew:
                new_membership = self._create_renewed_membership(membership, sale_order)
                new_memberships.append(new_membership)
                
                # Update original membership
                self._process_original_membership(membership, new_membership)
            
            # Setup auto-renewal if requested
            if self.auto_renewal_setup:
                self._setup_auto_renewal(new_memberships)
            
            # Send confirmation emails
            if self.send_confirmation_email:
                self._send_renewal_confirmation_emails(new_memberships)
            
            # Log renewal activities
            self._log_renewal_activities(new_memberships)
            
            # Return to the main renewed membership
            main_membership = new_memberships[0]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renewed Membership'),
                'res_model': main_membership._name,
                'res_id': main_membership.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            _logger.error(f"Renewal processing failed: {str(e)}")
            raise UserError(_("Renewal failed: %s") % str(e))

    def _create_renewal_sale_order(self, memberships):
        """Create sale order for renewal"""
        self.ensure_one()
        
        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': f"Renewal of {self.membership_id.name}",
            'order_type': 'renewal',
            'original_membership_id': self.membership_id.id,
        }
        
        if self.payment_term_id:
            order_vals['payment_term_id'] = self.payment_term_id.id
        
        sale_order = self.env['sale.order'].create(order_vals)
        
        # Add line for each membership being renewed
        for membership in memberships:
            line_vals = {
                'order_id': sale_order.id,
                'product_id': membership.product_id.id,
                'product_uom_qty': 1,
                'price_unit': self.renewal_price if membership == self.membership_id else membership.product_id.lst_price,
                'membership_start_date': self.renewal_start_date,
                'membership_end_date': self.renewal_end_date,
            }
            
            # Apply discount to main membership
            if membership == self.membership_id and self.discount_amount > 0:
                line_vals['discount'] = (self.discount_amount / self.renewal_price) * 100
            
            self.env['sale.order.line'].create(line_vals)
        
        return sale_order

    def _create_renewed_membership(self, original_membership, sale_order=None):
        """Create renewed membership record"""
        self.ensure_one()
        
        membership_vals = {
            'partner_id': self.partner_id.id,
            'product_id': original_membership.product_id.id,
            'member_type_id': original_membership.member_type_id.id,
            'start_date': self.renewal_start_date,
            'end_date': self.renewal_end_date,
            'state': 'active',
            'original_price': self.original_price,
            'paid_amount': self.final_price,
            'is_renewal': True,
            'auto_renewal': self.auto_renewal_setup,
            'previous_membership_id': original_membership.id,
            'sale_order_id': sale_order.id if sale_order else False,
            'notes': self.renewal_notes or '',
        }
        
        # Get the appropriate model based on original membership
        membership_model = original_membership._name
        new_membership = self.env[membership_model].create(membership_vals)
        
        # Link memberships
        original_membership.next_membership_id = new_membership.id
        
        return new_membership

    def _process_original_membership(self, original_membership, new_membership):
        """Handle original membership after renewal"""
        self.ensure_one()
        
        if original_membership.state in ['lapsed', 'expired']:
            # Mark as renewed
            original_membership.write({
                'state': 'expired',
                'last_renewal_date': fields.Date.today()
            })
        elif self.early_renewal:
            # Keep active until end date, then it will auto-transition
            original_membership.write({
                'last_renewal_date': fields.Date.today()
            })
        else:
            # Immediate transition to expired
            original_membership.write({
                'state': 'expired',
                'last_renewal_date': fields.Date.today()
            })

    def _setup_auto_renewal(self, memberships):
        """Setup auto-renewal for renewed memberships"""
        for membership in memberships:
            membership.write({'auto_renewal': True})

    def _send_renewal_confirmation_emails(self, memberships):
        """Send renewal confirmation emails"""
        # Placeholder for email integration
        for membership in memberships:
            membership.message_post(
                body=_("Membership renewed successfully. New period: %s to %s") % (
                    membership.start_date,
                    membership.end_date
                ),
                message_type='notification'
            )

    def _log_renewal_activities(self, memberships):
        """Log renewal activities"""
        for membership in memberships:
            self.membership_id.message_post(
                body=_("Membership renewed. New membership: %s. Amount: $%.2f") % (
                    membership.name,
                    membership.paid_amount
                ),
                message_type='notification'
            )
            
            if self.internal_notes:
                membership.message_post(
                    body=_("Renewal notes: %s") % self.internal_notes,
                    message_type='comment'
                )

    def action_upgrade_instead(self):
        """Open upgrade wizard instead of renewal"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upgrade Membership'),
            'res_model': 'ams.membership.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.membership_id.id,
                'default_partner_id': self.partner_id.id,
                'default_current_product_id': self.product_id.id,
            }
        }

    # Constraints
    @api.constrains('renewal_start_date', 'current_end_date')
    def _check_renewal_dates(self):
        """Validate renewal dates"""
        for wizard in self:
            if wizard.renewal_start_date and wizard.current_end_date:
                if wizard.early_renewal:
                    if wizard.renewal_start_date <= wizard.current_end_date:
                        raise ValidationError(_("Early renewal start date must be after current membership end date."))
                else:
                    if wizard.renewal_start_date < fields.Date.today():
                        raise ValidationError(_("Renewal start date cannot be in the past."))

    @api.constrains('renewal_price', 'discount_amount')
    def _check_pricing(self):
        """Validate pricing"""
        for wizard in self:
            if wizard.renewal_price < 0:
                raise ValidationError(_("Renewal price cannot be negative."))
            if wizard.discount_amount < 0:
                raise ValidationError(_("Discount amount cannot be negative."))
            if wizard.discount_amount > wizard.renewal_price:
                raise ValidationError(_("Discount amount cannot exceed renewal price."))

    @api.constrains('final_price')
    def _check_final_price(self):
        """Validate final price"""
        for wizard in self:
            if wizard.final_price < 0:
                raise ValidationError(_("Final price cannot be negative."))