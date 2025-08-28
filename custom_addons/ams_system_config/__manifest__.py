{
    'name': 'AMS System Config',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Global configuration management for Association Management System',
    'description': '''
AMS System Config Module
========================

Centralized configuration management for all Association Management System 
settings. Provides unified configuration interface that controls system-wide 
behaviors, default values, and feature enablement across all AMS modules.

Key Features:
* Centralized system-wide configuration management
* Member ID generation and formatting control
* Membership lifecycle policy settings (grace periods, renewals)
* Financial configuration (currency, fiscal year, revenue sharing)
* Feature toggle management for all AMS modules
* Portal access and communication defaults
* Integration settings for external systems
* Multi-environment configuration support
* Configuration validation and dependency checking
* Audit trail for all configuration changes

This module serves as the central control point for AMS system behavior, 
enabling administrators to configure membership policies, financial settings, 
feature toggles, and default values that affect all other AMS modules while 
ensuring consistent system operation.
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
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
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,
}