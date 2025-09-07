# -*- coding: utf-8 -*-
{
    'name': 'AMS Product Types',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Product classification and categorization system',
    'description': """
AMS Product Types
=================

This module provides foundational product classification and categorization:

* Product Type Management
  - Membership products (renewals, upgrades)
  - Event products (registrations, tickets)
  - Educational products (courses, training)
  - Publications (books, journals, newsletters)
  - Merchandise (apparel, branded items)
  - Certifications (exams, credentials)
  - Digital downloads (e-books, resources)

* Product Classification Features
  - Category-based organization
  - Member vs. non-member pricing support
  - Subscription product identification
  - Digital product handling
  - Inventory tracking requirements

* Foundation Features
  - Extensible classification system
  - Configurable product attributes
  - Integration with pricing systems
  - Audit trail support

This is a Layer 1 foundation module that provides core product classification
infrastructure for all other AMS modules dealing with products and services.

Key Features:
* Comprehensive product categorization
* Flexible pricing model support
* Digital and physical product handling
* Built-in validation and business rules
* User-friendly administrative interface
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/product_type_data.xml',
        # Views
        'views/product_type_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 4,
}