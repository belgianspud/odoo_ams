# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Professional',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Professional designations, specialties, licenses, and career tracking',
    'description': """
AMS Core Professional Module
============================

This module extends the AMS Core Base with professional-specific functionality:

Professional Features:
* Professional designations and certifications
* Member specialties and areas of expertise  
* License and certification number tracking
* Professional networking profiles (LinkedIn, ORCID, etc.)
* Continuing education hours tracking
* Career progression monitoring

Integration:
* Extends res.partner with professional fields
* Extends ams.member.profile with career data
* Provides professional data templates
* Professional designation and specialty management

Dependencies:
* Requires ams_core_base
* Extends Odoo contacts module
""",
    'author': 'AMS Development Team',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    'depends': [
        'ams_core_base',
        'contacts',
        'mail',
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
    ],
    'demo': [
        # Demo data can be added here if needed
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 102,  # Load after ams_core_base (sequence 101)
}