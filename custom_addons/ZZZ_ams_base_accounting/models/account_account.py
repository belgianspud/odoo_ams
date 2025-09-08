# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAccount(models.Model):
    """Enhanced Account with AMS-specific fields"""
    _inherit = 'account.account'
    
    # AMS-specific fields
    ams_account_category = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('publication_revenue', 'Publication Revenue'),
        ('chapter_revenue', 'Chapter Revenue'),
        ('event_revenue', 'Event Revenue'),
        ('subscription_ar', 'Subscription A/R'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('cash_membership', 'Cash - Membership'),
        ('cash_events', 'Cash - Events'),
        ('membership_expense', 'Membership Expense'),
        ('publication_expense', 'Publication Expense'),
        ('chapter_expense', 'Chapter Expense'),
        ('event_expense', 'Event Expense'),
        ('technology_expense', 'Technology Expense'),
    ], string='AMS Account Category', help='Category for AMS-specific accounting')
    
    is_ams_account = fields.Boolean(
        string='AMS Account',
        compute='_compute_is_ams_account',
        store=True,
        help='This account is used for AMS transactions'
    )
    
    ams_description = fields.Text(
        string='AMS Description',
        help='Detailed description for AMS usage'
    )
    
    # Statistics for related products
    subscription_count = fields.Integer(
        string='Subscription Products',
        compute='_compute_subscription_count',
        help='Number of subscription products using this account'
    )
    
    @api.depends('ams_account_category')
    def _compute_is_ams_account(self):
        """Mark accounts as AMS accounts if they have a category"""
        for account in self:
            account.is_ams_account = bool(account.ams_account_category)
    
    def _compute_subscription_count(self):
        """Count subscription products using this account"""
        for account in self:
            count = self.env['product.template'].search_count([
                '|', '|', '|', '|', '|',
                ('ams_revenue_account_id', '=', account.id),
                ('ams_deferred_account_id', '=', account.id),
                ('ams_receivable_account_id', '=', account.id),
                ('ams_cash_account_id', '=', account.id),
                ('ams_expense_account_id', '=', account.id),
                ('is_subscription_product', '=', True)
            ])
            account.subscription_count = count
    
    def action_view_related_products(self):
        """View products that use this account"""
        self.ensure_one()
        
        return {
            'name': f'Products using {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [
                '|', '|', '|', '|', '|',
                ('ams_revenue_account_id', '=', self.id),
                ('ams_deferred_account_id', '=', self.id),
                ('ams_receivable_account_id', '=', self.id),
                ('ams_cash_account_id', '=', self.id),
                ('ams_expense_account_id', '=', self.id),
                ('is_subscription_product', '=', True)
            ],
            'context': {'default_use_ams_accounting': True}
        }
    
    @api.model
    def get_ams_account_by_category(self, category):
        """Get AMS account by category (safer than code-based lookup)"""
        account = self.search([
            ('ams_account_category', '=', category),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return account
    
    @api.model
    def get_ams_account_by_code(self, code):
        """Get AMS account by code with company filter"""
        account = self.search([
            ('code', '=', code),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return account
    
    @api.model
    def create_ams_account_structure(self):
        """Create AMS-specific chart of accounts (FIXED to avoid conflicts)"""
        
        # Check if AMS accounts already exist
        existing = self.search([
            ('ams_account_category', '!=', False),
            ('company_id', '=', self.env.company.id)
        ])
        
        if existing:
            return existing  # Already created
        
        # Define account structure (only create if XML data didn't create them)
        account_data = [
            {
                'code': '4100',
                'name': 'Membership Revenue - Individual',
                'account_type': 'income_other',
                'ams_account_category': 'membership_revenue',
                'ams_description': 'Revenue from individual membership subscriptions',
            },
            {
                'code': '4110', 
                'name': 'Membership Revenue - Enterprise',
                'account_type': 'income_other',
                'ams_account_category': 'membership_revenue',
                'ams_description': 'Revenue from enterprise membership subscriptions',
            },
            {
                'code': '4200',
                'name': 'Publication Revenue',
                'account_type': 'income_other',
                'ams_account_category': 'publication_revenue',
                'ams_description': 'Revenue from publication subscriptions',
            },
            {
                'code': '4300',
                'name': 'Chapter Revenue',
                'account_type': 'income_other', 
                'ams_account_category': 'chapter_revenue',
                'ams_description': 'Revenue from chapter memberships',
            },
            {
                'code': '4400',
                'name': 'Event Revenue',
                'account_type': 'income_other', 
                'ams_account_category': 'event_revenue',
                'ams_description': 'Revenue from events and conferences',
            },
            {
                'code': '1200',
                'name': 'Accounts Receivable - Memberships',
                'account_type': 'asset_receivable',
                'ams_account_category': 'subscription_ar',
                'ams_description': 'Outstanding membership invoices',
            },
            {
                'code': '2300',
                'name': 'Deferred Membership Revenue',
                'account_type': 'liability_current',
                'ams_account_category': 'deferred_revenue', 
                'ams_description': 'Unearned revenue from prepaid memberships',
            },
            {
                'code': '1010',
                'name': 'Cash - Membership Payments',
                'account_type': 'asset_cash',
                'ams_account_category': 'cash_membership', 
                'ams_description': 'Cash account for membership payments',
            },
        ]
        
        created_accounts = []
        for data in account_data:
            # FIXED: Check if account with this code already exists
            existing_account = self.search([
                ('code', '=', data['code']),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if existing_account:
                # Account exists, just update AMS fields if needed
                if not existing_account.ams_account_category:
                    existing_account.write({
                        'ams_account_category': data['ams_account_category'],
                        'ams_description': data['ams_description'],
                    })
                created_accounts.append(existing_account)
            else:
                # Create new account
                account = self.create(data)
                created_accounts.append(account)
        
        return created_accounts
    
    @api.model
    def ensure_ams_accounts_configured(self):
        """Ensure all AMS accounts are properly configured with categories"""
        
        # Find accounts that match AMS codes but don't have categories
        ams_codes = ['4100', '4110', '4200', '4300', '4400', '1200', '2300', '1010', '1020']
        
        for code in ams_codes:
            account = self.search([
                ('code', '=', code),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if account and not account.ams_account_category:
                # Set the category based on the code
                category_mapping = {
                    '4100': 'membership_revenue',
                    '4110': 'membership_revenue', 
                    '4200': 'publication_revenue',
                    '4300': 'chapter_revenue',
                    '4400': 'event_revenue',
                    '1200': 'subscription_ar',
                    '2300': 'deferred_revenue',
                    '1010': 'cash_membership',
                    '1020': 'cash_events',
                }
                
                if code in category_mapping:
                    account.ams_account_category = category_mapping[code]
        
        return True
    
    @api.model
    def get_default_account_mapping(self):
        """Get default account mapping for AMS product types"""
        
        return {
            'individual': {
                'revenue': self.get_ams_account_by_category('membership_revenue'),
                'deferred': self.get_ams_account_by_category('deferred_revenue'),
                'receivable': self.get_ams_account_by_category('subscription_ar'),
                'cash': self.get_ams_account_by_category('cash_membership'),
                'expense': self.get_ams_account_by_category('membership_expense'),
            },
            'enterprise': {
                'revenue': self.get_ams_account_by_code('4110') or self.get_ams_account_by_category('membership_revenue'),
                'deferred': self.get_ams_account_by_category('deferred_revenue'),
                'receivable': self.get_ams_account_by_category('subscription_ar'),
                'cash': self.get_ams_account_by_category('cash_membership'),
                'expense': self.get_ams_account_by_category('membership_expense'),
            },
            'chapter': {
                'revenue': self.get_ams_account_by_category('chapter_revenue'),
                'deferred': self.get_ams_account_by_category('deferred_revenue'),
                'receivable': self.get_ams_account_by_category('subscription_ar'),
                'cash': self.get_ams_account_by_category('cash_membership'),
                'expense': self.get_ams_account_by_category('chapter_expense'),
            },
            'publication': {
                'revenue': self.get_ams_account_by_category('publication_revenue'),
                'deferred': self.get_ams_account_by_category('deferred_revenue'),
                'receivable': self.get_ams_account_by_category('subscription_ar'),
                'cash': self.get_ams_account_by_category('cash_membership'),
                'expense': self.get_ams_account_by_category('publication_expense'),
            },
        }
    
    def validate_ams_account_setup(self):
        """Validate that AMS accounts are properly set up"""
        issues = []
        
        # Check for required AMS account categories
        required_categories = [
            'membership_revenue',
            'deferred_revenue', 
            'subscription_ar',
            'cash_membership',
        ]
        
        for category in required_categories:
            account = self.get_ams_account_by_category(category)
            if not account:
                issues.append(f"Missing account for category: {category}")
        
        # Check for account type consistency
        type_requirements = {
            'membership_revenue': ['income', 'income_other'],
            'publication_revenue': ['income', 'income_other'],
            'chapter_revenue': ['income', 'income_other'],
            'event_revenue': ['income', 'income_other'],
            'deferred_revenue': ['liability_current'],
            'subscription_ar': ['asset_receivable'],
            'cash_membership': ['asset_cash'],
            'cash_events': ['asset_cash'],
        }
        
        ams_accounts = self.search([('ams_account_category', '!=', False)])
        for account in ams_accounts:
            required_types = type_requirements.get(account.ams_account_category, [])
            if required_types and account.account_type not in required_types:
                issues.append(f"Account {account.code} has wrong type: expected {required_types}, got {account.account_type}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'accounts_checked': len(ams_accounts),
        }