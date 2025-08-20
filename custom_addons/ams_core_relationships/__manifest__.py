# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Relationships',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Partner relationships - employer/employee, household, dependents, emergency contacts',
    'description': """
AMS Core Relationships Module
=============================

Partner relationship management for professional associations with sophisticated
relationship tracking including bidirectional relationships, role-based access,
and comprehensive relationship types.

Key Features:
-------------
* Bidirectional relationship management (automatic inverse creation)
* Employer/employee tracking with organizational charts
* Household and family relationship management
* Emergency contact and dependent tracking
* Professional reference and networking relationships
* Relationship validation and conflict detection
* Temporal relationship tracking (start/end dates)
* Role-based relationship visibility and access control
* Comprehensive relationship reporting and analytics
* Integration with member profiles and audit logging

Relationship Types:
------------------
* Employment relationships (Employer/Employee, Supervisor/Subordinate)
* Family relationships (Spouse, Parent/Child, Sibling, Guardian)
* Household relationships (Household Member, Dependent)
* Emergency contacts (Primary/Secondary Emergency Contact)
* Professional relationships (Colleague, Mentor/Mentee, Referrer)
* Business relationships (Client, Vendor, Partner)

This module extends the AMS core base functionality to provide comprehensive
relationship management essential for professional associations.
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'ams_core_base',
        'contacts',
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/relationship_types.xml',
        'data/relationship_categories.xml',
        
        # Views
        'views/partner_relationship_views.xml',
        'views/res_partner_views.xml',
        'views/relationship_type_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo_relationships.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_core_relationships/static/src/css/relationships.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 11,
}