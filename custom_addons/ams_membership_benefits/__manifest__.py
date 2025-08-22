# -*- coding: utf-8 -*-
{
    'name': 'AMS Membership Benefits',
    'version': '1.0.0',
    'summary': 'Comprehensive membership benefit management with Events and eLearning integration',
    'description': """
AMS Membership Benefits
=======================
Extend AMS Subscriptions with comprehensive benefit management including:

Core Features:
- Define membership benefits by subscription tier with granular control
- Track benefit eligibility, usage quotas, and statistics
- Member portal integration with benefit dashboard
- Automatic discount application across the system

Event Integration:
- Early access registration periods for members by tier
- Automatic member pricing on event registration
- Event access restrictions based on membership level
- Member-only events and premium content

eLearning Integration:
- Course access control by membership tier
- Automatic enrollment for included courses
- CE credit tracking and reporting
- Learning path recommendations

Geographic Intelligence:
- Chapter recommendations based on ZIP code and location
- Regional event and content preferences
- Local member networking suggestions
- Territory-based benefit variations

Portal Access Control:
- Tiered portal feature access (directory, resources, networking)
- Premium content areas for higher tiers
- Member directory access levels
- Self-service benefit management

This module provides the foundation for sophisticated membership value delivery
and enables associations to clearly demonstrate ROI while driving tier upgrades.
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    'depends': [
        'ams_subscriptions',  # Core AMS functionality required
        'portal',             # For member portal integration
        'event',              # For event integration and member pricing
        'contacts',           # For geographic/ZIP code processing
    ],
    'external_dependencies': {
        'python': ['geopy'],  # For ZIP code to chapter mapping (optional)
    },
    'data': [
        # Security
        'security/ams_benefits_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/benefit_types.xml',
        'data/default_benefits.xml',
        'data/geographic_regions.xml',
        
        # Views - Backend
        'views/ams_membership_benefit_views.xml',
        'views/ams_benefit_category_views.xml',
        'views/ams_subscription_tier_views.xml',
        'views/ams_subscription_views.xml',
        'views/res_partner_views.xml',
        'views/event_event_views.xml',
        
        # Views - Portal
        'views/portal_benefits_template.xml',
        'views/portal_member_dashboard.xml',
        
        # Menus
        'views/ams_benefit_menu.xml',
        
        # Email Templates
        'data/email_templates.xml',
    ],
    'demo': [
        'demo/demo_benefit_categories.xml',
        'demo/demo_benefits.xml',
        'demo/demo_geographic_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_membership_benefits/static/src/css/benefits_backend.css',
            'ams_membership_benefits/static/src/js/benefit_configurator.js',
        ],
        'web.assets_frontend': [
            'ams_membership_benefits/static/src/css/portal_benefits.css',
            'ams_membership_benefits/static/src/js/benefit_dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}