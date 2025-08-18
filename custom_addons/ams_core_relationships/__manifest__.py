# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Relationships',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Partner relationship management for AMS',
    'description': '''
Partner Relationship Management for AMS:
- Define and track partner-to-partner relationships
- Configurable relationship types with reciprocal mappings
- Household and organizational hierarchy management
- Relationship history and lifecycle tracking
- Bulk relationship import and management tools
- Foundation for relationship-based business logic

This module extends the AMS Core to provide comprehensive relationship
management capabilities between individuals and organizations.
    ''',
    'author': 'Your Organization',
    'website': 'https://your-organization.com',
    'depends': [
        'ams_core',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/relationship_types.xml',
        'data/relationship_sequences.xml',
        
        # Views
        'views/ams_relationship_type_views.xml',
        'views/ams_partner_relationship_views.xml',
        'views/res_partner_views.xml',
        'views/ams_household_views.xml',
        'views/relationship_menu.xml',
        
        # Wizards
        'wizard/relationship_bulk_import_views.xml',
        'wizard/household_merge_views.xml',
    ],
    'demo': [
        'demo/relationship_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_core_relationships/static/src/css/relationships.css',
            'ams_core_relationships/static/src/js/relationship_widget.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}