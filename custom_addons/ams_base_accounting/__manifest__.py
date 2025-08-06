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
        'account',  # We'll use some base accounting concepts but build our own
        # Add subscription dependency if it exists, or make it optional
        'ams_subscriptions',
    ],
    'data': [
        # Security
        'security/ams_accounting_security.xml',
        'security/ir.model.access.csv',
        
        # Data - Chart of Accounts Templates
        'data/account_account_data.xml',
        'data/account_journal_data.xml',
        'data/subscription_sequence.xml',
        
        # Views
        'views/account_account_views.xml',
        'views/account_journal_views.xml',
        'views/product_template_views.xml',
        'views/ams_subscription_accounting_views.xml',
        'views/revenue_recognition_views.xml',
        
        # Menus
        'views/ams_accounting_menu.xml',
        
        # Reports
        'reports/financial_reports.xml',
    ],
    'demo': [
        'demo/demo_chart_of_accounts.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 10,
}