from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

class AMSFinancialDashboard(models.Model):
    """
    AMS-specific financial dashboard with subscription analytics
    """
    _name = 'ams.financial.dashboard'
    _description = 'AMS Financial Dashboard'
    _rec_name = 'name'
    
    name = fields.Char('Dashboard Name', required=True, default='AMS Financial Dashboard')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True)
    
    # Date Ranges
    date_from = fields.Date('From Date', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To Date', default=fields.Date.today)
    
    # Financial Summary
    total_revenue = fields.Float('Total Revenue', compute='_compute_financial_summary')
    subscription_revenue = fields.Float('Subscription Revenue', compute='_compute_financial_summary')
    chapter_revenue = fields.Float('Chapter Revenue', compute='_compute_financial_summary')
    renewal_revenue = fields.Float('Renewal Revenue', compute='_compute_financial_summary')
    other_revenue = fields.Float('Other Revenue', compute='_compute_financial_summary')
    
    total_expenses = fields.Float('Total Expenses', compute='_compute_financial_summary')
    net_income = fields.Float('Net Income', compute='_compute_financial_summary')
    
    # Subscription Analytics
    active_subscriptions = fields.Integer('Active Subscriptions', compute='_compute_subscription_analytics')
    new_subscriptions_mtd = fields.Integer('New Subscriptions MTD', compute='_compute_subscription_analytics')
    renewal_rate = fields.Float('Renewal Rate %', compute='_compute_subscription_analytics')
    churn_rate = fields.Float('Churn Rate %', compute='_compute_subscription_analytics')
    
    # Member Analytics
    total_members = fields.Integer('Total Members', compute='_compute_member_analytics')
    active_members = fields.Integer('Active Members', compute='_compute_member_analytics')
    new_members_mtd = fields.Integer('New Members MTD', compute='_compute_member_analytics')
    
    # Cash Flow
    cash_inflow = fields.Float('Cash Inflow', compute='_compute_cash_flow')
    cash_outflow = fields.Float('Cash Outflow', compute='_compute_cash_flow')
    net_cash_flow = fields.Float('Net Cash Flow', compute='_compute_cash_flow')
    
    # Receivables
    total_receivables = fields.Float('Total Receivables', compute='_compute_receivables')
    overdue_receivables = fields.Float('Overdue Receivables', compute='_compute_receivables')
    
    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_financial_summary(self):
        for dashboard in self:
            domain = [
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('company_id', '=', dashboard.company_id.id),
                ('state', '=', 'posted')
            ]
            
            # Revenue calculation
            revenue_lines = self.env['account.move.line'].search(domain + [
                ('account_id.account_type', '=', 'income')
            ])
            
            dashboard.total_revenue = sum(revenue_lines.mapped('credit')) - sum(revenue_lines.mapped('debit'))
            
            # Subscription-specific revenue
            subscription_lines = revenue_lines.filtered(lambda l: l.move_id.is_ams_subscription_invoice)
            dashboard.subscription_revenue = sum(subscription_lines.mapped('credit')) - sum(subscription_lines.mapped('debit'))
            
            # Chapter revenue
            chapter_lines = revenue_lines.filtered(lambda l: l.move_id.ams_chapter_id)
            dashboard.chapter_revenue = sum(chapter_lines.mapped('credit')) - sum(chapter_lines.mapped('debit'))
            
            # Renewal revenue
            renewal_lines = revenue_lines.filtered(lambda l: l.move_id.is_ams_renewal_invoice)
            dashboard.renewal_revenue = sum(renewal_lines.mapped('credit')) - sum(renewal_lines.mapped('debit'))
            
            # Other revenue
            dashboard.other_revenue = dashboard.total_revenue - dashboard.subscription_revenue - dashboard.chapter_revenue - dashboard.renewal_revenue
            
            # Expenses calculation
            expense_lines = self.env['account.move.line'].search(domain + [
                ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])
            ])
            
            dashboard.total_expenses = sum(expense_lines.mapped('debit')) - sum(expense_lines.mapped('credit'))
            
            # Net income
            dashboard.net_income = dashboard.total_revenue - dashboard.total_expenses
    
    @api.depends('date_from', 'date_to')
    def _compute_subscription_analytics(self):
        for dashboard in self:
            # Active subscriptions
            dashboard.active_subscriptions = self.env['ams.subscription'].search_count([
                ('state', '=', 'active')
            ])
            
            # New subscriptions this month
            month_start = dashboard.date_from.replace(day=1)
            dashboard.new_subscriptions_mtd = self.env['ams.subscription'].search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', dashboard.date_to),
                ('state', '=', 'active')
            ])
            
            # Renewal rate calculation
            last_month = dashboard.date_from - relativedelta(months=1)
            last_month_start = last_month.replace(day=1)
            last_month_end = (last_month_start + relativedelta(months=1)) - timedelta(days=1)
            
            expired_last_month = self.env['ams.subscription'].search_count([
                ('end_date', '>=', last_month_start),
                ('end_date', '<=', last_month_end),
                ('is_recurring', '=', True)
            ])
            
            renewed_from_last_month = self.env['ams.subscription'].search_count([
                ('end_date', '>=', last_month_start),
                ('end_date', '<=', last_month_end),
                ('is_recurring', '=', True),
                ('state', '=', 'active')
            ])
            
            dashboard.renewal_rate = (renewed_from_last_month / expired_last_month * 100) if expired_last_month > 0 else 0.0
            dashboard.churn_rate = 100 - dashboard.renewal_rate
    
    @api.depends('date_from', 'date_to')
    def _compute_member_analytics(self):
        for dashboard in self:
            # Total members (partners with subscriptions)
            dashboard.total_members = self.env['res.partner'].search_count([
                ('total_subscription_count', '>', 0)
            ])
            
            # Active members
            dashboard.active_members = self.env['res.partner'].search_count([
                ('active_subscription_count', '>', 0)
            ])
            
            # New members this month
            month_start = dashboard.date_from.replace(day=1)
            new_subscription_partners = self.env['ams.subscription'].search([
                ('create_date', '>=', month_start),
                ('create_date', '<=', dashboard.date_to),
                ('subscription_code', '=', 'membership')
            ]).mapped('partner_id')
            
            dashboard.new_members_mtd = len(new_subscription_partners)
    
    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_cash_flow(self):
        for dashboard in self:
            domain = [
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('company_id', '=', dashboard.company_id.id),
                ('state', '=', 'posted')
            ]
            
            # Cash inflow (payments received)
            inflow_lines = self.env['account.move.line'].search(domain + [
                ('account_id.account_type', 'in', ['asset_cash', 'asset_current']),
                ('debit', '>', 0)
            ])
            dashboard.cash_inflow = sum(inflow_lines.mapped('debit'))
            
            # Cash outflow (payments made)
            outflow_lines = self.env['account.move.line'].search(domain + [
                ('account_id.account_type', 'in', ['asset_cash', 'asset_current']),
                ('credit', '>', 0)
            ])
            dashboard.cash_outflow = sum(outflow_lines.mapped('credit'))
            
            # Net cash flow
            dashboard.net_cash_flow = dashboard.cash_inflow - dashboard.cash_outflow
    
    @api.depends('company_id')
    def _compute_receivables(self):
        for dashboard in self:
            today = fields.Date.today()
            
            # Total receivables
            receivable_moves = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('company_id', '=', dashboard.company_id.id)
            ])
            
            dashboard.total_receivables = sum(receivable_moves.mapped('amount_residual'))
            
            # Overdue receivables
            overdue_moves = receivable_moves.filtered(
                lambda m: m.invoice_date_due and m.invoice_date_due < today
            )
            dashboard.overdue_receivables = sum(overdue_moves.mapped('amount_residual'))
    
    def get_subscription_revenue_chart_data(self):
        """Get chart data for subscription revenue trends"""
        self.ensure_one()
        
        # Get monthly subscription revenue for the last 12 months
        start_date = self.date_from - relativedelta(months=11)
        
        data = []
        labels = []
        
        for i in range(12):
            month_start = start_date + relativedelta(months=i)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            revenue_lines = self.env['account.move.line'].search([
                ('date', '>=', month_start),
                ('date', '<=', month_end),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'posted'),
                ('account_id.account_type', '=', 'income'),
                ('move_id.is_ams_subscription_invoice', '=', True)
            ])
            
            monthly_revenue = sum(revenue_lines.mapped('credit')) - sum(revenue_lines.mapped('debit'))
            
            data.append(monthly_revenue)
            labels.append(month_start.strftime('%b %Y'))
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Subscription Revenue',
                'data': data,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 2,
                'fill': True
            }]
        }
    
    def get_member_growth_chart_data(self):
        """Get chart data for member growth trends"""
        self.ensure_one()
        
        # Get monthly member growth for the last 12 months
        start_date = self.date_from - relativedelta(months=11)
        
        data = []
        labels = []
        cumulative_members = 0
        
        for i in range(12):
            month_start = start_date + relativedelta(months=i)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            new_members = self.env['ams.subscription'].search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end),
                ('subscription_code', '=', 'membership'),
                ('state', '=', 'active')
            ])
            
            cumulative_members += new_members
            
            data.append(cumulative_members)
            labels.append(month_start.strftime('%b %Y'))
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Total Active Members',
                'data': data,
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 2,
                'fill': True
            }]
        }
    
    def get_revenue_breakdown_data(self):
        """Get pie chart data for revenue breakdown"""
        self.ensure_one()
        
        return {
            'labels': ['Subscription Revenue', 'Chapter Revenue', 'Renewal Revenue', 'Other Revenue'],
            'datasets': [{
                'data': [
                    self.subscription_revenue,
                    self.chapter_revenue,
                    self.renewal_revenue,
                    self.other_revenue
                ],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)'
                ]
            }]
        }
    
    def action_refresh_dashboard(self):
        """Refresh dashboard calculations"""
        self._compute_financial_summary()
        self._compute_subscription_analytics()
        self._compute_member_analytics()
        self._compute_cash_flow()
        self._compute_receivables()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_view_subscription_revenue_details(self):
        """View detailed subscription revenue transactions"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscription Revenue Details',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'posted'),
                ('account_id.account_type', '=', 'income'),
                ('move_id.is_ams_subscription_invoice', '=', True)
            ],
            'context': {
                'search_default_group_by_account': 1,
            }
        }
    
    def action_view_overdue_receivables(self):
        """View overdue receivables"""
        today = fields.Date.today()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Overdue Receivables',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('company_id', '=', self.company_id.id),
                ('invoice_date_due', '<', today)
            ],
            'context': {
                'search_default_group_by_partner': 1,
            }
        }
    
    @api.model
    def get_dashboard_data(self, company_id=None):
        """Get dashboard data for API/web calls"""
        if not company_id:
            company_id = self.env.company.id
        
        dashboard = self.search([('company_id', '=', company_id)], limit=1)
        if not dashboard:
            dashboard = self.create({
                'company_id': company_id,
                'name': f'Dashboard - {self.env.company.name}'
            })
        
        return {
            'financial_summary': {
                'total_revenue': dashboard.total_revenue,
                'subscription_revenue': dashboard.subscription_revenue,
                'chapter_revenue': dashboard.chapter_revenue,
                'renewal_revenue': dashboard.renewal_revenue,
                'total_expenses': dashboard.total_expenses,
                'net_income': dashboard.net_income,
            },
            'subscription_analytics': {
                'active_subscriptions': dashboard.active_subscriptions,
                'new_subscriptions_mtd': dashboard.new_subscriptions_mtd,
                'renewal_rate': dashboard.renewal_rate,
                'churn_rate': dashboard.churn_rate,
            },
            'member_analytics': {
                'total_members': dashboard.total_members,
                'active_members': dashboard.active_members,
                'new_members_mtd': dashboard.new_members_mtd,
            },
            'cash_flow': {
                'cash_inflow': dashboard.cash_inflow,
                'cash_outflow': dashboard.cash_outflow,
                'net_cash_flow': dashboard.net_cash_flow,
            },
            'receivables': {
                'total_receivables': dashboard.total_receivables,
                'overdue_receivables': dashboard.overdue_receivables,
            },
            'charts': {
                'subscription_revenue': dashboard.get_subscription_revenue_chart_data(),
                'member_growth': dashboard.get_member_growth_chart_data(),
                'revenue_breakdown': dashboard.get_revenue_breakdown_data(),
            }
        }