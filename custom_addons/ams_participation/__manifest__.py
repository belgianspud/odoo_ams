# -*- coding: utf-8 -*-
{
    'name': 'AMS Participation',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Basic participation records and status tracking for Association Management System',
    'description': """
AMS Participation - Core Business Entity
========================================

This module provides comprehensive participation management for associations:

* **Participation Records**
  - Individual and organizational participation tracking
  - Multiple participation types: membership, chapters, committees, events, courses
  - Comprehensive status lifecycle management (prospect, active, grace, suspended, terminated)
  - Company relationships and inheritance support
  - Sponsorship and employee participation tracking

* **Status Management**  
  - Automatic status transitions based on configurable rules
  - Integration with member status from ams_member_types
  - Grace period, suspension, and termination automation
  - Comprehensive audit trail and history tracking

* **Business Rules**
  - One active membership maximum per individual/company
  - Unlimited active chapter participations allowed
  - Configurable transition periods via system settings
  - Validation constraints and business logic enforcement

* **Integration Features**
  - Links to billing and invoicing (account.move)
  - Subscription product references (placeholder ready)
  - Committee position tracking (placeholder ready)
  - Cancellation reason management and reporting

* **Lifecycle Automation**
  - Automatic grace period activation when paid_through_date expires
  - Suspension after configurable grace period
  - Termination after configurable suspension period
  - Scheduled actions for status maintenance

This is a Layer 2 core business entity module that provides the foundation
for all membership participation tracking in the AMS ecosystem.

Key Features:
* Flexible participation type definitions
* Automated status lifecycle management  
* Company inheritance and sponsorship support
* Comprehensive audit trails and history
* Integration-ready for billing and products
* Configurable business rules and periods
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'ams_member_data',
        'ams_member_types',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/cancellation_reason_data.xml',
        # Views
        'views/participation_views.xml',
        'views/participation_history_views.xml',
        'views/cancellation_reason_views.xml',
        # Scheduled Actions
        'data/participation_cron.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 7,
    'external_dependencies': {
        'python': [],
    },
}