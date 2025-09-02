# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Management',
    'version': '17.0.1.0.0',
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
        'ams_member_management',
        
        # Optional integrations (soft dependencies)
        # These will be loaded if available but not required
    ],
    
    'external_dependencies': {
        'python': [
            'dateutil',  # For advanced date calculations
        ],
    },
    
    'data': [
        # Security
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
        
        # Menu structure will be defined in view files
    ],
    
    'demo': [
        'data/demo_data.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'ams_subscription_management/static/src/css/subscription_management.css',
            'ams_subscription_management/static/src/js/subscription_product_widget.js',
        ],
        'web.assets_frontend': [
            'ams_subscription_management/static/src/css/portal_subscription.css',
            'ams_subscription_management/static/src/js/subscription_selection.js',
        ],
    },
    
    'qweb': [
        'static/src/xml/subscription_templates.xml',
    ],
    
    'application': True,
    'installable': True,
    'auto_install': False,
    
    # Module installation order and dependencies
    'sequence': 150,
    
    # Version compatibility
    'odoo_version': '17.0',
    
    # Post-install configuration
    'post_init_hook': 'post_install_hook',
    'uninstall_hook': 'uninstall_hook',
    
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
    
    # Compatibility and testing
    'test': [
        'tests/test_subscription_product.py',
        'tests/test_pricing_tiers.py',
        'tests/test_billing_periods.py',
        'tests/test_wizards.py',
    ],
    
    'images': [
        'static/description/icon.png',
        'static/description/main_screenshot.png',
        'static/description/pricing_tiers.png',
        'static/description/wizard_flow.png',
    ],
    
    # Feature flags and configuration
    'config_parameter': 'ams_subscription_management',
    
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
    
    # Module lifecycle hooks
    'pre_init_hook': 'pre_install_hook',
    'post_load_hook': 'post_load_hook',
    
    # Advanced configuration
    'bootstrap': False,  # Not a bootstrap module
    'cloc_exclude': [
        'static/**/*',  # Exclude static files from code analysis
    ],
}