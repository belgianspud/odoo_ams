# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    """Enhanced Product Template with GL Account Configuration"""
    _inherit = 'product.template'
    
    # =============================================================================
    # AMS ACCOUNTING FIELDS
    # =============================================================================
    
    # Revenue Accounts
    ams_revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_other']), ('company_id', '=', current_company_id)]",
        help='General Ledger account for revenue recognition when this product is sold'
    )
    
    ams_deferred_account_id = fields.Many2one(
        'account.account', 
        string='Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current'), ('company_id', '=', current_company_id)]",
        help='Account for deferred/unearned revenue (used for prepaid subscriptions)'
    )
    
    # Receivables & Cash
    ams_receivable_account_id = fields.Many2one(
        'account.account',
        string='A/R Account', 
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', current_company_id)]",
        help='Accounts Receivable account for this product'
    )
    
    ams_cash_account_id = fields.Many2one(
        'account.account',
        string='Cash Account',
        domain="[('account_type', '=', 'asset_cash'), ('company_id', '=', current_company_id)]", 
        help='Cash account to use when payments are received'
    )
    
    # Expense Accounts
    ams_expense_account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        domain="[('account_type', '=', 'expense'), ('company_id', '=', current_company_id)]",
        help='Expense account for costs related to this product'
    )
    
    # Additional Accounting Configuration
    use_ams_accounting = fields.Boolean(
        string='Use AMS Accounting',
        default=False,
        help='Enable AMS-specific accounting for this product'
    )
    
    ams_accounting_notes = fields.Text(
        string='Accounting Notes',
        help='Internal notes about accounting treatment for this product'
    )
    
    # Computed fields for validation
    ams_accounts_configured = fields.Boolean(
        string='AMS Accounts Configured',
        compute='_compute_ams_accounts_configured',
        help='All required AMS accounts are configured'
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('ams_revenue_account_id', 'ams_receivable_account_id', 'is_subscription_product')
    def _compute_ams_accounts_configured(self):
        """Check if required AMS accounts are configured"""
        for product in self:
            if product.is_subscription_product and product.use_ams_accounting:
                # For subscription products, we need at least revenue and A/R accounts
                product.ams_accounts_configured = bool(
                    product.ams_revenue_account_id and 
                    product.ams_receivable_account_id
                )
            else:
                product.ams_accounts_configured = True  # Not required
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Auto-enable AMS accounting for subscription products"""
        if self.is_subscription_product:
            self.use_ams_accounting = True
            # Set default accounts based on subscription type
            self._set_default_ams_accounts()
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Update default accounts when subscription type changes"""
        if self.ams_product_type != 'none':
            self._set_default_ams_accounts()
    
    def _set_default_ams_accounts(self):
        """Set default AMS accounts based on product type"""
        if not self.ams_product_type or self.ams_product_type == 'none':
            return
        
        # Get suggested accounts based on subscription type
        account_mapping = self._get_default_account_mapping()
        subscription_type = self.ams_product_type
        
        if subscription_type in account_mapping:
            defaults = account_mapping[subscription_type]
            
            # Set revenue account if not already set
            if not self.ams_revenue_account_id and defaults.get('revenue_category'):
                revenue_account = self._find_account_by_category(defaults['revenue_category'])
                if revenue_account:
                    self.ams_revenue_account_id = revenue_account.id
            
            # Set A/R account if not already set
            if not self.ams_receivable_account_id:
                ar_account = self._find_account_by_category('subscription_ar')
                if ar_account:
                    self.ams_receivable_account_id = ar_account.id
            
            # Set deferred account for annual subscriptions
            if self.subscription_period == 'annual' and not self.ams_deferred_account_id:
                deferred_account = self._find_account_by_category('deferred_revenue')
                if deferred_account:
                    self.ams_deferred_account_id = deferred_account.id
    
    def _get_default_account_mapping(self):
        """Map subscription types to default account categories"""
        return {
            'individual': {
                'revenue_category': 'membership_revenue',
                'expense_category': 'membership_expense',
            },
            'enterprise': {
                'revenue_category': 'membership_revenue', 
                'expense_category': 'membership_expense',
            },
            'chapter': {
                'revenue_category': 'chapter_revenue',
                'expense_category': 'chapter_expense', 
            },
            'publication': {
                'revenue_category': 'publication_revenue',
                'expense_category': 'publication_expense',
            },
        }
    
    def _find_account_by_category(self, category):
        """Find an account by AMS category"""
        return self.env['account.account'].search([
            ('ams_account_category', '=', category),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
    
    # =============================================================================
    # VALIDATION METHODS  
    # =============================================================================
    
    @api.constrains('ams_revenue_account_id', 'ams_receivable_account_id')
    def _check_ams_accounts(self):
        """Validate AMS account configuration"""
        for product in self:
            if product.is_subscription_product and product.use_ams_accounting:
                if not product.ams_revenue_account_id:
                    raise UserError(_(
                        "Revenue Account is required for subscription product '%s'"
                    ) % product.name)
                
                if not product.ams_receivable_account_id:
                    raise UserError(_(
                        "A/R Account is required for subscription product '%s'"  
                    ) % product.name)
                
                # Validate account types
                if product.ams_revenue_account_id.account_type not in ['income', 'income_other']:
                    raise UserError(_(
                        "Revenue Account must be an income account for product '%s'"
                    ) % product.name)
                
                if product.ams_receivable_account_id.account_type != 'asset_receivable':
                    raise UserError(_(
                        "A/R Account must be a receivable account for product '%s'"
                    ) % product.name)
    
    # =============================================================================
    # ACTION METHODS
    # =============================================================================
    
    def action_configure_ams_accounts(self):
        """Open wizard to configure AMS accounts for this product"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure AMS Accounts',
            'res_model': 'ams.product.account.wizard', 
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_ams_product_type': self.ams_product_type,
            }
        }
    
    def action_auto_configure_accounts(self):
        """Automatically configure accounts based on product type"""
        for product in self:
            if product.is_subscription_product:
                product._set_default_ams_accounts()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'AMS accounts configured automatically',
                'type': 'success',
            }
        }
    
    def get_ams_journal_entry_data(self, amount, invoice=None):
        """Get journal entry data for AMS transactions"""
        self.ensure_one()
        
        if not self.use_ams_accounting or not self.ams_accounts_configured:
            return {}
        
        entry_data = {
            'product_id': self.id,
            'product_name': self.name,
            'subscription_type': self.ams_product_type,
            'amount': amount,
            'accounts': {
                'revenue': self.ams_revenue_account_id.id if self.ams_revenue_account_id else None,
                'receivable': self.ams_receivable_account_id.id if self.ams_receivable_account_id else None,
                'cash': self.ams_cash_account_id.id if self.ams_cash_account_id else None,
                'deferred': self.ams_deferred_account_id.id if self.ams_deferred_account_id else None,
                'expense': self.ams_expense_account_id.id if self.ams_expense_account_id else None,
            },
            'invoice': invoice.id if invoice else None,
        }
        
        return entry_data