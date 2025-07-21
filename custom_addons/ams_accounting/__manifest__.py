{
    'name': 'AMS Accounting - Full Accounting Kit',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete Accounting Features for Association Management System',
    'description': """
AMS Accounting Module
=====================

Complete accounting functionality adapted for Association Management Systems.
Built specifically for Odoo 18 with seamless AMS integration.

Core Features:
- Member financial management
- Subscription accounting integration
- Payment plan management
- Chapter financial tracking
- Credit management system
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'mail',
        'ams_subscriptions',
        'ams_module_manager',
    ],
    'data': [
        # Views only - ultra minimal
        'views/dashboard_views.xml',
        'views/accounting_menu.xml',
        
        # Our 5 new view files
        'views/ams_member_financial_views.xml',
        'views/ams_subscription_accounting_views.xml', 
        'views/ams_payment_plan_views.xml',
        'views/ams_chapter_financial_views.xml',
        'views/ams_credit_management_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,
}