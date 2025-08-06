# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSProductFinancialSetupWizard(models.TransientModel):
    """Wizard to set up financial accounts for AMS products"""
    _name = 'ams.product.financial.wizard'
    _description = 'AMS Product Financial Setup Wizard'
    
    # ==============================================
    # PRODUCT INFORMATION
    # ==============================================
    
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        readonly=True
    )
    
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name',
        readonly=True
    )
    
    ams_product_type = fields.Selection(
        related='product_id.ams_product_type',
        string='AMS Product Type',
        readonly=True
    )
    
    is_subscription_product = fields.Boolean(
        related='product_id.is_subscription_product',
        string='Subscription Product',
        readonly=True
    )
    
    subscription_period = fields.Selection(
        related='product_id.subscription_period',
        string='Subscription Period',
        readonly=True
    )
    
    requires_deferred_revenue = fields.Boolean(
        string='Requires Deferred Revenue',
        compute='_compute_requires_deferred_revenue',
        help='This product requires deferred revenue accounting'
    )
    
    # ==============================================
    # SETUP OPTIONS
    # ==============================================
    
    setup_mode = fields.Selection([
        ('guided', 'Guided Setup (Recommended)'),
        ('manual', 'Manual Account Selection'),
        ('create_new', 'Create New Accounts'),
    ], string='Setup Mode', required=True, default='guided',
       help='How to configure financial accounts for this product')
    
    use_company_defaults = fields.Boolean(
        string='Use Company Defaults',
        default=True,
        help='Use company default accounts where appropriate'
    )
    
    # ==============================================
    # REVENUE RECOGNITION SETTINGS
    # ==============================================
    
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Recognize Immediately'),
        ('deferred', 'Deferred Recognition'),
        ('subscription', 'Subscription-based'),
    ], string='Revenue Recognition Method',
       help='How revenue should be recognized for this product')
    
    # ==============================================
    # ACCOUNT SELECTIONS
    # ==============================================
    
    # Revenue Accounts
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
    
    # Receivables & Cash
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
    
    # Cost Management
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
    
    # Other Financial Settings
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
    # ACCOUNT CREATION OPTIONS
    # ==============================================
    
    create_revenue_account = fields.Boolean(
        string='Create Revenue Account',
        help='Create a new revenue account for this product'
    )
    
    create_deferred_revenue_account = fields.Boolean(
        string='Create Deferred Revenue Account',
        help='Create a new deferred revenue account for this product'
    )
    
    new_revenue_account_name = fields.Char(
        string='New Revenue Account Name',
        help='Name for new revenue account'
    )
    
    new_deferred_revenue_account_name = fields.Char(
        string='New Deferred Revenue Account Name',
        help='Name for new deferred revenue account'
    )
    
    # ==============================================
    # HELPER FIELDS
    # ==============================================
    
    current_company_id = fields.Many2one(
        'res.company',
        string='Current Company',
        compute='_compute_current_company',
        help='Current company for domain filtering'
    )
    
    setup_summary = fields.Html(
        string='Setup Summary',
        compute='_compute_setup_summary',
        help='Summary of financial setup'
    )
    
    missing_accounts = fields.Text(
        string='Missing Accounts',
        compute='_compute_missing_accounts',
        help='List of accounts that need to be configured'
    )
    
    recommended_accounts = fields.Html(
        string='Recommended Accounts',
        compute='_compute_recommended_accounts',
        help='Recommended account configuration for this product'
    )
    
    @api.depends()
    def _compute_current_company(self):
        """Compute current company for domain filtering"""
        for wizard in self:
            wizard.current_company_id = self.env.company.id
    
    @api.depends('is_subscription_product', 'subscription_period', 'ams_product_type')
    def _compute_requires_deferred_revenue(self):
        """Determine if product requires deferred revenue accounting"""
        for wizard in self:
            wizard.requires_deferred_revenue = (
                wizard.is_subscription_product and 
                wizard.subscription_period in ['quarterly', 'semi_annual', 'annual']
            )
    
    @api.depends('setup_mode', 'revenue_account_id', 'deferred_revenue_account_id', 'requires_deferred_revenue')
    def _compute_missing_accounts(self):
        """Compute list of missing required accounts"""
        for wizard in self:
            missing = []
            
            if not wizard.revenue_account_id and not wizard.create_revenue_account:
                missing.append('Revenue Account')
            
            if wizard.requires_deferred_revenue and not wizard.deferred_revenue_account_id and not wizard.create_deferred_revenue_account:
                missing.append('Deferred Revenue Account')
            
            if not wizard.receivable_account_id:
                missing.append('Receivable Account (recommended)')
            
            if not wizard.cash_account_id:
                missing.append('Cash Account (recommended)')
            
            wizard.missing_accounts = '\n'.join(missing) if missing else 'All required accounts configured'
    
    @api.depends('ams_product_type', 'is_subscription_product', 'use_company_defaults')
    def _compute_recommended_accounts(self):
        """Compute recommended account configuration"""
        for wizard in self:
            recommendations = ['<h5>Recommended Account Configuration:</h5>']
            
            if wizard.ams_product_type == 'individual':
                recommendations.append('<p><strong>Individual Membership Product</strong></p>')
                recommendations.append('<ul>')
                recommendations.append('<li>Revenue Account: Individual Membership Revenue</li>')
                if wizard.requires_deferred_revenue:
                    recommendations.append('<li>Deferred Revenue: Membership Deferred Revenue</li>')
                recommendations.append('<li>Recognition Method: Subscription-based</li>')
                recommendations.append('</ul>')
                
            elif wizard.ams_product_type == 'enterprise':
                recommendations.append('<p><strong>Enterprise Membership Product</strong></p>')
                recommendations.append('<ul>')
                recommendations.append('<li>Revenue Account: Enterprise Membership Revenue</li>')
                if wizard.requires_deferred_revenue:
                    recommendations.append('<li>Deferred Revenue: Membership Deferred Revenue</li>')
                recommendations.append('<li>Recognition Method: Subscription-based</li>')
                recommendations.append('</ul>')
                
            elif wizard.ams_product_type == 'chapter':
                recommendations.append('<p><strong>Chapter Product</strong></p>')
                recommendations.append('<ul>')
                recommendations.append('<li>Revenue Account: Chapter Revenue</li>')
                if wizard.requires_deferred_revenue:
                    recommendations.append('<li>Deferred Revenue: Chapter Deferred Revenue</li>')
                recommendations.append('<li>Recognition Method: Subscription-based</li>')
                recommendations.append('</ul>')
                
            elif wizard.ams_product_type == 'publication':
                recommendations.append('<p><strong>Publication Product</strong></p>')
                recommendations.append('<ul>')
                recommendations.append('<li>Revenue Account: Publication Revenue</li>')
                if wizard.requires_deferred_revenue:
                    recommendations.append('<li>Deferred Revenue: Publication Deferred Revenue</li>')
                recommendations.append('<li>Recognition Method: Subscription-based</li>')
                recommendations.append('</ul>')
            else:
                recommendations.append('<p><strong>General Product</strong></p>')
                recommendations.append('<ul>')
                recommendations.append('<li>Revenue Account: General Revenue</li>')
                recommendations.append('<li>Recognition Method: Immediate</li>')
                recommendations.append('</ul>')
            
            if wizard.use_company_defaults:
                recommendations.append('<p><em>Using company default accounts for receivables and cash.</em></p>')
            
            wizard.recommended_accounts = ''.join(recommendations)
    
    @api.depends('revenue_account_id', 'deferred_revenue_account_id', 'revenue_recognition_method')
    def _compute_setup_summary(self):
        """Compute setup summary"""
        for wizard in self:
            summary_parts = ['<h4>Financial Setup Summary</h4>']
            summary_parts.append(f'<p><strong>Product:</strong> {wizard.product_name}</p>')
            summary_parts.append(f'<p><strong>Product Type:</strong> {dict(wizard.product_id._fields["ams_product_type"].selection).get(wizard.ams_product_type, "None")}</p>')
            
            if wizard.is_subscription_product:
                summary_parts.append(f'<p><strong>Subscription Period:</strong> {dict(wizard.product_id._fields["subscription_period"].selection).get(wizard.subscription_period, "None")}</p>')
            
            summary_parts.append('<h5>Account Configuration:</h5>')
            summary_parts.append('<ul>')
            
            if wizard.revenue_account_id:
                summary_parts.append(f'<li><strong>Revenue:</strong> {wizard.revenue_account_id.name}</li>')
            elif wizard.create_revenue_account:
                summary_parts.append(f'<li><strong>Revenue:</strong> Will create "{wizard.new_revenue_account_name}"</li>')
            
            if wizard.requires_deferred_revenue:
                if wizard.deferred_revenue_account_id:
                    summary_parts.append(f'<li><strong>Deferred Revenue:</strong> {wizard.deferred_revenue_account_id.name}</li>')
                elif wizard.create_deferred_revenue_account:
                    summary_parts.append(f'<li><strong>Deferred Revenue:</strong> Will create "{wizard.new_deferred_revenue_account_name}"</li>')
            
            if wizard.receivable_account_id:
                summary_parts.append(f'<li><strong>Receivable:</strong> {wizard.receivable_account_id.name}</li>')
            
            if wizard.cash_account_id:
                summary_parts.append(f'<li><strong>Cash:</strong> {wizard.cash_account_id.name}</li>')
            
            summary_parts.append('</ul>')
            
            if wizard.revenue_recognition_method:
                method_name = dict(wizard._fields['revenue_recognition_method'].selection)[wizard.revenue_recognition_method]
                summary_parts.append(f'<p><strong>Revenue Recognition:</strong> {method_name}</p>')
            
            wizard.setup_summary = ''.join(summary_parts)
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        product_id = self.env.context.get('default_product_id')
        if product_id:
            product = self.env['product.template'].browse(product_id)
            
            # Set revenue recognition method based on product
            if product.is_subscription_product:
                if product.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                    res['revenue_recognition_method'] = 'subscription'
                else:
                    res['revenue_recognition_method'] = 'deferred'
            else:
                res['revenue_recognition_method'] = 'immediate'
        
        return res
    
    @api.onchange('setup_mode')
    def _onchange_setup_mode(self):
        """Update options when setup mode changes"""
        if self.setup_mode == 'guided':
            self.use_company_defaults = True
            self._set_guided_defaults()
        elif self.setup_mode == 'create_new':
            self._set_create_new_defaults()
    
    @api.onchange('use_company_defaults')
    def _onchange_use_company_defaults(self):
        """Set company defaults when enabled"""
        if self.use_company_defaults:
            self._set_company_defaults()
    
    @api.onchange('ams_product_type', 'requires_deferred_revenue')
    def _onchange_product_type(self):
        """Set account defaults based on product type"""
        if self.setup_mode == 'guided':
            self._set_guided_defaults()
    
    def _set_guided_defaults(self):
        """Set guided setup defaults"""
        company = self.env.company
        
        # Set revenue recognition method
        if self.is_subscription_product:
            if self.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                self.revenue_recognition_method = 'subscription'
            else:
                self.revenue_recognition_method = 'deferred'
        else:
            self.revenue_recognition_method = 'immediate'
        
        # Set accounts based on product type
        if self.ams_product_type == 'individual':
            self.revenue_account_id = company.individual_membership_revenue_account_id
            if self.requires_deferred_revenue:
                self.deferred_revenue_account_id = company.membership_deferred_revenue_account_id
        elif self.ams_product_type == 'enterprise':
            self.revenue_account_id = company.enterprise_membership_revenue_account_id
            if self.requires_deferred_revenue:
                self.deferred_revenue_account_id = company.membership_deferred_revenue_account_id
        elif self.ams_product_type == 'chapter':
            self.revenue_account_id = company.chapter_revenue_account_id
            if self.requires_deferred_revenue:
                self.deferred_revenue_account_id = company.chapter_deferred_revenue_account_id
        elif self.ams_product_type == 'publication':
            self.revenue_account_id = company.publication_revenue_account_id
            if self.requires_deferred_revenue:
                self.deferred_revenue_account_id = company.publication_deferred_revenue_account_id
        else:
            self.revenue_account_id = company.ams_default_revenue_account_id
            if self.requires_deferred_revenue:
                self.deferred_revenue_account_id = company.ams_default_deferred_revenue_account_id
        
        # Set company defaults
        self._set_company_defaults()
    
    def _set_company_defaults(self):
        """Set company default accounts"""
        company = self.env.company
        
        if not self.receivable_account_id:
            self.receivable_account_id = company.ams_default_receivable_account_id
        
        if not self.cash_account_id:
            self.cash_account_id = company.ams_default_cash_account_id
        
        if not self.bad_debt_account_id:
            self.bad_debt_account_id = company.ams_bad_debt_account_id
        
        if not self.discount_account_id:
            self.discount_account_id = company.ams_discount_account_id
    
    def _set_create_new_defaults(self):
        """Set defaults for creating new accounts"""
        if not self.new_revenue_account_name:
            self.new_revenue_account_name = f'{self.product_name} Revenue'
        
        if self.requires_deferred_revenue and not self.new_deferred_revenue_account_name:
            self.new_deferred_revenue_account_name = f'{self.product_name} Deferred Revenue'
        
        self.create_revenue_account = True
        if self.requires_deferred_revenue:
            self.create_deferred_revenue_account = True
    
    def action_apply_financial_setup(self):
        """Apply financial setup to the product"""
        self.ensure_one()
        
        if not self.product_id:
            raise UserError('Product is required')
        
        created_accounts = []
        
        try:
            # Create new accounts if requested
            if self.create_revenue_account:
                revenue_account = self._create_revenue_account()
                created_accounts.append(revenue_account)
                self.revenue_account_id = revenue_account.id
            
            if self.create_deferred_revenue_account:
                deferred_account = self._create_deferred_revenue_account()
                created_accounts.append(deferred_account)
                self.deferred_revenue_account_id = deferred_account.id
            
            # Update product with account settings
            self._update_product_accounts()
            
            return self._show_success_message(created_accounts)
            
        except Exception as e:
            return self._show_error_message(str(e), created_accounts)
    
    def _create_revenue_account(self):
        """Create revenue account for the product"""
        account_obj = self.env['ams.account.account']
        
        # Determine account type based on product type
        account_type_mapping = {
            'individual': 'income_membership',
            'enterprise': 'income_membership',
            'chapter': 'income_chapter',
            'publication': 'income_publication',
        }
        
        account_type = account_type_mapping.get(self.ams_product_type, 'income')
        
        # Generate account code
        code = account_obj._generate_account_code(account_type)
        
        account_vals = {
            'name': self.new_revenue_account_name,
            'code': code,
            'account_type': account_type,
            'company_id': self.env.company.id,
            'ams_category': self.ams_product_type if self.ams_product_type in ['membership', 'chapter', 'publication'] else 'general',
        }
        
        return account_obj.create(account_vals)
    
    def _create_deferred_revenue_account(self):
        """Create deferred revenue account for the product"""
        account_obj = self.env['ams.account.account']
        
        # Generate account code
        code = account_obj._generate_account_code('liability_deferred_revenue')
        
        account_vals = {
            'name': self.new_deferred_revenue_account_name,
            'code': code,
            'account_type': 'liability_deferred_revenue',
            'company_id': self.env.company.id,
            'ams_category': self.ams_product_type if self.ams_product_type in ['membership', 'chapter', 'publication'] else 'general',
        }
        
        return account_obj.create(account_vals)
    
    def _update_product_accounts(self):
        """Update product with selected accounts"""
        product_vals = {
            'revenue_recognition_method': self.revenue_recognition_method,
        }
        
        # Set accounts
        if self.revenue_account_id:
            product_vals['revenue_account_id'] = self.revenue_account_id.id
        
        if self.deferred_revenue_account_id:
            product_vals['deferred_revenue_account_id'] = self.deferred_revenue_account_id.id
        
        if self.receivable_account_id:
            product_vals['receivable_account_id'] = self.receivable_account_id.id
        
        if self.cash_account_id:
            product_vals['cash_account_id'] = self.cash_account_id.id
        
        if self.expense_account_id:
            product_vals['expense_account_id'] = self.expense_account_id.id
        
        if self.cogs_account_id:
            product_vals['cogs_account_id'] = self.cogs_account_id.id
        
        if self.bad_debt_account_id:
            product_vals['bad_debt_account_id'] = self.bad_debt_account_id.id
        
        if self.discount_account_id:
            product_vals['discount_account_id'] = self.discount_account_id.id
        
        self.product_id.write(product_vals)
    
    def _show_success_message(self, created_accounts):
        """Show success message"""
        message_parts = [f'<h4>Financial Setup Complete for {self.product_name}!</h4>']
        
        if created_accounts:
            message_parts.append(f'<p><strong>Created {len(created_accounts)} new accounts:</strong></p>')
            message_parts.append('<ul>')
            for account in created_accounts:
                message_parts.append(f'<li>[{account.code}] {account.name}</li>')
            message_parts.append('</ul>')
        
        message_parts.append('<p><strong>Configured Accounts:</strong></p>')
        message_parts.append('<ul>')
        if self.revenue_account_id:
            message_parts.append(f'<li>Revenue: {self.revenue_account_id.name}</li>')
        if self.deferred_revenue_account_id:
            message_parts.append(f'<li>Deferred Revenue: {self.deferred_revenue_account_id.name}</li>')
        if self.receivable_account_id:
            message_parts.append(f'<li>Receivable: {self.receivable_account_id.name}</li>')
        if self.cash_account_id:
            message_parts.append(f'<li>Cash: {self.cash_account_id.name}</li>')
        message_parts.append('</ul>')
        
        recognition_method = dict(self._fields['revenue_recognition_method'].selection)[self.revenue_recognition_method]
        message_parts.append(f'<p><strong>Revenue Recognition Method:</strong> {recognition_method}</p>')
        
        message_parts.append('<p>Your product is now ready for subscription accounting!</p>')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Setup Complete!',
                'message': ''.join(message_parts),
                'type': 'success',
                'sticky': True,
            }
        }
    
    def _show_error_message(self, error, created_accounts):
        """Show error message"""
        message_parts = [f'<h4>Error Setting Up {self.product_name}</h4>']
        message_parts.append(f'<p><strong>Error:</strong> {error}</p>')
        
        if created_accounts:
            message_parts.append(f'<p>Successfully created {len(created_accounts)} accounts before error:</p>')
            message_parts.append('<ul>')
            for account in created_accounts:
                message_parts.append(f'<li>[{account.code}] {account.name}</li>')
            message_parts.append('</ul>')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Setup Error',
                'message': ''.join(message_parts),
                'type': 'danger',
                'sticky': True,
            }
        }
    
    def action_validate_configuration(self):
        """Validate the current configuration"""
        self.ensure_one()
        
        issues = []
        warnings = []
        
        # Check required accounts
        if not self.revenue_account_id and not self.create_revenue_account:
            issues.append('Revenue account is required')
        
        if self.requires_deferred_revenue and not self.deferred_revenue_account_id and not self.create_deferred_revenue_account:
            issues.append('Deferred revenue account is required for subscription products')
        
        if not self.receivable_account_id:
            warnings.append('Receivable account is recommended')
        
        if not self.cash_account_id:
            warnings.append('Cash account is recommended')
        
        # Check account creation settings
        if self.create_revenue_account and not self.new_revenue_account_name:
            issues.append('Revenue account name is required when creating new account')
        
        if self.create_deferred_revenue_account and not self.new_deferred_revenue_account_name:
            issues.append('Deferred revenue account name is required when creating new account')
        
        # Show validation results
        return self._show_validation_results(issues, warnings)
    
    def _show_validation_results(self, issues, warnings):
        """Show validation results"""
        if not issues and not warnings:
            message = '✓ Configuration is valid and ready to apply!'
            msg_type = 'success'
        else:
            message_parts = ['<h4>Configuration Validation</h4>']
            
            if issues:
                message_parts.append('<p><strong>Issues (must be resolved):</strong></p>')
                message_parts.append('<ul>')
                for issue in issues:
                    message_parts.append(f'<li>❌ {issue}</li>')
                message_parts.append('</ul>')
            
            if warnings:
                message_parts.append('<p><strong>Warnings (recommended):</strong></p>')
                message_parts.append('<ul>')
                for warning in warnings:
                    message_parts.append(f'<li>⚠️ {warning}</li>')
                message_parts.append('</ul>')
            
            message = ''.join(message_parts)
            msg_type = 'warning' if issues else 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Results',
                'message': message,
                'type': msg_type,
                'sticky': True,
            }
        }
    
    def action_reset_to_defaults(self):
        """Reset to default configuration"""
        self.ensure_one()
        
        # Reset to defaults
        self.setup_mode = 'guided'
        self.use_company_defaults = True
        self.create_revenue_account = False
        self.create_deferred_revenue_account = False
        
        # Clear manual selections
        self.revenue_account_id = False
        self.deferred_revenue_account_id = False
        self.receivable_account_id = False
        self.cash_account_id = False
        
        # Trigger guided setup
        self._set_guided_defaults()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Configuration reset to recommended defaults',
                'type': 'info',
            }
        }