# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Billing (Core)',
    'version': '18.0.1.0.0',
    'summary': 'Core subscription billing functionality for AMS',
    'description': """
AMS Subscription Billing - Core Module
=======================================

This module provides essential automated billing functionality for AMS subscriptions:

Core Features:
--------------
* Automated billing schedules for subscription renewals
* Invoice generation for subscription periods
* Basic payment status tracking and overdue management
* Simple proration calculations for mid-cycle changes
* Integration with existing AMS subscription management

What this module does:
----------------------
* Creates billing schedules when subscriptions are activated
* Generates invoices automatically based on subscription periods
* Tracks payment status and marks invoices as overdue
* Sends basic payment reminders
* Handles simple proration for subscription changes
* Provides basic billing management interface

What this module does NOT include:
----------------------------------
* Advanced dunning sequences (see ams_advanced_dunning)
* Payment retry logic (see ams_payment_retry) 
* Stored payment methods (see ams_payment_methods)
* Advanced analytics (see ams_billing_analytics)
* Customer self-service portal (see ams_customer_portal)
* Complex proration methods (see ams_proration_engine)

This is the foundation module that other billing modules extend.
    """,
    'author': 'Your AMS Development Team',
    'website': 'https://yourcompany.com',
    'category': 'Association Management/Billing',
    'license': 'LGPL-3',
    
    # Minimal dependencies for core functionality
    'depends': [
        'base',
        'mail',
        'account',
        'ams_subscriptions',  # The core AMS subscription module
    ],
    
    # Data files - simplified
    'data': [
        # Security
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
    'application': True,  # This is an extension, not a standalone app
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
}