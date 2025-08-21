# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class MemberProfile(models.Model):
    """Extend ams.member.profile with professional networking and career fields."""
    
    _inherit = 'ams.member.profile'
    
    # Professional Social Media and Networking
    linkedin_url = fields.Char(
        string='LinkedIn Profile',
        help='LinkedIn profile URL'
    )
    
    twitter_handle = fields.Char(
        string='Twitter Handle',
        help='Twitter username (without @)'
    )
    
    facebook_url = fields.Char(
        string='Facebook Profile',
        help='Facebook profile or page URL'
    )
    
    instagram_handle = fields.Char(
        string='Instagram Handle',
        help='Instagram username (without @)'
    )
    
    youtube_channel = fields.Char(
        string='YouTube Channel',
        help='YouTube channel URL'
    )
    
    # Professional Networking Platforms
    researchgate_url = fields.Char(
        string='ResearchGate Profile',
        help='ResearchGate profile URL'
    )
    
    academia_edu_url = fields.Char(
        string='Academia.edu Profile',
        help='Academia.edu profile URL'
    )
    
    pubmed_author_id = fields.Char(
        string='PubMed Author ID',
        help='PubMed Author ID for publications'
    )
    
    scopus_author_id = fields.Char(
        string='Scopus Author ID',
        help='Scopus Author ID for publications'
    )
    
    # Industry-Specific Professional Networks
    doximity_profile = fields.Char(
        string='Doximity Profile',
        help='Doximity professional medical network profile'
    )
    
    medscape_profile = fields.Char(
        string='Medscape Profile',
        help='Medscape professional profile'
    )
    
    # Legal Professional Networks (for legal associations)
    avvo_profile = fields.Char(
        string='Avvo Profile',
        help='Avvo lawyer directory profile'
    )
    
    martindale_hubbell_id = fields.Char(
        string='Martindale-Hubbell ID',
        help='Martindale-Hubbell lawyer directory ID'
    )
    
    # Engineering/Technical Networks
    ieee_profile = fields.Char(
        string='IEEE Profile',
        help='IEEE professional profile'
    )
    
    github_profile = fields.Char(
        string='GitHub Profile',
        help='GitHub profile for technical professionals'
    )
    
    stackoverflow_profile = fields.Char(
        string='Stack Overflow Profile',
        help='Stack Overflow profile URL'
    )
    
    # Career and Education Information
    alma_mater = fields.Char(
        string='Alma Mater',
        help='Primary educational institution attended'
    )
    
    graduation_year = fields.Integer(
        string='Graduation Year',
        help='Year of graduation from primary degree program'
    )
    
    residency_program = fields.Char(
        string='Residency Program',
        help='Medical residency program completed'
    )
    
    fellowship_program = fields.Char(
        string='Fellowship Program',
        help='Fellowship program completed'
    )
    
    bar_admission_year = fields.Integer(
        string='Bar Admission Year',
        help='Year admitted to the bar (for legal professionals)'
    )
    
    bar_admission_state = fields.Many2one(
        'res.country.state',
        string='Bar Admission State',
        help='State where admitted to practice law'
    )
    
    # Publications and Research
    research_interests = fields.Text(
        string='Research Interests',
        help='Areas of research interest and focus'
    )
    
    publications_count = fields.Integer(
        string='Publications Count',
        help='Number of professional publications'
    )
    
    h_index = fields.Integer(
        string='H-Index',
        help='H-index for research impact measurement'
    )
    
    peer_review_journals = fields.Text(
        string='Peer Review Journals',
        help='Journals where member serves as peer reviewer'
    )
    
    # Professional Achievements and Recognition
    awards_honors = fields.Text(
        string='Awards and Honors',
        help='Professional awards and recognition received'
    )
    
    speaking_topics = fields.Text(
        string='Speaking Topics',
        help='Professional speaking topics and areas of expertise'
    )
    
    media_appearances = fields.Text(
        string='Media Appearances',
        help='TV, radio, podcast, or other media appearances'
    )
    
    # Professional Services and Volunteer Work
    editorial_boards = fields.Text(
        string='Editorial Board Memberships',
        help='Journal or publication editorial boards'
    )
    
    professional_committees = fields.Text(
        string='Professional Committee Service',
        help='Professional association committee memberships'
    )
    
    volunteer_activities = fields.Text(
        string='Professional Volunteer Activities',
        help='Professional volunteer work and community service'
    )
    
    # Teaching and Mentoring
    teaching_appointments = fields.Text(
        string='Teaching Appointments',
        help='Academic teaching positions and appointments'
    )
    
    mentoring_activities = fields.Text(
        string='Mentoring Activities',
        help='Professional mentoring and coaching activities'
    )
    
    guest_lectures = fields.Text(
        string='Guest Lectures',
        help='Guest lecture and presentation activities'
    )
    
    # Professional Goals and Development
    career_goals = fields.Text(
        string='Career Goals',
        help='Professional development and career objectives'
    )
    
    skill_development_areas = fields.Text(
        string='Skill Development Areas',
        help='Areas where member seeks professional development'
    )
    
    professional_interests = fields.Text(
        string='Professional Interests',
        help='Professional interests and emerging areas of focus'
    )
    
    # Networking and Availability
    available_for_mentoring = fields.Boolean(
        string='Available for Mentoring',
        default=False,
        help='Whether member is available to mentor other professionals'
    )
    
    seeking_mentorship = fields.Boolean(
        string='Seeking Mentorship',
        default=False,
        help='Whether member is seeking professional mentorship'
    )
    
    available_for_speaking = fields.Boolean(
        string='Available for Speaking',
        default=False,
        help='Whether member is available for speaking engagements'
    )
    
    available_for_consulting = fields.Boolean(
        string='Available for Consulting',
        default=False,
        help='Whether member is available for professional consulting'
    )
    
    # Professional Directory Settings
    directory_photo_permission = fields.Boolean(
        string='Directory Photo Permission',
        default=True,
        help='Permission to use photo in professional directory'
    )
    
    directory_contact_permission = fields.Boolean(
        string='Directory Contact Permission',
        default=True,
        help='Permission for other members to contact via directory'
    )
    
    directory_practice_info_permission = fields.Boolean(
        string='Directory Practice Info Permission',
        default=True,
        help='Permission to display practice information in directory'
    )
    
    # Professional Networking Preferences
    networking_interests = fields.Text(
        string='Networking Interests',
        help='Specific networking interests and goals'
    )
    
    collaboration_interests = fields.Text(
        string='Collaboration Interests',
        help='Areas where member seeks professional collaboration'
    )
    
    referral_interests = fields.Text(
        string='Referral Interests',
        help='Types of professional referrals member can provide or seeks'
    )
    
    # Computed Fields for Professional Summary
    professional_network_summary = fields.Char(
        string='Professional Network Summary',
        compute='_compute_professional_network_summary',
        store=True,
        help='Summary of professional networking platforms'
    )
    
    social_media_summary = fields.Char(
        string='Social Media Summary',
        compute='_compute_social_media_summary',
        store=True,
        help='Summary of social media presence'
    )
    
    @api.depends('linkedin_url', 'researchgate_url', 'doximity_profile', 'github_profile')
    def _compute_professional_network_summary(self):
        """Compute summary of professional networking platforms."""
        for profile in self:
            networks = []
            
            if profile.linkedin_url:
                networks.append('LinkedIn')
            if profile.researchgate_url:
                networks.append('ResearchGate')
            if profile.doximity_profile:
                networks.append('Doximity')
            if profile.github_profile:
                networks.append('GitHub')
            if profile.ieee_profile:
                networks.append('IEEE')
            
            profile.professional_network_summary = ', '.join(networks) if networks else ''
    
    @api.depends('twitter_handle', 'facebook_url', 'instagram_handle', 'youtube_channel')
    def _compute_social_media_summary(self):
        """Compute summary of social media presence."""
        for profile in self:
            platforms = []
            
            if profile.twitter_handle:
                platforms.append('Twitter')
            if profile.facebook_url:
                platforms.append('Facebook')
            if profile.instagram_handle:
                platforms.append('Instagram')
            if profile.youtube_channel:
                platforms.append('YouTube')
            
            profile.social_media_summary = ', '.join(platforms) if platforms else ''
    
    @api.constrains('linkedin_url')
    def _check_linkedin_url(self):
        """Validate LinkedIn URL format."""
        linkedin_pattern = re.compile(r'^https?://(www\.)?(linkedin\.com/in/|linkedin\.com/pub/)')
        for profile in self:
            if profile.linkedin_url and not linkedin_pattern.match(profile.linkedin_url):
                raise ValidationError(_('LinkedIn URL must be a valid LinkedIn profile URL'))
    
    @api.constrains('twitter_handle')
    def _check_twitter_handle(self):
        """Validate Twitter handle format."""
        twitter_pattern = re.compile(r'^[A-Za-z0-9_]{1,15}$')
        for profile in self:
            if profile.twitter_handle:
                # Remove @ if present
                handle = profile.twitter_handle.lstrip('@')
                if not twitter_pattern.match(handle):
                    raise ValidationError(_('Twitter handle must be 1-15 characters, letters, numbers, and underscores only'))
                profile.twitter_handle = handle
    
    @api.constrains('instagram_handle')
    def _check_instagram_handle(self):
        """Validate Instagram handle format."""
        instagram_pattern = re.compile(r'^[A-Za-z0-9_.]{1,30}$')
        for profile in self:
            if profile.instagram_handle:
                # Remove @ if present
                handle = profile.instagram_handle.lstrip('@')
                if not instagram_pattern.match(handle):
                    raise ValidationError(_('Instagram handle must be 1-30 characters, letters, numbers, periods, and underscores only'))
                profile.instagram_handle = handle
    
    @api.constrains('graduation_year', 'bar_admission_year')
    def _check_years(self):
        """Validate year fields are reasonable."""
        current_year = fields.Date.context_today(self).year
        for profile in self:
            if profile.graduation_year and (profile.graduation_year < 1900 or profile.graduation_year > current_year + 10):
                raise ValidationError(_('Graduation year must be between 1900 and %s') % (current_year + 10))
            
            if profile.bar_admission_year and (profile.bar_admission_year < 1900 or profile.bar_admission_year > current_year + 1):
                raise ValidationError(_('Bar admission year must be between 1900 and %s') % (current_year + 1))
    
    @api.constrains('h_index', 'publications_count')
    def _check_research_metrics(self):
        """Validate research metrics are non-negative."""
        for profile in self:
            if profile.h_index and profile.h_index < 0:
                raise ValidationError(_('H-index cannot be negative'))
            if profile.publications_count and profile.publications_count < 0:
                raise ValidationError(_('Publications count cannot be negative'))
    
    def get_professional_links(self):
        """Get a dictionary of all professional links for this member."""
        self.ensure_one()
        links = {}
        
        # Professional Networks
        if self.linkedin_url:
            links['LinkedIn'] = self.linkedin_url
        if self.researchgate_url:
            links['ResearchGate'] = self.researchgate_url
        if self.academia_edu_url:
            links['Academia.edu'] = self.academia_edu_url
        if self.doximity_profile:
            links['Doximity'] = self.doximity_profile
        if self.github_profile:
            links['GitHub'] = self.github_profile
        if self.ieee_profile:
            links['IEEE'] = self.ieee_profile
        
        # Social Media
        if self.twitter_handle:
            links['Twitter'] = f'https://twitter.com/{self.twitter_handle}'
        if self.facebook_url:
            links['Facebook'] = self.facebook_url
        if self.instagram_handle:
            links['Instagram'] = f'https://instagram.com/{self.instagram_handle}'
        if self.youtube_channel:
            links['YouTube'] = self.youtube_channel
        
        return links
    
    def get_research_profile(self):
        """Get research profile information."""
        self.ensure_one()
        return {
            'research_interests': self.research_interests,
            'publications_count': self.publications_count,
            'h_index': self.h_index,
            'pubmed_id': self.pubmed_author_id,
            'scopus_id': self.scopus_author_id,
            'peer_review_journals': self.peer_review_journals,
            'editorial_boards': self.editorial_boards
        }
    
    def get_networking_availability(self):
        """Get networking and availability information."""
        self.ensure_one()
        return {
            'available_for_mentoring': self.available_for_mentoring,
            'seeking_mentorship': self.seeking_mentorship,
            'available_for_speaking': self.available_for_speaking,
            'available_for_consulting': self.available_for_consulting,
            'networking_interests': self.networking_interests,
            'collaboration_interests': self.collaboration_interests,
            'referral_interests': self.referral_interests,
            'speaking_topics': self.speaking_topics
        }
    
    def action_update_professional_profile(self):
        """Action to open professional profile form for editing."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Professional Profile'),
            'res_model': 'ams.member.profile',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }