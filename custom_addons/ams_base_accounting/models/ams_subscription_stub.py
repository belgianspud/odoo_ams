# -*- coding: utf-8 -*-
"""
Basic subscription model stub for AMS Base Accounting

This provides a minimal subscription model when the full AMS Subscriptions
module is not installed, allowing the accounting module to function independently.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError

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
    
    # Related Records Count
    move_ids = fields.One2many(
        'ams.account.move',
        'subscription_id',
        string='Journal Entries',
        readonly=True,
        help='Related journal entries'
    )
    
    revenue_recognition_ids = fields.One2many(
        'ams.revenue.recognition',
        'subscription_id',
        string='Revenue Recognition Entries',
        readonly=True,
        help='Related revenue recognition entries'
    )
    
    journal_entry_count = fields.Integer(
        string='Journal Entries Count',
        compute='_compute_entry_counts',
        help='Number of related journal entries'
    )
    
    revenue_recognition_count = fields.Integer(
        string='Revenue Recognition Count',
        compute='_compute_entry_counts',
        help='Number of revenue recognition entries'
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
    
    @api.depends('move_ids', 'revenue_recognition_ids')
    def _compute_entry_counts(self):
        """Compute counts of related entries"""
        for subscription in self:
            subscription.journal_entry_count = len(subscription.move_ids)
            subscription.revenue_recognition_count = len(subscription.revenue_recognition_ids)
    
    # Lifecycle Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence numbers"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.subscription') or 'SUB001'
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to handle state changes"""
        if 'state' in vals:
            for subscription in self:
                # Trigger recomputation of financial amounts when state changes
                subscription._compute_financial_amounts()
        return super().write(vals)
    
    # Business Methods
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
    
    def action_suspend(self):
        """Suspend the subscription"""
        for subscription in self:
            subscription.state = 'suspended'
    
    def action_cancel(self):
        """Cancel the subscription"""
        for subscription in self:
            subscription.state = 'cancelled'
    
    def action_renew(self):
        """Renew the subscription"""
        for subscription in self:
            if subscription.paid_through_date:
                # Extend paid through date by one period
                if subscription.subscription_period == 'monthly':
                    subscription.paid_through_date = subscription.paid_through_date + relativedelta(months=1)
                elif subscription.subscription_period == 'quarterly':
                    subscription.paid_through_date = subscription.paid_through_date + relativedelta(months=3)
                elif subscription.subscription_period == 'semi_annual':
                    subscription.paid_through_date = subscription.paid_through_date + relativedelta(months=6)
                elif subscription.subscription_period == 'annual':
                    subscription.paid_through_date = subscription.paid_through_date + relativedelta(years=1)
                elif subscription.subscription_period == 'biennial':
                    subscription.paid_through_date = subscription.paid_through_date + relativedelta(years=2)
                
                subscription.state = 'active'
    
    # Accounting Integration Methods
    def action_setup_accounting(self):
        """Set up accounting for this subscription"""
        self.ensure_one()
        
        return {
            'name': 'Setup Subscription Accounting',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.accounting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_action_type': 'setup',
            }
        }
    
    def action_view_journal_entries(self):
        """View related journal entries"""
        self.ensure_one()
        
        return {
            'name': f'Journal Entries - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id}
        }
    
    def action_view_revenue_recognition(self):
        """View revenue recognition entries"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognition - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id}
        }
    
    def name_get(self):
        """Custom display name"""
        result = []
        for subscription in self:
            name = f'{subscription.name}'
            if subscription.partner_id:
                name += f' - {subscription.partner_id.name}'
            result.append((subscription.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search"""
        args = args or []
        if name:
            domain = [
                '|', '|',
                ('name', operator, name),
                ('partner_id.name', operator, name),
                ('product_id.name', operator, name)
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)