# -*- coding: utf-8 -*-
{
    'name': 'AMS Membership Core',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Membership lifecycle, subscriptions, and product management',
    'description': """
AMS Membership Core Module
=========================

This module provides the core membership and subscription management functionality:

Features:
---------
* Subscription product configuration with multiple product classes
* Membership lifecycle management (create, renew, upgrade, cancel)
* Multiple product classes: membership, chapter, subscription, publication, etc.
* Automated membership creation from paid invoices
* Pro-rating support for upgrades/downgrades
* Member portal with subscription management
* Renewal automation and reminders
* Integration with Odoo sales and accounting

Product Classes Supported:
-------------------------
* Membership - Primary association memberships
* Chapter - Local/regional chapter memberships  
* Subscription - Publications, newsletters, journals
* Publication - Books, guides, resources
* Exhibits - Trade show and exhibition access
* Advertising - Marketing and promotional opportunities
* Donations - Recurring donation programs
* Courses - Educational content and training
* Sponsorship - Event and program sponsorships
* Event Booth - Exhibition booth rentals
* Newsletter - Periodic communications
* Services - Professional services and consulting

Technical:
----------
* Extends product.template for subscription configuration
* Abstract base model with product class-specific child models
* Integration with ams_foundation for member types and settings
* Portal integration for member self-service
* Automated workflows for membership lifecycle events

Dependencies:
-------------
* ams_foundation - Core member data and settings
* Standard Odoo modules: sale, account, portal, website
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'ams_foundation',
        'sale',
        'account', 
        'portal',
        'website',
        'product',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/sequences.xml',
        'data/product_data.xml',
        
        # Views
        'views/product_template_views.xml',
        'views/membership_base_views.xml',
        'views/membership_membership_views.xml',
        'views/membership_subscription_views.xml',
        'views/portal_templates.xml',
        
        # Wizards
        'wizards/membership_upgrade_wizard_views.xml',
        'wizards/membership_renewal_wizard_views.xml',
        
        # Menus
        'views/menu_views.xml',
    ],
    'demo': [
        # Demo data files would go here
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 20,
    'post_init_hook': 'post_init_hook',
}