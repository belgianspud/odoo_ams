from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
import logging

class AmsFinancialSummary(models.Model):
    """
    Provide financial summary views for associations.
    This creates aggregated financial data for reporting.
    """
    _name = 'ams.financial.summary'
    _description = 'AMS Financial Summary'
    _auto = False  # This is a view, not a real table

    # Period information
    period_year = fields.Integer(string='Year')
    period_month = fields.Integer(string='Month')
    period_quarter = fields.Integer(string='Quarter')
    
    # Revenue breakdown
    membership_revenue = fields.Monetary(string='Membership Revenue', currency_field='currency_id')
    event_revenue = fields.Monetary(string='Event Revenue', currency_field='currency_id')
    donation_revenue = fields.Monetary(string='Donation Revenue', currency_field='currency_id')
    other_revenue = fields.Monetary(string='Other Revenue', currency_field='currency_id')
    total_revenue = fields.Monetary(string='Total Revenue', currency_field='currency_id')
    
    # Expense breakdown
    program_expenses = fields.Monetary(string='Program Expenses', currency_field='currency_id')
    admin_expenses = fields.Monetary(string='Administrative Expenses', currency_field='currency_id')
    total_expenses = fields.Monetary(string='Total Expenses', currency_field='currency_id')
    
    # Net income
    net_income = fields.Monetary(string='Net Income', currency_field='currency_id')
    
    # Chapter breakdown
    chapter_id = fields.Many2one('res.partner', string='Chapter')
    currency_id = fields.Many2one('res.currency')
    
    def init(self):
        """Create the SQL view for financial summaries"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Create a simplified view that doesn't depend on subscription-specific fields
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT 
                    row_number() OVER () AS id,
                    EXTRACT(year FROM am.invoice_date) as period_year,
                    EXTRACT(month FROM am.invoice_date) as period_month,
                    EXTRACT(quarter FROM am.invoice_date) as period_quarter,
                    
                    -- Basic revenue categorization without subscription dependencies
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        AND EXISTS (
                            SELECT 1 FROM ams_revenue_category arc 
                            WHERE arc.category_type = 'membership'
                        )
                        THEN aml.credit 
                        ELSE 0 
                    END) as membership_revenue,
                    
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        AND EXISTS (
                            SELECT 1 FROM ams_revenue_category arc 
                            WHERE arc.category_type = 'event'
                        )
                        THEN aml.credit 
                        ELSE 0 
                    END) as event_revenue,
                    
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        AND EXISTS (
                            SELECT 1 FROM ams_revenue_category arc 
                            WHERE arc.category_type = 'donation'
                        )
                        THEN aml.credit 
                        ELSE 0 
                    END) as donation_revenue,
                    
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        THEN aml.credit 
                        ELSE 0 
                    END) as other_revenue,
                    
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        THEN aml.credit 
                        ELSE 0 
                    END) as total_revenue,
                    
                    SUM(CASE 
                        WHEN am.move_type = 'in_invoice' 
                        THEN aml.debit 
                        ELSE 0 
                    END) as total_expenses,
                    
                    0 as program_expenses,  -- Will be enhanced later
                    0 as admin_expenses,    -- Will be enhanced later
                    
                    SUM(CASE 
                        WHEN am.move_type = 'out_invoice' 
                        THEN aml.credit 
                        WHEN am.move_type = 'in_invoice' 
                        THEN -aml.debit 
                        ELSE 0 
                    END) as net_income,
                    
                    am.partner_id as chapter_id,
                    rc.id as currency_id
                    
                FROM account_move am
                JOIN account_move_line aml ON am.id = aml.move_id
                JOIN res_company rc ON rc.id = am.company_id
                WHERE am.state = 'posted'
                    AND am.move_type IN ('out_invoice', 'in_invoice')
                    AND aml.account_id IS NOT NULL
                GROUP BY 
                    EXTRACT(year FROM am.invoice_date),
                    EXTRACT(month FROM am.invoice_date),
                    EXTRACT(quarter FROM am.invoice_date),
                    am.partner_id,
                    rc.id
                HAVING SUM(CASE 
                    WHEN am.move_type = 'out_invoice' THEN aml.credit 
                    WHEN am.move_type = 'in_invoice' THEN aml.debit 
                    ELSE 0 
                END) > 0
            )
        """)