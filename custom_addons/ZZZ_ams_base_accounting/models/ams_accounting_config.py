# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSAccountingConfig(models.TransientModel):
    """Configuration settings for AMS accounting"""
    _name = 'ams.accounting.config'
    _description = 'AMS Accounting Configuration'
    _inherit = 'res.config.settings'
    
    # Default Account Settings
    default_membership_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default Membership Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Default revenue account for membership products'
    )
    
    default_publication_revenue_account_id = fields.Many2one(
        'account.account', 
        string='Default Publication Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Default revenue account for publication products'
    )
    
    default_chapter_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default Chapter Revenue Account', 
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Default revenue account for chapter products'
    )
    
    default_subscription_ar_account_id = fields.Many2one(
        'account.account',
        string='Default Subscription A/R Account',
        domain="[('account_type', '=', 'asset_receivable')]", 
        help='Default accounts receivable account for subscriptions'
    )
    
    default_deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Default deferred revenue account for prepaid subscriptions'
    )
    
    default_cash_account_id = fields.Many2one(
        'account.account',
        string='Default Cash Account',
        domain="[('account_type', '=', 'asset_cash')]",
        help='Default cash account for subscription payments'
    )
    
    # AMS Integration Settings
    auto_create_journal_entries = fields.Boolean(
        string='Auto-Create AMS Journal Entries',
        default=True,
        help='Automatically create journal entries for AMS transactions'
    )
    
    use_product_specific_accounts = fields.Boolean(
        string='Use Product-Specific Accounts',
        default=True,
        help='Use accounts configured on individual products vs company defaults'
    )
    
    ams_journal_id = fields.Many2one(
        'account.journal',
        string='AMS Journal',
        domain="[('type', 'in', ['sale', 'general'])]",
        help='Journal to use for AMS-specific entries'
    )
    
    # Statistics
    total_ams_products = fields.Integer(
        string='Total AMS Products',
        compute='_compute_ams_stats',
        help='Number of products with AMS accounting enabled'
    )
    
    unconfigured_products = fields.Integer(
        string='Unconfigured Products',
        compute='_compute_ams_stats', 
        help='Number of AMS products without proper account configuration'
    )
    
    def _compute_ams_stats(self):
        """Compute AMS accounting statistics"""
        for config in self:
            config.total_ams_products = self.env['product.template'].search_count([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True)
            ])
            
            config.unconfigured_products = self.env['product.template'].search_count([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ])
    
    def action_setup_ams_accounts(self):
        """Launch setup wizard for AMS chart of accounts"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Setup AMS Chart of Accounts',
            'res_model': 'ams.accounting.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_configure_all_products(self):
        """Auto-configure all unconfigured AMS products"""
        unconfigured = self.env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('use_ams_accounting', '=', True),
            ('ams_accounts_configured', '=', False)
        ])
        
        for product in unconfigured:
            product._set_default_ams_accounts()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification', 
            'params': {
                'message': f'Configured {len(unconfigured)} AMS products automatically',
                'type': 'success',
            }
        }
    
    def action_view_unconfigured_products(self):
        """View products that need account configuration"""
        return {
            'name': 'Unconfigured AMS Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ],
            'context': {'search_default_unconfigured': 1}
        }