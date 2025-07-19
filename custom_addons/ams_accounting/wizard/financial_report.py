from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None
    _logger.warning("xlsxwriter not available. Excel export will be disabled.")


class FinancialReportWizard(models.TransientModel):
    """
    Enhanced financial report wizard with AMS-specific reporting capabilities
    """
    _name = 'financial.report.wizard'
    _description = 'Financial Report Wizard'
    
    # ========================
    # REPORT CONFIGURATION
    # ========================
    
    # Report Type
    report_type = fields.Selection([
        ('profit_loss', 'Profit & Loss Statement'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow Statement'),
        ('trial_balance', 'Trial Balance'),
        ('general_ledger', 'General Ledger'),
        ('partner_ledger', 'Partner Ledger'),
        ('aged_receivables', 'Aged Receivables'),
        ('aged_payables', 'Aged Payables'),
        ('ams_subscription_revenue', 'AMS Subscription Revenue'),
        ('ams_member_analysis', 'AMS Member Analysis'),
        ('ams_chapter_financial', 'AMS Chapter Financial'),
        ('ams_renewal_pipeline', 'AMS Renewal Pipeline'),
        ('budget_analysis', 'Budget Analysis'),
        ('variance_analysis', 'Variance Analysis')
    ], string='Report Type', required=True, default='profit_loss')
    
    # Date Range
    date_from = fields.Date('From Date', required=True,
        default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To Date', required=True, default=fields.Date.today)
    
    # Comparison Periods
    enable_comparison = fields.Boolean('Enable Comparison', default=False)
    comparison_type = fields.Selection([
        ('previous_period', 'Previous Period'),
        ('previous_year', 'Previous Year'),
        ('custom', 'Custom Period')
    ], string='Comparison Type', default='previous_period')
    
    comparison_date_from = fields.Date('Comparison From Date')
    comparison_date_to = fields.Date('Comparison To Date')
    
    # ========================
    # FILTER OPTIONS
    # ========================
    
    # Company and Currency
    company_ids = fields.Many2many('res.company', string='Companies',
        default=lambda self: [self.env.company.id])
    currency_id = fields.Many2one('res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id)
    
    # Account Filters
    account_ids = fields.Many2many('account.account', string='Accounts')
    
    # Partner Filters
    partner_ids = fields.Many2many('res.partner', string='Partners')
    partner_category_ids = fields.Many2many('res.partner.category', string='Partner Categories')
    
    # AMS-Specific Filters
    subscription_type_ids = fields.Many2many('ams.subscription.type', string='Subscription Types')
    chapter_ids = fields.Many2many('ams.chapter', string='Chapters')
    member_type = fields.Selection([
        ('all', 'All Members'),
        ('individual', 'Individual'),
        ('corporate', 'Corporate'),
        ('student', 'Student'),
        ('honorary', 'Honorary')
    ], string='Member Type Filter', default='all')
    
    # Journal and Analytic Filters
    journal_ids = fields.Many2many('account.journal', string='Journals')
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')
    
    # ========================
    # DISPLAY OPTIONS
    # ========================
    
    # Report Format
    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('html', 'HTML'),
        ('csv', 'CSV')
    ], string='Export Format', default='pdf')
    
    # Detail Level
    detail_level = fields.Selection([
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
        ('full_detail', 'Full Detail')
    ], string='Detail Level', default='summary')
    
    # Display Options
    show_zero_balance = fields.Boolean('Show Zero Balance', default=False)
    show_hierarchy = fields.Boolean('Show Account Hierarchy', default=True)
    show_percentages = fields.Boolean('Show Percentages', default=False)
    show_variance = fields.Boolean('Show Variance', default=False)
    
    # Grouping Options
    group_by_account_type = fields.Boolean('Group by Account Type', default=True)
    group_by_chapter = fields.Boolean('Group by Chapter', default=False)
    group_by_subscription_type = fields.Boolean('Group by Subscription Type', default=False)
    
    # ========================
    # OUTPUT CONFIGURATION
    # ========================
    
    # Report Title and Description
    report_title = fields.Char('Report Title')
    report_description = fields.Text('Report Description')
    
    # Logo and Branding
    include_logo = fields.Boolean('Include Company Logo', default=True)
    include_header = fields.Boolean('Include Report Header', default=True)
    include_footer = fields.Boolean('Include Report Footer', default=True)
    
    # Page Settings
    page_orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape')
    ], string='Page Orientation', default='portrait')
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    # Preview Information
    estimated_records = fields.Integer('Estimated Records', compute='_compute_estimated_records')
    report_size_warning = fields.Boolean('Large Report Warning', compute='_compute_report_size')
    
    @api.depends('report_type', 'date_from', 'date_to', 'account_ids', 'partner_ids')
    def _compute_estimated_records(self):
        for wizard in self:
            try:
                if wizard.report_type in ['general_ledger', 'partner_ledger']:
                    # Estimate move lines
                    domain = wizard._get_move_line_domain()
                    wizard.estimated_records = self.env['account.move.line'].search_count(domain)
                elif wizard.report_type in ['profit_loss', 'balance_sheet']:
                    # Estimate accounts
                    domain = wizard._get_account_domain()
                    wizard.estimated_records = self.env['account.account'].search_count(domain)
                else:
                    wizard.estimated_records = 0
            except Exception:
                wizard.estimated_records = 0
    
    @api.depends('estimated_records')
    def _compute_report_size(self):
        for wizard in self:
            wizard.report_size_warning = wizard.estimated_records > 10000
    
    # ========================
    # ONCHANGE METHODS
    # ========================
    
    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Set defaults based on report type"""
        if self.report_type == 'balance_sheet':
            self.date_from = fields.Date.today().replace(month=1, day=1)
            self.detail_level = 'summary'
            self.group_by_account_type = True
        elif self.report_type in ['ams_subscription_revenue', 'ams_member_analysis']:
            self.group_by_subscription_type = True
        elif self.report_type == 'ams_chapter_financial':
            self.group_by_chapter = True
        elif self.report_type in ['general_ledger', 'partner_ledger']:
            self.detail_level = 'detailed'
            self.page_orientation = 'landscape'
    
    @api.onchange('enable_comparison', 'comparison_type', 'date_from', 'date_to')
    def _onchange_comparison_dates(self):
        """Auto-calculate comparison dates"""
        if self.enable_comparison and self.comparison_type != 'custom':
            if self.comparison_type == 'previous_period':
                period_length = (self.date_to - self.date_from).days
                self.comparison_date_to = self.date_from - timedelta(days=1)
                self.comparison_date_from = self.comparison_date_to - timedelta(days=period_length)
            elif self.comparison_type == 'previous_year':
                self.comparison_date_from = self.date_from - relativedelta(years=1)
                self.comparison_date_to = self.date_to - relativedelta(years=1)
    
    @api.onchange('report_format')
    def _onchange_report_format(self):
        """Adjust options based on format"""
        if self.report_format == 'xlsx':
            self.include_logo = False  # Excel doesn't support logo embedding easily
        elif self.report_format == 'csv':
            self.include_header = False
            self.include_footer = False
            self.include_logo = False
    
    # ========================
    # VALIDATION METHODS
    # ========================
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_('From Date cannot be later than To Date.'))
            
            if wizard.enable_comparison and wizard.comparison_date_from:
                if wizard.comparison_date_from > wizard.comparison_date_to:
                    raise ValidationError(_('Comparison From Date cannot be later than Comparison To Date.'))
    
    # ========================
    # DOMAIN HELPERS
    # ========================
    
    def _get_move_line_domain(self):
        """Get domain for account move lines"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', 'in', self.company_ids.ids)
        ]
        
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        
        # AMS-specific filters
        if self.report_type.startswith('ams_'):
            if self.subscription_type_ids:
                domain.append(('move_id.subscription_type_id', 'in', self.subscription_type_ids.ids))
            
            if self.chapter_ids:
                domain.append(('move_id.ams_chapter_id', 'in', self.chapter_ids.ids))
        
        return domain
    
    def _get_account_domain(self):
        """Get domain for accounts"""
        domain = [
            ('company_id', 'in', self.company_ids.ids),
            ('deprecated', '=', False)
        ]
        
        if self.account_ids:
            domain.append(('id', 'in', self.account_ids.ids))
        
        if not self.show_zero_balance:
            # This would need to be computed based on the actual balances
            pass
        
        return domain
    
    # ========================
    # REPORT GENERATION
    # ========================
    
    def action_generate_report(self):
        """Generate the financial report"""
        try:
            # Validate configuration
            self._validate_report_configuration()
            
            # Generate report data
            report_data = self._generate_report_data()
            
            # Create report based on format
            if self.report_format == 'pdf':
                return self._generate_pdf_report(report_data)
            elif self.report_format == 'xlsx':
                return self._generate_excel_report(report_data)
            elif self.report_format == 'html':
                return self._generate_html_report(report_data)
            elif self.report_format == 'csv':
                return self._generate_csv_report(report_data)
            else:
                raise UserError(_('Unsupported report format: %s') % self.report_format)
                
        except Exception as e:
            _logger.error(f"Financial report generation failed: {str(e)}")
            raise UserError(_('Report generation failed: %s') % str(e))
    
    def _validate_report_configuration(self):
        """Validate report configuration"""
        if not self.company_ids:
            raise UserError(_('At least one company must be selected.'))
        
        if self.report_format == 'xlsx' and not xlsxwriter:
            raise UserError(_('Excel export requires xlsxwriter library. Please install it.'))
        
        if self.estimated_records > 50000:
            raise UserError(_('Report too large (%d records). Please narrow your selection.') % self.estimated_records)
    
    def _generate_report_data(self):
        """Generate the core report data"""
        if self.report_type == 'profit_loss':
            return self._generate_profit_loss_data()
        elif self.report_type == 'balance_sheet':
            return self._generate_balance_sheet_data()
        elif self.report_type == 'cash_flow':
            return self._generate_cash_flow_data()
        elif self.report_type == 'trial_balance':
            return self._generate_trial_balance_data()
        elif self.report_type == 'general_ledger':
            return self._generate_general_ledger_data()
        elif self.report_type == 'partner_ledger':
            return self._generate_partner_ledger_data()
        elif self.report_type == 'aged_receivables':
            return self._generate_aged_receivables_data()
        elif self.report_type == 'ams_subscription_revenue':
            return self._generate_ams_subscription_revenue_data()
        elif self.report_type == 'ams_member_analysis':
            return self._generate_ams_member_analysis_data()
        elif self.report_type == 'ams_chapter_financial':
            return self._generate_ams_chapter_financial_data()
        elif self.report_type == 'ams_renewal_pipeline':
            return self._generate_ams_renewal_pipeline_data()
        else:
            raise UserError(_('Report type not implemented: %s') % self.report_type)
    
    def _generate_profit_loss_data(self):
        """Generate Profit & Loss statement data"""
        # Get income accounts
        income_accounts = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        # Get expense accounts
        expense_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        # Calculate balances
        report_data = {
            'report_title': self.report_title or 'Profit & Loss Statement',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'income_section': self._calculate_account_balances(income_accounts),
            'expense_section': self._calculate_account_balances(expense_accounts),
        }
        
        # Calculate totals
        total_income = sum(acc['balance'] for acc in report_data['income_section'])
        total_expense = sum(acc['balance'] for acc in report_data['expense_section'])
        
        report_data.update({
            'total_income': total_income,
            'total_expense': total_expense,
            'net_income': total_income - total_expense,
        })
        
        return report_data
    
    def _generate_balance_sheet_data(self):
        """Generate Balance Sheet data"""
        # Assets
        asset_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        # Liabilities
        liability_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        # Equity
        equity_accounts = self.env['account.account'].search([
            ('account_type', '=', 'equity'),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        report_data = {
            'report_title': self.report_title or 'Balance Sheet',
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'assets': self._calculate_account_balances(asset_accounts),
            'liabilities': self._calculate_account_balances(liability_accounts),
            'equity': self._calculate_account_balances(equity_accounts),
        }
        
        # Calculate totals
        total_assets = sum(acc['balance'] for acc in report_data['assets'])
        total_liabilities = sum(acc['balance'] for acc in report_data['liabilities'])
        total_equity = sum(acc['balance'] for acc in report_data['equity'])
        
        report_data.update({
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liab_equity': total_liabilities + total_equity,
        })
        
        return report_data
    
    def _generate_cash_flow_data(self):
        """Generate Cash Flow statement data"""
        # Get cash and bank accounts
        cash_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['asset_cash']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        # Operating activities (simplified)
        operating_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', 'in', ['income', 'expense', 'expense_depreciation', 'expense_direct_cost']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        operating_cash_flow = sum(operating_lines.mapped('credit')) - sum(operating_lines.mapped('debit'))
        
        # Investment activities (asset purchases/sales)
        investing_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', 'in', ['asset_non_current', 'asset_fixed']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        investing_cash_flow = sum(investing_lines.mapped('credit')) - sum(investing_lines.mapped('debit'))
        
        # Financing activities (loans, equity)
        financing_lines = self.env['account.move.line'].search([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', 'in', ['liability_non_current', 'equity']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        financing_cash_flow = sum(financing_lines.mapped('credit')) - sum(financing_lines.mapped('debit'))
        
        return {
            'report_title': self.report_title or 'Cash Flow Statement',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'operating_cash_flow': operating_cash_flow,
            'investing_cash_flow': investing_cash_flow,
            'financing_cash_flow': financing_cash_flow,
            'net_cash_flow': operating_cash_flow + investing_cash_flow + financing_cash_flow,
        }
    
    def _generate_trial_balance_data(self):
        """Generate Trial Balance data"""
        accounts = self.env['account.account'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('deprecated', '=', False)
        ])
        
        trial_balance_data = self._calculate_account_balances(accounts)
        
        # Calculate totals
        total_debit = sum(acc['debit'] for acc in trial_balance_data)
        total_credit = sum(acc['credit'] for acc in trial_balance_data)
        
        return {
            'report_title': self.report_title or 'Trial Balance',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'accounts': trial_balance_data,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'is_balanced': abs(total_debit - total_credit) < 0.01,
        }
    
    def _generate_general_ledger_data(self):
        """Generate General Ledger data"""
        domain = self._get_move_line_domain()
        move_lines = self.env['account.move.line'].search(domain, order='account_id, date')
        
        # Group by account
        ledger_data = {}
        for line in move_lines:
            account_id = line.account_id.id
            if account_id not in ledger_data:
                ledger_data[account_id] = {
                    'account': line.account_id,
                    'lines': [],
                    'opening_balance': 0.0,
                    'closing_balance': 0.0,
                }
            
            ledger_data[account_id]['lines'].append({
                'date': line.date,
                'move_name': line.move_id.name,
                'partner_name': line.partner_id.name if line.partner_id else '',
                'name': line.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.debit - line.credit,
            })
        
        # Calculate running balances
        for account_data in ledger_data.values():
            running_balance = 0.0
            for line in account_data['lines']:
                running_balance += line['balance']
                line['running_balance'] = running_balance
            account_data['closing_balance'] = running_balance
        
        return {
            'report_title': self.report_title or 'General Ledger',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'ledger_data': ledger_data,
        }
    
    def _generate_partner_ledger_data(self):
        """Generate Partner Ledger data"""
        domain = self._get_move_line_domain()
        domain.append(('partner_id', '!=', False))
        
        move_lines = self.env['account.move.line'].search(domain, order='partner_id, date')
        
        # Group by partner
        partner_data = {}
        for line in move_lines:
            partner_id = line.partner_id.id
            if partner_id not in partner_data:
                partner_data[partner_id] = {
                    'partner': line.partner_id,
                    'lines': [],
                    'total_debit': 0.0,
                    'total_credit': 0.0,
                    'balance': 0.0,
                }
            
            partner_data[partner_id]['lines'].append({
                'date': line.date,
                'account_name': line.account_id.name,
                'move_name': line.move_id.name,
                'name': line.name,
                'debit': line.debit,
                'credit': line.credit,
            })
            
            partner_data[partner_id]['total_debit'] += line.debit
            partner_data[partner_id]['total_credit'] += line.credit
            partner_data[partner_id]['balance'] += line.debit - line.credit
        
        return {
            'report_title': self.report_title or 'Partner Ledger',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'partner_data': partner_data,
        }
    
    def _generate_aged_receivables_data(self):
        """Generate Aged Receivables data"""
        today = fields.Date.today()
        
        # Get outstanding receivables
        receivable_moves = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        aged_data = {}
        for move in receivable_moves:
            partner_id = move.partner_id.id
            if partner_id not in aged_data:
                aged_data[partner_id] = {
                    'partner': move.partner_id,
                    'current': 0.0,
                    'days_30': 0.0,
                    'days_60': 0.0,
                    'days_90': 0.0,
                    'days_120': 0.0,
                    'total': 0.0,
                }
            
            amount = move.amount_residual
            days_overdue = (today - move.invoice_date_due).days if move.invoice_date_due else 0
            
            if days_overdue <= 0:
                aged_data[partner_id]['current'] += amount
            elif days_overdue <= 30:
                aged_data[partner_id]['days_30'] += amount
            elif days_overdue <= 60:
                aged_data[partner_id]['days_60'] += amount
            elif days_overdue <= 90:
                aged_data[partner_id]['days_90'] += amount
            else:
                aged_data[partner_id]['days_120'] += amount
            
            aged_data[partner_id]['total'] += amount
        
        return {
            'report_title': self.report_title or 'Aged Receivables',
            'as_of_date': today,
            'currency': self.currency_id.name,
            'aged_data': aged_data,
        }
    
    def _generate_ams_subscription_revenue_data(self):
        """Generate AMS subscription revenue analysis"""
        domain = self._get_move_line_domain()
        domain.append(('move_id.is_ams_subscription_invoice', '=', True))
        
        move_lines = self.env['account.move.line'].search(domain)
        
        # Group by subscription type
        revenue_by_type = {}
        for line in move_lines:
            subscription_type = line.move_id.subscription_type_id.name if line.move_id.subscription_type_id else 'Other'
            if subscription_type not in revenue_by_type:
                revenue_by_type[subscription_type] = {
                    'revenue': 0.0,
                    'count': 0,
                    'members': set()
                }
            
            revenue_by_type[subscription_type]['revenue'] += line.credit - line.debit
            revenue_by_type[subscription_type]['count'] += 1
            if line.partner_id:
                revenue_by_type[subscription_type]['members'].add(line.partner_id.id)
        
        # Convert sets to counts
        for type_data in revenue_by_type.values():
            type_data['member_count'] = len(type_data['members'])
            del type_data['members']
        
        return {
            'report_title': self.report_title or 'AMS Subscription Revenue Analysis',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'revenue_by_type': revenue_by_type,
            'total_revenue': sum(data['revenue'] for data in revenue_by_type.values()),
            'total_transactions': sum(data['count'] for data in revenue_by_type.values()),
            'total_members': len(set(line.partner_id.id for line in move_lines if line.partner_id)),
        }
    
    def _generate_ams_member_analysis_data(self):
        """Generate AMS member financial analysis"""
        members = self.env['res.partner'].search([
            ('is_ams_member', '=', True),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        member_data = {}
        for member in members:
            # Get member's invoices in period
            invoices = member.invoice_ids.filtered(
                lambda inv: inv.invoice_date >= self.date_from and 
                           inv.invoice_date <= self.date_to and
                           inv.state == 'posted' and
                           inv.is_ams_subscription_invoice
            )
            
            total_invoiced = sum(invoices.mapped('amount_total'))
            total_paid = sum(invoices.filtered(lambda inv: inv.payment_state == 'paid').mapped('amount_total'))
            
            if total_invoiced > 0 or self.show_zero_balance:
                member_data[member.id] = {
                    'member': member,
                    'member_type': member.member_type,
                    'total_invoiced': total_invoiced,
                    'total_paid': total_paid,
                    'outstanding': total_invoiced - total_paid,
                    'payment_rate': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0,
                    'invoice_count': len(invoices),
                }
        
        return {
            'report_title': self.report_title or 'AMS Member Financial Analysis',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'member_data': member_data,
            'summary': {
                'total_members': len(member_data),
                'total_invoiced': sum(data['total_invoiced'] for data in member_data.values()),
                'total_paid': sum(data['total_paid'] for data in member_data.values()),
                'total_outstanding': sum(data['outstanding'] for data in member_data.values()),
                'average_payment_rate': sum(data['payment_rate'] for data in member_data.values()) / len(member_data) if member_data else 0,
            }
        }
    
    def _generate_ams_chapter_financial_data(self):
        """Generate AMS chapter financial analysis"""
        chapters = self.env['ams.chapter'].search([
            ('active', '=', True)
        ])
        
        chapter_data = {}
        for chapter in chapters:
            # Get chapter-related revenue
            chapter_lines = self.env['account.move.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('move_id.state', '=', 'posted'),
                ('move_id.ams_chapter_id', '=', chapter.id),
                ('company_id', 'in', self.company_ids.ids)
            ])
            
            revenue = sum(chapter_lines.mapped('credit')) - sum(chapter_lines.mapped('debit'))
            
            # Get chapter expenses if analytic account configured
            expenses = 0.0
            if chapter.analytic_account_id:
                expense_lines = self.env['account.move.line'].search([
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('move_id.state', '=', 'posted'),
                    ('analytic_account_id', '=', chapter.analytic_account_id.id),
                    ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
                    ('company_id', 'in', self.company_ids.ids)
                ])
                expenses = sum(expense_lines.mapped('debit')) - sum(expense_lines.mapped('credit'))
            
            if revenue > 0 or expenses > 0 or self.show_zero_balance:
                chapter_data[chapter.id] = {
                    'chapter': chapter,
                    'revenue': revenue,
                    'expenses': expenses,
                    'net_income': revenue - expenses,
                    'member_count': chapter.active_member_count,
                    'revenue_per_member': revenue / chapter.active_member_count if chapter.active_member_count > 0 else 0,
                }
        
        return {
            'report_title': self.report_title or 'AMS Chapter Financial Analysis',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'currency': self.currency_id.name,
            'chapter_data': chapter_data,
            'summary': {
                'total_chapters': len(chapter_data),
                'total_revenue': sum(data['revenue'] for data in chapter_data.values()),
                'total_expenses': sum(data['expenses'] for data in chapter_data.values()),
                'total_net_income': sum(data['net_income'] for data in chapter_data.values()),
                'total_members': sum(data['member_count'] for data in chapter_data.values()),
            }
        }
    
    def _generate_ams_renewal_pipeline_data(self):
        """Generate AMS renewal pipeline analysis"""
        # Get subscriptions due for renewal in the next 12 months
        future_date = self.date_to + relativedelta(months=12)
        
        subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('is_recurring', '=', True),
            ('next_renewal_date', '>=', self.date_from),
            ('next_renewal_date', '<=', future_date)
        ])
        
        pipeline_data = {}
        monthly_totals = {}
        
        for subscription in subscriptions:
            renewal_month = subscription.next_renewal_date.strftime('%Y-%m')
            
            if renewal_month not in pipeline_data:
                pipeline_data[renewal_month] = {
                    'subscriptions': [],
                    'count': 0,
                    'revenue': 0.0,
                    'auto_renewal_count': 0,
                }
                monthly_totals[renewal_month] = 0.0
            
            pipeline_data[renewal_month]['subscriptions'].append({
                'subscription': subscription,
                'partner': subscription.partner_id,
                'amount': subscription.amount,
                'auto_renewal': subscription.auto_renewal,
                'subscription_type': subscription.subscription_type_id.name if subscription.subscription_type_id else 'Other',
            })
            
            pipeline_data[renewal_month]['count'] += 1
            pipeline_data[renewal_month]['revenue'] += subscription.amount
            monthly_totals[renewal_month] += subscription.amount
            
            if subscription.auto_renewal:
                pipeline_data[renewal_month]['auto_renewal_count'] += 1
        
        return {
            'report_title': self.report_title or 'AMS Renewal Pipeline',
            'date_from': self.date_from,
            'date_to': future_date,
            'currency': self.currency_id.name,
            'pipeline_data': pipeline_data,
            'monthly_totals': monthly_totals,
            'summary': {
                'total_renewals': sum(data['count'] for data in pipeline_data.values()),
                'total_revenue': sum(data['revenue'] for data in pipeline_data.values()),
                'auto_renewal_percentage': (sum(data['auto_renewal_count'] for data in pipeline_data.values()) / 
                                          sum(data['count'] for data in pipeline_data.values()) * 100) if pipeline_data else 0,
            }
        }
    
    def _calculate_account_balances(self, accounts):
        """Calculate balances for given accounts"""
        result = []
        
        for account in accounts:
            domain = [
                ('account_id', '=', account.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('move_id.state', '=', 'posted')
            ]
            
            move_lines = self.env['account.move.line'].search(domain)
            
            debit_sum = sum(move_lines.mapped('debit'))
            credit_sum = sum(move_lines.mapped('credit'))
            balance = debit_sum - credit_sum
            
            # Adjust balance based on account type
            if account.account_type in ['income', 'liability_payable', 'liability_current', 'liability_non_current', 'equity']:
                balance = credit_sum - debit_sum
            
            if balance != 0 or self.show_zero_balance:
                result.append({
                    'account_id': account.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type,
                    'debit': debit_sum,
                    'credit': credit_sum,
                    'balance': balance,
                })
        
        return result
    
    # ========================
    # EXPORT METHODS
    # ========================
    
    def _generate_pdf_report(self, report_data):
        """Generate PDF report"""
        # Use Odoo's report engine
        report_name = f'ams_accounting.report_{self.report_type}'
        
        return self.env.ref(report_name).report_action(
            self, data={'report_data': report_data}
        )
    
    def _generate_excel_report(self, report_data):
        """Generate Excel report"""
        if not xlsxwriter:
            raise UserError(_('Excel export requires xlsxwriter library.'))
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(self.report_type.replace('_', ' ').title())
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        # Write header
        worksheet.write(0, 0, report_data['report_title'], header_format)
        worksheet.write(1, 0, f"Period: {self.date_from} to {self.date_to}")
        
        # Write data based on report type
        if self.report_type == 'profit_loss':
            self._write_profit_loss_excel(worksheet, report_data, header_format, currency_format)
        elif self.report_type == 'balance_sheet':
            self._write_balance_sheet_excel(worksheet, report_data, header_format, currency_format)
        elif self.report_type == 'ams_subscription_revenue':
            self._write_subscription_revenue_excel(worksheet, report_data, header_format, currency_format)
        elif self.report_type == 'ams_member_analysis':
            self._write_member_analysis_excel(worksheet, report_data, header_format, currency_format)
        elif self.report_type == 'ams_chapter_financial':
            self._write_chapter_financial_excel(worksheet, report_data, header_format, currency_format)
        elif self.report_type == 'trial_balance':
            self._write_trial_balance_excel(worksheet, report_data, header_format, currency_format)
        
        workbook.close()
        output.seek(0)
        
        # Create attachment
        filename = f"{self.report_type}_{self.date_from}_{self.date_to}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def _write_profit_loss_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Profit & Loss data to Excel"""
        row = 3
        
        # Income section
        worksheet.write(row, 0, 'INCOME', header_format)
        row += 1
        
        for account in report_data['income_section']:
            worksheet.write(row, 0, account['account_name'])
            worksheet.write(row, 1, account['balance'], currency_format)
            row += 1
        
        worksheet.write(row, 0, 'Total Income', header_format)
        worksheet.write(row, 1, report_data['total_income'], currency_format)
        row += 2
        
        # Expense section
        worksheet.write(row, 0, 'EXPENSES', header_format)
        row += 1
        
        for account in report_data['expense_section']:
            worksheet.write(row, 0, account['account_name'])
            worksheet.write(row, 1, account['balance'], currency_format)
            row += 1
        
        worksheet.write(row, 0, 'Total Expenses', header_format)
        worksheet.write(row, 1, report_data['total_expense'], currency_format)
        row += 2
        
        # Net income
        worksheet.write(row, 0, 'NET INCOME', header_format)
        worksheet.write(row, 1, report_data['net_income'], currency_format)
    
    def _write_balance_sheet_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Balance Sheet data to Excel"""
        row = 3
        
        # Assets section
        worksheet.write(row, 0, 'ASSETS', header_format)
        row += 1
        
        for account in report_data['assets']:
            worksheet.write(row, 0, account['account_name'])
            worksheet.write(row, 1, account['balance'], currency_format)
            row += 1
        
        worksheet.write(row, 0, 'Total Assets', header_format)
        worksheet.write(row, 1, report_data['total_assets'], currency_format)
        row += 2
        
        # Liabilities section
        worksheet.write(row, 0, 'LIABILITIES', header_format)
        row += 1
        
        for account in report_data['liabilities']:
            worksheet.write(row, 0, account['account_name'])
            worksheet.write(row, 1, account['balance'], currency_format)
            row += 1
        
        worksheet.write(row, 0, 'Total Liabilities', header_format)
        worksheet.write(row, 1, report_data['total_liabilities'], currency_format)
        row += 2
        
        # Equity section
        worksheet.write(row, 0, 'EQUITY', header_format)
        row += 1
        
        for account in report_data['equity']:
            worksheet.write(row, 0, account['account_name'])
            worksheet.write(row, 1, account['balance'], currency_format)
            row += 1
        
        worksheet.write(row, 0, 'Total Equity', header_format)
        worksheet.write(row, 1, report_data['total_equity'], currency_format)
    
    def _write_subscription_revenue_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Subscription Revenue data to Excel"""
        row = 3
        
        # Headers
        worksheet.write(row, 0, 'Subscription Type', header_format)
        worksheet.write(row, 1, 'Revenue', header_format)
        worksheet.write(row, 2, 'Count', header_format)
        worksheet.write(row, 3, 'Members', header_format)
        row += 1
        
        # Data
        for type_name, data in report_data['revenue_by_type'].items():
            worksheet.write(row, 0, type_name)
            worksheet.write(row, 1, data['revenue'], currency_format)
            worksheet.write(row, 2, data['count'])
            worksheet.write(row, 3, data['member_count'])
            row += 1
        
        # Totals
        row += 1
        worksheet.write(row, 0, 'TOTALS', header_format)
        worksheet.write(row, 1, report_data['total_revenue'], currency_format)
        worksheet.write(row, 2, report_data['total_transactions'])
        worksheet.write(row, 3, report_data['total_members'])
    
    def _write_member_analysis_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Member Analysis data to Excel"""
        row = 3
        
        # Headers
        worksheet.write(row, 0, 'Member', header_format)
        worksheet.write(row, 1, 'Type', header_format)
        worksheet.write(row, 2, 'Invoiced', header_format)
        worksheet.write(row, 3, 'Paid', header_format)
        worksheet.write(row, 4, 'Outstanding', header_format)
        worksheet.write(row, 5, 'Payment Rate %', header_format)
        row += 1
        
        # Data
        for data in report_data['member_data'].values():
            worksheet.write(row, 0, data['member'].name)
            worksheet.write(row, 1, data['member_type'])
            worksheet.write(row, 2, data['total_invoiced'], currency_format)
            worksheet.write(row, 3, data['total_paid'], currency_format)
            worksheet.write(row, 4, data['outstanding'], currency_format)
            worksheet.write(row, 5, data['payment_rate'])
            row += 1
        
        # Summary
        row += 1
        summary = report_data['summary']
        worksheet.write(row, 0, 'SUMMARY', header_format)
        row += 1
        worksheet.write(row, 0, 'Total Members')
        worksheet.write(row, 1, summary['total_members'])
        row += 1
        worksheet.write(row, 0, 'Total Invoiced')
        worksheet.write(row, 1, summary['total_invoiced'], currency_format)
        row += 1
        worksheet.write(row, 0, 'Total Paid')
        worksheet.write(row, 1, summary['total_paid'], currency_format)
        row += 1
        worksheet.write(row, 0, 'Total Outstanding')
        worksheet.write(row, 1, summary['total_outstanding'], currency_format)
    
    def _write_chapter_financial_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Chapter Financial data to Excel"""
        row = 3
        
        # Headers
        worksheet.write(row, 0, 'Chapter', header_format)
        worksheet.write(row, 1, 'Revenue', header_format)
        worksheet.write(row, 2, 'Expenses', header_format)
        worksheet.write(row, 3, 'Net Income', header_format)
        worksheet.write(row, 4, 'Members', header_format)
        worksheet.write(row, 5, 'Revenue/Member', header_format)
        row += 1
        
        # Data
        for data in report_data['chapter_data'].values():
            worksheet.write(row, 0, data['chapter'].name)
            worksheet.write(row, 1, data['revenue'], currency_format)
            worksheet.write(row, 2, data['expenses'], currency_format)
            worksheet.write(row, 3, data['net_income'], currency_format)
            worksheet.write(row, 4, data['member_count'])
            worksheet.write(row, 5, data['revenue_per_member'], currency_format)
            row += 1
    
    def _write_trial_balance_excel(self, worksheet, report_data, header_format, currency_format):
        """Write Trial Balance data to Excel"""
        row = 3
        
        # Headers
        worksheet.write(row, 0, 'Account Code', header_format)
        worksheet.write(row, 1, 'Account Name', header_format)
        worksheet.write(row, 2, 'Debit', header_format)
        worksheet.write(row, 3, 'Credit', header_format)
        worksheet.write(row, 4, 'Balance', header_format)
        row += 1
        
        # Data
        for account in report_data['accounts']:
            worksheet.write(row, 0, account['account_code'])
            worksheet.write(row, 1, account['account_name'])
            worksheet.write(row, 2, account['debit'], currency_format)
            worksheet.write(row, 3, account['credit'], currency_format)
            worksheet.write(row, 4, account['balance'], currency_format)
            row += 1
        
        # Totals
        row += 1
        worksheet.write(row, 0, '', header_format)
        worksheet.write(row, 1, 'TOTALS', header_format)
        worksheet.write(row, 2, report_data['total_debit'], currency_format)
        worksheet.write(row, 3, report_data['total_credit'], currency_format)
        worksheet.write(row, 4, '', header_format)
    
    def _generate_html_report(self, report_data):
        """Generate HTML report for web display"""
        return {
            'type': 'ir.actions.act_window',
            'name': report_data['report_title'],
            'res_model': 'financial.report.html.viewer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_report_data': report_data,
                'default_report_html': self._generate_html_content(report_data)
            }
        }
    
    def _generate_html_content(self, report_data):
        """Generate HTML content for the report"""
        # Generate basic HTML structure
        html = f"""
        <html>
        <head>
            <title>{report_data['report_title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .currency {{ text-align: right; }}
                .total {{ font-weight: bold; background-color: #e6f3ff; }}
                .section-header {{ font-weight: bold; background-color: #d4edda; }}
                .summary {{ background-color: #f8f9fa; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; }}
                .report-info {{ margin-bottom: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <h1>{report_data['report_title']}</h1>
            <div class="report-info">
                <p>Period: {self.date_from} to {self.date_to}</p>
                <p>Currency: {report_data.get('currency', self.currency_id.name)}</p>
            </div>
        """
        
        if self.report_type == 'profit_loss':
            html += self._generate_profit_loss_html(report_data)
        elif self.report_type == 'balance_sheet':
            html += self._generate_balance_sheet_html(report_data)
        elif self.report_type == 'ams_subscription_revenue':
            html += self._generate_subscription_revenue_html(report_data)
        elif self.report_type == 'ams_member_analysis':
            html += self._generate_member_analysis_html(report_data)
        elif self.report_type == 'trial_balance':
            html += self._generate_trial_balance_html(report_data)
        
        html += "</body></html>"
        return html
    
    def _generate_profit_loss_html(self, report_data):
        """Generate HTML for Profit & Loss report"""
        html = """
        <table>
            <thead>
                <tr><th>Account</th><th>Amount</th></tr>
            </thead>
            <tbody>
                <tr class="section-header"><td colspan="2">INCOME</td></tr>
        """
        
        for account in report_data['income_section']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Income</td><td class='currency'>{report_data['total_income']:,.2f}</td></tr>"
        html += "<tr class='section-header'><td colspan='2'>EXPENSES</td></tr>"
        
        for account in report_data['expense_section']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Expenses</td><td class='currency'>{report_data['total_expense']:,.2f}</td></tr>"
        html += f"<tr class='total'><td>NET INCOME</td><td class='currency'>{report_data['net_income']:,.2f}</td></tr>"
        html += "</tbody></table>"
        
        return html
    
    def _generate_balance_sheet_html(self, report_data):
        """Generate HTML for Balance Sheet report"""
        html = """
        <table>
            <thead>
                <tr><th>Account</th><th>Amount</th></tr>
            </thead>
            <tbody>
                <tr class="section-header"><td colspan="2">ASSETS</td></tr>
        """
        
        for account in report_data['assets']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Assets</td><td class='currency'>{report_data['total_assets']:,.2f}</td></tr>"
        html += "<tr class='section-header'><td colspan='2'>LIABILITIES</td></tr>"
        
        for account in report_data['liabilities']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Liabilities</td><td class='currency'>{report_data['total_liabilities']:,.2f}</td></tr>"
        html += "<tr class='section-header'><td colspan='2'>EQUITY</td></tr>"
        
        for account in report_data['equity']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Equity</td><td class='currency'>{report_data['total_equity']:,.2f}</td></tr>"
        html += "</tbody></table>"
        
        return html
    
    def _generate_subscription_revenue_html(self, report_data):
        """Generate HTML for Subscription Revenue report"""
        html = """
        <table>
            <thead>
                <tr><th>Subscription Type</th><th>Revenue</th><th>Transactions</th><th>Members</th></tr>
            </thead>
            <tbody>
        """
        
        for type_name, data in report_data['revenue_by_type'].items():
            html += f"""
            <tr>
                <td>{type_name}</td>
                <td class='currency'>{data['revenue']:,.2f}</td>
                <td>{data['count']}</td>
                <td>{data['member_count']}</td>
            </tr>
            """
        
        html += f"""
            </tbody>
            <tfoot>
                <tr class='total'>
                    <td>TOTALS</td>
                    <td class='currency'>{report_data['total_revenue']:,.2f}</td>
                    <td>{report_data['total_transactions']}</td>
                    <td>{report_data['total_members']}</td>
                </tr>
            </tfoot>
        </table>
        """
        
        return html
    
    def _generate_member_analysis_html(self, report_data):
        """Generate HTML for Member Analysis report"""
        html = """
        <table>
            <thead>
                <tr><th>Member</th><th>Type</th><th>Invoiced</th><th>Paid</th><th>Outstanding</th><th>Payment Rate %</th></tr>
            </thead>
            <tbody>
        """
        
        for data in report_data['member_data'].values():
            html += f"""
            <tr>
                <td>{data['member'].name}</td>
                <td>{data['member_type']}</td>
                <td class='currency'>{data['total_invoiced']:,.2f}</td>
                <td class='currency'>{data['total_paid']:,.2f}</td>
                <td class='currency'>{data['outstanding']:,.2f}</td>
                <td class='currency'>{data['payment_rate']:.1f}%</td>
            </tr>
            """
        
        summary = report_data['summary']
        html += f"""
            </tbody>
            <tfoot>
                <tr class='total'>
                    <td>TOTALS ({summary['total_members']} members)</td>
                    <td></td>
                    <td class='currency'>{summary['total_invoiced']:,.2f}</td>
                    <td class='currency'>{summary['total_paid']:,.2f}</td>
                    <td class='currency'>{summary['total_outstanding']:,.2f}</td>
                    <td class='currency'>{summary['average_payment_rate']:.1f}%</td>
                </tr>
            </tfoot>
        </table>
        """
        
        return html
    
    def _generate_trial_balance_html(self, report_data):
        """Generate HTML for Trial Balance report"""
        html = """
        <table>
            <thead>
                <tr><th>Code</th><th>Account</th><th>Debit</th><th>Credit</th><th>Balance</th></tr>
            </thead>
            <tbody>
        """
        
        for account in report_data['accounts']:
            html += f"""
            <tr>
                <td>{account['account_code']}</td>
                <td>{account['account_name']}</td>
                <td class='currency'>{account['debit']:,.2f}</td>
                <td class='currency'>{account['credit']:,.2f}</td>
                <td class='currency'>{account['balance']:,.2f}</td>
            </tr>
            """
        
        html += f"""
            </tbody>
            <tfoot>
                <tr class='total'>
                    <td></td>
                    <td>TOTALS</td>
                    <td class='currency'>{report_data['total_debit']:,.2f}</td>
                    <td class='currency'>{report_data['total_credit']:,.2f}</td>
                    <td></td>
                </tr>
                <tr class='summary'>
                    <td colspan='5'>Balanced: {'Yes' if report_data['is_balanced'] else 'No'}</td>
                </tr>
            </tfoot>
        </table>
        """
        
        return html
    
    def _generate_csv_report(self, report_data):
        """Generate CSV report"""
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([report_data['report_title']])
        writer.writerow([f"Period: {self.date_from} to {self.date_to}"])
        writer.writerow([])  # Empty row
        
        if self.report_type == 'profit_loss':
            writer.writerow(['Account', 'Amount'])
            writer.writerow(['INCOME', ''])
            
            for account in report_data['income_section']:
                writer.writerow([account['account_name'], account['balance']])
            
            writer.writerow(['Total Income', report_data['total_income']])
            writer.writerow([])
            writer.writerow(['EXPENSES', ''])
            
            for account in report_data['expense_section']:
                writer.writerow([account['account_name'], account['balance']])
            
            writer.writerow(['Total Expenses', report_data['total_expense']])
            writer.writerow(['NET INCOME', report_data['net_income']])
            
        elif self.report_type == 'balance_sheet':
            writer.writerow(['Account', 'Amount'])
            writer.writerow(['ASSETS', ''])
            
            for account in report_data['assets']:
                writer.writerow([account['account_name'], account['balance']])
            
            writer.writerow(['Total Assets', report_data['total_assets']])
            writer.writerow([])
            writer.writerow(['LIABILITIES', ''])
            
            for account in report_data['liabilities']:
                writer.writerow([account['account_name'], account['balance']])
            
            writer.writerow(['Total Liabilities', report_data['total_liabilities']])
            writer.writerow([])
            writer.writerow(['EQUITY', ''])
            
            for account in report_data['equity']:
                writer.writerow([account['account_name'], account['balance']])
            
            writer.writerow(['Total Equity', report_data['total_equity']])
            
        elif self.report_type == 'ams_subscription_revenue':
            writer.writerow(['Subscription Type', 'Revenue', 'Transactions', 'Members'])
            
            for type_name, data in report_data['revenue_by_type'].items():
                writer.writerow([type_name, data['revenue'], data['count'], data['member_count']])
            
            writer.writerow([])
            writer.writerow(['TOTALS', report_data['total_revenue'], report_data['total_transactions'], report_data['total_members']])
            
        elif self.report_type == 'ams_member_analysis':
            writer.writerow(['Member', 'Type', 'Invoiced', 'Paid', 'Outstanding', 'Payment Rate %'])
            
            for data in report_data['member_data'].values():
                writer.writerow([
                    data['member'].name,
                    data['member_type'],
                    data['total_invoiced'],
                    data['total_paid'],
                    data['outstanding'],
                    data['payment_rate']
                ])
            
            summary = report_data['summary']
            writer.writerow([])
            writer.writerow(['SUMMARY'])
            writer.writerow(['Total Members', summary['total_members']])
            writer.writerow(['Total Invoiced', summary['total_invoiced']])
            writer.writerow(['Total Paid', summary['total_paid']])
            writer.writerow(['Total Outstanding', summary['total_outstanding']])
            
        elif self.report_type == 'trial_balance':
            writer.writerow(['Account Code', 'Account Name', 'Debit', 'Credit', 'Balance'])
            
            for account in report_data['accounts']:
                writer.writerow([
                    account['account_code'],
                    account['account_name'],
                    account['debit'],
                    account['credit'],
                    account['balance']
                ])
            
            writer.writerow([])
            writer.writerow(['', 'TOTALS', report_data['total_debit'], report_data['total_credit'], ''])
        
        # Create attachment
        filename = f"{self.report_type}_{self.date_from}_{self.date_to}.csv"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/csv'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    # ========================
    # UTILITY METHODS
    # ========================
    
    def action_preview_report(self):
        """Preview report configuration without generating full report"""
        try:
            # Validate configuration
            self._validate_report_configuration()
            
            # Generate preview data (limited)
            preview_data = self._generate_preview_data()
            
            return {
                'type': 'ir.actions.act_window',
                'name': f'Preview: {self.report_title or self.report_type.replace("_", " ").title()}',
                'res_model': 'financial.report.preview',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_wizard_id': self.id,
                    'default_preview_data': preview_data,
                }
            }
        except Exception as e:
            raise UserError(_('Preview generation failed: %s') % str(e))
    
    def _generate_preview_data(self):
        """Generate limited preview data"""
        if self.report_type == 'profit_loss':
            return self._generate_profit_loss_preview()
        elif self.report_type == 'balance_sheet':
            return self._generate_balance_sheet_preview()
        elif self.report_type == 'ams_subscription_revenue':
            return self._generate_subscription_revenue_preview()
        else:
            return {
                'report_type': self.report_type,
                'estimated_records': self.estimated_records,
                'date_range': f"{self.date_from} to {self.date_to}",
                'filters_applied': self._get_applied_filters(),
            }
    
    def _generate_profit_loss_preview(self):
        """Generate P&L preview"""
        income_count = self.env['account.account'].search_count([
            ('account_type', '=', 'income'),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        expense_count = self.env['account.account'].search_count([
            ('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        return {
            'report_type': 'Profit & Loss Statement',
            'income_accounts': income_count,
            'expense_accounts': expense_count,
            'total_accounts': income_count + expense_count,
            'estimated_records': self.estimated_records,
        }
    
    def _generate_balance_sheet_preview(self):
        """Generate Balance Sheet preview"""
        asset_count = self.env['account.account'].search_count([
            ('account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        liability_count = self.env['account.account'].search_count([
            ('account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        equity_count = self.env['account.account'].search_count([
            ('account_type', '=', 'equity'),
            ('company_id', 'in', self.company_ids.ids)
        ])
        
        return {
            'report_type': 'Balance Sheet',
            'asset_accounts': asset_count,
            'liability_accounts': liability_count,
            'equity_accounts': equity_count,
            'total_accounts': asset_count + liability_count + equity_count,
        }
    
    def _generate_subscription_revenue_preview(self):
        """Generate Subscription Revenue preview"""
        subscription_invoices = self.env['account.move'].search_count([
            ('is_ams_subscription_invoice', '=', True),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ])
        
        subscription_types = self.env['ams.subscription.type'].search_count([])
        
        return {
            'report_type': 'AMS Subscription Revenue',
            'subscription_invoices': subscription_invoices,
            'subscription_types': subscription_types,
            'date_range': f"{self.date_from} to {self.date_to}",
        }
    
    def _get_applied_filters(self):
        """Get list of applied filters"""
        filters = []
        
        if self.account_ids:
            filters.append(f"Specific Accounts ({len(self.account_ids)})")
        
        if self.partner_ids:
            filters.append(f"Specific Partners ({len(self.partner_ids)})")
        
        if self.journal_ids:
            filters.append(f"Specific Journals ({len(self.journal_ids)})")
        
        if self.subscription_type_ids:
            filters.append(f"Subscription Types ({len(self.subscription_type_ids)})")
        
        if self.chapter_ids:
            filters.append(f"Chapters ({len(self.chapter_ids)})")
        
        if self.member_type != 'all':
            filters.append(f"Member Type: {self.member_type}")
        
        if self.enable_comparison:
            filters.append(f"Comparison: {self.comparison_type}")
        
        return filters if filters else ['No filters applied']
    
    def action_reset_filters(self):
        """Reset all filters to default"""
        self.write({
            'account_ids': [(5, 0, 0)],
            'partner_ids': [(5, 0, 0)],
            'journal_ids': [(5, 0, 0)],
            'subscription_type_ids': [(5, 0, 0)],
            'chapter_ids': [(5, 0, 0)],
            'analytic_account_ids': [(5, 0, 0)],
            'member_type': 'all',
            'enable_comparison': False,
            'show_zero_balance': False,
            'group_by_account_type': True,
            'group_by_chapter': False,
            'group_by_subscription_type': False,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Filters Reset'),
                'message': _('All filters have been reset to default values.'),
                'type': 'success',
            }
        }
    
    def action_save_as_template(self):
        """Save current configuration as template"""
        template_name = self.report_title or f"{self.report_type.replace('_', ' ').title()} Template"
        
        template_vals = {
            'name': template_name,
            'report_type': self.report_type,
            'report_format': self.report_format,
            'detail_level': self.detail_level,
            'show_zero_balance': self.show_zero_balance,
            'show_hierarchy': self.show_hierarchy,
            'show_percentages': self.show_percentages,
            'group_by_account_type': self.group_by_account_type,
            'group_by_chapter': self.group_by_chapter,
            'group_by_subscription_type': self.group_by_subscription_type,
            'include_logo': self.include_logo,
            'include_header': self.include_header,
            'include_footer': self.include_footer,
            'page_orientation': self.page_orientation,
            'enable_comparison': self.enable_comparison,
            'comparison_type': self.comparison_type,
        }
        
        template = self.env['financial.report.template'].create(template_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Report Template Created',
            'res_model': 'financial.report.template',
            'view_mode': 'form',
            'res_id': template.id,
            'target': 'new',
        }


class FinancialReportTemplate(models.Model):
    """
    Templates for frequently used financial report configurations
    """
    _name = 'financial.report.template'
    _description = 'Financial Report Template'
    _order = 'name'
    
    name = fields.Char('Template Name', required=True)
    description = fields.Text('Description')
    
    # Report Configuration
    report_type = fields.Selection([
        ('profit_loss', 'Profit & Loss Statement'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow Statement'),
        ('trial_balance', 'Trial Balance'),
        ('general_ledger', 'General Ledger'),
        ('partner_ledger', 'Partner Ledger'),
        ('aged_receivables', 'Aged Receivables'),
        ('aged_payables', 'Aged Payables'),
        ('ams_subscription_revenue', 'AMS Subscription Revenue'),
        ('ams_member_analysis', 'AMS Member Analysis'),
        ('ams_chapter_financial', 'AMS Chapter Financial'),
        ('ams_renewal_pipeline', 'AMS Renewal Pipeline'),
    ], string='Report Type', required=True)
    
    # Saved Configuration
    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('html', 'HTML'),
        ('csv', 'CSV')
    ], string='Export Format', default='pdf')
    
    detail_level = fields.Selection([
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
        ('full_detail', 'Full Detail')
    ], string='Detail Level', default='summary')
    
    show_zero_balance = fields.Boolean('Show Zero Balance', default=False)
    show_hierarchy = fields.Boolean('Show Account Hierarchy', default=True)
    show_percentages = fields.Boolean('Show Percentages', default=False)
    
    group_by_account_type = fields.Boolean('Group by Account Type', default=True)
    group_by_chapter = fields.Boolean('Group by Chapter', default=False)
    group_by_subscription_type = fields.Boolean('Group by Subscription Type', default=False)
    
    include_logo = fields.Boolean('Include Company Logo', default=True)
    include_header = fields.Boolean('Include Report Header', default=True)
    include_footer = fields.Boolean('Include Report Footer', default=True)
    page_orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape')
    ], string='Page Orientation', default='portrait')
    
    enable_comparison = fields.Boolean('Enable Comparison', default=False)
    comparison_type = fields.Selection([
        ('previous_period', 'Previous Period'),
        ('previous_year', 'Previous Year'),
        ('custom', 'Custom Period')
    ], string='Comparison Type', default='previous_period')
    
    # Usage Statistics
    usage_count = fields.Integer('Times Used', default=0)
    last_used = fields.Datetime('Last Used')
    created_by = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user)
    
    def action_use_template(self):
        """Create new report wizard with this template's configuration"""
        wizard_vals = {
            'report_type': self.report_type,
            'report_format': self.report_format,
            'detail_level': self.detail_level,
            'show_zero_balance': self.show_zero_balance,
            'show_hierarchy': self.show_hierarchy,
            'show_percentages': self.show_percentages,
            'group_by_account_type': self.group_by_account_type,
            'group_by_chapter': self.group_by_chapter,
            'group_by_subscription_type': self.group_by_subscription_type,
            'include_logo': self.include_logo,
            'include_header': self.include_header,
            'include_footer': self.include_footer,
            'page_orientation': self.page_orientation,
            'enable_comparison': self.enable_comparison,
            'comparison_type': self.comparison_type,
            'report_title': f"Report from {self.name}",
        }
        
        wizard = self.env['financial.report.wizard'].create(wizard_vals)
        
        # Update usage statistics
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Report - {self.name}',
            'res_model': 'financial.report.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }


class FinancialReportHtmlViewer(models.TransientModel):
    """
    HTML viewer for financial reports
    """
    _name = 'financial.report.html.viewer'
    _description = 'Financial Report HTML Viewer'
    
    report_data = fields.Text('Report Data')
    report_html = fields.Html('Report HTML')
    
    def action_export_pdf(self):
        """Export the HTML report as PDF"""
        # This would convert the HTML to PDF using wkhtmltopdf or similar
        pass
    
    def action_export_excel(self):
        """Export the report data as Excel"""
        # This would regenerate the original wizard and export as Excel
        pass


class FinancialReportPreview(models.TransientModel):
    """
    Preview model for financial reports
    """
    _name = 'financial.report.preview'
    _description = 'Financial Report Preview'
    
    wizard_id = fields.Many2one('financial.report.wizard', 'Report Wizard')
    preview_data = fields.Text('Preview Data')
    
    def action_generate_full_report(self):
        """Generate the full report"""
        if self.wizard_id:
            return self.wizard_id.action_generate_report()