{
    'name': 'Membership Event Pricing',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Event pricing based on membership levels with waitlist management and certificates',
    'description': """
        Event pricing and management module that provides:
        - Member vs non-member event pricing
        - Early bird and late registration pricing tiers
        - Membership level-based pricing rules
        - Integration with Odoo Events module
        - Automatic price calculation based on membership status
        - Waitlist management with priority system based on membership level
        - Event certificates and CEU/CPE credit tracking
        - Automated certificate generation and distribution
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['membership_level', 'event', 'website_event'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/event_pricing_views.xml',
        'views/event_waitlist_views.xml',
        'views/event_certificates_views.xml',
        'data/certificate_sequence.xml',
        'data/waitlist_email_templates.xml',
        'data/certificate_email_templates.xml',
        'data/waitlist_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}