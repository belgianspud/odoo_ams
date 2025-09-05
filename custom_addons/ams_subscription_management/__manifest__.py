{
    'name': 'AMS Subscription Management',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Subscription product definitions and member-type pricing for Association Management System',
    'description': '''
AMS Subscription Management Module
=================================

Transforms standard products into sophisticated subscription offerings through the proven
"Subscription Toggle" pattern. This module provides subscription product definition 
capabilities with intelligent member-type pricing management while maintaining clean 
architectural boundaries with other AMS modules.

Key Features:
* One-Click Subscription Toggle for any product
* Smart auto-configuration when subscription features are enabled
* Member-type pricing tiers (Student, Professional, Corporate, etc.)
* Enterprise subscription support with seat-based models
* Flexible duration control (days, months, years)
* Automatic discount calculations and display
* Time-based promotional pricing with validity periods
* Configurable renewal policies and auto-renewal settings
* Billing period management for recurring subscriptions
* Integration-ready APIs for lifecycle and billing modules

Business Functions:
* Configure subscription products with multiple billing periods
* Offer tiered pricing by member type with automatic discounts
* Enable auto-renewal or manual renewal options
* Support enterprise subscriptions with seat allocations
* Require staff approval for premium subscription products
* Provide member vs non-member pricing visibility

This module focuses exclusively on subscription product configuration and pricing
strategies, leaving subscription lifecycle, billing, and portal services to other
specialized AMS modules for clean separation of concerns.

NOTE: This module currently operates in standalone mode. Full functionality requires
ams_member_data and ams_products_base modules which will be installed separately.
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale_management',
        'account',
        'mail',
        'ams_member_data',    # Member types and member management
        'ams_products_base',  # Product extensions and base functionality
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data - Basic billing periods only until dependencies available
        'data/billing_periods_data.xml',
        'data/subscription_types_data.xml',
        
        # Views
        'views/product_template_views.xml',
        'views/subscription_product_views.xml',
        'views/pricing_tier_views.xml',
        'views/billing_period_views.xml',
        
        # Wizards
        'wizards/subscription_builder_wizard_views.xml',
        'wizards/pricing_tier_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 9,  # Layer 2 - Core Business Entities, after ams_products_base (8)
    
    # Development and compatibility information
    'external_dependencies': {
        'python': ['dateutil'],
    },
    
    # Module compatibility and requirements
    'depends_if_installed': [
        'ams_member_data',
        'ams_products_base',
    ],
    
    # Post-init hook to handle missing dependencies gracefully
    'post_init_hook': 'post_init_hook',
    
    # Module lifecycle hooks
    'pre_init_hook': 'pre_init_hook',
}