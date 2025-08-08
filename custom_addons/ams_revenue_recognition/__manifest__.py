# -*- coding: utf-8 -*-
{
    'name': 'AMS Revenue Recognition',
    'version': '18.0.1.0.0',
    'summary': 'Automated revenue recognition for AMS subscription organizations (ASC 606/IFRS 15)',
    'description': """
AMS Revenue Recognition
=======================

This module provides automated revenue recognition for subscription-based membership organizations 
according to accounting standards (ASC 606/IFRS 15).

Key Features:
-------------
* Automated monthly revenue recognition jobs
* Deferred revenue management for prepaid subscriptions
* Proration logic for mid-cycle changes and cancellations
* Recognition schedules with visual timeline
* Contract modification handling with proper revenue adjustment
* Recognition dashboard and detailed reporting
* ASC 606/IFRS 15 compliance automation

Integration:
------------
* Seamlessly integrates with AMS Base Accounting
* Automatically processes AMS subscription revenue
* Creates proper journal entries for recognition
* Handles complex scenarios like upgrades, downgrades, and cancellations

Workflow:
---------
1. Subscription invoices create deferred revenue entries
2. Recognition schedules are automatically generated
3. Monthly cron jobs recognize revenue based on schedules
4. Contract modifications trigger proper revenue adjustments
5. Dashboard provides visibility into recognition status

This module is essential for associations that need:
- Accurate financial reporting
- Compliance with revenue recognition standards
- Automated processing of subscription revenue
- Professional-grade accounting practices
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
        # Security
        'security/ams_revenue_recognition_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/ams_revenue_recognition_cron.xml',
        'data/ams_revenue_recognition_data.xml',
        
        # Views
        'views/ams_revenue_schedule_views.xml',
        'views/ams_revenue_recognition_views.xml',
        'views/ams_contract_modification_views.xml',
        'views/ams_revenue_dashboard_views.xml',
        'wizard/ams_revenue_adjustment_wizard_views.xml',
        'wizard/ams_recognition_manual_wizard_views.xml',
        
        # Reports
        'reports/ams_revenue_recognition_reports.xml',
        'reports/ams_revenue_schedule_report.xml',
        'reports/ams_deferred_revenue_report.xml',
        
        # Menu
        'views/ams_revenue_recognition_menu.xml',
    ],
    'demo': [
        'demo/ams_revenue_recognition_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'external_dependencies': {
        'python': ['dateutil'],
    },
}