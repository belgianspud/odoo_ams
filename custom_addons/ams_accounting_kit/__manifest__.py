{
    'name': 'AMS Full Accounting Kit for Community',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': """Complete accounting solution for Association Management Systems""",
    'description': """
            AMS Accounting Kit
            ==================
        
            Complete accounting solution designed specifically for Association Management Systems.
            Based on the proven base_accounting_kit with AMS-specific enhancements.
        
            Features:
            ---------
            • Advanced Financial Reports & Dashboards
            • Multi-Currency Support
            • Budget Management & Analysis
            • Asset Management
            • Cash Flow Management
            • Bank Reconciliation
            • Tax Management
            • Cost Center Accounting
            • AMS Subscription Integration
            • Member Financial Tracking
            • Chapter-wise Financial Reporting
            • Automated Journal Entries
            • Financial Analytics & KPIs
            • Audit Trail & Compliance
        
            AMS Integration:
            ---------------
            • Links with ams_subscriptions for revenue tracking
            • Member-specific financial dashboards
            • Chapter and region financial analysis
            • Subscription revenue recognition
            • Automated billing workflows
            • Member payment tracking
        
            Technical:
            ----------
            • Compatible with Odoo 18.0+
            • Extends native Odoo accounting
            • RESTful API for integrations
            • Custom report engine
            • Automated backup & restore
    """,
    'author': 'AMS Development Team',
    'website': "",
    'company': '',
    'maintainer': '',
    'depends': ['base', 'account', 'sale', 'account_check_printing', 'base_account_budget', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/account_financial_report_data.xml',
        'data/cash_flow_data.xml',
        'data/followup_levels.xml',
        'data/multiple_invoice_data.xml',
        'data/recurring_entry_cron.xml',
        'views/assets.xml',
        'views/dashboard_views.xml',
        'views/reports_config_view.xml',
        'views/accounting_menu.xml',
        'views/account_group.xml',
        'views/credit_limit_view.xml',
        'views/account_configuration.xml',
        'views/res_config_view.xml',
        'views/account_followup.xml',
        'views/followup_report.xml',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/account_move_views.xml',
        'views/account_asset_templates.xml',
        'views/product_template_views.xml',
        'views/multiple_invoice_layout_view.xml',
        'views/multiple_invoice_form.xml',
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
        'views/recurring_payments_view.xml',
        'wizard/account_lock_date.xml',
        'views/account_payment_view.xml',
        'data/account_pdc_data.xml',
        'views/report_payment_receipt_document_inherit.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ams_accounting_kit/static/src/scss/style.scss',
            'ams_accounting_kit/static/src/scss/account_asset.scss',
            'ams_accounting_kit/static/lib/bootstrap-toggle-master/css/bootstrap-toggle.min.css',
            'ams_accounting_kit/static/src/js/account_dashboard.js',
            'ams_accounting_kit/static/src/js/account_asset.js',
            'ams_accounting_kit/static/lib/Chart.bundle.js',
            'ams_accounting_kit/static/lib/Chart.bundle.min.js',
            'ams_accounting_kit/static/lib/Chart.min.js',
            'ams_accounting_kit/static/lib/Chart.js',
            'ams_accounting_kit/static/lib/bootstrap-toggle-master/js/bootstrap-toggle.min.js',
            'ams_accounting_kit/static/src/xml/template.xml',
        ],
    },
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': True,
}