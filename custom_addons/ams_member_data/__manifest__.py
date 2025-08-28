{
    'name': 'AMS Member Data',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Foundation data layer for Association Management System',
    'description': '''
AMS Member Data Module
======================

The foundational data layer for the Association Management System that transforms 
Odoo's basic contact management into a comprehensive member database.

Key Features:
* Enhanced member profiles with association-specific fields
* Configurable member types and status tracking
* Automatic member ID generation
* Dual address support for members
* Organization relationship management
* Data quality controls for phone, email, and address validation
* Support for both individual and organization memberships

This module provides the core data structures that all other AMS modules depend on.
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'mail',
        'ams_system_config',  # Added dependency for foundation menus and config
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence_data.xml',
        'data/member_type_data.xml', 
        'data/member_status_data.xml',
        
        # Views
        'views/member_type_views.xml',
        'views/member_status_views.xml',
        'views/res_partner_individual_views.xml',
        'views/res_partner_organization_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 2,  # After ams_system_config
}