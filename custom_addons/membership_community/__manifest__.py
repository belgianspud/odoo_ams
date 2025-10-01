# -*- coding: utf-8 -*-
{
    'name': 'Membership Community - Base',
    'version': '18.0.1.0.0',
    'category': 'Membership',
    'summary': 'Core Membership Management Infrastructure',
    'description': """
Membership Community - Base Module
===================================

Core membership management infrastructure that provides:

* Base membership category model
* Membership features and benefits framework
* Partner membership status tracking
* Subscription extensions for memberships
* Product template membership flag
* Security groups and access rights
* Core menu structure

This module is designed to be extended by specialized modules:
- membership_individual: Individual member types (student, retired, etc.)
- membership_organizational: Organizational memberships with seats
- membership_chapter: Chapter/section memberships

Note: Install specialized modules for specific membership types.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'subscription_management',
    ],
    'data': [
        # Security - Load first
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data files - Load before views
        'data/membership_category_data.xml',
        'data/membership_feature_data.xml',
        'data/membership_benefit_data.xml',
        'data/product_template_data.xml',
        'data/membership_cron.xml',
        'data/membership_email_templates.xml',
        
        # Core Views
        'views/membership_category_views.xml',
        'views/membership_feature_views.xml',
        'views/membership_benefit_views.xml',
        'views/product_template_views.xml',
        'views/subscription_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/membership_category_demo.xml',
        'demo/membership_feature_demo.xml',
        'demo/membership_benefit_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}