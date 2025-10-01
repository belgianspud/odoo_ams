# -*- coding: utf-8 -*-
{
    'name': 'Membership Community',
    'version': '18.0.1.0.0',
    'category': 'Membership',
    'summary': 'Association Management System - Membership & Community Features',
    'description': """
Membership Community Module
===========================

Complete Association Management System (AMS) for managing memberships, 
member categories, benefits, and features.

Key Features:
------------
* Individual and Organizational Memberships
* Chapter/Section Memberships with Primary Membership Requirements
* Member Categories with Eligibility Requirements
* Membership Benefits Management
* Membership Features and Access Control
* Portal Access Levels
* Professional Features (Credentials, CE Tracking, Designations)
* Organizational Seats Management
* Member Directory
* Membership Approval Workflows
* Eligibility Verification
* Upgrade/Downgrade Paths
* Financial Tracking

Integration:
-----------
* Extends subscription_management module for billing and renewals
* Integrates with Odoo contacts and invoicing
* Portal integration for member self-service

    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'subscription_management',
    ],
    'data': [
        # Security
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/membership_data.xml',
        
        # Views - Order matters for dependencies
        'views/membership_category_views.xml',
        'views/membership_feature_views.xml',
        'views/membership_benefit_views.xml',
        'views/product_template_views.xml',
        'views/subscription_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        
        # Wizards
        # 'wizard/membership_wizard_views.xml',
        # 'wizard/membership_rejection_wizard_views.xml',
        
        # Reports
        # 'reports/membership_reports.xml',
    ],
    'demo': [
        # 'demo/membership_demo.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}