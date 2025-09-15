# -*- coding: utf-8 -*-
{
    'name': 'AMS Products Base',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Simple AMS product integration layer',
    'description': """
AMS Products Base - Simplified Integration Layer
===============================================

This module provides a clean integration layer between Odoo's native product 
system and the AMS modules, focusing on essential functionality:

* **Category-Driven Configuration**
  - Auto-detect AMS products from enhanced categories (ams_product_types)
  - Inherit pricing, digital, and inventory settings from categories
  - Simple onchange behavior to apply category defaults

* **Member Pricing Integration**
  - Calculate member pricing from category discount percentages
  - Integration with ams_member_data for membership status checking
  - Partner-specific pricing methods for sales integration

* **Essential Digital Product Support**
  - Basic digital content fields (URL and file attachment)
  - Digital content availability checking
  - Simple validation for digital products

* **Membership Requirements**
  - Auto-detect membership requirements from categories
  - Purchase permission checking based on membership status
  - Integration hooks for other modules

* **Simple SKU Management**
  - Auto-generate SKUs from product names when needed
  - Use Odoo's native default_code field
  - Legacy system integration support

This simplified approach leverages existing modules rather than duplicating 
functionality, making it a clean foundation for other AMS modules to build upon.

Key Design Principles:
- Leverage ams_product_types for category-driven behavior
- Integrate with ams_member_data for membership logic  
- Use Odoo native features where possible
- Provide hooks for specialized modules
- Keep the UI simple and focused

Dependencies:
- ams_member_data: For membership status integration
- ams_product_types: For enhanced category functionality
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
        'ams_member_data',      # For membership status integration
        'ams_product_types'     # For enhanced category functionality
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [
        'demo/demo_ams_products.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True, 
    'sequence': 10,  # After core AMS modules
}