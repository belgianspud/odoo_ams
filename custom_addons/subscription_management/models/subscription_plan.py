# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


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
    
    # Billing Configuration
    billing_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Billing Period', required=True, default='monthly', tracking=True)
    
    billing_interval = fields.Integer('Billing Interval', default=1, 
                                      help='Repeat every X periods')
    
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
    
    def get_next_billing_date(self, start_date):
        """Calculate next billing date based on plan configuration"""
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