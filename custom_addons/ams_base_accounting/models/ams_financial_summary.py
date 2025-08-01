# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from dateutil.relativedelta import relativedelta

class AMSFinancialSummary(models.Model):
    _name = 'ams.financial.summary'
    _description = 'AMS Financial Summary'
    _auto = False  # This is a view model for reporting
    
    # Date fields
    date = fields.Date(string='Date')
    month = fields.Char(string='Month')
    year = fields.Integer(string='Year')
    
    # Financial data
    revenue_category_id = fields.Many2one('ams.revenue.category', string='Revenue Category')
    total_amount = fields.Float(string='Total Amount')
    transaction_count = fields.Integer(string='Transaction Count')
    
    # Partner info
    partner_id = fields.Many2one('res.partner', string='Contact/Account')
    
    def init(self):
        """Create the SQL view for financial summary reporting"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    t.date,
                    to_char(t.date, 'YYYY-MM') AS month,
                    EXTRACT(year FROM t.date) AS year,
                    t.revenue_category_id,
                    t.partner_id,
                    SUM(t.amount) AS total_amount,
                    COUNT(*) AS transaction_count
                FROM ams_financial_transaction t
                WHERE t.is_revenue = true
                GROUP BY
                    t.date,
                    to_char(t.date, 'YYYY-MM'),
                    EXTRACT(year FROM t.date),
                    t.revenue_category_id,
                    t.partner_id
            )
        """)

class AMSFinancialDashboard(models.TransientModel):
    _name = 'ams.financial.dashboard'
    _description = 'AMS Financial Dashboard'
    
    # Date range for dashboard
    date_from = fields.Date(
        string='From Date',
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='To Date',
        default=fields.Date.today
    )
    
    # Summary data
    total_revenue = fields.Float(
        string='Total Revenue',
        compute='_compute_summary_data'
    )
    membership_revenue = fields.Float(
        string='Membership Revenue',
        compute='_compute_summary_data'
    )
    event_revenue = fields.Float(
        string='Event Revenue',
        compute='_compute_summary_data'
    )
    other_revenue = fields.Float(
        string='Other Revenue',
        compute='_compute_summary_data'
    )
    
    @api.depends('date_from', 'date_to')
    def _compute_summary_data(self):
        for dashboard in self:
            domain = [
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('is_revenue', '=', True)
            ]
            
            transactions = self.env['ams.financial.transaction'].search(domain)
            
            dashboard.total_revenue = sum(transactions.mapped('amount'))
            dashboard.membership_revenue = sum(
                transactions.filtered(
                    lambda t: t.revenue_category_id.revenue_type == 'membership'
                ).mapped('amount')
            )
            dashboard.event_revenue = sum(
                transactions.filtered(
                    lambda t: t.revenue_category_id.revenue_type == 'event'
                ).mapped('amount')
            )
            dashboard.other_revenue = dashboard.total_revenue - dashboard.membership_revenue - dashboard.event_revenue