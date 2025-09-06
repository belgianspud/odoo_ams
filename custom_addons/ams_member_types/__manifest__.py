# -*- coding: utf-8 -*-
{
    'name': 'AMS Member Types',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Member classification and status definitions',
    'description': """
AMS Member Types
================

This module provides foundational member classification and status management:

* Member Type Management
  - Individual vs Organization classification
  - Eligibility rules and age restrictions
  - Verification requirements
  - Auto-approval settings

* Member Status Management
  - Lifecycle status definitions
  - Active/inactive member classification
  - Renewal and purchase permissions
  - Status color coding for visual management

* Foundation Features
  - Extensible classification system
  - Configurable eligibility rules
  - Audit trail support
  - Integration with other AMS modules

This is a Layer 1 foundation module that provides core member classification
infrastructure for all other AMS modules.

Key Features:
* Flexible member type definitions
* Comprehensive status lifecycle management
* Built-in validation and business rules
* User-friendly administrative interface
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/member_type_data.xml',
        'data/member_status_data.xml',
        # Views
        'views/member_type_views.xml',
        'views/member_status_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 3,
}