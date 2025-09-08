{
    'name': 'Association Business Automation',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Visual business automation rules for association management',
    'description': '''
Association Business Automation
===============================

Create powerful automation rules for association management without coding.

Key Features:
• Visual rule builder for membership workflows
• Automated member lifecycle management
• Event and meeting automation
• Dues and payment processing rules
• Committee and role assignment automation
• Communication triggers
• Reporting and compliance automation

Perfect for:
• Membership organizations
• Professional associations
• Non-profits
• Clubs and societies
• Industry groups
    ''',
    'author': 'Your Association Tech Team',
    'website': 'https://your-association.org',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'contacts',
        # Add your association management base modules here
        # 'association_membership',  # If you have a membership module
        # 'association_events',      # If you have an events module
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/automation_security.xml',
        'data/automation_templates.xml',
        'views/automation_views.xml',
        'views/automation_templates_views.xml',
        'wizards/automation_wizard_views.xml',
        'views/automation_menus.xml',
    ],
    'demo': [
        'demo/association_automation_demo.xml',
    ],
    'external_dependencies': {
        'python': [],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 100,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}