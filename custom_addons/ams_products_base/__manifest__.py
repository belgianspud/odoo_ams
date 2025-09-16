# -*- coding: utf-8 -*-
{
    'name': 'AMS Products Base',
    'version': '18.0.2.0.0',
    'category': 'Association Management',
    'summary': 'Enhanced AMS product management with behavior-driven configuration',
    'description': """
AMS Products Base - Enhanced Product Behavior Management
=======================================================

This module provides comprehensive product behavior management for associations,
with intuitive employee UX and powerful integration capabilities for downstream modules.

* **Product Behavior Types (Radio Button Selection)**
  - Membership Products: Recurring memberships with portal access
  - Subscription Products: Recurring billing with flexible terms  
  - Event Products: Event registration with automatic enrollment
  - Publication Products: Magazines, newsletters with subscription options
  - Merchandise Products: Physical goods with member pricing
  - Certification Products: Digital certificates with portal access
  - Digital Downloads: File/URL delivery with access control
  - Donation Products: Tax-deductible contributions with receipts

* **Enhanced Employee UX**
  - Clear "Product Behavior" tab with contextual field display
  - Radio button behavior selection with smart defaults
  - Tooltips and help text eliminate need for technical Odoo knowledge
  - Visual indicators for configuration status and issues
  - One-click testing for member pricing and product behavior

* **Category-Driven Defaults with Override Capability**
  - Products inherit settings from enhanced AMS categories
  - Employees can override any category default for specific products
  - Smart onchange behavior applies appropriate defaults automatically
  - Behavior-based SKU generation with prefixes (MEM-, EVT-, DIG-, etc.)

* **Comprehensive Feature Set**
  - Member pricing with automatic discount calculation
  - Subscription management with flexible term configuration
  - Portal access grants with group-specific permissions
  - Digital content delivery with URL/file attachment support
  - Event integration with automatic registration creation
  - Donation receipts with tax deductibility tracking
  - Benefit bundle linking and description management

* **Accounting Integration**
  - Multiple GL account types: deferred revenue, cash receipt, refund, membership revenue
  - Revenue recognition support for subscriptions and memberships
  - Configurable per product with category-level defaults
  - Integration with Odoo's native accounting workflows

* **Enhanced Search and Reporting**
  - Behavior-based filtering and grouping
  - Issue tracking (missing digital content, event templates)
  - Member pricing analysis and savings calculation
  - Subscription product identification and management
  - Portal access product tracking

* **Integration Hooks for Downstream Modules**
  - Clean API for subscription module integration
  - Event registration automation hooks  
  - Portal access management integration points
  - Digital delivery system compatibility
  - Membership lifecycle integration support
  - Donation receipt generation hooks

* **Legacy System Support**
  - Legacy product ID tracking for data migration
  - Flexible SKU management with auto-generation
  - Backward compatibility with existing AMS modules
  - Import/export support for bulk product creation

Key Benefits for Associations:
- Simplified product setup with behavior-driven configuration
- Consistent member pricing across all product types
- Automated workflows for subscriptions, events, and digital delivery
- Comprehensive tracking of member benefits and access rights
- Professional donation receipt generation for tax compliance
- Seamless integration with association management workflows

Key Benefits for Employees:
- Intuitive interface eliminates need for Odoo technical knowledge
- Visual configuration status with clear next steps
- One-click testing and validation of product settings
- Smart defaults reduce setup time and errors
- Clear separation of product behavior types with appropriate fields

Technical Architecture:
- Leverages ams_product_types for category-driven behavior
- Integrates with ams_member_data for membership validation  
- Uses Odoo native features for maximum compatibility
- Provides clean extension points for specialized modules
- Maintains performance with stored computed fields and proper indexing

Version 2.0 Enhancements:
- Complete product behavior management system
- Enhanced employee UX with contextual field display
- Comprehensive integration hooks for downstream modules
- Behavior-based product creation workflows
- Advanced search and filtering capabilities
- Issue tracking and validation systems
- Accounting integration with multiple GL account types
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
        'account',          # For accounting GL account fields
        'mail',
        'event',            # For event template integration
        'portal',           # For portal group management
        'ams_member_data',      # For membership status integration
        'ams_product_types'     # For enhanced category functionality
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Views - Enhanced product management
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        
        # Data - Demo products and configurations
        'demo/demo_ams_products.xml',
    ],
    'demo': [
        'demo/demo_ams_products.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Future: Add any custom CSS/JS for enhanced UX
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True, 
    'sequence': 10,  # After core AMS modules but before specialized ones
    
    # Module relationships
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
    
    # External dependencies
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    
    # Development and maintenance info
    'maintainers': ['your-organization'],
    'contributors': [],
    
    # Module maturity and support
    'development_status': 'Production/Stable',
    'support': 'https://your-support-url.com',
    'documentation': 'https://your-docs-url.com/ams-products-base',
    
    # Compatibility and requirements
    'python_requires': '>=3.8',
    'bootstrap': False,
    
    # Additional metadata
    'images': [
        #'static/description/banner.png',
        #'static/description/product_behavior_selection.png', 
        #'static/description/member_pricing.png',
        #'static/description/subscription_management.png',
    ],
    
    # Localization support
    'translations': [
        # Future: Add translation files
        # 'i18n/es.po',
        # 'i18n/fr.po', 
    ],
    
    # Price and commercial info (if applicable)
    'price': 0,
    'currency': 'USD',
    'live_test_url': None,
}