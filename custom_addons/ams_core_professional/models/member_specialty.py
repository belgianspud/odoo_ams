# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MemberSpecialty(models.Model):
    """Member specialties and areas of expertise for professional associations."""
    
    _name = 'ams.member.specialty'
    _description = 'Member Specialty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _rec_name = 'name'
    
    # Basic Information
    name = fields.Char(
        string='Specialty Name',
        required=True,
        tracking=True,
        help='Name of the specialty or area of expertise'
    )
    
    code = fields.Char(
        string='Specialty Code',
        size=20,
        help='Short code or abbreviation for the specialty'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this specialty area'
    )
    
    # Classification
    specialty_type = fields.Selection([
        ('clinical', 'Clinical Specialty'),
        ('technical', 'Technical Specialty'),
        ('administrative', 'Administrative'),
        ('research', 'Research Area'),
        ('industry', 'Industry Focus'),
        ('practice_area', 'Practice Area'),
        ('subspecialty', 'Subspecialty'),
        ('other', 'Other')
    ], string='Specialty Type', required=True, default='clinical', tracking=True)
    
    # Hierarchy
    parent_specialty_id = fields.Many2one(
        'ams.member.specialty',
        string='Parent Specialty',
        help='Parent specialty for hierarchical organization'
    )
    
    child_specialty_ids = fields.One2many(
        'ams.member.specialty',
        'parent_specialty_id',
        string='Child Specialties',
        help='Sub-specialties under this specialty'
    )
    
    # Requirements and Qualifications
    requires_certification = fields.Boolean(
        string='Requires Certification',
        default=False,
        help='Whether this specialty requires specific certification'
    )
    
    certification_body = fields.Char(
        string='Certification Body',
        help='Organization that provides certification for this specialty'
    )
    
    requires_training = fields.Boolean(
        string='Requires Special Training',
        default=False,
        help='Whether this specialty requires specialized training'
    )
    
    training_requirements = fields.Text(
        string='Training Requirements',
        help='Description of required training or education'
    )
    
    # Professional Development
    has_continuing_education = fields.Boolean(
        string='Has CE Requirements',
        default=False,
        help='Whether this specialty has specific continuing education requirements'
    )
    
    ce_hours_annual = fields.Float(
        string='Annual CE Hours',
        help='Annual continuing education hours required for this specialty'
    )
    
    # Administrative
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display in lists'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Whether this specialty is currently available'
    )
    
    # Related Records
    member_specialty_ids = fields.One2many(
        'ams.member.specialty.line',
        'specialty_id',
        string='Member Specialties',
        help='Members who have this specialty'
    )
    
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
        help='Number of members with this specialty'
    )
    
    # Industry/Association Specific
    specialty_category = fields.Char(
        string='Specialty Category',
        help='Category grouping for association-specific organization'
    )
    
    board_certification_available = fields.Boolean(
        string='Board Certification Available',
        default=False,
        help='Whether board certification is available for this specialty'
    )
    
    # Notes
    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes about this specialty'
    )
    
    @api.depends('member_specialty_ids')
    def _compute_member_count(self):
        """Compute the number of members with this specialty."""
        for specialty in self:
            specialty.member_count = len(specialty.member_specialty_ids.filtered('active'))
    
    @api.constrains('parent_specialty_id')
    def _check_parent_recursion(self):
        """Prevent circular references in specialty hierarchy."""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive specialty hierarchies.'))
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure specialty codes are unique when provided."""
        for specialty in self:
            if specialty.code:
                existing = self.search([
                    ('code', '=', specialty.code),
                    ('id', '!=', specialty.id)
                ])
                if existing:
                    raise ValidationError(_('Specialty code "%s" already exists. Codes must be unique.') % specialty.code)
    
    def name_get(self):
        """Return name with hierarchy context."""
        result = []
        for specialty in self:
            name = specialty.name
            if specialty.parent_specialty_id:
                name = f'{specialty.parent_specialty_id.name} / {name}'
            if specialty.code:
                name = f'{name} ({specialty.code})'
            result.append((specialty.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enable search by name or code."""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)


class MemberSpecialtyLine(models.Model):
    """Junction model for member specialties with specific details."""
    
    _name = 'ams.member.specialty.line'
    _description = 'Member Specialty Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, is_primary desc, date_acquired desc'
    _rec_name = 'specialty_id'
    
    # Related Records
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Member who has this specialty'
    )
    
    specialty_id = fields.Many2one(
        'ams.member.specialty',
        string='Specialty',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Member specialty area'
    )
    
    # Specialty Details
    is_primary = fields.Boolean(
        string='Primary Specialty',
        default=False,
        tracking=True,
        help='Whether this is the member\'s primary specialty'
    )
    
    proficiency_level = fields.Selection([
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert')
    ], string='Proficiency Level', default='intermediate', tracking=True)
    
    date_acquired = fields.Date(
        string='Date Acquired',
        tracking=True,
        help='Date when this specialty was acquired'
    )
    
    years_experience = fields.Integer(
        string='Years of Experience',
        help='Years of experience in this specialty'
    )
    
    # Certification Information
    is_certified = fields.Boolean(
        string='Certified',
        default=False,
        tracking=True,
        help='Whether member is certified in this specialty'
    )
    
    certification_number = fields.Char(
        string='Certification Number',
        help='Certification number if applicable'
    )
    
    certification_date = fields.Date(
        string='Certification Date',
        help='Date of certification'
    )
    
    certification_expiration = fields.Date(
        string='Certification Expiration',
        help='Date when certification expires'
    )
    
    certifying_body = fields.Char(
        string='Certifying Body',
        help='Organization that issued the certification'
    )
    
    # Board Certification
    is_board_certified = fields.Boolean(
        string='Board Certified',
        default=False,
        tracking=True,
        help='Whether member is board certified in this specialty'
    )
    
    board_certification_date = fields.Date(
        string='Board Certification Date',
        help='Date of board certification'
    )
    
    board_certification_number = fields.Char(
        string='Board Certification Number',
        help='Board certification number'
    )
    
    board_name = fields.Char(
        string='Board Name',
        help='Name of the certifying board'
    )
    
    # Practice Information
    practice_percentage = fields.Float(
        string='Practice Percentage',
        help='Percentage of practice devoted to this specialty'
    )
    
    practice_setting = fields.Selection([
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('private_practice', 'Private Practice'),
        ('academic', 'Academic Institution'),
        ('research', 'Research Institution'),
        ('government', 'Government'),
        ('corporate', 'Corporate'),
        ('consulting', 'Consulting'),
        ('other', 'Other')
    ], string='Practice Setting', help='Primary practice setting for this specialty')
    
    # Status and Administrative
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('retired', 'Retired'),
        ('on_hold', 'On Hold')
    ], string='Status', default='active', required=True, tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Whether this specialty record is active'
    )
    
    # Computed Fields
    is_certification_expired = fields.Boolean(
        string='Certification Expired',
        compute='_compute_certification_expired',
        store=True,
        help='Whether certification has expired'
    )
    
    certification_days_until_expiration = fields.Integer(
        string='Days Until Cert. Expiration',
        compute='_compute_certification_days_until_expiration',
        help='Days until certification expires'
    )
    
    # Notes
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this specialty'
    )
    
    @api.depends('certification_expiration')
    def _compute_certification_expired(self):
        """Compute if certification is expired."""
        today = fields.Date.context_today(self)
        for specialty_line in self:
            if specialty_line.certification_expiration:
                specialty_line.is_certification_expired = specialty_line.certification_expiration < today
            else:
                specialty_line.is_certification_expired = False
    
    @api.depends('certification_expiration')
    def _compute_certification_days_until_expiration(self):
        """Compute days until certification expiration."""
        today = fields.Date.context_today(self)
        for specialty_line in self:
            if specialty_line.certification_expiration:
                delta = specialty_line.certification_expiration - today
                specialty_line.certification_days_until_expiration = delta.days
            else:
                specialty_line.certification_days_until_expiration = 0
    
    @api.constrains('is_primary', 'partner_id')
    def _check_single_primary_specialty(self):
        """Ensure only one primary specialty per member."""
        for specialty_line in self:
            if specialty_line.is_primary:
                existing_primary = self.search([
                    ('partner_id', '=', specialty_line.partner_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', specialty_line.id),
                    ('active', '=', True)
                ])
                if existing_primary:
                    raise ValidationError(_('Member can only have one primary specialty.'))
    
    @api.constrains('practice_percentage')
    def _check_practice_percentage(self):
        """Validate practice percentage is between 0 and 100."""
        for specialty_line in self:
            if specialty_line.practice_percentage and (specialty_line.practice_percentage < 0 or specialty_line.practice_percentage > 100):
                raise ValidationError(_('Practice percentage must be between 0 and 100.'))
    
    @api.constrains('date_acquired', 'certification_date', 'certification_expiration')
    def _check_dates(self):
        """Validate date logic."""
        for specialty_line in self:
            if (specialty_line.date_acquired and specialty_line.certification_date 
                and specialty_line.date_acquired > specialty_line.certification_date):
                raise ValidationError(_('Specialty acquisition date cannot be after certification date.'))
            
            if (specialty_line.certification_date and specialty_line.certification_expiration 
                and specialty_line.certification_date > specialty_line.certification_expiration):
                raise ValidationError(_('Certification date cannot be after expiration date.'))
    
    @api.model
    def _cron_update_expired_certifications(self):
        """Cron job to identify and flag expired certifications."""
        today = fields.Date.context_today(self)
        expired_certifications = self.search([
            ('certification_expiration', '<', today),
            ('is_certified', '=', True),
            ('active', '=', True)
        ])
        
        # Log expired certifications for follow-up
        for cert in expired_certifications:
            cert.message_post(
                body=_('Certification expired on %s') % cert.certification_expiration,
                message_type='notification'
            )
        
        _logger.info(f'Found {len(expired_certifications)} expired specialty certifications')
    
    def action_renew_certification(self):
        """Action to renew an expired certification."""
        self.ensure_one()
        # This could be extended to integrate with external certification systems
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Certification'),
            'res_model': 'ams.member.specialty.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }