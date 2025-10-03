# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
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
    
    # Company
    company_id = fields.Many2one(
        'res.company', 
        'Company',
        required=True,
        default=lambda self: self.env.company,
        help="The Odoo company that manages this subscription"
    )
    
    # Plan and Pricing
    plan_id = fields.Many2one('subscription.plan', 'Subscription Plan',
                              required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  related='plan_id.currency_id', store=True)
    
    # Lifetime Support (NEW)
    is_lifetime = fields.Boolean(
        string='Is Lifetime',
        related='plan_id.is_lifetime',
        store=True,
        help='This is a lifetime subscription that never expires'
    )
    
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
    
    # Payment Retry & Dunning
    payment_retry_count = fields.Integer('Payment Retry Count', default=0, tracking=True)
    last_payment_error = fields.Text('Last Payment Error')
    payment_retry_date = fields.Date('Next Payment Retry')
    dunning_level = fields.Selection([
        ('none', 'No Dunning'),
        ('soft', 'Soft Dunning'),
        ('hard', 'Hard Dunning'),
        ('final', 'Final Notice'),
    ], default='none', string='Dunning Level', tracking=True)
    failed_invoice_ids = fields.One2many('account.move', 'subscription_id',
                                         domain=[('payment_state', '=', 'not_paid')],
                                         string='Failed Invoices')
    failed_invoice_count = fields.Integer('Failed Invoices', compute='_compute_failed_invoice_count')
    
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
    
    # Coupon
    coupon_id = fields.Many2one('subscription.coupon', 'Applied Coupon')
    original_price = fields.Float('Original Price')
    
    # ==========================================
    # GRACE PERIOD & LIFECYCLE FIELDS
    # ==========================================
    
    # Period Overrides (can be customized per subscription)
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        compute='_compute_lifecycle_periods',
        store=True,
        help='Days after expiry before suspension. Inherits from plan or system default.'
    )
    
    suspend_period_days = fields.Integer(
        string='Suspension Period (Days)',
        compute='_compute_lifecycle_periods',
        store=True,
        help='Days in suspension before termination. Inherits from plan or system default.'
    )
    
    terminate_period_days = fields.Integer(
        string='Termination Period (Days)',
        compute='_compute_lifecycle_periods',
        store=True,
        help='Total days before termination. Inherits from plan or system default.'
    )
    
    # Computed Dates
    paid_through_date = fields.Date(
        string='Paid Through Date',
        compute='_compute_paid_through_date',
        store=True,
        help='Last date subscription is paid for (same as date_end for active subscriptions)'
    )
    
    grace_period_end_date = fields.Date(
        string='Grace Period End Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Date when grace period ends and suspension begins'
    )
    
    suspend_end_date = fields.Date(
        string='Suspension End Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Date when suspension ends and termination occurs'
    )
    
    terminate_date = fields.Date(
        string='Termination Date',
        compute='_compute_lifecycle_dates',
        store=True,
        help='Final termination date'
    )
    
    # Status Flags
    is_in_grace_period = fields.Boolean(
        string='In Grace Period',
        compute='_compute_lifecycle_status',
        store=True,
        help='Subscription is past expiry but within grace period'
    )
    
    is_pending_suspension = fields.Boolean(
        string='Pending Suspension',
        compute='_compute_lifecycle_status',
        store=True,
        help='Grace period has ended, suspension is pending'
    )
    
    is_pending_termination = fields.Boolean(
        string='Pending Termination',
        compute='_compute_lifecycle_status',
        store=True,
        help='Suspension period has ended, termination is pending'
    )
    
    lifecycle_stage = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Lifecycle Stage',
       compute='_compute_lifecycle_status',
       store=True,
       help='Current stage in subscription lifecycle')
    
    days_in_grace = fields.Integer(
        string='Days in Grace',
        compute='_compute_lifecycle_status',
        help='Number of days currently in grace period'
    )
    
    days_until_suspension = fields.Integer(
        string='Days Until Suspension',
        compute='_compute_lifecycle_status',
        help='Days remaining before suspension'
    )
    
    days_until_termination = fields.Integer(
        string='Days Until Termination',
        compute='_compute_lifecycle_status',
        help='Days remaining before termination'
    )
    
    # Tracking
    grace_period_start_date = fields.Date(
        string='Grace Period Started',
        readonly=True,
        tracking=True,
        help='Date when subscription entered grace period'
    )
    
    actual_suspend_date = fields.Date(
        string='Actually Suspended On',
        readonly=True,
        tracking=True,
        help='Date when subscription was actually suspended'
    )
    
    actual_terminate_date = fields.Date(
        string='Actually Terminated On',
        readonly=True,
        tracking=True,
        help='Date when subscription was actually terminated'
    )
    
    # Email Tracking
    last_grace_email_date = fields.Date(
        string='Last Grace Email',
        help='Last date grace period email was sent'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_active_subscription',
         'CHECK(1=1)',
         'Customer already has an active subscription for this plan!')
    ]
    
    @api.constrains('partner_id', 'plan_id', 'state')
    def _check_duplicate_active_subscription(self):
        """Prevent duplicate active subscriptions for the same partner and plan"""
        for subscription in self:
            if subscription.state in ('active', 'trial'):
                duplicate = self.search([
                    ('partner_id', '=', subscription.partner_id.id),
                    ('plan_id', '=', subscription.plan_id.id),
                    ('state', 'in', ('active', 'trial')),
                    ('id', '!=', subscription.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(_(
                        'Customer %s already has an active subscription (%s) for plan %s. '
                        'Please cancel or modify the existing subscription instead.'
                    ) % (subscription.partner_id.name, duplicate.name, subscription.plan_id.name))
    
    @api.model
    def create(self, vals):
        """Override create to set dates based on billing type"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('subscription.subscription') or _('New')
        
        subscription = super(SubscriptionSubscription, self).create(vals)
        
        # Set subscription dates after creation
        subscription._set_subscription_dates()
        
        return subscription
    
    def write(self, vals):
        """Override write to update dates when plan changes"""
        result = super(SubscriptionSubscription, self).write(vals)
        
        # If plan changed, recalculate dates
        if 'plan_id' in vals or 'date_start' in vals:
            for subscription in self:
                if subscription.plan_id and subscription.date_start:
                    # Only update end date if calendar-based and not lifetime
                    if not subscription.is_lifetime and subscription.plan_id.billing_type == 'calendar' and not vals.get('date_end'):
                        subscription.date_end = subscription.plan_id.get_subscription_end_date(
                            subscription.date_start
                        )
        
        return result
    
    @api.depends('plan_id.trial_period', 'date_start')
    def _compute_trial_end_date(self):
        for subscription in self:
            if subscription.plan_id.trial_period > 0 and subscription.date_start:
                subscription.trial_end_date = subscription.date_start + relativedelta(
                    days=subscription.plan_id.trial_period
                )
            else:
                subscription.trial_end_date = False
    
    # UPDATED: Handle lifetime subscriptions
    @api.depends('date_start', 'plan_id', 'last_invoice_date', 'state', 'plan_id.billing_type', 'is_lifetime')
    def _compute_next_billing_date(self):
        for subscription in self:
            # NEW: Lifetime subscriptions don't have next billing
            if subscription.is_lifetime:
                subscription.next_billing_date = False
                continue
            
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
    
    @api.depends('failed_invoice_ids')
    def _compute_failed_invoice_count(self):
        for subscription in self:
            subscription.failed_invoice_count = len(subscription.failed_invoice_ids)
    
    # ==========================================
    # LIFECYCLE COMPUTE METHODS
    # ==========================================
    
    @api.depends('date_end', 'last_invoice_date')
    def _compute_paid_through_date(self):
        """Calculate the date subscription is paid through"""
        for subscription in self:
            if subscription.state in ('active', 'trial'):
                subscription.paid_through_date = subscription.date_end
            else:
                subscription.paid_through_date = False
    
    @api.depends('plan_id', 'plan_id.grace_period_days', 'plan_id.suspend_period_days', 
                 'plan_id.terminate_period_days')
    def _compute_lifecycle_periods(self):
        """Compute lifecycle periods from plan or system defaults"""
        # Get system defaults
        sys_grace = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.grace_period_days', '30'))
        sys_suspend = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.suspend_period_days', '60'))
        sys_terminate = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.terminate_period_days', '90'))
        
        for subscription in self:
            # Use plan-specific periods if set (> 0), otherwise use system defaults
            if subscription.plan_id:
                subscription.grace_period_days = (
                    subscription.plan_id.grace_period_days 
                    if subscription.plan_id.grace_period_days > 0 
                    else sys_grace
                )
                subscription.suspend_period_days = (
                    subscription.plan_id.suspend_period_days 
                    if subscription.plan_id.suspend_period_days > 0 
                    else sys_suspend
                )
                subscription.terminate_period_days = (
                    subscription.plan_id.terminate_period_days 
                    if subscription.plan_id.terminate_period_days > 0 
                    else sys_terminate
                )
            else:
                # No plan, use system defaults
                subscription.grace_period_days = sys_grace
                subscription.suspend_period_days = sys_suspend
                subscription.terminate_period_days = sys_terminate
    
    @api.depends('paid_through_date', 'grace_period_days', 'suspend_period_days', 
                 'terminate_period_days', 'state')
    def _compute_lifecycle_dates(self):
        """Calculate grace, suspend, and terminate dates"""
        for subscription in self:
            if subscription.paid_through_date:
                base_date = subscription.paid_through_date
                
                # Grace period end date
                subscription.grace_period_end_date = base_date + timedelta(
                    days=subscription.grace_period_days
                )
                
                # Suspend end date (grace + suspend period)
                subscription.suspend_end_date = base_date + timedelta(
                    days=subscription.grace_period_days + subscription.suspend_period_days
                )
                
                # Terminate date (total period)
                subscription.terminate_date = base_date + timedelta(
                    days=subscription.terminate_period_days
                )
            else:
                subscription.grace_period_end_date = False
                subscription.suspend_end_date = False
                subscription.terminate_date = False
    
    @api.depends('paid_through_date', 'grace_period_end_date', 'suspend_end_date',
                 'terminate_date', 'state')
    def _compute_lifecycle_status(self):
        """Determine current lifecycle status"""
        today = fields.Date.today()
        
        for subscription in self:
            if not subscription.paid_through_date:
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.lifecycle_stage = 'active' if subscription.state == 'active' else False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0
                continue
            
            paid_through = subscription.paid_through_date
            grace_end = subscription.grace_period_end_date
            suspend_end = subscription.suspend_end_date
            terminate = subscription.terminate_date
            
            # Determine lifecycle stage
            if subscription.state == 'active':
                if today <= paid_through:
                    # Still within paid period
                    subscription.lifecycle_stage = 'active'
                    subscription.is_in_grace_period = False
                    subscription.is_pending_suspension = False
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = 0
                    subscription.days_until_suspension = (grace_end - today).days if grace_end else 0
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                elif today <= grace_end:
                    # In grace period
                    subscription.lifecycle_stage = 'grace'
                    subscription.is_in_grace_period = True
                    subscription.is_pending_suspension = False
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = (today - paid_through).days
                    subscription.days_until_suspension = (grace_end - today).days
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                else:
                    # Past grace period, should be suspended
                    subscription.lifecycle_stage = 'grace'
                    subscription.is_in_grace_period = False
                    subscription.is_pending_suspension = True
                    subscription.is_pending_termination = False
                    subscription.days_in_grace = subscription.grace_period_days
                    subscription.days_until_suspension = 0
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
            elif subscription.state == 'suspended':
                subscription.lifecycle_stage = 'suspended'
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                
                if suspend_end and today > suspend_end:
                    subscription.is_pending_termination = True
                    subscription.days_until_termination = 0
                else:
                    subscription.is_pending_termination = False
                    subscription.days_until_termination = (terminate - today).days if terminate else 0
                    
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                
            elif subscription.state in ('cancelled', 'expired'):
                subscription.lifecycle_stage = 'terminated'
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0
                
            else:
                # Draft, trial, etc.
                subscription.lifecycle_stage = False
                subscription.is_in_grace_period = False
                subscription.is_pending_suspension = False
                subscription.is_pending_termination = False
                subscription.days_in_grace = 0
                subscription.days_until_suspension = 0
                subscription.days_until_termination = 0
    
    @api.onchange('plan_id', 'date_start')
    def _onchange_plan_set_end_date(self):
        """Automatically set end date when plan or start date changes"""
        if self.plan_id and self.date_start and not self.date_end:
            # Set end date based on billing type
            self.date_end = self.plan_id.get_subscription_end_date(self.date_start)
    
    # UPDATED: Handle lifetime subscriptions
    def _set_subscription_dates(self):
        """Set subscription dates based on plan billing type"""
        self.ensure_one()
        
        if not self.date_start:
            self.date_start = fields.Date.today()
        
        # NEW: Lifetime subscriptions never expire
        if self.is_lifetime:
            self.date_end = False
            self.next_billing_date = False
            return
        
        # Set end date if not already set
        if not self.date_end and self.plan_id:
            self.date_end = self.plan_id.get_subscription_end_date(self.date_start)
        
        # Set next billing date
        if self.state in ('active', 'trial'):
            if self.last_invoice_date:
                base_date = self.last_invoice_date
            else:
                base_date = self.trial_end_date or self.date_start
            
            if base_date:
                self.next_billing_date = self.plan_id.get_next_billing_date(base_date)
    
    def get_renewal_date(self):
        """Get the date when renewal should be offered"""
        self.ensure_one()
        
        # NEW: Lifetime subscriptions don't need renewal
        if self.is_lifetime:
            return False
        
        if not self.date_end:
            return False
        
        # For calendar-based subscriptions, offer renewal closer to period end
        if self.plan_id.billing_type == 'calendar':
            if self.plan_id.billing_period == 'yearly':
                return self.date_end - relativedelta(months=2)
            elif self.plan_id.billing_period == 'quarterly':
                return self.date_end - relativedelta(weeks=2)
            else:
                return self.date_end - relativedelta(weeks=1)
        else:
            # Anniversary-based: offer renewal 1 week before
            return self.date_end - relativedelta(days=7)
    
    def should_offer_renewal(self):
        """Check if renewal should be offered now"""
        self.ensure_one()
        
        # NEW: Lifetime subscriptions don't need renewal
        if self.is_lifetime:
            return False
        
        if self.state not in ('active', 'trial'):
            return False
        
        if not self.date_end:
            return False
        
        renewal_date = self.get_renewal_date()
        if not renewal_date:
            return False
        
        return fields.Date.today() >= renewal_date
    
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
        # Reset dunning when reactivated
        self.dunning_level = 'none'
        self.payment_retry_count = 0
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
        # NEW: Only set end date for non-lifetime subscriptions
        if not self.is_lifetime:
            self.date_end = fields.Date.today()
    
    def action_renew(self):
        """Renew subscription - handle calendar vs anniversary billing"""
        self.ensure_one()
        
        # NEW: Lifetime subscriptions cannot be renewed
        if self.is_lifetime:
            raise UserError(_('Lifetime subscriptions do not require renewal'))
        
        if self.plan_id.auto_renew:
            # Calculate new end date based on billing type
            if self.plan_id.billing_type == 'calendar':
                current_end = self.date_end or self.date_start
                
                if self.plan_id.billing_period == 'yearly':
                    self.date_end = date(current_end.year + 1, 12, 31)
                elif self.plan_id.billing_period == 'quarterly':
                    next_quarter_start = current_end + relativedelta(days=1)
                    self.date_end = self.plan_id._get_calendar_based_billing_date(next_quarter_start)
                elif self.plan_id.billing_period == 'monthly':
                    next_month_start = current_end + relativedelta(days=1)
                    self.date_end = self.plan_id._get_calendar_based_billing_date(next_month_start)
                else:
                    self.date_end = self.plan_id.get_next_billing_date(current_end)
            else:
                # Anniversary-based
                self.date_end = self.plan_id.get_next_billing_date(
                    self.date_end or self.date_start
                )
            
            if self.state == 'expired':
                self.state = 'active'
            
            self.message_post(
                body=f"Subscription renewed until {self.date_end}",
                message_type='notification'
            )
    
    def action_reactivate(self):
        """Reactivate a suspended, cancelled or expired subscription"""
        self.ensure_one()
        
        if self.state not in ('suspended', 'cancelled', 'expired'):
            raise UserError(_('Only suspended, cancelled or expired subscriptions can be reactivated.'))
        
        # For suspended subscriptions, simply reactivate
        if self.state == 'suspended':
            self.write({
                'state': 'active',
                'payment_retry_count': 0,
                'dunning_level': 'none',
                'last_payment_error': False,
                'payment_retry_date': False,
                'actual_suspend_date': False,
            })
            
            self.message_post(
                body=_('Subscription reactivated from suspended state'),
                message_type='notification'
            )
        
        # For cancelled/expired subscriptions, reset dates (unless lifetime)
        else:
            today = fields.Date.today()
            self.date_start = today
            
            # NEW: Lifetime subscriptions never have end date
            if not self.is_lifetime:
                self.date_end = self.plan_id.get_subscription_end_date(today)
            else:
                self.date_end = False
            
            self.write({
                'state': 'active',
                'payment_retry_count': 0,
                'dunning_level': 'none',
                'last_payment_error': False,
                'payment_retry_date': False,
                'grace_period_start_date': False,
                'actual_suspend_date': False,
                'actual_terminate_date': False,
            })
            
            # Create reactivation invoice
            self._create_initial_invoice()
            
            self.message_post(
                body=_('Subscription reactivated with new billing period'),
                message_type='notification'
            )
        
        # Send reactivation email
        template = self.env.ref(
            'subscription_management.email_template_subscription_reactivated',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Subscription reactivated successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    # ==========================================
    # GRACE PERIOD BUSINESS METHODS
    # ==========================================
    
    def action_enter_grace_period(self):
        """Manually enter grace period (usually automatic)"""
        self.ensure_one()
        if self.state == 'active' and not self.is_in_grace_period:
            self.grace_period_start_date = fields.Date.today()
            self._send_grace_period_email()
            
            self.message_post(
                body=f"Entered grace period. Grace ends on {self.grace_period_end_date}",
                message_type='notification'
            )
    
    def action_suspend_from_grace(self):
        """Suspend subscription after grace period ends"""
        self.ensure_one()
        
        if self.state == 'active':
            self.actual_suspend_date = fields.Date.today()
            self.action_suspend()
            
            # Send suspension email
            send_email = self.env['ir.config_parameter'].sudo().get_param(
                'subscription.suspend_send_email', 'True'
            )
            if send_email == 'True':
                self._send_suspension_email()
            
            self.message_post(
                body=f"Suspended after grace period ended. Suspension ends on {self.suspend_end_date}",
                message_type='notification'
            )
    
    def action_terminate_from_suspension(self):
        """Terminate subscription after suspension period ends"""
        self.ensure_one()
        
        if self.state == 'suspended':
            self.actual_terminate_date = fields.Date.today()
            self.state = 'expired'
            
            # Send termination email
            self._send_termination_email()
            
            self.message_post(
                body=f"Subscription terminated after suspension period ended.",
                message_type='notification'
            )
    
    def _send_grace_period_email(self):
        """Send grace period notification email"""
        template = self.env.ref(
            'subscription_management.email_template_grace_period',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
            self.last_grace_email_date = fields.Date.today()
    
    def _send_suspension_email(self):
        """Send suspension notification email"""
        template = self.env.ref(
            'subscription_management.email_template_suspended_from_grace',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _send_termination_email(self):
        """Send termination notification email"""
        template = self.env.ref(
            'subscription_management.email_template_terminated',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
    
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
    
    def action_view_failed_invoices(self):
        """Action to view failed invoices"""
        return {
            'name': _('Failed Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.failed_invoice_ids.ids)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_retry_payment(self):
        """Manually retry payment for failed invoices"""
        self.ensure_one()
        
        for invoice in self.failed_invoice_ids:
            if invoice.state == 'posted' and invoice.payment_state == 'not_paid':
                _logger.info(f"Manual payment retry requested for invoice {invoice.name}")
                
                # Create activity for follow-up
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f'Follow up on payment for {invoice.name}',
                    user_id=self.env.user.id
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Retry'),
                'message': _('Payment retry has been initiated. Please follow up manually.'),
                'type': 'info',
                'sticky': False,
            }
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
            'company_id': self.company_id.id,
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
    
    # ==========================================
    # Payment Failure & Dunning Methods
    # ==========================================
    
    def _process_failed_payment(self, invoice):
        """Handle failed payment with retry logic and dunning"""
        self.ensure_one()
        
        max_retries = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.settings.max_billing_retries', '3'
        ))
        
        self.payment_retry_count += 1
        self.last_payment_error = f"Payment failed for invoice {invoice.name} on {fields.Date.today()}"
        
        _logger.warning(f"Payment failed for subscription {self.name}. Retry count: {self.payment_retry_count}")
        
        # Determine dunning level and actions
        if self.payment_retry_count >= max_retries:
            self.dunning_level = 'final'
            self.action_suspend()
            self._send_dunning_email('final_notice')
            self.message_post(
                body=f"Subscription suspended due to {max_retries} failed payment attempts.",
                message_type='notification'
            )
            
        elif self.payment_retry_count >= 2:
            self.dunning_level = 'hard'
            self._send_dunning_email('hard_dunning')
            
        else:
            self.dunning_level = 'soft'
            self._send_dunning_email('soft_dunning')
        
        # Schedule next retry
        retry_days = self.payment_retry_count * 3
        self.payment_retry_date = fields.Date.today() + timedelta(days=retry_days)
        
        # Create activity for sales team
        if self.payment_retry_count >= 2:
            self.activity_schedule(
                'mail.mail_activity_data_call',
                summary=f'Payment Failed - Contact Customer ({self.payment_retry_count} attempts)',
                note=f'Customer {self.partner_id.name} has failed payment {self.payment_retry_count} times. Please contact them.',
                user_id=self.env.ref('base.user_admin').id
            )
    
    def _process_successful_payment(self, invoice):
        """Reset dunning state when payment succeeds"""
        self.ensure_one()
        
        if self.dunning_level != 'none' or self.payment_retry_count > 0:
            _logger.info(f"Payment successful for subscription {self.name}. Resetting dunning state.")
            
            self.write({
                'payment_retry_count': 0,
                'dunning_level': 'none',
                'last_payment_error': False,
                'payment_retry_date': False,
            })
            
            # Reactivate if suspended
            if self.state == 'suspended':
                self.action_activate()
            
            self.message_post(
                body=f"Payment successful for invoice {invoice.name}. Dunning cleared.",
                message_type='notification'
            )
    
    def _send_dunning_email(self, email_type):
        """Send dunning notification email"""
        template_map = {
            'soft_dunning': 'subscription_management.email_template_payment_failed_soft',
            'hard_dunning': 'subscription_management.email_template_payment_failed_hard',
            'final_notice': 'subscription_management.email_template_payment_failed_final',
        }
        
        template_ref = template_map.get(email_type)
        if not template_ref:
            return
        
        template = self.env.ref(template_ref, raise_if_not_found=False)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                _logger.info(f"Sent {email_type} email for subscription {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send {email_type} email for subscription {self.name}: {e}")
    
    # ==========================================
    # CRON METHODS
    # ==========================================
    
    @api.model
    def _cron_process_grace_periods(self):
        """Process subscriptions entering or in grace period"""
        today = fields.Date.today()
        
        # Find subscriptions that should enter grace period
        entering_grace = self.search([
            ('state', '=', 'active'),
            ('paid_through_date', '<', today),
            ('grace_period_start_date', '=', False),
            ('grace_period_end_date', '>=', today),
        ])
        
        for subscription in entering_grace:
            subscription.action_enter_grace_period()
        
        _logger.info(f"Processed {len(entering_grace)} subscriptions entering grace period")
        
        # Send reminders for subscriptions in grace period
        send_reminders = self.env['ir.config_parameter'].sudo().get_param(
            'subscription.grace_send_email', 'True'
        )
        if send_reminders == 'True':
            self._send_grace_reminders()
    
    @api.model
    def _cron_process_suspensions(self):
        """Process subscriptions that should be suspended"""
        today = fields.Date.today()
        
        # Find subscriptions past grace period
        to_suspend = self.search([
            ('state', '=', 'active'),
            ('grace_period_end_date', '<', today),
            ('actual_suspend_date', '=', False),
        ])
        
        for subscription in to_suspend:
            subscription.action_suspend_from_grace()
        
        _logger.info(f"Suspended {len(to_suspend)} subscriptions after grace period")
    
    @api.model
    def _cron_process_terminations(self):
        """Process subscriptions that should be terminated"""
        today = fields.Date.today()
        
        # Find suspended subscriptions past suspension period
        to_terminate = self.search([
            ('state', '=', 'suspended'),
            ('suspend_end_date', '<', today),
            ('actual_terminate_date', '=', False),
        ])
        
        for subscription in to_terminate:
            subscription.action_terminate_from_suspension()
        
        _logger.info(f"Terminated {len(to_terminate)} subscriptions after suspension period")
    
    @api.model
    def _send_grace_reminders(self):
        """Send reminder emails to subscriptions in grace period"""
        today = fields.Date.today()
        frequency = self.env['ir.config_parameter'].sudo().get_param(
            'subscription.grace_email_frequency', 'weekly'
        )
        
        # Determine which subscriptions need reminders
        domain = [
            ('is_in_grace_period', '=', True),
            ('state', '=', 'active'),
        ]
        
        if frequency == 'once':
            domain.append(('last_grace_email_date', '=', False))
        elif frequency == 'weekly':
            domain.append('|')
            domain.append(('last_grace_email_date', '=', False))
            domain.append(('last_grace_email_date', '<=', today - timedelta(days=7)))
        elif frequency == 'daily':
            domain.append('|')
            domain.append(('last_grace_email_date', '=', False))
            domain.append(('last_grace_email_date', '<', today))
        
        subscriptions = self.search(domain)
        
        template = self.env.ref(
            'subscription_management.email_template_grace_reminder',
            raise_if_not_found=False
        )
        
        if template:
            for subscription in subscriptions:
                template.send_mail(subscription.id, force_send=False)
                subscription.last_grace_email_date = today
        
        _logger.info(f"Sent grace reminders to {len(subscriptions)} subscriptions")
    
    @api.model
    def _cron_retry_failed_payments(self):
        """Cron job to retry failed payments"""
        today = fields.Date.today()
        
        subscriptions = self.search([
            ('payment_retry_date', '<=', today),
            ('payment_retry_count', '>', 0),
            ('payment_retry_count', '<', 3),
            ('state', 'in', ['active', 'trial'])
        ])
        
        _logger.info(f"Retrying payments for {len(subscriptions)} subscriptions")
        
        for subscription in subscriptions:
            try:
                failed_invoice = subscription.failed_invoice_ids[:1]
                if failed_invoice:
                    _logger.info(f"Retrying payment for subscription {subscription.name}, invoice {failed_invoice.name}")
                    
            except Exception as e:
                _logger.error(f"Error retrying payment for subscription {subscription.name}: {e}")
    
    @api.model
    def _cron_check_renewals(self):
        """Check for subscriptions that need renewal and send reminders"""
        today = fields.Date.today()
        
        subscriptions = self.search([
            ('state', 'in', ['active', 'trial']),
            ('date_end', '!=', False),
            ('is_lifetime', '=', False),  # NEW: Skip lifetime subscriptions
        ])
        
        renewal_count = 0
        reminder_count = 0
        
        for subscription in subscriptions:
            try:
                if subscription.should_offer_renewal():
                    last_message = subscription.message_ids.filtered(
                        lambda m: 'Renewal reminder sent' in (m.body or '')
                    )[:1]
                    
                    send_reminder = True
                    if last_message:
                        days_since_last = (today - last_message.date.date()).days
                        if days_since_last < 7:
                            send_reminder = False
                    
                    if send_reminder:
                        template = self.env.ref(
                            'subscription_management.email_template_subscription_renewal_reminder',
                            raise_if_not_found=False
                        )
                        if template:
                            template.send_mail(subscription.id, force_send=False)
                            subscription.message_post(
                                body=f"Renewal reminder sent for subscription ending on {subscription.date_end}",
                                message_type='notification'
                            )
                            reminder_count += 1
                        
                        subscription.activity_schedule(
                            'mail.mail_activity_data_call',
                            summary=f'Follow up on renewal for {subscription.partner_id.name}',
                            note=f'Subscription {subscription.name} is due for renewal on {subscription.date_end}. Contact customer to confirm renewal.',
                            date_deadline=subscription.date_end - relativedelta(days=3),
                            user_id=self.env.ref('base.user_admin').id
                        )
                        renewal_count += 1
                        
            except Exception as e:
                _logger.error(f"Error checking renewal for subscription {subscription.name}: {e}")
        
        _logger.info(f"Renewal check completed: {renewal_count} subscriptions due for renewal, {reminder_count} reminders sent")
    
    @api.model
    def _cron_process_billing(self):
        """Process billing for subscriptions due today"""
        today = fields.Date.today()
        subscriptions = self.search([
            ('state', 'in', ['active', 'trial']),
            ('next_billing_date', '<=', today),
            ('is_lifetime', '=', False),  # NEW: Skip lifetime subscriptions
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
            try:
                template.send_mail(invoice.id, force_send=True)
            except Exception as e:
                _logger.error(f"Failed to send invoice email for {invoice.name}: {e}")
    
    @api.model
    def _cron_check_trial_expiry(self):
        """Check for trial subscriptions that are expiring"""
        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        
        trials_expiring = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '=', tomorrow)
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_trial_expiry', 
                               raise_if_not_found=False)
        if template:
            for subscription in trials_expiring:
                try:
                    template.send_mail(subscription.id, force_send=False)
                except Exception as e:
                    _logger.error(f"Failed to send trial expiry email for {subscription.name}: {e}")
        
        trials_expired = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '<=', today)
        ])
        
        for subscription in trials_expired:
            subscription.action_activate()
    
    # UPDATED: Skip lifetime subscriptions
    @api.model
    def _cron_check_expiry(self):
        """Check for subscriptions that have expired - skip lifetime"""
        today = fields.Date.today()
        
        expired_subscriptions = self.search([
            ('state', 'in', ['active', 'suspended']),
            ('date_end', '<=', today),
            ('date_end', '!=', False),
            ('is_lifetime', '=', False),  # NEW: Skip lifetime subscriptions
        ])
        
        for subscription in expired_subscriptions:
            subscription.state = 'expired'
    
    @api.model
    def _cron_auto_renew(self):
        """Process auto-renewals for expiring subscriptions"""
        today = fields.Date.today()
        renew_date = today + relativedelta(days=7)
        
        subscriptions_to_renew = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', renew_date),
            ('date_end', '!=', False),
            ('plan_id.auto_renew', '=', True),
            ('is_lifetime', '=', False),  # NEW: Skip lifetime subscriptions
        ])
        
        for subscription in subscriptions_to_renew:
            subscription.action_renew()
    
    @api.model
    def _cron_send_billing_reminders(self):
        """Send billing reminders for upcoming billing"""
        today = fields.Date.today()
        reminder_date = today + relativedelta(days=3)
        
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '=', reminder_date),
            ('is_lifetime', '=', False),  # NEW: Skip lifetime subscriptions
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_billing_reminder', 
                               raise_if_not_found=False)
        if template:
            for subscription in subscriptions:
                try:
                    template.send_mail(subscription.id, force_send=False)
                except Exception as e:
                    _logger.error(f"Failed to send billing reminder for {subscription.name}: {e}")
    
    @api.model
    def _cron_update_usage_metrics(self):
        """Update usage metrics for all active subscriptions"""
        active_subscriptions = self.search([('state', '=', 'active')])
        
        for subscription in active_subscriptions:
            pass
    
    def _get_portal_return_action(self):
        """Return the action to display when returning from payment"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/subscriptions/%s' % self.id,
            'target': 'self',
        }