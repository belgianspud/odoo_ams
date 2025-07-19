# -*- coding: utf-8 -*-
#############################################################################
#
#    AMS Accounting - Financial Report Wizard
#    Enhanced financial reporting with AMS-specific features
#
#############################################################################

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
    account_type_ids = fields.Many2many('account.account.type', string='Account Types')
    
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
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .currency {{ text-align: right; }}
                .total {{ font-weight: bold; background-color: #e6f3ff; }}
            </style>
        </head>
        <body>
            <h1>{report_data['report_title']}</h1>
            <p>Period: {self.date_from} to {self.date_to}</p>
        """
        
        if self.report_type == 'profit_loss':
            html += self._generate_profit_loss_html(report_data)
        elif self.report_type == 'ams_subscription_revenue':
            html += self._generate_subscription_revenue_html(report_data)
        
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
                <tr class="total"><td colspan="2">INCOME</td></tr>
        """
        
        for account in report_data['income_section']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Income</td><td class='currency'>{report_data['total_income']:,.2f}</td></tr>"
        html += "<tr class='total'><td colspan='2'>EXPENSES</td></tr>"
        
        for account in report_data['expense_section']:
            html += f"<tr><td>{account['account_name']}</td><td class='currency'>{account['balance']:,.2f}</td></tr>"
        
        html += f"<tr class='total'><td>Total Expenses</td><td class='currency'>{report_data['total_expense']:,.2f}</td></tr>"
        html += f"<tr class='total'><td>NET INCOME</td><td class='currency'>{report_data['net_income']:,.2f}</td></tr>"
        html += "</tbody></table>"
        
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
        
        # Create attachment
        filename = f"{self.report_type}_{self.date_from}_{self.date_to}.csv"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue().encode()),
            'res_model': self._name,
            'res_id': self.id,