# -*- coding: utf-8 -*-
{
    'name': 'AMS Communication Preferences',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Communication preference management and consent tracking for Association Management System',
    'description': """
AMS Communication Preferences - Foundation Module
===============================================

This module provides comprehensive communication preference management for associations:

* Member communication preferences by channel (email, SMS, mail, phone)
* Category-based preferences (marketing, membership, events, education, fundraising, governance)
* Consent tracking with source and IP address logging for GDPR compliance
* GDPR-compliant opt-in/opt-out management with audit trail
* Integration with member profiles for seamless preference management
* Email bounce tracking and automatic disable functionality
* Global communication opt-out capabilities
* Communication permission checking and validation
* Portal integration for member self-service preference management

This is a Layer 1 foundation module that extends member data with communication preferences.

Key Features:
* Granular preference control by communication type and category
* Full GDPR compliance with consent tracking and audit trails
* Member self-service preference management via portal
* Staff override capabilities with complete audit trail
* Integration points for communication automation systems
* CAN-SPAM compliance support and validation
* Automatic email bounce handling and list hygiene
* Communication permission validation before sending
* Comprehensive reporting on communication preferences and compliance
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'ams_member_data',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/communication_types_data.xml',
        # Views
        'views/communication_preference_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 6,
    'external_dependencies': {
        'python': [],
    },
}