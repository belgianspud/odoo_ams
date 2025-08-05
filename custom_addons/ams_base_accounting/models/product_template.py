# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # ==============================================
    # REVENUE RECOGNITION FIELDS
    # ==============================================
    
    revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_membership', 'income_chapter', 'income_publication', 'income_other']), ('company_id', '=', current_company_id)]",
        help='Account used for recognizing revenue from this product'
    )
    
    deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', current_company_id)]",
        help='Account used for storing unearned revenue (for subscription products)'
    )
    
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Recognize Immediately'),
        ('deferred', 'Deferred Recognition'),
        ('subscription', 'Subscription-based'),
    ], string='Revenue Recognition Method', 
       default='immediate',
       help='How revenue should be recognized for this product')
    
    # ==============================================
    # RECEIVABLES & CASH FIELDS
    # ==============================================
    
    receivable_account_id = fields.Many2one(
        'ams.account.account',
        string='Accounts Receivable Account',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', current_company_id)]",
        help='Account for tracking money owed by customers'
    )
    
    cash_account_id = fields.Many2one(
        'ams.account.account',
        string='Cash Account',
        domain="[('account_type', 'in', ['asset_cash', 'asset_current']), ('company_id', '=', current_company_id)]",
        help='Account where payments for this product are deposited'
    )
    
    payment_terms_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        help='Default payment terms for this product'
    )
    
    # ==============================================
    # COST MANAGEMENT FIELDS
    # ==============================================
    
    expense_account_id = fields.Many2one(
        'ams.account.account',
        string='Expense Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), ('company_id', '=', current_company_id)]",
        help='Account for expenses related to this product'
    )
    
    cogs_account_id = fields.Many2one(
        'ams.account.account',
        string='Cost of Goods Sold Account',
        domain="[('account_type', '=', 'expense_direct_cost'), ('company_id', '=', current_company_id)]",
        help='Account for cost of goods sold (for physical products)'
    )
    
    inventory_account_id = fields.Many2one(
        'ams.account.account',
        string='Inventory Account',
        domain="[('account_type', 'in', ['asset_current', 'asset_non_current']), ('company_id', '=', current_company_id)]",
        help='Account for inventory valuation (for physical products)'
    )
    
    standard_cost = fields.Float(
        string='Standard Cost',
        digits='Product Price',
        help='Standard cost for this product'
    )
    
    # ==============================================
    # OTHER FINANCIAL SETTINGS
    # ==============================================
    
    bad_debt_account_id = fields.Many2one(
        'ams.account.account',
        string='Bad Debt Account',
        domain="[('account_type', '=', 'expense'), ('company_id', '=', current_company_id)]",
        help='Account for recording bad debt expenses'
    )
    
    discount_account_id = fields.Many2one(
        'ams.account.account',
        string='Discount Account',
        domain="[('account_type', 'in', ['expense', 'income']), ('company_id', '=', current_company_id)]",
        help='Account for recording discounts given'
    )
    
    # ==============================================
    # AMS-SPECIFIC FINANCIAL SETTINGS
    # ==============================================
    
    financial_setup_complete = fields.Boolean(
        string='Financial Setup Complete',
        compute='_compute_financial_setup_complete',
        help='Indicates if all required financial accounts are configured'
    )
    
    requires_deferred_revenue = fields.Boolean(
        string='Requires Deferred Revenue',
        compute='_compute_requires_deferred_revenue',
        help='This product requires deferred revenue accounting'
    )
    
    # ==============================================
    # COMPANY-RELATED FIELDS
    # ==============================================
    
    current_company_id = fields.Many2one(
        'res.company',
        string='Current Company',
        compute='_compute_current_company',
        help='Current company for domain filtering'
    )
    
    @api.depends()
    def _compute_current_company(self):
        """Compute current company for domain filtering"""
        for product in self:
            product.current_company_id = self.env.company.id
    
    @api.depends('is_subscription_product', 'ams_product_type', 'subscription_period')
    def _compute_requires_deferred_revenue(self):
        """Determine if product requires deferred revenue accounting"""
        for product in self:
            # Subscription products with periods longer than monthly typically need deferred revenue
            product.requires_deferred_revenue = (
                product.is_subscription_product and 
                product.subscription_period in ['quarterly', 'semi_annual', 'annual']
            )
    
    @api.depends(
        'revenue_account_id', 'deferred_revenue_account_id', 'receivable_account_id',
        'cash_account_id', 'requires_deferred_revenue', 'is_subscription_product'
    )
    def _compute_financial_setup_complete(self):
        """Check if financial setup is complete"""
        for product in self:
            required_fields = ['revenue_account_id', 'receivable_account_id', 'cash_account_id']
            
            # Add deferred revenue account if required
            if product.requires_deferred_revenue:
                required_fields.append('deferred_revenue_account_id')
            
            # Check if all required fields are set
            complete = all(getattr(product, field) for field in required_fields)
            product.financial_setup_complete = complete
    
    @api.onchange('is_subscription_product', 'ams_product_type', 'subscription_period')
    def _onchange_subscription_settings(self):
        """Set smart defaults when subscription settings change"""
        if self.is_subscription_product:
            # Set revenue recognition method
            if self.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                self.revenue_recognition_method = 'subscription'
            else:
                self.revenue_recognition_method = 'deferred'
            
            # Set smart account defaults based on AMS product type
            self._set_default_accounts()
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Set account defaults based on AMS product type"""
        if self.ams_product_type != 'none':
            self._set_default_accounts()
    
    def _set_default_accounts(self):
        """Set default accounts based on product type"""
        company_id = self.env.company.id
        account_obj = self.env['ams.account.account']
        
        # Mapping of AMS product types to account types
        account_mappings = {
            'individual': {
                'revenue_account': ('income_membership', '4100'),
                'deferred_revenue_account': ('liability_deferred_revenue', '2400'),
            },
            'enterprise': {
                'revenue_account': ('income_membership', '4110'),
                'deferred_revenue_account': ('liability_deferred_revenue', '2400'),
            },
            'chapter': {
                'revenue_account': ('income_chapter', '4200'),
                'deferred_revenue_account': ('liability_deferred_revenue', '2420'),
            },
            'publication': {
                'revenue_account': ('income_publication', '4300'),
                'deferred_revenue_account': ('liability_deferred_revenue', '2410'),
            },
        }
        
        # Get mapping for current product type
        mapping = account_mappings.get(self.ams_product_type, {})
        
        # Set revenue account
        if not self.revenue_account_id and 'revenue_account' in mapping:
            account_type, fallback_code = mapping['revenue_account']
            account = account_obj.search([
                ('account_type', '=', account_type),
                ('company_id', '=', company_id)
            ], limit=1)
            if not account:
                # Try fallback by code
                account = account_obj.search([
                    ('code', '=', fallback_code),
                    ('company_id', '=', company_id)
                ], limit=1)
            if account:
                self.revenue_account_id = account.id
        
        # Set deferred revenue account for subscriptions
        if (not self.deferred_revenue_account_id and 
            self.requires_deferred_revenue and 
            'deferred_revenue_account' in mapping):
            
            account_type, fallback_code = mapping['deferred_revenue_account']
            account = account_obj.search([
                ('account_type', '=', account_type),
                ('company_id', '=', company_id)
            ], limit=1)
            if not account:
                # Try fallback by code
                account = account_obj.search([
                    ('code', '=', fallback_code),
                    ('company_id', '=', company_id)
                ], limit=1)
            if account:
                self.deferred_revenue_account_id = account.id
        
        # Set common defaults if not already set
        if not self.receivable_account_id:
            ar_account = account_obj.search([
                ('account_type', '=', 'asset_receivable'),
                ('company_id', '=', company_id)
            ], limit=1)
            if ar_account:
                self.receivable_account_id = ar_account.id
        
        if not self.cash_account_id:
            cash_account = account_obj.search([
                ('account_type', '=', 'asset_cash'),
                ('company_id', '=', company_id)
            ], limit=1)
            if cash_account:
                self.cash_account_id = cash_account.id
    
    def action_setup_financial_accounts(self):
        """Action to help set up financial accounts"""
        self.ensure_one()
        
        return {
            'name': f'Financial Setup - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.financial.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_product_name': self.name,
                'default_ams_product_type': self.ams_product_type,
                'default_is_subscription_product': self.is_subscription_product,
                'default_requires_deferred_revenue': self.requires_deferred_revenue,
            }
        }
    
    def action_create_missing_accounts(self):
        """Create missing accounts for this product"""
        self.ensure_one()
        
        if self.financial_setup_complete:
            raise UserError('Financial setup is already complete for this product')
        
        account_obj = self.env['ams.account.account']
        company_id = self.env.company.id
        created_accounts = []
        
        # Create revenue account if missing
        if not self.revenue_account_id:
            account_vals = {
                'name': f'{self.name} Revenue',
                'code': account_obj._generate_account_code('income'),
                'account_type': 'income',
                'company_id': company_id,
                'ams_category': self.ams_product_type if self.ams_product_type in ['membership', 'chapter', 'publication'] else 'general',
            }
            revenue_account = account_obj.create(account_vals)
            self.revenue_account_id = revenue_account.id
            created_accounts.append(revenue_account.name)
        
        # Create deferred revenue account if needed
        if self.requires_deferred_revenue and not self.deferred_revenue_account_id:
            account_vals = {
                'name': f'{self.name} Deferred Revenue',
                'code': account_obj._generate_account_code('liability_deferred_revenue'),
                'account_type': 'liability_deferred_revenue',
                'company_id': company_id,
                'ams_category': self.ams_product_type if self.ams_product_type in ['membership', 'chapter', 'publication'] else 'general',
            }
            deferred_account = account_obj.create(account_vals)
            self.deferred_revenue_account_id = deferred_account.id
            created_accounts.append(deferred_account.name)
        
        if created_accounts:
            message = f"Created accounts: {', '.join(created_accounts)}"
            self.message_post(body=message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError('No accounts needed to be created')
    
    @api.constrains('revenue_recognition_method', 'is_subscription_product')
    def _check_revenue_recognition_method(self):
        """Validate revenue recognition method"""
        for product in self:
            if (product.revenue_recognition_method == 'subscription' and 
                not product.is_subscription_product):
                raise ValidationError(
                    'Subscription-based revenue recognition can only be used with subscription products'
                )
    
    def get_revenue_account(self):
        """Get the appropriate revenue account for this product"""
        self.ensure_one()
        if not self.revenue_account_id:
            raise UserError(f'No revenue account configured for product {self.name}')
        return self.revenue_account_id
    
    def get_deferred_revenue_account(self):
        """Get the deferred revenue account for this product"""
        self.ensure_one()
        if self.requires_deferred_revenue and not self.deferred_revenue_account_id:
            raise UserError(f'No deferred revenue account configured for product {self.name}')
        return self.deferred_revenue_account_id
    
    def get_receivable_account(self):
        """Get the receivable account for this product"""
        self.ensure_one()
        if not self.receivable_account_id:
            # Fall back to default receivable account
            default_ar = self.env['ams.account.account'].search([
                ('account_type', '=', 'asset_receivable'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if not default_ar:
                raise UserError('No receivable account configured')
            return default_ar
        return self.receivable_account_id
    
    def get_cash_account(self):
        """Get the cash account for this product"""
        self.ensure_one()
        if not self.cash_account_id:
            # Fall back to default cash account
            default_cash = self.env['ams.account.account'].search([
                ('account_type', '=', 'asset_cash'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if not default_cash:
                raise UserError('No cash account configured')
            return default_cash
        return self.cash_account_id