# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
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
    
    # Member Information (integrated with ams_foundation)
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
    
    # Lifecycle Dates (computed using foundation settings)
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
        """Compute lifecycle dates using ams_foundation settings"""
        for membership in self:
            if not membership.end_date:
                membership.grace_end_date = False
                membership.suspension_end_date = False
                membership.termination_date = False
                continue
            
            # Get grace period from member type or foundation settings
            grace_days = membership._get_effective_grace_period()
            
            membership.grace_end_date = membership.end_date + timedelta(days=grace_days)
            membership.suspension_end_date = membership.grace_end_date + timedelta(days=60)
            membership.termination_date = membership.suspension_end_date + timedelta(days=30)
    
    def _get_effective_grace_period(self):
        """Get effective grace period using foundation settings"""
        self.ensure_one()
        
        # First check member type override
        if self.member_type_id and hasattr(self.member_type_id, 'grace_period_override') and self.member_type_id.grace_period_override:
            return getattr(self.member_type_id, 'grace_period_days', 30)
        
        # Then check foundation settings
        settings = self._get_ams_settings()
        if settings and hasattr(settings, 'grace_period_days'):
            return settings.grace_period_days
        
        # Default fallback
        return 30
    
    def _get_ams_settings(self):
        """Get active AMS settings from foundation"""
        return self.env['ams.settings'].search([('active', '=', True)], limit=1)
    
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
        """Override create to handle sequence and integrations"""
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
        """Override write to handle state changes and foundation integration"""
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
        """Handle membership state changes and sync with foundation"""
        self.ensure_one()
        
        if new_state == 'active':
            # Update foundation partner membership status
            partner_vals = {
                'member_status': 'active',
                'membership_start_date': self.start_date,
                'membership_end_date': self.end_date,
            }
            # Use context to prevent recursion
            self.partner_id.with_context(skip_portal_creation=True).write(partner_vals)
            
            # Ensure single active membership for membership products
            if self.product_id.subscription_product_type == 'membership':
                self._ensure_single_active_membership()
            
            # Grant portal access if product allows and foundation settings enable it
            self._handle_portal_access_on_activation()
            
            # Apply engagement points for membership activation
            self._apply_engagement_points('membership_activation')
        
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
                    self.partner_id.with_context(skip_portal_creation=True).write({
                        'member_status': 'terminated'
                    })

    def _handle_portal_access_on_activation(self):
        """Handle portal access when membership becomes active"""
        self.ensure_one()
        
        # Check if product grants portal access
        if not self.product_id.grant_portal_access:
            return
        
        # Check if foundation settings allow auto portal user creation
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'auto_create_portal_users') or not settings.auto_create_portal_users:
            return
        
        # Use foundation's portal user creation method
        if not self.partner_id.portal_user_id and self.partner_id.email:
            try:
                self.partner_id.action_create_portal_user()
            except Exception as e:
                _logger.warning(f"Failed to create portal user for {self.partner_id.name}: {str(e)}")
    
    def _apply_engagement_points(self, rule_type, context_data=None):
        """Apply engagement points using foundation's engagement system"""
        self.ensure_one()
        
        # Check if engagement scoring is enabled in foundation settings
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'engagement_scoring_enabled') or not settings.engagement_scoring_enabled:
            return
        
        # Find applicable engagement rules
        engagement_rules = self.env['ams.engagement.rule'].search([
            ('rule_type', '=', rule_type),
            ('active', '=', True)
        ])
        
        for rule in engagement_rules:
            try:
                if hasattr(rule, 'apply_rule'):
                    success, message = rule.apply_rule(self.partner_id, context_data)
                    if success:
                        _logger.info(f"Applied engagement rule {rule.name} to {self.partner_id.name}")
                    else:
                        _logger.debug(f"Engagement rule {rule.name} not applied: {message}")
            except Exception as e:
                _logger.warning(f"Failed to apply engagement rule {rule.name}: {str(e)}")
    
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
        """Create membership from paid invoice line - CORRECTED VERSION"""
        product = invoice_line.product_id.product_tmpl_id
        
        if not product.is_subscription_product or product.subscription_product_type != 'membership':
            return False
        
        # Check if membership already exists for this invoice line
        existing = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing:
            return existing
        
        partner = invoice_line.move_id.partner_id
        
        # CRITICAL FIXES START HERE
        
        # 1. ENSURE PARTNER IS MARKED AS MEMBER
        partner_vals = {}
        if not partner.is_member:
            partner_vals['is_member'] = True
            _logger.info(f"Setting is_member=True for {partner.name}")
        
        # 2. SET DEFAULT MEMBER TYPE IF NONE EXISTS
        if not partner.member_type_id:
            # Look for default member type (first try "Regular", then "Individual", then first available)
            default_member_type = self.env['ams.member.type'].search([
                ('name', 'ilike', 'regular')
            ], limit=1)
            
            if not default_member_type:
                default_member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', 'individual')
                ], limit=1)
            
            if not default_member_type:
                default_member_type = self.env['ams.member.type'].search([], limit=1)
            
            if default_member_type:
                partner_vals['member_type_id'] = default_member_type.id
                _logger.info(f"Setting default member type {default_member_type.name} for {partner.name}")
        
        # 3. GENERATE MEMBER NUMBER/ID IF NOT EXISTS
        if not getattr(partner, 'member_number', None):
            # Try foundation's method first
            if hasattr(partner, '_generate_member_number'):
                partner._generate_member_number()
            else:
                # Fallback: use sequence or simple generation
                try:
                    settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
                    if settings:
                        prefix = getattr(settings, 'member_number_prefix', 'M')
                        padding = getattr(settings, 'member_number_padding', 6)
                        sequence = self.env['ir.sequence'].next_by_code('ams.member.number')
                        if not sequence:
                            # Create a simple incremental number
                            last_member = self.env['res.partner'].search([
                                ('is_member', '=', True),
                                ('member_number', '!=', False)
                            ], order='id desc', limit=1)
                            next_num = 1
                            if last_member and last_member.member_number:
                                try:
                                    # Extract number from existing member number
                                    import re
                                    numbers = re.findall(r'\d+', last_member.member_number)
                                    if numbers:
                                        next_num = int(numbers[-1]) + 1
                                except:
                                    next_num = 1
                            sequence = str(next_num).zfill(padding)
                        member_number = f"{prefix}{sequence}"
                        partner_vals['member_number'] = member_number
                        _logger.info(f"Generated member number {member_number} for {partner.name}")
                except Exception as e:
                    _logger.warning(f"Could not generate member number for {partner.name}: {str(e)}")
        
        # 4. SET MEMBER STATUS TO ACTIVE
        partner_vals['member_status'] = 'active'
        
        # Apply all partner updates at once
        if partner_vals:
            partner.with_context(skip_portal_creation=True).write(partner_vals)
        
        # 5. CALCULATE MEMBERSHIP DATES
        start_date = fields.Date.today()
        
        # FIXED: Annual memberships should end December 31st
        if product.subscription_period == 'annual':
            # Always set to December 31st of the current year
            # If we're already past December 31st, set to next year's December 31st
            current_year = start_date.year
            end_date = date(current_year, 12, 31)
            
            # If purchase date is after December 31st (shouldn't happen) or it's December 31st,
            # extend to next year
            if start_date > end_date:
                end_date = date(current_year + 1, 12, 31)
                
        elif product.subscription_period == 'monthly':
            end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        elif product.subscription_period == 'quarterly':
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        elif product.subscription_period == 'semi_annual':
            end_date = start_date + relativedelta(months=6) - timedelta(days=1)
        else:  # default to annual
            current_year = start_date.year
            end_date = date(current_year, 12, 31)
            if start_date > end_date:
                end_date = date(current_year + 1, 12, 31)
        
        # 6. UPDATE FOUNDATION PARTNER DATES
        partner.with_context(skip_portal_creation=True).write({
            'membership_start_date': start_date,
            'membership_end_date': end_date,
        })
        
        # 7. CREATE MEMBERSHIP RECORD
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
        
        _logger.info(f"Created membership {membership.name} for {partner.name} "
                     f"from {start_date} to {end_date}")
        
        return membership
    
    @api.model
    def process_membership_lifecycle(self):
        """Cron job to process membership lifecycle transitions using foundation logic"""
        _logger.info("Processing membership lifecycle transitions...")
        
        # Let foundation handle the main lifecycle transitions
        # This method will sync membership records with partner status
        today = fields.Date.today()
        
        # Sync active memberships with expired foundation member status
        expired_partners = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_status', '=', 'grace'),
            ('membership_end_date', '<', today)
        ])
        
        for partner in expired_partners:
            active_memberships = self.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ])
            
            for membership in active_memberships:
                membership.write({'state': 'grace'})
                _logger.info(f"Synced membership {membership.name} to grace period")
        
        # Sync lapsed members
        lapsed_partners = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_status', '=', 'lapsed')
        ])
        
        for partner in lapsed_partners:
            grace_memberships = self.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'grace')
            ])
            
            for membership in grace_memberships:
                membership.write({'state': 'suspended'})
                _logger.info(f"Synced membership {membership.name} to suspended")
    
    @api.model
    def send_renewal_reminders(self):
        """Send renewal reminders using foundation settings"""
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'renewal_reminder_enabled') or not settings.renewal_reminder_enabled:
            return
        
        reminder_days = getattr(settings, 'renewal_reminder_days', 30)
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

    def action_view_invoice(self):
        """View membership invoice"""
        self.ensure_one()
    
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this membership."))
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_view_sale_order(self):
        """View membership sale order"""
        self.ensure_one()

        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this membership."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }


class AMSMembershipTag(models.Model):
    _name = 'ams.membership.tag'
    _description = 'Membership Tag'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color')
    active = fields.Boolean('Active', default=True)