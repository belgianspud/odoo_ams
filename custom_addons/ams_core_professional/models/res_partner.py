# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extend res.partner with professional designation and specialty fields."""
    
    _inherit = 'res.partner'
    
    # Professional Designations
    professional_designation_ids = fields.One2many(
        'ams.member.designation',
        'partner_id',
        string='Professional Designations',
        help='Professional designations, licenses, and certifications held by this member'
    )
    
    designation_count = fields.Integer(
        string='Designation Count',
        compute='_compute_designation_count',
        help='Number of professional designations held'
    )
    
    active_designation_ids = fields.One2many(
        'ams.member.designation',
        'partner_id',
        string='Active Designations',
        domain=[('active', '=', True), ('status', '=', 'active')],
        help='Currently active professional designations'
    )
    
    # Member Specialties
    specialty_ids = fields.One2many(
        'ams.member.specialty.line',
        'partner_id',
        string='Member Specialties',
        help='Areas of specialization and expertise'
    )
    
    specialty_count = fields.Integer(
        string='Specialty Count',
        compute='_compute_specialty_count',
        help='Number of specialties'
    )
    
    primary_specialty_id = fields.Many2one(
        'ams.member.specialty',
        string='Primary Specialty',
        compute='_compute_primary_specialty',
        store=True,
        help='Primary area of specialization'
    )
    
    active_specialty_ids = fields.One2many(
        'ams.member.specialty.line',
        'partner_id',
        string='Active Specialties',
        domain=[('active', '=', True), ('status', '=', 'active')],
        help='Currently active specialties'
    )
    
    # License and Certification Information
    license_certification_number = fields.Char(
        string='Primary License Number',
        help='Primary professional license or certification number'
    )
    
    license_issuing_state = fields.Many2one(
        'res.country.state',
        string='License Issuing State',
        help='State or province that issued the primary license'
    )
    
    license_issuing_country = fields.Many2one(
        'res.country',
        string='License Issuing Country',
        help='Country that issued the primary license'
    )
    
    license_expiration_date = fields.Date(
        string='License Expiration Date',
        help='Expiration date of primary license'
    )
    
    license_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive')
    ], string='License Status', default='active',
       help='Current status of primary professional license')
    
    # Professional Development
    continuing_education_hours = fields.Float(
        string='CE Hours (Current Period)',
        help='Continuing education hours completed in current reporting period'
    )
    
    ce_reporting_period_start = fields.Date(
        string='CE Reporting Period Start',
        help='Start date of current CE reporting period'
    )
    
    ce_reporting_period_end = fields.Date(
        string='CE Reporting Period End',
        help='End date of current CE reporting period'
    )
    
    ce_hours_required = fields.Float(
        string='CE Hours Required',
        compute='_compute_ce_hours_required',
        help='Total CE hours required based on designations and specialties'
    )
    
    # Professional Networking and Online Presence
    orcid_id = fields.Char(
        string='ORCID ID',
        help='Open Researcher and Contributor ID (https://orcid.org/)'
    )
    
    researchgate_profile = fields.Char(
        string='ResearchGate Profile',
        help='ResearchGate profile URL'
    )
    
    google_scholar_profile = fields.Char(
        string='Google Scholar Profile',
        help='Google Scholar profile URL'
    )
    
    professional_website = fields.Char(
        string='Professional Website',
        help='Personal or practice website URL'
    )
    
    # Practice Information
    practice_name = fields.Char(
        string='Practice/Organization Name',
        help='Name of practice, clinic, or organization'
    )
    
    practice_type = fields.Selection([
        ('solo', 'Solo Practice'),
        ('group', 'Group Practice'),
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('academic', 'Academic Institution'),
        ('government', 'Government Agency'),
        ('corporate', 'Corporate'),
        ('consulting', 'Consulting'),
        ('research', 'Research Institution'),
        ('non_profit', 'Non-Profit Organization'),
        ('other', 'Other')
    ], string='Practice Type', help='Type of practice or work setting')
    
    years_in_practice = fields.Integer(
        string='Years in Practice',
        help='Total years of professional practice'
    )
    
    board_certifications = fields.Text(
        string='Board Certifications',
        help='List of board certifications held'
    )
    
    # Computed Professional Summary Fields
    professional_credentials = fields.Char(
        string='Professional Credentials',
        compute='_compute_professional_credentials',
        store=True,
        help='Summary of professional credentials and designations'
    )
    
    specialty_summary = fields.Char(
        string='Specialty Summary',
        compute='_compute_specialty_summary',
        store=True,
        help='Summary of professional specialties'
    )
    
    # Professional Status Indicators
    has_expired_designations = fields.Boolean(
        string='Has Expired Designations',
        compute='_compute_professional_status',
        help='Whether member has any expired professional designations'
    )
    
    has_expiring_soon_designations = fields.Boolean(
        string='Has Soon-to-Expire Designations',
        compute='_compute_professional_status',
        help='Whether member has designations expiring within 90 days'
    )
    
    professional_compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('warning', 'Warning - Expiring Soon'),
        ('non_compliant', 'Non-Compliant'),
        ('unknown', 'Status Unknown')
    ], string='Professional Compliance Status',
       compute='_compute_professional_compliance_status',
       store=True,
       help='Overall professional compliance status')
    
    @api.depends('professional_designation_ids')
    def _compute_designation_count(self):
        """Compute the number of professional designations."""
        for partner in self:
            partner.designation_count = len(partner.professional_designation_ids.filtered('active'))
    
    @api.depends('specialty_ids')
    def _compute_specialty_count(self):
        """Compute the number of specialties."""
        for partner in self:
            partner.specialty_count = len(partner.specialty_ids.filtered('active'))
    
    @api.depends('specialty_ids.is_primary', 'specialty_ids.specialty_id')
    def _compute_primary_specialty(self):
        """Compute the primary specialty."""
        for partner in self:
            primary_specialty_line = partner.specialty_ids.filtered(lambda s: s.is_primary and s.active)
            if primary_specialty_line:
                partner.primary_specialty_id = primary_specialty_line[0].specialty_id
            else:
                partner.primary_specialty_id = False
    
    @api.depends('professional_designation_ids.designation_id', 'specialty_ids.specialty_id')
    def _compute_ce_hours_required(self):
        """Compute total CE hours required based on designations and specialties."""
        for partner in self:
            total_hours = 0.0
            
            # Add CE hours from active designations
            for designation_line in partner.professional_designation_ids.filtered('active'):
                if designation_line.designation_id.requires_continuing_education:
                    total_hours += designation_line.designation_id.ce_hours_required or 0.0
            
            # Add CE hours from active specialties
            for specialty_line in partner.specialty_ids.filtered('active'):
                if specialty_line.specialty_id.has_continuing_education:
                    total_hours += specialty_line.specialty_id.ce_hours_annual or 0.0
            
            partner.ce_hours_required = total_hours
    
    @api.depends('active_designation_ids.designation_id.code')
    def _compute_professional_credentials(self):
        """Compute a summary string of professional credentials."""
        for partner in self:
            credentials = []
            for designation_line in partner.active_designation_ids:
                if designation_line.designation_id.code:
                    credentials.append(designation_line.designation_id.code)
            
            partner.professional_credentials = ', '.join(credentials) if credentials else ''
    
    @api.depends('active_specialty_ids.specialty_id.name')
    def _compute_specialty_summary(self):
        """Compute a summary string of specialties."""
        for partner in self:
            specialties = []
            
            # Primary specialty first
            primary = partner.specialty_ids.filtered(lambda s: s.is_primary and s.active)
            if primary:
                specialties.append(primary[0].specialty_id.name)
            
            # Other specialties
            other_specialties = partner.active_specialty_ids.filtered(lambda s: not s.is_primary)
            for specialty_line in other_specialties[:3]:  # Limit to avoid overly long summaries
                if specialty_line.specialty_id.name not in specialties:
                    specialties.append(specialty_line.specialty_id.name)
            
            if len(other_specialties) > 3:
                specialties.append('...')
            
            partner.specialty_summary = ', '.join(specialties) if specialties else ''
    
    @api.depends('professional_designation_ids.expiration_date', 'professional_designation_ids.status')
    def _compute_professional_status(self):
        """Compute professional status indicators."""
        today = fields.Date.context_today(self)
        warning_date = fields.Date.add(today, days=90)
        
        for partner in self:
            active_designations = partner.professional_designation_ids.filtered('active')
            
            # Check for expired designations
            expired = active_designations.filtered(lambda d: d.expiration_date and d.expiration_date < today)
            partner.has_expired_designations = bool(expired)
            
            # Check for soon-to-expire designations
            expiring_soon = active_designations.filtered(
                lambda d: d.expiration_date and today <= d.expiration_date <= warning_date
            )
            partner.has_expiring_soon_designations = bool(expiring_soon)
    
    @api.depends('has_expired_designations', 'has_expiring_soon_designations', 'license_status')
    def _compute_professional_compliance_status(self):
        """Compute overall professional compliance status."""
        for partner in self:
            if partner.has_expired_designations or partner.license_status in ['expired', 'suspended', 'revoked']:
                partner.professional_compliance_status = 'non_compliant'
            elif partner.has_expiring_soon_designations or partner.license_status == 'pending':
                partner.professional_compliance_status = 'warning'
            elif partner.professional_designation_ids.filtered('active') or partner.license_status == 'active':
                partner.professional_compliance_status = 'compliant'
            else:
                partner.professional_compliance_status = 'unknown'
    
    @api.constrains('orcid_id')
    def _check_orcid_format(self):
        """Validate ORCID ID format."""
        orcid_pattern = re.compile(r'^(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$')
        for partner in self:
            if partner.orcid_id:
                # Clean up the ORCID ID (remove https://orcid.org/ if present)
                clean_orcid = partner.orcid_id.replace('https://orcid.org/', '').replace('http://orcid.org/', '')
                if not orcid_pattern.match(clean_orcid):
                    raise ValidationError(_('ORCID ID must be in format: 0000-0000-0000-0000'))
                partner.orcid_id = clean_orcid
    
    @api.constrains('ce_reporting_period_start', 'ce_reporting_period_end')
    def _check_ce_period_dates(self):
        """Validate CE reporting period dates."""
        for partner in self:
            if (partner.ce_reporting_period_start and partner.ce_reporting_period_end 
                and partner.ce_reporting_period_start >= partner.ce_reporting_period_end):
                raise ValidationError(_('CE reporting period start date must be before end date.'))
    
    def action_view_professional_designations(self):
        """Action to view member's professional designations."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Professional Designations'),
            'res_model': 'ams.member.designation',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }
    
    def action_view_specialties(self):
        """Action to view member's specialties."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Specialties'),
            'res_model': 'ams.member.specialty.line',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }
    
    def action_add_professional_designation(self):
        """Action to add a new professional designation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Professional Designation'),
            'res_model': 'ams.member.designation',
            'view_mode': 'form',
            'context': {'default_partner_id': self.id},
            'target': 'new',
        }
    
    def action_add_specialty(self):
        """Action to add a new specialty."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Specialty'),
            'res_model': 'ams.member.specialty.line',
            'view_mode': 'form',
            'context': {'default_partner_id': self.id},
            'target': 'new',
        }
    
    def get_professional_summary(self):
        """Get a formatted professional summary for this member."""
        self.ensure_one()
        summary_parts = []
        
        # Add name
        summary_parts.append(self.name)
        
        # Add credentials
        if self.professional_credentials:
            summary_parts.append(self.professional_credentials)
        
        # Add primary specialty
        if self.primary_specialty_id:
            summary_parts.append(self.primary_specialty_id.name)
        
        # Add practice information
        if self.practice_name:
            summary_parts.append(self.practice_name)
        
        return ' | '.join(summary_parts)
    
    def check_professional_compliance(self):
        """Check and return professional compliance details."""
        self.ensure_one()
        issues = []
        warnings = []
        
        today = fields.Date.context_today(self)
        warning_date = fields.Date.add(today, days=90)
        
        # Check designations
        for designation in self.professional_designation_ids.filtered('active'):
            if designation.expiration_date:
                if designation.expiration_date < today:
                    issues.append(f"Expired designation: {designation.designation_id.name}")
                elif designation.expiration_date <= warning_date:
                    warnings.append(f"Expiring soon: {designation.designation_id.name} ({designation.expiration_date})")
        
        # Check license status
        if self.license_status in ['expired', 'suspended', 'revoked']:
            issues.append(f"License status: {self.license_status}")
        elif self.license_status == 'pending':
            warnings.append("License status is pending")
        
        # Check CE hours if in reporting period
        if (self.ce_reporting_period_end and self.ce_reporting_period_end >= today 
            and self.ce_hours_required > 0):
            if self.continuing_education_hours < self.ce_hours_required:
                shortfall = self.ce_hours_required - self.continuing_education_hours
                warnings.append(f"CE hours shortfall: {shortfall} hours needed")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'status': self.professional_compliance_status
        }