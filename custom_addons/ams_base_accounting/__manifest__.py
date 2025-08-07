# -*- coding: utf-8 -*-
{
    'name': 'AMS Base Accounting',
    'version': '18.0.1.0.0',
    'summary': 'Base accounting functionality for AMS (Association Management System)',
    'description': """
AMS Base Accounting
===================

This module provides basic accounting functionality for the AMS (Association Management System):

* GL account configuration for subscription products
* Chart of accounts for associations
* Integration with standard Odoo accounting
* Setup wizard for account configuration

Features:
---------
* Product-specific GL account mapping
* AMS-specific chart of accounts
* Revenue recognition for subscriptions  
* Accounts receivable management
* Deferred revenue handling
* Setup and configuration wizards

    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'category': 'Association Management/Accounting',
    'depends': [
        'base',
        'account', 
        'product',
        'ams_subscriptions',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data files
        'data/ams_account_types.xml',
        'data/ams_account_templates.xml', 
        'data/ams_journals.xml',
        
        # Views
        'views/account_account_views.xml',
        'views/product_template_views.xml',
        'views/ams_accounting_config_views.xml',
        'views/account_move_views.xml',
        'wizard/ams_accounting_setup_wizard_views.xml',
        'views/ams_accounting_menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}