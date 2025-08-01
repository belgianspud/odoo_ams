{
    'name': 'AMS Accounting',
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
        # NOTE: Add 'ams_subscriptions' here after both modules are working together
    ],
    'data': [
        # Security - MUST load in this order
        'security/ams_accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Master data
        'data/revenue_category_data.xml',
        
        # Demo data
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,  
    'auto_install': False,
    'license': 'LGPL-3',
}