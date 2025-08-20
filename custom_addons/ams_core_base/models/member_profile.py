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

    # ===== SOCIAL MEDIA & PROFESSIONAL NETWORKS =====
    linkedin_url = fields.Char(
        string='LinkedIn Profile',
        help="LinkedIn profile URL"
    )

    twitter_handle = fields.Char(
        string='Twitter/X Handle',
        help="Twitter or X social media handle"
    )

    researchgate_url = fields.Char(
        string='ResearchGate Profile',
        help="ResearchGate profile URL"
    )

    orcid_id = fields.Char(
        string='ORCID ID',
        help="Open Researcher and Contributor ID"
    )

    other_social_media = fields.Text(
        string='Other Social Media',
        help="Other social media profiles or professional networks"
    )

    # ===== ENGAGEMENT & INTERESTS =====
    interests_tags = fields.Many2many(
        'res.partner.category',
        'member_profile_interest_rel',
        string='Interests/Topics',
        domain="[('category_type', '=', 'interest')]",
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

    # ===== PRIVACY & PREFERENCES =====
    photo_permission = fields.Boolean(
        string='Photo Permission',
        default=False,
        help="Permission to use member's photo in publications"
    )

    marketing_consent = fields.Boolean(
        string='Marketing Consent',
        default=True,
        help="Consent to receive marketing communications"
    )

    directory_listing_consent = fields.Boolean(
        string='Directory Listing Consent',
        default=True,
        help="Consent to appear in member directory"
    )

    data_sharing_consent = fields.Boolean(
        string='Data Sharing Consent',
        default=False,
        help="Consent to share data with partner organizations"
    )

    # ===== PROFESSIONAL DEVELOPMENT =====
    continuing_education_hours = fields.Float(
        string='CE Hours This Year',
        default=0.0,
        help="Continuing education hours completed this year"
    )

    ce_hours_required = fields.Float(
        string='CE Hours Required',
        default=0.0,
        help="Continuing education hours required annually"
    )

    certification_expiry_date = fields.Date(
        string='Certification Expiry',
        help="Date when professional certification expires"
    )

    # ===== EMERGENCY CONTACT =====
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name',
        help="Name of emergency contact person"
    )

    emergency_contact_relationship = fields.Char(
        string='Emergency Contact Relationship',
        help="Relationship to emergency contact"
    )

    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone',
        help="Phone number of emergency contact"
    )

    emergency_contact_email = fields.Char(
        string='Emergency Contact Email',
        help="Email address of emergency contact"
    )

    # ===== MEMBER ENGAGEMENT METRICS =====
    engagement_score = fields.Float(
        string='Engagement Score',
        compute='_compute_engagement_score',
        store=True,
        help="Computed engagement score based on activities"
    )

    last_activity_date = fields.Datetime(
        string='Last Activity',
        help="Date of last member activity"
    )

    total_events_attended = fields.Integer(
        string='Events Attended',
        default=0,
        help="Total number of events attended"
    )

    # ===== NOTES & COMMENTS =====
    internal_notes = fields.Text(
        string='Internal Notes',
        help="Internal staff notes about the member"
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
            timezones = [(tz, tz) for tz in pytz.common_timezones]
            return timezones
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

    @api.depends('partner_id.member_category_ids', 'total_events_attended', 'continuing_education_hours')
    def _compute_engagement_score(self):
        """Compute member engagement score based on various activities"""
        for profile in self:
            score = 0.0
            
            # Base score for being an active member
            if profile.partner_id.is_member and profile.partner_id.member_status == 'active':
                score += 10.0
            
            # Points for events attended
            score += min(profile.total_events_attended * 2.0, 20.0)
            
            # Points for continuing education
            score += min(profile.continuing_education_hours * 0.5, 15.0)
            
            # Points for volunteer status
            if profile.volunteer_status == 'current_volunteer':
                score += 15.0
            elif profile.volunteer_status == 'available':
                score += 5.0
            
            # Points for profile completeness
            score += profile.profile_completeness * 0.3
            
            # Cap at 100
            profile.engagement_score = min(score, 100.0)

    @api.depends('graduation_year', 'graduation_institution', 'ethnicity', 'language_ids',
                 'linkedin_url', 'emergency_contact_name', 'volunteer_status')
    def _compute_profile_completeness(self):
        """Calculate profile completeness percentage"""
        for profile in self:
            total_fields = 20  # Total number of optional profile fields
            completed_fields = 0
            
            # Count completed fields
            fields_to_check = [
                'graduation_year', 'graduation_institution', 'ethnicity',
                'primary_language', 'time_zone', 'geographic_region',
                'linkedin_url', 'twitter_handle', 'orcid_id',
                'volunteer_status', 'emergency_contact_name',
                'emergency_contact_relationship', 'emergency_contact_phone',
            ]
            
            for field_name in fields_to_check:
                if getattr(profile, field_name):
                    completed_fields += 1
            
            # Check many2many fields
            if profile.language_ids:
                completed_fields += 1
            if profile.interests_tags:
                completed_fields += 1
            
            # Check boolean consent fields (count as complete if explicitly set)
            consent_fields = ['photo_permission', 'marketing_consent', 
                            'directory_listing_consent', 'data_sharing_consent']
            for field_name in consent_fields:
                # These are always set (default values), so count them as complete
                completed_fields += 1
            
            profile.profile_completeness = (completed_fields / total_fields) * 100.0

    @api.constrains('graduation_year')
    def _check_graduation_year(self):
        """Validate graduation year is reasonable"""
        current_year = fields.Date.today().year
        for profile in self:
            if profile.graduation_year:
                if profile.graduation_year > current_year + 10:
                    raise ValidationError(_("Graduation year cannot be more than 10 years in the future"))
                if profile.graduation_year < 1900:
                    raise ValidationError(_("Graduation year must be after 1900"))

    @api.constrains('continuing_education_hours', 'ce_hours_required')
    def _check_ce_hours(self):
        """Validate continuing education hours are positive"""
        for profile in self:
            if profile.continuing_education_hours < 0:
                raise ValidationError(_("Continuing education hours cannot be negative"))
            if profile.ce_hours_required < 0:
                raise ValidationError(_("Required CE hours cannot be negative"))

    @api.constrains('linkedin_url', 'researchgate_url')
    def _check_urls(self):
        """Basic URL validation"""
        for profile in self:
            if profile.linkedin_url and not profile.linkedin_url.startswith(('http://', 'https://')):
                raise ValidationError(_("LinkedIn URL must start with http:// or https://"))
            if profile.researchgate_url and not profile.researchgate_url.startswith(('http://', 'https://')):
                raise ValidationError(_("ResearchGate URL must start with http:// or https://"))

    def action_update_engagement_score(self):
        """Manual action to recalculate engagement score"""
        self._compute_engagement_score()
        return True

    def action_export_profile_data(self):
        """Export member profile data for GDPR compliance"""
        self.ensure_one()
        
        # This would typically generate a downloadable file
        # For now, we'll return the data in a readable format
        data = {
            'Partner Information': {
                'Name': self.partner_id.name,
                'Member ID': self.partner_id.member_id,
                'Email': self.partner_id.email,
                'Phone': self.partner_id.phone,
            },
            'Demographics': {
                'Ethnicity': dict(self._fields['ethnicity'].selection).get(self.ethnicity, ''),
                'Graduation Year': self.graduation_year,
                'Languages': ', '.join(self.language_ids.mapped('name')),
            },
            'Professional Networks': {
                'LinkedIn': self.linkedin_url,
                'Twitter': self.twitter_handle,
                'ORCID': self.orcid_id,
            },
            'Engagement': {
                'Engagement Score': self.engagement_score,
                'Events Attended': self.total_events_attended,
                'CE Hours': self.continuing_education_hours,
            }
        }
        
        # Log the data export request
        self.partner_id._log_audit_trail(
            self, 'export', 'Profile data exported', 
            {'exported_by': self.env.user.name}
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Profile Data Export',
            'view_mode': 'form',
            'res_model': 'ams.member.profile',
            'res_id': self.id,
            'target': 'new',
        }