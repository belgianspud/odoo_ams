{
    'name': 'AMS Accounting',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Basic accounting module for Association Management System',
    'description': """
        AMS Accounting Module
        =====================
        
        Basic accounting functionality for Association Management System (AMS).
        
        Features:
        - Chart of accounts management
        - Product-to-account mapping for subscriptions
        - Integration with Odoo native accounting
        - Subscription revenue tracking
        - Contact-based financial reporting
        - Automated account entries for subscription products
        - Financial dashboards and reports
        
        Integration:
        - Links to ams_subscriptions for subscription revenue tracking
        - Extends Odoo's native accounting functionality
        - Partner financial summaries
        - Product-based account automation
    """,
    'author': 'AMS Development Team',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',  # Odoo native accounting
        'sale',
        'product',
        'contacts',
        'ams_subscriptions',  # Our subscription module - MUST be installed first
    ],
    'data': [
        # Security - MUST be first
        'security/ir.model.access.csv',
        
        # Data files
        'data/account_chart_data.xml',
        #'data/product_account_mapping_data.xml',
        
        # Views - ORDER MATTERS!
        'views/account_chart_views.xml',
        'views/product_account_mapping_views.xml', 
        'views/partner_accounting_views.xml',
        'views/subscription_accounting_views.xml',
        'views/accounting_dashboard_views.xml',
        'views/menu_views.xml',  # Menu views should be LAST
        
        # Reports
        'reports/subscription_revenue_report.xml',
        'reports/partner_financial_report.xml',
    ],
    'installable': True,
    'application': True,   # KEEP AS TRUE - this is correct!
    'auto_install': False,
    'sequence': 130,  # Load after accounting and ams_subscriptions
    'external_dependencies': {
        'python': [],
    },
}