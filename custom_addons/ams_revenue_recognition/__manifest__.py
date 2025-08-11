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
    
    # FIXED: Proper dependency order and requirements
    'depends': [
        'base',
        'account',
        'mail',  # ADDED: Required for mail.thread functionality
        'ams_base_accounting',
        'ams_subscriptions',
    ],
    
    # FIXED: Proper file loading order
    'data': [
        # Security - Load first (CRITICAL ORDER)
        'security/ams_revenue_recognition_security.xml',
        'security/ir.model.access.csv',
        
        # Data files - Load after security
        'data/ams_revenue_recognition_cron.xml',
        
        # Core model views - Load in dependency order
        'views/ams_revenue_recognition_views.xml',  # Load recognition views first
        'views/ams_revenue_schedule_views.xml',     # Then schedule views
        
        # Extension views - Load after core views (FIXED ORDER)
        'views/product_template_views.xml',         # Extend product forms first
        'views/ams_subscription_views.xml',         # Then subscription forms  
        'views/account_move_views.xml',             # Then invoice forms
        
        # Menu and actions - Load last
        'views/ams_revenue_recognition_menu.xml',
        
        # Reports - Load after all views
        'reports/ams_revenue_reports.xml',
    ],
    
    'demo': [
        'demo/ams_revenue_recognition_demo.xml',
    ],
    
    # FIXED: Module properties
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # FIXED: Proper hook configuration
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',  # ADDED: For clean uninstall
    
    # ADDED: External dependencies (if any)
    'external_dependencies': {
        'python': ['dateutil'],  # Already in Odoo, but explicit
    },
    
    # ADDED: Assets (if needed for future web components)
    'assets': {
        'web.assets_backend': [
            # Future: Add any custom CSS/JS files here
        ],
    },
    
    # ADDED: Odoo version constraints
    'odoo_version': '18.0',
    
    # ADDED: Module maturity and support info
    'development_status': 'Beta',  # Alpha, Beta, Production/Stable, Mature
    'maintainers': ['your-team'],
    
    # ADDED: Sequence for module loading
    'sequence': 100,
    
    # ADDED: Images for module store (optional)
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    
    # ADDED: Additional metadata
    'support': 'https://yourcompany.com/support',
    'website': 'https://yourcompany.com/ams',
    
    # ADDED: Price and currency (if commercial)
    # 'price': 0.00,
    # 'currency': 'EUR',
    
    # FIXED: Ensure clean installation
    'init_xml': [],
    'update_xml': [],
}