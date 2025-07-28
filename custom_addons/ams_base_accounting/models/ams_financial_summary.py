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
        
        # This creates a basic view structure
        # You'll enhance this as you add more transaction tracking
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT 
                    row_number() OVER () AS id,
                    EXTRACT(year FROM am.invoice_date) as period_year,
                    EXTRACT(month FROM am.invoice_date) as period_month,
                    EXTRACT(quarter FROM am.invoice_date) as period_quarter,
                    
                    -- Revenue by category (will be enhanced with actual categorization)
                    SUM(CASE WHEN am.move_type = 'out_invoice' 
                        AND aml.product_id IN (
                            SELECT id FROM product_product pp 
                            -- WHERE pp.is_membership = true
                        ) 
                        THEN aml.credit ELSE 0 END) as membership_revenue,
                        
                    SUM(CASE WHEN am.move_type = 'out_invoice' 
                        AND aml.product_id IN (
                            SELECT DISTINCT product_id FROM event_registration
                        ) 
                        THEN aml.credit ELSE 0 END) as event_revenue,
                        
                    SUM(CASE WHEN am.move_type = 'out_invoice' 
                        AND aml.product_id NOT IN (
                            SELECT id FROM product_product pp WHERE pp.is_membership = true
                        )
                        AND aml.product_id NOT IN (
                            SELECT DISTINCT product_id FROM event_registration
                        )
                        THEN aml.credit ELSE 0 END) as other_revenue,
                        
                    0 as donation_revenue,  -- Will be enhanced with donation tracking
                    
                    SUM(CASE WHEN am.move_type = 'out_invoice' 
                        THEN aml.credit ELSE 0 END) as total_revenue,
                        
                    SUM(CASE WHEN am.move_type = 'in_invoice' 
                        THEN aml.debit ELSE 0 END) as total_expenses,
                        
                    0 as program_expenses,  -- Will be categorized later
                    0 as admin_expenses,    -- Will be categorized later
                    
                    SUM(CASE WHEN am.move_type = 'out_invoice' 
                        THEN aml.credit 
                        WHEN am.move_type = 'in_invoice' 
                        THEN -aml.debit 
                        ELSE 0 END) as net_income,
                        
                    am.partner_id as chapter_id,
                    rc.id as currency_id
                    
                FROM account_move am
                JOIN account_move_line aml ON am.id = aml.move_id
                JOIN res_company rc ON rc.id = am.company_id
                WHERE am.state = 'posted'
                    AND am.move_type IN ('out_invoice', 'in_invoice')
                GROUP BY 
                    EXTRACT(year FROM am.invoice_date),
                    EXTRACT(month FROM am.invoice_date),
                    EXTRACT(quarter FROM am.invoice_date),
                    am.partner_id,
                    rc.id
            )
        """)
