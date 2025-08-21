# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Professional',
    'version': '18.0.1.0.0',
    'category': 'Association/Professional',
    'summary': 'Professional designations, specialties, and career tracking',
    'description': """
AMS Core Professional Module
============================

Extends the AMS Core Base with comprehensive professional designation and specialty management
specifically designed for professional associations.

Key Features:
-------------
* Professional designations (degrees, certifications, licenses, titles)
* Hierarchical specialty and practice area management
* License and certification tracking with expiry dates
* Continuing education requirements and tracking
* Professional networking profile fields
* Career progression and milestone tracking
* Industry-specific designation templates

Professional Association Types Supported:
-----------------------------------------
* Medical associations (MD, DO, RN, specialties)
* Legal associations (JD, Esq., practice areas)
* Engineering associations (PE, EIT, disciplines)
* Aviation associations (ATP, CFI, AMT)
* Business associations (CPA, MBA, consulting areas)
* Academic associations (PhD, research areas)

This module extends ams_core_base with professional-specific functionality
while maintaining the microservice architecture for flexibility.

Integration:
------------
* Seamlessly extends res.partner with professional fields
* Integrates with member profiles for complete professional tracking
* Provides foundation for other modules (billing, education, etc.)
* Supports multi-industry association management
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'ams_core_base',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/professional_data.xml',
        
        # Views
        'views/professional_designation_views.xml',
        'views/member_specialty_views.xml',
        'views/res_partner_views.xml',
        'views/member_profile_views.xml',
        'views/menus.xml',
    ],
    'demo': [
        'demo/demo_professional_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'sequence': 11,
}