# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSAccountingSetupWizard(models.TransientModel):
    """Wizard to set up AMS accounting for a company"""
    _name = 'ams.accounting.setup.wizard'
    _description = 'AMS Accounting Setup Wizard'
    
    # ==============================================
    # BASIC SETTINGS
    # ==============================================
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    setup_type = fields.Selection([
        ('quick', 'Quick Setup (Use Defaults)'),
        ('custom', 'Custom Setup'),
        ('existing', 'Use Existing Accounts'),
    ], string='Setup Type', required=True, default='quick',
       help='Choose how to set up AMS accounting')
    
    # ==============================================
    # ACCOUNT CREATION OPTIONS
    # ==============================================
    
    create_chart_of_accounts = fields.Boolean(
        string='Create AMS Chart of Accounts',
        default=True,
        help='Create default AMS chart of accounts'
    )
    
    create_journals = fields.Boolean(
        string='Create AMS Journals',
        default=True,
        help='Create default AMS journals'
    )
    
    # ==============================================
    # ACCOUNT SELECTIONS
    # ==============================================
    
    # Cash and Receivables
    cash_account_id = fields.Many2one(
        'ams.account.account',
        string='Cash Account',
        domain="[('account_type', '=', 'asset_cash'), ('company_id', '=', company_id)]",
        help='Account for cash receipts'
    )
    
    receivable_account_id = fields.Many2one(
        'ams.account.account',
        string='Accounts Receivable',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', company_id)]",
        help='Account for amounts owed by customers'
    )
    
    # Revenue Accounts
    individual_membership_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Individual Membership Revenue',
        domain="[('account_type', 'in', ['income', 'income_membership']), ('company_id', '=', company_id)]",
        help='Revenue account for individual memberships'
    )
    
    enterprise_membership_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Enterprise Membership Revenue',
        domain="[('account_type', 'in', ['income', 'income_membership']), ('company_id', '=', company_id)]",
        help='Revenue account for enterprise memberships'
    )
    
    chapter_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Chapter Revenue',
        domain="[('account_type', 'in', ['income', 'income_chapter']), ('company_id', '=', company_id)]",
        help='Revenue account for chapter subscriptions'
    )
    
    publication_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Publication Revenue',
        domain="[('account_type', 'in', ['income', 'income_publication']), ('company_id', '=', company_id)]",
        help='Revenue account for publication subscriptions'
    )
    
    # Deferred Revenue Accounts
    membership_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Membership Deferred Revenue',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]",
        help='Deferred revenue account for memberships'
    )
    
    chapter_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Chapter Deferred Revenue',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]",
        help='Deferred revenue account for chapters'
    )
    
    publication_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Publication Deferred Revenue',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]",
        help='Deferred revenue account for publications'
    )
    
    # Other Accounts
    bad_debt_account_id = fields.Many2one(
        'ams.account.account',
        string='Bad Debt Expense',
        domain="[('account_type', '=', 'expense'), ('company_id', '=', company_id)]",
        help='Account for bad debt expenses'
    )
    
    discount_account_id = fields.Many2one(
        'ams.account.account',
        string='Discount Account',
        domain="[('account_type', 'in', ['expense', 'income']), ('company_id', '=', company_id)]",
        help='Account for membership discounts'
    )
    
    # ==============================================
    # JOURNAL SELECTIONS
    # ==============================================
    
    membership_journal_id = fields.Many2one(
        'ams.account.journal',
        string='Membership Journal',
        domain="[('company_id', '=', company_id)]",
        help='Journal for membership transactions'
    )
    
    revenue_recognition_journal_id = fields.Many2one(
        'ams.account.journal',
        string='Revenue Recognition Journal',
        domain="[('company_id', '=', company_id)]",
        help='Journal for revenue recognition entries'
    )
    
    general_journal_id = fields.Many2one(
        'ams.account.journal',
        string='General Journal',
        domain="[('company_id', '=', company_id)]",
        help='General journal for adjustments'
    )
    
    # ==============================================
    # AUTOMATION SETTINGS
    # ==============================================
    
    auto_post_subscription_entries = fields.Boolean(
        string='Auto Post Subscription Entries',
        default=False,
        help='Automatically post journal entries for new subscriptions'
    )
    
    auto_post_revenue_recognition = fields.Boolean(
        string='Auto Post Revenue Recognition',
        default=True,
        help='Automatically post revenue recognition entries'
    )
    
    auto_create_revenue_recognition = fields.Boolean(
        string='Auto Create Revenue Recognition',
        default=True,
        help='Automatically create monthly revenue recognition entries'
    )
    
    revenue_recognition_day = fields.Integer(
        string='Revenue Recognition Day',
        default=31,
        help='Day of month to recognize revenue (31 = last day of month)'
    )
    
    # ==============================================
    # SETUP STATUS
    # ==============================================
    
    accounts_to_create = fields.Text(
        string='Accounts to Create',
        compute='_compute_accounts_to_create',
        help='List of accounts that will be created'
    )
    
    journals_to_create = fields.Text(
        string='Journals to Create',
        compute='_compute_journals_to_create',
        help='List of journals that will be created'
    )
    
    setup_summary = fields.Html(
        string='Setup Summary',
        compute='_compute_setup_summary',
        help='Summary of setup actions'
    )
    
    @api.depends('setup_type', 'create_chart_of_accounts', 'company_id')
    def _compute_accounts_to_create(self):
        """Compute list of accounts to create"""
        for wizard in self:
            if wizard.setup_type == 'quick' and wizard.create_chart_of_accounts:
                accounts = [
                    'Cash and Bank (1000)',
                    'Accounts Receivable (1200)',
                    'Membership A/R (1210)',
                    'Accounts Payable (2000)',
                    'Deferred Revenue - Memberships (2400)',
                    'Deferred Revenue - Publications (2410)',
                    'Deferred Revenue - Chapters (2420)',
                    'Retained Earnings (3000)',
                    'Individual Membership Revenue (4100)',
                    'Enterprise Membership Revenue (4110)',
                    'Chapter Revenue (4200)',
                    'Publication Revenue (4300)',
                    'Operating Expenses (5000)',
                    'Bad Debt Expense (5100)',
                ]
                wizard.accounts_to_create = '\n'.join(accounts)
            else:
                wizard.accounts_to_create = 'Using existing accounts or custom selection'
    
    @api.depends('setup_type', 'create_journals', 'company_id')
    def _compute_journals_to_create(self):
        """Compute list of journals to create"""
        for wizard in self:
            if wizard.setup_type == 'quick' and wizard.create_journals:
                journals = [
                    'Membership Sales (MEMB)',
                    'Chapter Operations (CHAP)',
                    'Publication Sales (PUB)',
                    'Revenue Recognition (REVR)',
                    'General Journal (GEN)',
                    'Cash Receipts (CASH)',
                ]
                wizard.journals_to_create = '\n'.join(journals)
            else:
                wizard.journals_to_create = 'Using existing journals or custom selection'
    
    @api.depends('setup_type', 'accounts_to_create', 'journals_to_create')
    def _compute_setup_summary(self):
        """Compute setup summary"""
        for wizard in self:
            summary_parts = ['<h4>AMS Accounting Setup Summary</h4>']
            
            if wizard.setup_type == 'quick':
                summary_parts.append('<p><strong>Setup Type:</strong> Quick Setup (Recommended)</p>')
                summary_parts.append('<p>This will create a complete AMS chart of accounts and journals with industry best practices.</p>')
            elif wizard.setup_type == 'custom':
                summary_parts.append('<p><strong>Setup Type:</strong> Custom Setup</p>')
                summary_parts.append('<p>You can customize which accounts and journals to create.</p>')
            else:
                summary_parts.append('<p><strong>Setup Type:</strong> Use Existing Accounts</p>')
                summary_parts.append('<p>Configure AMS to use your existing chart of accounts.</p>')
            
            if wizard.create_chart_of_accounts:
                summary_parts.append('<h5>Accounts to Create:</h5>')
                summary_parts.append(f'<pre>{wizard.accounts_to_create}</pre>')
            
            if wizard.create_journals:
                summary_parts.append('<h5>Journals to Create:</h5>')
                summary_parts.append(f'<pre>{wizard.journals_to_create}</pre>')
            
            summary_parts.append('<h5>Automation Settings:</h5>')
            summary_parts.append('<ul>')
            if wizard.auto_post_subscription_entries:
                summary_parts.append('<li>✓ Auto-post subscription entries</li>')
            if wizard.auto_post_revenue_recognition:
                summary_parts.append('<li>✓ Auto-post revenue recognition entries</li>')
            if wizard.auto_create_revenue_recognition:
                summary_parts.append('<li>✓ Auto-create monthly revenue recognition</li>')
            summary_parts.append('</ul>')
            
            wizard.setup_summary = ''.join(summary_parts)
    
    @api.onchange('setup_type')
    def _onchange_setup_type(self):
        """Update settings when setup type changes"""
        if self.setup_type == 'quick':
            self.create_chart_of_accounts = True
            self.create_journals = True
        elif self.setup_type == 'existing':
            self.create_chart_of_accounts = False
            self.create_journals = False
    
    @api.onchange('create_chart_of_accounts')
    def _onchange_create_chart_of_accounts(self):
        """Load existing accounts when not creating new ones"""
        if not self.create_chart_of_accounts and self.company_id:
            # Try to find existing accounts to suggest
            self._suggest_existing_accounts()
    
    def _suggest_existing_accounts(self):
        """Suggest existing accounts based on types"""
        account_obj = self.env['ams.account.account']
        
        # Find existing accounts by type
        cash_account = account_obj.search([
            ('account_type', '=', 'asset_cash'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if cash_account:
            self.cash_account_id = cash_account.id
        
        receivable_account = account_obj.search([
            ('account_type', '=', 'asset_receivable'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if receivable_account:
            self.receivable_account_id = receivable_account.id
        
        # Try to find revenue accounts
        revenue_accounts = account_obj.search([
            ('account_type', 'in', ['income', 'income_membership']),
            ('company_id', '=', self.company_id.id)
        ])
        
        if revenue_accounts:
            self.individual_membership_revenue_account_id = revenue_accounts[0].id
            if len(revenue_accounts) > 1:
                self.enterprise_membership_revenue_account_id = revenue_accounts[1].id
        
        # Deferred revenue accounts
        deferred_accounts = account_obj.search([
            ('account_type', '=', 'liability_deferred_revenue'),
            ('company_id', '=', self.company_id.id)
        ])
        
        if deferred_accounts:
            self.membership_deferred_revenue_account_id = deferred_accounts[0].id
    
    def action_setup_accounting(self):
        """Execute the accounting setup"""
        self.ensure_one()
        
        if not self.company_id:
            raise UserError('Company is required')
        
        created_items = {
            'accounts': [],
            'journals': [],
            'errors': []
        }
        
        try:
            # Step 1: Create chart of accounts if requested
            if self.create_chart_of_accounts:
                created_accounts = self._create_chart_of_accounts()
                created_items['accounts'] = created_accounts
            
            # Step 2: Create journals if requested
            if self.create_journals:
                created_journals = self._create_journals()
                created_items['journals'] = created_journals
            
            # Step 3: Configure company settings
            self._configure_company_settings(created_items)
            
            # Step 4: Configure automation settings
            self._configure_automation_settings()
            
            # Step 5: Mark setup as complete
            self.company_id.ams_chart_of_accounts_installed = True
            
            return self._show_success_message(created_items)
            
        except Exception as e:
            created_items['errors'].append(str(e))
            return self._show_error_message(created_items)
    
    def _create_chart_of_accounts(self):
        """Create AMS chart of accounts"""
        account_obj = self.env['ams.account.account']
        
        if self.setup_type == 'quick':
            # Use default chart of accounts
            return account_obj.create_default_accounts(self.company_id.id)
        else:
            # Create only selected accounts
            created_accounts = self.env['ams.account.account']
            
            # This would be expanded for custom account creation
            # For now, use default creation
            return account_obj.create_default_accounts(self.company_id.id)
    
    def _create_journals(self):
        """Create AMS journals"""
        journal_obj = self.env['ams.account.journal']
        
        if self.setup_type == 'quick':
            # Use default journals
            return journal_obj.create_default_journals(self.company_id.id)
        else:
            # Create only selected journals
            created_journals = self.env['ams.account.journal']
            
            # This would be expanded for custom journal creation
            # For now, use default creation
            return journal_obj.create_default_journals(self.company_id.id)
    
    def _configure_company_settings(self, created_items):
        """Configure company AMS accounting settings"""
        company = self.company_id
        
        # Get created or selected accounts
        if self.create_chart_of_accounts and created_items['accounts']:
            # Map created accounts to company settings
            account_mapping = {
                '1000': 'ams_default_cash_account_id',
                '1200': 'ams_default_receivable_account_id',
                '4100': 'individual_membership_revenue_account_id',
                '4110': 'enterprise_membership_revenue_account_id',
                '4200': 'chapter_revenue_account_id',
                '4300': 'publication_revenue_account_id',
                '2400': 'membership_deferred_revenue_account_id',
                '2410': 'publication_deferred_revenue_account_id',
                '2420': 'chapter_deferred_revenue_account_id',
                '5100': 'ams_bad_debt_account_id',
            }
            
            updates = {}
            for account in created_items['accounts']:
                if account.code in account_mapping:
                    field_name = account_mapping[account.code]
                    updates[field_name] = account.id
            
            # Set general defaults
            revenue_account = created_items['accounts'].filtered(lambda a: a.code == '4100')
            if revenue_account:
                updates['ams_default_revenue_account_id'] = revenue_account[0].id
            
            deferred_account = created_items['accounts'].filtered(lambda a: a.code == '2400')
            if deferred_account:
                updates['ams_default_deferred_revenue_account_id'] = deferred_account[0].id
            
            company.write(updates)
        else:
            # Use manually selected accounts
            updates = {
                'ams_default_cash_account_id': self.cash_account_id.id if self.cash_account_id else False,
                'ams_default_receivable_account_id': self.receivable_account_id.id if self.receivable_account_id else False,
                'individual_membership_revenue_account_id': self.individual_membership_revenue_account_id.id if self.individual_membership_revenue_account_id else False,
                'enterprise_membership_revenue_account_id': self.enterprise_membership_revenue_account_id.id if self.enterprise_membership_revenue_account_id else False,
                'chapter_revenue_account_id': self.chapter_revenue_account_id.id if self.chapter_revenue_account_id else False,
                'publication_revenue_account_id': self.publication_revenue_account_id.id if self.publication_revenue_account_id else False,
                'membership_deferred_revenue_account_id': self.membership_deferred_revenue_account_id.id if self.membership_deferred_revenue_account_id else False,
                'chapter_deferred_revenue_account_id': self.chapter_deferred_revenue_account_id.id if self.chapter_deferred_revenue_account_id else False,
                'publication_deferred_revenue_account_id': self.publication_deferred_revenue_account_id.id if self.publication_deferred_revenue_account_id else False,
                'ams_bad_debt_account_id': self.bad_debt_account_id.id if self.bad_debt_account_id else False,
                'ams_discount_account_id': self.discount_account_id.id if self.discount_account_id else False,
            }
            
            # Set general defaults
            if self.individual_membership_revenue_account_id:
                updates['ams_default_revenue_account_id'] = self.individual_membership_revenue_account_id.id
            if self.membership_deferred_revenue_account_id:
                updates['ams_default_deferred_revenue_account_id'] = self.membership_deferred_revenue_account_id.id
            
            company.write(updates)
        
        # Configure journals
        if self.create_journals and created_items['journals']:
            journal_mapping = {
                'MEMB': 'default_membership_journal_id',
                'REVR': 'default_revenue_recognition_journal_id',
            }
            
            journal_updates = {}
            for journal in created_items['journals']:
                if journal.code in journal_mapping:
                    field_name = journal_mapping[journal.code]
                    journal_updates[field_name] = journal.id
            
            if journal_updates:
                company.write(journal_updates)
        else:
            # Use manually selected journals
            journal_updates = {
                'default_membership_journal_id': self.membership_journal_id.id if self.membership_journal_id else False,
                'default_revenue_recognition_journal_id': self.revenue_recognition_journal_id.id if self.revenue_recognition_journal_id else False,
            }
            company.write(journal_updates)
    
    def _configure_automation_settings(self):
        """Configure automation settings"""
        company = self.company_id
        
        automation_updates = {
            'auto_post_subscription_entries': self.auto_post_subscription_entries,
            'auto_post_revenue_recognition': self.auto_post_revenue_recognition,
            'auto_create_revenue_recognition': self.auto_create_revenue_recognition,
            'revenue_recognition_day': self.revenue_recognition_day,
        }
        
        company.write(automation_updates)
    
    def _show_success_message(self, created_items):
        """Show success message with details"""
        message_parts = ['<h4>AMS Accounting Setup Complete!</h4>']
        
        if created_items['accounts']:
            message_parts.append(f'<p><strong>Created {len(created_items["accounts"])} accounts:</strong></p>')
            message_parts.append('<ul>')
            for account in created_items['accounts'][:10]:  # Limit display
                message_parts.append(f'<li>[{account.code}] {account.name}</li>')
            if len(created_items['accounts']) > 10:
                message_parts.append(f'<li>... and {len(created_items["accounts"]) - 10} more</li>')
            message_parts.append('</ul>')
        
        if created_items['journals']:
            message_parts.append(f'<p><strong>Created {len(created_items["journals"])} journals:</strong></p>')
            message_parts.append('<ul>')
            for journal in created_items['journals']:
                message_parts.append(f'<li>[{journal.code}] {journal.name}</li>')
            message_parts.append('</ul>')
        
        message_parts.append('<p>Your AMS accounting system is now ready to use!</p>')
        message_parts.append('<p>You can:</p>')
        message_parts.append('<ul>')
        message_parts.append('<li>Create subscription products with financial settings</li>')
        message_parts.append('<li>Process subscription payments with automatic journal entries</li>')
        message_parts.append('<li>Set up automated revenue recognition</li>')
        message_parts.append('<li>View financial reports and analytics</li>')
        message_parts.append('</ul>')
        
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
    
    def _show_error_message(self, created_items):
        """Show error message with details"""
        message_parts = ['<h4>AMS Accounting Setup Encountered Errors</h4>']
        
        if created_items['errors']:
            message_parts.append('<p><strong>Errors:</strong></p>')
            message_parts.append('<ul>')
            for error in created_items['errors']:
                message_parts.append(f'<li>{error}</li>')
            message_parts.append('</ul>')
        
        if created_items['accounts']:
            message_parts.append(f'<p>Successfully created {len(created_items["accounts"])} accounts before error.</p>')
        
        if created_items['journals']:
            message_parts.append(f'<p>Successfully created {len(created_items["journals"])} journals before error.</p>')
        
        message_parts.append('<p>Please review the errors and try again, or contact support.</p>')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Setup Errors',
                'message': ''.join(message_parts),
                'type': 'danger',
                'sticky': True,
            }
        }
    
    def action_validate_setup(self):
        """Validate the setup configuration"""
        self.ensure_one()
        
        issues = []
        warnings = []
        
        # Check if accounts are selected or will be created
        if not self.create_chart_of_accounts:
            # Check manual selections
            if not self.cash_account_id:
                issues.append('Cash account must be selected')
            if not self.receivable_account_id:
                issues.append('Receivable account must be selected')
            if not self.individual_membership_revenue_account_id:
                issues.append('Individual membership revenue account must be selected')
            if not self.membership_deferred_revenue_account_id:
                warnings.append('Deferred revenue account recommended for subscriptions')
        
        # Check journal setup
        if not self.create_journals:
            if not self.membership_journal_id:
                issues.append('Membership journal must be selected')
            if not self.revenue_recognition_journal_id and self.auto_create_revenue_recognition:
                issues.append('Revenue recognition journal required for automation')
        
        # Show validation results
        if issues or warnings:
            return self._show_validation_results(issues, warnings)
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Validation Passed',
                    'message': '✓ Configuration is valid and ready for setup!',
                    'type': 'success',
                }
            }
    
    def _show_validation_results(self, issues, warnings):
        """Show validation results"""
        message_parts = ['<h4>Setup Validation Results</h4>']
        
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
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Results',
                'message': ''.join(message_parts),
                'type': 'warning' if issues else 'info',
                'sticky': True,
            }
        }
    
    def action_preview_setup(self):
        """Preview what will be created"""
        self.ensure_one()
        
        preview_content = f"""
        <div class="o_form_view">
            <h3>AMS Accounting Setup Preview</h3>
            
            <h4>Setup Configuration:</h4>
            <ul>
                <li><strong>Company:</strong> {self.company_id.name}</li>
                <li><strong>Setup Type:</strong> {dict(self._fields['setup_type'].selection)[self.setup_type]}</li>
                <li><strong>Create Chart of Accounts:</strong> {'Yes' if self.create_chart_of_accounts else 'No'}</li>
                <li><strong>Create Journals:</strong> {'Yes' if self.create_journals else 'No'}</li>
            </ul>
            
            {self.setup_summary}
            
            <p><em>Click "Setup Accounting" to proceed with this configuration.</em></p>
        </div>
        """
        
        return {
            'name': 'Setup Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.accounting.setup.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_content': preview_content,
                'default_wizard_id': self.id,
            }
        }


class AMSAccountingSetupPreview(models.TransientModel):
    """Preview wizard for accounting setup"""
    _name = 'ams.accounting.setup.preview'
    _description = 'AMS Accounting Setup Preview'
    
    preview_content = fields.Html(
        string='Preview',
        readonly=True
    )
    
    wizard_id = fields.Many2one(
        'ams.accounting.setup.wizard',
        string='Setup Wizard'
    )
    
    def action_proceed_with_setup(self):
        """Proceed with the setup"""
        if self.wizard_id:
            return self.wizard_id.action_setup_accounting()
        return {'type': 'ir.actions.act_window_close'}
    
    def action_back_to_wizard(self):
        """Go back to setup wizard"""
        if self.wizard_id:
            return {
                'name': 'AMS Accounting Setup',
                'type': 'ir.actions.act_window',
                'res_model': 'ams.accounting.setup.wizard',
                'res_id': self.wizard_id.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return {'type': 'ir.actions.act_window_close'}