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