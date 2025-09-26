# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipBase(models.AbstractModel):
    _name = 'ams.membership.base'
    _description = 'Abstract Base Model for All Membership Types'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'start_date desc, id desc'

    # Core Fields
    name = fields.Char('Membership Reference', compute='_compute_name', store=True)
    member_number = fields.Char('Membership Number', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', 'Member', required=True, tracking=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, tracking=True)
    member_type_id = fields.Many2one('ams.member.type', 'Member Type', tracking=True)

    # State and Lifecycle
    state = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated')
    ], string='Status', default='pending', required=True, tracking=True)

    # Dates
    start_date = fields.Date('Start Date', required=True, tracking=True)
    end_date = fields.Date('End Date', required=True, tracking=True)
    grace_period_end = fields.Date('Grace Period End', readonly=True)
    activation_date = fields.Date('Activation Date', readonly=True)
    cancellation_date = fields.Date('Cancellation Date', readonly=True)
    last_renewal_date = fields.Date('Last Renewal Date', readonly=True)

    # Financial Information
    original_price = fields.Float('Original Price', readonly=True)
    paid_amount = fields.Float('Paid Amount', readonly=True)
    prorated_amount = fields.Float('Pro-rated Amount', readonly=True)
    setup_fee = fields.Float('Setup Fee', readonly=True)
    
    # Related Invoice Information
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', related='invoice_line_id.move_id', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', readonly=True)
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', related='sale_order_line_id.order_id', readonly=True)

    # Configuration and Features
    auto_renewal = fields.Boolean('Auto Renewal', default=False, tracking=True)
    requires_approval = fields.Boolean('Requires Approval', readonly=True)
    is_upgrade = fields.Boolean('Is Upgrade', readonly=True, help="This membership was created as an upgrade")
    is_renewal = fields.Boolean('Is Renewal', readonly=True, help="This membership was created as a renewal")
    
    # Relationships
    previous_membership_id = fields.Many2one('ams.membership.base', 'Previous Membership', readonly=True)
    next_membership_id = fields.Many2one('ams.membership.base', 'Next Membership', readonly=True)
    
    # Notes and Tracking
    notes = fields.Text('Notes')
    cancellation_reason = fields.Text('Cancellation Reason')
    approval_notes = fields.Text('Approval Notes')
    
    # Computed Fields
    days_remaining = fields.Integer('Days Remaining', compute='_compute_days_remaining')
    is_expiring_soon = fields.Boolean('Expiring Soon', compute='_compute_expiring_status')
    renewal_due = fields.Boolean('Renewal Due', compute='_compute_expiring_status')
    can_be_renewed = fields.Boolean('Can Be Renewed', compute='_compute_renewal_eligibility')
    
    # Portal Access
    access_token = fields.Char('Access Token', groups="base.group_user")

    @api.depends('partner_id', 'product_id', 'member_number')
    def _compute_name(self):
        """Compute membership reference name"""
        for membership in self:
            if membership.member_number:
                name = membership.member_number
            elif membership.partner_id and membership.product_id:
                name = f"{membership.partner_id.name} - {membership.product_id.name}"
            else:
                name = f"Membership #{membership.id}"
            membership.name = name

    @api.depends('end_date')
    def _compute_days_remaining(self):
        """Compute days remaining until expiration"""
        today = fields.Date.today()
        for membership in self:
            if membership.end_date:
                delta = membership.end_date - today
                membership.days_remaining = delta.days
            else:
                membership.days_remaining = 0

    @api.depends('days_remaining', 'state')
    def _compute_expiring_status(self):
        """Compute expiring and renewal due status"""
        for membership in self:
            if membership.state in ['active', 'grace']:
                membership.is_expiring_soon = membership.days_remaining <= 30
                membership.renewal_due = membership.days_remaining <= 60
            else:
                membership.is_expiring_soon = False
                membership.renewal_due = False

    def _compute_renewal_eligibility(self):
        """Compute if membership can be renewed"""
        for membership in self:
            membership.can_be_renewed = (
                membership.state in ['active', 'grace', 'lapsed'] and
                not membership.next_membership_id and
                membership.product_id.auto_renewal_eligible
            )

    @api.model
    def create(self, vals):
        """Override create to generate membership number and handle initial setup"""
        # Generate membership number if not provided
        if not vals.get('member_number'):
            vals['member_number'] = self.env['ir.sequence'].next_by_code('ams.membership.number')
        
        # Set original price from product if not provided
        if not vals.get('original_price') and vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['original_price'] = product.lst_price
        
        # Set member type from product if not provided
        if not vals.get('member_type_id') and vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.product_tmpl_id.member_type_id:
                vals['member_type_id'] = product.product_tmpl_id.member_type_id.id
        
        membership = super().create(vals)
        
        # Set activation date if state is active
        if membership.state == 'active':
            membership.activation_date = fields.Date.today()
        
        # Generate access token for portal
        membership._portal_ensure_token()
        
        return membership

    def write(self, vals):
        """Override write to handle state changes and date updates"""
        # Track state changes
        if 'state' in vals:
            for membership in self:
                old_state = membership.state
                new_state = vals['state']
                
                # Handle state-specific logic
                if new_state == 'active' and old_state != 'active':
                    vals['activation_date'] = fields.Date.today()
                elif new_state in ['cancelled', 'terminated'] and old_state not in ['cancelled', 'terminated']:
                    vals['cancellation_date'] = fields.Date.today()
                elif new_state == 'grace' and old_state == 'active':
                    # Set grace period end date
                    grace_days = membership._get_effective_grace_period()
                    vals['grace_period_end'] = fields.Date.today() + timedelta(days=grace_days)
        
        result = super().write(vals)
        
        # Update partner membership status if this is a membership product
        if 'state' in vals:
            for membership in self:
                if membership.product_id.product_tmpl_id.product_class == 'membership':
                    membership._update_partner_membership_status()
        
        return result

    def _get_effective_grace_period(self):
        """Get effective grace period for this membership"""
        self.ensure_one()
        if self.product_id.product_tmpl_id.grace_period_override:
            return self.product_id.product_tmpl_id.grace_period_days
        elif self.member_type_id:
            return self.member_type_id.get_effective_grace_period()
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.grace_period_days if settings else 30

    def _update_partner_membership_status(self):
        """Update partner membership status based on this membership"""
        self.ensure_one()
        
        if self.product_id.product_tmpl_id.product_class != 'membership':
            return
        
        partner = self.partner_id
        
        # Check if partner has other active memberships
        other_active = self.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['active', 'grace']),
            ('product_id.product_tmpl_id.product_class', '=', 'membership'),
            ('id', '!=', self.id)
        ])
        
        if self.state in ['active', 'grace']:
            # Update partner to active member status
            partner.write({
                'is_member': True,
                'member_status': self.state,
                'member_type_id': self.member_type_id.id if self.member_type_id else partner.member_type_id.id,
                'membership_start_date': self.start_date,
                'membership_end_date': self.end_date,
            })
        elif not other_active:
            # No other active memberships, update partner status
            if self.state in ['lapsed', 'expired']:
                partner.member_status = 'lapsed'
            elif self.state in ['cancelled', 'terminated']:
                partner.member_status = 'terminated'
            elif self.state == 'suspended':
                partner.member_status = 'suspended'

    # Action Methods
    def action_activate(self):
        """Activate pending membership"""
        for membership in self:
            if membership.state != 'pending':
                raise UserError(_("Only pending memberships can be activated."))
            
            membership.write({
                'state': 'active',
                'activation_date': fields.Date.today()
            })

    def action_suspend(self):
        """Suspend active membership"""
        for membership in self:
            if membership.state not in ['active', 'grace']:
                raise UserError(_("Only active or grace period memberships can be suspended."))
            
            membership.write({
                'state': 'suspended'
            })

    def action_cancel(self):
        """Cancel membership"""
        for membership in self:
            if membership.state in ['cancelled', 'terminated']:
                raise UserError(_("Membership is already cancelled or terminated."))
            
            membership.write({
                'state': 'cancelled',
                'cancellation_date': fields.Date.today()
            })

    def action_reinstate(self):
        """Reinstate suspended or cancelled membership"""
        for membership in self:
            if membership.state not in ['suspended', 'cancelled']:
                raise UserError(_("Only suspended or cancelled memberships can be reinstated."))
            
            # Determine new state based on dates
            today = fields.Date.today()
            if membership.end_date >= today:
                new_state = 'active'
            elif membership.grace_period_end and membership.grace_period_end >= today:
                new_state = 'grace'
            else:
                new_state = 'lapsed'
            
            membership.write({
                'state': new_state,
                'cancellation_date': False
            })

    def action_renew(self):
        """Open renewal wizard"""
        self.ensure_one()
        
        if not self.can_be_renewed:
            raise UserError(_("This membership cannot be renewed."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Membership'),
            'res_model': 'ams.membership.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_product_id': self.product_id.id,
            }
        }

    def action_upgrade(self):
        """Open upgrade wizard"""
        self.ensure_one()
        
        if self.state not in ['active', 'grace']:
            raise UserError(_("Only active or grace period memberships can be upgraded."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upgrade Membership'),
            'res_model': 'ams.membership.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_current_product_id': self.product_id.id,
            }
        }

    def action_view_invoice(self):
        """View related invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("No invoice linked to this membership."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }

    def action_create_renewal_invoice(self):
        """Create renewal invoice for this membership"""
        self.ensure_one()
        
        if not self.can_be_renewed:
            raise UserError(_("This membership cannot be renewed."))
        
        # Create sale order for renewal
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': f"Renewal of {self.name}",
        })
        
        # Add product line
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'price_unit': self.product_id.lst_price,
        })
        
        # Confirm order and create invoice
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    # Automated Processing Methods
    @api.model
    def process_membership_transitions(self):
        """Cron job to process membership status transitions"""
        _logger.info("Starting membership status transitions processing...")
        
        today = fields.Date.today()
        processed_count = 0
        
        try:
            # Process expired memberships -> grace period
            expired_memberships = self.search([
                ('state', '=', 'active'),
                ('end_date', '<', today)
            ])
            
            for membership in expired_memberships:
                grace_end = today + timedelta(days=membership._get_effective_grace_period())
                membership.write({
                    'state': 'grace',
                    'grace_period_end': grace_end
                })
                processed_count += 1
            
            _logger.info(f"Moved {len(expired_memberships)} memberships to grace period")
            
            # Process grace period -> lapsed
            grace_expired = self.search([
                ('state', '=', 'grace'),
                ('grace_period_end', '<=', today)
            ])
            
            for membership in grace_expired:
                membership.write({
                    'state': 'lapsed'
                })
                processed_count += 1
            
            _logger.info(f"Moved {len(grace_expired)} memberships to lapsed status")
            
            _logger.info(f"Membership transitions completed. Total processed: {processed_count}")
            
        except Exception as e:
            _logger.error(f"Error in membership status transitions: {str(e)}")

    @api.model
    def create_renewal_invoices(self):
        """Cron job to create renewal invoices"""
        _logger.info("Starting renewal invoice creation...")
        
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if not settings or not settings.auto_create_renewal_invoices:
            _logger.info("Auto renewal invoice creation disabled, skipping...")
            return
        
        advance_days = settings.renewal_invoice_days_advance
        target_date = fields.Date.today() + timedelta(days=advance_days)
        
        try:
            # Find memberships that need renewal invoices
            expiring_memberships = self.search([
                ('state', '=', 'active'),
                ('end_date', '=', target_date),
                ('auto_renewal', '=', True),
                ('next_membership_id', '=', False),  # No renewal created yet
            ])
            
            created_count = 0
            for membership in expiring_memberships:
                try:
                    membership.action_create_renewal_invoice()
                    created_count += 1
                except Exception as e:
                    _logger.warning(f"Failed to create renewal invoice for {membership.name}: {str(e)}")
                    continue
            
            _logger.info(f"Created {created_count} renewal invoices")
            
        except Exception as e:
            _logger.error(f"Error in renewal invoice creation: {str(e)}")

    # Portal Methods
    def _portal_ensure_token(self):
        """Ensure membership has access token for portal"""
        if not self.access_token:
            self.access_token = self._portal_generate_access_token()

    def _get_portal_return_action(self):
        """Return action for portal"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/membership/{self.id}',
            'target': 'self',
        }

    # Constraints and Validations
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate membership dates"""
        for membership in self:
            if membership.end_date <= membership.start_date:
                raise ValidationError(_("End date must be after start date."))

    @api.constrains('partner_id', 'product_id', 'state')
    def _check_multiple_active_memberships(self):
        """Check multiple active membership rules"""
        for membership in self:
            if membership.state not in ['active', 'grace']:
                continue
            
            product = membership.product_id.product_tmpl_id
            
            if not product.allow_multiple_active:
                # Check if partner has other active memberships of same product
                other_active = self.search([
                    ('partner_id', '=', membership.partner_id.id),
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', 'in', ['active', 'grace']),
                    ('id', '!=', membership.id)
                ])
                
                if other_active:
                    raise ValidationError(_(
                        "Member %s already has an active membership of type %s. "
                        "Multiple active memberships are not allowed for this product."
                    ) % (membership.partner_id.name, product.name))
            
            elif product.max_active_per_member > 0:
                # Check max limit
                active_count = self.search_count([
                    ('partner_id', '=', membership.partner_id.id),
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', 'in', ['active', 'grace'])
                ])
                
                if active_count > product.max_active_per_member:
                    raise ValidationError(_(
                        "Member %s has reached the maximum number of active memberships (%d) "
                        "for product %s."
                    ) % (membership.partner_id.name, product.max_active_per_member, product.name))

    def name_get(self):
        """Custom name_get"""
        result = []
        for record in self:
            if record.member_number:
                name = f"{record.member_number} - {record.partner_id.name}"
            else:
                name = f"{record.partner_id.name} - {record.product_id.name}"
            result.append((record.id, name))
        return result