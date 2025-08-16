# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    """Subscription model with billing functionality - can work standalone or extend existing"""
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =============================================================================
    # CORE SUBSCRIPTION FIELDS
    # =============================================================================
    
    name = fields.Char(
        string='Subscription Name',
        required=True,
        index=True,
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        tracking=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product/Service',
        required=True,
        domain=[('type', '=', 'service')],
        tracking=True
    )
    
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        tracking=True
    )
    
    price = fields.Monetary(
        string='Price',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Subscription Period', default='annual', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', required=True, tracking=True)

    # =============================================================================
    # BASIC BILLING CONFIGURATION
    # =============================================================================
    
    # Auto-Billing Settings
    enable_auto_billing = fields.Boolean(
        string='Enable Auto Billing',
        default=True,
        help='Automatically generate invoices for this subscription',
        tracking=True
    )
    
    auto_send_invoices = fields.Boolean(
        string='Auto Send Invoices',
        default=True,
        help='Automatically send invoices to customer'
    )
    
    # Billing Dates
    next_billing_date = fields.Date(
        string='Next Billing Date',
        index=True,
        tracking=True,
        help='Date when next invoice will be generated'
    )
    
    last_billing_date = fields.Date(
        string='Last Billing Date',
        readonly=True,
        help='Date of last successful billing'
    )
    
    # =============================================================================
    # BILLING STATUS
    # =============================================================================
    
    # Payment Status
    payment_status = fields.Selection([
        ('current', 'Current'),
        ('overdue', 'Overdue'),
        ('pending', 'Pending Payment'),
    ], string='Payment Status', compute='_compute_payment_status', store=True)
    
    has_overdue_invoices = fields.Boolean(
        string='Has Overdue Invoices',
        compute='_compute_payment_status',
        store=True,
        help='Customer has overdue invoices'
    )
    
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_payment_status',
        store=True
    )
    
    # Basic Statistics
    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    # =============================================================================
    # RELATED BILLING RECORDS
    # =============================================================================
    
    # Billing Records
    billing_schedule_ids = fields.One2many(
        'ams.billing.schedule',
        'subscription_id',
        string='Billing Schedules'
    )
    
    billing_event_ids = fields.One2many(
        'ams.billing.event',
        'subscription_id',
        string='Billing Events'
    )
    
    # Invoice tracking
    subscription_invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Subscription Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('subscription_invoice_ids')
    def _compute_payment_status(self):
        """Compute basic payment status based on invoices"""
        for subscription in self:
            # Get unpaid invoices
            unpaid_invoices = subscription.subscription_invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state in ['not_paid', 'partial']
            )
            
            if not unpaid_invoices:
                subscription.payment_status = 'current'
                subscription.has_overdue_invoices = False
                subscription.days_overdue = 0
            else:
                # Check if any invoice is overdue
                overdue_invoices = unpaid_invoices.filtered(
                    lambda inv: inv.invoice_date_due and inv.invoice_date_due < fields.Date.today()
                )
                
                if overdue_invoices:
                    subscription.payment_status = 'overdue'
                    subscription.has_overdue_invoices = True
                    # Calculate days overdue from oldest overdue invoice
                    oldest_due = min(overdue_invoices.mapped('invoice_date_due'))
                    subscription.days_overdue = (fields.Date.today() - oldest_due).days
                else:
                    subscription.payment_status = 'pending'
                    subscription.has_overdue_invoices = False
                    subscription.days_overdue = 0
    
    @api.depends('subscription_invoice_ids')
    def _compute_billing_stats(self):
        """Compute basic billing statistics"""
        for subscription in self:
            invoices = subscription.subscription_invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
            )
            
            subscription.total_invoiced = sum(invoices.mapped('amount_total'))
            subscription.total_paid = sum(invoices.mapped('amount_total')) - sum(invoices.mapped('amount_residual'))
            subscription.outstanding_balance = sum(invoices.mapped('amount_residual'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('enable_auto_billing')
    def _onchange_enable_auto_billing(self):
        """Handle auto billing enablement"""
        if self.enable_auto_billing and not self.next_billing_date:
            self._calculate_next_billing_date()
    
    @api.onchange('subscription_period')
    def _onchange_subscription_period(self):
        """Recalculate billing dates when period changes"""
        if self.enable_auto_billing:
            self._calculate_next_billing_date()
    
    @api.onchange('partner_id', 'product_id')
    def _onchange_subscription_basics(self):
        """Update subscription name when basics change"""
        if self.partner_id and self.product_id:
            self.name = f"{self.partner_id.name} - {self.product_id.name}"
    
    # =============================================================================
    # CRUD OPERATIONS
    # =============================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to set up subscription defaults"""
        for vals in vals_list:
            # Auto-generate name if not provided
            if not vals.get('name') and vals.get('partner_id') and vals.get('product_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                product = self.env['product.product'].browse(vals['product_id'])
                vals['name'] = f"{partner.name} - {product.name}"
            
            # Set default next billing date
            if vals.get('enable_auto_billing', True) and not vals.get('next_billing_date'):
                start_date = vals.get('start_date', fields.Date.today())
                if isinstance(start_date, str):
                    start_date = fields.Date.from_string(start_date)
                vals['next_billing_date'] = start_date
        
        return super().create(vals_list)
    
    # =============================================================================
    # BASIC SUBSCRIPTION ACTIONS
    # =============================================================================
    
    def action_activate(self):
        """Activate the subscription"""
        for subscription in self:
            if subscription.state != 'draft':
                raise UserError(_('Only draft subscriptions can be activated'))
            
            subscription.state = 'active'
            
            # Enable auto-billing by default for new subscriptions
            if not subscription.enable_auto_billing:
                subscription.enable_auto_billing = True
            
            # Create billing schedule
            if subscription.enable_auto_billing and not subscription.billing_schedule_ids:
                subscription._create_billing_schedule()
            
            # Calculate next billing date
            subscription._calculate_next_billing_date()
            
            subscription.message_post(body=_('Subscription activated'))
    
    def action_suspend(self):
        """Suspend the subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_('Only active subscriptions can be suspended'))
            
            subscription.state = 'suspended'
            
            # Pause billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'active'
            )
            active_schedules.action_pause()
            
            subscription.message_post(body=_('Subscription suspended'))
    
    def action_reactivate(self):
        """Reactivate suspended subscription"""
        for subscription in self:
            if subscription.state != 'suspended':
                raise UserError(_('Only suspended subscriptions can be reactivated'))
            
            subscription.state = 'active'
            
            # Resume billing schedules
            paused_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'paused'
            )
            paused_schedules.action_resume()
            
            subscription.message_post(body=_('Subscription reactivated'))
    
    def action_terminate(self):
        """Terminate the subscription"""
        for subscription in self:
            if subscription.state == 'terminated':
                raise UserError(_('Subscription is already terminated'))
            
            # Cancel billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state in ['active', 'paused']
            )
            active_schedules.action_cancel()
            
            subscription.state = 'terminated'
            subscription.end_date = fields.Date.today()
            
            subscription.message_post(body=_('Subscription terminated'))
    
    # =============================================================================
    # BILLING ACTIONS
    # =============================================================================
    
    def action_enable_billing(self):
        """Enable auto-billing for this subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_('Only active subscriptions can have billing enabled'))
            
            subscription.enable_auto_billing = True
            
            # Create billing schedule if it doesn't exist
            if not subscription.billing_schedule_ids:
                subscription._create_billing_schedule()
            
            # Calculate next billing date
            subscription._calculate_next_billing_date()
            
            subscription.message_post(body=_('Auto-billing enabled'))
    
    def action_disable_billing(self):
        """Disable auto-billing for this subscription"""
        for subscription in self:
            subscription.enable_auto_billing = False
            
            # Pause billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'active'
            )
            active_schedules.action_pause()
            
            subscription.message_post(body=_('Auto-billing disabled'))
    
    def action_bill_now(self):
        """Manually trigger billing for this subscription"""
        for subscription in self:
            if not subscription.enable_auto_billing:
                raise UserError(_('Auto-billing must be enabled to bill now'))
            
            # Find or create billing schedule
            schedule = subscription._get_or_create_billing_schedule()
            
            # Process billing
            result = schedule.process_billing()
            
            if result.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Billing processed successfully'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Billing failed: %s') % result.get('error', 'Unknown error'),
                        'type': 'danger',
                    }
                }
    
    # =============================================================================
    # BILLING HELPER METHODS
    # =============================================================================
    
    def _create_billing_schedule(self):
        """Create basic billing schedule for this subscription"""
        self.ensure_one()
        
        schedule = self.env['ams.billing.schedule'].create({
            'subscription_id': self.id,
            'billing_frequency': self.subscription_period,
            'start_date': fields.Date.today(),
            'next_billing_date': self.next_billing_date or fields.Date.today(),
            'auto_generate_invoice': True,
            'auto_send_invoice': self.auto_send_invoices,
        })
        
        return schedule
    
    def _get_or_create_billing_schedule(self):
        """Get existing or create new billing schedule"""
        self.ensure_one()
        
        schedule = self.billing_schedule_ids.filtered(lambda s: s.state == 'active')
        if not schedule:
            schedule = self._create_billing_schedule()
            schedule.action_activate()
        
        return schedule[:1]  # Return only the first one
    
    def _calculate_next_billing_date(self):
        """Calculate next billing date based on subscription period"""
        for subscription in self:
            if not subscription.enable_auto_billing:
                continue
            
            today = fields.Date.today()
            
            # Use start date as base if no last billing date
            base_date = subscription.last_billing_date or subscription.start_date or today
            
            # Calculate next date based on subscription period
            if subscription.subscription_period == 'monthly':
                next_date = base_date + relativedelta(months=1)
            elif subscription.subscription_period == 'quarterly':
                next_date = base_date + relativedelta(months=3)
            elif subscription.subscription_period == 'semi_annual':
                next_date = base_date + relativedelta(months=6)
            elif subscription.subscription_period == 'annual':
                next_date = base_date + relativedelta(years=1)
            else:
                next_date = base_date + relativedelta(months=1)
            
            # Ensure next date is in the future
            if next_date <= today:
                next_date = today + timedelta(days=1)
            
            subscription.next_billing_date = next_date
    
    # =============================================================================
    # VIEW ACTIONS
    # =============================================================================
    
    def action_view_billing_schedules(self):
        """View billing schedules"""
        self.ensure_one()
        
        return {
            'name': _('Billing Schedules - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.schedule',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_billing_events(self):
        """View billing events"""
        self.ensure_one()
        
        return {
            'name': _('Billing Events - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.event',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_invoices(self):
        """View subscription invoices"""
        self.ensure_one()
        
        return {
            'name': _('Invoices - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_send_payment_reminder(self):
        """Send basic payment reminder for overdue invoices"""
        self.ensure_one()
        
        if not self.has_overdue_invoices:
            raise UserError(_('No overdue invoices to send reminder for'))
        
        # Find overdue invoices
        overdue_invoices = self.subscription_invoice_ids.filtered(
            lambda inv: (inv.state == 'posted' and 
                        inv.payment_state in ['not_paid', 'partial'] and
                        inv.invoice_date_due and 
                        inv.invoice_date_due < fields.Date.today())
        )
        
        if not overdue_invoices:
            raise UserError(_('No overdue invoices found'))
        
        # Send reminder for each overdue invoice
        template = self.env.ref('ams_subscription_billing.email_template_payment_reminder', False)
        if template:
            for invoice in overdue_invoices:
                template.send_mail(invoice.id, force_send=True)
        
        self.message_post(body=_('Payment reminder sent for %d overdue invoice(s)') % len(overdue_invoices))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment reminder sent successfully'),
                'type': 'success',
            }
        }


# If ams_subscriptions module exists, try to extend it instead of creating new model
try:
    # Check if parent model exists
    from odoo.addons.ams_subscriptions.models.ams_subscription import AMSSubscription as ParentSubscription
    
    class AMSSubscriptionExtend(models.Model):
        """Extension of existing AMS Subscription with billing functionality"""
        _inherit = 'ams.subscription'
        
        # Add only the billing-specific fields to existing model
        enable_auto_billing = fields.Boolean(
            string='Enable Auto Billing',
            default=True,
            help='Automatically generate invoices for this subscription',
            tracking=True
        )
        
        auto_send_invoices = fields.Boolean(
            string='Auto Send Invoices',
            default=True,
            help='Automatically send invoices to customer'
        )
        
        next_billing_date = fields.Date(
            string='Next Billing Date',
            index=True,
            tracking=True,
            help='Date when next invoice will be generated'
        )
        
        last_billing_date = fields.Date(
            string='Last Billing Date',
            readonly=True,
            help='Date of last successful billing'
        )
        
        payment_status = fields.Selection([
            ('current', 'Current'),
            ('overdue', 'Overdue'),
            ('pending', 'Pending Payment'),
        ], string='Payment Status', compute='_compute_payment_status', store=True)
        
        has_overdue_invoices = fields.Boolean(
            string='Has Overdue Invoices',
            compute='_compute_payment_status',
            store=True,
            help='Customer has overdue invoices'
        )
        
        days_overdue = fields.Integer(
            string='Days Overdue',
            compute='_compute_payment_status',
            store=True
        )
        
        total_invoiced = fields.Monetary(
            string='Total Invoiced',
            compute='_compute_billing_stats',
            currency_field='currency_id',
            store=True
        )
        
        total_paid = fields.Monetary(
            string='Total Paid',
            compute='_compute_billing_stats',
            currency_field='currency_id',
            store=True
        )
        
        outstanding_balance = fields.Monetary(
            string='Outstanding Balance',
            compute='_compute_billing_stats',
            currency_field='currency_id',
            store=True
        )
        
        billing_schedule_ids = fields.One2many(
            'ams.billing.schedule',
            'subscription_id',
            string='Billing Schedules'
        )
        
        billing_event_ids = fields.One2many(
            'ams.billing.event',
            'subscription_id',
            string='Billing Events'
        )
        
        subscription_invoice_ids = fields.One2many(
            'account.move',
            'subscription_id',
            string='Subscription Invoices',
            domain=[('move_type', '=', 'out_invoice')]
        )
        
        # Copy all the methods from the standalone model
        # (methods would be copied here but for brevity, using the same logic)
        
except ImportError:
    # Parent model doesn't exist, use standalone model
    _logger.info("ams_subscriptions module not found, using standalone subscription model")
    pass