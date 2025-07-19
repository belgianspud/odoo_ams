from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """
    Enhanced company model with AMS-specific accounting features and configurations
    """
    _inherit = 'res.company'
    
    # ========================
    # AMS ORGANIZATION SETTINGS
    # ========================
    
    # Organization Classification
    organization_type = fields.Selection([
        ('association', 'Professional Association'),
        ('nonprofit', 'Non-Profit Organization'),
        ('society', 'Professional Society'),
        ('union', 'Trade Union'),
        ('club', 'Club/Social Organization'),
        ('foundation', 'Foundation'),
        ('chamber', 'Chamber of Commerce'),
        ('federation', 'Federation'),
        ('institute', 'Institute'),
        ('other', 'Other')
    ], string='Organization Type', default='association')
    
    # Tax-Exempt Status
    is_tax_exempt = fields.Boolean('Tax Exempt Organization', default=False)
    tax_exempt_number = fields.Char('Tax Exempt Number',
        help="Federal tax exemption number (e.g., EIN for 501(c) organizations)")
    tax_exempt_type = fields.Selection([
        ('501c3', '501(c)(3) - Charitable'),
        ('501c6', '501(c)(6) - Business League'),
        ('501c7', '501(c)(7) - Social Club'),
        ('501c4', '501(c)(4) - Social Welfare'),
        ('other', 'Other Tax-Exempt Status')
    ], string='Tax Exempt Type')
    
    # Professional Licensing
    professional_license_number = fields.Char('Professional License Number')
    licensing_authority = fields.Char('Licensing Authority')
    license_expiry_date = fields.Date('License Expiry Date')
    
    # ========================
    # AMS ACCOUNTING CONFIGURATION
    # ========================
    
    # Default Accounts for AMS Operations
    ams_subscription_revenue_account_id = fields.Many2one('account.account',
        'AMS Subscription Revenue Account',
        domain="[('account_type', '=', 'income'), ('company_id', '=', id)]",
        help="Default account for subscription revenue")
    
    ams_chapter_revenue_account_id = fields.Many2one('account.account',
        'AMS Chapter Revenue Account',
        domain="[('account_type', '=', 'income'), ('company_id', '=', id)]",
        help="Default account for chapter fee revenue")
    
    ams_deferred_revenue_account_id = fields.Many2one('account.account',
        'AMS Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current'), ('company_id', '=', id)]",
        help="Default account for deferred revenue recognition")
    
    ams_member_receivable_account_id = fields.Many2one('account.account',
        'AMS Member Receivables Account',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', id)]",
        help="Default receivables account for member transactions")
    
    ams_chapter_allocation_account_id = fields.Many2one('account.account',
        'Chapter Allocation Account',
        domain="[('account_type', '=', 'liability_current'), ('company_id', '=', id)]",
        help="Account for chapter revenue allocations")
    
    # Default Journals for AMS Operations
    ams_subscription_journal_id = fields.Many2one('account.journal',
        'AMS Subscription Journal',
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]")
    
    ams_payment_journal_id = fields.Many2one('account.journal',
        'AMS Payment Journal',
        domain="[('type', 'in', ['cash', 'bank']), ('company_id', '=', id)]")
    
    ams_refund_journal_id = fields.Many2one('account.journal',
        'AMS Refund Journal',
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]")
    
    # ========================
    # FINANCIAL POLICIES
    # ========================
    
    # Revenue Recognition Policies
    default_revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('proportional', 'Proportional Over Period')
    ], string='Default Revenue Recognition Method', default='proportional')
    
    # Payment and Credit Policies
    default_payment_terms_id = fields.Many2one('account.payment.term',
        'Default Payment Terms for Members')
    
    default_credit_limit = fields.Float('Default Member Credit Limit', default=1000.0)
    
    enable_credit_checks = fields.Boolean('Enable Credit Checks', default=False,
        help="Check member credit limits before creating invoices")
    
    # Late Fee Policies
    enable_late_fees = fields.Boolean('Enable Late Fees', default=False)
    late_fee_amount = fields.Float('Late Fee Amount', default=25.0)
    late_fee_percentage = fields.Float('Late Fee Percentage', default=0.0,
        help="Percentage of overdue amount")
    late_fee_grace_period = fields.Integer('Late Fee Grace Period (Days)', default=15)
    
    # ========================
    # SUBSCRIPTION POLICIES
    # ========================
    
    # Default Subscription Settings
    default_subscription_term = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Default Subscription Term', default='yearly')
    
    auto_renewal_enabled = fields.Boolean('Enable Auto-Renewal', default=True)
    renewal_reminder_days = fields.Integer('Renewal Reminder Days', default=30,
        help="Days before expiry to send renewal reminders")
    grace_period_days = fields.Integer('Grace Period Days', default=30,
        help="Days after expiry before marking subscription as expired")
    
    # ========================
    # CHAPTER MANAGEMENT
    # ========================
    
    # Chapter Configuration
    enable_chapter_management = fields.Boolean('Enable Chapter Management', default=True)
    chapter_allocation_enabled = fields.Boolean('Enable Chapter Allocations', default=False)
    default_chapter_allocation_percentage = fields.Float('Default Chapter Allocation %', default=0.0)
    
    # Multi-Chapter Settings
    allow_multiple_chapters = fields.Boolean('Allow Multiple Chapter Memberships', default=True)
    require_primary_chapter = fields.Boolean('Require Primary Chapter', default=False)
    
    # ========================
    # APPROVAL WORKFLOWS
    # ========================
    
    # Invoice Approval
    require_invoice_approval = fields.Boolean('Require Invoice Approval', default=False)
    invoice_approval_limit = fields.Float('Invoice Approval Limit', default=1000.0)
    
    # Payment Approval
    require_payment_approval = fields.Boolean('Require Payment Approval', default=False)
    payment_approval_limit = fields.Float('Payment Approval Limit', default=500.0)
    
    # Refund Approval
    require_refund_approval = fields.Boolean('Require Refund Approval', default=True)
    refund_approval_limit = fields.Float('Refund Approval Limit', default=100.0)
    
    # ========================
    # COMMUNICATION SETTINGS
    # ========================
    
    # Email Configuration
    send_welcome_emails = fields.Boolean('Send Welcome Emails', default=True)
    send_renewal_reminders = fields.Boolean('Send Renewal Reminders', default=True)
    send_payment_receipts = fields.Boolean('Send Payment Receipts', default=True)
    send_overdue_notices = fields.Boolean('Send Overdue Notices', default=True)
    
    # Member Portal Settings
    enable_member_portal = fields.Boolean('Enable Member Portal', default=True)
    portal_allow_payment = fields.Boolean('Allow Portal Payments', default=True)
    portal_allow_subscription_changes = fields.Boolean('Allow Subscription Changes', default=False)
    
    # ========================
    # FINANCIAL REPORTING
    # ========================
    
    # Fiscal Year Configuration
    ams_fiscal_year_end = fields.Selection([
        ('december', 'December 31'),
        ('june', 'June 30'),
        ('september', 'September 30'),
        ('march', 'March 31')
    ], string='AMS Fiscal Year End', default='december')
    
    # Fund Accounting (for Non-Profits)
    enable_fund_accounting = fields.Boolean('Enable Fund Accounting', default=False)
    enable_grant_tracking = fields.Boolean('Enable Grant Tracking', default=False)
    enable_donor_tracking = fields.Boolean('Enable Donor Tracking', default=False)
    
    # ========================
    # COMPLIANCE AND REPORTING
    # ========================
    
    # Regulatory Compliance
    enable_audit_trail = fields.Boolean('Enable Audit Trail', default=True)
    require_financial_approvals = fields.Boolean('Require Financial Approvals', default=False)
    
    # Tax Reporting
    annual_filing_required = fields.Boolean('Annual Filing Required', default=True)
    annual_filing_deadline = fields.Selection([
        ('march_15', 'March 15'),
        ('may_15', 'May 15'),
        ('november_15', 'November 15'),
        ('custom', 'Custom Date')
    ], string='Annual Filing Deadline')
    custom_filing_deadline = fields.Char('Custom Filing Deadline')
    
    # ========================
    # STATISTICS AND ANALYTICS
    # ========================
    
    # Computed Statistics
    total_active_members = fields.Integer('Total Active Members', compute='_compute_member_statistics')
    total_active_subscriptions = fields.Integer('Total Active Subscriptions', compute='_compute_subscription_statistics')
    total_chapters = fields.Integer('Total Chapters', compute='_compute_chapter_statistics')
    
    # Financial Statistics
    current_month_revenue = fields.Float('Current Month Revenue', compute='_compute_financial_statistics')
    current_year_revenue = fields.Float('Current Year Revenue', compute='_compute_financial_statistics')
    outstanding_receivables = fields.Float('Outstanding Receivables', compute='_compute_financial_statistics')
    
    @api.depends('partner_ids')
    def _compute_member_statistics(self):
        for company in self:
            # Count active members for this company
            active_members = self.env['res.partner'].search_count([
                ('is_ams_member', '=', True),
                ('member_status', '=', 'active'),
                ('company_id', '=', company.id)
            ])
            company.total_active_members = active_members
    
    def _compute_subscription_statistics(self):
        for company in self:
            # Count active subscriptions for this company
            active_subscriptions = self.env['ams.subscription'].search_count([
                ('state', '=', 'active'),
                ('partner_id.company_id', '=', company.id)
            ])
            company.total_active_subscriptions = active_subscriptions
    
    def _compute_chapter_statistics(self):
        for company in self:
            # Count chapters for this company
            chapters = self.env['ams.chapter'].search_count([
                ('active', '=', True)
            ])
            company.total_chapters = chapters
    
    def _compute_financial_statistics(self):
        for company in self:
            # Current month revenue
            current_month_start = fields.Date.today().replace(day=1)
            current_month_revenue = self.env['account.move.line'].search([
                ('company_id', '=', company.id),
                ('account_id.account_type', '=', 'income'),
                ('date', '>=', current_month_start),
                ('move_id.state', '=', 'posted'),
                ('move_id.is_ams_subscription_invoice', '=', True)
            ])
            company.current_month_revenue = sum(current_month_revenue.mapped('credit')) - sum(current_month_revenue.mapped('debit'))
            
            # Current year revenue
            current_year_start = fields.Date.today().replace(month=1, day=1)
            current_year_revenue = self.env['account.move.line'].search([
                ('company_id', '=', company.id),
                ('account_id.account_type', '=', 'income'),
                ('date', '>=', current_year_start),
                ('move_id.state', '=', 'posted'),
                ('move_id.is_ams_subscription_invoice', '=', True)
            ])
            company.current_year_revenue = sum(current_year_revenue.mapped('credit')) - sum(current_year_revenue.mapped('debit'))
            
            # Outstanding receivables
            outstanding_invoices = self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('is_ams_subscription_invoice', '=', True)
            ])
            company.outstanding_receivables = sum(outstanding_invoices.mapped('amount_residual'))
    
    # ========================
    # BUSINESS METHODS
    # ========================
    
    def action_setup_ams_accounts(self):
        """Setup default AMS accounts for this company"""
        try:
            self._create_ams_accounts()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('AMS accounts have been created successfully.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to create AMS accounts: {str(e)}")
            raise UserError(_('Failed to create AMS accounts: %s') % str(e))
    
    def _create_ams_accounts(self):
        """Create default AMS accounts"""
        account_obj = self.env['account.account']
        
        # Default AMS accounts configuration
        ams_accounts = [
            {
                'code': '4100',
                'name': 'AMS Subscription Revenue',
                'account_type': 'income',
                'is_ams_subscription_account': True,
            },
            {
                'code': '4110',
                'name': 'AMS Chapter Revenue',
                'account_type': 'income',
                'is_ams_chapter_account': True,
            },
            {
                'code': '2300',
                'name': 'AMS Deferred Revenue',
                'account_type': 'liability_current',
            },
            {
                'code': '1200',
                'name': 'AMS Member Receivables',
                'account_type': 'asset_receivable',
            },
            {
                'code': '2310',
                'name': 'Chapter Allocations Payable',
                'account_type': 'liability_current',
            },
        ]
        
        created_accounts = {}
        
        for account_data in ams_accounts:
            # Check if account already exists
            existing_account = account_obj.search([
                ('code', '=', account_data['code']),
                ('company_id', '=', self.id)
            ])
            
            if not existing_account:
                account_data['company_id'] = self.id
                account = account_obj.create(account_data)
                created_accounts[account_data['name']] = account
            else:
                created_accounts[account_data['name']] = existing_account
        
        # Update company default accounts
        if 'AMS Subscription Revenue' in created_accounts:
            self.ams_subscription_revenue_account_id = created_accounts['AMS Subscription Revenue'].id
        
        if 'AMS Chapter Revenue' in created_accounts:
            self.ams_chapter_revenue_account_id = created_accounts['AMS Chapter Revenue'].id
        
        if 'AMS Deferred Revenue' in created_accounts:
            self.ams_deferred_revenue_account_id = created_accounts['AMS Deferred Revenue'].id
        
        if 'AMS Member Receivables' in created_accounts:
            self.ams_member_receivable_account_id = created_accounts['AMS Member Receivables'].id
        
        if 'Chapter Allocations Payable' in created_accounts:
            self.ams_chapter_allocation_account_id = created_accounts['Chapter Allocations Payable'].id
        
        return created_accounts
    
    def action_setup_ams_journals(self):
        """Setup default AMS journals"""
        try:
            self._create_ams_journals()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('AMS journals have been created successfully.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Failed to create AMS journals: {str(e)}")
            raise UserError(_('Failed to create AMS journals: %s') % str(e))
    
    def _create_ams_journals(self):
        """Create default AMS journals"""
        journal_obj = self.env['account.journal']
        
        # Use the existing setup method
        created_journals = journal_obj.setup_ams_journals()
        
        # Update company default journals
        for journal in created_journals:
            if journal.ams_journal_type == 'subscription':
                self.ams_subscription_journal_id = journal.id
            elif journal.ams_journal_type == 'payment':
                self.ams_payment_journal_id = journal.id
        
        return created_journals
    
    def action_view_member_dashboard(self):
        """View member management dashboard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Member Management Dashboard',
            'res_model': 'ams.member.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_company_id': self.id}
        }
    
    def action_view_financial_dashboard(self):
        """View AMS financial dashboard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'AMS Financial Dashboard',
            'res_model': 'ams.financial.dashboard',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_company_id': self.id}
        }
    
    def get_ams_configuration_status(self):
        """Get AMS configuration completion status"""
        config_items = {
            'accounts_configured': bool(
                self.ams_subscription_revenue_account_id and
                self.ams_deferred_revenue_account_id and
                self.ams_member_receivable_account_id
            ),
            'journals_configured': bool(
                self.ams_subscription_journal_id and
                self.ams_payment_journal_id
            ),
            'payment_terms_set': bool(self.default_payment_terms_id),
            'organization_type_set': bool(self.organization_type),
            'fiscal_year_set': bool(self.ams_fiscal_year_end),
            'email_settings_configured': bool(
                self.send_welcome_emails or
                self.send_renewal_reminders or
                self.send_payment_receipts
            )
        }
        
        completed_items = sum(config_items.values())
        total_items = len(config_items)
        completion_percentage = (completed_items / total_items) * 100
        
        return {
            'completion_percentage': completion_percentage,
            'completed_items': completed_items,
            'total_items': total_items,
            'config_items': config_items,
            'is_fully_configured': completion_percentage == 100
        }
    
    # ========================
    # VALIDATION METHODS
    # ========================
    
    @api.constrains('default_credit_limit')
    def _check_default_credit_limit(self):
        if self.default_credit_limit < 0:
            raise ValidationError(_('Default credit limit cannot be negative.'))
    
    @api.constrains('late_fee_amount', 'late_fee_percentage')
    def _check_late_fee_settings(self):
        if self.enable_late_fees:
            if self.late_fee_amount < 0:
                raise ValidationError(_('Late fee amount cannot be negative.'))
            if self.late_fee_percentage < 0 or self.late_fee_percentage > 100:
                raise ValidationError(_('Late fee percentage must be between 0 and 100.'))
    
    @api.constrains('default_chapter_allocation_percentage')
    def _check_chapter_allocation_percentage(self):
        if self.default_chapter_allocation_percentage < 0 or self.default_chapter_allocation_percentage > 100:
            raise ValidationError(_('Chapter allocation percentage must be between 0 and 100.'))
    
    @api.constrains('renewal_reminder_days', 'grace_period_days')
    def _check_subscription_days(self):
        if self.renewal_reminder_days < 0:
            raise ValidationError(_('Renewal reminder days cannot be negative.'))
        if self.grace_period_days < 0:
            raise ValidationError(_('Grace period days cannot be negative.'))
    
    # ========================
    # ONCHANGE METHODS
    # ========================
    
    @api.onchange('organization_type')
    def _onchange_organization_type(self):
        """Set defaults based on organization type"""
        if self.organization_type in ['nonprofit', 'foundation']:
            self.is_tax_exempt = True
            self.enable_fund_accounting = True
            self.enable_grant_tracking = True
            self.enable_donor_tracking = True
        elif self.organization_type == 'association':
            self.enable_chapter_management = True
            self.auto_renewal_enabled = True
    
    @api.onchange('is_tax_exempt')
    def _onchange_is_tax_exempt(self):
        """Clear tax exempt settings if not tax exempt"""
        if not self.is_tax_exempt:
            self.tax_exempt_number = False
            self.tax_exempt_type = False
    
    @api.onchange('enable_late_fees')
    def _onchange_enable_late_fees(self):
        """Clear late fee settings if disabled"""
        if not self.enable_late_fees:
            self.late_fee_amount = 0.0
            self.late_fee_percentage = 0.0
    
    @api.onchange('enable_chapter_management')
    def _onchange_enable_chapter_management(self):
        """Clear chapter settings if disabled"""
        if not self.enable_chapter_management:
            self.chapter_allocation_enabled = False
            self.default_chapter_allocation_percentage = 0.0
            self.allow_multiple_chapters = False
            self.require_primary_chapter = False