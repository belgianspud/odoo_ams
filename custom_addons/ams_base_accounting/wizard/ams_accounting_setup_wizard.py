# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSAccountingSetupWizard(models.TransientModel):
    """Main wizard for setting up AMS accounting"""
    _name = 'ams.accounting.setup.wizard'
    _description = 'AMS Accounting Setup Wizard'
    
    # Setup Type
    setup_type = fields.Selection([
        ('quick', 'Quick Setup'),
        ('advanced', 'Advanced Setup'),
        ('company_setup', 'Company Setup'),
        ('chart_install', 'Install Chart of Accounts'),
    ], string='Setup Type', required=True, default='quick')
    
    # Company Information
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    company_name = fields.Char(
        string='Company Name',
        related='company_id.name',
        readonly=True
    )
    
    # Chart of Accounts
    install_chart = fields.Boolean(
        string='Install AMS Chart of Accounts',
        default=True,
        help="Install the standard AMS chart of accounts"
    )
    
    chart_template = fields.Selection([
        ('ams_standard', 'AMS Standard Chart'),
        ('ams_medical', 'AMS Medical Association Chart'),
        ('ams_professional', 'AMS Professional Association Chart'),
        ('custom', 'Custom Chart'),
    ], string='Chart Template', default='ams_standard')
    
    # Journal Setup
    create_journals = fields.Boolean(
        string='Create Default Journals',
        default=True,
        help="Create standard journals for association accounting"
    )
    
    # Account Configuration
    setup_default_accounts = fields.Boolean(
        string='Setup Default Accounts',
        default=True,
        help="Configure default accounts in company settings"
    )
    
    # Currency and Localization
    currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True
    )
    
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        related='company_id.country_id',
        readonly=True
    )
    
    # Automation Settings
    enable_automation = fields.Boolean(
        string='Enable Automation',
        default=True,
        help="Enable automated accounting processes"
    )
    
    auto_post_entries = fields.Boolean(
        string='Auto-Post Journal Entries',
        default=True,
        help="Automatically post journal entries when created"
    )
    
    auto_revenue_recognition = fields.Boolean(
        string='Auto Revenue Recognition',
        default=True,
        help="Automatically create revenue recognition entries"
    )
    
    # Revenue Recognition Settings
    default_recognition_method = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Default Recognition Method', default='monthly')
    
    recognition_day = fields.Integer(
        string='Recognition Day',
        default=31,
        help="Day of month for revenue recognition (31 = last day)"
    )
    
    # Setup Progress
    setup_step = fields.Integer(string='Setup Step', default=1)
    total_steps = fields.Integer(string='Total Steps', default=5)
    
    setup_complete = fields.Boolean(
        string='Setup Complete',
        default=False,
        readonly=True
    )
    
    # Setup Results
    created_accounts_count = fields.Integer(
        string='Accounts Created',
        readonly=True
    )
    
    created_journals_count = fields.Integer(
        string='Journals Created',
        readonly=True
    )
    
    setup_log = fields.Text(
        string='Setup Log',
        readonly=True
    )
    
    # Validation
    has_existing_accounts = fields.Boolean(
        string='Has Existing Accounts',
        compute='_compute_existing_data'
    )
    
    has_existing_journals = fields.Boolean(
        string='Has Existing Journals',
        compute='_compute_existing_data'
    )
    
    can_proceed = fields.Boolean(
        string='Can Proceed',
        compute='_compute_can_proceed'
    )
    
    warning_message = fields.Text(
        string='Warning Message',
        compute='_compute_can_proceed'
    )
    
    @api.depends('company_id')
    def _compute_existing_data(self):
        """Check for existing accounting data"""
        for wizard in self:
            if wizard.company_id:
                # Check for existing accounts
                existing_accounts = self.env['ams.account.account'].search_count([
                    ('company_id', '=', wizard.company_id.id)
                ])
                wizard.has_existing_accounts = existing_accounts > 0
                
                # Check for existing journals
                existing_journals = self.env['ams.account.journal'].search_count([
                    ('company_id', '=', wizard.company_id.id)
                ])
                wizard.has_existing_journals = existing_journals > 0
            else:
                wizard.has_existing_accounts = False
                wizard.has_existing_journals = False
    
    @api.depends('has_existing_accounts', 'has_existing_journals', 'install_chart')
    def _compute_can_proceed(self):
        """Check if setup can proceed"""
        for wizard in self:
            warnings = []
            can_proceed = True
            
            if wizard.install_chart and wizard.has_existing_accounts:
                warnings.append(
                    "⚠️  Company already has accounts configured. "
                    "Installing chart may create duplicates."
                )
                can_proceed = False
            
            if wizard.create_journals and wizard.has_existing_journals:
                warnings.append(
                    "⚠️  Company already has journals configured. "
                    "Creating journals may create duplicates."
                )
            
            if wizard.company_id.ams_accounting_setup_complete:
                warnings.append(
                    "ℹ️  AMS Accounting is already set up for this company. "
                    "This will update existing configuration."
                )
            
            wizard.can_proceed = can_proceed
            wizard.warning_message = '\n'.join(warnings) if warnings else ''
    
    @api.onchange('setup_type')
    def _onchange_setup_type(self):
        """Update settings based on setup type"""
        if self.setup_type == 'quick':
            self.install_chart = True
            self.create_journals = True
            self.setup_default_accounts = True
            self.enable_automation = True
            self.auto_post_entries = True
            self.auto_revenue_recognition = True
        elif self.setup_type == 'advanced':
            # Let user choose settings
            pass
        elif self.setup_type == 'chart_install':
            self.install_chart = True
            self.create_journals = False
            self.setup_default_accounts = False
    
    # Action Methods
    def action_start_setup(self):
        """Start the setup process"""
        self.ensure_one()
        
        if not self.can_proceed and self.setup_type != 'advanced':
            raise UserError(f"Cannot proceed with setup:\n{self.warning_message}")
        
        # Reset progress
        self.write({
            'setup_step': 1,
            'setup_complete': False,
            'setup_log': 'Starting AMS Accounting Setup...\n',
        })
        
        return self._continue_setup()
    
    def _continue_setup(self):
        """Continue with setup process"""
        self.ensure_one()
        log_messages = [self.setup_log or '']
        
        try:
            # Step 1: Install Chart of Accounts
            if self.setup_step == 1 and self.install_chart:
                log_messages.append("Step 1/5: Installing Chart of Accounts...")
                accounts_created = self._install_chart_of_accounts()
                self.created_accounts_count = accounts_created
                log_messages.append(f"✓ Created {accounts_created} accounts")
                self.setup_step = 2
            
            # Step 2: Create Journals
            elif self.setup_step <= 2 and self.create_journals:
                log_messages.append("Step 2/5: Creating Default Journals...")
                journals_created = self._create_default_journals()
                self.created_journals_count = journals_created
                log_messages.append(f"✓ Created {journals_created} journals")
                self.setup_step = 3
            
            # Step 3: Setup Default Accounts
            elif self.setup_step <= 3 and self.setup_default_accounts:
                log_messages.append("Step 3/5: Configuring Default Accounts...")
                self._setup_default_accounts()
                log_messages.append("✓ Default accounts configured")
                self.setup_step = 4
            
            # Step 4: Configure Automation
            elif self.setup_step <= 4 and self.enable_automation:
                log_messages.append("Step 4/5: Configuring Automation...")
                self._configure_automation()
                log_messages.append("✓ Automation configured")
                self.setup_step = 5
            
            # Step 5: Finalize Setup
            elif self.setup_step <= 5:
                log_messages.append("Step 5/5: Finalizing Setup...")
                self._finalize_setup()
                log_messages.append("✅ AMS Accounting Setup Complete!")
                self.setup_complete = True
            
            # Update log
            self.setup_log = '\n'.join(log_messages)
            
            if self.setup_complete:
                return self._show_completion()
            else:
                return self._continue_setup()
        
        except Exception as e:
            log_messages.append(f"❌ Error in step {self.setup_step}: {str(e)}")
            self.setup_log = '\n'.join(log_messages)
            raise UserError(f"Setup failed at step {self.setup_step}: {str(e)}")
    
    def _install_chart_of_accounts(self):
        """Install the chart of accounts"""
        accounts_created = 0
        
        if self.chart_template == 'ams_standard':
            # Create standard AMS accounts
            account_data = [
                # Assets
                ('1000', 'Cash and Bank', 'asset_cash', 'general'),
                ('1200', 'Accounts Receivable', 'asset_receivable', 'general'),
                ('1300', 'Prepaid Expenses', 'asset_prepayments', 'general'),
                ('1500', 'Fixed Assets', 'asset_fixed', 'general'),
                
                # Liabilities
                ('2000', 'Accounts Payable', 'liability_payable', 'general'),
                ('2400', 'Deferred Revenue - Memberships', 'liability_deferred_revenue', 'membership'),
                ('2410', 'Deferred Revenue - Publications', 'liability_deferred_revenue', 'publication'),
                ('2420', 'Deferred Revenue - Chapters', 'liability_deferred_revenue', 'chapter'),
                
                # Equity
                ('3000', 'Net Assets', 'equity', 'general'),
                ('3900', 'Current Year Earnings', 'equity_unaffected', 'general'),
                
                # Income
                ('4100', 'Individual Membership Revenue', 'income_membership', 'membership'),
                ('4110', 'Enterprise Membership Revenue', 'income_membership', 'membership'),
                ('4200', 'Chapter Revenue', 'income_chapter', 'chapter'),
                ('4300', 'Publication Revenue', 'income_publication', 'publication'),
                ('4400', 'Event Revenue', 'income_other', 'event'),
                ('4900', 'Other Income', 'income_other', 'general'),
                
                # Expenses
                ('5100', 'Bad Debt Expense', 'expense', 'general'),
                ('5200', 'Program Expenses', 'expense', 'general'),
                ('5300', 'Administrative Expenses', 'expense', 'general'),
                ('5400', 'Marketing Expenses', 'expense', 'general'),
            ]
            
            for code, name, account_type, ams_category in account_data:
                # Check if account exists
                existing = self.env['ams.account.account'].search([
                    ('code', '=', code),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                
                if not existing:
                    self.env['ams.account.account'].create({
                        'code': code,
                        'name': name,
                        'account_type': account_type,
                        'ams_category': ams_category,
                        'company_id': self.company_id.id,
                    })
                    accounts_created += 1
        
        return accounts_created
    
    def _create_default_journals(self):
        """Create default journals"""
        journals_created = 0
        
        journal_data = [
            ('MEMB', 'Membership Sales', 'sale', 'membership'),
            ('CHAP', 'Chapter Operations', 'general', 'chapter'),
            ('PUB', 'Publication Sales', 'sale', 'publication'),
            ('REV', 'Revenue Recognition', 'general', 'revenue_recognition'),
            ('CASH', 'Cash Receipts', 'cash', 'general'),
            ('GEN', 'General Journal', 'general', 'general'),
        ]
        
        for code, name, journal_type, ams_type in journal_data:
            # Check if journal exists
            existing = self.env['ams.account.journal'].search([
                ('code', '=', code),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if not existing:
                self.env['ams.account.journal'].create({
                    'code': code,
                    'name': name,
                    'type': journal_type,
                    'ams_journal_type': ams_type,
                    'company_id': self.company_id.id,
                })
                journals_created += 1
        
        return journals_created
    
    def _setup_default_accounts(self):
        """Setup default accounts in company settings"""
        company = self.company_id
        
        # Find key accounts
        accounts = {
            'cash': self.env['ams.account.account'].search([
                ('code', '=', '1000'),
                ('company_id', '=', company.id)
            ], limit=1),
            'receivable': self.env['ams.account.account'].search([
                ('code', '=', '1200'),
                ('company_id', '=', company.id)
            ], limit=1),
            'individual_membership': self.env['ams.account.account'].search([
                ('code', '=', '4100'),
                ('company_id', '=', company.id)
            ], limit=1),
            'enterprise_membership': self.env['ams.account.account'].search([
                ('code', '=', '4110'),
                ('company_id', '=', company.id)
            ], limit=1),
            'chapter_revenue': self.env['ams.account.account'].search([
                ('code', '=', '4200'),
                ('company_id', '=', company.id)
            ], limit=1),
            'publication_revenue': self.env['ams.account.account'].search([
                ('code', '=', '4300'),
                ('company_id', '=', company.id)
            ], limit=1),
            'membership_deferred': self.env['ams.account.account'].search([
                ('code', '=', '2400'),
                ('company_id', '=', company.id)
            ], limit=1),
            'chapter_deferred': self.env['ams.account.account'].search([
                ('code', '=', '2420'),
                ('company_id', '=', company.id)
            ], limit=1),
            'publication_deferred': self.env['ams.account.account'].search([
                ('code', '=', '2410'),
                ('company_id', '=', company.id)
            ], limit=1),
        }
        
        # Find key journals
        journals = {
            'membership': self.env['ams.account.journal'].search([
                ('code', '=', 'MEMB'),
                ('company_id', '=', company.id)
            ], limit=1),
            'revenue_recognition': self.env['ams.account.journal'].search([
                ('code', '=', 'REV'),
                ('company_id', '=', company.id)
            ], limit=1),
            'chapter': self.env['ams.account.journal'].search([
                ('code', '=', 'CHAP'),
                ('company_id', '=', company.id)
            ], limit=1),
            'publication': self.env['ams.account.journal'].search([
                ('code', '=', 'PUB'),
                ('company_id', '=', company.id)
            ], limit=1),
            'cash': self.env['ams.account.journal'].search([
                ('code', '=', 'CASH'),
                ('company_id', '=', company.id)
            ], limit=1),
            'general': self.env['ams.account.journal'].search([
                ('code', '=', 'GEN'),
                ('company_id', '=', company.id)
            ], limit=1),
        }
        
        # Update company settings
        company_vals = {}
        
        if accounts['cash']:
            company_vals['ams_default_cash_account_id'] = accounts['cash'].id
        if accounts['receivable']:
            company_vals['ams_default_receivable_account_id'] = accounts['receivable'].id
        if accounts['individual_membership']:
            company_vals['individual_membership_revenue_account_id'] = accounts['individual_membership'].id
        if accounts['enterprise_membership']:
            company_vals['enterprise_membership_revenue_account_id'] = accounts['enterprise_membership'].id
        if accounts['chapter_revenue']:
            company_vals['chapter_revenue_account_id'] = accounts['chapter_revenue'].id
        if accounts['publication_revenue']:
            company_vals['publication_revenue_account_id'] = accounts['publication_revenue'].id
        if accounts['membership_deferred']:
            company_vals['membership_deferred_revenue_account_id'] = accounts['membership_deferred'].id
        if accounts['chapter_deferred']:
            company_vals['chapter_deferred_revenue_account_id'] = accounts['chapter_deferred'].id
        if accounts['publication_deferred']:
            company_vals['publication_deferred_revenue_account_id'] = accounts['publication_deferred'].id
        
        if journals['membership']:
            company_vals['default_membership_journal_id'] = journals['membership'].id
        if journals['revenue_recognition']:
            company_vals['default_revenue_recognition_journal_id'] = journals['revenue_recognition'].id
        if journals['chapter']:
            company_vals['default_chapter_journal_id'] = journals['chapter'].id
        if journals['publication']:
            company_vals['default_publication_journal_id'] = journals['publication'].id
        if journals['cash']:
            company_vals['default_cash_journal_id'] = journals['cash'].id
        if journals['general']:
            company_vals['default_general_journal_id'] = journals['general'].id
        
        if company_vals:
            company.write(company_vals)
    
    def _configure_automation(self):
        """Configure automation settings"""
        company = self.company_id
        
        automation_vals = {
            'auto_post_subscription_entries': self.auto_post_entries,
            'auto_post_revenue_recognition': self.auto_post_entries,
            'auto_create_revenue_recognition': self.auto_revenue_recognition,
            'revenue_recognition_method': self.default_recognition_method,
            'revenue_recognition_day': self.recognition_day,
        }
        
        company.write(automation_vals)
    
    def _finalize_setup(self):
        """Finalize the setup"""
        company = self.company_id
        
        # Mark setup as complete
        company.write({
            'ams_accounting_setup_complete': True,
            'ams_chart_of_accounts_installed': True,
        })
        
        # Create sequences if needed
        self._create_sequences()
    
    def _create_sequences(self):
        """Create necessary sequences"""
        sequences_to_create = [
            ('ams.revenue.recognition', 'Revenue Recognition', 'RR'),
            ('ams.revenue.recognition.schedule', 'Revenue Recognition Schedule', 'RRS'),
        ]
        
        for code, name, prefix in sequences_to_create:
            existing = self.env['ir.sequence'].search([
                ('code', '=', code),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if not existing:
                self.env['ir.sequence'].create({
                    'name': name,
                    'code': code,
                    'prefix': f'{prefix}/%(year)s/',
                    'padding': 4,
                    'company_id': self.company_id.id,
                })
    
    def _show_completion(self):
        """Show setup completion"""
        return {
            'name': 'AMS Accounting Setup Complete',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.accounting.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_completion': True}
        }
    
    def action_finish(self):
        """Finish the setup"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_open_dashboard(self):
        """Open the accounting dashboard"""
        return {
            'name': 'AMS Accounting',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.journal',
            'view_mode': 'kanban',
            'domain': [('show_on_dashboard', '=', True)],
            'context': {'search_default_dashboard': 1}
        }