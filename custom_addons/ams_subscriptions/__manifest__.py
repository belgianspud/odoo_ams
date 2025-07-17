{
    'name': 'AMS Subscriptions',
    'version': '2.0.0',  # Updated version
    'category': 'Sales',
    'summary': 'Association Management System - Advanced Subscription Management',
    'description': """
        AMS Subscriptions Module
        ========================
        
        Advanced subscription management functionality for Association Management System (AMS).
        
        Features:
        - Membership subscriptions
        - Chapter subscriptions (regional add-ons)
        - Publication subscriptions (print/digital)
        - E-commerce integration
        - Automatic invoicing
        - Product integration
    """,
    'author': 'John Janis',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'sale', 
        'account', 
        'product',
        'website_sale',  # For e-commerce integration
        'point_of_sale'  # For POS integration
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/subscription_type_data.xml',  # New: Default subscription types
        'views/subscription_type_views.xml',  # New: Subscription type management
        'views/subscription_views.xml',
        'views/menu_views.xml',
        'views/product_views.xml',  # New: Product integration
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}