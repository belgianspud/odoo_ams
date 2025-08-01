{
    'name': 'AMS Base Accounting',
    'version': '18.0.2.0.0',
    'category': 'Association Management',
    'summary': 'Financial Management Foundation for Association Management System',
    'description': '''
        AMS Base Accounting - Financial Management Foundation
        ==================================================
        
        Complete accounting foundation for associations including:
        
        Core Features:
        - GL Account mapping framework for AMS products
        - Deferred revenue and revenue recognition automation
        - Prorated billing and mid-period membership changes  
        - Multi-year membership revenue scheduling
        - Enterprise seat tracking and accounting
        
        Revenue Management:
        - Automatic deferred revenue posting on invoice payment
        - Monthly revenue recognition with journal entries
        - Proration handling for upgrades/downgrades
        - Credit management for membership changes
        
        Integration:
        - Seamless integration with ams_subscriptions
        - Contact/Account membership tracking
        - Product-to-GL account mapping
        - Invoice posting customization
        
        Financial Analytics:
        - Deferred revenue aging reports
        - Revenue recognition forecasting
        - Member lifetime value analysis
        - Board-ready financial summaries
    ''',
    'author': 'Your Organization',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'depends': [
        'base',
        'account',
        'sale',
        'product',
        'contacts',
        'mail',
        'web',
        'ams_subscriptions',  # Required integration
    ],
    'data': [
        # Security - MUST load in this order
        'security/ams_accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/ams_account_types_data.xml',
        'data/ams_accounting_cron.xml',
        
        # Views
        'views/ams_gl_account_views.xml',
        'views/ams_revenue_schedule_views.xml',
        'views/ams_membership_credit_views.xml',
        'views/res_partner_views.xml',  # Contact/Account enhancements
        'views/product_template_views.xml',  # GL account mapping
        'views/account_move_views.xml',  # Invoice enhancements
        
        # Reports
        'reports/ams_deferred_revenue_report.xml',
        'reports/ams_recognition_forecast_report.xml',
        'reports/ams_member_lifetime_value_report.xml',
        'reports/ams_financial_summary_report.xml',
        
        # Menu (load last)
        'views/ams_accounting_menu.xml',
    ],
    'demo': [
        'demo/ams_gl_accounts_demo.xml',
        'demo/ams_revenue_schedules_demo.xml',
    ],
    'installable': True,
    'application': True,  
    'auto_install': False,
    'license': 'LGPL-3',
}