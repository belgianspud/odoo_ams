# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSAccountingSetupWizard(models.TransientModel):
    """Wizard to set up AMS accounting"""
    _name = 'ams.accounting.setup.wizard'
    _description = 'AMS Accounting Setup Wizard'
    
    # Setup options
    configure_ams_accounts = fields.Boolean(
        string='Configure AMS Account Categories',
        default=True,
        help='Ensure AMS accounts have proper categories assigned'
    )
    
    configure_existing_products = fields.Boolean(
        string='Configure Existing Products',
        default=True,
        help='Auto-configure GL accounts for existing AMS products'
    )
    
    setup_default_journals = fields.Boolean(
        string='Verify AMS Journals',
        default=True,
        help='Verify AMS-specific journals are properly configured'
    )
    
    validate_account_setup = fields.Boolean(
        string='Validate Account Setup',
        default=True,
        help='Run validation checks on AMS account configuration'
    )
    
    # Information fields
    unconfigured_product_count = fields.Integer(
        string='Unconfigured Products',
        compute='_compute_product_stats',
        help='Number of AMS products needing configuration'
    )
    
    existing_ams_accounts = fields.Integer(
        string='Existing AMS Accounts', 
        compute='_compute_account_stats',
        help='Number of existing AMS accounts'
    )
    
    accounts_need_categories = fields.Integer(
        string='Accounts Need Categories',
        compute='_compute_account_stats',
        help='Number of accounts that need AMS categories'
    )
    
    setup_status = fields.Html(
        string='Current Setup Status',
        compute='_compute_setup_status',
        help='Overview of current AMS accounting setup'
    )
    
    @api.depends()
    def _compute_product_stats(self):
        """Compute product statistics"""
        for wizard in self:
            wizard.unconfigured_product_count = self.env['product.template'].search_count([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ])
    
    @api.depends()
    def _compute_account_stats(self):
        """Compute account statistics"""
        for wizard in self:
            wizard.existing_ams_accounts = self.env['account.account'].search_count([
                ('is_ams_account', '=', True)
            ])
            
            # Count accounts that might be AMS accounts but don't have categories
            ams_codes = ['4100', '4110', '4200', '4300', '4400', '1200', '2300', '1010', '1020']
            wizard.accounts_need_categories = self.env['account.account'].search_count([
                ('code', 'in', ams_codes),
                ('ams_account_category', '=', False),
                ('company_id', '=', self.env.company.id)
            ])
    
    @api.depends('existing_ams_accounts', 'accounts_need_categories', 'unconfigured_product_count')
    def _compute_setup_status(self):
        """Compute setup status overview"""
        for wizard in self:
            status_html = "<div class='mb-3'>"
            
            # Account Status
            if wizard.existing_ams_accounts > 0:
                status_html += f"<div class='alert alert-success mb-2'><i class='fa fa-check'></i> <strong>{wizard.existing_ams_accounts}</strong> AMS accounts configured</div>"
            else:
                status_html += "<div class='alert alert-warning mb-2'><i class='fa fa-exclamation-triangle'></i> No AMS accounts found</div>"
            
            # Account Categories Status
            if wizard.accounts_need_categories > 0:
                status_html += f"<div class='alert alert-info mb-2'><i class='fa fa-info'></i> <strong>{wizard.accounts_need_categories}</strong> accounts need AMS categories</div>"
            
            # Product Status
            if wizard.unconfigured_product_count > 0:
                status_html += f"<div class='alert alert-warning mb-2'><i class='fa fa-cog'></i> <strong>{wizard.unconfigured_product_count}</strong> products need configuration</div>"
            else:
                status_html += "<div class='alert alert-success mb-2'><i class='fa fa-check'></i> All products are configured</div>"
            
            status_html += "</div>"
            wizard.setup_status = status_html
    
    def action_run_setup(self):
        """Execute the AMS accounting setup"""
        self.ensure_one()
        
        messages = []
        issues = []
        
        # Configure AMS account categories
        if self.configure_ams_accounts:
            try:
                configured = self.env['account.account'].ensure_ams_accounts_configured()
                if configured:
                    messages.append("✓ Configured AMS account categories")
                else:
                    messages.append("✓ AMS account categories already configured")
            except Exception as e:
                issues.append(f"Account configuration error: {str(e)}")
        
        # Configure existing products
        if self.configure_existing_products:
            try:
                unconfigured = self.env['product.template'].search([
                    ('is_subscription_product', '=', True),
                    ('use_ams_accounting', '=', True),
                    ('ams_accounts_configured', '=', False)
                ])
                
                configured_count = 0
                for product in unconfigured:
                    try:
                        product._set_default_ams_accounts()
                        configured_count += 1
                    except Exception as e:
                        issues.append(f"Product {product.name}: {str(e)}")
                
                if configured_count > 0:
                    messages.append(f"✓ Configured {configured_count} AMS products")
                else:
                    messages.append("✓ All AMS products already configured")
                    
            except Exception as e:
                issues.append(f"Product configuration error: {str(e)}")
        
        # Verify journals
        if self.setup_default_journals:
            try:
                journal_status = self._verify_ams_journals()
                if journal_status['created']:
                    messages.append(f"✓ Created {journal_status['created']} AMS journals")
                if journal_status['existing']:
                    messages.append(f"✓ Verified {journal_status['existing']} existing journals")
            except Exception as e:
                issues.append(f"Journal verification error: {str(e)}")
        
        # Validate account setup
        if self.validate_account_setup:
            try:
                validation = self.env['account.account'].validate_ams_account_setup()
                if validation['valid']:
                    messages.append(f"✓ Validated {validation['accounts_checked']} AMS accounts")
                else:
                    issues.extend([f"Validation: {issue}" for issue in validation['issues']])
            except Exception as e:
                issues.append(f"Validation error: {str(e)}")
        
        # Prepare result message
        if messages and not issues:
            message_text = "✅ AMS Accounting Setup Completed Successfully!\n\n" + "\n".join(messages)
            message_type = 'success'
        elif messages and issues:
            message_text = "⚠️ AMS Accounting Setup Completed with Warnings:\n\n"
            message_text += "✅ Completed:\n" + "\n".join(messages)
            message_text += "\n\n⚠️ Issues:\n" + "\n".join(issues)
            message_type = 'warning'
        elif issues:
            message_text = "❌ AMS Accounting Setup Failed:\n\n" + "\n".join(issues)
            message_type = 'danger'
        else:
            message_text = "ℹ️ No changes needed. AMS accounting is already configured."
            message_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'AMS Accounting Setup',
                'message': message_text,
                'type': message_type,
                'sticky': True,
            }
        }
    
    def _verify_ams_journals(self):
        """Verify AMS-specific journals exist and are configured"""
        company = self.env.company
        
        # Expected journals and their configurations
        expected_journals = {
            'AMS': {
                'name': 'AMS Sales',
                'type': 'sale',
                'exists': False,
            },
            'REVR': {
                'name': 'Revenue Recognition',
                'type': 'general', 
                'exists': False,
            },
            'MBPAY': {
                'name': 'Membership Payments',
                'type': 'cash',
                'exists': False,
            },
        }
        
        created_count = 0
        existing_count = 0
        
        for code, config in expected_journals.items():
            journal = self.env['account.journal'].search([
                ('code', '=', code),
                ('company_id', '=', company.id)
            ], limit=1)
            
            if journal:
                config['exists'] = True
                existing_count += 1
            else:
                # Create missing journal
                try:
                    self.env['account.journal'].create({
                        'name': config['name'],
                        'code': code,
                        'type': config['type'],
                        'company_id': company.id,
                    })
                    created_count += 1
                except Exception:
                    # Journal creation might fail if done by XML data
                    pass
        
        return {
            'created': created_count,
            'existing': existing_count,
            'total_expected': len(expected_journals),
        }
    
    def action_view_ams_accounts(self):
        """View AMS accounts"""
        return {
            'name': 'AMS Chart of Accounts',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'domain': [('is_ams_account', '=', True)],
            'context': {'search_default_filter_ams_accounts': 1},
        }
    
    def action_view_unconfigured_products(self):
        """View products that need configuration"""
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
    
    def action_test_revenue_recognition(self):
        """Test revenue recognition setup"""
        # Create a simple test to verify integration
        try:
            # Check if revenue recognition module is installed
            revenue_rec_module = self.env['ir.module.module'].search([
                ('name', '=', 'ams_revenue_recognition'),
                ('state', '=', 'installed')
            ])
            
            if revenue_rec_module:
                message = "✅ Revenue Recognition module is installed and ready"
                message_type = 'success'
            else:
                message = "ℹ️ Revenue Recognition module not installed. Install it for advanced revenue features."
                message_type = 'info'
        except Exception as e:
            message = f"❌ Error testing revenue recognition: {str(e)}"
            message_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Revenue Recognition Test',
                'message': message,
                'type': message_type,
            }
        }
    
    def action_create_demo_data(self):
        """Create demo accounts if needed for testing"""
        self.ensure_one()
        
        try:
            # Use the model method to ensure accounts exist
            created_accounts = self.env['account.account'].create_ams_account_structure()
            
            if created_accounts:
                message = f"✅ Created {len(created_accounts)} AMS demo accounts"
                message_type = 'success'
            else:
                message = "ℹ️ AMS accounts already exist"
                message_type = 'info'
                
        except Exception as e:
            message = f"❌ Error creating demo accounts: {str(e)}"
            message_type = 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demo Account Creation',
                'message': message,
                'type': message_type,
            }
        }