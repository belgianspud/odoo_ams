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

* **AMS Product Classification**
  - Products identified as AMS-specific with type classification
  - Integration with AMS product types for filtering and organization

* **Member Pricing and Discounts** 
  - Member-specific pricing vs non-member pricing
  - Automatic calculation of member discount percentages
  - Support for membership-based pricing strategies

* **Digital Product Management**
  - Digital product identification and delivery
  - Download URLs and file attachments
  - Automatic fulfillment for digital items
  - Integration with digital content systems

* **Advanced Product Features**
  - Membership requirement flags for restricted products
  - Inventory and fulfillment control separation
  - Chapter-specific product access restrictions
  - Regional and chapter-based product offerings

* **Integration and Legacy Support**
  - SKU management and legacy system integration
  - Seamless transition from previous AMS data
  - Compatibility with existing product workflows

* **Foundation for Higher-Level Modules**
  - Core data structures for billing and e-commerce
  - Integration points for event registration
  - Support for membership renewal products
  - Digital content delivery infrastructure

This module extends Odoo's standard product management with association-specific
functionality while maintaining full compatibility with Odoo Community 18.
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',                    # Core Odoo functionality
        'product',                 # Standard product management
        'mail',                    # Messaging and activities
        'ams_member_data',         # Member data structures
        'ams_product_types',       # Product type classification
    ],
    'data': [
        # Security files first
        'security/ir.model.access.csv',
        # View files
        'views/product_template_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True, 
    'sequence': 8,  # Layer 1 foundation module
}