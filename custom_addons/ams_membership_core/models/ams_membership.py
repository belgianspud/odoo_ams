# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSMembership(models.Model):
    _name = 'ams.membership'
    _description = 'Association Membership Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char('Membership Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Member Information
    partner_id = fields.Many2one('res.partner', 'Member', required=True, tracking=True,
                                domain=[('is_member', '=', True)])
    member_type_id = fields.Many2one(related='partner_id.member_type_id', store=True, readonly=True)
    
    # Product and Sales Integration
    product_id = fields.Many2one('product.product', 'Membership Product', required=True,
                                domain=[('is_subscription_product', '=', True), 
                                       ('subscription_product_type', '=', 'membership')])
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True)
    
    # Membership Timeline
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True)
    end_date = fields.Date('End Date', required=True, tracking=True)
    last_renewal_date = fields.Date('Last Renewal Date', tracking=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)
    
    # Renewal Configuration
    auto_renew = fields.Boolean('Auto Renew', default=True, tracking=True)
    renewal_interval = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Renewal Interval', default='annual', required=True)
    
    # Pricing and Payment
    membership_fee = fields.Monetary('Membership Fee', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    payment_status = fields.Selection([
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
    ], string='Payment Status', default='pending', tracking=True)
    
    # Benefits and Features
    benefit_ids = fields.Many2many('ams.benefit', 'membership_benefit_rel', 
                                  'membership_id', 'benefit_id', string='Active Benefits')
    has_portal_access = fields.Boolean('Has Portal Access', compute='_compute_portal_access', store=True)
    
    # Lifecycle Dates (computed based on settings)
    grace_end_date = fields.Date('Grace Period End', compute='_compute_lifecycle_dates', store=True)
    suspension_end_date = fields.Date('Suspension End Date', compute='_compute_lifecycle_dates', store=True)
    termination_date = fields.Date('Termination Date', compute='_compute_lifecycle_dates', store=True)
    
    # Renewal Management
    renewal_ids = fields.One2many('ams.renewal', 'membership_id', 'Renewals')
    next_renewal_date = fields.Date('Next Renewal Date', compute='_compute_next_renewal_date', store=True)
    renewal_reminder_sent = fields.Boolean('Renewal Reminder Sent', default=False)
    
    # Additional Information
    notes = fields.Text('Internal Notes')
    tags = fields.Many2many('ams.membership.tag', string='Tags')
    
    # Computed Fields
    is_expired = fields.Boolean('Is Expired', compute='_compute_status_flags')
    days_until_expiry = fields.Integer('Days Until Expiry', compute='_compute_status_flags')
    membership_duration = fields.Integer('Duration (Days)', compute='_compute_membership_duration')
    
    @api.depends('partner_id', 'product_id', 'start_date')
    def _compute_display_name(self):
        for membership in self:
            if membership.partner_id and membership.product_id:
                membership.display_name = f"{membership.partner_id.name} - {membership.product_id.name}"
            else:
                membership.display_name = membership.name or _('New Membership')
    
    @api.depends('partner_id.portal_user_id')
    def _compute_portal_access(self):
        for membership in self:
            membership.has_portal_access = bool(membership.partner_id.portal_user_id)
    
    @api.depends('end_date', 'member_type_id')
    def _compute_lifecycle_dates(self):
        for membership in self:
            if not membership.end_date:
                membership.grace_end_date = False
                membership.suspension_end_date = False
                membership.termination_date = False
                continue
            
            # Get grace period from member type or settings
            if membership.member_type_id and membership.member_type_id.grace_period_override:
                grace_days = membership.member_type_id.grace_period_days
            else:
                settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
                grace_days = settings.grace_period_days if settings else 30
            
            membership.grace_end_date = membership.end_date + timedelta(days=grace_days)
            membership.suspension_end_date = membership.grace_end_date + timedelta(days=60)
            membership.termination_date = membership.suspension_end_date + timedelta(days=30)
    
    @api.depends('end_date', 'auto_renew', 'renewal_interval')
    def _compute_next_renewal_date(self):
        for membership in self:
            if not membership.auto_renew or not membership.end_date:
                membership.next_renewal_date = False
                continue
            
            # Calculate next renewal based on interval
            if membership.renewal_interval == 'monthly':
                membership.next_renewal_date = membership.end_date + relativedelta(months=1)
            elif membership.renewal_interval == 'quarterly':
                membership.next_renewal_date = membership.end_date + relativedelta(months=3)
            elif membership.renewal_interval == 'semi_annual':
                membership.next_renewal_date = membership.end_date + relativedelta(months=6)
            else:  # annual
                membership.next_renewal_date = membership.end_date + relativedelta(years=1)
    
    @api.depends('end_date')
    def _compute_status_flags(self):
        today = fields.Date.today()
        for membership in self:
            if membership.end_date:
                membership.is_expired = membership.end_date < today
                membership.days_until_expiry = (membership.end_date - today).days
            else:
                membership.is_expired = False
                membership.days_until_expiry = 0
    
    @api.depends('start_date', 'end_date')
    def _compute_membership_duration(self):
        for membership in self:
            if membership.start_date and membership.end_date:
                membership.membership_duration = (membership.end_date - membership.start_date).days
            else:
                membership.membership_duration = 0

    @api.model
    def create(self, vals):
        """Override create to handle sequence and validations"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.membership') or _('New')
        
        membership = super().create(vals)
        
        # Set benefits based on product configuration
        if membership.product_id and membership.product_id.benefit_ids:
            membership.benefit_ids = [(6, 0, membership.product_id.benefit_ids.ids)]
        
        # Handle membership type restrictions (only 1 active membership)
        if membership.product_id.subscription_product_type == 'membership':
            membership._ensure_single_active_membership()
        
        return membership
    
    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for membership in self:
                membership._handle_state_change(vals['state'])
        
        return result
    
    def _ensure_single_active_membership(self):
        """Ensure only one active membership per member"""
        self.ensure_one()
        
        if self.state != 'active':
            return
        
        # Find other active memberships for same member
        other_memberships = self.search([
            ('partner_id', '=', self.partner_id.id),
            ('product_id.subscription_product_type', '=', 'membership'),
            ('state', '=', 'active'),
            ('id', '!=', self.id)
        ])
        
        if other_memberships:
            # Terminate other active memberships
            other_memberships.write({
                'state': 'terminated',
                'notes': f"Terminated due to new active membership: {self.name}"
            })
    
    def _handle_state_change(self, new_state):
        """Handle membership state changes"""
        self.ensure_one()
        
        if new_state == 'active':
            # Update partner membership status
            self.partner_id.write({
                'member_status': 'active',
                'membership_start_date': self.start_date,
                'membership_end_date': self.end_date,
            })
            
            # Ensure single active membership for membership products
            if self.product_id.subscription_product_type == 'membership':
                self._ensure_single_active_membership()
        
        elif new_state == 'terminated':
            # Check if this was the active membership
            if (self.partner_id.member_status == 'active' and 
                self.product_id.subscription_product_type == 'membership'):
                # Look for other active memberships
                other_active = self.search([
                    ('partner_id', '=', self.partner_id.id),
                    ('product_id.subscription_product_type', '=', 'membership'),
                    ('state', '=', 'active'),
                    ('id', '!=', self.id)
                ])
                
                if not other_active:
                    # No other active memberships, update partner status
                    self.partner_id.write({'member_status': 'terminated'})
    
    # Action Methods
    def action_activate(self):
        """Activate membership"""
        for membership in self:
            if membership.state != 'draft':
                raise UserError(_("Only draft memberships can be activated."))
            
            membership.write({
                'state': 'active',
                'start_date': fields.Date.today(),
            })
    
    def action_suspend(self):
        """Suspend membership"""
        for membership in self:
            if membership.state not in ['active', 'grace']:
                raise UserError(_("Only active or grace period memberships can be suspended."))
            
            membership.write({'state': 'suspended'})
    
    def action_terminate(self):
        """Terminate membership"""
        for membership in self:
            membership.write({'state': 'terminated'})
    
    def action_renew(self):
        """Create renewal for this membership"""
        self.ensure_one()
        
        renewal = self.env['ams.renewal'].create({
            'membership_id': self.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': self._calculate_renewal_end_date(),
            'amount': self.membership_fee,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Renewal'),
            'res_model': 'ams.renewal',
            'res_id': renewal.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _calculate_renewal_end_date(self):
        """Calculate the new end date for renewal"""
        self.ensure_one()
        
        base_date = max(self.end_date, fields.Date.today())
        
        if self.renewal_interval == 'monthly':
            return base_date + relativedelta(months=1)
        elif self.renewal_interval == 'quarterly':
            return base_date + relativedelta(months=3)
        elif self.renewal_interval == 'semi_annual':
            return base_date + relativedelta(months=6)
        else:  # annual
            return base_date + relativedelta(years=1)
    
    @api.model
    def create_from_invoice_payment(self, invoice_line):
        """Create membership from paid invoice line"""
        product = invoice_line.product_id.product_tmpl_id
        
        if not product.is_subscription_product or product.subscription_product_type != 'membership':
            return False
        
        # Check if membership already exists for this invoice line
        existing = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing:
            return existing
        
        partner = invoice_line.move_id.partner_id
        
        # Calculate membership period
        start_date = fields.Date.today()
        if product.subscription_period == 'monthly':
            end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        elif product.subscription_period == 'quarterly':
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        elif product.subscription_period == 'semi_annual':
            end_date = start_date + relativedelta(months=6) - timedelta(days=1)
        else:  # annual or default
            end_date = start_date + relativedelta(years=1) - timedelta(days=1)
        
        membership_vals = {
            'partner_id': partner.id,
            'product_id': invoice_line.product_id.id,
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'start_date': start_date,
            'end_date': end_date,
            'last_renewal_date': start_date,
            'membership_fee': invoice_line.price_subtotal,
            'payment_status': 'paid',
            'state': 'active',
            'auto_renew': product.auto_renew_default or True,
            'renewal_interval': product.subscription_period or 'annual',
        }
        
        membership = self.create(membership_vals)
        
        _logger.info(f"Created membership {membership.name} for {partner.name}")
        
        return membership
    
    @api.model
    def process_membership_lifecycle(self):
        """Cron job to process membership lifecycle transitions"""
        _logger.info("Processing membership lifecycle transitions...")
        
        today = fields.Date.today()
        
        # Active -> Grace (expired memberships)
        expired_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
        ])
        
        for membership in expired_memberships:
            membership.write({'state': 'grace'})
            _logger.info(f"Moved membership {membership.name} to grace period")
        
        # Grace -> Suspended (grace period ended)
        grace_expired = self.search([
            ('state', '=', 'grace'),
            ('grace_end_date', '<', today),
        ])
        
        for membership in grace_expired:
            membership.write({'state': 'suspended'})
            _logger.info(f"Suspended membership {membership.name}")
        
        # Suspended -> Terminated (suspension period ended)
        suspension_expired = self.search([
            ('state', '=', 'suspended'),
            ('suspension_end_date', '<', today),
        ])
        
        for membership in suspension_expired:
            membership.write({'state': 'terminated'})
            _logger.info(f"Terminated membership {membership.name}")
    
    @api.model
    def send_renewal_reminders(self):
        """Send renewal reminders for expiring memberships"""
        reminder_days = 30  # TODO: Make configurable
        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        
        expiring_memberships = self.search([
            ('state', '=', 'active'),
            ('auto_renew', '=', False),
            ('end_date', '<=', reminder_date),
            ('renewal_reminder_sent', '=', False),
        ])
        
        for membership in expiring_memberships:
            # TODO: Send renewal reminder email
            membership.renewal_reminder_sent = True
            _logger.info(f"Sent renewal reminder for membership {membership.name}")
    
    # Constraints
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for membership in self:
            if membership.start_date and membership.end_date:
                if membership.end_date <= membership.start_date:
                    raise ValidationError(_("End date must be after start date."))
    
    @api.constrains('partner_id', 'product_id', 'state')
    def _check_single_active_membership(self):
        """Ensure only one active membership per member"""
        for membership in self:
            if (membership.state == 'active' and 
                membership.product_id.subscription_product_type == 'membership'):
                
                existing = self.search([
                    ('partner_id', '=', membership.partner_id.id),
                    ('product_id.subscription_product_type', '=', 'membership'),
                    ('state', '=', 'active'),
                    ('id', '!=', membership.id)
                ])
                
                if existing:
                    raise ValidationError(
                        _("Member %s already has an active membership: %s. "
                          "Only one active membership is allowed per member.") % 
                        (membership.partner_id.name, existing[0].name)
                    )


class AMSMembershipTag(models.Model):
    _name = 'ams.membership.tag'
    _description = 'Membership Tag'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color')
    active = fields.Boolean('Active', default=True)