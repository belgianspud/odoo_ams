{
    'name': 'AMS Member Data',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Core member and organization data structures for AMS',
    'description': """
    AMS Member Data - Foundation Module
    
    This module provides the core data structures for Association Management System:
    - Individual member extensions to res.partner
    - Organization member extensions to res.partner  
    - Member ID generation and management
    - Basic member demographics and contact information
    - System integration fields for portal and legacy systems
    
    This is a foundational module with no business logic dependencies.
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        # Security files first
        'security/ir.model.access.csv',
        # Data files
        'data/ir_sequence_data.xml',
        # View files
        'views/res_partner_individual_views.xml',
        'views/res_partner_organization_views.xml',
        # Menu files last
        'views/ams_member_menus.xml',
    ],
    #'demo': [
    #    'demo/demo_member_data.xml',
    #],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,  # First in Layer 1
}