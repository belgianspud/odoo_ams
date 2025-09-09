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
    - Member ID generation using existing ref field
    - Basic member demographics and contact information
    - Integration with Odoo's messaging and activity systems
    - Leverages existing Odoo fields (website, vat, industry_id, etc.)
    
    This is a foundational module optimized for Odoo Community 18 compatibility.
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',           # Core Odoo functionality
        'contacts',       # res.partner model and contact management
        'account',
        'mail',           # Messaging, activities, followers - essential for associations
    ],
    'data': [
        # Security files first
        'security/ir.model.access.csv',
        # Data files
        'data/ir_sequence_data.xml',
        # View files
        'views/res_partner_individual_views.xml',
        'views/res_partner_organization_views.xml'
        # Menu files last
        'views/ams_member_menus.xml',
    ],
    'demo': [
        'demo/demo_member_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,  # First in Layer 1
}