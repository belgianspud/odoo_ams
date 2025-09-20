# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    'name': 'Membership Core',
    'version': '18.0.1.0.0',
    'category': 'Operations/Membership',
    'summary': 'Foundation membership management system',
    'description': '''
        Core membership management functionality including:
        * Membership types and categories
        * Basic membership records and lifecycle
        * Partner integration
        * Foundation for all membership modules
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.ams-software.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'mail',
        'contacts',
        'website'
    ],
    'data': [
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        'data/membership_sequence.xml',
        'data/membership_types_basic.xml',
        'data/email_templates_basic.xml',
        'data/membership_cron.xml',
        'views/membership_type_views.xml',
        'views/membership_membership_views.xml',
        'views/res_partner_views.xml',
        'views/membership_menus.xml',
        'wizard/membership_wizard_views.xml',
    ],
    'demo': [
        'demo/membership_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'membership_core/static/src/css/membership_core.css',
            'membership_core/static/src/js/membership_core.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },
    'post_init_hook': None,
    'uninstall_hook': None,
}