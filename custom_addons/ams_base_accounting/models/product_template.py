# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # ==============================================
    # AMS PRODUCT TYPE FIELDS
    # ==============================================
    
    ams_product_type = fields.Selection([
        ('none', 'Not AMS Product'),
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication'),
        ('event', 'Event'),
        ('general', 'General AMS Product'),
    ], string='AMS Product Type', default='none',
       help='Type of AMS product for accounting and membership management')
    
    is_subscription_product = fields.Boolean(
        string='Is Subscription Product',
        default=False,
        help='This product is used for subscriptions'
    )
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Default Subscription Period',
       help='Default subscription period for this product')
    
    auto_renew = fields.Boolean(
        string='Auto-Renew by Default',
        default=True,
        help='Subscriptions using this product auto-renew by default'
    )
    
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
    # OTHER FINANCIAL FIELDS
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
    
    expense_account_id = fields.Many2one(
        'ams.account.account',
        string='Expense Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), ('company_id', '=', current_company_id)]",
        help='Account for expenses related to this product'
    )
    
    # ==============================================
    # FINANCIAL STATUS FIELDS
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
                product.subscription_period in ['quarterly', 'semi_annual', 'annual', 'biennial']
            )
    
    @api.depends('revenue_account_id', 'deferred_revenue_account_id', 'receivable_account_id', 'requires_deferred_revenue')
    def _compute_financial_setup_complete(self):
        """Check if financial setup is complete"""
        for product in self:
            if product.ams_product_type == 'none':
                product.financial_setup_complete = True  # Non-AMS products don't need AMS setup
                continue
                
            required_fields = ['revenue_account_id']
            
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
            if self.subscription_period in ['quarterly', 'semi_annual', 'annual', 'biennial']:
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
        if self.ams_product_type == 'none':
            return
            
        company_id = self.env.company.id
        account_obj = self.env['ams.account.account']
        
        # Try to get company default accounts safely
        company = self.env.company
        
        # Mapping of AMS product types to account lookups
        account_type_mapping = {
            'individual': 'income_membership',
            'enterprise': 'income_membership',
            'chapter': 'income_chapter',
            'publication': 'income_publication',
            'event': 'income_other',
            'general': 'income',
        }
        
        # Set revenue account
        if not self.revenue_account_id:
            account_type = account_type_mapping.get(self.ams_product_type, 'income')
            
            # Try to find appropriate account
            account = account_obj.search([
                ('account_type', '=', account_type),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if account:
                self.revenue_account_id = account.id
        
        # Set deferred revenue account for subscriptions
        if self.requires_deferred_revenue and not self.deferred_revenue_account_id:
            deferred_account = account_obj.search([
                ('account_type', '=', 'liability_deferred_revenue'),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if deferred_account:
                self.deferred_revenue_account_id = deferred_account.id
        
        # Set receivable account if not set
        if not self.receivable_account_id:
            ar_account = account_obj.search([
                ('account_type', '=', 'asset_receivable'),
                ('company_id', '=', company_id)
            ], limit=1)
            if ar_account:
                self.receivable_account_id = ar_account.id
        
        # Set cash account if not set
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
            'res_model': 'ams.product.financial.setup.wizard',
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