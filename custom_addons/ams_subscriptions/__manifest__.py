{
    'name': 'AMS Subscriptions',
    'version': '18.0.1.0.0',  # Updated for Odoo 18
    'category': 'Association Management',
    'summary': 'Subscription management for associations - memberships, chapters, publications',
    'description': """
AMS Subscriptions Module
========================

This module provides comprehensive subscription management for associations including:

* Membership subscriptions with different tiers
* Chapter subscriptions for local/regional groups
* Publication subscriptions (magazines, newsletters, etc.)
* Recurring billing and automatic renewals
* Integration with website and ecommerce
* Member portal for subscription management
* Flexible pricing and discount structures
* Grace periods and renewal notifications

Features:
---------
* Multiple subscription types and plans
* Automated recurring invoicing
* Website integration for self-service
* Member dashboard
* Renewal reminders and notifications
* Proration handling
* Subscription analytics and reporting
    """,
    'author': 'Your AMS Team',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'account',
        'website',
        'website_sale',
        'portal',
        'mail',
        'contacts',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data files (load order matters)
        'data/product_category_data.xml',
        'data/subscription_data.xml',
        'data/subscription_templates_data.xml',
        'data/ir_cron_data.xml',  # Add cron jobs
        'data/website_menu.xml',
        
        # Views
        'views/menu.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/website_subscription_templates.xml',
        
        # Wizards
        'wizard/subscription_renewal_wizard.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ams_subscriptions/static/src/css/subscription_style.css',
            'ams_subscriptions/static/src/js/subscription_widget.js',
        ],
        'web.assets_backend': [
            'ams_subscriptions/static/src/css/subscription_style.css',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}