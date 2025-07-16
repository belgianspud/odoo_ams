{
    'name': 'AMS Module Manager',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Hide unnecessary modules and organize AMS interface',
    'description': """
        This module customizes the Odoo interface for Association Management Systems by:
        - Hiding Enterprise-only modules
        - Hiding irrelevant community modules
        - Organizing remaining modules into AMS-focused categories
    """,
    'author': 'Your AMS Development Team',
    'website': '',
    'depends': ['base', 'web'],
    'data': [
        'data/ir_module_module_data.xml',
        'views/apps_menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}