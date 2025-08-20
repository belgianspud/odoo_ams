# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Base',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Foundation layer - member IDs, demographics, security, audit logging',
    'description': """
AMS Core Base Module
====================

Foundation layer that makes Odoo "association-aware" with core partner extensions,
member IDs, basic demographics, professional designations, and security infrastructure.

Key Features:
-------------
* Member ID generation with configurable sequences
* Extended partner model for individuals and organizations
* Professional designation and specialty tracking
* Member categories and career stage management
* Comprehensive audit logging
* Association-specific security groups
* Configurable demographic fields
* Universal contact methods and preferences

This module is the foundation that all other AMS modules depend on.
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts', 
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/member_id_sequence.xml',
        'data/member_categories.xml',
        'data/professional_data.xml',
        'data/default_groups.xml',
        
        # Views
        'views/res_partner_views.xml',
        'views/member_profile_views.xml',
        'views/professional_designation_views.xml',
        'views/member_specialty_views.xml',
        'views/audit_log_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo_partners.xml',
        'demo/demo_member_profiles.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_core_base/static/src/css/ams_core.css',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'sequence': 10,
}