{
    'name': 'AMS Subscriptions',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Membership subscription management for associations',
    'description': """
        AMS Subscriptions Module
        ========================
        
        This module provides comprehensive membership subscription management for 
        Association Management Systems including:
        
        * Membership Types and Tiers
        * Subscription Lifecycle Management (New, Active, Renewal, Lapsed, Canceled)
        * Automated Billing Integration
        * Member Portal Access
        * Renewal Notifications and Workflows
        * Chapter-based Memberships
        * Membership Benefits Tracking
        * Member Communication Tools
        
        Perfect for organizations like the AMA and other professional associations.
    """,
    'author': 'Your AMS Development Team',
    'website': '',
    'depends': [
        'base',
        'sale',
        'account', 
        'contacts',
        'website',
        'mail',
        'portal',
        'ams_module_manager',
    ],
    'data': [
        'security/ams_subscriptions_security.xml',
        'security/ir.model.access.csv',
        'data/membership_type_data.xml',
        'data/subscription_stage_data.xml',
        'views/membership_type_views.xml',
        'views/member_subscription_views.xml',
        'views/member_views.xml',
        'views/chapter_views.xml',
        'views/ams_subscriptions_menus.xml',
        'templates/portal_templates.xml',
        'wizard/subscription_renewal_wizard_views.xml',
        'wizard/bulk_subscription_wizard_views.xml',
        'reports/membership_reports.xml',
    ],
    'demo': [
        'demo/membership_type_demo.xml',
        'demo/member_subscription_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'sequence': 10,
}