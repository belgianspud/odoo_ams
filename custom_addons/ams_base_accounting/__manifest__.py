# -*- coding: utf-8 -*-
{
    'name': 'AMS Base Accounting',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Base accounting functionality for Association Management System',
    'description': """
Association Management System - Base Accounting
===============================================

This module provides the foundational accounting functionality for association management, 
including specialized financial accounts, member billing, and revenue tracking.

Key Features:
------------
* Association-specific chart of accounts
* Member invoice and payment processing
* Subscription product financial configuration
* Revenue tracking by membership type
* Automated financial account assignment
* Financial reporting for associations
* Setup wizard for easy configuration

Business Benefits:
-----------------
* Proper financial tracking for membership organizations
* Automated revenue categorization by service type
* Simplified billing and payment processing
* Association-specific financial reports
* Streamlined financial operations for staff

Target Users:
------------
* Association financial staff
* Membership coordinators  
* Finance managers
* Association administrators
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    
    # Dependencies
    'depends': [
        'base',
        'account',
        'product',
        'sale',
        'mail',
    ],
    
    # Module Data Files
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',  # Removed group_descriptions.xml
        
        # Data
        'data/account_account_data.xml',
        'data/product_category_data.xml',
        'data/account_journal_data.xml',
        
        # Views
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        
        # Wizards
        'wizard/ams_accounting_setup_wizard_views.xml',
        
        # Menus
        'views/ams_accounting_menu.xml',
    ],
    
    # Demo Data
    'demo': [
        'demo/account_account_demo.xml',
        'demo/product_template_demo.xml',
        'demo/res_partner_demo.xml',
    ],
    
    # Module Configuration
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 100,
    
    # Post Installation Hook
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Support Information
    'support': 'support@yourorganization.com',
    'maintainer': 'Your Organization Development Team',
    
    # Development Information
    'development_status': 'Production/Stable',
    'complexity': 'normal',
    
    # Compatibility
    'python_requires': '>=3.8',
}