{
    'name': 'Membership Communications',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Centralized communication management with push notifications and analytics',
    'description': """
        Communication management module that provides:
        - Multi-channel communication (Email, SMS, Push Notifications)
        - Campaign management and scheduling
        - Template library with personalization
        - Automated communication workflows
        - Delivery tracking and analytics
        - Member segmentation and targeting
        - Push notification campaigns for mobile apps
        - Advanced analytics and reporting with engagement insights
        - Performance dashboards and trend analysis
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['membership_chapter', 'mail', 'sms'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/communications_views.xml',
        'views/push_notifications_views.xml',
        'views/communication_analytics_views.xml',
        'data/communications_cron.xml',
        'data/push_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}