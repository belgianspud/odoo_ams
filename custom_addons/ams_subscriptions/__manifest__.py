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
        'point_of_sale',
    ],
    'data': [
        # Security first
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
        
        # Essential data only
        'data/chapter_data.xml',
        'data/subscription_type_data.xml',
        # 'data/subscription_rules_data.xml',  # COMMENTED OUT - has missing references
        # 'data/cron_data.xml',               # COMMENTED OUT - may have missing references
        # 'data/email_templates.xml',         # COMMENTED OUT - may have missing references
        
        # Essential views only
        'views/subscription_type_views.xml',
        'views/subscription_views.xml',
        # 'views/menu_views.xml',              # COMMENTED OUT - has missing action reference
        # 'views/chapter_views.xml',          # COMMENTED OUT - may have missing references
        # 'views/subscription_renewal_views.xml',  # COMMENTED OUT
        # 'views/partner_views.xml',          # COMMENTED OUT
        # 'views/product_views.xml',          # COMMENTED OUT
        # 'views/portal_templates.xml',       # COMMENTED OUT
        # 'views/website_templates.xml',      # COMMENTED OUT
        
        # Reports - commented out for now
        # 'reports/subscription_reports.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}