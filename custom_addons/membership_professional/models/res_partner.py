# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ResPartner(models.Model):
    """
    Professional Extensions for Members
    """
    _inherit = 'res.partner'

    # ==========================================
    # PROFESSIONAL CREDENTIALS
    # ==========================================
    
    professional_credentials = fields.Many2many(
        'membership.credential',
        'partner_credential_rel',
        'partner_id',
        'credential_id',
        string='Professional Credentials',
        help='All professional credentials held by this member'
    )
    
    primary_credential_id = fields.Many2one(
        'membership.credential',
        string='Primary Credential',
        help='Main professional credential for display'
    )
    
    credential_display = fields.Char(
        string='Credentials',
        compute='_compute_credential_display',
        help='Display string of all credentials'
    )
    
    credential_history_ids = fields.One2many(
        'membership.credential.history',
        'partner_id',
        string='Credential History'
    )
    
    credential_count = fields.Integer(
        string='Credential Count',
        compute='_compute_credential_count'
    )

    @api.depends('professional_credentials')
    def _compute_credential_count(self):
        """Count credentials"""
        for partner in self:
            partner.credential_count = len(partner.professional_credentials)

    @api.depends('professional_credentials', 'professional_credentials.code')
    def _compute_credential_display(self):
        """Create display string of credentials"""
        for partner in self:
            if partner.professional_credentials:
                codes = partner.professional_credentials.mapped('code')
                partner.credential_display = ', '.join(codes)
            else:
                partner.credential_display = ''

    # ==========================================
    # PROFESSIONAL SPECIALTIES
    # ==========================================
    
    specialty_ids = fields.Many2many(
        'membership.specialty',
        'partner_specialty_rel',
        'partner_id',
        'specialty_id',
        string='Areas of Specialty',
        help='Professional specialties and focus areas'
    )
    
    primary_specialty_id = fields.Many2one(
        'membership.specialty',
        string='Primary Specialty',
        help='Main area of professional focus'
    )
    
    specialty_count = fields.Integer(
        string='Specialty Count',
        compute='_compute_specialty_count'
    )

    @api.depends('specialty_ids')
    def _compute_specialty_count(self):
        """Count specialties"""
        for partner in self:
            partner.specialty_count = len(partner.specialty_ids)

    # ==========================================
    # EMPLOYMENT INFORMATION
    # ==========================================
    
    employer_name = fields.Char(
        string='Current Employer',
        help='Name of current employer/organization'
    )
    
    job_title = fields.Char(
        string='Job Title',
        help='Current professional title/position'
    )
    
    department = fields.Char(
        string='Department',
        help='Department or division within organization'
    )
    
    industry_sector = fields.Selection([
        ('public', 'Public Sector'),
        ('private', 'Private Sector'),
        ('academic', 'Academic/Education'),
        ('nonprofit', 'Non-Profit'),
        ('government', 'Government'),
        ('military', 'Military'),
        ('self_employed', 'Self-Employed'),
        ('retired', 'Retired'),
        ('student', 'Student'),
        ('other', 'Other'),
    ], string='Industry Sector',
       help='Employment sector classification')
    
    employment_status = fields.Selection([
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract/Consultant'),
        ('self_employed', 'Self-Employed'),
        ('retired', 'Retired'),
        ('unemployed', 'Unemployed'),
        ('student', 'Student'),
    ], string='Employment Status',
       help='Current employment status')
    
    employment_start_date = fields.Date(
        string='Employment Start Date',
        help='Date started with current employer'
    )
    
    years_with_employer = fields.Float(
        string='Years with Current Employer',
        compute='_compute_years_with_employer',
        help='Years with current employer'
    )

    @api.depends('employment_start_date')
    def _compute_years_with_employer(self):
        """Calculate years with current employer"""
        today = date.today()
        for partner in self:
            if partner.employment_start_date:
                delta = today - partner.employment_start_date
                partner.years_with_employer = delta.days / 365.25
            else:
                partner.years_with_employer = 0.0

    # ==========================================
    # EXPERIENCE
    # ==========================================
    
    career_start_date = fields.Date(
        string='Career Start Date',
        help='Date when professional career began'
    )
    
    years_of_experience = fields.Float(
        string='Years of Experience',
        compute='_compute_years_of_experience',
        help='Total years of professional experience'
    )
    
    experience_level = fields.Selection([
        ('entry', 'Entry Level (0-2 years)'),
        ('junior', 'Junior (2-5 years)'),
        ('mid', 'Mid-Level (5-10 years)'),
        ('senior', 'Senior (10-20 years)'),
        ('expert', 'Expert (20+ years)'),
    ], string='Experience Level',
       compute='_compute_experience_level',
       store=True,
       help='Professional experience level')

    @api.depends('career_start_date')
    def _compute_years_of_experience(self):
        """Calculate total years of experience"""
        today = date.today()
        for partner in self:
            if partner.career_start_date:
                delta = today - partner.career_start_date
                partner.years_of_experience = delta.days / 365.25
            else:
                partner.years_of_experience = 0.0

    @api.depends('years_of_experience')
    def _compute_experience_level(self):
        """Determine experience level"""
        for partner in self:
            years = partner.years_of_experience
            if years < 2:
                partner.experience_level = 'entry'
            elif years < 5:
                partner.experience_level = 'junior'
            elif years < 10:
                partner.experience_level = 'mid'
            elif years < 20:
                partner.experience_level = 'senior'
            else:
                partner.experience_level = 'expert'

    # ==========================================
    # LICENSE TRACKING
    # ==========================================
    
    license_ids = fields.One2many(
        'membership.license',
        'partner_id',
        string='Professional Licenses'
    )
    
    active_license_ids = fields.One2many(
        'membership.license',
        'partner_id',
        string='Active Licenses',
        domain=[('status', '=', 'active')]
    )
    
    license_count = fields.Integer(
        string='License Count',
        compute='_compute_license_count'
    )
    
    active_license_count = fields.Integer(
        string='Active Licenses',
        compute='_compute_license_count'
    )
    
    has_expired_license = fields.Boolean(
        string='Has Expired License',
        compute='_compute_license_status',
        help='Member has at least one expired license'
    )
    
    has_expiring_license = fields.Boolean(
        string='Has Expiring License',
        compute='_compute_license_status',
        help='Member has license expiring soon'
    )
    
    license_status = fields.Selection([
        ('good', 'All Licenses Current'),
        ('expiring', 'License Expiring Soon'),
        ('expired', 'Expired License'),
        ('no_license', 'No License on File'),
    ], string='License Status',
       compute='_compute_license_status',
       help='Overall license status')

    @api.depends('license_ids')
    def _compute_license_count(self):
        """Count licenses"""
        for partner in self:
            partner.license_count = len(partner.license_ids)
            partner.active_license_count = len(partner.active_license_ids)

    @api.depends('license_ids', 'license_ids.status')
    def _compute_license_status(self):
        """Determine overall license status"""
        for partner in self:
            if not partner.license_ids:
                partner.license_status = 'no_license'
                partner.has_expired_license = False
                partner.has_expiring_license = False
                continue
            
            # Check for expired licenses
            expired = partner.license_ids.filtered(lambda l: l.status == 'expired')
            partner.has_expired_license = bool(expired)
            
            # Check for expiring licenses
            expiring = partner.license_ids.filtered(lambda l: l.status == 'expiring_soon')
            partner.has_expiring_license = bool(expiring)
            
            # Set overall status
            if expired:
                partner.license_status = 'expired'
            elif expiring:
                partner.license_status = 'expiring'
            else:
                partner.license_status = 'good'

    # ==========================================
    # EDUCATION (Basic)
    # ==========================================
    
    highest_education = fields.Selection([
        ('high_school', 'High School'),
        ('associates', 'Associate Degree'),
        ('bachelors', 'Bachelor\'s Degree'),
        ('masters', 'Master\'s Degree'),
        ('doctorate', 'Doctorate'),
        ('other', 'Other'),
    ], string='Highest Education',
       help='Highest level of education attained')
    
    graduation_year = fields.Integer(
        string='Graduation Year',
        help='Year of highest degree graduation'
    )
    
    alma_mater = fields.Char(
        string='Alma Mater',
        help='Primary educational institution'
    )

    # ==========================================
    # PROFESSIONAL DEVELOPMENT
    # ==========================================
    
    ce_hours_current_cycle = fields.Float(
        string='CE Hours (Current Cycle)',
        compute='_compute_ce_hours',
        help='Continuing education hours in current cycle'
    )
    
    ce_compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('not_required', 'Not Required'),
    ], string='CE Compliance',
       compute='_compute_ce_compliance',
       help='Continuing education compliance status')

    @api.depends('license_ids', 'license_ids.ce_hours_completed')
    def _compute_ce_hours(self):
        """Sum CE hours from all licenses"""
        for partner in self:
            partner.ce_hours_current_cycle = sum(
                partner.license_ids.mapped('ce_hours_completed')
            )

    @api.depends('license_ids', 'license_ids.ce_compliance')
    def _compute_ce_compliance(self):
        """Check CE compliance across all licenses"""
        for partner in self:
            ce_required_licenses = partner.license_ids.filtered(lambda l: l.ce_required)
            
            if not ce_required_licenses:
                partner.ce_compliance_status = 'not_required'
            elif all(ce_required_licenses.mapped('ce_compliance')):
                partner.ce_compliance_status = 'compliant'
            else:
                partner.ce_compliance_status = 'non_compliant'

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_view_licenses(self):
        """View all licenses"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Professional Licenses - %s') % self.name,
            'res_model': 'membership.license',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_credentials(self):
        """View credential history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credential History - %s') % self.name,
            'res_model': 'membership.credential.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def check_credential_eligibility(self, credential):
        """Check if member is eligible for a membership based on credentials"""
        self.ensure_one()
        
        if not credential.is_required_for_membership:
            return True
        
        return credential in self.professional_credentials

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('primary_credential_id')
    def _onchange_primary_credential(self):
        """Ensure primary credential is in the list"""
        if self.primary_credential_id:
            if self.primary_credential_id not in self.professional_credentials:
                self.professional_credentials = [(4, self.primary_credential_id.id)]

    @api.onchange('primary_specialty_id')
    def _onchange_primary_specialty(self):
        """Ensure primary specialty is in the list"""
        if self.primary_specialty_id:
            if self.primary_specialty_id not in self.specialty_ids:
                self.specialty_ids = [(4, self.primary_specialty_id.id)]

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('graduation_year')
    def _check_graduation_year(self):
        """Validate graduation year"""
        current_year = date.today().year
        for partner in self:
            if partner.graduation_year:
                if partner.graduation_year < 1900 or partner.graduation_year > current_year + 10:
                    raise ValidationError(_(
                        'Graduation year must be between 1900 and %s'
                    ) % (current_year + 10))