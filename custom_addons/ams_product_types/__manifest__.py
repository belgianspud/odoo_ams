# -*- coding: utf-8 -*-
{
    'name': 'AMS Product Types',
    'version': '18.0.2.0.0',
    'category': 'Association Management',
    'summary': 'Enhanced product categories with AMS-specific functionality',
    'description': """
AMS Product Types - Enhanced Product Category System
===================================================

This module enhances Odoo's standard product categories with AMS-specific functionality:

* **Enhanced Product Categories**
  - AMS-specific category types (membership, event, education, etc.)
  - Category-driven product attributes and defaults
  - Automatic product configuration based on category selection
  - Smart business rules for digital, subscription, and inventory products

* **Category-Based Product Classification**
  - Membership products (renewals, upgrades)
  - Event products (registrations, tickets)
  - Educational products (courses, training)
  - Publications (books, journals, newsletters)
  - Merchandise (apparel, branded items)
  - Certifications (exams, credentials)
  - Digital downloads (e-books, resources)

* **Automatic Product Configuration**
  - Member vs. non-member pricing support
  - Subscription product identification
  - Digital product handling
  - Inventory tracking requirements
  - Service vs stockable product type setting

* **Enhanced Category Management**
  - Category-specific product counts and statistics
  - Bulk product creation from categories
  - Category-based product filtering and search
  - Rich category summary and attribute display

* **Foundation Features**
  - Extensible category attribute system
  - Configurable product defaults per category
  - Integration with Odoo's native category features
  - Audit trail and tracking support

Key Benefits:
* Single classification system using enhanced product categories
* No separate product type model to maintain
* Leverages Odoo's native category hierarchy and features
* Simplified architecture with category-driven defaults
* Better performance through native Odoo category indexing

Version 2.0 Changes:
* Removed separate ams.product.type model
* Enhanced product.category with AMS-specific fields
* Simplified architecture using native Odoo categories
* Better integration with Odoo's existing category features
* Improved performance through native category relationships
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'mail',
        'stock',      # For route and fulfillment features
        'sale',       # For product views and menu integration
        'account',    # For accounting fields
        'uom',        # For unit of measure
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data - Create enhanced categories
        'data/enhanced_category_data.xml',
        # Views - Enhanced category management
        'views/product_category_enhanced_views.xml',
        # Views - Product template extensions
        'views/product_template_ams_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 4,
}