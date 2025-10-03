# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Plan'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Plan Name', required=True, tracking=True)
    code = fields.Char('Plan Code', required=True, tracking=True)
    description = fields.Html('Description')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # Pricing
    price = fields.Float('Price', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Lifetime Membership Support (NEW)
    is_lifetime = fields.Boolean(
        string='Lifetime Membership',
        default=False,
        tracking=True,
        help='One-time payment membership that never expires. '
             'Members pay once and have access forever.'
    )
    
    # Billing Configuration
    billing_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),  # NEW
    ], string='Billing Period', required=True, default='monthly', tracking=True)
    
    billing_interval = fields.Integer('Billing Interval', default=1, 
                                      help='Repeat every X periods')
    
    # Billing Type
    billing_type = fields.Selection([
        ('anniversary', 'Anniversary-based'),
        ('calendar', 'Calendar-based'),
    ], string='Billing Type', default='anniversary', required=True, tracking=True,
       help='Anniversary: Billing cycle is X period from purchase date.\n'
            'Calendar: Billing cycle aligns with calendar periods (end of month/quarter/year).')
    
    # Trial Configuration
    trial_period = fields.Integer('Trial Period (days)', default=0)
    trial_price = fields.Float('Trial Price', default=0.0)
    
    # Plan Limits
    user_limit = fields.Integer('User Limit', default=0, 
                                help='0 = unlimited users')
    storage_limit = fields.Float('Storage Limit (GB)', default=0.0,
                                 help='0.0 = unlimited storage')
    
    # Usage-based billing
    usage_based = fields.Boolean('Usage-based Billing')
    usage_unit = fields.Char('Usage Unit', help='e.g., API calls, emails sent')
    usage_price = fields.Float('Price per Usage Unit')
    included_usage = fields.Float('Included Usage', 
                                  help='Usage included in base price')
    
    # Product Configuration
    product_template_id = fields.Many2one('product.template', 'Product Template',
                                          domain=[('type', '=', 'service')])
    
    # Relations
    subscription_ids = fields.One2many('subscription.subscription', 'plan_id', 
                                       'Subscriptions')
    subscription_count = fields.Integer('Subscription Count', 
                                        compute='_compute_subscription_count')
    
    # Contract Terms
    min_duration = fields.Integer('Minimum Duration (months)', default=0)
    max_duration = fields.Integer('Maximum Duration (months)', default=0,
                                  help='0 = no maximum')
    auto_renew = fields.Boolean('Auto Renew', default=True)
    cancellation_period = fields.Integer('Cancellation Notice (days)', default=30)
    
    # Lifecycle Management - Plan-specific overrides
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=0,
        help='Plan-specific grace period. 0 = use system default'
    )
    suspend_period_days = fields.Integer(
        string='Suspension Period (Days)',
        default=0,
        help='Plan-specific suspension period. 0 = use system default'
    )
    terminate_period_days = fields.Integer(
        string='Termination Period (Days)',
        default=0,
        help='Plan-specific termination period. 0 = use system default'
    )
    
    # ==========================================
    # SEAT MANAGEMENT (NEW - for organizational memberships)
    # ==========================================
    
    supports_seats = fields.Boolean(
        string='Supports Multiple Seats',
        default=False,
        tracking=True,
        help='This plan allows seat-based subscriptions (organizational memberships)'
    )
    
    included_seats = fields.Integer(
        string='Included Seats',
        default=0,
        help='Number of seats included in the base price'
    )
    
    max_seats = fields.Integer(
        string='Maximum Seats',
        default=0,
        help='Maximum number of seats allowed (0 = unlimited)'
    )
    
    additional_seat_price = fields.Monetary(
        string='Additional Seat Price',
        currency_field='currency_id',
        default=0.0,
        help='Price per additional seat beyond included seats'
    )
    
    seat_product_id = fields.Many2one(
        'product.template',
        string='Seat Add-on Product',
        domain=[('is_membership_product', '=', True), ('provides_seats', '=', True)],
        help='Optional product for purchasing additional seats (seat packs)'
    )
    
    # Seat Statistics
    total_allocated_seats = fields.Integer(
        string='Total Allocated Seats',
        compute='_compute_seat_statistics',
        help='Total seats allocated across all subscriptions'
    )
    
    active_seat_subscriptions = fields.Integer(
        string='Active Seat Subscriptions',
        compute='_compute_seat_statistics',
        help='Number of active seat subscriptions'
    )
    
    @api.depends('subscription_ids', 'subscription_ids.allocated_seat_count',
                 'subscription_ids.child_subscription_ids')
    def _compute_seat_statistics(self):
        """Calculate seat allocation statistics"""
        for plan in self:
            if plan.supports_seats:
                active_subs = plan.subscription_ids.filtered(
                    lambda s: s.state in ('active', 'trial')
                )
                plan.total_allocated_seats = sum(active_subs.mapped('allocated_seat_count'))
                
                # Count all child subscriptions (seat subscriptions)
                plan.active_seat_subscriptions = len(
                    active_subs.mapped('child_subscription_ids')
                )
            else:
                plan.total_allocated_seats = 0
                plan.active_seat_subscriptions = 0
    
    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for plan in self:
            plan.subscription_count = len(plan.subscription_ids)
    
    @api.constrains('billing_interval')
    def _check_billing_interval(self):
        for plan in self:
            if plan.billing_interval <= 0:
                raise ValidationError(_('Billing interval must be greater than 0'))
    
    @api.constrains('price')
    def _check_price(self):
        for plan in self:
            if plan.price < 0:
                raise ValidationError(_('Price cannot be negative'))
    
    # NEW: Lifetime validation
    @api.constrains('is_lifetime', 'billing_period')
    def _check_lifetime_configuration(self):
        """Validate lifetime membership configuration"""
        for plan in self:
            if plan.is_lifetime and plan.billing_period != 'lifetime':
                raise ValidationError(_(
                    'Lifetime memberships must have billing period set to "Lifetime"'
                ))
            
            if plan.billing_period == 'lifetime' and not plan.is_lifetime:
                plan.is_lifetime = True  # Auto-fix
    
    @api.constrains('is_lifetime', 'auto_renew')
    def _check_lifetime_auto_renew(self):
        """Lifetime plans cannot auto-renew"""
        for plan in self:
            if plan.is_lifetime and plan.auto_renew:
                raise ValidationError(_(
                    'Lifetime plans cannot have auto-renewal enabled. '
                    'Lifetime memberships are one-time payments that never expire.'
                ))
    
    # NEW: Seat validation
    @api.constrains('supports_seats', 'included_seats', 'max_seats')
    def _check_seat_configuration(self):
        """Validate seat configuration"""
        for plan in self:
            if plan.supports_seats:
                if plan.included_seats < 0:
                    raise ValidationError(_('Included seats cannot be negative'))
                if plan.max_seats < 0:
                    raise ValidationError(_('Maximum seats cannot be negative'))
                if plan.max_seats > 0 and plan.included_seats > plan.max_seats:
                    raise ValidationError(_(
                        'Included seats cannot exceed maximum seats'
                    ))
    
    # NEW: Lifetime onchange
    @api.onchange('is_lifetime')
    def _onchange_is_lifetime(self):
        """Set defaults when lifetime is enabled"""
        if self.is_lifetime:
            self.billing_period = 'lifetime'
            self.auto_renew = False
            self.trial_period = 0
            self.max_duration = 0
            self.usage_based = False
    
    @api.onchange('billing_period')
    def _onchange_billing_period(self):
        """Handle lifetime billing period selection"""
        if self.billing_period == 'lifetime':
            self.is_lifetime = True
            self.auto_renew = False
            self.trial_period = 0
    
    @api.onchange('supports_seats')
    def _onchange_supports_seats(self):
        """Set defaults when seat support is enabled"""
        if self.supports_seats and self.included_seats == 0:
            self.included_seats = 1
    
    def get_next_billing_date(self, start_date):
        """Calculate next billing date based on plan configuration and billing type"""
        self.ensure_one()
        
        # NEW: Lifetime memberships don't have next billing
        if self.is_lifetime or self.billing_period == 'lifetime':
            return False
        
        if self.billing_type == 'calendar':
            return self._get_calendar_based_billing_date(start_date)
        else:
            return self._get_anniversary_based_billing_date(start_date)
    
    def _get_anniversary_based_billing_date(self, start_date):
        """Calculate anniversary-based billing date (X period from start date)"""
        if self.billing_period == 'daily':
            return start_date + relativedelta(days=self.billing_interval)
        elif self.billing_period == 'weekly':
            return start_date + relativedelta(weeks=self.billing_interval)
        elif self.billing_period == 'monthly':
            return start_date + relativedelta(months=self.billing_interval)
        elif self.billing_period == 'quarterly':
            return start_date + relativedelta(months=3 * self.billing_interval)
        elif self.billing_period == 'yearly':
            return start_date + relativedelta(years=self.billing_interval)
        return start_date
    
    def _get_calendar_based_billing_date(self, start_date):
        """Calculate calendar-based billing date (aligned to calendar periods)"""
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        
        if self.billing_period == 'daily':
            # Daily billing doesn't make sense for calendar-based, treat as anniversary
            return start_date + relativedelta(days=self.billing_interval)
        
        elif self.billing_period == 'weekly':
            # End of current week (Sunday)
            days_until_sunday = (6 - start_date.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            return start_date + relativedelta(days=days_until_sunday)
        
        elif self.billing_period == 'monthly':
            # End of current month
            next_month = start_date + relativedelta(months=1)
            return date(next_month.year, next_month.month, 1) - relativedelta(days=1)
        
        elif self.billing_period == 'quarterly':
            # End of current quarter
            # Quarters: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec)
            current_quarter = (start_date.month - 1) // 3
            end_month = (current_quarter + 1) * 3  # Last month of quarter
            
            if end_month > 12:
                # Next year's Q1
                return date(start_date.year + 1, 3, 31)
            else:
                # End of current quarter
                next_month = date(start_date.year, end_month, 1) + relativedelta(months=1)
                return next_month - relativedelta(days=1)
        
        elif self.billing_period == 'yearly':
            # End of current year
            return date(start_date.year, 12, 31)
        
        return start_date
    
    def get_subscription_end_date(self, start_date):
        """Calculate subscription end date based on billing type"""
        self.ensure_one()
        
        # NEW: Lifetime memberships never expire
        if self.is_lifetime or self.billing_period == 'lifetime':
            return False  # Never expires
        
        if self.billing_type == 'calendar':
            return self._get_calendar_based_billing_date(start_date)
        else:
            return self._get_anniversary_based_billing_date(start_date)
    
    def action_view_subscriptions(self):
        """Action to view subscriptions for this plan"""
        return {
            'name': _('Subscriptions'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
    
    def action_view_seat_subscriptions(self):
        """Action to view seat subscriptions for this plan"""
        self.ensure_one()
        
        # Get all parent subscriptions for this plan
        parent_subs = self.subscription_ids.filtered(
            lambda s: s.state in ('active', 'trial') and s.supports_seats
        )
        
        # Get all child (seat) subscriptions
        seat_subs = parent_subs.mapped('child_subscription_ids')
        
        return {
            'name': _('Seat Subscriptions - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', seat_subs.ids)],
            'context': {
                'default_plan_id': self.id,
                'search_default_active': 1,
            },
        }