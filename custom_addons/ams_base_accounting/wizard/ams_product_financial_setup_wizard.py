# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSProductFinancialSetupWizard(models.TransientModel):
    """Wizard for configuring financial settings for products"""
    _name = 'ams.product.financial.setup.wizard'
    _description = 'AMS Product Financial Setup Wizard'
    
    # Wizard Type
    wizard_type = fields.Selection([
        ('single_product', 'Single Product'),
        ('bulk_products', 'Multiple Products'),
        ('category_setup', 'Product Category Setup'),
        ('template_setup', 'Template Setup'),
    ], string='Setup Type', required=True, default='single_product')
    
    # Product Selection
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        help="Select a product to configure"
    )
    
    product_ids = fields.Many2many(
        'product.template',
        string='Products',
        help="Select multiple products for bulk configuration"
    )
    
    # Product Category Filter
    category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help="Filter products by category"
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Product Information (for single product setup)
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name',
        readonly=True
    )
    
    current_setup_status = fields.Boolean(
        string='Currently Setup',
        related='product_id.financial_setup_complete',
        readonly=True
    )
    
    # Financial Configuration
    ams_product_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication'),
        ('event', 'Event'),
        ('general', 'General Product'),
    ], string='AMS Product Type', required=True, default='general')
    
    is_subscription_product = fields.Boolean(
        string='Is Subscription Product',
        default=False
    )
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Subscription Period')
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('subscription', 'Subscription-based'),
        ('milestone', 'Milestone-based'),
        ('percentage', 'Percentage Completion'),
    ], string='Revenue Recognition Method', default='immediate')
    
    requires_deferred_revenue = fields.Boolean(
        string='Requires Deferred Revenue',
        default=False
    )
    
    # Account Configuration
    revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Revenue Account',
        required=True,
        domain="[('account_type', 'in', ['income', 'income_membership', 'income_chapter', 'income_publication']), ('company_id', '=', company_id)]"
    )
    
    deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]"
    )
    
    expense_account_id = fields.Many2one(
        'ams.account.account',
        string='Expense Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost']), ('company_id', '=', company_id)]"
    )
    
    # Bulk Setup Options
    apply_to_all = fields.Boolean(
        string='Apply to All Selected',
        default=True,
        help="Apply the same configuration to all selected products"
    )
    
    filter_by_type = fields.Boolean(
        string='Filter by Product Type',
        default=False
    )
    
    product_type_filter = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication'),
        ('event', 'Event'),
        ('general', 'General Product'),
    ], string='Product Type Filter')
    
    only_incomplete = fields.Boolean(
        string='Only Incomplete Setup',
        default=True,
        help="Only configure products that don't have complete financial setup"
    )
    
    # Template Configuration (for bulk setup)
    use_template = fields.Boolean(
        string='Use Template Configuration',
        default=False,
        help="Use predefined templates for configuration"
    )
    
    template_type = fields.Selection([
        ('membership_individual', 'Individual Membership Template'),
        ('membership_enterprise', 'Enterprise Membership Template'),
        ('chapter_standard', 'Standard Chapter Template'),
        ('publication_standard', 'Standard Publication Template'),
        ('event_standard', 'Standard Event Template'),
    ], string='Configuration Template')
    
    # Validation and Status
    configuration_valid = fields.Boolean(
        string='Configuration Valid',
        compute='_compute_configuration_status'
    )
    
    validation_errors = fields.Text(
        string='Validation Errors',
        compute='_compute_configuration_status'
    )
    
    # Processing Results
    processed_count = fields.Integer(
        string='Processed Products',
        readonly=True,
        default=0
    )
    
    error_count = fields.Integer(
        string='Errors',
        readonly=True,
        default=0
    )
    
    processing_log = fields.Text(
        string='Processing Log',
        readonly=True
    )
    
    # Company Account Defaults (for easy selection)
    default_individual_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Individual Membership Account',
        related='company_id.individual_membership_revenue_account_id',
        readonly=True
    )
    
    default_enterprise_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Enterprise Membership Account',
        related='company_id.enterprise_membership_revenue_account_id',
        readonly=True
    )
    
    default_chapter_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Chapter Account',
        related='company_id.chapter_revenue_account_id',
        readonly=True
    )
    
    default_publication_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Publication Account',
        related='company_id.publication_revenue_account_id',
        readonly=True
    )
    
    # Computed Methods
    @api.depends('revenue_account_id', 'requires_deferred_revenue', 'deferred_revenue_account_id')
    def _compute_configuration_status(self):
        """Validate the configuration"""
        for wizard in self:
            errors = []
            
            if not wizard.revenue_account_id:
                errors.append("Revenue account is required")
            
            if wizard.requires_deferred_revenue and not wizard.deferred_revenue_account_id:
                errors.append("Deferred revenue account is required when deferred revenue is enabled")
            
            if wizard.is_subscription_product and not wizard.subscription_period:
                errors.append("Subscription period is required for subscription products")
            
            if wizard.is_subscription_product and wizard.revenue_recognition_method == 'immediate':
                errors.append("Subscription products should not use immediate revenue recognition")
            
            wizard.configuration_valid = len(errors) == 0
            wizard.validation_errors = '\n'.join([f"• {error}" for error in errors])
    
    # Onchange Methods
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Load current product configuration"""
        if self.product_id:
            product = self.product_id
            
            # Load existing configuration
            if hasattr(product, 'ams_product_type'):
                self.ams_product_type = product.ams_product_type or 'general'
            if hasattr(product, 'is_subscription_product'):
                self.is_subscription_product = product.is_subscription_product
            if hasattr(product, 'subscription_period'):
                self.subscription_period = product.subscription_period
            if hasattr(product, 'revenue_recognition_method'):
                self.revenue_recognition_method = product.revenue_recognition_method or 'immediate'
            if hasattr(product, 'requires_deferred_revenue'):
                self.requires_deferred_revenue = product.requires_deferred_revenue
            if hasattr(product, 'revenue_account_id'):
                self.revenue_account_id = product.revenue_account_id
            if hasattr(product, 'deferred_revenue_account_id'):
                self.deferred_revenue_account_id = product.deferred_revenue_account_id
            if hasattr(product, 'expense_account_id'):
                self.expense_account_id = product.expense_account_id
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Set default configuration based on product type"""
        if not self.ams_product_type:
            return
        
        company = self.company_id
        
        # Set default accounts based on product type
        account_mapping = {
            'individual': company.individual_membership_revenue_account_id,
            'enterprise': company.enterprise_membership_revenue_account_id,
            'chapter': company.chapter_revenue_account_id,
            'publication': company.publication_revenue_account_id,
        }
        
        deferred_account_mapping = {
            'individual': company.membership_deferred_revenue_account_id,
            'enterprise': company.membership_deferred_revenue_account_id,
            'chapter': company.chapter_deferred_revenue_account_id,
            'publication': company.publication_deferred_revenue_account_id,
        }
        
        if self.ams_product_type in account_mapping:
            self.revenue_account_id = account_mapping[self.ams_product_type]
            self.deferred_revenue_account_id = deferred_account_mapping.get(self.ams_product_type)
            
            # Set subscription defaults for membership products
            if self.ams_product_type in ['individual', 'enterprise', 'chapter', 'publication']:
                self.is_subscription_product = True
                self.requires_deferred_revenue = True
                self.revenue_recognition_method = 'subscription'
                self.subscription_period = 'annual'
    
    @api.onchange('template_type')
    def _onchange_template_type(self):
        """Load template configuration"""
        if not self.template_type:
            return
        
        templates = {
            'membership_individual': {
                'ams_product_type': 'individual',
                'is_subscription_product': True,
                'subscription_period': 'annual',
                'revenue_recognition_method': 'subscription',
                'requires_deferred_revenue': True,
            },
            'membership_enterprise': {
                'ams_product_type': 'enterprise',
                'is_subscription_product': True,
                'subscription_period': 'annual',
                'revenue_recognition_method': 'subscription',
                'requires_deferred_revenue': True,
            },
            'chapter_standard': {
                'ams_product_type': 'chapter',
                'is_subscription_product': True,
                'subscription_period': 'annual',
                'revenue_recognition_method': 'subscription',
                'requires_deferred_revenue': True,
            },
            'publication_standard': {
                'ams_product_type': 'publication',
                'is_subscription_product': True,
                'subscription_period': 'annual',
                'revenue_recognition_method': 'subscription',
                'requires_deferred_revenue': True,
            },
            'event_standard': {
                'ams_product_type': 'event',
                'is_subscription_product': False,
                'revenue_recognition_method': 'immediate',
                'requires_deferred_revenue': False,
            },
        }
        
        if self.template_type in templates:
            template = templates[self.template_type]
            for field, value in template.items():
                setattr(self, field, value)
            
            # Trigger onchange for ams_product_type to set accounts
            self._onchange_ams_product_type()
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Update related fields when subscription status changes"""
        if self.is_subscription_product:
            self.requires_deferred_revenue = True
            if self.revenue_recognition_method == 'immediate':
                self.revenue_recognition_method = 'subscription'
            if not self.subscription_period:
                self.subscription_period = 'annual'
        else:
            self.requires_deferred_revenue = False
            self.revenue_recognition_method = 'immediate'
            self.subscription_period = False
    
    # Action Methods
    def action_configure_products(self):
        """Main action to configure products"""
        self.ensure_one()
        
        if not self.configuration_valid:
            raise UserError(f"Configuration is not valid:\n{self.validation_errors}")
        
        if self.wizard_type == 'single_product':
            return self._configure_single_product()
        elif self.wizard_type == 'bulk_products':
            return self._configure_bulk_products()
        elif self.wizard_type == 'category_setup':
            return self._configure_category_products()
        elif self.wizard_type == 'template_setup':
            return self._configure_template_products()
    
    def _configure_single_product(self):
        """Configure a single product"""
        if not self.product_id:
            raise UserError("Please select a product to configure.")
        
        try:
            self._apply_configuration_to_product(self.product_id)
            
            self.write({
                'processed_count': 1,
                'processing_log': f"✓ {self.product_id.name}: Configuration applied successfully"
            })
            
            return self._show_results()
            
        except Exception as e:
            raise UserError(f"Error configuring product: {str(e)}")
    
    def _configure_bulk_products(self):
        """Configure multiple products"""
        if not self.product_ids:
            raise UserError("Please select products to configure.")
        
        return self._process_multiple_products(self.product_ids)
    
    def _configure_category_products(self):
        """Configure all products in a category"""
        if not self.category_id:
            raise UserError("Please select a product category.")
        
        domain = [('categ_id', '=', self.category_id.id)]
        
        if self.only_incomplete:
            domain.append(('financial_setup_complete', '=', False))
        
        if self.filter_by_type:
            domain.append(('ams_product_type', '=', self.product_type_filter))
        
        products = self.env['product.template'].search(domain)
        
        if not products:
            raise UserError("No products found matching the criteria.")
        
        return self._process_multiple_products(products)
    
    def _process_multiple_products(self, products):
        """Process multiple products"""
        processed = 0
        errors = 0
        log_messages = []
        
        for product in products:
            try:
                self._apply_configuration_to_product(product)
                processed += 1
                log_messages.append(f"✓ {product.name}: Configuration applied")
                
            except Exception as e:
                errors += 1
                log_messages.append(f"✗ {product.name}: {str(e)}")
        
        self.write({
            'processed_count': processed,
            'error_count': errors,
            'processing_log': '\n'.join(log_messages)
        })
        
        return self._show_results()
    
    def _apply_configuration_to_product(self, product):
        """Apply configuration to a single product"""
        vals = {
            'ams_product_type': self.ams_product_type,
            'is_subscription_product': self.is_subscription_product,
            'revenue_recognition_method': self.revenue_recognition_method,
            'requires_deferred_revenue': self.requires_deferred_revenue,
            'revenue_account_id': self.revenue_account_id.id,
            'financial_setup_complete': True,
        }
        
        if self.subscription_period:
            vals['subscription_period'] = self.subscription_period
        
        if self.deferred_revenue_account_id:
            vals['deferred_revenue_account_id'] = self.deferred_revenue_account_id.id
        
        if self.expense_account_id:
            vals['expense_account_id'] = self.expense_account_id.id
        
        # Additional subscription product fields
        if self.is_subscription_product:
            vals.update({
                'auto_renew': True,  # Default for subscription products
            })
        
        product.write(vals)
        
        # Create subscription accounting record if product is used in subscriptions
        self._ensure_subscription_accounting(product)
    
    def _ensure_subscription_accounting(self, product):
        """Ensure subscription accounting is set up for subscription products"""
        if not product.is_subscription_product:
            return
        
        # Find subscriptions using this product
        subscriptions = self.env['ams.subscription'].search([
            ('product_id', '=', product.id),
            ('state', 'in', ['active', 'pending'])
        ])
        
        for subscription in subscriptions:
            # Check if accounting record exists
            existing = self.env['ams.subscription.accounting'].search([
                ('subscription_id', '=', subscription.id)
            ], limit=1)
            
            if not existing:
                # Create accounting record
                accounting_vals = {
                    'subscription_id': subscription.id,
                    'revenue_account_id': self.revenue_account_id.id,
                    'deferred_revenue_account_id': self.deferred_revenue_account_id.id or False,
                    'revenue_recognition_method': self.revenue_recognition_method,
                    'auto_create_entries': True,
                    'auto_post_entries': self.company_id.auto_post_subscription_entries,
                    'auto_revenue_recognition': self.company_id.auto_create_revenue_recognition,
                    'company_id': self.company_id.id,
                }
                
                # Set default journal
                if self.company_id.default_membership_journal_id:
                    accounting_vals['journal_id'] = self.company_id.default_membership_journal_id.id
                
                self.env['ams.subscription.accounting'].create(accounting_vals)
    
    def _show_results(self):
        """Show processing results"""
        return {
            'name': 'Product Financial Setup Results',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.financial.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }
    
    def action_view_configured_products(self):
        """View the configured products"""
        products_to_show = []
        
        if self.wizard_type == 'single_product' and self.product_id:
            products_to_show = [self.product_id.id]
        elif self.wizard_type in ['bulk_products', 'category_setup'] and self.product_ids:
            products_to_show = self.product_ids.ids
        
        if not products_to_show:
            raise UserError("No products to display.")
        
        return {
            'name': 'Configured Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', products_to_show)],
            'context': {'create': False}
        }
    
    def action_setup_more_products(self):
        """Setup more products"""
        return {
            'name': 'Product Financial Setup',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.financial.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_type': 'bulk_products',
                'default_company_id': self.company_id.id,
            }
        }
    
    # Utility Methods
    @api.model
    def get_products_needing_setup(self, company_id=None):
        """Get products that need financial setup"""
        domain = [('financial_setup_complete', '=', False)]
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        return self.env['product.template'].search(domain)
    
    @api.model
    def bulk_setup_by_type(self, product_type, company_id=None):
        """Bulk setup products by type using templates"""
        if not company_id:
            company_id = self.env.company.id
        
        template_mapping = {
            'individual': 'membership_individual',
            'enterprise': 'membership_enterprise',
            'chapter': 'chapter_standard',
            'publication': 'publication_standard',
            'event': 'event_standard',
        }
        
        if product_type not in template_mapping:
            raise UserError(f"No template available for product type: {product_type}")
        
        # Find products of this type
        products = self.env['product.template'].search([
            ('ams_product_type', '=', product_type),
            ('financial_setup_complete', '=', False),
        ])
        
        if not products:
            return {'processed': 0, 'message': 'No products found'}
        
        # Create wizard and process
        wizard = self.create({
            'wizard_type': 'bulk_products',
            'product_ids': [(6, 0, products.ids)],
            'template_type': template_mapping[product_type],
            'use_template': True,
            'company_id': company_id,
        })
        
        # Load template configuration
        wizard._onchange_template_type()
        
        # Process products
        result = wizard._process_multiple_products(products)
        
        return {
            'processed': wizard.processed_count,
            'errors': wizard.error_count,
            'message': f'Processed {wizard.processed_count} products with {wizard.error_count} errors'
        }