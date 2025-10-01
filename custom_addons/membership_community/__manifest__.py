# -*- coding: utf-8 -*-
{
    'name': 'Membership Community',
    'version': '18.0.1.0.0',
    'category': 'Membership',
    'summary': 'Association membership management extending subscriptions',
    'description': '''
Membership Community - Association Management
============================================

Extends subscription_management with association-specific features:

Core Features:
* Member Categories (Individual, Student, Corporate, Honorary, etc.)
* Membership Benefits (discounts, access, publications)
* Membership Features (portal access, credentials, CE tracking)
* Eligibility Requirements & Verification
* Chapter Memberships
* Member Directory
* Professional Integration hooks

Leverages subscription_management for:
* Recurring billing and invoicing
* Subscription lifecycle management
* Renewal and upgrade/downgrade logic
* Seat management for organizational memberships
* Pricing tiers and prorating
* Calendar vs Anniversary periods

Perfect for:
* Professional Associations
* Trade Organizations
* Non-profit Membership Organizations
* Clubs and Societies
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    
    'depends': [
        'subscription_management',  # Core dependency - provides billing & lifecycle
        'portal',                   # Member portal access
        'mail',                     # Messaging and activity tracking
    ],
    
    'data': [
        # Security
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data - load in order
        'data/membership_category_data.xml',
        'data/membership_feature_data.xml',
        'data/membership_benefit_data.xml',
        
        # Views - Master Data
        'views/membership_category_views.xml',
        'views/membership_benefit_views.xml',
        'views/membership_feature_views.xml',
        
        # Views - Extensions
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/subscription_views.xml',
        
        # Wizards
        'wizards/membership_wizard_views.xml',
        'wizards/category_change_wizard_views.xml',
        
        # Menus
        'views/menu_views.xml',
    ],
    
    'demo': [
        'demo/membership_demo.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'membership_community/static/src/css/membership.css',
        ],
    },
    
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,
}