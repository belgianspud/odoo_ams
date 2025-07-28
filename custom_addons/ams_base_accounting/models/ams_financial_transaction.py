# ==============================================================================
# AMS Base Accounting Module for Odoo Community 18.0.1
# This module provides association-specific accounting functionality
# that works within Community edition constraints
# ==============================================================================

# __manifest__.py
{
    'name': 'AMS Base Accounting',
    'version': '18.0.1.0.0',
    'category': 'Association Management/Accounting',
    'summary': 'Base accounting module for Association Management System',
    'description': '''
        Base Accounting Module for Associations - Community Edition
        
        This module extends Odoo Community's Invoicing capabilities to provide
        association-specific accounting functionality:
        
        Features:
        - Association-specific account structure
        - Revenue tracking by category (membership, events, donations)
        - Chapter/regional financial tracking
        - Basic financial reporting for associations
        - Integration hooks for AMS modules
        - Easily extensible architecture
        
        Designed to work within Odoo Community constraints while providing
        essential accounting features for membership organizations.
    ''',
    'author': 'Your Organization',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'depends': [
        'base',
        'account',  # Invoicing app in Community
        'sale',
        'product',
        'contacts',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/ams_accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Data - Account structure
        'data/account_account_data.xml',
        'data/account_journal_data.xml',
        'data/product_category_data.xml',
        'data/revenue_category_data.xml',
        
        # Views
        'views/ams_account_views.xml',
        'views/ams_revenue_category_views.xml',
        'views/ams_financial_summary_views.xml',
        'views/ams_transaction_views.xml',
        'views/partner_views.xml',
        'views/invoice_views.xml',
        'views/menu_views.xml',
        
        # Reports
        'reports/financial_summary_report.xml',
        'reports/revenue_analysis_report.xml',
        'reports/member_financial_report.xml',
        
        # Wizards
        'wizards/financial_period_close_views.xml',
        'wizards/revenue_allocation_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_base_accounting/static/src/css/financial_dashboard.css',
            'ams_base_accounting/static/src/js/financial_widgets.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,  # Base module, not standalone app
    'license': 'LGPL-3',
}

# ==============================================================================
# MODELS
# ==============================================================================

# models/ams_revenue_category.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AmsRevenueCategory(models.Model):
    """
    Define revenue categories for association financial tracking.
    This allows categorizing income by source for better reporting.
    """
    _name = 'ams.revenue.category'
    _description = 'AMS Revenue Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code', required=True, size=10)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    
    # Account mapping
    income_account_id = fields.Many2one(
        'account.account', 
        string='Income Account',
        domain=[('account_type', '=', 'income')]
    )
    
    # Category type
    category_type = fields.Selection([
        ('membership', 'Membership Revenue'),
        ('event', 'Event Revenue'),
        ('donation', 'Donations'),
        ('sponsorship', 'Sponsorships'),
        ('merchandise', 'Merchandise Sales'),
        ('training', 'Training/Education'),
        ('certification', 'Certification Fees'),
        ('other', 'Other Revenue')
    ], string='Category Type', required=True)
    
    # Financial tracking
    budget_amount = fields.Monetary(string='Annual Budget', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Statistics
    current_year_revenue = fields.Monetary(
        string='Current Year Revenue', 
        compute='_compute_revenue_stats',
        currency_field='currency_id'
    )
    transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_revenue_stats'
    )
    
    @api.depends('name')
    def _compute_revenue_stats(self):
        """Compute revenue statistics for the current year"""
        current_year = fields.Date.today().year
        for category in self:
            # This will be populated by actual transactions
            # For now, set to 0 - will be enhanced when transactions are tracked
            category.current_year_revenue = 0.0
            category.transaction_count = 0
    
    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Revenue category code '{record.code}' must be unique!")

# models/ams_account_extension.py
class AmsAccountExtension(models.Model):
    """
    Extend account.account to add association-specific features
    """
    _inherit = 'account.account'
    
    # Association-specific fields
    is_ams_account = fields.Boolean(string='AMS Account', default=False)
    ams_account_type = fields.Selection([
        ('membership_revenue', 'Membership Revenue'),
        ('event_revenue', 'Event Revenue'),
        ('donation_revenue', 'Donation Revenue'),
        ('operational_expense', 'Operational Expense'),
        ('program_expense', 'Program Expense'),
        ('administrative_expense', 'Administrative Expense'),
        ('member_receivable', 'Member Receivables'),
        ('event_receivable', 'Event Receivables'),
        ('deferred_revenue', 'Deferred Revenue'),
    ], string='AMS Account Type')
    
    revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='Revenue Category'
    )

# models/ams_financial_transaction.py
class AmsFinancialTransaction(models.Model):
    """
    Track financial transactions for association reporting.
    This provides a simplified transaction log that works within Community constraints.
    """
    _name = 'ams.financial.transaction'
    _description = 'AMS Financial Transaction'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    # Basic transaction info
    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Transaction Date', required=True, default=fields.Date.today)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Transaction categorization
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
    ], string='Transaction Type', required=True)
    
    revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='Revenue Category'
    )
    
    # Related records
    partner_id = fields.Many2one('res.partner', string='Contact')
    invoice_id = fields.Many2one('account.move', string='Related Invoice')
    
    # Chapter/regional tracking
    chapter_id = fields.Many2one('res.partner', string='Chapter',
                                domain=[('is_company', '=', True)])
    
    # Status and notes
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('reconciled', 'Reconciled'),
    ], string='Status', default='draft')
    
    notes = fields.Text(string='Notes')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    
    @api.depends('name', 'date', 'amount', 'partner_id')
    def _compute_display_name(self):
        for transaction in self:
            partner_name = transaction.partner_id.name if transaction.partner_id else 'N/A'
            transaction.display_name = f"{transaction.date} - {transaction.name} - {partner_name} - {transaction.amount}"
