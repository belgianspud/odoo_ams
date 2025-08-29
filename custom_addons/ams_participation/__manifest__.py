{
    'name': 'AMS Participation',
    'version': '1.0.0',
    'category': 'Association Management',
    'summary': 'Core participation tracking and lifecycle management',
    'description': '''
AMS Participation Module
========================

Core transactional layer for tracking all types of member participations within 
the association. Provides fundamental participation record structure that underpins 
membership instances, committee positions, chapter memberships, and other 
association engagement activities.

Key Features:
* Complete participation lifecycle management from prospect to termination
* Multiple participation type support (membership, chapter, committee positions)
* Comprehensive status workflow with automated processing
* Full audit trail and history tracking for all participation changes
* Billing integration with invoice and subscription relationships
* Cancellation reason tracking and analytics
* Grace period and suspension management
* Auto-renewal capabilities
* Flexible business rules and approval workflows

This module transforms abstract membership concepts into concrete, trackable 
participation records with full lifecycle management and serves as the foundation 
for all membership-related business processes.
    ''',
    'author': 'AMS Development Team',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'ams_member_data',
        'ams_system_config',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/cancellation_reason_data.xml',
        
        # Views
        'views/cancellation_reason_views.xml',
        'views/participation_history_views.xml',
        'views/participation_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
}