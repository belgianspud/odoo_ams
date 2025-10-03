# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionPlan(models.Model):
    """
    Subscription Plan - Defines pricing and billing configuration
    ENHANCED: Now supports lifetime memberships
    """
    _name = 'subscription.plan'
    _description = 'Subscription Plan'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Plan Name',
        required=True,
        tracking=True,
        translate=True,
        help='Display name for this subscription plan'
    )
    
    code = fields.Char(
        string='Plan Code',
        help='Unique identifier for this plan'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True,
        help='Inactive plans cannot be selected for new subscriptions'
    )
    
    description = fields.Html(
        string='Description',
        translate=True,
        help='Detailed description shown to customers'
    )

    # ==========================================
    # PRODUCT LINK
    # ==========================================
    
    product_template_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        domain=[('is_subscription', '=', True)],
        help='Product that customers will purchase'
    )

    # ==========================================
    # PRICING
    # ==========================================
    
    price = fields.Float(
        string='Price',
        required=True,
        tracking=True,
        help='Subscription price per billing period'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ==========================================
    # BILLING CONFIGURATION (ENHANCED)
    # ==========================================
    
    billing_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),  # NEW
    ], string='Billing Period',
       default='monthly',
       required=True,
       tracking=True,
       help='How often the subscription is billed')
    
    billing_interval = fields.Integer(
        string='Billing Interval',
        default=1,
        required=True,
        help='Number of periods between billings (e.g., 2 = every 2 months)'
    )
    
    billing_type = fields.Selection([
        ('anniversary', 'Anniversary-based'),
        ('calendar', 'Calendar-based'),
    ], string='Billing Type',
       default='anniversary',
       required=True,
       help='Anniversary: bills from signup date. Calendar: aligns to calendar periods')
    
    # NEW: Lifetime membership flag
    is_lifetime = fields.Boolean(
        string='Lifetime Membership',
        compute='_compute_is_lifetime',
        store=True,
        help='One-time payment, never expires'
    )
    
    @api.depends('billing_period')
    def _compute_is_lifetime(self):
        """Determine if this is a lifetime plan"""
        for plan in self:
            plan.is_lifetime = (plan.billing_period == 'lifetime')

    # ==========================================
    # RENEWAL CONFIGURATION
    # ==========================================
    
    auto_renew = fields.Boolean(
        string='Auto-Renew',
        default=True,
        help='Automatically renew subscriptions when they expire'
    )

    # ==========================================
    # TRIAL CONFIGURATION
    # ==========================================
    
    trial_period = fields.Integer(
        string='Trial Period',
        default=0,
        help='Number of days for free trial (0 = no trial)'
    )
    
    trial_price = fields.Float(
        string='Trial Price',
        default=0.0,
        help='Price during trial period (usually 0)'
    )

    # ==========================================
    # PLAN LIMITS
    # ==========================================
    
    user_limit = fields.Integer(
        string='User Limit',
        default=0,
        help='Maximum number of users (0 = unlimited)'
    )
    
    storage_limit = fields.Integer(
        string='Storage Limit (GB)',
        default=0,
        help='Storage quota in GB (0 = unlimited)'
    )
    
    min_duration = fields.Integer(
        string='Minimum Duration',
        default=0,
        help='Minimum subscription duration in months'
    )
    
    max_duration = fields.Integer(
        string='Maximum Duration',
        default=0,
        help='Maximum subscription duration in months (0 = unlimited)'
    )
    
    cancellation_period = fields.Integer(
        string='Cancellation Period',
        default=0,
        help='Notice period required for cancellation in days'
    )

    # ==========================================
    # USAGE-BASED BILLING
    # ==========================================
    
    usage_based = fields.Boolean(
        string='Usage-Based Billing',
        default=False,
        help='Enable metered/usage-based billing'
    )
    
    usage_unit = fields.Char(
        string='Usage Unit',
        help='Unit of measurement (e.g., GB, API calls, users)'
    )
    
    usage_price = fields.Float(
        string='Price per Unit',
        help='Price per usage unit'
    )
    
    included_usage = fields.Float(
        string='Included Usage',
        default=0,
        help='Usage included in base price'
    )

    # ==========================================
    # LIFECYCLE MANAGEMENT (Plan-specific overrides)
    # ==========================================
    
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
    # STATISTICS
    # ==========================================
    
    subscription_count = fields.Integer(
        string='Subscriptions',
        compute='_compute_subscription_count',
        help='Number of active subscriptions using this plan'
    )

    @api.depends('product_template_id')
    def _compute_subscription_count(self):
        """Count subscriptions using this plan"""
        for plan in self:
            plan.subscription_count = self.env['subscription.subscription'].search_count([
                ('plan_id', '=', plan.id)
            ])

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_billing_frequency_display(self):
        """Get human-readable billing frequency"""
        self.ensure_one()
        
        if self.is_lifetime:
            return _('One-time payment')
        
        if self.billing_interval == 1:
            return dict(self._fields['billing_period'].selection)[self.billing_period]
        else:
            return _('Every %s %s') % (
                self.billing_interval,
                dict(self._fields['billing_period'].selection)[self.billing_period]
            )

    def calculate_next_billing_date(self, start_date):
        """
        Calculate next billing date based on plan configuration
        
        Args:
            start_date: Starting date for calculation
            
        Returns:
            date: Next billing date, or False for lifetime plans
        """
        self.ensure_one()
        
        # Lifetime plans never have a next billing date
        if self.is_lifetime:
            return False
        
        if self.billing_type == 'anniversary':
            return self._calculate_anniversary_date(start_date)
        else:
            return self._calculate_calendar_date(start_date)
    
    def _calculate_anniversary_date(self, start_date):
        """Calculate anniversary-based next billing date"""
        from dateutil.relativedelta import relativedelta
        
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
        
        return False
    
    def _calculate_calendar_date(self, start_date):
        """Calculate calendar-aligned next billing date"""
        from dateutil.relativedelta import relativedelta
        
        if self.billing_period == 'monthly':
            # End of current month + interval
            next_date = start_date + relativedelta(day=31, months=self.billing_interval)
            return next_date
        elif self.billing_period == 'quarterly':
            # End of current quarter
            quarter = (start_date.month - 1) // 3
            next_quarter_start = start_date.replace(month=quarter * 3 + 1, day=1)
            next_date = next_quarter_start + relativedelta(months=3 * self.billing_interval, day=31)
            return next_date
        elif self.billing_period == 'yearly':
            # End of current year
            return start_date.replace(month=12, day=31) + relativedelta(years=self.billing_interval - 1)
        
        # Default to anniversary for other periods
        return self._calculate_anniversary_date(start_date)

    def action_view_subscriptions(self):
        """View all subscriptions using this plan"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {
                'default_plan_id': self.id,
            }
        }

    def name_get(self):
        """Custom display name"""
        result = []
        for plan in self:
            name = plan.name
            if plan.code:
                name = f"[{plan.code}] {name}"
            if plan.is_lifetime:
                name = f"{name} (Lifetime)"
            result.append((plan.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('price')
    def _check_price(self):
        """Validate price is positive"""
        for plan in self:
            if plan.price < 0:
                raise ValidationError(_('Plan price cannot be negative'))

    @api.constrains('billing_interval')
    def _check_billing_interval(self):
        """Validate billing interval"""
        for plan in self:
            if plan.billing_interval < 1:
                raise ValidationError(_('Billing interval must be at least 1'))
    
    @api.constrains('billing_period', 'auto_renew')
    def _check_lifetime_auto_renew(self):
        """Lifetime plans cannot auto-renew"""
        for plan in self:
            if plan.is_lifetime and plan.auto_renew:
                raise ValidationError(_(
                    'Lifetime plans cannot have auto-renewal enabled. '
                    'Lifetime memberships are one-time payments that never expire.'
                ))
    
    @api.constrains('billing_period', 'billing_interval')
    def _check_lifetime_interval(self):
        """Lifetime plans must have interval of 1"""
        for plan in self:
            if plan.is_lifetime and plan.billing_interval != 1:
                raise ValidationError(_(
                    'Lifetime plans must have a billing interval of 1.'
                ))

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================
    
    @api.onchange('billing_period')
    def _onchange_billing_period(self):
        """Handle lifetime selection"""
        if self.billing_period == 'lifetime':
            # Disable auto-renew for lifetime plans
            self.auto_renew = False
            self.billing_interval = 1
            
            # Clear trial period (doesn't make sense for lifetime)
            self.trial_period = 0
            self.trial_price = 0.0

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Plan code must be unique!'),
    ]