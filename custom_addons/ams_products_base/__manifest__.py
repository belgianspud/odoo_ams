# -*- coding: utf-8 -*-
{
    'name': 'AMS Products Base',
    'version': '18.0.2.0.0',
    'category': 'Association Management',
    'summary': 'Enhanced product data structures extending AMS Product Types',
    'description': """
AMS Products Base - Enhanced Product Module
==========================================

This module extends the AMS Product Types module with advanced association-specific 
product functionality:

* **Advanced Member Pricing**
  - Configurable pricing methods (fixed price, percentage discount, or both)
  - Automatic price calculations based on membership status  
  - Member savings tracking and display
  - Integration with ams_member_data for membership verification

* **Enhanced SKU Management**
  - Multiple SKU generation methods (auto from name, category-based, sequence, manual)
  - Category-specific SKU prefixes (MEM-, EVT-, EDU-, etc.)
  - Legacy SKU tracking for data migration
  - Automatic SKU synchronization with Odoo default_code

* **Digital Product Management**
  - Download URLs and file attachments
  - Access duration controls
  - Auto-fulfillment configuration
  - Digital content status tracking

* **Access Control & Restrictions**
  - Membership requirement enforcement
  - Membership level requirements
  - Chapter-specific product restrictions (future)
  - Public visibility controls

* **Advanced Fulfillment**
  - Multiple fulfillment methods (manual, auto-digital, auto-physical, event-based, subscription)
  - Custom delivery instructions
  - Fulfillment status tracking
  - Integration hooks for future fulfillment modules

This module extends ams_product_types and leverages enhanced product categories
while adding association-specific business logic and advanced features.
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
        'ams_member_data',      # For member status integration
        'ams_product_types'     # EXTENDS this module (required)
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 9,  # After ams_product_types (sequence 4)
}