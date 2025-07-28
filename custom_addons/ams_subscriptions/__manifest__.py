{
    'name': 'AMS Subscriptions',
    'version': '18.0.2.1.0',  # Updated version
    'category': 'Association Management',
    'summary': 'Association Management System - Advanced Subscription Management with Renewals',
    'description': """
        AMS Subscriptions Module
        ========================
        
        Advanced subscription management functionality for Association Management System (AMS).
        
        Key Features:
        - Membership, chapter, and publication subscriptions
        - Recurring subscriptions with auto-renewal
        - Automatic renewal invoice generation
        - E-commerce integration (Website & POS)
        - Product-based subscription creation
        - Chapter auto-creation for memberships
        - Comprehensive renewal management
        - Member portal integration
        - Automated cron jobs for renewal processing
        - Partner subscription tracking
        - Email notifications for renewals and activations
        - Grace, suspend, and termination lifecycle management
        - Financial integration with invoicing
        
        Enhanced in v2.1.0:
        - Enhanced product integration
        - Automatic subscription creation from sales orders
        - Renewal management with pending renewal status
        - Advanced cron jobs for automatic renewal processing
        - Enhanced partner views with subscription analytics
        - Website and POS integration
        - Chapter auto-creation for memberships
        - Professional email templates for renewals
        - Subscription lifecycle management
        - Financial transaction integration
    """,
    'author': 'Your AMS Development Team',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'sale', 
        'account', 
        'product',
        'contacts',
        'website_sale',  # For e-commerce integration
        'point_of_sale',  # For POS integration
        'mail',  # For email templates
        'portal',  # For customer portal
    ],
    'data': [
        # Security
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
    
        # Data files (load first)
        'data/subscription_type_data.xml',
        'data/chapter_data.xml',
        'data/cron_data.xml',
        'data/email_templates.xml',
        'data/subscription_rules_data.xml',
    
        # Views (load after data)
        'views/subscription_type_views.xml',
        'views/chapter_views.xml',
        'views/subscription_views.xml',
        'views/product_views.xml',
        'views/partner_views.xml',
        'views/subscription_renewal_views.xml',
        'views/menu_views.xml',
        
        # Reports
        'reports/subscription_reports.xml',
        
        # Portal templates
        'views/portal_templates.xml',
        'views/website_templates.xml',
    ],
    'demo': [
        'demo/subscription_demo_data.xml',
    ],
    ''''assets': {
        'web.assets_backend': [
            'ams_subscriptions/static/src/css/subscription_dashboard.css',
            'ams_subscriptions/static/src/js/subscription_widgets.js',
        ],
        'web.assets_frontend': [
            'ams_subscriptions/static/src/css/portal_subscriptions.css',
            'ams_subscriptions/static/src/js/subscription_portal.js',
        ],
    },'''
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['dateutil'],
    },
}