# -*- coding: utf-8 -*-
{
    'name': 'AMS Foundation',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core member data structures and management foundation',
    'description': """
AMS Foundation Module
====================

This module provides the core foundation for Association Management System (AMS):

Features:
---------
* Extended partner model for member management
* Configurable member types and classifications
* Automated member status workflow with grace periods
* Sequential member numbering with configurable prefix
* Member engagement scoring framework
* Portal user management and access controls
* Global AMS configuration settings

Technical:
----------
* Extends res.partner for seamless integration
* Configurable status transitions and grace periods
* Automated cron jobs for status management
* Security groups and access controls
* Portal integration for member self-service

Dependencies:
-------------
* Base Odoo modules: contacts, portal, mail
* No external dependencies required
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'portal',
        'mail',
        'website',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
    
        # Data (basic data only)
        'data/sequences.xml',
        'data/settings_data.xml',
        'data/member_types_data.xml',
    
        # Views (load actions before menus)
        'views/ams_settings_views.xml',
        'views/ams_member_type_views.xml',
        'views/res_partner_views.xml',
        'views/res_engagement_rule_views.xml',
    
        # Data that depends on models being loaded
        'data/cron_jobs.xml',  # <- Move this after views
    
        # Wizards
        'wizards/portal_user_wizard_views.xml',
    
        # Menus (load after all actions are defined)
        'views/menu_views.xml',
    ],
    'demo': [
        # Demo data files would go here
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 10,
    'post_init_hook': 'post_init_hook',
}