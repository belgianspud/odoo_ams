# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Base',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'sequence': 10,
    'summary': 'Foundation layer for Association Management System',
    'description': """
AMS Core Base Module
===================

This module provides the foundational layer for the Association Management System (AMS).
It extends Odoo's standard Contacts and Users to be association-aware with configurable
fields and relationships suitable for professional associations across industries.

Key Features:
-----------
* Industry-configurable contact and account fields
* Member ID assignment and tracking  
* Professional relationship management (Employee/Employer, Parent/Child Organization)
* Multi-address support (billing, shipping, residential, corporate)
* Configurable lookup values by industry type
* AMS security roles (Guest, Member, Company POC, Staff, Admin)
* Safe contact deduplication and merging
* Generic configuration framework for association settings

Supported Industries:
-------------------
* Healthcare/Medical
* Aviation  
* Legal
* Engineering
* And other professional associations

This module serves as the foundation that other AMS modules build upon.
It contains no hard-coded values - all behavior is driven by configuration.
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts', 
        'mail',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        
        # Data  
        'data/ams_config_data.xml',
        'data/ams_lookup_data.xml',
        
        # Views
        'views/menus.xml',
        'views/ams_config_views.xml', 
        'views/ams_lookup_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': None,
    'external_dependencies': {
        'python': [],
    },
}