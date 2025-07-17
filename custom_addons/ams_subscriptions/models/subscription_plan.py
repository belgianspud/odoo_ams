from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date


class SubscriptionPlan(models.Model):
    _name = 'ams.subscription.plan'
    _description = 'Subscription Plan'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Plan Name', required=True, tracking=True)
    code = fields.Char('Plan Code', required=True, tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Status', default='active', required=True, tracking=True)

    # Plan Type
    plan_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('service', 'Service'),
        ('other', 'Other'),
    ], string='Plan Type', required=True, default='membership', tracking=True)
    
    # Subscription Details
    description = fields.Html('Description')
    product_id = fields.Many2one('product.product', 'Related Product', required=True, 
                                domain=[('type', '=', 'service')], tracking=True)
    
    # Billing Configuration
    billing_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Billing Period', required=True, default='annual', tracking=True)
    
    billing_interval = fields.Integer('Billing Interval', default=1, required=True,
                                    help="Bill every X periods (e.g., every 2 months)")
    
    # Pricing
    price = fields.Float('Regular Price', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Membership specific fields
    membership_grade = fields.Selection([
        ('student', 'Student'),
        ('associate', 'Associate'),
        ('full', 'Full Member'),
        ('senior', 'Senior'),
        ('honorary', 'Honorary'),
        ('corporate', 'Corporate'),
    ], string='Membership Grade', tracking=True)
    
    # Access and Benefits
    website_published = fields.Boolean('Published on Website', default=True, tracking=True)
    website_description = fields.Html('Website Description')
    benefits = fields.Text('Benefits')
    
    # Subscription Rules
    auto_renew = fields.Boolean('Auto Renew', default=True, 
                               help="Automatically renew subscriptions")
    grace_period_days = fields.Integer('Grace Period (Days)', default=30,
                                     help="Days after expiry to maintain access")
    trial_period_days = fields.Integer('Trial Period (Days)', default=0,
                                     help="Free trial period for new subscriptions")
    
    # Renewal Settings
    renewal_reminder_days = fields.Integer('Renewal Reminder (Days)', default=30,
                                         help="Send renewal reminder X days before expiry")
    allow_partial_periods = fields.Boolean('Allow Partial Periods', default=True,
                                         help="Allow prorated billing for partial periods")
    
    # Restrictions
    max_subscriptions = fields.Integer('Max Subscriptions', default=0,
                                     help="Maximum number of active subscriptions (0 = unlimited)")
    subscription_count = fields.Integer('Active Subscriptions', compute='_compute_subscription_count')
    
    # Chapter specific
    chapter_id = fields.Many2one('res.partner', 'Chapter', 
                               domain=[('is_company', '=', True), ('category_id.name', 'ilike', 'chapter')])
    
    # Publication specific
    publication_type = fields.Selection([
        ('magazine', 'Magazine'),
        ('newsletter', 'Newsletter'),
        ('journal', 'Journal'),
        ('digest', 'Digest'),
    ], string='Publication Type')
    
    # Computed fields
    subscription_ids = fields.One2many('ams.subscription', 'plan_id', 'Subscriptions')
    
    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for plan in self:
            plan.subscription_count = len(plan.subscription_ids.filtered(
                lambda s: s.active and s.state in ['active', 'trial'] if hasattr(s, 'state') else s.active
            ))
    
    def get_billing_period_delta(self):
        """Return relativedelta for the billing period"""
        period_map = {
            'daily': relativedelta(days=self.billing_interval),
            'weekly': relativedelta(weeks=self.billing_interval),
            'monthly': relativedelta(months=self.billing_interval),
            'quarterly': relativedelta(months=3 * self.billing_interval),
            'semi_annual': relativedelta(months=6 * self.billing_interval),
            'annual': relativedelta(years=self.billing_interval),
            'biennial': relativedelta(years=2 * self.billing_interval),
        }
        return period_map.get(self.billing_period, relativedelta(years=1))
    
    def calculate_next_billing_date(self, start_date):
        """Calculate next billing date from start date"""
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        return start_date + self.get_billing_period_delta()
    
    def calculate_proration_amount(self, start_date, end_date):
        """Calculate prorated amount for partial period"""
        if not self.allow_partial_periods:
            return self.price
            
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        if isinstance(end_date, str):
            end_date = fields.Date.from_string(end_date)
            
        # Calculate the full period
        full_period_end = self.calculate_next_billing_date(start_date)
        full_period_days = (full_period_end - start_date).days
        actual_days = (end_date - start_date).days
        
        if full_period_days > 0:
            return (actual_days / full_period_days) * self.price
        return self.price
    
    @api.constrains('max_subscriptions')
    def _check_max_subscriptions(self):
        for plan in self:
            if plan.max_subscriptions > 0 and plan.subscription_count >= plan.max_subscriptions:
                raise ValidationError(
                    _('Maximum number of subscriptions (%s) reached for plan %s') 
                    % (plan.max_subscriptions, plan.name)
                )
    
    @api.constrains('billing_interval')
    def _check_billing_interval(self):
        for plan in self:
            if plan.billing_interval <= 0:
                raise ValidationError(_('Billing interval must be greater than 0'))
    
    def action_view_subscriptions(self):
        """Action to view subscriptions for this plan"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }