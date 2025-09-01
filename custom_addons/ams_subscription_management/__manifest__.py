{
    'name': 'AMS Subscription Management',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Subscription product definitions and member-type pricing management',
    'description': '''
AMS Subscription Management Module
=================================

A focused microservice that transforms standard products into sophisticated 
subscription offerings through intelligent product definition and member-type 
pricing management.

Key Features:
* Simple "Subscription Toggle" - Transform any product into a subscription with one click
* Intelligent auto-configuration with smart defaults based on product type
* Member-type pricing tiers (Student, Professional, Retired, International)
* Enterprise seat-based subscription models with configurable seat counts
* Billing period definitions (Monthly, Quarterly, Annual, Custom)
* Sophisticated pricing strategies with promotional pricing support
* Integration APIs for other modules to consume subscription definitions
* Clean microservice boundaries - handles product definition only

This module focuses exclusively on subscription product configuration, pricing 
strategies, and member-type differentiation, leaving lifecycle management, billing, 
and member services to other specialized AMS modules.

Integration Pattern:
* This module provides definitions → Other modules create instances
* ams_participation creates subscription instances using product definitions  
* ams_billing_core generates invoices using pricing tiers
* ams_portal_services displays products with member pricing
* ams_analytics sources subscription data for reporting
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        # Core Odoo modules
        'base',
        'product',
        'sale_management',
        # Required AMS modules (Layer 1 & 2 dependencies)
        'ams_member_data',        # Member types for pricing tiers
        'ams_products_base',      # Core product extensions
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data - Load in dependency order
        'data/billing_periods_data.xml',
        'data/subscription_types_data.xml',
        
        # Views - Core functionality
        'views/billing_period_views.xml',
        'views/subscription_product_views.xml', 
        'views/pricing_tier_views.xml',
        'views/product_template_views.xml',      # Subscription toggle UI
        
        # Wizards
        'wizards/subscription_builder_wizard_views.xml',
        'wizards/pricing_tier_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,  # This is a focused microservice, not a standalone application
    'sequence': 15,        # Layer 2 - Core Business Entities
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}