{
    'name': 'Membership Base',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core membership record keeping for AMS with directory and digital cards',
    'description': """
        Core membership management module that provides:
        - Membership records linked to contacts
        - Membership lifecycle tracking (start, end, paid-through dates)
        - Status management (Active, Grace, Lapsed, Cancelled)
        - Invoice linking and payment tracking
        - Member Directory for networking
        - Digital Membership Cards with QR codes
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['base', 'contacts', 'account', 'mail'],
    'external_dependencies': {'python': ['qrcode']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/membership_views.xml',
        'views/member_directory_views.xml',
        'views/membership_card_views.xml',
        'data/membership_cron.xml',
        'data/card_email_template.xml',
        'reports/membership_card_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}