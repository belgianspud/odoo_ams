# -*- coding: utf-8 -*-
{
    'name': 'Membership Community',
    'version': '2.0.0',
    'category': 'Membership',
    'summary': 'Enhanced membership management with subscription integration',
    'description': '''
Membership Community Module
===========================

Comprehensive membership management system that extends subscription_management
with member-specific features for professional associations.

Key Features:
* Membership Records - Track member history and status
* Member Categories - Individual, Student, Corporate, Honorary, etc.
* Membership Benefits - Define benefits included with memberships
* Membership Features - Technical features for module integration
* Anniversary vs Calendar Year - Flexible membership year types
* Subscription Integration - Leverages subscription_management for billing/renewal
* Chapter Memberships - Support for chapter/section memberships
* Organizational Support - Foundation for seat-based organizational memberships
* Professional Integration - Extension points for professional features
* Portal Ready - Member portal access configuration

Member Categories:
* Individual Members
* Organizational/Corporate Members
* Student Members
* Honorary Members
* Retired Members
* Emeritus Members
* Affiliate Members
* Associate Members

Membership Year Types:
* Calendar Year - Jan 1 - Dec 31 (with prorating)
* Anniversary Year - 12 months from join date

Integration Points:
* Extends subscription_management for billing and renewal
* Ready for membership_professional module (credentials, CE, designations)
* Ready for membership_organizational module (seats, org admin)
* Portal integration for member self-service

This module provides the foundation for professional association membership
management while leveraging proven subscription infrastructure.
    ''',
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'product',
        'sale',
        'sale_management',
        'subscription_management',  # KEY DEPENDENCY - for billing/renewal
        'portal',
        'mail',
    ],
    'data': [
        # Security
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/membership_sequence.xml',
        'data/membership_category_data.xml',
        'data/membership_feature_data.xml',
        'data/membership_benefit_data.xml',
        
        # Views - Master Data
        'views/membership_category_views.xml',
        'views/membership_feature_views.xml',
        'views/membership_benefit_views.xml',
        
        # Views - Core
        'views/membership_record_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        
        # Menus
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/membership_demo.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'post_init_hook': 'post_init_hook',
}