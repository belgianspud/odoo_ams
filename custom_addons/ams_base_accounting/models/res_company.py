# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # ==============================================
    # AMS ACCOUNTING CONFIGURATION
    # ==============================================
    
    # Default GL Accounts for AMS
    ams_default_cash_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Cash Account',
        domain="[('account_type', '=', 'asset_cash'), ('company_id', '=', id)]",
        help='Default cash account for AMS transactions'
    )
    
    ams_default_receivable_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Receivable Account',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', id)]",
        help='Default accounts receivable account for AMS'
    )
    
    ams_default_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_membership']), ('company_id', '=', id)]",
        help='Default revenue account for AMS'
    )
    
    ams_default_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Default Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', id)]",
        help='Default deferred revenue account for subscriptions'
    )
    
    # Membership-specific accounts
    individual_membership_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Individual Membership Revenue Account',
        domain="[('account_type', 'in', ['income_membership', 'income']), ('company_id', '=', id)]",
        help='Revenue account for individual memberships'
    )
    
    enterprise_membership_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Enterprise Membership Revenue Account',
        domain="[('account_type', 'in', ['income_membership', 'income']), ('company_id', '=', id)]",
        help='Revenue account for enterprise memberships'
    )
    
    chapter_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Chapter Revenue Account',
        domain="[('account_type', 'in', ['income_chapter', 'income']), ('company_id', '=', id)]",
        help='Revenue account for chapter subscriptions'
    )
    
    publication_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Publication Revenue Account',
        domain="[('account_type', 'in', ['income_publication', 'income']), ('company_id', '=', id)]",
        help='Revenue account for publication subscriptions'
    )
    
    # Deferred revenue accounts by type
    membership_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Membership Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', id)]",
        help='Deferred revenue account for memberships'
    )
    
    chapter_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Chapter Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', id)]",
        help='Deferred revenue account for chapters'
    )
    
    publication_deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Publication Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', id)]",
        help='Deferred revenue account for publications'
    )
    
    # Bad debt and adjustments
    ams_bad_debt_account_id = fields.Many2one(
        'ams.account.account',
        string='Bad Debt Expense Account',
        domain="[('account_type', '=', 'expense'), ('company_id', '=', id)]",
        help='Account for bad debt expenses'
    )
    
    ams_discount_account_id = fields.Many2one(
        'ams.account.account',
        string='Discount Account',
        domain="[('account_type', 'in', ['expense', 'income']), ('company_id', '=', id)]",
        help='Account for membership discounts'
    )
    
    # ==============================================
    # REVENUE RECOGNITION SETTINGS
    # ==============================================
    
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Recognize Immediately'),
        ('deferred', 'Deferred Recognition'),
        ('subscription', 'Subscription-based'),
    ], string='Default Revenue Recognition Method', 
       default='subscription',
       help='Default method for revenue recognition')
    
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
    # JOURNAL SETTINGS
    # ==============================================
    
    default_membership_journal_id = fields.Many2one(
        'ams.account.journal',
        string='Default Membership Journal',
        domain="[('type', 'in', ['membership', 'sale']), ('company_id', '=', id)]",
        help='Default journal for membership transactions'
    )
    
    default_revenue_recognition_journal_id = fields.Many2one(
        'ams.account.journal',
        string='Default Revenue Recognition Journal',
        domain="[('type', 'in', ['deferred_revenue', 'general']), ('company_id', '=', id)]",
        help='Default journal for revenue recognition entries'
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
    
    # ==============================================
    # FISCAL SETTINGS
    # ==============================================
    
    ams_fiscal_year_start = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Fiscal Year Start Month', default='01',
       help='Month when fiscal year starts for AMS reporting')
    
    # ==============================================
    # SETUP STATUS
    # ==============================================
    
    ams_accounting_setup_complete = fields.Boolean(
        string='AMS Accounting Setup Complete',
        compute='_compute_ams_accounting_setup_complete',
        help='All required AMS accounting accounts and settings are configured'
    )
    
    ams_chart_of_accounts_installed = fields.Boolean(
        string='AMS Chart of Accounts Installed',
        default=False,
        help='AMS chart of accounts has been installed'
    )
    
    @api.depends(
        'ams_default_cash_account_id', 'ams_default_receivable_account_id',
        'ams_default_revenue_account_id', 'ams_default_deferred_revenue_account_id',
        'default_membership_journal_id', 'default_revenue_recognition_journal_id'
    )
    def _compute_ams_accounting_setup_complete(self):
        """Check if AMS accounting setup is complete"""
        for company in self:
            required_accounts = [
                'ams_default_cash_account_id',
                'ams_default_receivable_account_id', 
                'ams_default_revenue_account_id',
                'ams_default_deferred_revenue_account_id'
            ]
            
            required_journals = [
                'default_membership_journal_id',
                'default_revenue_recognition_journal_id'
            ]
            
            accounts_complete = all(getattr(company, field) for field in required_accounts)
            journals_complete = all(getattr(company, field) for field in required_journals)
            
            company.ams_accounting_setup_complete = accounts_complete and journals_complete
    
    def action_setup_ams_accounting(self):
        """Action to set up AMS accounting"""
        self.ensure_one()
        
        return {
            'name': 'AMS Accounting Setup',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.accounting.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_company_id': self.id,
            }
        }
    
    def action_install_ams_chart_of_accounts(self):
        """Install AMS chart of accounts"""
        self.ensure_one()
        
        if self.ams_chart_of_accounts_installed:
            raise UserError('AMS chart of accounts is already installed')
        
        # Create default accounts
        account_obj = self.env['ams.account.account']
        created_accounts = account_obj.create_default_accounts(self.id)
        
        # Create default journals
        journal_obj = self.env['ams.account.journal']
        created_journals = journal_obj.create_default_journals(self.id)
        
        # Update company settings with created accounts and journals
        self._update_default_accounts(created_accounts, created_journals)
        
        # Mark as installed
        self.ams_chart_of_accounts_installed = True
        
        message = f"""
AMS Chart of Accounts Installation Complete:

Created Accounts: {len(created_accounts)}
- {', '.join(created_accounts.mapped('name'))}

Created Journals: {len(created_journals)}
- {', '.join(created_journals.mapped('name'))}

Default accounts and journals have been configured automatically.
You can review and modify these settings in Company > AMS Accounting Configuration.
        """
        
        self.message_post(body=message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Installation Complete',
                'message': 'AMS Chart of Accounts has been installed successfully!',
                'type': 'success',
                'sticky': True,
            }
        }
    
    def _update_default_accounts(self, created_accounts, created_journals):
        """Update company default accounts and journals"""
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
        
        # Map created accounts to company fields
        for account in created_accounts:
            if account.code in account_mapping:
                field_name = account_mapping[account.code]
                updates[field_name] = account.id
        
        # Set general defaults
        if not updates.get('ams_default_revenue_account_id'):
            revenue_account = created_accounts.filtered(lambda a: a.code == '4100')
            if revenue_account:
                updates['ams_default_revenue_account_id'] = revenue_account[0].id
        
        if not updates.get('ams_default_deferred_revenue_account_id'):
            deferred_account = created_accounts.filtered(lambda a: a.code == '2400')
            if deferred_account:
                updates['ams_default_deferred_revenue_account_id'] = deferred_account[0].id
        
        # Map created journals to company fields
        journal_mapping = {
            'MEMB': 'default_membership_journal_id',
            'REVR': 'default_revenue_recognition_journal_id',
        }
        
        for journal in created_journals:
            if journal.code in journal_mapping:
                field_name = journal_mapping[journal.code]
                updates[field_name] = journal.id
        
        # Apply updates
        if updates:
            self.write(updates)
    
    def get_default_account(self, account_type):
        """Get default account for a specific type"""
        self.ensure_one()
        
        account_map = {
            'cash': self.ams_default_cash_account_id,
            'receivable': self.ams_default_receivable_account_id,
            'revenue': self.ams_default_revenue_account_id,
            'deferred_revenue': self.ams_default_deferred_revenue_account_id,
            'individual_membership': self.individual_membership_revenue_account_id,
            'enterprise_membership': self.enterprise_membership_revenue_account_id,
            'chapter': self.chapter_revenue_account_id,
            'publication': self.publication_revenue_account_id,
            'membership_deferred': self.membership_deferred_revenue_account_id,
            'chapter_deferred': self.chapter_deferred_revenue_account_id,
            'publication_deferred': self.publication_deferred_revenue_account_id,
            'bad_debt': self.ams_bad_debt_account_id,
            'discount': self.ams_discount_account_id,
        }
        
        account = account_map.get(account_type)
        if not account:
            raise UserError(f'No default {account_type} account configured for company {self.name}')
        
        return account
    
    def get_default_journal(self, journal_type):
        """Get default journal for a specific type"""
        self.ensure_one()
        
        journal_map = {
            'membership': self.default_membership_journal_id,
            'revenue_recognition': self.default_revenue_recognition_journal_id,
        }
        
        journal = journal_map.get(journal_type)
        if not journal:
            # Try to find a journal of the requested type
            journal = self.env['ams.account.journal'].search([
                ('type', '=', journal_type),
                ('company_id', '=', self.id)
            ], limit=1)
        
        if not journal:
            raise UserError(f'No {journal_type} journal configured for company {self.name}')
        
        return journal
    
    def action_validate_ams_accounting_setup(self):
        """Validate AMS accounting setup"""
        self.ensure_one()
        
        issues = []
        warnings = []
        
        # Check required accounts
        required_accounts = {
            'Cash Account': self.ams_default_cash_account_id,
            'Receivable Account': self.ams_default_receivable_account_id,
            'Revenue Account': self.ams_default_revenue_account_id,
            'Deferred Revenue Account': self.ams_default_deferred_revenue_account_id,
        }
        
        for name, account in required_accounts.items():
            if not account:
                issues.append(f'Missing {name}')
            elif not account.active:
                warnings.append(f'{name} is inactive')
        
        # Check required journals
        required_journals = {
            'Membership Journal': self.default_membership_journal_id,
            'Revenue Recognition Journal': self.default_revenue_recognition_journal_id,
        }
        
        for name, journal in required_journals.items():
            if not journal:
                issues.append(f'Missing {name}')
            elif not journal.active:
                warnings.append(f'{name} is inactive')
        
        # Check account types
        if self.ams_default_cash_account_id and self.ams_default_cash_account_id.account_type != 'asset_cash':
            warnings.append('Cash account has incorrect type')
        
        if self.ams_default_receivable_account_id and self.ams_default_receivable_account_id.account_type != 'asset_receivable':
            warnings.append('Receivable account has incorrect type')
        
        if (self.ams_default_deferred_revenue_account_id and 
            self.ams_default_deferred_revenue_account_id.account_type != 'liability_deferred_revenue'):
            warnings.append('Deferred revenue account has incorrect type')
        
        # Generate report
        status = 'error' if issues else ('warning' if warnings else 'success')
        title = 'AMS Accounting Validation'
        
        message_parts = []
        if issues:
            message_parts.append(f"Issues Found ({len(issues)}):")
            for issue in issues:
                message_parts.append(f"• {issue}")
        
        if warnings:
            if message_parts:
                message_parts.append("")
            message_parts.append(f"Warnings ({len(warnings)}):")
            for warning in warnings:
                message_parts.append(f"• {warning}")
        
        if not issues and not warnings:
            message_parts.append("✓ All AMS accounting settings are properly configured!")
        
        message = "\n".join(message_parts)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': status,
                'sticky': True,
            }
        }
    
    @api.model
    def get_company_fiscal_year_dates(self, date_ref=None):
        """Get fiscal year start and end dates for the company"""
        if not date_ref:
            date_ref = fields.Date.today()
        
        company = self.env.company
        fiscal_start_month = int(company.ams_fiscal_year_start or '01')
        
        # Determine fiscal year
        if date_ref.month >= fiscal_start_month:
            fiscal_year = date_ref.year
        else:
            fiscal_year = date_ref.year - 1
        
        # Calculate fiscal year dates
        from datetime import date
        fiscal_start = date(fiscal_year, fiscal_start_month, 1)
        
        if fiscal_start_month == 1:
            fiscal_end = date(fiscal_year, 12, 31)
        else:
            fiscal_end = date(fiscal_year + 1, fiscal_start_month - 1, 28)  # Simplified
            # Adjust for actual last day of month
            import calendar
            fiscal_end = date(fiscal_year + 1, fiscal_start_month - 1, 
                            calendar.monthrange(fiscal_year + 1, fiscal_start_month - 1)[1])
        
        return fiscal_start, fiscal_end