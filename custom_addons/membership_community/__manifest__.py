# -*- coding: utf-8 -*-
{
    'name': 'Membership Community - Base',
    'version': '18.0.1.0.0',
    'category': 'Membership',
    'summary': 'Core Membership Management Infrastructure',
    'description': """
Membership Community - Base Module
===================================

Core membership management infrastructure that provides:

* Base membership category model (simplified)
* Membership features and benefits framework
* Partner membership status tracking
* Subscription extensions for memberships
* Product template membership flag
* Organizational memberships with seat allocation
* Seat inheritance and benefit cascading
* Security groups and access rights
* Core menu structure
* Quick Setup Wizard for easy configuration

This module is designed to be extended by specialized modules:
- membership_individual: Individual member types (student, retired, etc.)
- membership_organizational: Enhanced organizational membership features
- membership_chapter: Chapter/section memberships

Key Features:
- Quick Setup Wizard: Create complete membership configurations in one step
- Organizational Memberships: Support for seat-based memberships
- Seat Management: Allocate/deallocate seats with full lifecycle tracking
- Benefit Inheritance: Seat members inherit benefits from parent organization
- Leverages subscription_management for lifecycle management
- Simplified configuration focused on ease of use
- No duplicate lifecycle code - inherits from subscription_management

Organizational Membership Support:
- Parent-child subscription relationships
- Seat allocation and deallocation wizards
- Automatic benefit inheritance to seat holders
- Lifecycle synchronization (suspend/cancel cascades to seats)
- Seat utilization tracking and reporting
- Email notifications for seat events
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'subscription_management',  # Core dependency for lifecycle management
    ],
    'data': [
        # Security - Load first
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        
        # Data files - Load before views
        'data/ir_sequence_data.xml',
        'data/membership_category_data.xml',
        'data/membership_feature_data.xml',
        'data/membership_benefit_data.xml',
        'data/product_template_data.xml',
        'data/membership_cron.xml',
        'data/membership_email_templates.xml',
        'data/seat_notification_email_templates.xml',  # NEW: Seat allocation/deallocation emails
        
        # Wizard views
        'wizard/membership_quick_setup_wizard_views.xml',
        'wizard/seat_allocation_wizard_views.xml',  # NEW: Seat allocation wizard
        'wizard/seat_deallocation_wizard_views.xml',  # NEW: Seat deallocation wizard
        
        # Core Views
        'views/membership_category_views.xml',
        'views/membership_feature_views.xml',
        'views/membership_benefit_views.xml',
        'views/product_template_views.xml',
        'views/subscription_plan_views.xml',  # NEW: Enhanced with seat configuration
        'views/subscription_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        
        # NOTE: res_config_settings_views.xml REMOVED
        # Settings are now in subscription_management module
    ],
    'demo': [
        'demo/membership_category_demo.xml',
        'demo/membership_feature_demo.xml',
        'demo/membership_benefit_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}