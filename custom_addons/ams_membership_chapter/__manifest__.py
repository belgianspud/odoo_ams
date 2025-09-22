{
    'name': 'Membership Chapter',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Support chapters/sections for AMS with meetings and financial tracking',
    'description': """
        Chapter management module that provides:
        - Define chapters (regional or special interest groups)
        - Link contacts and memberships to chapters
        - Assign chapter managers and officers
        - Track chapter membership statistics
        - Support hierarchical chapter structures
        - Chapter meeting management with RSVP system
        - Chapter financial tracking with budgets and transactions
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['membership_base', 'contacts', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/chapter_views.xml',
        'views/chapter_meetings_views.xml',
        'views/chapter_finance_views.xml',
        'data/meeting_email_templates.xml',
        'data/meeting_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}