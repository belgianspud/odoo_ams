# -*- coding: utf-8 -*-
{
    'name': 'AMS Communication Module',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Member communication preferences and delivery tracking',
    'description': """
        AMS Communication Module - Implementation Documentation
        
        The AMS Communication module provides comprehensive communication
        preference management and delivery tracking for association members. It
        enables granular control over member communication consent, tracks all
        communication history, and provides the foundation for GDPR-compliant
        member communications across all channels.
        
        Key Features:
        - Granular communication preferences by type and category
        - Complete communication history and delivery tracking
        - GDPR compliance with consent documentation
        - Integration with Odoo mail templates and SMS
        - Multi-channel support (Email, SMS, Mail, Phone)
        - Campaign attribution and performance tracking
    """,
    'author': 'AMS Development Team',
    'website': 'https://www.ams-odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'sms',
        'ams_member_data',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/communication_types_data.xml',
        
        # Views
        'views/communication_preference_views.xml',
        'views/communication_log_views.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 2,
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
}