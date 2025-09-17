# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscriptions Enhanced',
    'version': '2.0.0',
    'summary': 'Enhanced subscription lifecycle management with ams_products_base integration',
    'description': """
AMS Subscriptions Enhanced - Version 2.0
========================================

Advanced subscription lifecycle management for associations with clean architecture:

**Layer 2 Architecture:**
- Inherits from ams_products_base (Layer 1) for product behavior management
- Uses ams_billing_periods for flexible billing cycle calculations
- Focuses on subscription lifecycle, not product configuration
- Clean separation of concerns for maintainability

**Key Features:**
- Individual and Enterprise membership lifecycle management
- Chapter and Publication subscription management  
- Complete state automation (Active → Grace → Suspended → Terminated)
- Member portal with self-service capabilities
- Payment failure tracking and NSF management
- Modification and cancellation workflows with wizards
- Enterprise seat management and assignment
- Integration with billing periods for accurate date calculations

**Enhanced V2.0 Features:**
- ✅ Eliminated duplication with ams_products_base
- ✅ Integrated ams_billing_periods for flexible billing
- ✅ Enhanced member pricing through base module inheritance
- ✅ Cleaner product template inheritance
- ✅ Better integration with product behavior system
- ✅ Improved subscription creation from sales/payments
- ✅ Enhanced portal functionality with modification wizards

**Technical Architecture:**
- Layer 1: ams_products_base (product behavior, pricing, billing config)  
- Layer 2: ams_subscriptions (subscription lifecycle management)
- Layer 3: Future modules (advanced workflows, enterprise features)

This creates a clean, maintainable architecture where each module has a specific purpose.
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    
    # ENHANCED DEPENDENCIES - Layer 2 Architecture
    'depends': [
        # Core Odoo modules
        'base',
        'contacts', 
        'product',
        'sale_management',
        'account',
        'website_sale',
        'point_of_sale', 
        'mail',
        'portal',
        'event',                    # For event template integration
        
        # AMS Foundation modules (Layer 1) - REQUIRED FOR V2.0
        'ams_products_base',        # Product behavior management and configuration
        'ams_billing_periods',      # Flexible billing period calculations  
        'ams_member_data',          # Member status and pricing integration
    ],
    
    'data': [
        # Security - Load in proper order
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
        
        # Data files - Enhanced with billing periods
        'data/ams_subscription_cron.xml',
        'data/ams_subscription_email_templates.xml',    # New templates
        
        # Core Models Views - Enhanced to inherit from base modules  
        'views/product_template_subscription_views.xml',   # Clean inheritance from base
        'views/ams_subscription_views.xml',               # Enhanced subscription management
        'views/ams_subscription_seat_views.xml',          # Enterprise seat management
        'views/ams_subscription_tier_views.xml',          # Tier configuration
        'views/ams_subscription_modification_views.xml',   # Modification wizards
        'views/ams_payment_history_views.xml',            # Payment tracking
        'views/res_partner_views.xml',                    # Enhanced partner integration
        
        # Wizard views for enhanced UX
        'wizard/ams_subscription_modification_wizard_views.xml',
        'wizard/ams_subscription_cancellation_wizard_views.xml',
        
        # Portal integration - Enhanced self-service
        'views/portal_templates.xml',                     # Enhanced portal templates
        'views/portal_subscription_templates.xml',       # Subscription management
        'views/ams_subscription_portal_menu.xml',        # Portal menu integration
        
        # Enhanced management and reporting views
        'views/ams_subscription_dashboard_views.xml',    # Management dashboard
        'views/ams_subscription_reports_views.xml',      # Enhanced reporting
        'views/ams_lifecycle_settings_views.xml',        # Lifecycle configuration
        
        # Actions and menus - Enhanced organization
        'views/ams_subscription_actions.xml',            # All actions
        'views/ams_subscription_menu.xml',               # Clean menu structure
    ],
    
    # Assets for enhanced UX
    'assets': {
        'web.assets_backend': [
            'ams_subscriptions/static/src/css/subscription_dashboard.css',
            'ams_subscriptions/static/src/js/subscription_widgets.js',
            'ams_subscriptions/static/src/js/subscription_kanban.js',    # New kanban enhancements
        ],
        'web.assets_frontend': [
            'ams_subscriptions/static/src/css/portal_subscriptions.css',
            'ams_subscriptions/static/src/js/portal_subscription_management.js',  # New portal JS
        ],
    },
    
    # Installation and compatibility  
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,  # After ams_products_base (Layer 1) but before specialized modules
    
    # Version and upgrade handling
    'pre_init_hook': None,
    'post_init_hook': None,
    'post_load': None,
    'uninstall_hook': None,
    
    # Module relationship info  
    'depends_if_installed': [
        'website_sale_subscription',          # Enhanced integration if present
        'sale_subscription',                  # Odoo native subscription integration
    ],
    
    # Development info
    'development_status': 'Production/Stable',
    'maintainers': ['your-organization'],
    'support': 'https://your-support-url.com/ams-subscriptions',
    'documentation': 'https://your-docs-url.com/ams-subscriptions-v2',
    
    # External dependencies 
    'external_dependencies': {
        'python': ['dateutil'],               # For advanced date calculations with billing periods
        'bin': [],
    },
    
    # Localization support
    'translations': [
        # Future: Add translation support
        # 'i18n/es.po',
        # 'i18n/fr.po',
    ],
    
    # Demo and test data
    'demo': [
        'demo/ams_subscription_demo.xml',    # Enhanced demo data
    ],
    'test': [],
    
    # Commercial info
    'price': 0,
    'currency': 'USD', 
    'live_test_url': None,
    
    # Technical metadata
    'bootstrap': False,
    'cloc_exclude': ['./**/*'],
    
    # Images for app store
    'images': [
        #'static/description/banner.png',
        #'static/description/subscription_lifecycle.png',
        #'static/description/portal_management.png', 
        #'static/description/enterprise_seats.png',
    ],
}