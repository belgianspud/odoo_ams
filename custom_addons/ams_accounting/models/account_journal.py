from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    """
    Enhanced journal model with AMS-specific features and validations
    """
    _inherit = 'account.journal'
    
    # AMS Integration Fields
    is_ams_journal = fields.Boolean('AMS Journal', default=False,
        help="Mark this journal for AMS-specific transactions")
    
    ams_journal_type = fields.Selection([
        ('subscription', 'Subscription Revenue'),
        ('chapter', 'Chapter Fees'),
        ('renewal', 'Renewal Billing'),
        ('payment', 'Member Payments'),
        ('expense', 'AMS Expenses'),
        ('allocation', 'Chapter Allocations'),
        ('adjustment', 'Financial Adjustments')
    ], string='AMS Journal Type',
    help="Categorize this journal for AMS transaction types")
    
    # Chapter-specific journals
    chapter_id = fields.Many2one('ams.chapter', 'Related Chapter',
        help="Link this journal to a specific chapter")
    
    # Enhanced Security and Controls
    restrict_date_entries = fields.Boolean('Restrict Date Entries', default=False,
        help="Only allow entries within the current period")
    
    max_entry_amount = fields.Float('Maximum Entry Amount', default=0.0,
        help="Maximum amount allowed per journal entry (0 = no limit)")
    
    require_analytic_account = fields.Boolean('Require Analytic Account', default=False,
        help="All entries in this journal must have an analytic account")
    
    default_analytic_account_id = fields.Many2one('account.analytic.account', 'Default Analytic Account',
        help="Default analytic account for entries in this journal")
    
    # Approval Workflow
    require_approval = fields.Boolean('Require Approval', default=False,
        help="Journal entries require approval before posting")
    
    approval_amount_limit = fields.Float('Approval Amount Limit', default=1000.0,
        help="Entries above this amount require approval")
    
    approver_user_ids = fields.Many2many('res.users', 'journal_approver_rel',
                                        'journal_id', 'user_id', 'Approvers',
                                        help="Users who can approve entries in this journal")
    
    # Bank Statement Integration
    auto_reconcile_ams = fields.Boolean('Auto Reconcile AMS Payments', default=False,
        help="Automatically reconcile AMS subscription payments")
    
    ams_payment_account_id = fields.Many2one('account.account', 'AMS Payment Account',
        help="Account used for AMS payment reconciliation")
    
    # Reporting and Analytics
    include_in_ams_reports = fields.Boolean('Include in AMS Reports', default=True,
        help="Include this journal in AMS financial reports")
    
    journal_category = fields.Selection([
        ('operating', 'Operating'),
        ('investing', 'Investing'),
        ('financing', 'Financing'),
        ('other', 'Other')
    ], string='Journal Category', default='operating',
    help="Categorize journal for cash flow reporting")
    
    # Statistics
    ams_entries_count = fields.Integer('AMS Entries Count', compute='_compute_ams_statistics')
    ams_total_amount = fields.Float('AMS Total Amount', compute='_compute_ams_statistics')
    last_ams_entry_date = fields.Date('Last AMS Entry Date', compute='_compute_ams_statistics')
    
    @api.depends('move_ids')
    def _compute_ams_statistics(self):
        for journal in self:
            ams_moves = journal.move_ids.filtered(
                lambda m: m.is_ams_subscription_invoice or 
                         m.ams_subscription_id or 
                         m.ams_chapter_id
            )
            
            journal.ams_entries_count = len(ams_moves)
            journal.ams_total_amount = sum(ams_moves.mapped('amount_total'))
            journal.last_ams_entry_date = max(ams_moves.mapped('date')) if ams_moves else False
    
    @api.onchange('is_ams_journal')
    def _onchange_is_ams_journal(self):
        """Set defaults for AMS journals"""
        if self.is_ams_journal:
            self.include_in_ams_reports = True
            if not self.ams_journal_type:
                if self.type == 'sale':
                    self.ams_journal_type = 'subscription'
                elif self.type == 'cash':
                    self.ams_journal_type = 'payment'
                elif self.type == 'purchase':
                    self.ams_journal_type = 'expense'
    
    @api.onchange('ams_journal_type')
    def _onchange_ams_journal_type(self):
        """Set defaults based on AMS journal type"""
        if self.ams_journal_type == 'subscription':
            self.require_analytic_account = True
        elif self.ams_journal_type == 'chapter':
            self.require_analytic_account = True
        elif self.ams_journal_type == 'payment':
            self.auto_reconcile_ams = True
    
    @api.onchange('chapter_id')
    def _onchange_chapter_id(self):
        """Set chapter-specific defaults"""
        if self.chapter_id:
            self.default_analytic_account_id = self.chapter_id.analytic_account_id
            self.ams_journal_type = 'chapter'
            self.is_ams_journal = True
    
    def action_view_ams_entries(self):
        """View AMS-related entries in this journal"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'AMS Entries - {self.name}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('journal_id', '=', self.id),
                '|', '|',
                ('is_ams_subscription_invoice', '=', True),
                ('ams_subscription_id', '!=', False),
                ('ams_chapter_id', '!=', False)
            ],
            'context': {
                'search_default_group_by_subscription': 1,
            }
        }
    
    def action_reconcile_ams_payments(self):
        """Manually trigger AMS payment reconciliation"""
        if not self.auto_reconcile_ams:
            raise UserError(_('Auto reconciliation is not enabled for this journal.'))
        
        return self._reconcile_ams_payments()
    
    def _reconcile_ams_payments(self):
        """Reconcile AMS subscription payments automatically"""
        if not self.ams_payment_account_id:
            return
        
        # Find unreconciled payment lines
        unreconciled_lines = self.env['account.move.line'].search([
            ('journal_id', '=', self.id),
            ('account_id', '=', self.ams_payment_account_id.id),
            ('reconciled', '=', False),
            ('credit', '>', 0)  # Payment lines have credit
        ])
        
        reconciled_count = 0
        
        for payment_line in unreconciled_lines:
            # Try to find matching subscription invoice
            matching_invoices = self.env['account.move.line'].search([
                ('partner_id', '=', payment_line.partner_id.id),
                ('account_id', '=', payment_line.partner_id.property_account_receivable_id.id),
                ('reconciled', '=', False),
                ('debit', '=', payment_line.credit),
                ('move_id.is_ams_subscription_invoice', '=', True)
            ])
            
            if matching_invoices:
                # Reconcile with the first matching invoice
                (payment_line + matching_invoices[0]).reconcile()
                reconciled_count += 1
        
        if reconciled_count > 0:
            _logger.info(f"Auto-reconciled {reconciled_count} AMS payments in journal {self.name}")
        
        return reconciled_count
    
    def validate_journal_entry(self, move):
        """Validate journal entry based on AMS journal settings"""
        if not self.is_ams_journal:
            return True
        
        # Check date restrictions
        if self.restrict_date_entries:
            current_period_start = fields.Date.today().replace(day=1)
            current_period_end = current_period_start + relativedelta(months=1) - timedelta(days=1)
            
            if move.date < current_period_start or move.date > current_period_end:
                raise UserError(_('This journal only allows entries within the current period.'))
        
        # Check maximum entry amount
        if self.max_entry_amount > 0 and abs(move.amount_total) > self.max_entry_amount:
            raise UserError(_('Entry amount exceeds the maximum limit of %s for this journal.') % self.max_entry_amount)
        
        # Check analytic account requirement
        if self.require_analytic_account:
            lines_without_analytic = move.line_ids.filtered(
                lambda l: not l.analytic_account_id and l.account_id.account_type not in ['asset_cash', 'liability_payable', 'asset_receivable']
            )
            
            if lines_without_analytic:
                raise UserError(_('All lines in this journal must have an analytic account assigned.'))
        
        # Check approval requirement
        if self.require_approval and abs(move.amount_total) > self.approval_amount_limit:
            if not move.approval_user_id or move.approval_user_id not in self.approver_user_ids:
                raise UserError(_('This entry requires approval from an authorized user.'))
        
        return True
    
    def create_chapter_journal(self, chapter):
        """Create a dedicated journal for a chapter"""
        journal_vals = {
            'name': f'Chapter {chapter.name}',
            'code': f'CH{chapter.code}',
            'type': 'general',
            'company_id': self.env.company.id,
            'is_ams_journal': True,
            'ams_journal_type': 'chapter',
            'chapter_id': chapter.id,
            'default_analytic_account_id': chapter.analytic_account_id.id if chapter.analytic_account_id else False,
            'require_analytic_account': True,
            'include_in_ams_reports': True,
        }
        
        return self.create(journal_vals)
    
    @api.model
    def setup_ams_journals(self):
        """Setup default AMS journals"""
        company = self.env.company
        
        # Default AMS journals to create
        ams_journals = [
            {
                'name': 'AMS Subscription Revenue',
                'code': 'AMSSUB',
                'type': 'sale',
                'ams_journal_type': 'subscription',
                'require_analytic_account': True,
            },
            {
                'name': 'AMS Chapter Fees',
                'code': 'AMSCHP',
                'type': 'sale',
                'ams_journal_type': 'chapter',
                'require_analytic_account': True,
            },
            {
                'name': 'AMS Renewal Billing',
                'code': 'AMSREN',
                'type': 'sale',
                'ams_journal_type': 'renewal',
                'require_analytic_account': True,
            },
            {
                'name': 'AMS Member Payments',
                'code': 'AMSPAY',
                'type': 'cash',
                'ams_journal_type': 'payment',
                'auto_reconcile_ams': True,
            },
            {
                'name': 'AMS Expenses',
                'code': 'AMSEXP',
                'type': 'purchase',
                'ams_journal_type': 'expense',
                'require_analytic_account': True,
            },
        ]
        
        created_journals = []
        
        for journal_data in ams_journals:
            # Check if journal already exists
            existing_journal = self.search([
                ('code', '=', journal_data['code']),
                ('company_id', '=', company.id)
            ])
            
            if not existing_journal:
                journal_data.update({
                    'company_id': company.id,
                    'is_ams_journal': True,
                    'include_in_ams_reports': True,
                })
                
                journal = self.create(journal_data)
                created_journals.append(journal)
                _logger.info(f"Created AMS journal: {journal.name}")
        
        return created_journals
    
    def get_journal_statistics(self):
        """Get comprehensive statistics for this journal"""
        current_year_start = fields.Date.today().replace(month=1, day=1)
        
        # Basic statistics
        all_moves = self.move_ids.filtered(lambda m: m.state == 'posted')
        current_year_moves = all_moves.filtered(lambda m: m.date >= current_year_start)
        
        # AMS-specific statistics
        ams_moves = all_moves.filtered(
            lambda m: m.is_ams_subscription_invoice or m.ams_subscription_id or m.ams_chapter_id
        )
        
        ams_current_year = ams_moves.filtered(lambda m: m.date >= current_year_start)
        
        return {
            'total_entries': len(all_moves),
            'current_year_entries': len(current_year_moves),
            'current_year_amount': sum(current_year_moves.mapped('amount_total')),
            'ams_entries_total': len(ams_moves),
            'ams_entries_current_year': len(ams_current_year),
            'ams_amount_current_year': sum(ams_current_year.mapped('amount_total')),
            'average_entry_amount': sum(all_moves.mapped('amount_total')) / len(all_moves) if all_moves else 0,
            'last_entry_date': max(all_moves.mapped('date')) if all_moves else False,
        }
    
    @api.model
    def get_ams_journal_dashboard_data(self):
        """Get dashboard data for AMS journals"""
        ams_journals = self.search([('is_ams_journal', '=', True)])
        
        dashboard_data = {
            'total_ams_journals': len(ams_journals),
            'journal_types': {},
            'total_entries': 0,
            'total_amount': 0.0,
            'journals_by_chapter': {},
        }
        
        for journal in ams_journals:
            stats = journal.get_journal_statistics()
            
            # Aggregate by journal type
            journal_type = journal.ams_journal_type or 'other'
            if journal_type not in dashboard_data['journal_types']:
                dashboard_data['journal_types'][journal_type] = {
                    'count': 0,
                    'entries': 0,
                    'amount': 0.0
                }
            
            dashboard_data['journal_types'][journal_type]['count'] += 1
            dashboard_data['journal_types'][journal_type]['entries'] += stats['current_year_entries']
            dashboard_data['journal_types'][journal_type]['amount'] += stats['current_year_amount']
            
            # Aggregate totals
            dashboard_data['total_entries'] += stats['current_year_entries']
            dashboard_data['total_amount'] += stats['current_year_amount']
            
            # Chapter-specific data
            if journal.chapter_id:
                chapter_name = journal.chapter_id.name
                if chapter_name not in dashboard_data['journals_by_chapter']:
                    dashboard_data['journals_by_chapter'][chapter_name] = {
                        'journals': 0,
                        'entries': 0,
                        'amount': 0.0
                    }
                
                dashboard_data['journals_by_chapter'][chapter_name]['journals'] += 1
                dashboard_data['journals_by_chapter'][chapter_name]['entries'] += stats['current_year_entries']
                dashboard_data['journals_by_chapter'][chapter_name]['amount'] += stats['current_year_amount']
        
        return dashboard_data
    
    @api.constrains('chapter_id', 'ams_journal_type')
    def _check_chapter_journal_type(self):
        """Validate chapter journal configuration"""
        for journal in self:
            if journal.chapter_id and journal.ams_journal_type not in ['chapter', 'allocation', 'expense']:
                raise ValidationError(_('Chapter journals must be of type Chapter, Allocation, or Expense.'))
    
    @api.constrains('max_entry_amount')
    def _check_max_entry_amount(self):
        """Validate maximum entry amount"""
        for journal in self:
            if journal.max_entry_amount < 0:
                raise ValidationError(_('Maximum entry amount cannot be negative.'))
    
    @api.constrains('approver_user_ids', 'require_approval')
    def _check_approval_configuration(self):
        """Validate approval configuration"""
        for journal in self:
            if journal.require_approval and not journal.approver_user_ids:
                raise ValidationError(_('Journals requiring approval must have at least one approver assigned.'))