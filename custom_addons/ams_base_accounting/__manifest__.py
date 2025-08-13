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

Installation:
-------------
This module automatically creates and configures AMS-specific accounts during installation.
If you encounter account conflicts, run the Setup Wizard from AMS → Configuration → Accounting Setup.

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
        # Security - Load first
        'security/ir.model.access.csv',
        
        # Data files - Configuration only (no account creation)
        'data/ams_account_types.xml',          # Configuration parameters only
        'data/ams_account_templates.xml',      # Additional templates and categories
        'data/ams_journals.xml',               # Journal configuration parameters
        
        # Views - Load after data
        'views/account_account_views.xml',
        'views/product_template_views.xml',
        'views/ams_accounting_config_views.xml',
        'views/account_move_views.xml',
        'views/ams_accounting_dashboard_views.xml',    # ADDED: Dashboard views
        'wizard/ams_accounting_setup_wizard_views.xml',
        'views/ams_accounting_menu.xml',               # Load menu last
    ],
    'demo': [
        # Demo data for testing (optional)
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # Hooks for setup and cleanup
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # License and metadata
    'license': 'LGPL-3',
    'sequence': 100,
    'development_status': 'Beta',
    
    # Version constraints
    'odoo_version': '18.0',
    
    # External dependencies
    'external_dependencies': {
        'python': [],  # No special Python dependencies
    },
    
    # Assets (if needed for web components)
    'assets': {
        'web.assets_backend': [
            # Add any custom CSS/JS files here if needed
        ],
    },
    
    # Images for module store
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    
    # Support information
    'support': 'https://yourcompany.com/support',
    'maintainers': ['your-team'],
}