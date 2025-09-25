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
* Product-based subscription management (Odoo 18 compatible)
* Membership lifecycle management with automatic renewals
* Member benefit system with customizable benefits
* Portal integration for member self-service
* Upgrade/downgrade membership functionality
* Mass renewal processing
* Revenue recognition framework
* Proration calculations for membership changes

Integration:
-----------
* Extends ams_foundation for member data
* Compatible with Odoo Community 18
* Portal access for member self-service
* Automatic membership creation from paid invoices
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    'depends': [
        'portal',         # Load portal first to ensure it's available
        'ams_foundation', # Must be second for proper integration
        'sale_management',
        'account',
        'mail',
        'website',
        'payment',      # Commented out - add back if needed later
    ],
    'external_dependencies': {
        'python': ['python-dateutil'],
    },
    'data': [
        # Security
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequences.xml',
        'data/membership_data.xml',
        'data/cron_data.xml',
        
        # Views
        'views/product_template_views.xml',
        'views/ams_membership_views.xml',
        'views/ams_subscription_views.xml',
        'views/ams_benefit_views.xml',
        'views/ams_renewal_views.xml',
        'views/res_partner_views.xml',  # Added missing partner views
        
        # Wizards
        'wizards/mass_renewal_wizard_views.xml',
        'wizards/membership_transfer_wizard_views.xml',
        
        # Portal
        'views/portal_membership_templates.xml',  # Renamed for clarity
        
        # Reports
        #'reports/membership_certificate.xml',
        
        # Menu (load last)
        'views/membership_menu.xml',
    ],
    'demo': [
        'demo/membership_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
        ],
    },
    'installable': True,
    'application': False,  # Extension module
    'auto_install': False,
    'sequence': 16,
    'post_init_hook': '_post_init_hook',
    'pre_init_hook': '_pre_init_hook',  # Added for data migration
}