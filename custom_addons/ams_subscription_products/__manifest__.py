# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Products',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Comprehensive subscription product management with lifecycle automation',
    'description': """
AMS Subscription Products - Enhanced Subscription Management
==========================================================

This module provides comprehensive subscription product management for professional
associations with complete lifecycle automation and advanced features.

* **Enhanced Product Integration**
  - Extends ams_products_base subscription functionality
  - Leverages ams_billing_periods for standardized billing cycles
  - Category-driven subscription defaults and configuration
  - Behavior-aware subscription setup and management

* **Comprehensive Subscription Types**
  - Individual and organizational memberships
  - Chapter and regional memberships
  - Professional development subscriptions
  - Publication and content subscriptions
  - Service and access subscriptions
  - Certification maintenance programs

* **Complete Lifecycle Management**
  - Draft → Approval → Active → Renewal/Expiration workflow
  - Automated state transitions and notifications
  - Grace period handling for expired subscriptions
  - Suspension and cancellation with reason tracking
  - Multi-generational renewal tracking

* **Advanced Renewal Management**
  - Automatic and manual renewal options
  - Early renewal discounts and incentives
  - Configurable renewal notice periods
  - Bulk renewal processing capabilities
  - Renewal rate analytics and reporting

* **Enterprise Multi-Seat Support**
  - Organizational subscription hierarchies
  - Seat allocation and assignment management
  - Volume discount tiers for large subscriptions
  - Per-seat or flat-rate pricing models
  - Sub-user management and access control

* **Flexible Billing Integration**
  - Multiple billing period support per product
  - Partner-specific billing period selection
  - Prorated billing for mid-cycle changes
  - Integration with Odoo invoicing system
  - Payment method tracking and management

* **Association-Specific Features**
  - Member vs. non-member subscription eligibility
  - Chapter and regional access restrictions
  - Professional qualification requirements
  - Approval workflows for sensitive subscriptions
  - Benefits and access rights management

* **Comprehensive Access Control**
  - Portal group assignment automation
  - Digital content access management
  - Event discount and priority registration
  - Publication and resource access control
  - Networking and directory enhancements

* **Advanced Analytics and Reporting**
  - Subscription revenue tracking (MRR/ARR)
  - Renewal rate analysis and forecasting
  - Subscriber lifecycle analytics
  - Usage tracking and reporting
  - Churn analysis and prevention

* **Automation and Workflows**
  - Automated renewal processing
  - Expiration and renewal notifications
  - Approval workflow integration
  - Payment reminder automation
  - Grace period management

* **Portal and Self-Service**
  - Subscriber portal dashboards
  - Self-service renewal options
  - Subscription modification requests
  - Usage reporting and analytics
  - Seat management for organizations

Key Benefits for Associations:
- Streamlined subscription lifecycle management
- Automated renewal and billing processes
- Comprehensive member benefit tracking
- Professional association-specific features
- Enterprise-ready multi-seat support
- Advanced analytics and reporting

Technical Features:
- Extends existing AMS foundation modules
- Clean integration with Odoo core features
- Comprehensive test coverage
- Scalable architecture for large associations
- API-ready for external integrations
- Performance optimized for high-volume operations

Version 1.0.0 Features:
- Complete subscription product management system
- Full lifecycle automation with state management
- Advanced renewal workflows and notifications
- Multi-seat and organizational subscription support
- Comprehensive reporting and analytics
- Integration with billing, invoicing, and portal systems
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        # Core Odoo modules
        'base',
        'mail',
        'account',
        'sale',
        'portal',
        'website',
        
        # AMS foundation modules
        'ams_products_base',      # Enhanced product behavior management
        'ams_billing_periods',    # Standardized billing cycles
        'ams_member_data',        # Member data and status management
        'ams_product_types',      # Enhanced category functionality
        
        # Optional integrations
        'approvals',              # For approval workflows (if available)
        'hr',                     # For employee/user management (if needed)
    ],
    'data': [
        # Security and Access Control
        'security/ir.model.access.csv',
        'security/subscription_security.xml',
        
        # Data and Configuration
        'data/subscription_sequences.xml',
        'data/subscription_product_data.xml',
        'data/email_templates.xml',
        'data/cron_jobs.xml',
        'data/mail_activity_types.xml',
        
        # Core Views
        'views/subscription_product_views.xml',
        'views/subscription_instance_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        
        # Management Views
        'views/subscription_renewal_views.xml',
        'views/subscription_analytics_views.xml',
        'views/subscription_reporting_views.xml',
        
        # Wizards
        'wizard/subscription_renewal_wizard_views.xml',
        'wizard/subscription_bulk_renewal_views.xml',
        'wizard/subscription_seat_management_views.xml',
        'wizard/subscription_migration_wizard_views.xml',
        
        # Navigation and Menus
        'views/menus.xml',
        
        # Portal Views (if portal integration needed)
        'views/portal_subscription_templates.xml',
        
        # Reports
        'report/subscription_reports.xml',
        'report/subscription_templates.xml',
    ],
    'demo': [
        # Demo data for testing and development
        'demo/demo_subscription_products.xml',
        'demo/demo_subscription_instances.xml',
        'demo/demo_partners.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_subscription_products/static/src/css/subscription_backend.css',
            'ams_subscription_products/static/src/js/subscription_widgets.js',
        ],
        'web.assets_frontend': [
            'ams_subscription_products/static/src/css/subscription_portal.css',
            'ams_subscription_products/static/src/js/subscription_portal.js',
        ],
        'web.report_assets_common': [
            'ams_subscription_products/static/src/css/subscription_reports.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,  # After core AMS modules
    
    # Module relationships and dependencies
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # External dependencies
    'external_dependencies': {
        'python': ['dateutil'],
        'bin': [],
    },
    
    # Development and maintenance info
    'maintainers': ['your-organization'],
    'contributors': [
        'Development Team',
        'Product Management Team',
    ],
    
    # Module maturity and support
    'development_status': 'Production/Stable',
    'support': 'https://your-support-url.com/ams-subscription-products',
    'documentation': 'https://your-docs-url.com/ams-subscription-products',
    
    # Compatibility and requirements
    'python_requires': '>=3.8',
    'bootstrap': False,
    
    # Additional metadata
    'images': [
        #'static/description/banner.png',
        #'static/description/subscription_lifecycle.png',
        #'static/description/renewal_management.png',
        #'static/description/multi_seat_support.png',
        #'static/description/analytics_dashboard.png',
    ],
    
    # Localization support
    'translations': [
        # Future: Add translation files
        # 'i18n/es.po',
        # 'i18n/fr.po',
        # 'i18n/de.po',
    ],
    
    # Pricing and commercial info (if applicable)
    'price': 0,
    'currency': 'USD',
    'live_test_url': 'https://demo.your-site.com/ams-subscription-demo',
    
    # Quality and testing
    'test_tags': ['subscription', 'ams', 'lifecycle', 'renewal'],
    
    # Technical configuration
    'cloc_exclude': [
        'tests/**',
        'demo/**',
        'static/lib/**',
    ],
}