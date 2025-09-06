# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AMSConfigSettings(models.TransientModel):
    """Global AMS configuration settings."""
    
    _name = 'ams.config.settings'
    _inherit = 'res.config.settings'
    _description = 'AMS System Configuration'


    # ========================================================================
    # MEMBERSHIP CONFIGURATION FIELDS
    # ========================================================================
    
    auto_member_id = fields.Boolean(
        string='Auto-Generate Member IDs',
        default=True,
        config_parameter='ams_system_config.auto_member_id',
        help="Automatically assign unique member IDs to new members"
    )
    
    member_id_prefix = fields.Char(
        string='Member ID Prefix',
        default='M',
        config_parameter='ams_system_config.member_id_prefix',
        help="Prefix for auto-generated member IDs"
    )
    
    member_id_sequence = fields.Many2one(
        'ir.sequence',
        string='Member ID Sequence',
        config_parameter='ams_system_config.member_id_sequence_id',
        default_model='ams.config.settings',
        help="Sequence used for member ID generation"
    )
    
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        config_parameter='ams_system_config.grace_period_days',
        help="Default grace period for expired memberships"
    )
    
    renewal_window_days = fields.Integer(
        string='Renewal Notice Window (Days)',
        default=90,
        config_parameter='ams_system_config.renewal_window_days',
        help="Days before expiration to send renewal notices"
    )
    
    allow_multiple_memberships = fields.Boolean(
        string='Allow Multiple Active Memberships',
        default=False,
        config_parameter='ams_system_config.allow_multiple_memberships',
        help="Whether members can hold multiple active memberships"
    )

    # ========================================================================
    # COMMUNICATION & PORTAL CONFIGURATION FIELDS
    # ========================================================================
    
    portal_enabled = fields.Boolean(
        string='Enable Member Portal',
        default=True,
        config_parameter='ams_system_config.portal_enabled',
        help="Enable member self-service portal"
    )
    
    portal_self_registration = fields.Boolean(
        string='Allow Portal Self-Registration',
        default=False,
        config_parameter='ams_system_config.portal_self_registration',
        help="Allow new members to register through portal"
    )
    
    communication_opt_out_default = fields.Boolean(
        string='Default Communication Opt-Out',
        default=False,
        config_parameter='ams_system_config.communication_opt_out_default',
        help="Default opt-out status for new member communications"
    )
    
    emergency_communications_override = fields.Boolean(
        string='Emergency Communications Override',
        default=True,
        config_parameter='ams_system_config.emergency_communications_override',
        help="Allow emergency communications regardless of preferences"
    )
    
    notification_digest_frequency = fields.Selection([
        ('immediate', 'Immediate'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest')
    ], string='Default Notification Frequency', 
       default='immediate',
       config_parameter='ams_system_config.notification_digest_frequency')

    # ========================================================================
    # FINANCIAL SYSTEM CONFIGURATION FIELDS
    # ========================================================================
    
    default_currency_id = fields.Many2one(
        'res.currency',
        string='Default Currency',
        config_parameter='ams_system_config.default_currency_id',
        help="Primary currency for membership dues and transactions",
        default_model = 'ams.config.settings'
    )
    
    fiscal_year_start = fields.Selection([
        ('january', 'January'),
        ('july', 'July'),
        ('october', 'October'),
        ('april', 'April')
    ], string='Fiscal Year Start', 
       default='january',
       config_parameter='ams_system_config.fiscal_year_start')
    
    chapter_revenue_sharing = fields.Boolean(
        string='Enable Chapter Revenue Sharing',
        default=False,
        config_parameter='ams_system_config.chapter_revenue_sharing',
        help="Enable revenue sharing with local chapters"
    )
    
    default_chapter_percentage = fields.Float(
        string='Default Chapter Revenue Share %',
        default=30.0,
        config_parameter='ams_system_config.default_chapter_percentage',
        help="Default percentage of revenue shared with chapters",
        default_model = 'ams.config.settings.default_chapter_percentage'
    )

    # ========================================================================
    # FEATURE TOGGLE FIELDS
    # ========================================================================
    
    enterprise_subscriptions_enabled = fields.Boolean(
        string='Enable Enterprise Subscriptions',
        default=True,
        config_parameter='ams_system_config.enterprise_subscriptions_enabled',
        help="Enable enterprise seat management features"
    )
    
    continuing_education_required = fields.Boolean(
        string='Continuing Education Required',
        default=False,
        config_parameter='ams_system_config.continuing_education_required',
        help="Require CE credits for membership maintenance"
    )
    
    fundraising_enabled = fields.Boolean(
        string='Enable Fundraising Features',
        default=True,
        config_parameter='ams_system_config.fundraising_enabled',
        help="Enable donation and campaign management"
    )
    
    event_member_pricing = fields.Boolean(
        string='Enable Member Event Pricing',
        default=True,
        config_parameter='ams_system_config.event_member_pricing',
        help="Enable special pricing for members at events"
    )

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('grace_period_days')
    def _check_grace_period_days(self):
        """Validate grace period is within acceptable limits."""
        for record in self:
            if record.grace_period_days and (record.grace_period_days < 0 or record.grace_period_days > 365):
                raise ValidationError(_("Grace period must be between 0 and 365 days"))

    @api.constrains('renewal_window_days')
    def _check_renewal_window_days(self):
        """Validate renewal window is within acceptable limits."""
        for record in self:
            if record.renewal_window_days and (record.renewal_window_days < 0 or record.renewal_window_days > 365):
                raise ValidationError(_("Renewal window must be between 0 and 365 days"))

    @api.constrains('default_chapter_percentage')
    def _check_chapter_percentage(self):
        """Validate chapter revenue percentage is valid."""
        for record in self:
            if record.default_chapter_percentage and (record.default_chapter_percentage < 0 or record.default_chapter_percentage > 100):
                raise ValidationError(_("Chapter revenue percentage must be between 0 and 100"))

    @api.constrains('member_id_prefix')
    def _check_member_id_prefix(self):
        """Validate member ID prefix format."""
        for record in self:
            if record.auto_member_id and record.member_id_prefix:
                if len(record.member_id_prefix) > 10:
                    raise ValidationError(_("Member ID prefix cannot be longer than 10 characters"))
                if not record.member_id_prefix.isalnum():
                    raise ValidationError(_("Member ID prefix must contain only letters and numbers"))

    @api.constrains('continuing_education_required')
    def _check_ce_requirements(self):
        """Check if CE module is available when CE is required."""
        for record in self:
            if record.continuing_education_required:
                ce_module = self.env['ir.module.module'].search([
                    ('name', '=', 'ams_education_credits'),
                    ('state', '=', 'installed')
                ])
                if not ce_module:
                    raise ValidationError(_(
                        "Continuing Education requires the 'ams_education_credits' module to be installed. "
                        "Please install the module first or disable this requirement."
                    ))

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('auto_member_id')
    def _onchange_auto_member_id(self):
        """Handle member ID generation toggle changes."""
        if not self.auto_member_id:
            self.member_id_prefix = False
            self.member_id_sequence = False

    @api.onchange('chapter_revenue_sharing')
    def _onchange_chapter_revenue_sharing(self):
        """Handle chapter revenue sharing toggle changes."""
        if not self.chapter_revenue_sharing:
            self.default_chapter_percentage = 0.0

    @api.onchange('portal_enabled')
    def _onchange_portal_enabled(self):
        """Handle portal enablement changes."""
        if not self.portal_enabled:
            self.portal_self_registration = False

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @api.model
    def get_global_setting(self, setting_name, default=None):
        """Retrieve global AMS setting value.
        
        Args:
            setting_name (str): Name of the configuration parameter
            default: Default value if setting not found
            
        Returns:
            The setting value or default
        """
        param_name = f'ams_system_config.{setting_name}'
        return self.env['ir.config_parameter'].sudo().get_param(param_name, default)

    @api.model
    def set_global_setting(self, setting_name, value):
        """Set global AMS setting value.
        
        Args:
            setting_name (str): Name of the configuration parameter
            value: Value to set
        """
        param_name = f'ams_system_config.{setting_name}'
        self.env['ir.config_parameter'].sudo().set_param(param_name, value)

    @api.model
    def get_member_id_format(self):
        """Get the complete member ID format configuration.
        
        Returns:
            dict: Configuration for member ID generation
        """
        return {
            'auto_generate': self.get_global_setting('auto_member_id', True),
            'prefix': self.get_global_setting('member_id_prefix', 'M'),
            'sequence_id': self.get_global_setting('member_id_sequence_id', False),
        }

    @api.model
    def get_membership_policies(self):
        """Get membership lifecycle policy configuration.
        
        Returns:
            dict: Membership policy settings
        """
        return {
            'grace_period_days': int(self.get_global_setting('grace_period_days', 30)),
            'renewal_window_days': int(self.get_global_setting('renewal_window_days', 90)),
            'allow_multiple': self.get_global_setting('allow_multiple_memberships', False),
        }

    @api.model
    def get_portal_configuration(self):
        """Get portal access configuration.
        
        Returns:
            dict: Portal configuration settings
        """
        return {
            'enabled': self.get_global_setting('portal_enabled', True),
            'self_registration': self.get_global_setting('portal_self_registration', False),
        }

    @api.model
    def get_feature_flags(self):
        """Get all feature toggle states.
        
        Returns:
            dict: Feature enablement flags
        """
        return {
            'enterprise_subscriptions': self.get_global_setting('enterprise_subscriptions_enabled', True),
            'continuing_education': self.get_global_setting('continuing_education_required', False),
            'fundraising': self.get_global_setting('fundraising_enabled', True),
            'event_member_pricing': self.get_global_setting('event_member_pricing', True),
            'chapter_revenue_sharing': self.get_global_setting('chapter_revenue_sharing', False),
        }

    @api.model
    def validate_system_configuration(self):
        """Validate critical system configuration.
        
        Returns:
            list: List of validation errors, empty if all valid
        """
        errors = []
        
        # Check currency configuration
        if not self.get_global_setting('default_currency_id'):
            errors.append(_("Default currency must be configured"))
        
        # Validate member ID settings
        if self.get_global_setting('auto_member_id', True):
            if not self.get_global_setting('member_id_prefix'):
                errors.append(_("Member ID prefix required when auto-generation enabled"))
        
        # Check feature dependencies
        if self.get_global_setting('continuing_education_required', False):
            if not self.get_global_setting('portal_enabled', True):
                errors.append(_("Portal must be enabled for CE management"))
        
        return errors

    # ========================================================================
    # MODEL CREATION HOOKS
    # ========================================================================
    
    def set_values(self):
        """Override to handle special configuration actions."""
        _logger.info("Setting values - currency: %s", self.default_currency_id)

        super().set_values()
        _logger.info("Values set successfully")        
        # Create member ID sequence if auto generation is enabled and no sequence exists
        if self.auto_member_id and not self.member_id_sequence:
            sequence = self._create_member_id_sequence()
            if sequence:
                self.env['ir.config_parameter'].sudo().set_param(
                    'ams_system_config.member_id_sequence_id', 
                    sequence.id
                )

    def _create_member_id_sequence(self):
        """Create the member ID sequence if it doesn't exist.
        
        Returns:
            ir.sequence: Created sequence record
        """
        sequence_vals = {
            'name': 'AMS Member ID',
            'code': 'ams.member.id',
            'prefix': self.member_id_prefix or 'M',
            'suffix': '',
            'padding': 6,
            'number_increment': 1,
            'number_next_actual': 1,
            'use_date_range': False,
            'company_id': False,  # Global sequence
        }
        
        # Check if sequence already exists
        existing_sequence = self.env['ir.sequence'].search([
            ('code', '=', 'ams.member.id')
        ], limit=1)
        
        if existing_sequence:
            # Update existing sequence with new prefix if needed
            if existing_sequence.prefix != sequence_vals['prefix']:
                existing_sequence.write({'prefix': sequence_vals['prefix']})
            return existing_sequence
        
        return self.env['ir.sequence'].create(sequence_vals)