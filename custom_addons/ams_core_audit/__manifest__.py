# -*- coding: utf-8 -*-
{
    'name': 'AMS Core Audit',
    'version': '18.0.1.0.0',
    'category': 'Association/Core',
    'summary': 'Audit logging and compliance tracking across AMS modules',
    'description': """
AMS Core Audit Module
=====================

Centralized audit logging for compliance and traceability across all AMS modules.
Records create, update, and delete events with role-based access and configurable 
retention policies.

Core Features:
--------------
* Comprehensive audit trail for all AMS data changes
* Automatic logging of create, write, and unlink operations
* Field-level change tracking with before/after values
* User attribution and IP address tracking
* Configurable retention policies with automated cleanup
* Role-based access to audit logs (viewer, manager)
* Integration with privacy compliance requirements

Audit Capabilities:
-------------------
* Member record changes (profile updates, status changes)
* Professional credential modifications
* Membership lifecycle events (join, renew, lapse)
* Financial transaction logging
* Privacy consent changes
* System configuration modifications
* Data import/export activities

Compliance Features:
--------------------
* GDPR audit requirements
* SOX compliance for financial associations
* Professional licensing board requirements
* Association governance audit trails
* Data retention policy enforcement
* Tamper-evident logging

Security & Access:
------------------
* Audit Viewer: Read-only access to audit logs
* Audit Manager: Full access plus retention management
* Privacy Officer: Access to privacy-related audit events
* System integration with existing AMS security groups

Integration:
------------
* Audit Mixin for easy integration with other AMS modules
* Smart buttons on partner and member records
* Dashboard widgets for audit activity monitoring
* Automated alerts for critical audit events
* Export capabilities for compliance reporting

This module provides the foundation for compliance-ready audit logging
across the entire AMS ecosystem.
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/yourusername/ams-odoo',
    'license': 'LGPL-3',
    'depends': [
        'ams_core_base',
        'mail',
        'base',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/audit_cron.xml',
        'data/audit_categories.xml',
        
        # Views
        'views/audit_log_views.xml',
        'views/res_partner_views.xml',
        'views/audit_dashboard_views.xml',
    ],
    'demo': [
        # Demo audit data can be added here if needed
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 106,  # Load after ams_core_base and ams_core_professional
}