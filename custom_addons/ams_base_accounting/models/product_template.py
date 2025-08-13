# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    """Enhanced Product Template with User-Friendly GL Account Configuration"""
    _inherit = 'product.template'
    
    # =============================================================================
    # AMS ACCOUNTING FIELDS (Enhanced for User Experience)
    # =============================================================================
    
    # Revenue Accounts
    ams_revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Where revenue is recorded when this product is sold and earned'
    )
    
    ams_deferred_account_id = fields.Many2one(
        'account.account', 
        string='Prepaid Revenue Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Where money is held for prepaid subscriptions until services are delivered'
    )
    
    # Receivables & Cash
    ams_receivable_account_id = fields.Many2one(
        'account.account',
        string='Outstanding Invoices Account', 
        domain="[('account_type', '=', 'asset_receivable')]",
        help='Tracks money owed by customers for this product'
    )
    
    ams_cash_account_id = fields.Many2one(
        'account.account',
        string='Payment Deposits Account',
        domain="[('account_type', '=', 'asset_cash')]", 
        help='Where customer payments for this product are deposited'
    )
    
    # Expense Accounts
    ams_expense_account_id = fields.Many2one(
        'account.account',
        string='Product Costs Account',
        domain="[('account_type', '=', 'expense')]",
        help='Optional: Track costs related to delivering this product'
    )
    
    # Additional Accounting Configuration
    use_ams_accounting = fields.Boolean(
        string='Enable Revenue Tracking',
        default=False,
        help='Turn on automatic revenue tracking and financial reporting for this product'
    )
    
    ams_accounting_notes = fields.Text(
        string='Revenue Setup Notes',
        help='Internal notes about special revenue tracking requirements for this product'
    )
    
    # NEW: User-friendly fields for revenue recognition
    auto_create_recognition = fields.Boolean(
        string='Auto-Create Revenue Schedules',
        default=True,
        help='Automatically create revenue recognition schedules when invoices are posted'
    )
    
    auto_process_recognition = fields.Boolean(
        string='Auto-Process Revenue Recognition',
        default=True,
        help='Allow automated processing of revenue recognition for this product'
    )
    
    # Computed fields for validation and user feedback
    ams_accounts_configured = fields.Boolean(
        string='Revenue Setup Complete',
        compute='_compute_ams_accounts_configured',
        store=True,
        help='All required revenue tracking accounts are properly configured'
    )
    
    # User-friendly status fields
    revenue_setup_status = fields.Selection([
        ('not_needed', 'Not Needed'),
        ('needs_setup', 'Needs Setup'),
        ('partially_configured', 'Partially Configured'),
        ('fully_configured', 'Fully Configured'),
    ], string='Revenue Setup Status', compute='_compute_revenue_setup_status', store=True)
    
    revenue_setup_progress = fields.Integer(
        string='Setup Progress %',
        compute='_compute_revenue_setup_status',
        store=True,
        help='Percentage of revenue setup completed'
    )
    
    # =============================================================================
    # COMPUTED FIELDS (Enhanced for User Experience)
    # =============================================================================
    
    @api.depends('ams_revenue_account_id', 'ams_receivable_account_id', 'is_subscription_product', 'use_ams_accounting')
    def _compute_ams_accounts_configured(self):
        """Check if required revenue tracking accounts are configured"""
        for product in self:
            if product.is_subscription_product and product.use_ams_accounting:
                # For subscription products, we need at least revenue and receivable accounts
                product.ams_accounts_configured = bool(
                    product.ams_revenue_account_id and 
                    product.ams_receivable_account_id
                )
            else:
                product.ams_accounts_configured = True  # Not required
    
    @api.depends('is_subscription_product', 'use_ams_accounting', 'ams_revenue_account_id', 
                 'ams_receivable_account_id', 'ams_deferred_account_id')
    def _compute_revenue_setup_status(self):
        """Compute user-friendly setup status and progress"""
        for product in self:
            if not product.is_subscription_product:
                product.revenue_setup_status = 'not_needed'
                product.revenue_setup_progress = 100
                continue
            
            if not product.use_ams_accounting:
                product.revenue_setup_status = 'needs_setup'
                product.revenue_setup_progress = 0
                continue
            
            # Calculate progress based on required fields
            required_fields = ['ams_revenue_account_id', 'ams_receivable_account_id']
            optional_fields = ['ams_deferred_account_id', 'ams_cash_account_id']
            
            # Check required fields
            required_complete = sum(1 for field in required_fields if getattr(product, field))
            required_total = len(required_fields)
            
            # Check optional fields that make sense for this product
            optional_complete = 0
            optional_total = 0
            
            if product.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                # Long-term subscriptions should have deferred account
                optional_total += 1
                if product.ams_deferred_account_id:
                    optional_complete += 1
            
            if product.ams_cash_account_id:
                optional_complete += 1
            optional_total += 1  # Cash account is always optional but beneficial
            
            # Calculate overall progress
            total_possible = required_total + optional_total
            total_complete = required_complete + optional_complete
            
            if total_possible > 0:
                product.revenue_setup_progress = int((total_complete / total_possible) * 100)
            else:
                product.revenue_setup_progress = 0
            
            # Determine status
            if required_complete == required_total:
                if total_complete == total_possible:
                    product.revenue_setup_status = 'fully_configured'
                else:
                    product.revenue_setup_status = 'partially_configured'
            else:
                product.revenue_setup_status = 'needs_setup'
    
    # =============================================================================
    # ONCHANGE METHODS (Enhanced with User-Friendly Automation)
    # =============================================================================
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product_accounting(self):
        """Auto-enable revenue tracking for subscription products"""
        # Call parent module's onchange first if it exists (ams_subscriptions)
        if hasattr(super(), '_onchange_is_subscription_product'):
            super()._onchange_is_subscription_product()
        
        if self.is_subscription_product:
            self.use_ams_accounting = True
            # Set default automation settings
            self.auto_create_recognition = True
            self.auto_process_recognition = True
            # Set default accounts based on subscription type
            self._set_default_ams_accounts()
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type_accounting(self):
        """Update default accounts when subscription type changes"""
        # Call parent module's onchange first if it exists (ams_subscriptions)
        if hasattr(super(), '_onchange_ams_product_type'):
            super()._onchange_ams_product_type()
            
        if self.ams_product_type != 'none':
            self._set_default_ams_accounts()
    
    @api.onchange('subscription_period')
    def _onchange_subscription_period_revenue_setup(self):
        """Auto-configure revenue recognition settings based on subscription period"""
        if self.subscription_period and self.is_subscription_product:
            # Auto-set deferred account for longer subscriptions
            if self.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                if not self.ams_deferred_account_id:
                    deferred_account = self._find_account_by_category('deferred_revenue')
                    if deferred_account:
                        self.ams_deferred_account_id = deferred_account.id
    
    # =============================================================================
    # USER-FRIENDLY ACTION METHODS
    # =============================================================================
    
    def action_configure_ams_accounts(self):
        """🔧 Manual account configuration wizard"""
        self.ensure_one()
        
        return {
            'name': _('Configure Revenue Accounts'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.account.wizard', 
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_ams_product_type': self.ams_product_type,
            }
        }
    
    def action_auto_configure_accounts(self):
        """🚀 One-click automatic account configuration"""
        for product in self:
            if not product.is_subscription_product:
                raise UserError(_('Revenue tracking is only available for subscription products.'))
            
            # Enable revenue tracking
            product.use_ams_accounting = True
            product.auto_create_recognition = True
            product.auto_process_recognition = True
            
            # Set up accounts automatically
            product._set_default_ams_accounts()
            
            # Validate the setup
            if product.ams_accounts_configured:
                message = _('✅ Revenue tracking configured successfully!\n\n'
                          'Your product is now set up for:\n'
                          '• Automatic revenue tracking\n'
                          '• Customer payment recording\n'
                          '• Financial reporting integration')
                message_type = 'success'
            else:
                missing_accounts = product._get_missing_accounts_list()
                message = _('⚠️ Partial configuration completed.\n\n'
                          'Still needed:\n%s\n\n'
                          'Use Manual Setup to complete configuration.') % '\n'.join(missing_accounts)
                message_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Revenue Setup Complete'),
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }
    
    def action_view_help_documentation(self):
        """📖 Show step-by-step setup guide"""
        self.ensure_one()
        
        # Return action to show documentation (could be improved with actual help system)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/ams_base_accounting/static/description/revenue_setup_guide.html',
            'target': 'new',
        }
    
    def action_validate_revenue_setup(self):
        """🔍 Validate current revenue setup and provide feedback"""
        self.ensure_one()
        
        validation_result = self.validate_ams_accounting_setup()
        
        if validation_result['status'] == 'complete':
            message = _('✅ Perfect! Your revenue setup is complete and ready to use.')
            message_type = 'success'
        elif validation_result['status'] == 'incomplete':
            message = _('⚠️ Setup Issues Found:\n\n%s\n\nWould you like to auto-fix these issues?') % validation_result['message']
            message_type = 'warning'
        else:
            message = validation_result['message']
            message_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Revenue Setup Validation'),
                'message': message,
                'type': message_type,
            }
        }
    
    def action_revenue_setup_wizard(self):
        """🧙‍♂️ Launch step-by-step setup wizard"""
        self.ensure_one()
        
        return {
            'name': _('Revenue Setup Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.revenue.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_product_type': self.ams_product_type,
                'default_subscription_period': self.subscription_period,
            }
        }
    
    # =============================================================================
    # HELPER METHODS (Enhanced for User Experience)
    # =============================================================================
    
    def _set_default_ams_accounts(self):
        """Set default AMS accounts based on product type with user-friendly feedback"""
        if not self.ams_product_type or self.ams_product_type == 'none':
            return
        
        # Only set accounts if they haven't been manually configured
        # This prevents overriding user choices
        accounts_already_configured = (
            self.ams_revenue_account_id and 
            self.ams_receivable_account_id
        )
        
        if accounts_already_configured:
            # Only set missing accounts, don't override existing ones
            pass
        
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
            
            # Set deferred account for annual subscriptions (if not already set)
            if (self.subscription_period in ['quarterly', 'semi_annual', 'annual'] and 
                not self.ams_deferred_account_id):
                deferred_account = self._find_account_by_category('deferred_revenue')
                if deferred_account:
                    self.ams_deferred_account_id = deferred_account.id
            
            # Set cash account if not already set
            if not self.ams_cash_account_id:
                cash_account = self._find_account_by_category('cash_membership')
                if cash_account:
                    self.ams_cash_account_id = cash_account.id
    
    def _get_missing_accounts_list(self):
        """Get user-friendly list of missing account configurations"""
        missing = []
        
        if not self.ams_revenue_account_id:
            missing.append('• Revenue Account (where earnings are recorded)')
        
        if not self.ams_receivable_account_id:
            missing.append('• Outstanding Invoices Account (customer payment tracking)')
        
        if (self.subscription_period in ['quarterly', 'semi_annual', 'annual'] and 
            not self.ams_deferred_account_id):
            missing.append('• Prepaid Revenue Account (for subscription advance payments)')
        
        if not self.ams_cash_account_id:
            missing.append('• Payment Deposits Account (recommended for complete tracking)')
        
        return missing
    
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
    # VALIDATION METHODS (Enhanced User Feedback)
    # =============================================================================
    
    @api.constrains('ams_revenue_account_id', 'ams_receivable_account_id')
    def _check_ams_accounts(self):
        """Validate AMS account configuration with user-friendly messages"""
        for product in self:
            if product.is_subscription_product and product.use_ams_accounting:
                if not product.ams_revenue_account_id:
                    raise UserError(_(
                        "💰 Revenue Account Required\n\n"
                        "Please select where revenue should be recorded for '%s'.\n\n"
                        "💡 Tip: Use the 'Auto-Configure' button for automatic setup."
                    ) % product.name)
                
                if not product.ams_receivable_account_id:
                    raise UserError(_(
                        "📋 Outstanding Invoices Account Required\n\n"
                        "Please select where customer payments should be tracked for '%s'.\n\n"
                        "💡 Tip: Use the 'Auto-Configure' button for automatic setup."
                    ) % product.name)
                
                # Validate account types with helpful messages
                if product.ams_revenue_account_id.account_type not in ['income', 'income_other']:
                    raise UserError(_(
                        "❌ Wrong Account Type\n\n"
                        "The Revenue Account for '%s' must be an Income account.\n"
                        "Currently selected: %s (%s)\n\n"
                        "💡 Tip: Look for accounts starting with '4' (Revenue accounts)."
                    ) % (product.name, product.ams_revenue_account_id.name, product.ams_revenue_account_id.account_type))
                
                if product.ams_receivable_account_id.account_type != 'asset_receivable':
                    raise UserError(_(
                        "❌ Wrong Account Type\n\n"
                        "The Outstanding Invoices Account for '%s' must be a Receivable account.\n"
                        "Currently selected: %s (%s)\n\n"
                        "💡 Tip: Look for accounts like 'Accounts Receivable' (usually code 1200)."
                    ) % (product.name, product.ams_receivable_account_id.name, product.ams_receivable_account_id.account_type))
    
    # =============================================================================
    # ENHANCED EXISTING METHODS
    # =============================================================================
    
    def validate_ams_accounting_setup(self):
        """Enhanced validation with user-friendly feedback"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'status': 'not_applicable', 'message': 'This is not a subscription product - revenue tracking not needed.'}
        
        if not self.use_ams_accounting:
            return {'status': 'disabled', 'message': 'Revenue tracking is not enabled for this product.'}
        
        issues = []
        
        if not self.ams_revenue_account_id:
            issues.append('💰 Missing Revenue Account')
        
        if not self.ams_receivable_account_id:
            issues.append('📋 Missing Outstanding Invoices Account')
        
        if (self.subscription_period in ['quarterly', 'semi_annual', 'annual'] and 
            not self.ams_deferred_account_id):
            issues.append('📊 Missing Prepaid Revenue Account (recommended for long-term subscriptions)')
        
        if not self.ams_cash_account_id:
            issues.append('💳 Missing Payment Deposits Account (recommended for complete tracking)')
        
        if issues:
            return {
                'status': 'incomplete',
                'message': f'Configuration needs attention:\n\n{chr(10).join(issues)}',
                'issues': issues
            }
        
        return {'status': 'complete', 'message': '✅ Revenue setup is properly configured and ready to use!'}
    
    # =============================================================================
    # INTEGRATION METHODS (For Revenue Recognition Module)
    # =============================================================================
    
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
    
    # Legacy method compatibility
    def setup_ams_accounting_configuration(self):
        """Legacy compatibility wrapper"""
        return self.action_auto_configure_accounts()
    
    def reset_ams_accounts(self):
        """Reset AMS account configuration with user-friendly feedback"""
        self.ensure_one()
        
        self.write({
            'ams_revenue_account_id': False,
            'ams_deferred_account_id': False,
            'ams_receivable_account_id': False,
            'ams_cash_account_id': False,
            'ams_expense_account_id': False,
            'use_ams_accounting': False,
            'auto_create_recognition': True,
            'auto_process_recognition': True,
            'ams_accounting_notes': '',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Revenue Setup Reset'),
                'message': _('🔄 Revenue setup has been reset.\n\nYou can now reconfigure it from scratch.'),
                'type': 'info',
            }
        }