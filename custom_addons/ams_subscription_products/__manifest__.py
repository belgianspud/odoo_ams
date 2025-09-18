# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Products',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Advanced subscription product management for associations with recurring billing',
    'description': """
AMS Subscription Products - Advanced Subscription Management
===========================================================

This module extends AMS Products Base with comprehensive subscription management
capabilities specifically designed for professional associations.

* **Subscription Product Enhancement**
  - Extends AMS product behavior types with 'subscription' option
  - Advanced subscription term configuration (days, weeks, months, years)
  - Integration with AMS Billing Periods for standardized cycles
  - Flexible billing frequency and payment schedule management
  - Subscription lifecycle automation (creation, renewal, cancellation)

* **Professional Association Features**
  - Member vs non-member subscription pricing
  - Professional journal and publication subscriptions
  - Research report and industry analysis subscriptions
  - Software license and platform access subscriptions
  - Educational content and course access subscriptions
  - Committee and special interest group subscriptions

* **Advanced Billing & Revenue Management**
  - Integration with AMS Billing Periods for consistent cycles
  - Prorated billing for mid-cycle starts
  - Automatic renewal processing with member notification
  - Deferred revenue recognition for accounting compliance
  - Multiple payment schedule options (annual, semi-annual, quarterly, monthly)
  - Grace period management for lapsed subscriptions

* **Subscription Lifecycle Management**
  - Automated subscription creation from product purchases
  - Renewal reminder workflows and member communications
  - Subscription modification and upgrade/downgrade workflows
  - Cancellation processing with proper notice periods
  - Subscription pause and hold functionality
  - Reactivation workflows for lapsed memberships

* **Member Portal Integration**
  - Subscription status dashboard for members
  - Self-service renewal and modification capabilities
  - Payment history and invoice access
  - Subscription benefit and access tracking
  - Automatic portal group management based on subscription status

* **Analytics & Reporting**
  - Subscription revenue analytics and forecasting
  - Churn analysis and retention metrics
  - Member engagement tracking by subscription type
  - Renewal rate analysis and trend reporting
  - Subscription lifecycle analytics
  - Member value and lifetime value calculations

* **Integration Points**
  - Seamless integration with AMS Products Base behavior system
  - AMS Billing Periods integration for standardized cycles
  - Event module integration for event-based subscriptions
  - Digital content delivery for subscriber-only resources
  - Membership module integration for membership-based subscriptions
  - Accounting integration for proper revenue recognition

* **Automation & Workflows**
  - Automated subscription creation from sales orders
  - Renewal notification workflows with customizable timing
  - Payment failure handling and retry logic
  - Subscription status synchronization with member records
  - Automated access control based on subscription status
  - Integration with payment gateways for automated billing

* **Subscription Types Supported**
  - Professional journal and magazine subscriptions
  - Research and industry report subscriptions
  - Software and platform access licenses
  - Educational course and content subscriptions
  - Committee and working group subscriptions
  - Premium content and resource library access
  - Event series and webinar subscriptions
  - Certification maintenance and renewal programs

* **Professional Association Compliance**
  - Support for professional development credit tracking
  - Compliance with association billing standards
  - Member communication requirements adherence
  - Professional licensing renewal integration
  - Industry-specific reporting and analytics
  - Regulatory compliance for subscription billing

Key Benefits for Associations:
- Streamlined subscription management reducing administrative overhead
- Consistent billing cycles aligned with association standards
- Comprehensive member self-service capabilities
- Advanced analytics for subscription business optimization
- Automated workflows reducing manual processing
- Professional-grade subscription lifecycle management

Key Benefits for Members:
- Clear subscription status and benefit tracking
- Self-service renewal and modification capabilities
- Transparent billing and payment history
- Integrated access to subscription benefits
- Flexible payment options and schedules
- Professional portal experience

Technical Architecture:
- Extends AMS Products Base without modifying core functionality
- Leverages AMS Billing Periods for standardized billing cycles
- Uses Odoo native subscription framework with association enhancements
- Provides clean APIs for third-party integration
- Maintains performance with optimized queries and caching
- Supports multi-company and multi-currency environments

Version 1.0 Features:
- Complete subscription product behavior management
- Integration with AMS Billing Periods for standardized cycles
- Advanced subscription lifecycle automation
- Member portal integration with self-service capabilities
- Comprehensive analytics and reporting suite
- Professional association-specific workflows and compliance
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'sale_subscription',      # Odoo's native subscription functionality
        'account',               # For revenue recognition and accounting
        'mail',                  # For automated communications
        'portal',                # For member portal integration
        'payment',               # For automated payment processing
        'ams_products_base',     # Core AMS product functionality
        'ams_billing_periods',   # Standardized billing cycles
        'ams_member_data',       # Member status and data management
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/subscription_security.xml',
        
        # Data - Subscription configurations
        'data/subscription_product_data.xml',
        'data/billing_period_integration_data.xml',
        'data/subscription_email_templates.xml',
        
        # Views - Product subscription enhancements
        'views/product_template_subscription_views.xml',
        'views/product_product_subscription_views.xml',
        
        # Views - Subscription management
        'views/subscription_billing_views.xml',
        'views/subscription_renewal_views.xml',
        'views/subscription_analytics_views.xml',
        
        # Views - Member portal
        'views/portal_subscription_views.xml',
        
        # Wizards - Subscription management
        'wizard/subscription_renewal_wizard_views.xml',
        'wizard/subscription_modification_wizard_views.xml',
        
        # Reports
        'reports/subscription_reports.xml',
        'reports/subscription_analytics_reports.xml',
        
        # Menu items
        'views/subscription_menu.xml',
    ],
    'demo': [
        'demo/demo_subscription_products.xml',
        'demo/demo_subscription_scenarios.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_subscriptions_products/static/src/css/subscription_dashboard.css',
            'ams_subscriptions_products/static/src/js/subscription_analytics.js',
        ],
        'web.assets_frontend': [
            'ams_subscriptions_products/static/src/css/portal_subscription.css',
            'ams_subscriptions_products/static/src/js/portal_subscription.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,  # Extension module, not standalone application
    'sequence': 15,  # After ams_products_base (10) but before specialized modules
    
    # Module relationships
    'pre_init_hook': None,
    'post_init_hook': '_post_init_subscription_integration',
    'uninstall_hook': '_uninstall_cleanup_subscriptions',
    
    # External dependencies
    'external_dependencies': {
        'python': ['dateutil'],  # For advanced date calculations
        'bin': [],
    },
    
    # Development and maintenance info
    'maintainers': ['your-organization'],
    'contributors': [],
    
    # Module maturity and support
    'development_status': 'Production/Stable',
    'support': 'https://your-support-url.com',
    'documentation': 'https://your-docs-url.com/ams-subscriptions-products',
    
    # Compatibility and requirements
    'python_requires': '>=3.8',
    'bootstrap': False,
    
    # Additional metadata
    'images': [
        #'static/description/banner.png',
        #'static/description/subscription_lifecycle.png',
        #'static/description/billing_integration.png',
        #'static/description/member_portal.png',
    ],
    
    # Localization support
    'translations': [
        # Future: Add translation files for subscription terminology
        # 'i18n/es.po',
        # 'i18n/fr.po',
    ],
    
    # Price and commercial info (if applicable)
    'price': 0,
    'currency': 'USD',
    'live_test_url': None,
    
    # Technical configuration
    'cloc_exclude': [
        'static/**/*',
        'tests/**/*',
        'demo/**/*',
    ],
}