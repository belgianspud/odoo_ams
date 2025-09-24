# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription (Non-Membership)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char('Subscription Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Partner Information
    partner_id = fields.Many2one('res.partner', 'Subscriber', required=True, tracking=True)
    account_id = fields.Many2one('res.partner', 'Account', 
                                help='Main account (for organizational subscriptions)')
    
    # Product and Sales Integration
    product_id = fields.Many2one('product.product', 'Subscription Product', required=True,
                                domain=[('is_subscription_product', '=', True), 
                                       ('subscription_product_type', '!=', 'membership')])
    subscription_type = fields.Selection([
        ('subscription', 'General Subscription'),
        ('publication', 'Publication'),
        ('chapter', 'Chapter'),
        ('event', 'Event Access'),
    ], string='Type', compute='_compute_subscription_type', store=True)
    
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True)
    
    # Subscription Timeline
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True)
    end_date = fields.Date('End Date', required=True, tracking=True)
    last_renewal_date = fields.Date('Last Renewal Date', tracking=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
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
    subscription_fee = fields.Monetary('Subscription Fee', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    payment_status = fields.Selection([
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
    ], string='Payment Status', default='pending', tracking=True)
    
    # Publication-specific fields
    digital_access = fields.Boolean('Digital Access', default=True)
    print_delivery = fields.Boolean('Print Delivery', default=False)
    delivery_address_id = fields.Many2one('res.partner', 'Delivery Address')
    
    # Chapter-specific fields
    chapter_role = fields.Selection([
        ('member', 'Chapter Member'),
        ('officer', 'Chapter Officer'),
        ('admin', 'Chapter Admin'),
    ], string='Chapter Role', default='member')
    
    # Event-specific fields
    event_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('vip', 'VIP Access'),
    ], string='Event Access Level', default='basic')
    
    # Benefits and Features
    benefit_ids = fields.Many2many('ams.benefit', 'subscription_benefit_rel', 
                                  'subscription_id', 'benefit_id', string='Active Benefits')
    
    # Renewal Management
    renewal_ids = fields.One2many('ams.renewal', 'subscription_id', 'Renewals')
    next_renewal_date = fields.Date('Next Renewal Date', compute='_compute_next_renewal_date', store=True)
    renewal_reminder_sent = fields.Boolean('Renewal Reminder Sent', default=False)
    
    # Additional Information
    notes = fields.Text('Internal Notes')
    tags = fields.Many2many('ams.subscription.tag', string='Tags')
    
    # Computed Fields
    is_expired = fields.Boolean('Is Expired', compute='_compute_status_flags')
    days_until_expiry = fields.Integer('Days Until Expiry', compute='_compute_status_flags')
    subscription_duration = fields.Integer('Duration (Days)', compute='_compute_subscription_duration')
    
    @api.depends('partner_id', 'product_id', 'start_date')
    def _compute_display_name(self):
        for subscription in self:
            if subscription.partner_id and subscription.product_id:
                subscription.display_name = f"{subscription.partner_id.name} - {subscription.product_id.name}"
            else:
                subscription.display_name = subscription.name or _('New Subscription')
    
    @api.depends('product_id.subscription_product_type')
    def _compute_subscription_type(self):
        for subscription in self:
            if subscription.product_id and hasattr(subscription.product_id, 'subscription_product_type'):
                subscription.subscription_type = subscription.product_id.subscription_product_type or 'subscription'
            else:
                subscription.subscription_type = 'subscription'
    
    @api.depends('end_date', 'auto_renew', 'renewal_interval')
    def _compute_next_renewal_date(self):
        for subscription in self:
            if not subscription.auto_renew or not subscription.end_date:
                subscription.next_renewal_date = False
                continue
            
            # Calculate next renewal based on interval
            if subscription.renewal_interval == 'monthly':
                subscription.next_renewal_date = subscription.end_date + relativedelta(months=1)
            elif subscription.renewal_interval == 'quarterly':
                subscription.next_renewal_date = subscription.end_date + relativedelta(months=3)
            elif subscription.renewal_interval == 'semi_annual':
                subscription.next_renewal_date = subscription.end_date + relativedelta(months=6)
            else:  # annual
                subscription.next_renewal_date = subscription.end_date + relativedelta(years=1)
    
    @api.depends('end_date')
    def _compute_status_flags(self):
        today = fields.Date.today()
        for subscription in self:
            if subscription.end_date:
                subscription.is_expired = subscription.end_date < today
                subscription.days_until_expiry = (subscription.end_date - today).days
            else:
                subscription.is_expired = False
                subscription.days_until_expiry = 0
    
    @api.depends('start_date', 'end_date')
    def _compute_subscription_duration(self):
        for subscription in self:
            if subscription.start_date and subscription.end_date:
                subscription.subscription_duration = (subscription.end_date - subscription.start_date).days
            else:
                subscription.subscription_duration = 0

    @api.model
    def create(self, vals):
        """Override create to handle sequence and setup"""
        if vals.get('name', _('New')) == _('New'):
            sequence_code = 'ams.subscription'
            if vals.get('subscription_type'):
                sequence_code = f'ams.subscription.{vals["subscription_type"]}'
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or _('New')
        
        subscription = super().create(vals)
        
        # Set benefits based on product configuration
        if subscription.product_id and hasattr(subscription.product_id, 'benefit_ids') and subscription.product_id.benefit_ids:
            subscription.benefit_ids = [(6, 0, subscription.product_id.benefit_ids.ids)]
        
        return subscription
    
    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for subscription in self:
                subscription._handle_state_change(vals['state'])
        
        return result
    
    def _handle_state_change(self, new_state):
        """Handle subscription state changes"""
        self.ensure_one()
        
        if new_state == 'active':
            # Enable benefits
            pass  # Benefits are already linked
        elif new_state in ['paused', 'suspended', 'terminated']:
            # Handle benefit suspension if needed
            pass
    
    # Action Methods
    def action_activate(self):
        """Activate subscription"""
        for subscription in self:
            if subscription.state != 'draft':
                raise UserError(_("Only draft subscriptions can be activated."))
            
            subscription.write({
                'state': 'active',
                'start_date': fields.Date.today(),
            })
    
    def action_pause(self):
        """Pause subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_("Only active subscriptions can be paused."))
            
            subscription.write({'state': 'paused'})
    
    def action_resume(self):
        """Resume paused subscription"""
        for subscription in self:
            if subscription.state != 'paused':
                raise UserError(_("Only paused subscriptions can be resumed."))
            
            subscription.write({'state': 'active'})
    
    def action_suspend(self):
        """Suspend subscription"""
        for subscription in self:
            if subscription.state not in ['active', 'paused']:
                raise UserError(_("Only active or paused subscriptions can be suspended."))
            
            subscription.write({'state': 'suspended'})
    
    def action_terminate(self):
        """Terminate subscription"""
        for subscription in self:
            subscription.write({'state': 'terminated'})
    
    def action_renew(self):
        """Create renewal for this subscription"""
        self.ensure_one()
        
        renewal = self.env['ams.renewal'].create({
            'subscription_id': self.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': self._calculate_renewal_end_date(),
            'amount': self.subscription_fee,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Renewal'),
            'res_model': 'ams.renewal',
            'res_id': renewal.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_view_invoice(self):
        """View subscription invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this subscription."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
    
    def action_view_sale_order(self):
        """View subscription sale order"""
        self.ensure_one()
        
        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this subscription."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
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
        """Create subscription from paid invoice line"""
        product = invoice_line.product_id.product_tmpl_id
        
        if not product.is_subscription_product or product.subscription_product_type == 'membership':
            return False
        
        # Check if subscription already exists for this invoice line
        existing = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing:
            return existing
        
        partner = invoice_line.move_id.partner_id
        
        # Calculate subscription period
        start_date = fields.Date.today()
        if hasattr(product, 'subscription_period'):
            if product.subscription_period == 'monthly':
                end_date = start_date + relativedelta(months=1) - timedelta(days=1)
            elif product.subscription_period == 'quarterly':
                end_date = start_date + relativedelta(months=3) - timedelta(days=1)
            elif product.subscription_period == 'semi_annual':
                end_date = start_date + relativedelta(months=6) - timedelta(days=1)
            else:  # annual or default
                end_date = start_date + relativedelta(years=1) - timedelta(days=1)
        else:
            # Default to annual if no subscription period
            end_date = start_date + relativedelta(years=1) - timedelta(days=1)
        
        subscription_vals = {
            'partner_id': partner.id,
            'product_id': invoice_line.product_id.id,
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'start_date': start_date,
            'end_date': end_date,
            'last_renewal_date': start_date,
            'subscription_fee': invoice_line.price_subtotal,
            'payment_status': 'paid',
            'state': 'active',
            'auto_renew': getattr(product, 'auto_renew_default', True),
            'renewal_interval': getattr(product, 'subscription_period', 'annual'),
        }
        
        # Set type-specific fields
        if hasattr(product, 'subscription_product_type') and product.subscription_product_type == 'publication':
            subscription_vals.update({
                'digital_access': getattr(product, 'publication_digital_access', True),
                'print_delivery': getattr(product, 'publication_print_delivery', False),
            })
        
        subscription = self.create(subscription_vals)
        
        _logger.info(f"Created subscription {subscription.name} for {partner.name}")
        
        return subscription
    
    @api.model
    def process_subscription_lifecycle(self):
        """Cron job to process subscription lifecycle transitions"""
        _logger.info("Processing subscription lifecycle transitions...")
        
        today = fields.Date.today()
        
        # Active -> Suspended (expired subscriptions)
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', False),
        ])
        
        for subscription in expired_subscriptions:
            subscription.write({'state': 'suspended'})
            _logger.info(f"Suspended subscription {subscription.name}")
        
        # Handle auto-renewals
        auto_renewals = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', True),
        ])
        
        for subscription in auto_renewals:
            # Create automatic renewal
            try:
                subscription._create_automatic_renewal()
            except Exception as e:
                _logger.error(f"Failed to auto-renew subscription {subscription.name}: {str(e)}")
    
    def _create_automatic_renewal(self):
        """Create automatic renewal for subscription"""
        self.ensure_one()
        
        new_end_date = self._calculate_renewal_end_date()
        
        # Create renewal record
        renewal = self.env['ams.renewal'].create({
            'subscription_id': self.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': new_end_date,
            'amount': self.subscription_fee,
            'renewal_type': 'automatic',
            'state': 'confirmed',
        })
        
        # Update subscription
        self.write({
            'end_date': new_end_date,
            'last_renewal_date': fields.Date.today(),
        })
        
        _logger.info(f"Auto-renewed subscription {self.name} until {new_end_date}")
        
        return renewal
    
    # Constraints
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for subscription in self:
            if subscription.start_date and subscription.end_date:
                if subscription.end_date <= subscription.start_date:
                    raise ValidationError(_("End date must be after start date."))


    def action_view_invoice(self):
        """View subscription invoice"""
        self.ensure_one()
    
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this subscription."))
    
        return {
           'type': 'ir.actions.act_window',
            'name': _('Subscription Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_view_sale_order(self):
        """View subscription sale order"""
        self.ensure_one()
    
        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this subscription."))
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

class AMSSubscriptionTag(models.Model):
    _name = 'ams.subscription.tag'
    _description = 'Subscription Tag'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color')
    active = fields.Boolean('Active', default=True)