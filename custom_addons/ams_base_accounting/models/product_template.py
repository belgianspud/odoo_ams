# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # AMS Product Configuration
    is_subscription_product = fields.Boolean(
        string='Is Subscription Product',
        default=False,
        help='Check if this product is used for subscriptions/memberships'
    )
    
    use_ams_accounting = fields.Boolean(
        string='Use AMS Accounting',
        default=False,
        help='Use AMS-specific accounting features for this product'
    )
    
    ams_product_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Corporate Membership'),
        ('student', 'Student Membership'),
        ('publication', 'Publication Subscription'),
        ('chapter', 'Chapter Membership'),
        ('event', 'Event Registration'),
        ('addon', 'Add-on Service'),
    ], string='AMS Product Type', help='Type of association product or service')
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('one_time', 'One Time'),
    ], string='Subscription Period', default='annual', help='Billing frequency for this product')
    
    # Financial account configuration
    ams_accounts_configured = fields.Boolean(
        string='AMS Accounts Configured',
        default=False,
        compute='_compute_ams_accounts_configured',
        help='Whether AMS-specific accounts are configured for this product'
    )
    
    ams_revenue_account_id = fields.Many2one(
        'account.account',
        string='AMS Revenue Account',
        domain=[('account_type', '=', 'income')],
        help='Revenue account to use for this AMS product'
    )
    
    ams_receivable_account_id = fields.Many2one(
        'account.account',
        string='AMS Receivable Account',
        domain=[('account_type', '=', 'asset_receivable')],
        help='Receivable account to use for this AMS product'
    )
    
    @api.depends('ams_revenue_account_id', 'ams_receivable_account_id', 'use_ams_accounting')
    def _compute_ams_accounts_configured(self):
        """Check if AMS accounts are properly configured"""
        for product in self:
            if product.use_ams_accounting:
                product.ams_accounts_configured = bool(
                    product.ams_revenue_account_id and 
                    product.ams_receivable_account_id
                )
            else:
                product.ams_accounts_configured = False
    
    @api.onchange('use_ams_accounting')
    def _onchange_use_ams_accounting(self):
        """Set default values when AMS accounting is enabled"""
        if self.use_ams_accounting and not self.is_subscription_product:
            self.is_subscription_product = True
        if not self.use_ams_accounting:
            self.ams_product_type = False
            self.ams_revenue_account_id = False
            self.ams_receivable_account_id = False
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Set default accounts based on product type"""
        if self.ams_product_type and self.use_ams_accounting:
            self._set_default_ams_accounts()
    
    def _set_default_ams_accounts(self):
        """Set default AMS accounts based on product type"""
        account_model = self.env['account.account']
        
        # Define account mappings based on product type
        account_mappings = {
            'individual': {
                'revenue_category': 'membership_revenue',
                'revenue_code': '4100',
            },
            'enterprise': {
                'revenue_category': 'membership_revenue', 
                'revenue_code': '4110',
            },
            'student': {
                'revenue_category': 'membership_revenue',
                'revenue_code': '4120',
            },
            'publication': {
                'revenue_category': 'publication_revenue',
                'revenue_code': '4200',
            },
            'chapter': {
                'revenue_category': 'chapter_revenue',
                'revenue_code': '4300',
            },
            'event': {
                'revenue_category': 'event_revenue',
                'revenue_code': '4400',
            },
            'addon': {
                'revenue_category': 'addon_revenue',
                'revenue_code': '4500',
            },
        }
        
        mapping = account_mappings.get(self.ams_product_type, {})
        
        if mapping:
            # Try to find revenue account by category first, then by code
            revenue_account = account_model.search([
                ('ams_account_category', '=', mapping['revenue_category']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if not revenue_account:
                revenue_account = account_model.search([
                    ('code', '=', mapping['revenue_code']),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
            
            if revenue_account:
                self.ams_revenue_account_id = revenue_account.id
            
            # Set default receivable account
            receivable_account = account_model.search([
                ('ams_account_category', '=', 'member_receivables'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if not receivable_account:
                receivable_account = account_model.search([
                    ('code', '=', '1200'),
                    ('account_type', '=', 'asset_receivable'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
            
            if receivable_account:
                self.ams_receivable_account_id = receivable_account.id
    
    @api.model
    def create(self, vals):
        """Auto-configure AMS accounts on creation"""
        product = super().create(vals)
        if product.use_ams_accounting and product.ams_product_type:
            product._set_default_ams_accounts()
        return product
    
    def write(self, vals):
        """Auto-configure AMS accounts on write"""
        result = super().write(vals)
        if 'ams_product_type' in vals or 'use_ams_accounting' in vals:
            for product in self:
                if product.use_ams_accounting and product.ams_product_type:
                    product._set_default_ams_accounts()
        return result