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
* Extends ams_subscriptions with billing functionality

What this module does:
----------------------
* Creates billing schedules when subscriptions are activated
* Generates invoices automatically based on subscription periods
* Tracks payment status and marks invoices as overdue
* Sends basic payment reminders
* Handles simple proration for subscription changes
* Provides basic billing management interface

Dependencies:
-------------
* Requires ams_subscriptions module (core subscription management)
* Requires ams_base_accounting module (accounting foundation)
* Compatible with Odoo Community 18.0

This module extends the core subscription functionality with billing automation.
    """,
    'author': 'AMS Development Team',
    'website': 'https://example.com',
    'category': 'Sales/Subscriptions',
    'license': 'LGPL-3',
    
    # Proper dependency chain
    'depends': [
        'base',
        'mail',
        'account',
        'product',
        'sale',
        'ams_base_accounting',  # Accounting foundation first
        'ams_subscriptions',    # Then core subscriptions
    ],
    
    # Data files - FIXED loading order
    'data': [
        # Security first
        'security/ams_billing_security.xml',
        'security/ir.model.access.csv',
        
        # Basic data
        'data/billing_sequences.xml',
        'data/email_templates.xml',
        'data/cron_jobs.xml',
        
        # Core views - load models first, then views that depend on them
        'views/ams_billing_schedule_views.xml',
        'views/ams_billing_event_views.xml',
        'views/ams_subscription_billing_views.xml',
        'views/res_config_settings_views.xml',
        
        # Menu - load last
        'views/ams_billing_menu.xml',
        
        # Wizards
        'wizards/ams_manual_billing_wizard_views.xml',
    ],
    
    'demo': [
        'demo/billing_demo.xml',
    ],
    
    'installable': True,
    'application': False,  # This extends ams_subscriptions, not standalone
    'auto_install': False,
    
    # Hooks
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Version info
    'odoo_version': '18.0',
    
    # No external dependencies for core
    'external_dependencies': {},
    
    # Module metadata
    'sequence': 110,  # Higher than base modules
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