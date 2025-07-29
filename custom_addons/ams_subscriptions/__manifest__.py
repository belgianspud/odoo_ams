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
        'ams_base_accounting',
    ],
    'data': [
        # Your data files here
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
        # Add other data files as needed
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