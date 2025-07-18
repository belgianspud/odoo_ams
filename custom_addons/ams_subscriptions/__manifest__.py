{
    'name': 'AMS Subscriptions',
    'version': '2.1.0',  # Updated version
    'category': 'Sales',
    'summary': 'Association Management System - Advanced Subscription Management with Renewals',
    'description': """
        AMS Subscriptions Module
        ========================
        
        Advanced subscription management functionality for Association Management System (AMS).
        
        Features:
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
        
        New in v2.1.0:
        - Enhanced product integration
        - Automatic subscription creation from sales orders
        - Renewal management with pending renewal status
        - Cron jobs for automatic renewal processing
        - Partner views with subscription tabs
        - Website and POS integration
        - Chapter auto-creation for memberships
        - Professional email templates for renewals
    """,
    'author': 'John Janis',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'sale', 
        'account', 
        'product',
        'website_sale',  # For e-commerce integration
        'point_of_sale',  # For POS integration
        'mail'  # For email templates
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
    
        # Data files
        'data/subscription_type_data.xml',
        'data/chapter_data.xml',
        'data/cron_data.xml',
        'data/email_templates.xml',
    
        # Views
        'views/subscription_type_views.xml',
        'views/chapter_views.xml',
        'views/subscription_views.xml',
        'views/product_views.xml',
        # 'views/partner_views.xml',  # Temporarily commented out
        'views/menu_views.xml',
    ],
    'demo': [
        # Demo data can be added here if needed
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['dateutil'],
    },
}