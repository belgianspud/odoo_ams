# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAccount(models.Model):
    """Enhanced Chart of Accounts with AMS-specific categories"""
    _inherit = 'account.account'

    # AMS-specific account categorization
    ams_account_category = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('dues_revenue', 'Dues Revenue'),
        ('publication_revenue', 'Publication Revenue'), 
        ('chapter_revenue', 'Chapter Revenue'),
        ('event_revenue', 'Event Revenue'),
        ('donation_revenue', 'Donation Revenue'),
        ('grant_revenue', 'Grant Revenue'),
        ('subscription_ar', 'Subscription A/R'),
        ('membership_expense', 'Membership Expenses'),
        ('publication_expense', 'Publication Expenses'),
        ('chapter_expense', 'Chapter Expenses'),
        ('event_expense', 'Event Expenses'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('cash_membership', 'Cash - Membership'),
        ('cash_events', 'Cash - Events'),
        ('other', 'Other'),
    ], string='AMS Category', help='Association-specific account category')
    
    # Enhanced description for association context
    ams_description = fields.Text(
        string='AMS Description',
        help='Additional description specific to association use case'
    )
    
    # Flag for AMS-managed accounts
    is_ams_account = fields.Boolean(
        string='AMS Managed Account',
        default=False,
        help='This account is managed by the AMS system'
    )
    
    # Usage tracking
    subscription_count = fields.Integer(
        string='Subscription Usage Count',
        compute='_compute_ams_usage',
        help='Number of products using this account for subscriptions'
    )
    
    def _compute_ams_usage(self):
        """Compute how many products are using this account"""
        for account in self:
            # Count products using this account in any capacity
            product_count = self.env['product.template'].search_count([
                '|', '|', '|', '|',
                ('ams_revenue_account_id', '=', account.id),
                ('ams_receivable_account_id', '=', account.id),
                ('ams_cash_account_id', '=', account.id),
                ('ams_deferred_account_id', '=', account.id),
                ('ams_expense_account_id', '=', account.id),
            ])
            account.subscription_count = product_count
    
    @api.model
    def create_ams_account_structure(self):
        """Create default AMS account structure"""
        company = self.env.company
        
        # Define default AMS accounts to create
        ams_accounts = [
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
                'code': '2300',
                'name': 'Deferred Membership Revenue',
                'account_type': 'liability_current',
                'ams_account_category': 'deferred_revenue',
                'ams_description': 'Unearned revenue from prepaid memberships',
            },
            {
                'code': '1200',
                'name': 'Accounts Receivable - Memberships',
                'account_type': 'asset_receivable',
                'ams_account_category': 'subscription_ar',
                'ams_description': 'Outstanding membership invoices',
            },
        ]
        
        created_accounts = []
        for account_data in ams_accounts:
            # Check if account already exists
            existing = self.search([
                ('code', '=', account_data['code']),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if not existing:
                account_data.update({
                    'company_id': company.id,
                    'is_ams_account': True,
                })
                account = self.create(account_data)
                created_accounts.append(account)
        
        return created_accounts
    
    def action_view_related_products(self):
        """Action to view products using this account"""
        self.ensure_one()
        
        domain = [
            '|', '|', '|', '|',
            ('ams_revenue_account_id', '=', self.id),
            ('ams_receivable_account_id', '=', self.id), 
            ('ams_cash_account_id', '=', self.id),
            ('ams_deferred_account_id', '=', self.id),
            ('ams_expense_account_id', '=', self.id),
        ]
        
        return {
            'name': f'Products Using Account: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_ams_products': 1}
        }


class AccountAccountType(models.Model):
    """Add AMS-specific account type information"""
    _inherit = 'account.account'
    
    @api.model
    def _get_ams_account_type_mapping(self):
        """Mapping of AMS categories to appropriate Odoo account types"""
        return {
            'membership_revenue': 'income_other',
            'dues_revenue': 'income_other', 
            'publication_revenue': 'income_other',
            'chapter_revenue': 'income_other',
            'event_revenue': 'income_other',
            'donation_revenue': 'income_other',
            'grant_revenue': 'income_other',
            'subscription_ar': 'asset_receivable',
            'membership_expense': 'expense',
            'publication_expense': 'expense', 
            'chapter_expense': 'expense',
            'event_expense': 'expense',
            'deferred_revenue': 'liability_current',
            'cash_membership': 'asset_cash',
            'cash_events': 'asset_cash',
            'other': 'expense',
        }
    
    @api.onchange('ams_account_category')
    def _onchange_ams_account_category(self):
        """Auto-set account type based on AMS category"""
        if self.ams_account_category:
            mapping = self._get_ams_account_type_mapping()
            suggested_type = mapping.get(self.ams_account_category)
            if suggested_type:
                self.account_type = suggested_type