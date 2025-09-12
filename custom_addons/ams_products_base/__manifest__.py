# -*- coding: utf-8 -*-
{
    'name': 'AMS Products Base',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core product data structures and AMS extensions',
    'description': """
AMS Products Base - Foundation Product Module
============================================

This module provides the core product data structures and AMS-specific extensions
for the Association Management System:

* **Category-Based AMS Classification**
  - Products classified using enhanced Odoo product categories
  - AMS-specific category types (membership, event, education, etc.)
  - Automatic product configuration based on category attributes

* **Member Pricing System** 
  - Member vs non-member pricing with automatic calculations
  - Template-level pricing with variant-level overrides
  - Member discount percentage computation

* **Digital Product Management**
  - Digital product identification and delivery
  - Download URLs and file attachments
  - Automatic fulfillment for digital items

* **Inventory Integration**
  - Smart product type configuration (service vs stockable)
  - Integration with Odoo's inventory and stock management
  - Variant-specific inventory overrides

* **Enhanced SKU Management**
  - Automatic SKU generation with intelligent formatting
  - Template and variant-level SKU management
  - Legacy system integration support

* **Business Features**
  - Membership requirement flags for restricted products
  - Rich business methods for pricing and access control
  - Category-driven product defaults and validation

Foundation module for all AMS product-related functionality.

Key Changes in v18:
* Removed separate ams.product.type model
* Enhanced product.category with AMS-specific fields
* Simplified architecture with single classification system
* Better integration with Odoo's native category features
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
        'mail',
        'ams_member_data',
        'ams_product_types' #- now using enhanced product.category
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_category_data.xml',  # Renamed from pricelists_data.xml
        'views/product_category_views.xml',  # New - for enhanced categories
        'views/product_template_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 8,
}