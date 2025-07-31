# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscriptions',
    'version': '1.0',
    'summary': 'Association Management Subscriptions for Memberships, Chapters, and Publications',
    'description': """
AMS Subscriptions
=================
This module provides subscription management for associations including:
- Individual and Enterprise Memberships (with seat management)
- Regional Chapters (multi-chapter support)
- Publications (Digital and Print)
- Subscription lifecycle (Active → Grace → Suspended → Terminated)
- Renewal invoicing and proration
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'account',
        'contacts',
        'website',
        'website_sale',
        'point_of_sale',
        'mail',
        # Removed 'sale_subscription' - Enterprise only
    ],
    'data': [
        'security/ir.model.access.csv',
        # Load data FIRST
        'data/recurring_plans.xml',
        # Load views and actions BEFORE menus that reference them
        'views/ams_subscription_views.xml',
        'views/ams_subscription_tier_views.xml',
        'views/ams_subscription_seat_views.xml',
        'views/product_template_views.xml',
        # Load menus LAST so they can find the actions
        'views/ams_subscription_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}