# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Privacy',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Privacy controls, consent tracking, data retention, GDPR compliance',
    'description': """
AMS Core Privacy Module
=======================

Privacy controls, consent tracking, data retention policies, and GDPR-style compliance 
features specifically designed for professional associations.

Key Features:
-------------
* Granular consent tracking and management
* GDPR/CCPA compliance tools and workflows
* Automated data retention policy enforcement
* Member data export and portability (Right to Data Portability)
* Privacy preference management
* Consent history and audit trails
* Data anonymization and deletion workflows
* Privacy impact assessment tools
* Consent renewal automation
* Cross-border data transfer compliance

Privacy Management:
------------------
* Marketing consent (email, SMS, direct mail)
* Directory listing consent and visibility controls
* Photo and image usage permissions
* Data sharing consent for partner organizations
* Research participation consent
* Event photography and recording consent
* Third-party integration consent
* Communication preference management

GDPR Compliance:
---------------
* Right to Access - Member data export wizard
* Right to Rectification - Profile update workflows
* Right to Erasure - Data deletion and anonymization
* Right to Restrict Processing - Processing limitation flags
* Right to Data Portability - Structured data export
* Right to Object - Opt-out mechanisms
* Data Protection Impact Assessments
* Consent withdrawal mechanisms

Data Retention:
--------------
* Configurable retention policies by data type
* Automated cleanup schedules and notifications
* Legal hold capabilities for litigation/investigations
* Archive and purge workflows
* Retention policy compliance reporting
* Data lifecycle management

This module provides the privacy foundation for all other AMS modules,
ensuring compliance with modern privacy regulations while maintaining
the functionality needed for effective association management.
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'ams_core_base',
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/consent_types.xml',
        'data/privacy_policies.xml',
        
        # Views
        'views/privacy_consent_views.xml',
        'views/data_retention_views.xml',
        'views/privacy_export_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo_privacy_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_core_privacy/static/src/css/privacy.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 12,
}