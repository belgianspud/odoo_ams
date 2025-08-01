# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscriptions',
    'version': '1.0.0',
    'summary': 'Manage association memberships, chapters, publications, and enterprise seats.',
    'description': """
AMS Subscriptions
=================
Custom subscription management for associations, including:
- Individual and Enterprise Memberships
- Chapters and Publications
- Seat Management for Enterprise Accounts
- Lifecycle Automation (Active → Grace → Suspended → Terminated)
- Product Integration for Website, POS, and Sales
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'sale_management',
        'account',
        'website_sale',
        'point_of_sale',
        'mail',
        'portal',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Views
        'views/ams_subscription_views.xml',
        'views/ams_subscription_seat_views.xml',
        'views/ams_subscription_tier_views.xml',
        # Menu
        'views/ams_subscription_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
