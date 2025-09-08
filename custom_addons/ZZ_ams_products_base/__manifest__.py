{
    'name': 'AMS Products Base',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Core product data structures and member pricing for Association Management System',
    'description': '''
AMS Products Base Module
========================

Transforms Odoo's standard product management into a comprehensive association-focused 
commerce system with member-specific pricing, digital product delivery, and 
association-specific product categorization.

Key Features:
* Member vs. Non-Member dual pricing structure
* Digital product delivery with secure download links
* Association-specific product categories (merchandise, publications, certifications, etc.)
* Chapter-specific product restrictions (placeholder for future ams_chapters_core)
* Integration with Odoo's inventory management
* Access control based on membership status
* Automatic member discount calculations

This module provides the foundation for all association commerce activities, from 
simple merchandise sales to complex certification packages and digital downloads.
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',  # For inventory integration
        'account',  # For pricing and monetary fields
        'ams_member_data',  # Required for member pricing logic
    ],
    'data': [
        # Data files first (including sample data that might create model records)
        'data/product_types_data.xml',
        
        # Security files after data
        'security/ir.model.access.csv',
        
        # Views last
        'views/product_standard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 8,  # Layer 2 - Core Business Entities
}