from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ChapterBudget(models.Model):
    _name = 'membership.chapter.budget'
    _description = 'Chapter Budget'
    _order = 'fiscal_year desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Budget Name',
        compute='_compute_name',
        store=True,
        help="Budget name"
    )
    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        required=True,
        help="Chapter this budget belongs to"
    )
    fiscal_year = fields.Char(
        string='Fiscal Year',
        required=True,
        help="Fiscal year for this budget (e.g., '2024', '2024-2025')"
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        help="Budget period start date"
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        help="Budget period end date"
    )
    
    # Budget Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Financial Totals
    budgeted_income = fields.Monetary(
        string='Budgeted Income',
        currency_field='currency_id',
        help="Total budgeted income for the period"
    )
    budgeted_expenses = fields.Monetary(
        string='Budgeted Expenses',
        currency_field='currency_id',
        help="Total budgeted expenses for the period"
    )
    budgeted_net = fields.Monetary(
        string='Budgeted Net',
        compute='_compute_budget_totals',
        currency_field='currency_id',
        help="Net budget (income - expenses)"
    )
    
    # Actual Totals
    actual_income = fields.Monetary(
        string='Actual Income',
        compute='_compute_actual_totals',
        currency_field='currency_id',
        help="Actual income received"
    )
    actual_expenses = fields.Monetary(
        string='Actual Expenses',
        compute='_compute_actual_totals',
        currency_field='currency_id',
        help="Actual expenses incurred"
    )
    actual_net = fields.Monetary(
        string='Actual Net',
        compute='_compute_actual_totals',
        currency_field='currency_id',
        help="Actual net (income - expenses)"
    )
    
    # Variance Analysis
    income_variance = fields.Monetary(
        string='Income Variance',
        compute='_compute_variances',
        currency_field='currency_id',
        help="Actual vs budgeted income variance"
    )
    expense_variance = fields.Monetary(
        string='Expense Variance',
        compute='_compute_variances',
        currency_field='currency_id',
        help="Actual vs budgeted expense variance"
    )
    net_variance = fields.Monetary(
        string='Net Variance',
        compute='_compute_variances',
        currency_field='currency_id',
        help="Actual vs budgeted net variance"
    )
    
    # Budget Lines
    income_line_ids = fields.One2many(
        'membership.chapter.budget.line',
        'budget_id',
        string='Income Lines',
        domain=[('line_type', '=', 'income')]
    )
    expense_line_ids = fields.One2many(
        'membership.chapter.budget.line',
        'budget_id',
        string='Expense Lines',
        domain=[('line_type', '=', 'expense')]
    )
    
    # Transactions
    transaction_ids = fields.One2many(
        'membership.chapter.transaction',
        'budget_id',
        string='Transactions'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('chapter_id.name', 'fiscal_year')
    def _compute_name(self):
        for budget in self:
            if budget.chapter_id and budget.fiscal_year:
                budget.name = f"{budget.chapter_id.name} - {budget.fiscal_year} Budget"
            else:
                budget.name = "New Budget"

    @api.depends('budgeted_income', 'budgeted_expenses')
    def _compute_budget_totals(self):
        for budget in self:
            budget.budgeted_net = budget.budgeted_income - budget.budgeted_expenses

    @api.depends('transaction_ids.amount', 'transaction_ids.transaction_type')
    def _compute_actual_totals(self):
        for budget in self:
            income_transactions = budget.transaction_ids.filtered(lambda t: t.transaction_type == 'income')
            expense_transactions = budget.transaction_ids.filtered(lambda t: t.transaction_type == 'expense')
            
            budget.actual_income = sum(income_transactions.mapped('amount'))
            budget.actual_expenses = sum(expense_transactions.mapped('amount'))
            budget.actual_net = budget.actual_income - budget.actual_expenses

    @api.depends('actual_income', 'budgeted_income', 'actual_expenses', 'budgeted_expenses')
    def _compute_variances(self):
        for budget in self:
            budget.income_variance = budget.actual_income - budget.budgeted_income
            budget.expense_variance = budget.actual_expenses - budget.budgeted_expenses
            budget.net_variance = budget.actual_net - budget.budgeted_net

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for budget in self:
            if budget.start_date and budget.end_date:
                if budget.start_date > budget.end_date:
                    raise ValidationError(_("Start date cannot be after end date."))

    def action_approve(self):
        """Approve budget"""
        self.state = 'approved'
        self.message_post(body=_("Budget approved."))

    def action_activate(self):
        """Activate budget"""
        self.state = 'active'
        self.message_post(body=_("Budget activated."))

    def action_close(self):
        """Close budget"""
        self.state = 'closed'
        self.message_post(body=_("Budget closed."))

    def action_view_transactions(self):
        """View budget transactions"""
        self.ensure_one()
        return {
            'name': f"Transactions - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.transaction',
            'view_mode': 'tree,form',
            'domain': [('budget_id', '=', self.id)],
            'context': {'default_budget_id': self.id, 'default_chapter_id': self.chapter_id.id},
        }


class ChapterBudgetLine(models.Model):
    _name = 'membership.chapter.budget.line'
    _description = 'Budget Line'
    _order = 'sequence, name'

    budget_id = fields.Many2one(
        'membership.chapter.budget',
        string='Budget',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Description', required=True)
    
    line_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Type', required=True)
    
    category = fields.Selection([
        # Income categories
        ('membership_dues', 'Membership Dues'),
        ('event_revenue', 'Event Revenue'),
        ('sponsorship', 'Sponsorship'),
        ('donations', 'Donations'),
        ('grants', 'Grants'),
        ('other_income', 'Other Income'),
        # Expense categories
        ('venue_costs', 'Venue Costs'),
        ('catering', 'Catering'),
        ('speakers', 'Speakers/Presenters'),
        ('marketing', 'Marketing'),
        ('supplies', 'Supplies'),
        ('travel', 'Travel'),
        ('administration', 'Administration'),
        ('other_expense', 'Other Expense')
    ], string='Category', required=True)
    
    budgeted_amount = fields.Monetary(
        string='Budgeted Amount',
        currency_field='currency_id',
        required=True
    )
    actual_amount = fields.Monetary(
        string='Actual Amount',
        compute='_compute_actual_amount',
        currency_field='currency_id'
    )
    variance = fields.Monetary(
        string='Variance',
        compute='_compute_variance',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.currency_id',
        readonly=True
    )

    @api.depends('budget_id.transaction_ids.amount', 'budget_id.transaction_ids.category')
    def _compute_actual_amount(self):
        for line in self:
            transactions = line.budget_id.transaction_ids.filtered(
                lambda t: t.category == line.category and t.transaction_type == line.line_type
            )
            line.actual_amount = sum(transactions.mapped('amount'))

    @api.depends('actual_amount', 'budgeted_amount')
    def _compute_variance(self):
        for line in self:
            line.variance = line.actual_amount - line.budgeted_amount


class ChapterTransaction(models.Model):
    _name = 'membership.chapter.transaction'
    _description = 'Chapter Financial Transaction'
    _order = 'transaction_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Description',
        required=True,
        help="Description of the transaction"
    )
    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        required=True,
        help="Chapter this transaction belongs to"
    )
    budget_id = fields.Many2one(
        'membership.chapter.budget',
        string='Budget',
        help="Budget this transaction is part of"
    )
    transaction_date = fields.Date(
        string='Transaction Date',
        required=True,
        default=fields.Date.today,
        help="Date of the transaction"
    )
    
    # Transaction Details
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Type', required=True, tracking=True)
    
    category = fields.Selection([
        # Income categories
        ('membership_dues', 'Membership Dues'),
        ('event_revenue', 'Event Revenue'),
        ('sponsorship', 'Sponsorship'),
        ('donations', 'Donations'),
        ('grants', 'Grants'),
        ('other_income', 'Other Income'),
        # Expense categories
        ('venue_costs', 'Venue Costs'),
        ('catering', 'Catering'),
        ('speakers', 'Speakers/Presenters'),
        ('marketing', 'Marketing'),
        ('supplies', 'Supplies'),
        ('travel', 'Travel'),
        ('administration', 'Administration'),
        ('other_expense', 'Other Expense')
    ], string='Category', required=True)
    
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        help="Transaction amount"
    )
    
    # Payment Information
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('other', 'Other')
    ], string='Payment Method')
    
    reference = fields.Char(
        string='Reference',
        help="Check number, transaction ID, etc."
    )
    
    # Related Records
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help="Related contact (vendor, member, etc.)"
    )
    meeting_id = fields.Many2one(
        'membership.chapter.meeting',
        string='Related Meeting',
        help="Meeting this transaction is related to"
    )
    event_id = fields.Many2one(
        'event.event',
        string='Related Event',
        help="Event this transaction is related to"
    )
    
    # Status and Approval
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True, tracking=True)
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help="User who approved this transaction"
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        help="When transaction was approved"
    )
    
    # Supporting Documents
    receipt = fields.Binary(
        string='Receipt',
        help="Receipt or supporting document"
    )
    receipt_filename = fields.Char(string='Receipt Filename')
    
    notes = fields.Text(
        string='Notes',
        help="Additional notes about the transaction"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.constrains('amount')
    def _check_amount(self):
        for transaction in self:
            if transaction.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero."))

    def action_submit(self):
        """Submit transaction for approval"""
        self.state = 'submitted'
        self.message_post(body=_("Transaction submitted for approval."))

    def action_approve(self):
        """Approve transaction"""
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        self.message_post(body=_("Transaction approved by %s.") % self.env.user.name)

    def action_reject(self):
        """Reject transaction"""
        self.state = 'rejected'
        self.message_post(body=_("Transaction rejected."))

    @api.onchange('transaction_type')
    def _onchange_transaction_type(self):
        """Update category options based on transaction type"""
        if self.transaction_type:
            # This will update the available categories in the UI
            return {}


class ChapterExpense(models.Model):
    _name = 'membership.chapter.expense'
    _description = 'Chapter Expense (Simplified)'
    _order = 'date desc'

    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        required=True
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )
    description = fields.Char(
        string='Description',
        required=True
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id'
    )
    category = fields.Selection([
        ('meeting', 'Meeting Costs'),
        ('events', 'Event Expenses'),
        ('marketing', 'Marketing'),
        ('admin', 'Administrative'),
        ('travel', 'Travel'),
        ('other', 'Other')
    ], string='Category', required=True)
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )


# Enhanced Chapter model with financial features
class MembershipChapter(models.Model):
    _inherit = 'membership.chapter'

    # Financial Management
    budget_ids = fields.One2many(
        'membership.chapter.budget',
        'chapter_id',
        string='Budgets'
    )
    current_budget_id = fields.Many2one(
        'membership.chapter.budget',
        string='Current Budget',
        compute='_compute_current_budget'
    )
    transaction_ids = fields.One2many(
        'membership.chapter.transaction',
        'chapter_id',
        string='Transactions'
    )
    expense_ids = fields.One2many(
        'membership.chapter.expense',
        'chapter_id',
        string='Expenses'
    )
    
    # Financial Settings
    requires_budget_approval = fields.Boolean(
        string='Requires Budget Approval',
        default=True,
        help="Transactions require approval"
    )
    expense_approval_limit = fields.Monetary(
        string='Expense Approval Limit',
        currency_field='currency_id',
        help="Maximum expense amount without special approval"
    )
    
    # Financial Statistics
    current_year_income = fields.Monetary(
        string='Current Year Income',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    current_year_expenses = fields.Monetary(
        string='Current Year Expenses',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )
    current_year_net = fields.Monetary(
        string='Current Year Net',
        compute='_compute_financial_stats',
        currency_field='currency_id'
    )

    @api.depends('budget_ids.state', 'budget_ids.start_date', 'budget_ids.end_date')
    def _compute_current_budget(self):
        today = fields.Date.today()
        for chapter in self:
            current_budget = chapter.budget_ids.filtered(
                lambda b: b.state == 'active' and b.start_date <= today <= b.end_date
            )
            chapter.current_budget_id = current_budget[0] if current_budget else False

    @api.depends('transaction_ids.amount', 'transaction_ids.transaction_type', 'transaction_ids.transaction_date')
    def _compute_financial_stats(self):
        current_year = fields.Date.today().year
        for chapter in self:
            year_transactions = chapter.transaction_ids.filtered(
                lambda t: t.transaction_date.year == current_year and t.state == 'approved'
            )
            
            income_transactions = year_transactions.filtered(lambda t: t.transaction_type == 'income')
            expense_transactions = year_transactions.filtered(lambda t: t.transaction_type == 'expense')
            
            chapter.current_year_income = sum(income_transactions.mapped('amount'))
            chapter.current_year_expenses = sum(expense_transactions.mapped('amount'))
            chapter.current_year_net = chapter.current_year_income - chapter.current_year_expenses

    def action_view_budget(self):
        """View chapter budget"""
        self.ensure_one()
        return {
            'name': f"Budget - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.budget',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id)],
            'context': {'default_chapter_id': self.id},
        }

    def action_view_transactions(self):
        """View chapter transactions"""
        self.ensure_one()
        return {
            'name': f"Transactions - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.transaction',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id)],
            'context': {'default_chapter_id': self.id},
        }

    def action_create_budget(self):
        """Create new budget for chapter"""
        self.ensure_one()
        current_year = fields.Date.today().year
        return {
            'name': f"New Budget - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.budget',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_chapter_id': self.id,
                'default_fiscal_year': str(current_year),
                'default_start_date': f"{current_year}-01-01",
                'default_end_date': f"{current_year}-12-31",
            },
        }