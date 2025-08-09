# -*- coding: utf-8 -*-
{
    'name': 'AMS Revenue Recognition',
    'version': '18.0.1.0.0',
    'summary': 'Revenue recognition for AMS subscription products',
    'description': """
AMS Revenue Recognition
=======================

This module provides revenue recognition functionality for AMS subscription products:

Key Features:
-------------
* Automated revenue recognition schedules for subscriptions
* Straight-line recognition over subscription periods
* Deferred revenue handling for prepaid memberships
* Integration with subscription lifecycle (Active → Grace → Suspended)
* Manual and automated recognition processing
* Revenue recognition dashboard and reporting

Workflow:
---------
1. When subscription invoices are posted, recognition schedules are created
2. For annual memberships: revenue is deferred and recognized monthly
3. For monthly memberships: revenue is recognized immediately  
4. Automated cron processes recognition entries
5. Integration with subscription state changes

Supported Subscription Types:
-----------------------------
* Individual and Enterprise Memberships
* Chapter Memberships
* Publication Subscriptions
* Enterprise Seat Add-ons

This module integrates seamlessly with AMS Subscriptions and AMS Base Accounting
to provide professional revenue recognition for membership organizations.
    """,
    'author': 'Your AMS Development Team',
    'website': 'https://yourcompany.com',
    'category': 'Association Management/Accounting',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'ams_base_accounting',
        'ams_subscriptions',
    ],
    'data': [
        # Security - Load first
        'security/ams_revenue_recognition_security.xml',
        'security/ir.model.access.csv',
        
        # Data files - Load after security
        'data/ams_revenue_recognition_cron.xml',
        
        # Core model views - Load in dependency order
        'views/ams_revenue_recognition_views.xml',  # Load recognition views first
        'views/ams_revenue_schedule_views.xml',     # Then schedule views
        
        # Extension views - Load after core views
        'views/product_template_views.xml',         # Extend product forms
        'views/ams_subscription_views.xml',         # Extend subscription forms  
        'views/account_move_views.xml',             # Extend invoice forms
        
        # Menu and actions - Load last
        'views/ams_revenue_recognition_menu.xml',
        
        # Reports - Load after all views
        'reports/ams_revenue_reports.xml',
    ],
    'demo': [
        'demo/ams_revenue_recognition_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}