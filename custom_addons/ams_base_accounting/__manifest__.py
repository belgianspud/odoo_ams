# -*- coding: utf-8 -*-
{
    'name': 'AMS Base Accounting',
    'version': '18.0.1.0.0',
    'summary': 'Accounting foundation for Association Management Systems',
    'description': """
AMS Base Accounting
==================
Complete accounting foundation for Association Management Systems including:

Core Features:
- Chart of Accounts management
- GL account setup and configuration
- Revenue recognition for subscriptions
- Deferred revenue handling
- Financial reporting foundation

Product Integration:
- Financial tab on all products
- GL account assignments per product
- Revenue recognition settings
- Cost accounting setup

Subscription Integration:
- Automatic journal entries for subscriptions
- Monthly revenue recognition automation
- Deferred revenue management
- Payment failure accounting

This module provides the accounting backbone for AMS operations while
integrating seamlessly with existing subscription management.
    """,
    'author': 'AMS Development Team',
    'website': 'https://yourwebsite.com',
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale_management',
        'mail',
        'analytic',
    ],
    'external_dependencies': {
        'python': ['dateutil'],
    },
    'data': [
        # Security
        'security/ams_accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Data - Chart of Accounts Templates and Sequences
        'data/account_account_data.xml',
        'data/account_journal_data.xml',
        'data/subscription_sequence.xml',
        
        # Views - in dependency order
        'views/account_account_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/ams_subscription_accounting_views.xml',
        'views/revenue_recognition_views.xml',
        
        # Menus
        'views/ams_accounting_menu.xml',
        
        # Reports
        'reports/financial_reports.xml',
    ],
    'demo': [
        # Only include demo data if no dependency issues
        # 'demo/demo_chart_of_accounts.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 10,
    'post_init_hook': '_ams_accounting_post_init',
}