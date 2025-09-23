# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSSettings(models.Model):
    _name = 'ams.settings'
    _description = 'AMS Global Settings'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Basic Information
    name = fields.Char('Settings Name', required=True, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True,
                          help="Only one settings record can be active at a time")
    company_id = fields.Many2one('res.company', 'Company', 
                               default=lambda self: self.env.company)

    # Member Numbering Configuration
    member_number_prefix = fields.Char('Member Number Prefix', default='M', 
                                     required=True, tracking=True)
    member_number_padding = fields.Integer('Member Number Padding', default=6,
                                         help="Total length of member number including prefix")
    member_number_next = fields.Integer('Next Member Number', compute='_compute_member_number_next',
                                      help="Next member number to be assigned")

    # Status Management Configuration
    auto_status_transitions = fields.Boolean('Auto Status Transitions', default=True, 
                                           tracking=True,
                                           help="Automatically transition member statuses based on dates")
    grace_period_days = fields.Integer('Grace Period (Days)', default=30, required=True,
                                     help="Days after membership expiration before moving to lapsed")
    suspend_period_days = fields.Integer('Suspend Period (Days)', default=60, required=True,
                                       help="Days a member can remain suspended")
    terminate_period_days = fields.Integer('Terminate Period (Days)', default=90, required=True,
                                         help="Days before final termination cleanup")

    # Portal and User Management
    auto_create_portal_users = fields.Boolean('Auto Create Portal Users', default=True,
                                            tracking=True,
                                            help="Automatically create portal users for new members")
    welcome_email_enabled = fields.Boolean('Welcome Email Enabled', default=True,
                                          help="Send welcome email to new members")

    # Communication Defaults
    default_communication_preference = fields.Selection([
        ('email', 'Email Only'),
        ('mail', 'Physical Mail Only'),
        ('both', 'Email and Mail'),
        ('minimal', 'Minimal Contact')
    ], string='Default Communication Preference', default='email',
       help="Default communication preference for new members")
    
    default_newsletter_subscription = fields.Boolean('Default Newsletter Subscription', 
                                                    default=True,
                                                    help="Default newsletter subscription for new members")
    default_directory_listing = fields.Boolean('Default Directory Listing', default=True,
                                              help="Default directory listing preference for new members")

    # Renewal and Expiration Management
    renewal_reminder_enabled = fields.Boolean('Renewal Reminder Enabled', default=True,
                                            help="Send automated renewal reminder emails")
    renewal_reminder_days = fields.Integer('Renewal Reminder Days', default=30,
                                         help="Days before expiration to send renewal reminder")
    expiration_warning_days = fields.Integer('Expiration Warning Days', default=7,
                                           help="Days before expiration to send final warning")

    # Engagement Scoring Configuration
    engagement_scoring_enabled = fields.Boolean('Engagement Scoring Enabled', default=False,
                                               tracking=True,
                                               help="Enable member engagement scoring system")
    default_engagement_score = fields.Float('Default Engagement Score', default=0.0,
                                           help="Starting engagement score for new members")
    engagement_recalc_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], string='Engagement Recalc Frequency', default='weekly',
       help="How often to recalculate engagement scores")

    # Data Management
    data_retention_years = fields.Integer('Data Retention (Years)', default=7,
                                        help="Years to retain member data after termination")
    auto_cleanup_enabled = fields.Boolean('Auto Cleanup Enabled', default=False,
                                        help="Automatically cleanup old data")

    # Integration Settings
    api_enabled = fields.Boolean('API Enabled', default=False,
                                help="Enable REST API access")
    webhook_enabled = fields.Boolean('Webhook Enabled', default=False,
                                    help="Enable outbound webhook notifications")

    # Notes and Documentation
    notes = fields.Text('Configuration Notes',
                       help="Internal notes about this configuration")

    # Computed Fields
    total_active_members = fields.Integer('Total Active Members', compute='_compute_member_stats')
    total_grace_members = fields.Integer('Grace Period Members', compute='_compute_member_stats')
    total_lapsed_members = fields.Integer('Lapsed Members', compute='_compute_member_stats')

    @api.depends('member_number_prefix')
    def _compute_member_number_next(self):
        """Compute next member number from sequence"""
        for setting in self:
            sequence = self.env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
            if sequence:
                setting.member_number_next = sequence.number_next_actual
            else:
                setting.member_number_next = 1

    def _compute_member_stats(self):
        """Compute member statistics"""
        for setting in self:
            Partner = self.env['res.partner']
            setting.total_active_members = Partner.search_count([
                ('is_member', '=', True),
                ('member_status', '=', 'active')
            ])
            setting.total_grace_members = Partner.search_count([
                ('is_member', '=', True),
                ('member_status', '=', 'grace')
            ])
            setting.total_lapsed_members = Partner.search_count([
                ('is_member', '=', True),
                ('member_status', '=', 'lapsed')
            ])

    @api.model
    def create(self, vals):
        """Override create to ensure only one active settings record"""
        if vals.get('active', False):
            # Deactivate all other settings
            self.search([('active', '=', True)]).write({'active': False})
        
        setting = super().create(vals)
        
        # Update member sequence if needed
        if 'member_number_prefix' in vals or 'member_number_padding' in vals:
            setting.action_update_member_sequence()
        
        return setting

    def write(self, vals):
        """Override write to handle active settings logic"""
        if 'active' in vals and vals['active']:
            # Deactivate all other settings
            other_settings = self.search([('active', '=', True), ('id', 'not in', self.ids)])
            other_settings.write({'active': False})
        
        result = super().write(vals)
        
        # Update member sequence if prefix or padding changed
        if 'member_number_prefix' in vals or 'member_number_padding' in vals:
            for setting in self:
                setting.action_update_member_sequence()
        
        return result

    def action_update_member_sequence(self):
        """Update member number sequence based on current settings"""
        self.ensure_one()
        
        sequence = self.env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
        if not sequence:
            # Create sequence if it doesn't exist
            sequence = self.env['ir.sequence'].create({
                'name': 'Member Number Sequence',
                'code': 'ams.member.number',
                'prefix': self.member_number_prefix,
                'padding': self.member_number_padding,
                'number_increment': 1,
                'number_next_actual': 1,
            })
        else:
            # Update existing sequence
            sequence.write({
                'prefix': self.member_number_prefix,
                'padding': self.member_number_padding,
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Member number sequence updated successfully.'),
                'type': 'success'
            }
        }

    def action_reset_engagement_scores(self):
        """Reset all member engagement scores to default"""
        self.ensure_one()
        
        if not self.engagement_scoring_enabled:
            raise UserError(_("Engagement scoring is not enabled."))
        
        members = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_status', 'in', ['active', 'grace'])
        ])
        
        members.write({'engagement_score': self.default_engagement_score})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Reset engagement scores for %d members.') % len(members),
                'type': 'success'
            }
        }

    def action_cleanup_old_data(self):
        """Manually trigger data cleanup process"""
        self.ensure_one()
        
        if not self.auto_cleanup_enabled:
            raise UserError(_("Auto cleanup is not enabled."))
        
        # This would implement data cleanup logic
        # For now, just show a notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Data cleanup functionality will be implemented in future updates.'),
                'type': 'info'
            }
        }

    def get_grace_period_end_date(self, start_date=None):
        """Calculate grace period end date"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        from datetime import timedelta
        return start_date + timedelta(days=self.grace_period_days)

    def get_suspend_end_date(self, start_date=None):
        """Calculate suspend period end date"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        from datetime import timedelta
        return start_date + timedelta(days=self.suspend_period_days)

    def get_terminate_date(self, start_date=None):
        """Calculate termination date"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        from datetime import timedelta
        return start_date + timedelta(days=self.terminate_period_days)

    @api.model
    def get_active_settings(self):
        """Get the currently active settings record"""
        return self.search([('active', '=', True)], limit=1)

    def validate_configuration(self):
        """Validate current configuration and return any issues"""
        self.ensure_one()
        issues = []

        # Check if member sequence exists
        sequence = self.env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
        if not sequence:
            issues.append(_("Member number sequence is not configured."))

        # Check grace period logic
        if self.grace_period_days >= self.suspend_period_days:
            issues.append(_("Grace period should be shorter than suspend period."))
        
        if self.suspend_period_days >= self.terminate_period_days:
            issues.append(_("Suspend period should be shorter than terminate period."))

        # Check engagement scoring
        if self.engagement_scoring_enabled and self.default_engagement_score < 0:
            issues.append(_("Default engagement score should not be negative."))

        # Check renewal reminders
        if self.renewal_reminder_enabled and self.renewal_reminder_days <= 0:
            issues.append(_("Renewal reminder days must be positive."))

        return issues

    # Constraints and Validations
    @api.constrains('member_number_prefix')
    def _check_member_number_prefix(self):
        """Validate member number prefix"""
        for setting in self:
            if not setting.member_number_prefix:
                raise ValidationError(_("Member number prefix is required."))
            if len(setting.member_number_prefix) > 5:
                raise ValidationError(_("Member number prefix cannot exceed 5 characters."))
            if not setting.member_number_prefix.isalnum():
                raise ValidationError(_("Member number prefix can only contain letters and numbers."))

    @api.constrains('member_number_padding')
    def _check_member_number_padding(self):
        """Validate member number padding"""
        for setting in self:
            if setting.member_number_padding < 1:
                raise ValidationError(_("Member number padding must be at least 1."))
            if setting.member_number_padding > 20:
                raise ValidationError(_("Member number padding cannot exceed 20."))

    @api.constrains('grace_period_days', 'suspend_period_days', 'terminate_period_days')
    def _check_period_logic(self):
        """Validate period day logic"""
        for setting in self:
            if setting.grace_period_days < 0:
                raise ValidationError(_("Grace period days cannot be negative."))
            if setting.suspend_period_days < 0:
                raise ValidationError(_("Suspend period days cannot be negative."))
            if setting.terminate_period_days < 0:
                raise ValidationError(_("Terminate period days cannot be negative."))
            
            # Logical order validation
            if setting.grace_period_days >= setting.suspend_period_days:
                raise ValidationError(_("Grace period must be shorter than suspend period."))
            if setting.suspend_period_days >= setting.terminate_period_days:
                raise ValidationError(_("Suspend period must be shorter than terminate period."))

    @api.constrains('renewal_reminder_days', 'expiration_warning_days')
    def _check_reminder_days(self):
        """Validate reminder day settings"""
        for setting in self:
            if setting.renewal_reminder_days < 0:
                raise ValidationError(_("Renewal reminder days cannot be negative."))
            if setting.expiration_warning_days < 0:
                raise ValidationError(_("Expiration warning days cannot be negative."))
            if setting.renewal_reminder_days <= setting.expiration_warning_days:
                raise ValidationError(_("Renewal reminder should be sent before expiration warning."))

    @api.constrains('default_engagement_score')
    def _check_engagement_score(self):
        """Validate default engagement score"""
        for setting in self:
            if setting.default_engagement_score < 0:
                raise ValidationError(_("Default engagement score cannot be negative."))
            if setting.default_engagement_score > 1000:
                raise ValidationError(_("Default engagement score seems unrealistic (>1000)."))

    @api.constrains('data_retention_years')
    def _check_data_retention(self):
        """Validate data retention years"""
        for setting in self:
            if setting.data_retention_years < 1:
                raise ValidationError(_("Data retention must be at least 1 year."))
            if setting.data_retention_years > 50:
                raise ValidationError(_("Data retention period seems excessive (>50 years)."))

    @api.constrains('active')
    def _check_one_active_setting(self):
        """Ensure only one active setting exists"""
        if self.search_count([('active', '=', True)]) > 1:
            raise ValidationError(_("Only one AMS setting can be active at a time."))

    def copy(self, default=None):
        """Override copy to handle unique active constraint"""
        if default is None:
            default = {}
        default.update({
            'name': _("%s (copy)") % self.name,
            'active': False,  # Copies are inactive by default
        })
        return super().copy(default)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_active(self):
        """Prevent deletion of active settings"""
        if self.filtered('active'):
            raise UserError(_("Cannot delete active AMS settings. Deactivate first."))