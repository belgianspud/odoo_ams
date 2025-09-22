{
    'name': 'Subscription Base',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Recurring subscription management for AMS with payment plans and change management',
    'description': """
        Subscription management module that provides:
        - Subscription plans with products, duration, and pricing
        - Subscription records linked to members
        - Automatic renewal logic with invoice generation
        - Status tracking (Active, Grace, Lapsed, Cancelled)
        - Configurable auto-renewal settings
        - Payment plans with installment options
        - Mid-term subscription changes with proration
        - Change approval workflows
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['ams_membership_level', 'sale', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/subscription_views.xml',
        'views/payment_plans_views.xml',
        'views/subscription_changes_views.xml',
        'data/subscription_cron.xml',
        'data/installment_email_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}