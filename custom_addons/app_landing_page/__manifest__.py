{
    'name': 'App Landing Page',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Custom landing page with tile display of installed apps',
    'description': """
        Creates a landing page showing all installed Odoo apps in a tile format.
        Users can click on tiles to navigate to the respective apps.
    """,
    'author': 'Your Company',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/landing_page_views.xml',
        'views/landing_page_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'app_landing_page/static/src/css/landing_page.css',
            'app_landing_page/static/src/js/landing_page.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}