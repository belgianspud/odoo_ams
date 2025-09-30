# -*- coding: utf-8 -*-
{
    'name': 'Membership Management',
    'version': '18.0.1.0.0',
    'category': 'Association',
    'summary': 'Manage memberships, member types, and member payments',
    'description': """
Community Membership Management Module
=====================================

This module provides comprehensive membership management functionality including:
* Member registration and management
* Multiple membership types and plans
* Payment tracking and invoicing
* Member portal access
* Membership renewal management
* Reporting and analytics
* Integration with contacts and accounting
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'depends': ['base', 'mail', 'portal', 'account', 'sale'],
    'data': [
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        'data/membership_data.xml',
        'views/membership_type_views.xml',
        'views/membership_views.xml',
        'views/res_partner_views.xml',
        'views/membership_payment_views.xml',
        'views/membership_menus.xml',
        'views/portal_templates.xml',
        'reports/membership_reports.xml',
        'wizard/membership_invoice_wizard_views.xml',
    ],
    'demo': [
        'demo/membership_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}