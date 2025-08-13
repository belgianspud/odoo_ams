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
    
    # Advanced options
    create_demo_accounts = fields.Boolean(
        string='Create Demo Accounts for Testing',
        default=False,
        help='Create sample account structure for testing purposes (experts only)'
    )
    
    force_account_reset = fields.Boolean(
        string='Reset Existing AMS Categories',
        default=False,
        help='Remove existing AMS categories and reconfigure (use with caution)'
    )
    
    enable_debug_logging = fields.Boolean(
        string='Enable Detailed Logging',
        default=False,
        help='Create detailed logs of all setup actions for troubleshooting'
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
    
    setup_results_summary = fields.Html(
        string='Setup Results Summary',
        help='Summary of setup actions performed'
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
            
            # Count accounts that could be AMS accounts but don't have categories
            wizard.accounts_need_categories = self.env['account.account'].search_count([
                ('account_type', 'in', ['income', 'asset_receivable', 'liability_current']),
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
                status_html += f"<div class='alert alert-info mb-2'><i class='fa fa-info'></i> <strong>{wizard.accounts_need_categories}</strong> accounts could be configured for AMS</div>"
            
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
                configured_count = self._configure_ams_account_categories()
                if configured_count > 0:
                    messages.append(f"✓ Configured {configured_count} accounts for AMS")
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
        
        # Prepare result message and summary
        if messages and not issues:
            message_text = "✅ AMS Accounting Setup Completed Successfully!"
            message_type = 'success'
            summary_html = self._generate_success_summary(messages)
        elif messages and issues:
            message_text = "⚠️ AMS Accounting Setup Completed with Warnings"
            message_type = 'warning'  
            summary_html = self._generate_warning_summary(messages, issues)
        elif issues:
            message_text = "❌ AMS Accounting Setup Failed"
            message_type = 'danger'
            summary_html = self._generate_error_summary(issues)
        else:
            message_text = "ℹ️ No changes needed. AMS accounting is already configured."
            message_type = 'info'
            summary_html = self._generate_no_change_summary()
        
        # Store results for display
        self.setup_results_summary = summary_html
        
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
    
    def _configure_ams_account_categories(self):
        """Configure AMS account categories based on existing accounts"""
        account_model = self.env['account.account']
        configured_count = 0
        
        # Define potential AMS account mappings
        account_mappings = [
            # Revenue accounts
            {'name_contains': ['membership', 'member'], 'account_type': 'income', 'category': 'membership_revenue'},
            {'name_contains': ['publication', 'journal', 'magazine'], 'account_type': 'income', 'category': 'publication_revenue'},
            {'name_contains': ['chapter'], 'account_type': 'income', 'category': 'chapter_revenue'},
            {'name_contains': ['event', 'conference', 'training'], 'account_type': 'income', 'category': 'event_revenue'},
            {'name_contains': ['revenue', 'income'], 'account_type': 'income', 'category': 'membership_revenue'},
            
            # Receivable accounts
            {'name_contains': ['receivable', 'member', 'customer'], 'account_type': 'asset_receivable', 'category': 'member_receivables'},
            
            # Deferred revenue
            {'name_contains': ['deferred', 'prepaid', 'unearned'], 'account_type': 'liability_current', 'category': 'deferred_revenue'},
        ]
        
        for mapping in account_mappings:
            # Build domain for searching accounts
            domain = [
                ('account_type', '=', mapping['account_type']),
                ('company_id', '=', self.env.company.id),
                ('ams_account_category', '=', False),  # Not already configured
            ]
            
            # Add name search conditions
            name_conditions = []
            for name_part in mapping['name_contains']:
                name_conditions.append(('name', 'ilike', name_part))
            
            if name_conditions:
                domain.append('|' * (len(name_conditions) - 1))
                domain.extend(name_conditions)
            
            # Find and configure matching accounts
            matching_accounts = account_model.search(domain, limit=5)  # Limit to avoid too many matches
            
            for account in matching_accounts:
                account.write({
                    'is_ams_account': True,
                    'ams_account_category': mapping['category']
                })
                configured_count += 1
        
        return configured_count
    
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
                # Try to create missing journal - but be careful about conflicts
                try:
                    self.env['account.journal'].create({
                        'name': config['name'],
                        'code': code,
                        'type': config['type'],
                        'company_id': company.id,
                    })
                    created_count += 1
                except Exception:
                    # Journal creation might fail if code conflicts
                    pass
        
        return {
            'created': created_count,
            'existing': existing_count,
            'total_expected': len(expected_journals),
        }
    
    def _generate_success_summary(self, messages):
        """Generate HTML summary for successful setup"""
        html = "<div class='alert alert-success'>"
        html += "<h6><i class='fa fa-check-circle'></i> Setup Completed Successfully!</h6>"
        html += "<ul>"
        for message in messages:
            html += f"<li>{message}</li>"
        html += "</ul>"
        html += "</div>"
        return html
    
    def _generate_warning_summary(self, messages, issues):
        """Generate HTML summary for setup with warnings"""
        html = "<div class='alert alert-warning'>"
        html += "<h6><i class='fa fa-exclamation-triangle'></i> Setup Completed with Warnings</h6>"
        html += "<h6>Completed Successfully:</h6><ul>"
        for message in messages:
            html += f"<li>{message}</li>"
        html += "</ul>"
        html += "<h6>Issues Encountered:</h6><ul>"
        for issue in issues:
            html += f"<li>{issue}</li>"
        html += "</ul>"
        html += "</div>"
        return html
    
    def _generate_error_summary(self, issues):
        """Generate HTML summary for failed setup"""
        html = "<div class='alert alert-danger'>"
        html += "<h6><i class='fa fa-times-circle'></i> Setup Failed</h6>"
        html += "<ul>"
        for issue in issues:
            html += f"<li>{issue}</li>"
        html += "</ul>"
        html += "</div>"
        return html
    
    def _generate_no_change_summary(self):
        """Generate HTML summary for no changes needed"""
        html = "<div class='alert alert-info'>"
        html += "<h6><i class='fa fa-info-circle'></i> No Changes Needed</h6>"
        html += "<p>Your AMS accounting system is already properly configured.</p>"
        html += "</div>"
        return html
    
    # Add the other missing methods from previous versions...
    def action_preview_setup(self):
        """Preview what changes will be made without executing them"""
        self.ensure_one()
        
        preview_html = "<h5>Preview of Setup Changes</h5>"
        
        if self.configure_ams_accounts:
            accounts_to_configure = self.env['account.account'].search([
                ('account_type', 'in', ['income', 'asset_receivable', 'liability_current']),
                ('ams_account_category', '=', False),
                ('company_id', '=', self.env.company.id)
            ])
            if accounts_to_configure:
                preview_html += f"<p><strong>Accounts to Configure:</strong> {len(accounts_to_configure)} accounts will get AMS categories</p>"
            else:
                preview_html += "<p><strong>Accounts:</strong> All accounts already have proper categories</p>"
        
        if self.configure_existing_products:
            unconfigured_products = self.env['product.template'].search([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ])
            if unconfigured_products:
                preview_html += f"<p><strong>Products to Configure:</strong> {len(unconfigured_products)} products will get account assignments</p>"
            else:
                preview_html += "<p><strong>Products:</strong> All products already configured</p>"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Setup Preview',
                'message': preview_html,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_view_current_setup(self):
        """View current setup status"""
        return {
            'name': 'Current AMS Setup Status',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'domain': [('is_ams_account', '=', True)],
            'context': {'search_default_group_by_ams_category': 1},
        }
    
    # Add all the missing action methods from the previous version
    def action_open_financial_management(self):
        """Open the Financial Management menu"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/web#menu_id=%d' % self.env.ref('ams_base_accounting.menu_ams_financial_management').id,
            'target': 'self',
        }
    
    def action_view_chart_of_accounts(self):
        """View the AMS Chart of Accounts"""
        return {
            'name': 'Association Chart of Accounts',
            'type': 'ir.actions.act_window',
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'domain': [('is_ams_account', '=', True)],
            'context': {'search_default_group_by_ams_category': 1},
        }
    
    def action_view_member_invoices(self):
        """View Member Invoices"""
        return {
            'name': 'Member Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('move_type', '=', 'out_invoice'), ('has_ams_products', '=', True)],
            'context': {'search_default_group_by_ams_transaction_type': 1},
        }
    
    def action_view_revenue_recognition(self):
        """View Revenue Recognition (if module is installed)"""
        try:
            # Check if revenue recognition module is installed
            revenue_rec_module = self.env['ir.module.module'].search([
                ('name', '=', 'ams_revenue_recognition'),
                ('state', '=', 'installed')
            ])
            
            if revenue_rec_module:
                return {
                    'name': 'Revenue Recognition Dashboard',
                    'type': 'ir.actions.act_window',
                    'res_model': 'ams.revenue.recognition',
                    'view_mode': 'graph,pivot,list',
                    'context': {'search_default_group_by_recognition_month': 1},
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Revenue Recognition module is not installed. Install it for advanced revenue features.',
                        'type': 'info',
                    }
                }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Revenue Recognition module is not available.',
                    'type': 'info',
                }
            }
    
    def action_view_financial_reports(self):
        """View Financial Reports"""
        return {
            'name': 'Association Financial Reports',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'pivot,graph,list',
            'domain': [('move_id.move_type', '=', 'out_invoice'), ('is_ams_line', '=', True)],
            'context': {
                'search_default_group_by_product': 1,
                'search_default_group_by_date_month': 1
            },
        }
    
    def action_run_test_transaction(self):
        """Create or guide user to create a test transaction"""
        return {
            'name': 'Create Test Member Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_type': 'out_invoice',
                'default_is_test_transaction': True,
            },
        }