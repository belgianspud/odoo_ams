{
    'name': 'AMS Accounting - Full Accounting Kit',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete Accounting Features for Association Management System',
    'description': """
AMS Accounting Module
=====================

Complete accounting functionality adapted for Association Management Systems.
Built specifically for Odoo 18 with seamless AMS integration.

Core Features:
- Enhanced Financial Dashboard with AMS metrics
- Comprehensive Financial Reports (P&L, Balance Sheet, Cash Flow)
- Asset Management with Depreciation
- Budget Management and Variance Analysis
- Customer Follow-ups and Dunning
- Recurring Payments (integrates with AMS subscriptions)
- Bank Statement Import and Reconciliation
- Multi-currency Support
- Advanced Journal Entries
- Tax Management

AMS Integration Features:
- Subscription revenue tracking and analytics
- Member payment behavior analysis
- Chapter-specific financial reports
- Renewal revenue forecasting
- Donation and grant management
- Event financial tracking
- Membership fee analysis
- Multi-company support for chapters

Perfect for:
- Associations and Non-profits
- Professional Organizations
- Community Groups
- Educational Institutions
- Membership Organizations
- Any organization using AMS subscriptions
    """,
    'author': 'AMS Development Team',
    'website': 'https://github.com/belgianspud/odoo_ams',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'sale',
        'purchase',
        'stock',
        'mail',
        'analytic',
        'ams_subscriptions',
        'ams_module_manager',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter', 'xlrd', 'dateutil', 'lxml'],
    },
    'data': [
        'security/accounting_security.xml',
        'security/ir.model.access.csv',
        'data/account_financial_report_data.xml',
        'data/cash_flow_data.xml',
        'data/followup_levels.xml',
        'data/recurring_entry_cron.xml',
        'data/ams_integration_data.xml',
        'views/accounting_menu.xml',
        'views/dashboard_views.xml',
        'views/account_configuration.xml',
        'views/res_config_view.xml',
        'views/account_asset_views.xml',
        'views/account_asset_templates.xml',
        'views/account_followup.xml',
        'views/followup_report.xml',
        'views/account_move_views.xml',
        'views/account_payment_view.xml',
        'views/credit_limit_view.xml',
        'views/recurring_payments_view.xml',
        'views/multiple_invoice_form.xml',
        'views/multiple_invoice_layout_view.xml',
        'views/product_template_views.xml',
        'views/ams_financial_views.xml',
        'views/ams_subscription_accounting_views.xml',
        'views/ams_member_financial_views.xml',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'wizard/financial_report.xml',
        'wizard/general_ledger.xml',
        'wizard/partner_ledger.xml',
        'wizard/tax_report.xml',
        'wizard/trial_balance.xml',
        'wizard/aged_partner.xml',
        'wizard/journal_audit.xml',
        'wizard/cash_flow_report.xml',
        'wizard/account_bank_book_wizard_view.xml',
        'wizard/account_cash_book_wizard_view.xml',
        'wizard/account_day_book_wizard_view.xml',
        'wizard/account_lock_date.xml',
        'report/report_financial.xml',
        'report/general_ledger_report.xml',
        'report/report_journal_audit.xml',
        'report/report_aged_partner.xml',
        'report/report_trial_balance.xml',
        'report/report_tax.xml',
        'report/report_partner_ledger.xml',
        'report/cash_flow_report.xml',
        'report/account_bank_book_view.xml',
        'report/account_cash_book_view.xml',
        'report/account_day_book_view.xml',
        'report/account_asset_report_views.xml',
        'report/report.xml',
        'report/multiple_invoice_layouts.xml',
        'report/multiple_invoice_report.xml',
        'report/report_payment_receipt_document_inherit.xml',
        'report/ams_subscription_financial_report.xml',
        'report/ams_member_financial_report.xml',
        'report/ams_chapter_financial_report.xml',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_accounting/static/src/scss/style.scss',
            'ams_accounting/static/src/scss/account_asset.scss',
            'ams_accounting/static/src/scss/ams_dashboard.scss',
            'ams_accounting/static/lib/bootstrap-toggle-master/css/bootstrap-toggle.min.css',
            'ams_accounting/static/src/js/account_dashboard.js',
            'ams_accounting/static/src/js/account_asset.js',
            'ams_accounting/static/src/js/ams_dashboard.js',
            'ams_accounting/static/lib/Chart.bundle.js',
            'ams_accounting/static/lib/Chart.bundle.min.js',
            'ams_accounting/static/lib/Chart.min.js',
            'ams_accounting/static/lib/Chart.js',
            'ams_accounting/static/lib/bootstrap-toggle-master/js/bootstrap-toggle.min.js',
            'ams_accounting/static/src/xml/template.xml',
            'ams_accounting/static/src/xml/ams_dashboard_templates.xml',
        ],
    },
    'demo': [
        'demo/ams_accounting_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,
}