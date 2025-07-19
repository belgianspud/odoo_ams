from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """
    Enhanced configuration settings with AMS accounting options
    """
    _inherit = 'res.config.settings'
    
    # ===================
    # AMS GENERAL SETTINGS
    # ===================
    
    # Organization Configuration
    ams_organization_name = fields.Char('Organization Name', 
        config_parameter='ams_accounting.organization_name',
        help="Full name of your association or organization")
    
    ams_organization_type = fields.Selection([
        ('association', 'Professional Association'),
        ('nonprofit', 'Non-Profit Organization'),
        ('society', 'Professional Society'),
        ('union', 'Trade Union'),
        ('club', 'Club/Social Organization'),
        ('foundation', 'Foundation'),
        ('other', 'Other')
    ], string='Organization Type',
    config_parameter='ams_accounting.organization_type',
    default='association')
    
    ams_tax_exempt_number = fields.Char('Tax Exempt Number',
        config_parameter='ams_accounting.tax_exempt_number',
        help="Tax exemption number for non-profit organizations")
    
    # ===================
    # SUBSCRIPTION SETTINGS
    # ===================
    
    # Default Subscription Configuration
    ams_default_subscription_term = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Default Subscription Term',
    config_parameter='ams_accounting.default_subscription_term',
    default='yearly')
    
    ams_auto_renewal_enabled = fields.Boolean('Enable Auto-Renewal',
        config_parameter='ams_accounting.auto_renewal_enabled',
        default=True,
        help="Enable automatic subscription renewals")
    
    ams_renewal_reminder_days = fields.Integer('Renewal Reminder Days',
        config_parameter='ams_accounting.renewal_reminder_days',
        default=30,
        help="Days before expiry to send renewal reminders")
    
    ams_grace_period_days = fields.Integer('Grace Period Days',
        config_parameter='ams_accounting.grace_period_days',
        default=30,
        help="Grace period after subscription expiry")
    
    # ===================
    # REVENUE RECOGNITION SETTINGS
    # ===================
    
    # Revenue Recognition
    ams_default_revenue_recognition = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('proportional', 'Proportional Over Period')
    ], string='Default Revenue Recognition',
    config_parameter='ams_accounting.default_revenue_recognition',
    default='proportional')
    
    ams_deferred_revenue_account_id = fields.Many2one('account.account', 
        'Default Deferred Revenue Account',
        config_parameter='ams_accounting.deferred_revenue_account_id',
        domain="[('account_type', '=', 'liability_current')]")
    
    ams_subscription_revenue_account_id = fields.Many2one('account.account',
        'Subscription Revenue Account',
        config_parameter='ams_accounting.subscription_revenue_account_id',
        domain="[('account_type', '=', 'income')]")
    
    ams_chapter_revenue_account_id = fields.Many2one('account.account',
        'Chapter Revenue Account',
        config_parameter='ams_accounting.chapter_revenue_account_id',
        domain="[('account_type', '=', 'income')]")
    
    # ===================
    # PAYMENT SETTINGS
    # ===================
    
    # Payment Configuration
    ams_default_payment_terms = fields.Many2one('account.payment.term',
        'Default Payment Terms',
        config_parameter='ams_accounting.default_payment_terms')
    
    ams_late_fee_enabled = fields.Boolean('Enable Late Fees',
        config_parameter='ams_accounting.late_fee_enabled',
        default=False)
    
    ams_late_fee_amount = fields.Float('Late Fee Amount',
        config_parameter='ams_accounting.late_fee_amount',
        default=25.0)
    
    ams_late_fee_percentage = fields.Float('Late Fee Percentage',
        config_parameter='ams_accounting.late_fee_percentage',
        default=0.0,
        help="Percentage of overdue amount to charge as late fee")
    
    ams_late_fee_grace_days = fields.Integer('Late Fee Grace Days',
        config_parameter='ams_accounting.late_fee_grace_days',
        default=15,
        help="Days after due date before applying late fees")
    
    # Payment Methods
    ams_enable_credit_card = fields.Boolean('Enable Credit Card Payments',
        config_parameter='ams_accounting.enable_credit_card',
        default=True)
    
    ams_enable_bank_transfer = fields.Boolean('Enable Bank Transfers',
        config_parameter='ams_accounting.enable_bank_transfer',
        default=True)
    
    ams_enable_check_payments = fields.Boolean('Enable Check Payments',
        config_parameter='ams_accounting.enable_check_payments',
        default=True)
    
    ams_enable_autopay = fields.Boolean('Enable Auto-Pay',
        config_parameter='ams_accounting.enable_autopay',
        default=True)
    
    # ===================
    # CHAPTER SETTINGS
    # ===================
    
    # Chapter Management
    ams_enable_chapters = fields.Boolean('Enable Chapter Management',
        config_parameter='ams_accounting.enable_chapters',
        default=True)
    
    ams_chapter_allocation_enabled = fields.Boolean('Enable Chapter Allocations',
        config_parameter='ams_accounting.chapter_allocation_enabled',
        default=False,
        help="Enable automatic revenue allocation to chapters")
    
    ams_default_chapter_allocation = fields.Float('Default Chapter Allocation %',
        config_parameter='ams_accounting.default_chapter_allocation',
        default=0.0,
        help="Default percentage of revenue to allocate to chapters")
    
    ams_chapter_separate_accounting = fields.Boolean('Chapter Separate Accounting',
        config_parameter='ams_accounting.chapter_separate_accounting',
        default=False,
        help="Enable separate accounting for each chapter")
    
    # ===================
    # FINANCIAL CONTROLS
    # ===================
    
    # Credit Management
    ams_enable_credit_limits = fields.Boolean('Enable Credit Limits',
        config_parameter='ams_accounting.enable_credit_limits',
        default=False)
    
    ams_default_credit_limit = fields.Float('Default Credit Limit',
        config_parameter='ams_accounting.default_credit_limit',
        default=1000.0)
    
    ams_credit_check_enabled = fields.Boolean('Enable Credit Checks',
        config_parameter='ams_accounting.credit_check_enabled',
        default=False,
        help="Check credit limits before creating invoices")
    
    # Approval Workflows
    ams_require_invoice_approval = fields.Boolean('Require Invoice Approval',
        config_parameter='ams_accounting.require_invoice_approval',
        default=False)
    
    ams_invoice_approval_limit = fields.Float('Invoice Approval Limit',
        config_parameter='ams_accounting.invoice_approval_limit',
        default=1000.0,
        help="Invoices above this amount require approval")
    
    ams_require_payment_approval = fields.Boolean('Require Payment Approval',
        config_parameter='ams_accounting.require_payment_approval',
        default=False)
    
    ams_payment_approval_limit = fields.Float('Payment Approval Limit',
        config_parameter='ams_accounting.payment_approval_limit',
        default=500.0)
    
    # ===================
    # COMMUNICATION SETTINGS
    # ===================
    
    # Email Configuration
    ams_send_welcome_emails = fields.Boolean('Send Welcome Emails',
        config_parameter='ams_accounting.send_welcome_emails',
        default=True)
    
    ams_send_renewal_reminders = fields.Boolean('Send Renewal Reminders',
        config_parameter='ams_accounting.send_renewal_reminders',
        default=True)
    
    ams_send_payment_receipts = fields.Boolean('Send Payment Receipts',
        config_parameter='ams_accounting.send_payment_receipts',
        default=True)
    
    ams_send_overdue_notices = fields.Boolean('Send Overdue Notices',
        config_parameter='ams_accounting.send_overdue_notices',
        default=True)
    
    # Email Templates
    ams_welcome_email_template_id = fields.Many2one('mail.template',
        'Welcome Email Template',
        config_parameter='ams_accounting.welcome_email_template_id',
        domain="[('model', '=', 'res.partner')]")
    
    ams_renewal_reminder_template_id = fields.Many2one('mail.template',
        'Renewal Reminder Template',
        config_parameter='ams_accounting.renewal_reminder_template_id',
        domain="[('model', '=', 'ams.subscription')]")
    
    ams_payment_receipt_template_id = fields.Many2one('mail.template',
        'Payment Receipt Template',
        config_parameter='ams_accounting.payment_receipt_template_id',
        domain="[('model', '=', 'account.payment')]")
    
    # ===================
    # REPORTING SETTINGS
    # ===================
    
    # Financial Reporting
    ams_fiscal_year_end = fields.Selection([
        ('december', 'December 31'),
        ('june', 'June 30'),
        ('september', 'September 30'),
        ('march', 'March 31')
    ], string='Fiscal Year End',
    config_parameter='ams_accounting.fiscal_year_end',
    default='december')
    
    ams_enable_fund_accounting = fields.Boolean('Enable Fund Accounting',
        config_parameter='ams_accounting.enable_fund_accounting',
        default=False,
        help="Enable fund-based accounting for non-profits")
    
    ams_enable_grant_tracking = fields.Boolean('Enable Grant Tracking',
        config_parameter='ams_accounting.enable_grant_tracking',
        default=False)
    
    # Dashboard Configuration
    ams_dashboard_refresh_interval = fields.Integer('Dashboard Refresh Interval (minutes)',
        config_parameter='ams_accounting.dashboard_refresh_interval',
        default=15)
    
    # ===================
    # INTEGRATION SETTINGS
    # ===================
    
    # External Integrations
    ams_enable_payment_gateway = fields.Boolean('Enable Payment Gateway',
        config_parameter='ams_accounting.enable_payment_gateway',
        default=False)
    
    ams_payment_gateway_provider = fields.Selection([
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('square', 'Square'),
        ('authorize_net', 'Authorize.Net'),
        ('custom', 'Custom Integration')
    ], string='Payment Gateway Provider',
    config_parameter='ams_accounting.payment_gateway_provider')
    
    ams_enable_bank_sync = fields.Boolean('Enable Bank Synchronization',
        config_parameter='ams_accounting.enable_bank_sync',
        default=False)
    
    # Data Management
    ams_auto_backup_enabled = fields.Boolean('Enable Auto Backup',
        config_parameter='ams_accounting.auto_backup_enabled',
        default=True)
    
    ams_backup_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Backup Frequency',
    config_parameter='ams_accounting.backup_frequency',
    default='weekly')
    
    ams_data_retention_years = fields.Integer('Data Retention Years',
        config_parameter='ams_accounting.data_retention_years',
        default=7,
        help="Number of years to retain financial data")
    
    # ===================
    # SECURITY SETTINGS
    # ===================
    
    # Access Control
    ams_enable_audit_trail = fields.Boolean('Enable Audit Trail',
        config_parameter='ams_accounting.enable_audit_trail',
        default=True)
    
    ams_require_2fa_finance = fields.Boolean('Require 2FA for Finance Users',
        config_parameter='ams_accounting.require_2fa_finance',
        default=False)
    
    ams_session_timeout_minutes = fields.Integer('Session Timeout (minutes)',
        config_parameter='ams_accounting.session_timeout_minutes',
        default=60)
    
    # ===================
    # VALIDATION METHODS
    # ===================
    
    @api.constrains('ams_renewal_reminder_days')
    def _check_renewal_reminder_days(self):
        if self.ams_renewal_reminder_days and self.ams_renewal_reminder_days < 1:
            raise ValidationError(_('Renewal reminder days must be at least 1 day.'))
    
    @api.constrains('ams_grace_period_days')
    def _check_grace_period_days(self):
        if self.ams_grace_period_days and self.ams_grace_period_days < 0:
            raise ValidationError(_('Grace period days cannot be negative.'))
    
    @api.constrains('ams_late_fee_amount', 'ams_late_fee_percentage')
    def _check_late_fee_settings(self):
        if self.ams_late_fee_enabled:
            if self.ams_late_fee_amount < 0:
                raise ValidationError(_('Late fee amount cannot be negative.'))
            if self.ams_late_fee_percentage < 0 or self.ams_late_fee_percentage > 100:
                raise ValidationError(_('Late fee percentage must be between 0 and 100.'))
    
    @api.constrains('ams_default_chapter_allocation')
    def _check_chapter_allocation(self):
        if self.ams_default_chapter_allocation < 0 or self.ams_default_chapter_allocation > 100:
            raise ValidationError(_('Chapter allocation percentage must be between 0 and 100.'))
    
    @api.constrains('ams_default_credit_limit')
    def _check_credit_limit(self):
        if self.ams_default_credit_limit < 0:
            raise ValidationError(_('Default credit limit cannot be negative.'))
    
    @api.constrains('ams_data_retention_years')
    def _check_data_retention(self):
        if self.ams_data_retention_years < 1:
            raise ValidationError(_('Data retention must be at least 1 year.'))
    
    # ===================
    # ONCHANGE METHODS
    # ===================
    
    @api.onchange('ams_late_fee_enabled')
    def _onchange_late_fee_enabled(self):
        if not self.ams_late_fee_enabled:
            self.ams_late_fee_amount = 0.0
            self.ams_late_fee_percentage = 0.0
    
    @api.onchange('ams_enable_chapters')
    def _onchange_enable_chapters(self):
        if not self.ams_enable_chapters:
            self.ams_chapter_allocation_enabled = False
            self.ams_chapter_separate_accounting = False
            self.ams_default_chapter_allocation = 0.0
    
    @api.onchange('ams_enable_credit_limits')
    def _onchange_enable_credit_limits(self):
        if not self.ams_enable_credit_limits:
            self.ams_credit_check_enabled = False
    
    @api.onchange('ams_organization_type')
    def _onchange_organization_type(self):
        """Set defaults based on organization type"""
        if self.ams_organization_type == 'nonprofit':
            self.ams_enable_fund_accounting = True
            self.ams_enable_grant_tracking = True
        elif self.ams_organization_type == 'association':
            self.ams_enable_chapters = True
            self.ams_auto_renewal_enabled = True
    
    # ===================
    # HELPER METHODS
    # ===================
    
    def action_setup_ams_defaults(self):
        """Setup AMS default configuration"""
        try:
            # Create default accounts if they don't exist
            self._create_default_accounts()
            
            # Setup default journals
            self._setup_default_journals()
            
            # Create default email templates
            self._create_default_email_templates()
            
            # Setup default subscription types
            self._setup_default_subscription_types()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('AMS defaults have been configured successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Failed to setup AMS defaults: {str(e)}")
            raise UserError(_('Failed to setup AMS defaults: %s') % str(e))
    
    def _create_default_accounts(self):
        """Create default AMS accounts"""
        company = self.env.company
        
        # Default accounts to create
        default_accounts = [
            {
                'code': 'AMS001',
                'name': 'AMS Subscription Revenue',
                'account_type': 'income',
                'is_ams_subscription_account': True,
            },
            {
                'code': 'AMS002',
                'name': 'AMS Chapter Revenue',
                'account_type': 'income',
                'is_ams_chapter_account': True,
            },
            {
                'code': 'AMS003',
                'name': 'AMS Deferred Revenue',
                'account_type': 'liability_current',
            },
        ]
        
        for account_data in default_accounts:
            existing = self.env['account.account'].search([
                ('code', '=', account_data['code']),
                ('company_id', '=', company.id)
            ])
            
            if not existing:
                account_data['company_id'] = company.id
                self.env['account.account'].create(account_data)
    
    def _setup_default_journals(self):
        """Setup default AMS journals"""
        journal_obj = self.env['account.journal']
        
        # Setup AMS journals if they don't exist
        if not journal_obj.search([('is_ams_journal', '=', True)]):
            journal_obj.setup_ams_journals()
    
    def _create_default_email_templates(self):
        """Create default email templates"""
        # This would create default email templates for AMS
        # Implementation would depend on specific template requirements
        pass
    
    def _setup_default_subscription_types(self):
        """Setup default subscription types"""
        # Ensure basic subscription types exist
        subscription_types = [
            {'name': 'Membership', 'code': 'membership'},
            {'name': 'Chapter', 'code': 'chapter'},
            {'name': 'Publication', 'code': 'publication'},
        ]
        
        for type_data in subscription_types:
            existing = self.env['ams.subscription.type'].search([
                ('code', '=', type_data['code'])
            ])
            
            if not existing:
                self.env['ams.subscription.type'].create(type_data)
    
    def action_reset_ams_settings(self):
        """Reset AMS settings to defaults"""
        default_values = {
            'ams_default_subscription_term': 'yearly',
            'ams_auto_renewal_enabled': True,
            'ams_renewal_reminder_days': 30,
            'ams_grace_period_days': 30,
            'ams_default_revenue_recognition': 'proportional',
            'ams_late_fee_enabled': False,
            'ams_late_fee_amount': 25.0,
            'ams_late_fee_percentage': 0.0,
            'ams_late_fee_grace_days': 15,
            'ams_enable_chapters': True,
            'ams_chapter_allocation_enabled': False,
            'ams_default_chapter_allocation': 0.0,
            'ams_enable_credit_limits': False,
            'ams_default_credit_limit': 1000.0,
            'ams_send_welcome_emails': True,
            'ams_send_renewal_reminders': True,
            'ams_send_payment_receipts': True,
            'ams_fiscal_year_end': 'december',
            'ams_dashboard_refresh_interval': 15,
        }
        
        # Set config parameters
        for key, value in default_values.items():
            param_name = f"ams_accounting.{key.replace('ams_', '')}"
            self.env['ir.config_parameter'].sudo().set_param(param_name, value)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('AMS settings have been reset to defaults.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_test_email_templates(self):
        """Test email template configuration"""
        # This would test if email templates are properly configured
        templates_to_test = [
            self.ams_welcome_email_template_id,
            self.ams_renewal_reminder_template_id,
            self.ams_payment_receipt_template_id,
        ]
        
        missing_templates = []
        for template in templates_to_test:
            if not template:
                missing_templates.append("Missing template")
        
        if missing_templates:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Some email templates are not configured.'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All email templates are properly configured.'),
                    'type': 'success',
                    'sticky': False,
                }
            }