# -*- coding: utf-8 -*-
{
    'name': 'AMS Membership Core',
    'version': '18.0.1.0.0',
    'summary': 'Core membership management with subscription functionality',
    'description': """
AMS Membership Core
===================

Core membership management functionality for Association Management System:

Features:
---------
* Product-based subscription management (Community compatible)
* Membership lifecycle management with automatic renewals
* Member benefit system with customizable benefits
* Portal integration for member self-service
* Upgrade/downgrade membership functionality
* Mass renewal processing
* Revenue recognition framework (placeholder)
* Proration calculations for membership changes

Subscription Product Types:
--------------------------
* Membership - Individual/Organization memberships (only 1 active at a time)
* Subscriptions - General recurring subscriptions
* Publications - Magazine/journal subscriptions  
* Chapter - Regional chapter memberships (future module)

Integration:
-----------
* Extends ams_foundation for member data
* Community-compatible subscription functionality
* Portal access for member self-service
* Automatic membership creation from paid invoices
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    'depends': [
        'ams_foundation',  # Must be first for proper integration
        'sale_management',
        'account',
        'portal',
        'mail',
        'website',
    ],
    'data': [
        # Security - Use foundation groups where possible
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequences.xml',
        'data/membership_data.xml',
        
        # Views - Models first, then actions
        'views/product_template_views.xml',
        'views/ams_membership_views.xml',
        'views/ams_subscription_views.xml',
        'views/ams_benefit_views.xml',
        'views/ams_renewal_views.xml',
        
        # Wizards
        'wizards/mass_renewal_wizard_views.xml',
        'wizards/membership_transfer_wizard_views.xml',
        
        # Portal
        'views/portal_membership_views.xml',
        
        # Reports
        'reports/membership_certificate.xml',
        
        # Menu (load last to use foundation structure)
        'views/membership_menu.xml',
    ],
    'demo': [
        'demo/membership_demo.xml',
    ],
    'installable': True,
    'application': False,  # Changed to False since this extends ams_foundation
    'auto_install': False,
    'sequence': 16,  # After ams_foundation (15)
    'post_init_hook': '_post_init_hook',
}