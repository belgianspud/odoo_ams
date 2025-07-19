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


class GeneralLedgerWizard(models.TransientModel):
    """
    Enhanced general ledger report wizard with AMS integration
    """
    _name = 'general.ledger.wizard'
    _description = 'General Ledger Report Wizard'
    
    # ========================
    # BASIC CONFIGURATION
    # ========================
    
    # Date Range
    date_from = fields.Date('From Date', required=True,
        default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To Date', required=True, default=fields.Date.today)
    
    # Company and Currency
    company_ids = fields.Many2many('res.company', string='Companies',
        default=lambda self: [self.env.company.id])
    currency_id = fields.Many2one('res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id)
    
    # ========================
    # ACCOUNT FILTERS
    # ========================
    
    # Account Selection
    account_selection = fields.Selection([
        ('all', 'All Accounts'),
        ('specific', 'Specific Accounts'),
        ('by_type', 'By Account Type'),
        ('range', 'Account Code Range')
    ], string='Account Selection', default='all', required=True)
    
    account_ids = fields.Many2many('account.account', string='Specific Accounts')
    
    account_types = fields.Selection([
        ('asset', 'Assets'),
        ('liability', 'Liabilities'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expenses'),
        ('receivable', 'Receivables'),
        ('payable', 'Payables')
    ], string='Account Type Filter')
    
    account_code_from = fields.Char('Account Code From')
    account_code_to = fields.Char('Account Code To')
    
    # ========================
    # ADDITIONAL FILTERS
    # ========================
    
    # Journal Filters
    journal_ids = fields.Many2many('account.journal', string='Journals')
    
    # Partner Filters
    partner_ids = fields.Many2many('res.partner', string='Partners')
    partner_category_ids = fields.Many2many('res.partner.category', string='Partner Categories')
    
    # Analytic Filters
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    
    # ========================
    # AMS-SPECIFIC FILTERS
    # ========================
    
    # AMS Integration Filters
    include_ams_data = fields.Boolean('Include AMS Data', default=True,
        help="Include AMS subscription and member data in the report")
    
    subscription_type_ids = fields.Many2many('ams.subscription.type', string='Subscription Types')
    chapter_ids = fields.Many2many('ams.chapter', string='Chapters')
    
    member_type_filter = fields.Selection([
        ('all', 'All Members'),
        ('individual', 'Individual'),
        ('corporate', 'Corporate'),
        ('student', 'Student'),
        ('honorary', 'Honorary')
    ], string='Member Type Filter', default='all')
    
    ams_invoice_types = fields.Selection([
        ('all', 'All AMS Invoices'),
        ('subscription', 'Subscription Invoices Only'),
        ('renewal', 'Renewal Invoices Only'),
        ('chapter', 'Chapter Fee Invoices Only'),
        ('donation', 'Donation Invoices Only')
    ], string='AMS Invoice Type Filter', default='all')
    
    # ========================
    # DISPLAY OPTIONS
    # ========================
    
    # Detail Level
    detail_level = fields.Selection([
        ('summary', 'Account Summary Only'),
        ('moves', 'Include Move Details'),
        ('lines', 'Include All Line Details')
    ], string='Detail Level', default='moves', required=True)
    
    # Display Options
    show_initial_balance = fields.Boolean('Show Initial Balance', default=True)
    show_foreign_currency = fields.Boolean('Show Foreign Currency', default=False)
    show_analytic_info = fields.Boolean('Show Analytic Information', default=False)
    show_zero_balance_accounts = fields.Boolean('Show Zero Balance Accounts', default=False)
    
    # Sorting Options
    sort_by = fields.Selection([
        ('account_code', 'Account Code'),
        ('account_name', 'Account Name'),
        ('date', 'Transaction Date'),
        ('amount', 'Amount')
    ], string='Sort By', default='account_code')
    
    sort_order = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending')
    ], string='Sort Order', default='asc')
    
    # Grouping Options
    group_by_account = fields.Boolean('Group by Account', default=True)
    group_by_partner = fields.Boolean('Group by Partner', default=False)
    group_by_journal = fields.Boolean('Group by Journal', default=False)
    group_by_period = fields.Selection([
        ('none', 'No Period Grouping'),
        ('month', 'By Month'),
        ('quarter', 'By Quarter'),
        ('year', 'By Year')
    ], string='Group by Period', default='none')
    
    # ========================
    # AMS DISPLAY OPTIONS
    # ========================
    
    # AMS-Specific Display
    show_member_info = fields.Boolean('Show Member Information', default=False,
        help="Display member details for AMS-related transactions")
    
    show_subscription_info = fields.Boolean('Show Subscription Information', default=False,
        help="Display subscription details for AMS transactions")
    
    show_chapter_info = fields.Boolean('Show Chapter Information', default=False,
        help="Display chapter information for AMS transactions")
    
    include_revenue_recognition = fields.Boolean('Include Revenue Recognition', default=False,
        help="Show deferred revenue recognition details")
    
    # ========================
    # OUTPUT OPTIONS
    # ========================
    
    # Export Format
    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('csv', 'CSV')
    ], string='Export Format', default='pdf')
    
    # Report Configuration
    report_title = fields.Char('Report Title', default='General Ledger Report')
    include_company_header = fields.Boolean('Include Company Header', default=True)
    include_filters_summary = fields.Boolean('Include Filters Summary', default=True)
    
    # Page Layout
    page_orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape')
    ], string='Page Orientation', default='landscape')
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    estimated_records = fields.Integer('Estimated Records', compute='_compute_estimated_records')
    filter_summary = fields.Text('Applied Filters', compute='_compute_filter_summary')
    
    @api.depends('date_from', 'date_to', 'account_ids', 'partner_ids', 'journal_ids')
    def _compute_estimated_records(self):
        for wizard in self:
            try:
                domain = wizard._get_move_line_domain()
                wizard.estimated_records = self.env['account.move.line'].search_count(domain)
            except Exception:
                wizard.estimated_records = 0
    
    @api.depends('account_selection', 'account_ids', 'partner_ids', 'journal_ids', 'include_ams_data')
    def _compute_filter_summary(self):
        for wizard in self:
            filters = []
            
            if wizard.account_selection == 'specific' and wizard.account_ids:
                filters.append(f"Accounts: {len(wizard.account_ids)} selected")
            elif wizard.account_selection == 'by_type' and wizard.account_types:
                filters.append(f"Account Type: {wizard.account_types}")
            elif wizard.account_selection == 'range':
                filters.append(f"Account Range: {wizard.account_code_from} - {wizard.account_code_to}")
            
            if wizard.partner_ids:
                filters.append(f"Partners: {len(wizard.partner_ids)} selected")
            
            if wizard.journal_ids:
                filters.append(f"Journals: {len(wizard.journal_ids)} selected")
            
            if wizard.include_ams_data:
                filters.append("AMS Data: Included")
                if wizard.subscription_type_ids:
                    filters.append(f"Subscription Types: {len(wizard.subscription_type_ids)} selected")
                if wizard.chapter_ids:
                    filters.append(f"Chapters: {len(wizard.chapter_ids)} selected")
            
            wizard.filter_summary = '\n'.join(filters) if filters else 'No specific filters applied'
    
    # ========================
    # ONCHANGE METHODS
    # ========================
    
    @api.onchange('account_selection')
    def _onchange_account_selection(self):
        """Clear account filters when selection method changes"""
        if self.account_selection == 'all':
            self.account_ids = [(5, 0, 0)]
            self.account_types = False
            self.account_code_from = False
            self.account_code_to = False
        elif self.account_selection == 'specific':
            self.account_types = False
            self.account_code_from = False
            self.account_code_to = False
        elif self.account_selection == 'by_type':
            self.account_ids = [(5, 0, 0)]
            self.account_code_from = False
            self.account_code_to = False
        elif self.account_selection == 'range':
            self.account_ids = [(5, 0, 0)]
            self.account_types = False
    
    @api.onchange('include_ams_data')
    def _onchange_include_ams_data(self):
        """Set AMS display options based on AMS data inclusion"""
        if self.include_ams_data:
            self.show_analytic_info = True
        else:
            self.show_member_info = False
            self.show_subscription_info = False
            self.show_chapter_info = False
            self.subscription_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]
    
    @api.onchange('detail_level')
    def _onchange_detail_level(self):
        """Adjust display options based on detail level"""
        if self.detail_level == 'summary':
            self.show_analytic_info = False
            self.show_member_info = False
            self.show_subscription_info = False
        elif self.detail_level == 'lines' and self.include_ams_data:
            self.show_analytic_info = True
    
    @api.onchange('export_format')
    def _onchange_export_format(self):
        """Adjust page orientation based on export format"""
        if self.export_format in ['xlsx', 'csv']:
            # Excel and CSV work better with landscape for detailed reports
            self.page_orientation = 'landscape'
    
    # ========================
    # VALIDATION METHODS
    # ========================
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_('From Date cannot be later than To Date.'))
    
    @api.constrains('account_code_from', 'account_code_to')
    def _check_account_range(self):
        for wizard in self:
            if wizard.account_selection == 'range':
                if not wizard.account_code_from or not wizard.account_code_to:
                    raise ValidationError(_('Both Account Code From and To are required for range selection.'))
                if wizard.account_code_from > wizard.account_code_to:
                    raise ValidationError(_('Account Code From cannot be greater than Account Code To.'))
    
    # ========================
    # DOMAIN BUILDING
    # ========================
    
    def _get_move_line_domain(self):
        """Build domain for account move lines"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('company_id', 'in', self.company_ids.ids)
        ]
        
        # Account filters
        if self.account_selection == 'specific' and self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        elif self.account_selection == 'by_type' and self.account_types:
            if self.account_types == 'asset':
                domain.append(('account_id.account_type', 'in', 
                              ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']))
            elif self.account_types == 'liability':
                domain.append(('account_id.account_type', 'in', 
                              ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']))
            elif self.account_types == 'equity':
                domain.append(('account_id.account_type', '=', 'equity'))
            elif self.account_types == 'income':
                domain.append(('account_id.account_type', '=', 'income'))
            elif self.account_types == 'expense':
                domain.append(('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']))
            elif self.account_types == 'receivable':
                domain.append(('account_id.account_type', '=', 'asset_receivable'))
            elif self.account_types == 'payable':
                domain.append(('account_id.account_type', '=', 'liability_payable'))
        elif self.account_selection == 'range':
            domain.append(('account_id.code', '>=', self.account_code_from))
            domain.append(('account_id.code', '<=', self.account_code_to))
        
        # Partner filters
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.partner_category_ids:
            partners_in_categories = self.env['res.partner'].search([
                ('category_id', 'in', self.partner_category_ids.ids)
            ])
            domain.append(('partner_id', 'in', partners_in_categories.ids))
        
        # Journal filters
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        
        # Analytic filters
        if self.analytic_account_ids:
            domain.append(('analytic_account_id', 'in', self.analytic_account_ids.ids))
        
        if self.analytic_tag_ids:
            domain.append(('analytic_tag_ids', 'in', self.analytic_tag_ids.ids))
        
        # AMS-specific filters
        if self.include_ams_data:
            if self.subscription_type_ids:
                domain.append(('move_id.subscription_type_id', 'in', self.subscription_type_ids.ids))
            
            if self.chapter_ids:
                domain.append(('move_id.ams_chapter_id', 'in', self.chapter_ids.ids))
            
            if self.member_type_filter != 'all':
                partners_by_type = self.env['res.partner'].search([
                    ('member_type', '=', self.member_type_filter)
                ])
                domain.append(('partner_id', 'in', partners_by_type.ids))
            
            if self.ams_invoice_types != 'all':
                if self.ams_invoice_types == 'subscription':
                    domain.append(('move_id.is_ams_subscription_invoice', '=', True))
                elif self.ams_invoice_types == 'renewal':
                    domain.append(('move_id.is_ams_renewal_invoice', '=', True))
                elif self.ams_invoice_types == 'chapter':
                    domain.append(('move_id.is_ams_chapter_fee', '=', True))
                elif self.ams_invoice_types == 'donation':
                    domain.append(('move_id.is_ams_donation', '=', True))
        
        return domain
    
    def _get_account_domain(self):
        """Build domain for accounts"""
        domain = [
            ('company_id', 'in', self.company_ids.ids),
            ('deprecated', '=', False)
        ]
        
        if self.account_selection == 'specific' and self.account_ids:
            domain.append(('id', 'in', self.account_ids.ids))
        elif self.account_selection == 'by_type' and self.account_types:
            # Apply same type filtering as in move lines
            if self.account_types == 'asset':
                domain.append(('account_type', 'in', 
                              ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed']))
            elif self.account_types == 'liability':
                domain.append(('account_type', 'in', 
                              ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']))
            elif self.account_types == 'equity':
                domain.append(('account_type', '=', 'equity'))
            elif self.account_types == 'income':
                domain.append(('account_type', '=', 'income'))
            elif self.account_types == 'expense':
                domain.append(('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']))
            elif self.account_types == 'receivable':
                domain.append(('account_type', '=', 'asset_receivable'))
            elif self.account_types == 'payable':
                domain.append(('account_type', '=', 'liability_payable'))
        elif self.account_selection == 'range':
            domain.append(('code', '>=', self.account_code_from))
            domain.append(('code', '<=', self.account_code_to))
        
        return domain
    
    # ========================
    # REPORT GENERATION
    # ========================
    
    def action_generate_report(self):
        """Generate the general ledger report"""
        try:
            # Validate configuration
            self._validate_configuration()
            
            # Generate report data
            report_data = self._generate_report_data()
            
            # Export based on format
            if self.export_format == 'pdf':
                return self._generate_pdf_report(report_data)
            elif self.export_format == 'xlsx':
                return self._generate_excel_report(report_data)
            elif self.export_format == 'csv':
                return self._generate_csv_report(report_data)
            else:
                raise UserError(_('Unsupported export format: %s') % self.export_format)
                
        except Exception as e:
            _logger.error(f"General ledger report generation failed: {str(e)}")
            raise UserError(_('Report generation failed: %s') % str(e))
    
    def _validate_configuration(self):
        """Validate report configuration"""
        if not self.company_ids:
            raise UserError(_('At least one company must be selected.'))
        
        if self.export_format == 'xlsx' and not xlsxwriter:
            raise UserError(_('Excel export requires xlsxwriter library. Please install it.'))
        
        if self.estimated_records > 100000:
            raise UserError(_('Report too large (%d records). Please narrow your selection.') % self.estimated_records)
    
    def _generate_report_data(self):
        """Generate the core report data"""
        # Get accounts to include in report
        account_domain = self._get_account_domain()
        accounts = self.env['account.account'].search(account_domain)
        
        # Get move lines
        move_line_domain = self._get_move_line_domain()
        
        # Build sort order
        sort_field = self.sort_by
        if sort_field == 'account_code':
            sort_field = 'account_id'
        elif sort_field == 'account_name':
            sort_field = 'account_id'
        
        order = f"{sort_field} {'desc' if self.sort_order == 'desc' else 'asc'}, date asc"
        
        move_lines = self.env['account.move.line'].search(move_line_domain, order=order)
        
        # Process data based on detail level
        if self.detail_level == 'summary':
            ledger_data = self._process_summary_data(accounts, move_lines)
        elif self.detail_level == 'moves':
            ledger_data = self._process_moves_data(accounts, move_lines)
        else:  # lines
            ledger_data = self._process_lines_data(accounts, move_lines)
        
        # Calculate totals
        total_debit = sum(line.debit for line in move_lines)
        total_credit = sum(line.credit for line in move_lines)
        
        return {
            'report_title': self.report_title,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_ids': self.company_ids,
            'currency': self.currency_id.name,
            'detail_level': self.detail_level,
            'ledger_data': ledger_data,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_debit - total_credit,
            'filter_summary': self.filter_summary,
            'estimated_records': self.estimated_records,
            'ams_data_included': self.include_ams_data,
        }
    
    def _process_summary_data(self, accounts, move_lines):
        """Process data for summary level report"""
        summary_data = {}
        
        for account in accounts:
            account_lines = move_lines.filtered(lambda l: l.account_id.id == account.id)
            
            if not account_lines and not self.show_zero_balance_accounts:
                continue
            
            total_debit = sum(account_lines.mapped('debit'))
            total_credit = sum(account_lines.mapped('credit'))
            balance = total_debit - total_credit
            
            # Calculate initial balance if requested
            initial_balance = 0.0
            if self.show_initial_balance:
                initial_balance = self._calculate_initial_balance(account)
            
            summary_data[account.id] = {
                'account': account,
                'initial_balance': initial_balance,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'balance': balance,
                'ending_balance': initial_balance + balance,
                'line_count': len(account_lines),
            }
        
        return summary_data
    
    def _process_moves_data(self, accounts, move_lines):
        """Process data for moves level report"""
        moves_data = {}
        
        for account in accounts:
            account_lines = move_lines.filtered(lambda l: l.account_id.id == account.id)
            
            if not account_lines and not self.show_zero_balance_accounts:
                continue
            
            # Group by move
            moves_by_account = {}
            for line in account_lines:
                move_id = line.move_id.id
                if move_id not in moves_by_account:
                    moves_by_account[move_id] = {
                        'move': line.move_id,
                        'lines': [],
                        'total_debit': 0.0,
                        'total_credit': 0.0,
                    }
                
                line_data = self._prepare_line_data(line)
                moves_by_account[move_id]['lines'].append(line_data)
                moves_by_account[move_id]['total_debit'] += line.debit
                moves_by_account[move_id]['total_credit'] += line.credit
            
            # Calculate account totals
            total_debit = sum(line.debit for line in account_lines)
            total_credit = sum(line.credit for line in account_lines)
            balance = total_debit - total_credit
            
            initial_balance = 0.0
            if self.show_initial_balance:
                initial_balance = self._calculate_initial_balance(account)
            
            moves_data[account.id] = {
                'account': account,
                'initial_balance': initial_balance,
                'moves': moves_by_account,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'balance': balance,
                'ending_balance': initial_balance + balance,
            }
        
        return moves_data
    
    def _process_lines_data(self, accounts, move_lines):
        """Process data for full lines level report"""
        lines_data = {}
        
        for account in accounts:
            account_lines = move_lines.filtered(lambda l: l.account_id.id == account.id)
            
            if not account_lines and not self.show_zero_balance_accounts:
                continue
            
            # Process each line
            processed_lines = []
            running_balance = 0.0
            
            # Calculate initial balance if requested
            initial_balance = 0.0
            if self.show_initial_balance:
                initial_balance = self._calculate_initial_balance(account)
                running_balance = initial_balance
            
            for line in account_lines:
                line_data = self._prepare_line_data(line)
                running_balance += line.debit - line.credit
                line_data['running_balance'] = running_balance
                processed_lines.append(line_data)
            
            # Calculate account totals
            total_debit = sum(account_lines.mapped('debit'))
            total_credit = sum(account_lines.mapped('credit'))
            balance = total_debit - total_credit
            
            lines_data[account.id] = {
                'account': account,
                'initial_balance': initial_balance,
                'lines': processed_lines,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'balance': balance,
                'ending_balance': initial_balance + balance,
            }
        
        return lines_data
    
    def _prepare_line_data(self, line):
        """Prepare individual line data with AMS information"""
        line_data = {
            'date': line.date,
            'move_name': line.move_id.name,
            'partner_name': line.partner_id.name if line.partner_id else '',
            'name': line.name,
            'debit': line.debit,
            'credit': line.credit,
            'balance': line.debit - line.credit,
            'ref': line.ref or '',
        }
        
        # Add analytic information if requested
        if self.show_analytic_info:
            line_data.update({
                'analytic_account': line.analytic_account_id.name if line.analytic_account_id else '',
                'analytic_tags': ', '.join(line.analytic_tag_ids.mapped('name')),
            })
        
        # Add foreign currency information if requested
        if self.show_foreign_currency and line.currency_id and line.currency_id != self.currency_id:
            line_data.update({
                'amount_currency': line.amount_currency,
                'currency_code': line.currency_id.name,
            })
        
        # Add AMS-specific information if requested
        if self.include_ams_data:
            move = line.move_id
            
            if self.show_member_info and line.partner_id and line.partner_id.is_ams_member:
                line_data.update({
                    'member_number': line.partner_id.member_number,
                    'member_type': line.partner_id.member_type,
                })
            
            if self.show_subscription_info and move.ams_subscription_id:
                line_data.update({
                    'subscription_type': move.ams_subscription_id.subscription_type_id.name if move.ams_subscription_id.subscription_type_id else '',
                    'subscription_reference': move.ams_subscription_id.name,
                })
            
            if self.show_chapter_info and move.ams_chapter_id:
                line_data.update({
                    'chapter_name': move.ams_chapter_id.name,
                    'chapter_code': move.ams_chapter_id.code,
                })
            
            # Add invoice type flags
            line_data.update({
                'is_subscription_invoice': move.is_ams_subscription_invoice,
                'is_renewal_invoice': move.is_ams_renewal_invoice,
                'is_chapter_fee': move.is_ams_chapter_fee,
                'is_donation': move.is_ams_donation,
            })
        
        return line_data
    
    def _calculate_initial_balance(self, account):
        """Calculate initial balance for an account"""
        initial_domain = [
            ('account_id', '=', account.id),
            ('date', '<', self.date_from),
            ('move_id.state', '=', 'posted'),
            ('company_id', 'in', self.company_ids.ids)
        ]
        
        initial_lines = self.env['account.move.line'].search(initial_domain)
        return sum(initial_lines.mapped('debit')) - sum(initial_lines.mapped('credit'))
    
    # ========================
    # EXPORT METHODS
    # ========================
    
    def _generate_excel_report(self, report_data):
        """Generate Excel report"""
        if not xlsxwriter:
            raise UserError(_('Excel export requires xlsxwriter library.'))
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1,
            'text_wrap': True
        })
        
        account_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E6F3FF',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00',
            'border': 1,
            'bg_color': '#FFFFCC'
        })
        
        # Create worksheet
        worksheet = workbook.add_worksheet('General Ledger')
        
        # Write header information
        row = 0
        worksheet.write(row, 0, report_data['report_title'], header_format)
        worksheet.merge_range(row, 0, row, 7, report_data['report_title'], header_format)
        row += 1
        
        worksheet.write(row, 0, f"Period: {report_data['date_from']} to {report_data['date_to']}")
        row += 1
        
        worksheet.write(row, 0, f"Currency: {report_data['currency']}")
        row += 1
        
        if self.include_filters_summary:
            worksheet.write(row, 0, "Filters Applied:")
            row += 1
            for filter_line in report_data['filter_summary'].split('\n'):
                worksheet.write(row, 0, filter_line)
                row += 1
        
        row += 1  # Empty row
        
        # Write data based on detail level
        if self.detail_level == 'summary':
            self._write_summary_excel(worksheet, report_data, row, header_format, currency_format, total_format)
        elif self.detail_level == 'moves':
            self._write_moves_excel(worksheet, report_data, row, header_format, account_header_format, currency_format, date_format, total_format)
        else:  # lines
            self._write_lines_excel(worksheet, report_data, row, header_format, account_header_format, currency_format, date_format, total_format)
        
        # Auto-adjust column widths
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 15)  # Reference
        worksheet.set_column('C:C', 20)  # Partner
        worksheet.set_column('D:D', 30)  # Description
        worksheet.set_column('E:E', 12)  # Debit
        worksheet.set_column('F:F', 12)  # Credit
        worksheet.set_column('G:G', 12)  # Balance
        
        if self.include_ams_data:
            worksheet.set_column('H:H', 15)  # Member Info
            worksheet.set_column('I:I', 15)  # Subscription Info
            worksheet.set_column('J:J', 15)  # Chapter Info
        
        workbook.close()
        output.seek(0)
        
        # Create attachment
        filename = f"general_ledger_{self.date_from}_{self.date_to}.xlsx"
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
    
    def _write_summary_excel(self, worksheet, report_data, start_row, header_format, currency_format, total_format):
        """Write summary data to Excel"""
        row = start_row
        
        # Headers
        headers = ['Account Code', 'Account Name', 'Initial Balance', 'Debit', 'Credit', 'Balance', 'Ending Balance', 'Lines']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # Data
        total_initial = total_debit = total_credit = total_balance = total_ending = 0.0
        
        for account_data in report_data['ledger_data'].values():
            account = account_data['account']
            worksheet.write(row, 0, account.code)
            worksheet.write(row, 1, account.name)
            worksheet.write(row, 2, account_data['initial_balance'], currency_format)
            worksheet.write(row, 3, account_data['total_debit'], currency_format)
            worksheet.write(row, 4, account_data['total_credit'], currency_format)
            worksheet.write(row, 5, account_data['balance'], currency_format)
            worksheet.write(row, 6, account_data['ending_balance'], currency_format)
            worksheet.write(row, 7, account_data['line_count'])
            
            total_initial += account_data['initial_balance']
            total_debit += account_data['total_debit']
            total_credit += account_data['total_credit']
            total_balance += account_data['balance']
            total_ending += account_data['ending_balance']
            
            row += 1
        
        # Totals row
        worksheet.write(row, 0, 'TOTALS', total_format)
        worksheet.write(row, 1, '', total_format)
        worksheet.write(row, 2, total_initial, total_format)
        worksheet.write(row, 3, total_debit, total_format)
        worksheet.write(row, 4, total_credit, total_format)
        worksheet.write(row, 5, total_balance, total_format)
        worksheet.write(row, 6, total_ending, total_format)
        worksheet.write(row, 7, '', total_format)
    
    def _write_moves_excel(self, worksheet, report_data, start_row, header_format, account_header_format, currency_format, date_format, total_format):
        """Write moves level data to Excel"""
        row = start_row
        
        # Headers
        headers = ['Date', 'Reference', 'Partner', 'Description', 'Debit', 'Credit', 'Balance']
        if self.include_ams_data:
            headers.extend(['Member', 'Subscription', 'Chapter'])
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # Data
        for account_data in report_data['ledger_data'].values():
            account = account_data['account']
            
            # Account header
            worksheet.write(row, 0, f"Account: {account.code} - {account.name}", account_header_format)
            worksheet.merge_range(row, 0, row, len(headers)-1, f"Account: {account.code} - {account.name}", account_header_format)
            row += 1
            
            # Initial balance
            if self.show_initial_balance and account_data['initial_balance'] != 0:
                worksheet.write(row, 0, '')
                worksheet.write(row, 1, 'Initial Balance')
                worksheet.write(row, 2, '')
                worksheet.write(row, 3, '')
                worksheet.write(row, 4, '')
                worksheet.write(row, 5, '')
                worksheet.write(row, 6, account_data['initial_balance'], currency_format)
                row += 1
            
            # Moves
            for move_data in account_data['moves'].values():
                move = move_data['move']
                
                # Move header (simplified for Excel)
                for line_data in move_data['lines']:
                    worksheet.write(row, 0, line_data['date'], date_format)
                    worksheet.write(row, 1, line_data['move_name'])
                    worksheet.write(row, 2, line_data['partner_name'])
                    worksheet.write(row, 3, line_data['name'])
                    worksheet.write(row, 4, line_data['debit'], currency_format)
                    worksheet.write(row, 5, line_data['credit'], currency_format)
                    worksheet.write(row, 6, line_data['balance'], currency_format)
                    
                    # AMS data
                    col = 7
                    if self.include_ams_data:
                        if self.show_member_info:
                            member_info = f"{line_data.get('member_number', '')} - {line_data.get('member_type', '')}"
                            worksheet.write(row, col, member_info)
                            col += 1
                        
                        if self.show_subscription_info:
                            subscription_info = f"{line_data.get('subscription_type', '')} - {line_data.get('subscription_reference', '')}"
                            worksheet.write(row, col, subscription_info)
                            col += 1
                        
                        if self.show_chapter_info:
                            chapter_info = f"{line_data.get('chapter_code', '')} - {line_data.get('chapter_name', '')}"
                            worksheet.write(row, col, chapter_info)
                    
                    row += 1
            
            # Account total
            worksheet.write(row, 0, 'Account Total:', total_format)
            worksheet.write(row, 1, '', total_format)
            worksheet.write(row, 2, '', total_format)
            worksheet.write(row, 3, '', total_format)
            worksheet.write(row, 4, account_data['total_debit'], total_format)
            worksheet.write(row, 5, account_data['total_credit'], total_format)
            worksheet.write(row, 6, account_data['ending_balance'], total_format)
            row += 2  # Empty row after each account
    
    def _write_lines_excel(self, worksheet, report_data, start_row, header_format, account_header_format, currency_format, date_format, total_format):
        """Write full lines data to Excel"""
        row = start_row
        
        # Headers
        headers = ['Date', 'Reference', 'Partner', 'Description', 'Debit', 'Credit', 'Balance', 'Running Balance']
        
        if self.show_analytic_info:
            headers.extend(['Analytic Account', 'Analytic Tags'])
        
        if self.show_foreign_currency:
            headers.extend(['Amount Currency', 'Currency'])
        
        if self.include_ams_data:
            if self.show_member_info:
                headers.extend(['Member Number', 'Member Type'])
            if self.show_subscription_info:
                headers.extend(['Subscription Type', 'Subscription Ref'])
            if self.show_chapter_info:
                headers.extend(['Chapter Code', 'Chapter Name'])
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        row += 1
        
        # Data
        for account_data in report_data['ledger_data'].values():
            account = account_data['account']
            
            # Account header
            worksheet.write(row, 0, f"Account: {account.code} - {account.name}", account_header_format)
            worksheet.merge_range(row, 0, row, len(headers)-1, f"Account: {account.code} - {account.name}", account_header_format)
            row += 1
            
            # Initial balance
            if self.show_initial_balance and account_data['initial_balance'] != 0:
                worksheet.write(row, 0, '')
                worksheet.write(row, 1, 'Initial Balance')
                worksheet.write(row, 2, '')
                worksheet.write(row, 3, '')
                worksheet.write(row, 4, '')
                worksheet.write(row, 5, '')
                worksheet.write(row, 6, '')
                worksheet.write(row, 7, account_data['initial_balance'], currency_format)
                row += 1
            
            # Lines
            for line_data in account_data['lines']:
                col = 0
                worksheet.write(row, col, line_data['date'], date_format); col += 1
                worksheet.write(row, col, line_data['move_name']); col += 1
                worksheet.write(row, col, line_data['partner_name']); col += 1
                worksheet.write(row, col, line_data['name']); col += 1
                worksheet.write(row, col, line_data['debit'], currency_format); col += 1
                worksheet.write(row, col, line_data['credit'], currency_format); col += 1
                worksheet.write(row, col, line_data['balance'], currency_format); col += 1
                worksheet.write(row, col, line_data['running_balance'], currency_format); col += 1
                
                # Analytic info
                if self.show_analytic_info:
                    worksheet.write(row, col, line_data.get('analytic_account', '')); col += 1
                    worksheet.write(row, col, line_data.get('analytic_tags', '')); col += 1
                
                # Foreign currency
                if self.show_foreign_currency:
                    worksheet.write(row, col, line_data.get('amount_currency', ''), currency_format); col += 1
                    worksheet.write(row, col, line_data.get('currency_code', '')); col += 1
                
                # AMS data
                if self.include_ams_data:
                    if self.show_member_info:
                        worksheet.write(row, col, line_data.get('member_number', '')); col += 1
                        worksheet.write(row, col, line_data.get('member_type', '')); col += 1
                    
                    if self.show_subscription_info:
                        worksheet.write(row, col, line_data.get('subscription_type', '')); col += 1
                        worksheet.write(row, col, line_data.get('subscription_reference', '')); col += 1
                    
                    if self.show_chapter_info:
                        worksheet.write(row, col, line_data.get('chapter_code', '')); col += 1
                        worksheet.write(row, col, line_data.get('chapter_name', '')); col += 1
                
                row += 1
            
            # Account total
            worksheet.write(row, 0, 'Account Total:', total_format)
            for col in range(1, 4):
                worksheet.write(row, col, '', total_format)
            worksheet.write(row, 4, account_data['total_debit'], total_format)
            worksheet.write(row, 5, account_data['total_credit'], total_format)
            worksheet.write(row, 6, '', total_format)
            worksheet.write(row, 7, account_data['ending_balance'], total_format)
            row += 2  # Empty row after each account
    
    def _generate_csv_report(self, report_data):
        """Generate CSV report"""
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([report_data['report_title']])
        writer.writerow([f"Period: {report_data['date_from']} to {report_data['date_to']}"])
        writer.writerow([f"Currency: {report_data['currency']}"])
        writer.writerow([])  # Empty row
        
        if self.detail_level == 'summary':
            # Summary headers
            headers = ['Account Code', 'Account Name', 'Initial Balance', 'Debit', 'Credit', 'Balance', 'Ending Balance', 'Lines']
            writer.writerow(headers)
            
            for account_data in report_data['ledger_data'].values():
                account = account_data['account']
                writer.writerow([
                    account.code,
                    account.name,
                    account_data['initial_balance'],
                    account_data['total_debit'],
                    account_data['total_credit'],
                    account_data['balance'],
                    account_data['ending_balance'],
                    account_data['line_count']
                ])
        
        elif self.detail_level == 'lines':
            # Detailed headers
            headers = ['Account Code', 'Account Name', 'Date', 'Reference', 'Partner', 'Description', 'Debit', 'Credit', 'Balance', 'Running Balance']
            
            if self.show_analytic_info:
                headers.extend(['Analytic Account', 'Analytic Tags'])
            
            if self.include_ams_data:
                if self.show_member_info:
                    headers.extend(['Member Number', 'Member Type'])
                if self.show_subscription_info:
                    headers.extend(['Subscription Type', 'Subscription Ref'])
                if self.show_chapter_info:
                    headers.extend(['Chapter Code', 'Chapter Name'])
            
            writer.writerow(headers)
            
            for account_data in report_data['ledger_data'].values():
                account = account_data['account']
                
                # Initial balance row
                if self.show_initial_balance and account_data['initial_balance'] != 0:
                    row = [account.code, account.name, '', 'Initial Balance', '', '', '', '', '', account_data['initial_balance']]
                    # Pad with empty values for additional columns
                    while len(row) < len(headers):
                        row.append('')
                    writer.writerow(row)
                
                # Detail lines
                for line_data in account_data['lines']:
                    row = [
                        account.code,
                        account.name,
                        line_data['date'],
                        line_data['move_name'],
                        line_data['partner_name'],
                        line_data['name'],
                        line_data['debit'],
                        line_data['credit'],
                        line_data['balance'],
                        line_data['running_balance']
                    ]
                    
                    if self.show_analytic_info:
                        row.extend([
                            line_data.get('analytic_account', ''),
                            line_data.get('analytic_tags', '')
                        ])
                    
                    if self.include_ams_data:
                        if self.show_member_info:
                            row.extend([
                                line_data.get('member_number', ''),
                                line_data.get('member_type', '')
                            ])
                        
                        if self.show_subscription_info:
                            row.extend([
                                line_data.get('subscription_type', ''),
                                line_data.get('subscription_reference', '')
                            ])
                        
                        if self.show_chapter_info:
                            row.extend([
                                line_data.get('chapter_code', ''),
                                line_data.get('chapter_name', '')
                            ])
                    
                    writer.writerow(row)
                
                # Account total row
                total_row = [account.code, account.name, '', 'ACCOUNT TOTAL', '', '', 
                            account_data['total_debit'], account_data['total_credit'], 
                            '', account_data['ending_balance']]
                while len(total_row) < len(headers):
                    total_row.append('')
                writer.writerow(total_row)
                writer.writerow([])  # Empty row between accounts
        
        # Create attachment
        filename = f"general_ledger_{self.date_from}_{self.date_to}.csv"
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
    
    def action_preview_accounts(self):
        """Preview which accounts will be included in the report"""
        account_domain = self._get_account_domain()
        accounts = self.env['account.account'].search(account_domain)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounts in Report',
            'res_model': 'account.account',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', accounts.ids)],
            'context': {'create': False, 'edit': False}
        }
    
    def action_reset_filters(self):
        """Reset all filters to default values"""
        self.write({
            'account_selection': 'all',
            'account_ids': [(5, 0, 0)],
            'account_types': False,
            'account_code_from': False,
            'account_code_to': False,
            'partner_ids': [(5, 0, 0)],
            'partner_category_ids': [(5, 0, 0)],
            'journal_ids': [(5, 0, 0)],
            'analytic_account_ids': [(5, 0, 0)],
            'analytic_tag_ids': [(5, 0, 0)],
            'subscription_type_ids': [(5, 0, 0)],
            'chapter_ids': [(5, 0, 0)],
            'member_type_filter': 'all',
            'ams_invoice_types': 'all',
            'show_member_info': False,
            'show_subscription_info': False,
            'show_chapter_info': False,
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
    
    def action_quick_setup(self):
        """Quick setup for common report configurations"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quick Setup - General Ledger',
            'res_model': 'general.ledger.quick.setup',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wizard_id': self.id}
        }


class GeneralLedgerQuickSetup(models.TransientModel):
    """
    Quick setup wizard for common general ledger configurations
    """
    _name = 'general.ledger.quick.setup'
    _description = 'General Ledger Quick Setup'
    
    wizard_id = fields.Many2one('general.ledger.wizard', 'Main Wizard', required=True)
    
    setup_type = fields.Selection([
        ('all_accounts', 'All Accounts - Summary'),
        ('receivables_payables', 'Receivables & Payables - Detailed'),
        ('income_expense', 'Income & Expenses - Detailed'),
        ('ams_subscription', 'AMS Subscription Accounts'),
        ('ams_member_analysis', 'AMS Member Analysis'),
        ('cash_bank', 'Cash & Bank Accounts'),
        ('custom', 'Custom Configuration')
    ], string='Setup Type', required=True)
    
    def action_apply_setup(self):
        """Apply the selected quick setup"""
        wizard = self.wizard_id
        
        if self.setup_type == 'all_accounts':
            wizard.write({
                'account_selection': 'all',
                'detail_level': 'summary',
                'show_initial_balance': True,
                'show_zero_balance_accounts': False,
            })
        
        elif self.setup_type == 'receivables_payables':
            wizard.write({
                'account_selection': 'by_type',
                'account_types': 'receivable',
                'detail_level': 'lines',
                'show_initial_balance': True,
                'group_by_partner': True,
            })
        
        elif self.setup_type == 'income_expense':
            wizard.write({
                'account_selection': 'by_type',
                'account_types': 'income',
                'detail_level': 'moves',
                'show_analytic_info': True,
            })
        
        elif self.setup_type == 'ams_subscription':
            # Find AMS subscription accounts
            ams_accounts = self.env['account.account'].search([
                ('is_ams_subscription_account', '=', True)
            ])
            
            wizard.write({
                'account_selection': 'specific',
                'account_ids': [(6, 0, ams_accounts.ids)],
                'detail_level': 'lines',
                'include_ams_data': True,
                'show_member_info': True,
                'show_subscription_info': True,
                'ams_invoice_types': 'subscription',
            })
        
        elif self.setup_type == 'ams_member_analysis':
            wizard.write({
                'detail_level': 'lines',
                'include_ams_data': True,
                'show_member_info': True,
                'show_subscription_info': True,
                'show_chapter_info': True,
                'group_by_partner': True,
            })
        
        elif self.setup_type == 'cash_bank':
            cash_accounts = self.env['account.account'].search([
                ('account_type', '=', 'asset_cash')
            ])
            
            wizard.write({
                'account_selection': 'specific',
                'account_ids': [(6, 0, cash_accounts.ids)],
                'detail_level': 'lines',
                'show_initial_balance': True,
            })
        
        return {'type': 'ir.actions.act_window_close'}