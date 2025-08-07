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
        ('subscription_ar', 'Subscription A/R'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('cash_membership', 'Cash - Membership'),
        ('cash_events', 'Cash - Events'),
        ('membership_expense', 'Membership Expense'),
        ('publication_expense', 'Publication Expense'),
        ('chapter_expense', 'Chapter Expense'),
        ('event_expense', 'Event Expense'),
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
    def create_ams_account_structure(self):
        """Create AMS-specific chart of accounts"""
        
        # Check if AMS accounts already exist
        existing = self.search([
            ('ams_account_category', '!=', False)
        ])
        
        if existing:
            return existing  # Already created
        
        # Define account structure
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
        ]
        
        created_accounts = []
        for data in account_data:
            # Check if account with this code already exists
            existing_account = self.search([('code', '=', data['code'])], limit=1)
            if not existing_account:
                account = self.create(data)
                created_accounts.append(account)
        
        return created_accounts