# -*- coding: utf-8 -*-
{
    'name': 'AMS Membership Core',
    'version': '17.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core membership and subscription management with chapter support',
    'description': '''
Association Membership System - Core Module
===========================================

Comprehensive membership and subscription management system that handles:

* **Membership Management**: Individual membership records with lifecycle tracking
* **Chapter Memberships**: Local and regional chapter memberships (unlimited per member)
* **Subscription Products**: Publications, events, and other recurring services
* **Renewal Management**: Automated and manual renewal processing
* **Member Benefits**: Flexible benefit system with usage tracking
* **Portal Access**: Member self-service portal with membership management
* **Financial Integration**: Integration with sales, invoicing, and payment processing

Key Features:
* Unified subscription product framework
* Multiple active chapter memberships per member
* Single active regular membership per member
* Automated renewal processing and reminders
* Member portal with self-service capabilities
* Flexible benefit management system
* Mass renewal processing tools
* Comprehensive reporting and analytics

Chapter Management:
* Geographic and specialty-based chapters
* Multiple access levels (basic, premium, leadership, officer)
* Chapter-specific benefits and resources
* Local event access and networking
* Document libraries and training materials
''',
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'product',
        'sale',
        'account',
        'website',
        'payment',
        'ams_foundation',  # Depends on foundation for member data
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        
        # Data Files
        'data/sequences.xml',
        'data/membership_data.xml',
        'data/cron_data.xml',
        'data/portal_groups.xml',
        
        # Views
        'views/product_template_views.xml',
        'views/ams_membership_views.xml',
        'views/ams_subscription_views.xml',
        'views/ams_benefit_views.xml',
        'views/ams_renewal_views.xml',
        'views/res_partner_views.xml',
        
        # Portal Templates
        'views/portal_membership_templates.xml',
        
        # Wizards
        'wizards/mass_renewal_wizard_views.xml',
        'wizards/membership_transfer_wizard_views.xml',
        
        # Menus (load last)
        'views/membership_menu.xml',
    ],
    'demo': [
        # Demo data if needed
    ],
    'assets': {
        'web.assets_frontend': [
            # Portal-specific CSS/JS if needed
        ],
        'web.assets_backend': [
            # Backend-specific CSS/JS if needed
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
    'external_dependencies': {
        'python': ['dateutil'],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}