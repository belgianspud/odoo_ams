# -*- coding: utf-8 -*-
{
    'name': 'Membership Community (Merged with AMS Foundation)',
    'version': '1.0.0',
    'category': 'Membership',
    'summary': 'Comprehensive membership and association management system',
    'description': """
        Membership Community Management - Merged Module
        ================================================
        
        This module combines:
        - Original membership_community features
        - AMS Foundation advanced member management
        
        Features:
        - Member directory and profiles
        - Membership types and records
        - Payment tracking
        - Member status management (prospective, active, grace, lapsed, suspended, terminated)
        - Professional information tracking
        - Portal user management
        - Engagement scoring system
        - Multiple membership configurations
        - Pro-rating and billing options
        - Automated status transitions
        - Communication preferences
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'product',
        'portal',
    ],
    'data': [
        # Security
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data - sequences and settings (always load)
        'data/sequences.xml',
        'data/settings_data.xml',
        
        # Data - membership types (original module, always load)
        'data/membership_data.xml',
        
        # Data - cron jobs
        'data/cron_jobs.xml',
        
        # Views - Settings and Configuration
        'views/ams_settings_views.xml',
        'views/ams_member_type_views.xml',
        'views/res_engagement_rule_views.xml',
        
        # Views - Core membership
        'views/membership_type_views.xml',
        'views/membership_membership_views.xml',
        'views/membership_payment_views.xml',
        'views/res_partner_views.xml',
        
        # Wizards
        'wizard/membership_invoice_wizard_views.xml',
        'wizard/portal_user_wizard_views.xml',
        
        # Menus (must be last)
        'views/membership_menus.xml',
    ],
    'demo': [
        # Demo data - AMS member types (only loaded in demo mode)
        'data/member_types_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}