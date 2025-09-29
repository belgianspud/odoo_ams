# -*- coding: utf-8 -*-
{
    'name': 'Subscription Management',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage recurring subscriptions and billing',
    'description': """
Subscription Management Module
==============================

Features:
---------
* Subscription Plans and Products
* Customer Subscriptions
* Recurring Billing Automation
* Payment Processing
* Subscription Lifecycle Management
* Usage Tracking and Metering
* Customer Portal
* Analytics and Reporting
* Sales Order Integration
* Failed Payment Handling & Dunning

This module provides a complete subscription management system for Odoo Community.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'account',
        'product',
        'portal',
        'payment',
        'mail',
    ],
    'data': [
        'security/subscription_security.xml',
        'security/ir.model.access.csv',
        'data/subscription_data.xml',
        'data/subscription_cron.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_subscription_views.xml',
        'views/subscription_line_views.xml',
        'views/subscription_usage_views.xml',
        'views/subscription_menus.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/portal_templates.xml',
        'reports/subscription_reports.xml',
        'wizards/subscription_wizard_views.xml',
    ],
    'demo': [
        'demo/subscription_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'subscription_management/static/src/css/subscription.css',
            'subscription_management/static/src/js/subscription_widget.js',
        ],
        'web.assets_frontend': [
            'subscription_management/static/src/css/portal.css',
            'subscription_management/static/src/js/portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}