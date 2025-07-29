{
    'name': 'AMS Subscriptions',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Subscription Management for Association Management System',
    'description': '''
        AMS Subscriptions - Membership and Subscription Management
        ========================================================
        
        Complete subscription management solution for associations.
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
        # NOTE: Do not include 'ams_subscriptions' - that creates circular dependency!
        # NOTE: Do not include 'ams_base_accounting' initially - add after both work separately
    ],
    'data': [
        # Security first
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/chapter_data.xml',
        'data/subscription_type_data.xml',
        'data/subscription_rules_data.xml',
        'data/cron_data.xml',
        'data/email_templates.xml',
        
        # Views
        'views/menu_views.xml',
        'views/chapter_views.xml',
        'views/subscription_views.xml',
        'views/subscription_type_views.xml',
        'views/subscription_renewal_views.xml',
        'views/partner_views.xml',
        'views/product_views.xml',
        'views/portal_templates.xml',
        'views/website_templates.xml',
        
        # Reports
        'reports/subscription_reports.xml',
    ],
    'demo': [
        # Demo files if any
    ],
    'assets': {
        # Assets if any
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}