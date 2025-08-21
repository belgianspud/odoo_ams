# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Base',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Foundation layer - member IDs, basic demographics, security',
    'description': """
AMS Core Base Module
====================

Foundation layer that makes Odoo "association-aware" with core partner extensions,
member IDs, basic demographics, and security infrastructure.

This module provides ONLY the essential functionality for professional associations:

Core Features:
--------------
* Member ID generation with configurable sequences
* Basic member status tracking (active, lapsed, prospect, etc.)
* Extended partner model with association-specific fields
* Simple member profile for extended demographics
* Member categories and classification
* Core security groups (member, staff, admin)
* Professional association contact preferences

Professional Association Focus:
-------------------------------
* Medical associations (doctors, nurses, specialists)
* Legal associations (attorneys, paralegals, judges) 
* Engineering associations (PE, civil, mechanical, etc.)
* Aviation associations (pilots, mechanics, controllers)
* Business associations (CPAs, consultants, executives)
* Academic associations (researchers, educators)

This is the foundation module that all other AMS modules depend on.
Additional functionality is available through complementary modules:

* Professional designations & specialties → ams_core_professional
* Audit logging & compliance → ams_core_audit  
* Privacy & consent management → ams_core_privacy
* Partner relationships → ams_core_relationships
* Communication preferences → ams_core_communications
* Duplicate detection → ams_core_deduplication
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts', 
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/member_id_sequence.xml',
        'data/member_categories.xml',
        'data/default_groups.xml',
        
        # Views
        'views/res_partner_views.xml',
        'views/member_profile_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'sequence': 10,
}