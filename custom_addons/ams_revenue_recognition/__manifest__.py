# -*- coding: utf-8 -*-
{
    'name': 'AMS Revenue Recognition',
    'version': '18.0.1.0.0',  # Fixed version format for Odoo 18
    'category': 'Association Management/Accounting',
    'summary': 'Advanced revenue recognition for Association Management System',
    'description': """
Association Management System - Revenue Recognition
=================================================

Advanced revenue recognition module for associations with annual memberships and subscriptions.
Automatically handles deferred revenue recognition for proper financial reporting.

Key Features:
------------
* Automated revenue recognition schedules
* Monthly processing for annual memberships
* Deferred revenue tracking and management
* Revenue recognition reporting and analytics
* Integration with subscription management
* Configurable recognition methods per product
* Financial compliance for subscription businesses

Business Benefits:
-----------------
* Accurate monthly income statements
* Proper accounting for prepaid memberships
* Automated financial compliance
* Detailed revenue recognition reporting
* Better cash flow and budget planning
* Professional financial statements for audits

Revenue Recognition Methods:
---------------------------
* Immediate Recognition: For monthly subscriptions
* Straight-Line Recognition: For annual memberships
* Manual Recognition: For custom scenarios
* Milestone-Based Recognition: For event-based services

Financial Compliance:
--------------------
* ASC 606 / IFRS 15 compliant revenue recognition
* Proper deferred revenue accounting
* Audit-ready transaction trails
* SOX compliance support
* Automated month-end processing

Target Users:
------------
* Association finance teams
* CFOs and financial managers
* Accounting supervisors
* External auditors
* Board members reviewing financials
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    
    # Dependencies
    'depends': [
        'ams_base_accounting',  # Required base module
        'account',
        'product',
        'sale',
        'mail',
    ],
    
    # Module Data Files
    'data': [
        # Security
        'security/ams_revenue_recognition_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/revenue_recognition_data.xml',
        'data/ams_revenue_recognition_cron.xml',
        
        # Views - Revenue Recognition Core
        'views/ams_revenue_recognition_views.xml',
        'views/ams_revenue_schedule_views.xml',
        'views/ams_revenue_recognition_menu.xml',
        
        # Views - Integration with Other Models
        'views/ams_subscription_views.xml',
        'views/product_template_views.xml',
        'views/account_move_views.xml',
        
        # Reports
        'reports/ams_revenue_reports.xml',
    ],
    
    # Demo Data
    'demo': [
        'demo/ams_revenue_recognition_demo.xml',
    ],
    
    # Module Configuration
    'installable': True,
    'auto_install': False,
    'application': False,   # This is an extension module, not a standalone app
    'sequence': 110,
    
    # Installation Hooks
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Support Information
    'support': 'support@yourorganization.com',
    'maintainer': 'Your Organization Development Team',
    
    # Development Information
    'development_status': 'Production/Stable',
    'complexity': 'expert',  # This is advanced accounting functionality
    
    # Compatibility
    'python_requires': '>=3.8',
    
    # Module Relationships
    'auto_install_requirements': ['ams_base_accounting'],
}