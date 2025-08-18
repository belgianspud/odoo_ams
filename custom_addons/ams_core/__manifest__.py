# -*- coding: utf-8 -*-
{
    'name': 'AMS Core',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core foundation for Association Management System',
    'description': '''
Core AMS foundation providing:
- Basic partner extensions with member IDs and status tracking
- Simple contact role system for organizational relationships
- Communication preference tracking and management
- Basic audit logging framework for compliance
- Core security groups and permissions
- Foundation infrastructure for all other AMS modules

This module establishes the essential building blocks needed for association
management while maintaining clean separation of concerns and minimal dependencies.
    ''',
    'author': 'Your Organization',
    'website': 'https://your-organization.com',
    'depends': [
        'base',
        'contacts',
        'mail',
    ],
    'data': [
        # Security - must be loaded first
        'security/ams_security.xml',
        'security/ir.model.access.csv',
        
        # Data - core sequences and configuration
        'data/member_sequences.xml',
        'data/contact_roles.xml',
        'data/communication_preferences.xml',
        
        # Views - user interface
        'views/res_partner_views.xml',
        'views/ams_contact_role_views.xml',
        'views/ams_communication_preference_views.xml',
        'views/ams_audit_log_views.xml',
        'views/ams_menu.xml',
    ],
    'demo': [
        'demo/ams_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_core/static/src/css/ams_core.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}