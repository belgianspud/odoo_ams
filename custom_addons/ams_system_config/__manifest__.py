# -*- coding: utf-8 -*-
{
    'name': 'AMS System Configuration',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Global AMS configuration and system settings',
    'description': """
AMS System Configuration
========================

This module provides global configuration settings for the Association Management System:

* Member ID generation settings
* Membership lifecycle defaults
* Portal and communication preferences
* Financial configuration (fiscal year, currency)
* Feature toggles for AMS modules
* System-wide defaults and policies

This is a Layer 1 foundation module that provides configuration infrastructure
for all other AMS modules.

Key Features:
* Centralized system configuration
* Member ID formatting control
* Default grace periods and renewal windows
* Feature toggle management
* Fiscal year and currency settings
* Portal and communication defaults
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'ams_member_data',  # Add dependency to use existing AMS menu
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ams_config_data.xml',
        # Views
        'views/ams_config_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 3,  # After ams_member_data
}