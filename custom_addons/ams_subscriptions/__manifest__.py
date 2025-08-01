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
        # 'portal',  # Removed - not needed
    ],
    'data': [
        # Security - MUST load in this order
        'security/ams_subscription_security.xml',  
        'security/ir.model.access.csv',            
        
        # Data files  
        'data/ams_subscription_cron.xml',         
        
        # Views - FIXED ORDER: Views must load before actions that reference them
        'views/product_template_views.xml',
        'views/ams_subscription_views.xml',
        'views/ams_subscription_seat_views.xml',
        'views/ams_subscription_tier_views.xml',
        'views/ams_enhanced_views.xml',         # ← Load enhanced views BEFORE actions
        'views/ams_menu_actions.xml',           # ← Load actions AFTER views
        
        # Portal - TEMPORARILY REMOVED
        # 'views/portal_template.xml',
        
        # Menu (load last)
        'views/ams_subscription_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}