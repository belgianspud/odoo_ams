{
    'name': 'AMS Accounting',  # ← Remove "Base" - it's the main app
    'version': '18.0.1.0.1',
    'category': 'Association Management',
    'summary': 'Financial Management for Association Management System',
    'description': '''
        AMS Accounting - Financial Management for Associations
        ====================================================
        
        Complete financial management solution for associations including:
        
        Revenue Management:
        - Revenue categorization by membership type
        - Chapter financial performance tracking
        - Event and training revenue analysis
        - Donation and sponsorship tracking
        
        Financial Analytics:
        - Member lifetime value analysis
        - Revenue forecasting and trends
        - Budget planning and variance analysis
        - Board-ready financial reports
        
        Integration Features:
        - Seamless integration with AMS Subscriptions
        - Automatic transaction creation from memberships
        - Real-time financial dashboard
        - Export capabilities for external accounting
        
        Designed specifically for association needs while working
        within Odoo Community Edition constraints.
    ''',
    'author': 'Your Organization',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'depends': [
        'base',
        'account',      # Community Invoicing
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
        
        # Master data
        'data/revenue_category_data.xml',
        
        # Views with dedicated menu structure
        'views/ams_revenue_category_views.xml',
        'views/ams_financial_transaction_views.xml',
        'views/ams_financial_summary_views.xml',
        'views/ams_financial_dashboard_views.xml',
        'views/menu_views.xml',  # ← Own menu structure
        
        # Reports
        'reports/financial_reports.xml',
        'reports/board_reports.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_accounting/static/src/css/financial_dashboard.css',
            'ams_accounting/static/src/js/financial_widgets.js',
        ],
    },
    'installable': True,
    'application': True,     # ← Standalone app
    'auto_install': False,
    'license': 'LGPL-3',
}