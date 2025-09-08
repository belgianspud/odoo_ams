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
* Consent tracking with source and IP address logging
* GDPR-compliant opt-in/opt-out management
* Integration with member profiles for seamless preference management
* Audit trail for preference changes and compliance reporting

This is a Layer 1 foundation module that extends member data with communication preferences.

Key Features:
* Granular preference control by communication type and category
* Compliance-ready consent tracking
* Member self-service preference management
* Staff override capabilities with audit trail
* Integration points for communication automation
* GDPR and CAN-SPAM compliance support
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
}