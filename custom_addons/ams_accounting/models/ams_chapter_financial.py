from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSChapterFinancial(models.Model):
    """
    Enhanced chapter model with comprehensive financial tracking
    """
    _inherit = 'ams.chapter'
    
    # Financial Configuration
    chapter_account_id = fields.Many2one('account.account', 'Chapter Revenue Account',
        domain="[('account_type', '=', 'income')]",
        help="Revenue account for this chapter's fees")
    
    expense_account_id = fields.Many2one('account.account', 'Chapter Expense Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]",
        help="Default expense account for chapter expenses")
    
    analytic_account_id = fields.Many2one('account.analytic.account', 'Chapter Analytic Account',
        help="Analytic account for tracking chapter finances separately")
    
    # Financial Summary
    total_chapter_revenue = fields.Float('Total Chapter Revenue', compute='_compute_chapter_financials', store=True)
    current_year_revenue = fields.Float('Current Year Revenue', compute='_compute_chapter_financials', store=True)
    last_year_revenue = fields.Float('Last Year Revenue', compute='_compute_chapter_financials', store=True)
    
    total_chapter_expenses = fields.Float('Total Chapter Expenses', compute='_compute_chapter_financials', store=True)
    current_year_expenses = fields.Float('Current Year Expenses', compute='_compute_chapter_financials', store=True)
    
    chapter_net_income = fields.Float('Chapter Net Income', compute='_compute_chapter_financials', store=True)
    chapter_profit_margin = fields.Float('Chapter Profit Margin %', compute='_compute_chapter_financials', store=True)
    
    # Member Financial Analytics
    total_member_fees_collected = fields.Float('Total Member Fees Collected', compute='_compute_member_financials', store=True)
    outstanding_member_fees = fields.Float('Outstanding Member Fees', compute='_compute_member_financials', store=True)
    average_member_value = fields.Float('Average Member Value', compute='_compute_member_financials', store=True)
    
    # Cash Flow
    chapter_cash_inflow = fields.Float('Chapter Cash Inflow', compute='_compute_chapter_cash_flow', store=True)
    chapter_cash_outflow = fields.Float('Chapter Cash Outflow', compute='_compute_chapter_cash_flow', store=True)
    chapter_net_cash_flow = fields.Float('Chapter Net Cash Flow', compute='_compute_chapter_cash_flow', store=True)
    
    # Budget Management
    annual_budget = fields.Float('Annual Budget', default=0.0)
    budget_utilization = fields.Float('Budget Utilization %', compute='_compute_budget_metrics', store=True)
    budget_variance = fields.Float('Budget Variance', compute='_compute_budget_metrics', store=True)
    budget_status = fields.Selection([
        ('under', 'Under Budget'),
        ('on_track', 'On Track'),
        ('over', 'Over Budget'),
        ('critical', 'Critical Overspend')
    ], string='Budget Status', compute='_compute_budget_metrics', store=True)
    
    # Financial Health Indicators
    revenue_growth_rate = fields.Float('Revenue Growth Rate %', compute='_compute_financial_health', store=True)
    member_retention_rate = fields.Float('Member Retention Rate %', compute='_compute_financial_health', store=True)
    collection_efficiency = fields.Float('Collection Efficiency %', compute='_compute_financial_health', store=True)
    
    financial_health_score = fields.Float('Financial Health Score', compute='_compute_financial_health', store=True,
        help="Overall financial health score from 0-100")
    
    # Chapter Allocations
    parent_organization_allocation = fields.Float('Parent Organization Allocation %', default=0.0,
        help="Percentage of revenue allocated to parent organization")
    reserve_fund_allocation = fields.Float('Reserve Fund Allocation %', default=10.0,
        help="Percentage of revenue allocated to reserve fund")
    
    # Banking and Accounts
    chapter_bank_account_id = fields.Many2one('res.partner.bank', 'Chapter Bank Account')
    separate_accounting = fields.Boolean('Separate Accounting', default=False,
        help="Chapter maintains separate books and accounting")
    
    @api.depends('subscription_ids', 'subscription_ids.total_invoiced', 'subscription_ids.total_paid')
    def _compute_chapter_financials(self):
        for chapter in self:
            # Get all revenue from chapter subscriptions
            chapter_subscriptions = chapter.subscription_ids
            
            chapter.total_chapter_revenue = sum(chapter_subscriptions.mapped('total_invoiced'))
            
            # Year-specific calculations
            current_year = fields.Date.today().year
            current_year_start = fields.Date(current_year, 1, 1)
            last_year_start = fields.Date(current_year - 1, 1, 1)
            last_year_end = fields.Date(current_year - 1, 12, 31)
            
            # Current year revenue from chapter subscriptions
            current_year_revenue = 0.0
            last_year_revenue = 0.0
            
            for subscription in chapter_subscriptions:
                # Current year invoices
                current_invoices = subscription.invoice_ids.filtered(
                    lambda inv: inv.invoice_date >= current_year_start and inv.state == 'posted'
                )
                current_year_revenue += sum(current_invoices.mapped('amount_total'))
                
                # Last year invoices
                last_invoices = subscription.invoice_ids.filtered(
                    lambda inv: inv.invoice_date >= last_year_start and 
                               inv.invoice_date <= last_year_end and 
                               inv.state == 'posted'
                )
                last_year_revenue += sum(last_invoices.mapped('amount_total'))
            
            chapter.current_year_revenue = current_year_revenue
            chapter.last_year_revenue = last_year_revenue
            
            # Calculate expenses if analytic account is configured
            if chapter.analytic_account_id:
                expense_lines = self.env['account.move.line'].search([
                    ('analytic_account_id', '=', chapter.analytic_account_id.id),
                    ('account_id.account_type', 'in', ['expense', 'expense_direct_cost', 'expense_depreciation']),
                    ('move_id.state', '=', 'posted')
                ])
                
                chapter.total_chapter_expenses = sum(expense_lines.mapped('debit')) - sum(expense_lines.mapped('credit'))
                
                # Current year expenses
                current_year_expenses = expense_lines.filtered(
                    lambda line: line.date >= current_year_start
                )
                chapter.current_year_expenses = sum(current_year_expenses.mapped('debit')) - sum(current_year_expenses.mapped('credit'))
            else:
                chapter.total_chapter_expenses = 0.0
                chapter.current_year_expenses = 0.0
            
            # Net income and profit margin
            chapter.chapter_net_income = chapter.current_year_revenue - chapter.current_year_expenses
            
            if chapter.current_year_revenue > 0:
                chapter.chapter_profit_margin = (chapter.chapter_net_income / chapter.current_year_revenue) * 100
            else:
                chapter.chapter_profit_margin = 0.0
    
    @api.depends('subscription_ids', 'subscription_ids.amount', 'subscription_ids.outstanding_balance')
    def _compute_member_financials(self):
        for chapter in self:
            chapter_subscriptions = chapter.subscription_ids.filtered(lambda s: s.subscription_code == 'chapter')
            
            chapter.total_member_fees_collected = sum(chapter_subscriptions.mapped('total_paid'))
            chapter.outstanding_member_fees = sum(chapter_subscriptions.mapped('outstanding_balance'))
            
            active_members = len(chapter_subscriptions.filtered(lambda s: s.state == 'active'))
            if active_members > 0:
                chapter.average_member_value = chapter.total_member_fees_collected / active_members
            else:
                chapter.average_member_value = 0.0
    
    @api.depends('analytic_account_id')
    def _compute_chapter_cash_flow(self):
        for chapter in self:
            if not chapter.analytic_account_id:
                chapter.chapter_cash_inflow = 0.0
                chapter.chapter_cash_outflow = 0.0
                chapter.chapter_net_cash_flow = 0.0
                continue
            
            current_year_start = fields.Date.today().replace(month=1, day=1)
            
            # Cash inflow (payments received)
            inflow_lines = self.env['account.move.line'].search([
                ('analytic_account_id', '=', chapter.analytic_account_id.id),
                ('account_id.account_type', 'in', ['asset_cash', 'asset_current']),
                ('debit', '>', 0),
                ('date', '>=', current_year_start),
                ('move_id.state', '=', 'posted')
            ])
            chapter.chapter_cash_inflow = sum(inflow_lines.mapped('debit'))
            
            # Cash outflow (payments made)
            outflow_lines = self.env['account.move.line'].search([
                ('analytic_account_id', '=', chapter.analytic_account_id.id),
                ('account_id.account_type', 'in', ['asset_cash', 'asset_current']),
                ('credit', '>', 0),
                ('date', '>=', current_year_start),
                ('move_id.state', '=', 'posted')
            ])
            chapter.chapter_cash_outflow = sum(outflow_lines.mapped('credit'))
            
            chapter.chapter_net_cash_flow = chapter.chapter_cash_inflow - chapter.chapter_cash_outflow
    
    @api.depends('annual_budget', 'current_year_expenses')
    def _compute_budget_metrics(self):
        for chapter in self:
            if chapter.annual_budget > 0:
                chapter.budget_utilization = (chapter.current_year_expenses / chapter.annual_budget) * 100
                chapter.budget_variance = chapter.annual_budget - chapter.current_year_expenses
                
                # Determine budget status
                if chapter.budget_utilization <= 80:
                    chapter.budget_status = 'under'
                elif chapter.budget_utilization <= 100:
                    chapter.budget_status = 'on_track'
                elif chapter.budget_utilization <= 120:
                    chapter.budget_status = 'over'
                else:
                    chapter.budget_status = 'critical'
            else:
                chapter.budget_utilization = 0.0
                chapter.budget_variance = 0.0
                chapter.budget_status = 'on_track'
    
    @api.depends('current_year_revenue', 'last_year_revenue', 'total_member_fees_collected', 'outstanding_member_fees', 'active_member_count')
    def _compute_financial_health(self):
        for chapter in self:
            # Revenue growth rate
            if chapter.last_year_revenue > 0:
                chapter.revenue_growth_rate = ((chapter.current_year_revenue - chapter.last_year_revenue) / chapter.last_year_revenue) * 100
            else:
                chapter.revenue_growth_rate = 0.0
            
            # Member retention rate (simplified calculation)
            total_members = chapter.member_count
            active_members = chapter.active_member_count
            
            if total_members > 0:
                chapter.member_retention_rate = (active_members / total_members) * 100
            else:
                chapter.member_retention_rate = 100.0
            
            # Collection efficiency
            total_fees = chapter.total_member_fees_collected + chapter.outstanding_member_fees
            if total_fees > 0:
                chapter.collection_efficiency = (chapter.total_member_fees_collected / total_fees) * 100
            else:
                chapter.collection_efficiency = 100.0
            
            # Overall financial health score
            health_components = [
                min(100, max(0, 50 + chapter.revenue_growth_rate)),  # Revenue growth (base 50, +/- growth rate)
                chapter.member_retention_rate,  # Member retention
                chapter.collection_efficiency,  # Collection efficiency
                min(100, max(0, 100 - abs(chapter.budget_utilization - 100))),  # Budget adherence
            ]
            
            chapter.financial_health_score = sum(health_components) / len(health_components)
    
    def action_create_chapter_budget(self):
        """Create annual budget for chapter"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Chapter Budget',
            'res_model': 'ams.chapter.budget.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_chapter_id': self.id,
                'default_budget_year': fields.Date.today().year,
            }
        }
    
    def action_view_chapter_financial_report(self):
        """Generate comprehensive financial report for chapter"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chapter Financial Report',
            'res_model': 'ams.chapter.financial.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_chapter_id': self.id,
            }
        }
    
    def action_view_chapter_analytics(self):
        """View detailed chapter analytics"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Financial Analytics',
            'res_model': 'account.move.line',
            'view_mode': 'pivot,graph,tree',
            'domain': [
                ('analytic_account_id', '=', self.analytic_account_id.id if self.analytic_account_id else False),
                ('move_id.state', '=', 'posted')
            ],
            'context': {
                'group_by': ['account_id', 'date:month'],
                'search_default_group_by_account': 1,
            }
        }
    
    def action_view_member_payments(self):
        """View all member payments for this chapter"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Member Payments',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_id', 'in', self.subscription_ids.mapped('partner_id').ids),
                ('state', '=', 'posted')
            ],
            'context': {
                'search_default_group_by_partner': 1,
            }
        }
    
    def create_analytic_account(self):
        """Create analytic account for chapter if not exists"""
        if self.analytic_account_id:
            return self.analytic_account_id
        
        analytic_vals = {
            'name': f'Chapter: {self.name}',
            'code': self.code,
            'partner_id': False,  # Chapter is not a partner
            'company_id': self.env.company.id,
        }
        
        self.analytic_account_id = self.env['account.analytic.account'].create(analytic_vals)
        return self.analytic_account_id
    
    def process_parent_allocation(self):
        """Process allocation to parent organization"""
        if not self.parent_organization_allocation or self.parent_organization_allocation <= 0:
            return
        
        allocation_amount = (self.current_year_revenue * self.parent_organization_allocation) / 100
        
        if allocation_amount <= 0:
            return
        
        # Create journal entry for allocation
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            raise UserError(_('No general journal found for allocation entry.'))
        
        # Parent organization account (could be configurable)
        parent_account = self.env['account.account'].search([
            ('code', '=', 'PARENT_ALLOC'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not parent_account:
            parent_account = self.env.company.transfer_account_id
        
        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'Parent Allocation - {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Allocation to Parent - {self.name}',
                    'account_id': self.chapter_account_id.id if self.chapter_account_id else self.env.company.income_currency_exchange_account_id.id,
                    'debit': allocation_amount,
                    'credit': 0.0,
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                }),
                (0, 0, {
                    'name': f'Allocation to Parent - {self.name}',
                    'account_id': parent_account.id,
                    'debit': 0.0,
                    'credit': allocation_amount,
                })
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move
    
    def get_chapter_financial_dashboard_data(self):
        """Get financial dashboard data for chapter"""
        return {
            'financial_summary': {
                'total_revenue': self.total_chapter_revenue,
                'current_year_revenue': self.current_year_revenue,
                'last_year_revenue': self.last_year_revenue,
                'total_expenses': self.total_chapter_expenses,
                'net_income': self.chapter_net_income,
                'profit_margin': self.chapter_profit_margin,
            },
            'member_metrics': {
                'active_members': self.active_member_count,
                'total_members': self.member_count,
                'fees_collected': self.total_member_fees_collected,
                'outstanding_fees': self.outstanding_member_fees,
                'average_member_value': self.average_member_value,
            },
            'cash_flow': {
                'inflow': self.chapter_cash_inflow,
                'outflow': self.chapter_cash_outflow,
                'net_flow': self.chapter_net_cash_flow,
            },
            'budget_metrics': {
                'annual_budget': self.annual_budget,
                'utilization': self.budget_utilization,
                'variance': self.budget_variance,
                'status': self.budget_status,
            },
            'health_indicators': {
                'revenue_growth': self.revenue_growth_rate,
                'retention_rate': self.member_retention_rate,
                'collection_efficiency': self.collection_efficiency,
                'health_score': self.financial_health_score,
            }
        }
    
    @api.model
    def get_chapters_financial_summary(self):
        """Get financial summary for all chapters"""
        chapters = self.search([('active', '=', True)])
        
        summary = {
            'total_chapters': len(chapters),
            'total_revenue': sum(chapters.mapped('current_year_revenue')),
            'total_members': sum(chapters.mapped('active_member_count')),
            'total_outstanding': sum(chapters.mapped('outstanding_member_fees')),
            'average_health_score': sum(chapters.mapped('financial_health_score')) / len(chapters) if chapters else 0,
            'chapters_over_budget': len(chapters.filtered(lambda c: c.budget_status in ['over', 'critical'])),
            'top_performing_chapters': chapters.sorted('financial_health_score', reverse=True)[:5].mapped('name'),
            'chapters_need_attention': chapters.filtered(lambda c: c.financial_health_score < 60).mapped('name'),
        }
        
        return summary


class AMSChapterBudget(models.Model):
    """
    Budget model for chapters
    """
    _name = 'ams.chapter.budget'
    _description = 'AMS Chapter Budget'
    _order = 'budget_year desc, chapter_id'
    
    chapter_id = fields.Many2one('ams.chapter', 'Chapter', required=True)
    budget_year = fields.Integer('Budget Year', required=True, default=lambda self: fields.Date.today().year)
    
    # Revenue Budget
    membership_revenue_budget = fields.Float('Membership Revenue Budget')
    chapter_fee_revenue_budget = fields.Float('Chapter Fee Revenue Budget')
    event_revenue_budget = fields.Float('Event Revenue Budget')
    other_revenue_budget = fields.Float('Other Revenue Budget')
    total_revenue_budget = fields.Float('Total Revenue Budget', compute='_compute_totals', store=True)
    
    # Expense Budget
    administrative_expense_budget = fields.Float('Administrative Expenses Budget')
    program_expense_budget = fields.Float('Program Expenses Budget')
    marketing_expense_budget = fields.Float('Marketing Expenses Budget')
    other_expense_budget = fields.Float('Other Expenses Budget')
    total_expense_budget = fields.Float('Total Expense Budget', compute='_compute_totals', store=True)
    
    # Net Budget
    net_budget = fields.Float('Net Budget', compute='_compute_totals', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], string='Status', default='draft')
    
    notes = fields.Text('Notes')
    
    @api.depends('membership_revenue_budget', 'chapter_fee_revenue_budget', 'event_revenue_budget', 'other_revenue_budget',
                 'administrative_expense_budget', 'program_expense_budget', 'marketing_expense_budget', 'other_expense_budget')
    def _compute_totals(self):
        for budget in self:
            budget.total_revenue_budget = (
                budget.membership_revenue_budget + 
                budget.chapter_fee_revenue_budget + 
                budget.event_revenue_budget + 
                budget.other_revenue_budget
            )
            
            budget.total_expense_budget = (
                budget.administrative_expense_budget + 
                budget.program_expense_budget + 
                budget.marketing_expense_budget + 
                budget.other_expense_budget
            )
            
            budget.net_budget = budget.total_revenue_budget - budget.total_expense_budget
    
    def action_approve_budget(self):
        """Approve the budget"""
        self.state = 'approved'
        
        # Update chapter's annual budget
        self.chapter_id.annual_budget = self.total_expense_budget
    
    def action_activate_budget(self):
        """Activate the budget for the year"""
        self.state = 'active'
        
        # Deactivate other budgets for the same chapter and year
        other_budgets = self.search([
            ('chapter_id', '=', self.chapter_id.id),
            ('budget_year', '=', self.budget_year),
            ('id', '!=', self.id)
        ])
        other_budgets.write({'state': 'closed'})
    
    _sql_constraints = [
        ('unique_chapter_year', 'unique(chapter_id, budget_year, state)', 
         'Only one active budget per chapter per year is allowed!'),
    ]