{
    'name': 'AMS Budget Management',
    'version': '18.0.1.0.0',  # Updated for Odoo 18
    'category': 'Association Management/Accounting',
    'summary': 'Advanced Budget Management for AMS',
    'description': """
        AMS Budget Management
        ====================
        
        Comprehensive budget management solution for Association Management Systems.
        Based on base_account_budget with AMS-specific enhancements.
        
        Features:
        ---------
        • Budget Planning & Forecasting
        • Multi-dimensional Budgets (Chapter, Department, Project)
        • Budget vs Actual Analysis
        • Budget Alerts & Notifications
        • Subscription Revenue Budgeting
        • Membership Growth Projections
        • Chapter-wise Budget Allocation
        • Event & Program Budgeting
        • Grant & Donation Budget Tracking
        • Cash Flow Budgeting
        • Budget Revision Control
        • Automated Budget Reports
        
        AMS Integration:
        ---------------
        • Links with ams_subscriptions for revenue budgeting
        • Member acquisition cost budgeting
        • Chapter financial planning
        • Event ROI budgeting
        • Subscription churn impact analysis
        
        Technical:
        ----------
        • Compatible with Odoo 18.0+
        • Extends native Odoo budgeting
        • Advanced reporting engine
        • API for budget data integration
    """,
    'author': 'AMS Development Team',
    'website': 'https://your-ams-website.com',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],
    'website': 'https://www.cybrosys.com',
    'data': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
