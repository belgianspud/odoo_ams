{
    'name': 'Membership Level',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Define tiers of membership for AMS with level changes and benefits tracking',
    'description': """
        Membership level management module that provides:
        - Define membership tiers (Individual, Student, Organization, etc.)
        - Set duration and pricing for each level
        - Link to Odoo Products for billing integration
        - Level upgrade/downgrade workflow with proration
        - Member benefits tracking and usage monitoring
        - Manage level-specific benefits and restrictions
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'depends': ['membership_base', 'product', 'sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/level_views.xml',
        'views/level_upgrade_views.xml',
        'views/member_benefits_views.xml',
        'data/level_change_email_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}