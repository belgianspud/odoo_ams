{
    'name': 'AMS Subscriptions',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Association Management System - Subscription Management',
    'description': """
        AMS Subscriptions Module
        ========================
        
        This module provides basic subscription management functionality for 
        Association Management System (AMS).
        
        Features:
        - Basic subscription management
        - Member subscription tracking
        - Simple subscription plans
    """,
    'author': 'Your Name',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/subscription_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}