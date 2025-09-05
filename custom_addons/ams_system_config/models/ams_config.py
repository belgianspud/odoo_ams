# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSConfigSettings(models.TransientModel):
    _name = 'ams.config.settings'
    _inherit = 'res.config.settings'
    _description = 'AMS Configuration Settings'

    # Member ID Configuration
    auto_member_id = fields.Boolean(
        string="Auto-generate Member IDs",
        default=True,
        config_parameter='ams.auto_member_id',
        help="Automatically generate unique member IDs for new members"
    )
    member_id_prefix = fields.Char(
        string="Member ID Prefix",
        default="M",
        config_parameter='ams.member_id_prefix',
        help="Prefix for auto-generated member IDs (e.g., 'M' for M000001)"
    )
    member_id_padding = fields.Integer(
        string="Member ID Padding",
        default=6,
        config_parameter='ams.member_id_padding',
        help="Number of digits for member ID sequence (e.g., 6 for 000001)"
    )
    member_id_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Member ID Sequence",
        config_parameter='ams.member_id_sequence_id',
        help="Sequence used for generating member IDs"
    )

    # Membership Lifecycle Rules
    grace_period_days = fields.Integer(
        string="Default Grace Period (Days)",
        default=30,
        config_parameter='ams.grace_period_days',
        help="Default number of days for membership grace period after expiration"
    )
    renewal_window_days = fields.Integer(
        string="Renewal Notice Period (Days)",
        default=90,
        config_parameter='ams.renewal_window_days',
        help="How many days before expiration to start sending renewal notices"
    )
    auto_renewal_enabled = fields.Boolean(
        string="Enable Auto-renewal",
        default=True,
        config_parameter='ams.auto_renewal_enabled',
        help="Allow members to set up automatic membership renewals"
    )
    renewal_reminder_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], string="Renewal Reminder Frequency",
       default='monthly',
       config_parameter='ams.renewal_reminder_frequency',
       help="How often to send renewal reminders during the renewal window")

    # Portal and Communication
    portal_enabled = fields.Boolean(
        string="Enable Member Portal",
        default=True,
        config_parameter='ams.portal_enabled',
        help="Enable self-service member portal functionality"
    )
    communication_opt_out_default = fields.Boolean(
        string="Default Communication Opt-out",
        default=False,
        config_parameter='ams.communication_opt_out_default',
        help="Default setting for new member communication preferences"
    )
    portal_registration_enabled = fields.Boolean(
        string="Allow Portal Self-Registration",
        default=False,
        config_parameter='ams.portal_registration_enabled',
        help="Allow prospects to register through the portal"
    )
    email_verification_required = fields.Boolean(
        string="Require Email Verification",
        default=True,
        config_parameter='ams.email_verification_required',
        help="Require email verification for new portal users"
    )

    # Financial Configuration
    fiscal_year_start = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December')
    ], string="Fiscal Year Start",
       default='january',
       config_parameter='ams.fiscal_year_start',
       help="Month when your association's fiscal year begins")
    
    default_currency_id = fields.Many2one(
        'res.currency',
        string="Default Currency",
        config_parameter='ams.default_currency_id',
        help="Default currency for membership fees and transactions"
    )
    multi_currency_enabled = fields.Boolean(
        string="Enable Multi-Currency",
        default=False,
        config_parameter='ams.multi_currency_enabled',
        help="Allow different currencies for international members"
    )

    # Feature Toggles
    chapter_revenue_sharing = fields.Boolean(
        string="Enable Chapter Revenue Sharing",
        default=False,
        config_parameter='ams.chapter_revenue_sharing',
        help="Enable revenue sharing with local chapters"
    )
    default_chapter_percentage = fields.Float(
        string="Default Chapter Share %",
        default=30.0,
        config_parameter='ams.default_chapter_percentage',
        help="Default percentage of revenue shared with chapters"
    )
    enterprise_subscriptions_enabled = fields.Boolean(
        string="Enable Enterprise Features",
        default=True,
        config_parameter='ams.enterprise_subscriptions_enabled',
        help="Enable enterprise subscription and seat management features"
    )
    continuing_education_required = fields.Boolean(
        string="CE Requirements Active",
        default=False,
        config_parameter='ams.continuing_education_required',
        help="Enable continuing education requirements and tracking"
    )
    fundraising_enabled = fields.Boolean(
        string="Enable Fundraising Features",
        default=True,
        config_parameter='ams.fundraising_enabled',
        help="Enable donation and fundraising campaign features"
    )
    event_member_pricing = fields.Boolean(
        string="Enable Member Event Pricing",
        default=True,
        config_parameter='ams.event_member_pricing',
        help="Enable special pricing for members on events"
    )

    # Data Management
    duplicate_detection_enabled = fields.Boolean(
        string="Enable Duplicate Detection",
        default=True,
        config_parameter='ams.duplicate_detection_enabled',
        help="Automatically detect potential duplicate member records"
    )
    data_retention_years = fields.Integer(
        string="Data Retention Period (Years)",
        default=7,
        config_parameter='ams.data_retention_years',
        help="How many years to retain inactive member data"
    )
    audit_trail_enabled = fields.Boolean(
        string="Enable Audit Trail",
        default=True,
        config_parameter='ams.audit_trail_enabled',
        help="Track changes to member records and important data"
    )

    # Communication Settings
    default_email_template_id = fields.Many2one(
        'mail.template',
        string="Default Email Template",
        config_parameter='ams.default_email_template_id',
        help="Default email template for member communications"
    )
    communication_tracking_enabled = fields.Boolean(
        string="Enable Communication Tracking",
        default=True,
        config_parameter='ams.communication_tracking_enabled',
        help="Track email opens, clicks, and communication history"
    )

    # System Performance
    batch_processing_size = fields.Integer(
        string="Batch Processing Size",
        default=100,
        config_parameter='ams.batch_processing_size',
        help="Number of records to process in batch operations"
    )
    cache_timeout_minutes = fields.Integer(
        string="Cache Timeout (Minutes)",
        default=30,
        config_parameter='ams.cache_timeout_minutes',
        help="How long to cache computed member data"
    )

    @api.constrains('member_id_padding')
    def _check_member_id_padding(self):
        """Validate member ID padding is reasonable"""
        for record in self:
            if record.member_id_padding and (record.member_id_padding < 3 or record.member_id_padding > 10):
                raise ValidationError("Member ID padding must be between 3 and 10 digits")

    @api.constrains('grace_period_days')
    def _check_grace_period_days(self):
        """Validate grace period is reasonable"""
        for record in self:
            if record.grace_period_days and (record.grace_period_days < 0 or record.grace_period_days > 365):
                raise ValidationError("Grace period must be between 0 and 365 days")

    @api.constrains('renewal_window_days')
    def _check_renewal_window_days(self):
        """Validate renewal window is reasonable"""
        for record in self:
            if record.renewal_window_days and (record.renewal_window_days < 7 or record.renewal_window_days > 365):
                raise ValidationError("Renewal window must be between 7 and 365 days")

    @api.constrains('default_chapter_percentage')
    def _check_chapter_percentage(self):
        """Validate chapter percentage is reasonable"""
        for record in self:
            if record.default_chapter_percentage and (record.default_chapter_percentage < 0 or record.default_chapter_percentage > 100):
                raise ValidationError("Chapter percentage must be between 0 and 100")

    @api.constrains('data_retention_years')
    def _check_data_retention_years(self):
        """Validate data retention period"""
        for record in self:
            if record.data_retention_years and (record.data_retention_years < 1 or record.data_retention_years > 50):
                raise ValidationError("Data retention period must be between 1 and 50 years")

    @api.model
    def get_values(self):
        """Override to set default currency if not set"""
        res = super().get_values()
        if not res.get('default_currency_id'):
            company_currency = self.env.company.currency_id
            if company_currency:
                res['default_currency_id'] = company_currency.id
        return res

    def set_values(self):
        """Override to update member ID sequence when settings change"""
        super().set_values()
        
        # Update member ID sequence if settings changed
        if self.member_id_sequence_id and (self.member_id_prefix or self.member_id_padding):
            sequence_vals = {}
            if self.member_id_prefix:
                sequence_vals['prefix'] = self.member_id_prefix
            if self.member_id_padding:
                sequence_vals['padding'] = self.member_id_padding
            
            if sequence_vals:
                self.member_id_sequence_id.write(sequence_vals)

    def action_reset_member_sequence(self):
        """Action to reset member ID sequence"""
        if self.member_id_sequence_id:
            self.member_id_sequence_id.write({'number_next': 1})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Member ID sequence has been reset to 1',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_test_member_id_generation(self):
        """Test member ID generation with current settings"""
        if not self.member_id_sequence_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No member ID sequence configured',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Generate a test ID
        test_id = self.member_id_sequence_id.next_by_id()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Test Member ID generated: {test_id}',
                'type': 'info',
                'sticky': True,
            }
        }

    @api.model
    def get_fiscal_year_dates(self, date=None):
        """Get fiscal year start and end dates for a given date"""
        if date is None:
            date = fields.Date.today()
        
        fiscal_start_month = self.env['ir.config_parameter'].sudo().get_param(
            'ams.fiscal_year_start', 'january'
        )
        
        month_mapping = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        start_month = month_mapping.get(fiscal_start_month, 1)
        
        if date.month >= start_month:
            # Current fiscal year
            start_date = date.replace(month=start_month, day=1)
            if start_month == 1:
                end_date = date.replace(year=date.year + 1, month=1, day=1) - fields.timedelta(days=1)
            else:
                end_date = date.replace(year=date.year + 1, month=start_month, day=1) - fields.timedelta(days=1)
        else:
            # Previous fiscal year
            start_date = date.replace(year=date.year - 1, month=start_month, day=1)
            end_date = date.replace(month=start_month, day=1) - fields.timedelta(days=1)
        
        return start_date, end_date