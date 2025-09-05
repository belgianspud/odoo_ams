# -*- coding: utf-8 -*-
{
    'name': 'AMS Member Data',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core member and organization data structures for Association Management System',
    'description': """
AMS Member Data - Foundation Module
=====================================

This module provides the foundational data structures for Association Management:

* Enhanced individual member profiles with demographics
* Organization member profiles with corporate details  
* Dual address management system
* Member ID generation system
* Legacy system integration fields
* Extended contact information management

This is a Layer 1 foundation module with no AMS dependencies.
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        # Views
        'views/res_partner_individual_views.xml',
        'views/res_partner_organization_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,
}