# -*- coding: utf-8 -*-
{
    'name': 'AMS Base Accounting',
    'version': '1.0.0',
    'summary': 'Base accounting functionality for Association Management System',
    'description': """
AMS Base Accounting
==================
Provides essential accounting functionality for associations:
- Association-specific chart of accounts categories
- Product-level GL account configuration  
- Basic journal entry automation for subscriptions
- Simple accounting integration with AMS subscriptions
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',
    'depends': [
        'account',              # Core accounting (Community)
        'sale_management',      # Sales integration
        'ams_subscriptions',    # AMS subscription integration
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data - Chart of accounts setup
        'data/ams_account_types.xml',
        'data/ams_account_templates.xml', 
        'data/ams_journals.xml',
        
        # Views
        'views/account_account_views.xml',
        'views/product_template_views.xml',
        'views/ams_accounting_config_views.xml',
        'views/account_move_views.xml',
        
        # Configuration wizard
        'wizard/ams_accounting_setup_wizard_views.xml',
        
        # Menu integration
        'views/ams_accounting_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}