# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscription Products',
    'version': '18.0.1.0.0',
    'category': 'Association Management/Subscriptions',
    'summary': 'Subscription product definitions and configuration for association management',
    'description': """
AMS Subscription Products
========================

This module provides comprehensive subscription product management for association management systems,
enabling professional associations to offer and manage various subscription-based products and services.

Key Features:
=============

* **Subscription Product Templates**
  - Extend standard products with subscription capabilities
  - Integration with AMS billing periods for flexible billing cycles
  - Subscription scope configuration (individual vs enterprise)
  - Auto-renewal and manual renewal options

* **Subscription Product Definitions**
  - Dedicated subscription product catalog (ams.subscription.product)
  - Classification by subscription type (membership, publication, service, etc.)
  - Duration and billing cycle configuration
  - Base pricing with currency support

* **Renewal Management**
  - Configurable renewal windows and notice periods
  - Auto-renewal enablement with member preferences
  - Staff approval requirements for enterprise subscriptions
  - Renewal workflow integration

* **Enterprise Features Foundation**
  - Seat allocation support for multi-user subscriptions
  - Default seat count configuration
  - Enterprise scope designation
  - Approval workflow integration

* **Integration Capabilities**
  - Seamless integration with ams_products_base for core product functionality
  - ams_billing_periods integration for standardized billing cycles
  - Portal access management for subscription benefits
  - Member-only subscription restrictions

* **Professional Association Use Cases**
  - Individual and organizational memberships
  - Chapter and committee access subscriptions
  - Professional publication subscriptions
  - Certification program subscriptions
  - Premium service access subscriptions

Technical Architecture:
======================

* **Clean Extension Pattern**: Extends existing product models without disrupting core functionality
* **Billing Period Integration**: Leverages ams_billing_periods for consistent billing cycle management
* **Modular Design**: Foundation for advanced subscription features in companion modules
* **Performance Optimized**: Efficient database design with proper indexing and computed fields

Business Benefits:
==================

* **Flexible Subscription Offerings**: Support for diverse subscription types and billing cycles
* **Professional Association Focus**: Pre-configured for common association subscription patterns
* **Member Experience**: Streamlined subscription management with auto-renewal options
* **Administrative Control**: Approval workflows and staff oversight for enterprise subscriptions
* **Revenue Predictability**: Structured subscription billing with renewal management

Future Integration Modules:
===========================

This module serves as the foundation for:
- ams_subscription_pricing (advanced pricing and discounting)
- ams_subscription_lifecycle (renewals, cancellations, lifecycle management)
- ams_subscription_enterprise (multi-seat, organizational features)
- ams_subscription_reporting (analytics and subscription insights)

Installation Notes:
==================

Requires ams_products_base and ams_billing_periods modules.
Compatible with all standard Odoo sales and accounting modules.
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'mail',
        'ams_products_base',      # For enhanced product functionality
        'ams_billing_periods',    # For billing cycle management
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/subscription_defaults_data.xml',
        
        # Views
        'views/product_template_subscription_views.xml',
        'views/subscription_product_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 11,
    
    # Module relationships
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
    
    # External dependencies
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    
    # Development info
    'maintainers': ['your-organization'],
    'contributors': [],
    
    # Compatibility
    'development_status': 'Beta',
    'python_requires': '>=3.8',
}