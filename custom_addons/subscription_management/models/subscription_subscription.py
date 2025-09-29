# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class SubscriptionSubscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription'
    _order = 'date_start desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Subscription Reference', required=True, copy=False,
                       readonly=True, default=lambda x: _('New'))
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,
                                 tracking=True, index=True)
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address')
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address')
    
    # Plan and Pricing
    plan_id = fields.Many2one('subscription.plan', 'Subscription Plan',
                              required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  related='plan_id.currency_id', store=True)
    
    # Subscription Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True, index=True)
    
    # Dates
    date_start = fields.Date('Start Date', required=True, tracking=True,
                             default=fields.Date.today)
    date_end = fields.Date('End Date', tracking=True)
    trial_end_date = fields.Date('Trial End Date', compute='_compute_trial_end_date',
                                 store=True)
    next_billing_date = fields.Date('Next Billing Date', 
                                    compute='_compute_next_billing_date',
                                    store=True)
    
    # Billing
    price = fields.Float('Price', related='plan_id.price', store=True)
    last_invoice_id = fields.Many2one('account.move', 'Last Invoice')
    last_invoice_date = fields.Date('Last Invoice Date')
    
    # Usage Tracking
    current_usage = fields.Float('Current Usage')
    usage_limit = fields.Float('Usage Limit', related='plan_id.included_usage')
    usage_overage = fields.Float('Usage Overage', compute='_compute_usage_overage')
    
    # Relations
    line_ids = fields.One2many('subscription.line', 'subscription_id',
                               'Subscription Lines')
    usage_ids = fields.One2many('subscription.usage', 'subscription_id',
                                'Usage Records')
    invoice_ids = fields.One2many('account.move', 'subscription_id',
                                  'Invoices')
    tag_ids = fields.Many2many('subscription.tag', string='Tags')
    
    # Counts
    invoice_count = fields.Integer('Invoice Count', compute='_compute_invoice_count')
    
    # Portal Access
    access_token = fields.Char('Access Token', copy=False)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('subscription.subscription') or _('New')
        return super().create(vals)
    
    @api.depends('plan_id.trial_period', 'date_start')
    def _compute_trial_end_date(self):
        for subscription in self:
            if subscription.plan_id.trial_period > 0 and subscription.date_start:
                subscription.trial_end_date = subscription.date_start + relativedelta(
                    days=subscription.plan_id.trial_period
                )
            else:
                subscription.trial_end_date = False
    
    @api.depends('date_start', 'plan_id', 'last_invoice_date', 'state')
    def _compute_next_billing_date(self):
        for subscription in self:
            if subscription.state in ('active', 'trial') and subscription.plan_id:
                if subscription.last_invoice_date:
                    base_date = subscription.last_invoice_date
                else:
                    base_date = subscription.trial_end_date or subscription.date_start
                
                if base_date:
                    subscription.next_billing_date = subscription.plan_id.get_next_billing_date(base_date)
                else:
                    subscription.next_billing_date = False
            else:
                subscription.next_billing_date = False
    
    @api.depends('current_usage', 'usage_limit')
    def _compute_usage_overage(self):
        for subscription in self:
            if subscription.usage_limit > 0:
                subscription.usage_overage = max(0, subscription.current_usage - subscription.usage_limit)
            else:
                subscription.usage_overage = 0
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)
    
    def action_start_trial(self):
        """Start trial period"""
        self.ensure_one()
        if self.plan_id.trial_period > 0:
            self.state = 'trial'
        else:
            self.state = 'active'
        self._create_initial_invoice()
    
    def action_activate(self):
        """Activate subscription"""
        self.ensure_one()
        self.state = 'active'
        if not self.last_invoice_date:
            self._create_initial_invoice()
    
    def action_suspend(self):
        """Suspend subscription"""
        self.ensure_one()
        self.state = 'suspended'
    
    def action_cancel(self):
        """Cancel subscription"""
        self.ensure_one()
        self.state = 'cancelled'
        self.date_end = fields.Date.today()
    
    def action_renew(self):
        """Renew subscription"""
        self.ensure_one()
        if self.plan_id.auto_renew:
            self.date_end = self.plan_id.get_next_billing_date(self.date_end or self.date_start)
            if self.state == 'expired':
                self.state = 'active'
    
    def action_view_invoices(self):
        """Action to view subscription invoices"""
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def _create_initial_invoice(self):
        """Create the initial invoice for the subscription"""
        if self.state == 'trial' and self.plan_id.trial_price == 0:
            return
        
        invoice_vals = self._prepare_invoice_vals()
        invoice = self.env['account.move'].create(invoice_vals)
        
        self.last_invoice_id = invoice.id
        self.last_invoice_date = fields.Date.today()
        
        return invoice
    
    def _prepare_invoice_vals(self):
        """Prepare invoice values"""
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'subscription_id': self.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.plan_id.product_template_id.product_variant_id.id,
                'name': f"Subscription: {self.plan_id.name}",
                'quantity': 1,
                'price_unit': self.plan_id.trial_price if self.state == 'trial' else self.plan_id.price,
            })],
        }
    
    def add_usage(self, usage_type, quantity, description=None, price_unit=0.0):
        """Add usage record to subscription"""
        self.ensure_one()
        usage_vals = {
            'subscription_id': self.id,
            'usage_type': usage_type,
            'quantity': quantity,
            'description': description or f"{usage_type}: {quantity}",
            'price_unit': price_unit,
        }
        usage = self.env['subscription.usage'].create(usage_vals)
        
        # Update current usage
        self.current_usage += quantity
        
        return usage
    
    @api.model
    def _cron_process_billing(self):
        """Process billing for subscriptions due today"""
        today = fields.Date.today()
        subscriptions = self.search([
            ('state', 'in', ['active', 'trial']),
            ('next_billing_date', '<=', today)
        ])
        
        _logger.info(f"Processing billing for {len(subscriptions)} subscriptions")
        
        for subscription in subscriptions:
            try:
                subscription._process_billing()
            except Exception as e:
                _logger.error(f"Error processing billing for subscription {subscription.name}: {e}")
    
    def _process_billing(self):
        """Process billing for this subscription"""
        self.ensure_one()
        
        if self.state not in ('active', 'trial'):
            return
        
        # Create invoice
        invoice_vals = self._prepare_invoice_vals()
        
        # Add usage overage if applicable
        if self.usage_overage > 0 and self.plan_id.usage_price > 0:
            overage_line = {
                'product_id': self.plan_id.product_template_id.product_variant_id.id,
                'name': f"Usage overage: {self.usage_overage} {self.plan_id.usage_unit}",
                'quantity': self.usage_overage,
                'price_unit': self.plan_id.usage_price,
            }
            invoice_vals['invoice_line_ids'].append((0, 0, overage_line))
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Update subscription
        self.last_invoice_id = invoice.id
        self.last_invoice_date = fields.Date.today()
        
        # Reset usage for next period
        if self.plan_id.usage_based:
            self.current_usage = 0
        
        # Post invoice automatically (optional)
        try:
            invoice.action_post()
        except Exception as e:
            _logger.warning(f"Could not auto-post invoice {invoice.name}: {e}")
        
        # Send invoice by email
        self._send_invoice_email(invoice)
        
        return invoice
    
    def _send_invoice_email(self, invoice):
        """Send invoice by email"""
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        if template:
            template.send_mail(invoice.id, force_send=True)
    
    @api.model
    def _cron_check_trial_expiry(self):
        """Check for trial subscriptions that are expiring"""
        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        
        # Find trials expiring tomorrow (send reminder)
        trials_expiring = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '=', tomorrow)
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_trial_expiry', 
                               raise_if_not_found=False)
        if template:
            for subscription in trials_expiring:
                template.send_mail(subscription.id, force_send=False)
        
        # Find trials that expired today (convert to active)
        trials_expired = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '<=', today)
        ])
        
        for subscription in trials_expired:
            subscription.action_activate()
    
    @api.model
    def _cron_check_expiry(self):
        """Check for subscriptions that have expired"""
        today = fields.Date.today()
        
        expired_subscriptions = self.search([
            ('state', 'in', ['active', 'suspended']),
            ('date_end', '<=', today),
            ('date_end', '!=', False)
        ])
        
        for subscription in expired_subscriptions:
            subscription.state = 'expired'
    
    @api.model
    def _cron_auto_renew(self):
        """Process auto-renewals for expiring subscriptions"""
        today = fields.Date.today()
        renew_date = today + relativedelta(days=7)  # Renew 7 days before expiry
        
        subscriptions_to_renew = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', renew_date),
            ('date_end', '!=', False),
            ('plan_id.auto_renew', '=', True)
        ])
        
        for subscription in subscriptions_to_renew:
            subscription.action_renew()
    
    @api.model
    def _cron_send_billing_reminders(self):
        """Send billing reminders for upcoming billing"""
        today = fields.Date.today()
        reminder_date = today + relativedelta(days=3)  # Remind 3 days before billing
        
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '=', reminder_date)
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_billing_reminder', 
                               raise_if_not_found=False)
        if template:
            for subscription in subscriptions:
                template.send_mail(subscription.id, force_send=False)
    
    @api.model
    def _cron_update_usage_metrics(self):
        """Update usage metrics for all active subscriptions"""
        # This method can be extended to calculate usage from various sources
        # For now, it's a placeholder for custom usage calculation logic
        active_subscriptions = self.search([('state', '=', 'active')])
        
        for subscription in active_subscriptions:
            # Custom logic to calculate usage
            # Example: Count API calls, emails sent, storage used, etc.
            pass
    
    def _get_portal_return_action(self):
        """Return the action to display when returning from payment"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/subscriptions/%s' % self.id,
            'target': 'self',
        }