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
        
        # Data
        'data/sequences.xml',
        'data/settings_data.xml',
        'data/member_types_data.xml',
        'data/cron_jobs.xml',
        
        # Views
        'views/menu_views.xml',
        'views/ams_settings_views.xml',
        'views/ams_member_type_views.xml',
        'views/res_partner_views.xml',
        
        # Wizards
        'wizards/portal_user_wizard_views.xml',
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


def post_init_hook(cr, registry):
    """
    Post-installation hook to set up initial data and configurations.
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Set up default member numbering sequence if not exists
    sequence = env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
    if not sequence:
        env['ir.sequence'].create({
            'name': 'Member Number Sequence',
            'code': 'ams.member.number',
            'prefix': 'M',
            'padding': 6,
            'number_increment': 1,
            'number_next_actual': 1,
        })
    
    # Initialize default AMS settings if not exists
    settings = env['ams.settings'].search([], limit=1)
    if not settings:
        env['ams.settings'].create({
            'name': 'Default AMS Settings',
            'member_number_prefix': 'M',
            'grace_period_days': 30,
            'suspend_period_days': 60,
            'terminate_period_days': 90,
            'auto_create_portal_users': True,
        })