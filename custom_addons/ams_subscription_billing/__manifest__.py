# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Billing',
    'version': '18.0.1.0.0',
    'summary': 'Automated subscription billing and payment management for AMS',
    'description': """
AMS Subscription Billing
========================

This module provides comprehensive automated billing functionality for AMS subscription products:

Core Features:
--------------
* Automated Invoice Generation - Bulk billing runs for subscription renewals
* Smart Payment Processing - Multiple payment gateways and retry logic
* Intelligent Dunning Management - 3-step escalation process with customizable templates
* Proration Engine - Handle mid-cycle upgrades, downgrades, and adjustments
* Payment Retry Logic - Exponential backoff with configurable retry attempts
* Billing Calendar - Smart scheduling around weekends and holidays
* Exception Handling - Manual review queue for billing issues and failed payments

Billing Automation:
-------------------
* Scheduled billing runs with batch processing
* Automatic invoice generation for subscription renewals
* Real-time payment processing with multiple gateway support
* Automated retry for failed payments with intelligent scheduling
* Comprehensive payment failure tracking and reporting

Dunning Management:
-------------------
* 3-tier dunning process: Reminder → Warning → Final Notice
* Customizable email templates with professional designs
* Grace period management with configurable suspension rules
* Automated escalation with manual intervention options
* Customer communication tracking and response management

Proration & Adjustments:
------------------------
* Automatic proration for mid-cycle subscription changes
* Credit/debit calculations for upgrades and downgrades
* Seat adjustment handling for enterprise subscriptions
* Partial billing period calculations
* Manual adjustment capabilities with approval workflows

Financial Integration:
----------------------
* Seamless integration with AMS Base Accounting
* Revenue recognition support for deferred billing
* Comprehensive financial reporting and analytics
* Account reconciliation and payment matching
* Audit trails for all billing transactions

This module transforms your AMS into a professional billing platform capable of
handling complex subscription scenarios with minimal manual intervention.
    """,
    'author': 'Your AMS Development Team',
    'website': 'https://yourcompany.com',
    'category': 'Association Management/Billing',
    'license': 'LGPL-3',
    
    # Dependencies
    'depends': [
        'base',
        'mail',
        'account',
        'payment',
        'ams_base_accounting',
        'ams_subscriptions',
        # 'ams_revenue_recognition',  # Optional but recommended
    ],
    
    # Data files
    'data': [
        # Security - Load first
        'security/ams_subscription_billing_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/billing_sequence.xml',
        'data/ams_dunning_templates.xml',
        'data/ams_billing_cron.xml',
        'data/ams_billing_configuration.xml',
        
        # Core model views
        'views/ams_billing_schedule_views.xml',
        'views/ams_billing_run_views.xml',
        'views/ams_billing_event_views.xml',
        'views/ams_payment_retry_views.xml',
        'views/ams_dunning_process_views.xml',
        'views/ams_proration_calculation_views.xml',
        
        # Extension views
        'views/ams_subscription_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        
        # Configuration and settings
        'views/ams_billing_configuration_views.xml',
        
        # Menu and actions
        'views/ams_subscription_billing_menu.xml',
        
        # Reports
        'reports/ams_billing_reports.xml',
        
        # Wizards
        'wizard/ams_billing_run_wizard_views.xml',
        'wizard/ams_payment_retry_wizard_views.xml',
        'wizard/ams_proration_wizard_views.xml',
    ],
    
    'demo': [
        'demo/ams_subscription_billing_demo.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # Hooks for setup and cleanup
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Version constraints
    'odoo_version': '18.0',
    
    # External dependencies
    'external_dependencies': {
        'python': ['dateutil'],
    },
    
    # Assets for web components
    'assets': {
        'web.assets_backend': [
            'ams_subscription_billing/static/src/css/billing_dashboard.css',
            'ams_subscription_billing/static/src/js/billing_widgets.js',
        ],
    },
    
    # Module metadata
    'sequence': 110,
    'development_status': 'Beta',
    'maintainers': ['your-team'],
    'support': 'https://yourcompany.com/support',
    
    # Images for module store
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
}