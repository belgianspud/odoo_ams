# -*- coding: utf-8 -*-
"""
Basic subscription model stub for AMS Base Accounting

This provides a minimal subscription model when the full AMS Subscriptions
module is not installed, allowing the accounting module to function independently.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

# Only create stub models if they don't already exist
def _model_exists(env, model_name):
    """Check if a model already exists"""
    try:
        return model_name in env.registry
    except:
        return False

class AMSSubscriptionStub(models.Model):
    """
    Basic subscription model for accounting integration
    
    This is a minimal implementation that provides the essential fields
    needed by the accounting module. If the full AMS Subscriptions module
    is installed, this model will be extended/replaced.
    """
    _name = 'ams.subscription'
    _description = 'AMS Subscription (Basic)'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def _check_model_exists(self):
        """Check if this stub should be active"""
        # If a more complete subscription model exists, don't interfere
        if hasattr(self.env, '_ams_subscription_full_model'):
            return False
        return True
    
    # Basic Information
    name = fields.Char(
        string='Subscription Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default='New'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        help='Customer associated with this subscription'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True,
        help='Product/service being subscribed to'
    )
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Subscription start date'
    )
    
    end_date = fields.Date(
        string='End Date',
        tracking=True,
        help='Subscription end date'
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        tracking=True,
        help='Date through which subscription is paid'
    )
    
    # Subscription Details
    subscription_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication Subscription'),
        ('event', 'Event Registration'),
        ('general', 'General Subscription'),
    ], string='Subscription Type', default='general', required=True,
       tracking=True, help='Type of subscription')
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Subscription Period', default='annual', required=True,
       tracking=True, help='Billing/renewal period')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True,
       tracking=True, help='Current subscription status')
    
    # Financial Information
    amount = fields.Float(
        string='Amount',
        digits='Account',
        help='Subscription amount'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for this subscription'
    )
    
    # Computed Financial Fields (for accounting integration)
    total_invoiced_amount = fields.Float(
        string='Total Invoiced Amount',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Total amount invoiced for this subscription'
    )
    
    total_recognized_revenue = fields.Float(
        string='Total Recognized Revenue',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Total revenue recognized to date'
    )
    
    deferred_revenue_balance = fields.Float(
        string='Deferred Revenue Balance',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Remaining deferred revenue balance'
    )
    
    # Accounting Integration
    accounting_setup_complete = fields.Boolean(
        string='Accounting Setup Complete',
        default=False,
        help='Whether accounting setup has been completed for this subscription'
    )
    
    auto_recognize_revenue = fields.Boolean(
        string='Auto Recognize Revenue',
        default=True,
        help='Automatically create revenue recognition entries'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Company this subscription belongs to'
    )
    
    # Computed Methods
    @api.depends('amount', 'product_id.list_price')
    def _compute_financial_amounts(self):
        """Compute financial amounts based on available data"""
        for subscription in self:
            # Use amount if set, otherwise use product price
            base_amount = subscription.amount or (subscription.product_id.list_price if subscription.product_id else 0.0)
            
            subscription.total_invoiced_amount = base_amount
            
            # Calculate recognized revenue (simplified calculation)
            if subscription.state == 'active' and subscription.start_date:
                days_elapsed = (fields.Date.today() - subscription.start_date).days
                total_days = subscription._get_subscription_days()
                
                if total_days > 0:
                    recognition_ratio = min(days_elapsed / total_days, 1.0)
                    subscription.total_recognized_revenue = base_amount * recognition_ratio
                else:
                    subscription.total_recognized_revenue = 0.0
            else:
                subscription.total_recognized_revenue = 0.0
            
            subscription.deferred_revenue_balance = base_amount - subscription.total_recognized_revenue
    
    # Lifecycle Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence numbers"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                sequence = self.env['ir.sequence'].next_by_code('ams.subscription')
                vals['name'] = sequence or f'SUB{self.env["ir.sequence"].next_by_code("base.sequence")}'
        return super().create(vals_list)
    
    def _get_subscription_days(self):
        """Get total number of days in subscription period"""
        period_days = {
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
            'biennial': 730,
        }
        return period_days.get(self.subscription_period, 365)
    
    def action_activate(self):
        """Activate the subscription"""
        for subscription in self:
            subscription.state = 'active'
            if not subscription.paid_through_date:
                # Set paid through date based on subscription period
                if subscription.subscription_period == 'monthly':
                    subscription.paid_through_date = subscription.start_date + relativedelta(months=1)
                elif subscription.subscription_period == 'quarterly':
                    subscription.paid_through_date = subscription.start_date + relativedelta(months=3)
                elif subscription.subscription_period == 'semi_annual':
                    subscription.paid_through_date = subscription.start_date + relativedelta(months=6)
                elif subscription.subscription_period == 'annual':
                    subscription.paid_through_date = subscription.start_date + relativedelta(years=1)
                elif subscription.subscription_period == 'biennial':
                    subscription.paid_through_date = subscription.start_date + relativedelta(years=2)
    
    def name_get(self):
        """Custom display name"""
        result = []
        for subscription in self:
            name = f'{subscription.name}'
            if subscription.partner_id:
                name += f' - {subscription.partner_id.name}'
            result.append((subscription.id, name))
        return result


# Minimal subscription tier model for the stub
class AMSSubscriptionTierStub(models.Model):
    """
    Basic subscription tier model for accounting integration
    """
    _name = 'ams.subscription.tier'
    _description = 'AMS Subscription Tier (Basic)'
    
    name = fields.Char(
        string='Tier Name',
        required=True,
        help='Name of the subscription tier'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the subscription tier'
    )
    
    subscription_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication Subscription'),
        ('event', 'Event Registration'),
        ('general', 'General Subscription'),
    ], string='Subscription Type', default='general', required=True,
       help='Type of subscription this tier applies to')
    
    period_length = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Period Length', default='annual', required=True,
       help='Billing period length')
    
    auto_renew = fields.Boolean(
        string='Auto Renew By Default',
        default=True,
        help='Whether subscriptions auto-renew by default'
    )
    
    is_free = fields.Boolean(
        string='Free Tier',
        default=False,
        help='This is a free subscription tier'
    )