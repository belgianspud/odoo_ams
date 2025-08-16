# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Billing (Core)',
    'version': '18.0.1.0.0',
    'summary': 'Core subscription billing functionality for Association Management System',
    'description': """
AMS Subscription Billing - Core Module
=======================================

This module provides essential automated billing functionality for subscription management:

Core Features:
--------------
* Automated billing schedules for subscription renewals
* Invoice generation for subscription periods
* Basic payment status tracking and overdue management
* Simple proration calculations for mid-cycle changes
* Standalone subscription management if no existing AMS module

What this module does:
----------------------
* Creates billing schedules when subscriptions are activated
* Generates invoices automatically based on subscription periods
* Tracks payment status and marks invoices as overdue
* Sends basic payment reminders
* Handles simple proration for subscription changes
* Provides basic billing management interface

Compatibility:
--------------
* Works standalone or extends existing ams_subscriptions module
* Compatible with Odoo Community 18.0
* Can be extended with additional billing modules

This is the foundation module that other billing modules can extend.
    """,
    'author': 'AMS Development Team',
    'website': 'https://example.com',
    'category': 'Sales/Subscriptions',
    'license': 'LGPL-3',
    
    # Core dependencies only - no external AMS modules required
    'depends': [
        'base',
        'mail',
        'account',
        'product',
        'sale',  # For basic subscription concepts
    ],
    
    # Data files
    'data': [
        # Security first
        'security/ams_billing_security.xml',
        'security/ir.model.access.csv',
        
        # Basic data
        'data/billing_sequences.xml',
        'data/email_templates.xml',
        'data/cron_jobs.xml',
        
        # Core views
        'views/ams_billing_schedule_views.xml',
        'views/ams_billing_event_views.xml',
        'views/ams_subscription_billing_views.xml',
        'views/res_config_settings_views.xml',
        
        # Menu
        'views/ams_billing_menu.xml',
        
        # Wizards
        'wizards/ams_manual_billing_wizard_views.xml',
    ],
    
    'demo': [
        'demo/billing_demo.xml',
    ],
    
    'installable': True,
    'application': True,  # This can be a standalone application
    'auto_install': False,
    
    # Hooks
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Version info
    'odoo_version': '18.0',
    
    # No external dependencies for core
    'external_dependencies': {},
    
    # Module metadata
    'sequence': 100,
    'development_status': 'Beta',
    
    # Assets (if needed for custom JS/CSS)
    'assets': {},
    
    # Price info (if commercial)
    'price': 0.0,
    'currency': 'USD',
    
    # Support info
    'support': 'support@example.com',
    'maintainer': 'AMS Development Team',
    
    # Images
    'images': ['static/description/banner.png'],
    
    # Cloc settings
    'cloc_exclude': ['./**/*'],
}