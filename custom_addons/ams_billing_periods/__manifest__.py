# -*- coding: utf-8 -*-
{
    'name': 'AMS Billing Periods',
    'version': '18.0.1.0.0',
    'category': 'Association Management',
    'summary': 'Standard billing cycle definitions for association management',
    'description': """
AMS Billing Periods
===================

This module provides foundational billing period definitions for association management:

* Billing Period Management
  - Standard billing cycles (monthly, quarterly, annual)
  - Custom duration definitions
  - Flexible time unit configuration
  - Default period designation

* Period Configuration Features
  - Duration value and unit specification
  - Automatic total days calculation
  - Display sequence management
  - Active/inactive status control

* Foundation Features
  - Extensible period definitions
  - Integration-ready design
  - Validation and business rules
  - User-friendly administrative interface

This is a Layer 1 foundation module that provides core billing period
infrastructure for all AMS modules dealing with subscriptions, renewals,
and recurring billing cycles.

Key Features:
* Pre-configured standard billing periods
* Flexible duration configuration (days, weeks, months, years)
* Default period designation
* Computed total days for easy comparison
* Built-in validation and business rules
* Integration with subscription and billing systems
    """,
    'author': 'Your Organization',
    'website': 'https://your-website.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/billing_period_data.xml',
        # Views
        'views/billing_period_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 5,
}