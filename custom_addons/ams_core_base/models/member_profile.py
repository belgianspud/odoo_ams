# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MemberProfile(models.Model):
    _name = 'ams.member.profile'
    _description = 'Extended Member Profile'
    _rec_name = 'partner_id'
    _order = 'partner_id'

    # ===== CORE LINK =====
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        help="Link to the partner record"
    )

    # ===== EXTENDED DEMOGRAPHICS =====
    ethnicity = fields.Selection([
        ('american_indian', 'American Indian or Alaska Native'),
        ('asian', 'Asian'),
        ('black', 'Black or African American'),
        ('hispanic', 'Hispanic or Latino'),
        ('pacific_islander', 'Native Hawaiian or Other Pacific Islander'),
        ('white', 'White'),
        ('two_or_more', 'Two or More Races'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ], string='Ethnicity')

    graduation_year = fields.Integer(
        string='Graduation Year',
        help="Year of graduation from primary degree program"
    )

    graduation_institution = fields.Char(
        string='Graduation Institution',
        help="Institution where primary degree was obtained"
    )

    # ===== LANGUAGES =====
    language_ids = fields.Many2many(
        'res.lang',
        'member_profile_language_rel',
        'profile_id',
        'language_id',
        string='Languages Spoken',
        help="Languages the member speaks"
    )

    primary_language = fields.Many2one(
        'res.lang',
        string='Primary Language',
        help="Member's primary language"
    )

    # ===== GEOGRAPHIC INFORMATION =====
    time_zone = fields.Selection(
        '_get_timezone_selection',
        string='Time Zone',
        help="Member's time zone"
    )

    geographic_region = fields.Char(
        string='Geographic Region',
        help="Custom geographic region classification"
    )

    # ===== INTERESTS & ENGAGEMENT (Basic) =====
    interests_tags = fields.Many2many(
        'res.partner.category',
        'member_profile_interest_rel',
        'profile_id',
        'category_id',
        string='Interests/Topics',
        domain="[('name', 'ilike', 'interest')]",
        help="Topics and areas of interest"
    )

    volunteer_status = fields.Selection([
        ('available', 'Available for Volunteer Opportunities'),
        ('limited', 'Limited Availability'),
        ('not_available', 'Not Available'),
        ('current_volunteer', 'Current Volunteer'),
    ], string='Volunteer Status', default='not_available')

    volunteer_skills = fields.Text(
        string='Volunteer Skills',
        help="Skills and expertise available for volunteer work"
    )

    # ===== BASIC NOTES =====
    internal_notes = fields.Text(
        string='Internal Notes',
        help="Internal staff notes about the member (not visible to member)"
    )

    member_notes = fields.Text(
        string='Member Notes',
        help="Notes visible to the member"
    )

    # ===== COMPUTED FIELDS =====
    profile_completeness = fields.Float(
        string='Profile Completeness',
        compute='_compute_profile_completeness',
        help="Percentage of profile fields completed"
    )

    @api.model
    def _get_timezone_selection(self):
        """Get list of timezones for selection field"""
        try:
            import pytz
            # Use common timezones to avoid overwhelming the user
            common_timezones = [
                ('UTC', 'UTC'),
                ('US/Eastern', 'US/Eastern'),
                ('US/Central', 'US/Central'),
                ('US/Mountain', 'US/Mountain'),
                ('US/Pacific', 'US/Pacific'),
                ('US/Alaska', 'US/Alaska'),
                ('US/Hawaii', 'US/Hawaii'),
                ('Europe/London', 'Europe/London'),
                ('Europe/Paris', 'Europe/Paris'),
                ('Europe/Berlin', 'Europe/Berlin'),
                ('Europe/Rome', 'Europe/Rome'),
                ('Asia/Tokyo', 'Asia/Tokyo'),
                ('Asia/Shanghai', 'Asia/Shanghai'),
                ('Asia/Dubai', 'Asia/Dubai'),
                ('Asia/Kolkata', 'Asia/Kolkata'),
                ('Australia/Sydney', 'Australia/Sydney'),
                ('Australia/Melbourne', 'Australia/Melbourne'),
            ]
            return common_timezones
        except ImportError:
            # Fallback to basic timezone list if pytz not available
            return [
                ('UTC', 'UTC'),
                ('US/Eastern', 'US/Eastern'),
                ('US/Central', 'US/Central'),
                ('US/Mountain', 'US/Mountain'),
                ('US/Pacific', 'US/Pacific'),
                ('Europe/London', 'Europe/London'),
                ('Europe/Paris', 'Europe/Paris'),
                ('Asia/Tokyo', 'Asia/Tokyo'),
            ]

    @api.depends('graduation_year', 'graduation_institution', 'ethnicity', 
                 'language_ids', 'volunteer_status', 'time_zone', 'geographic_region')
    def _compute_profile_completeness(self):
        """Calculate profile completeness percentage"""
        for profile in self:
            total_fields = 10  # Total number of important profile fields
            completed_fields = 0
            
            # Count completed basic fields
            basic_fields = [
                'graduation_year', 'graduation_institution', 'ethnicity',
                'primary_language', 'time_zone', 'geographic_region',
                'volunteer_status'
            ]
            
            for field_name in basic_fields:
                if getattr(profile, field_name):
                    completed_fields += 1
            
            # Count many2many fields
            if profile.language_ids:
                completed_fields += 1
            if profile.interests_tags:
                completed_fields += 1
            if profile.volunteer_skills:
                completed_fields += 1
            
            profile.profile_completeness = (completed_fields / total_fields) * 100.0

    @api.constrains('graduation_year')
    def _check_graduation_year(self):
        """Validate graduation year is reasonable"""
        current_year = fields.Date.today().year
        for profile in self:
            if profile.graduation_year:
                if profile.graduation_year > current_year + 10:
                    raise ValidationError(
                        _("Graduation year cannot be more than 10 years in the future")
                    )
                if profile.graduation_year < 1900:
                    raise ValidationError(_("Graduation year must be after 1900"))

    @api.constrains('partner_id')
    def _check_partner_unique(self):
        """Ensure one profile per partner"""
        for profile in self:
            if profile.partner_id:
                existing = self.search([
                    ('partner_id', '=', profile.partner_id.id),
                    ('id', '!=', profile.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Partner %s already has a member profile") % 
                        profile.partner_id.name
                    )

    def action_update_profile_completeness(self):
        """Manual action to recalculate profile completeness"""
        self._compute_profile_completeness()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Profile completeness updated: %d%%') % self.profile_completeness,
                'type': 'success',
            }
        }