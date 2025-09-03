# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Management',
    'version': '18.0.1.0.0',  # Updated for Odoo 18
    'category': 'Association Management',
    'summary': 'Advanced subscription product management for association memberships and services',
    'description': '''
AMS Subscription Management
===========================

Transform any product into a sophisticated subscription offering with member pricing, 
enterprise features, and intelligent renewal management.

Key Features
------------
* **Smart Product Conversion**: Convert any product to subscription with one click
* **Member Pricing Tiers**: Create pricing tiers for different member types with verification
* **Enterprise Subscriptions**: Seat-based pricing for organizational memberships
* **Flexible Billing Periods**: Monthly, quarterly, annual, and custom billing cycles
* **Guided Setup Wizard**: Step-by-step subscription product configuration
* **Bulk Pricing Tools**: Efficiently manage multiple pricing tiers
* **Renewal Management**: Automated renewal reminders and early bird discounts
* **Access Control**: Member-only subscriptions with approval workflows

Business Benefits
-----------------
* Increase revenue with tiered pricing strategies
* Reduce administrative overhead with automation
* Improve member retention with flexible renewal options
* Scale organizational memberships with enterprise features
* Maintain compliance with verification requirements

Technical Features
------------------
* Seamless Odoo integration with existing product catalog
* Multi-company support with proper security rules
* Extensible architecture for custom subscription types
* Comprehensive API for integration with other modules
* Advanced reporting and analytics ready

This module is part of the AMS (Association Management System) suite and integrates
seamlessly with member management, event registration, and financial modules.
    ''',
    
    'author': 'AMS Development Team',
    'website': 'https://www.ams-odoo.com',
    'license': 'LGPL-3',
    
    'depends': [
        # Core Odoo modules
        'base',
        'product',
        'mail',
        'portal',
        
        # AMS Core modules
        'ams_system_config',
        'ams_products_base',
        'ams_member_data',  
    ],
    
    # FIXED: Corrected external_dependencies syntax
    'external_dependencies': {
        'python': ['python-dateutil'],  # Removed the nested 'python' key
    },
    
    'data': [
        # Security
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        
        # Data files
        'data/billing_period_data.xml',
        
        # Views
        'views/billing_period_views.xml',
        'views/subscription_product_views.xml',
        'views/pricing_tier_views.xml',
        'views/product_template_views.xml',
        
        # Wizards
        'wizards/subscription_builder_wizard_views.xml',
    ],
    
    #'demo': [
    #    'data/demo_data.xml',
    #],
    
    'application': True,
    'installable': True,
    'auto_install': False,
    
    # Module installation order and dependencies
    'sequence': 150,
    
    # Version compatibility
    'odoo_version': '18.0',  # Updated for Odoo 18
    
    # Development and maintenance
    'maintainers': ['ams-dev-team'],
    'contributors': [
        'AMS Development Team',
    ],
    
    # Module classification
    'tags': [
        'subscription',
        'membership',
        'association',
        'pricing',
        'enterprise',
        'renewal',
    ],
    
    # Pricing and marketplace (if publishing to app store)
    'price': 0,  # Free/open source
    'currency': 'USD',
    
    # Support and documentation
    'support': 'support@ams-odoo.com',
    'documentation': 'https://docs.ams-odoo.com/subscription-management',
    'repository': 'https://github.com/ams-odoo/ams-subscription-management',
    
    # Integration points
    'depends_if_installed': [
        'ams_event_management',  # Event-based subscriptions
        'ams_financial_management',  # Payment integration
        'ams_analytics',  # Subscription analytics
        'ams_portal',  # Member portal integration
        'sale_management',  # Sales order integration
        'account',  # Invoice integration
        'website_sale',  # E-commerce integration
    ],
    
    # Advanced configuration
    'bootstrap': False,  # Not a bootstrap module
}