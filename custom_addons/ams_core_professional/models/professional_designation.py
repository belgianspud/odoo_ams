# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProfessionalDesignation(models.Model):
    """Professional designations, certifications, and credentials for association members."""
    
    _name = 'ams.professional.designation'
    _description = 'Professional Designation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _rec_name = 'name'
    
    # Basic Information
    name = fields.Char(
        string='Designation Name',
        required=True,
        tracking=True,
        help='Full name of the professional designation (e.g., "Certified Public Accountant")'
    )
    
    code = fields.Char(
        string='Designation Code',
        required=True,
        size=20,
        tracking=True,
        help='Short code or abbreviation (e.g., "CPA", "MD", "PE")'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of the designation and its requirements'
    )
    
    # Classification
    designation_type = fields.Selection([
        ('license', 'Professional License'),
        ('certification', 'Professional Certification'),
        ('degree', 'Academic Degree'),
        ('fellowship', 'Fellowship'),
        ('membership', 'Professional Membership'),
        ('other', 'Other Credential')
    ], string='Designation Type', required=True, default='certification', tracking=True)
    
    specialty_area = fields.Char(
        string='Specialty Area',
        help='Specific area or field of specialization'
    )
    
    # Issuing Organization
    issuing_body = fields.Char(
        string='Issuing Organization',
        required=True,
        tracking=True,
        help='Organization that grants this designation'
    )
    
    issuing_body_website = fields.Char(
        string='Issuing Body Website',
        help='Official website of the issuing organization'
    )
    
    # Validation and Requirements
    requires_exam = fields.Boolean(
        string='Requires Examination',
        default=False,
        help='Whether this designation requires passing an examination'
    )
    
    requires_experience = fields.Boolean(
        string='Requires Experience', 
        default=False,
        help='Whether this designation requires professional experience'
    )
    
    experience_years_required = fields.Integer(
        string='Years of Experience Required',
        help='Minimum years of professional experience required'
    )
    
    requires_education = fields.Boolean(
        string='Requires Education',
        default=False,
        help='Whether this designation has educational requirements'
    )
    
    education_requirements = fields.Text(
        string='Education Requirements',
        help='Description of educational prerequisites'
    )
    
    # Renewal and Maintenance
    has_expiration = fields.Boolean(
        string='Has Expiration Date',
        default=False,
        help='Whether this designation expires and requires renewal'
    )
    
    renewal_period_months = fields.Integer(
        string='Renewal Period (Months)',
        help='Number of months between renewal requirements'
    )
    
    requires_continuing_education = fields.Boolean(
        string='Requires Continuing Education',
        default=False,
        help='Whether maintaining this designation requires continuing education'
    )
    
    ce_hours_required = fields.Float(
        string='CE Hours Required',
        help='Continuing education hours required per renewal period'
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
        help='Whether this designation is currently available'
    )
    
    # Related Records
    member_designation_ids = fields.One2many(
        'ams.member.designation',
        'designation_id',
        string='Member Designations',
        help='Members who hold this designation'
    )
    
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
        help='Number of members with this designation'
    )
    
    # Notes and Additional Information
    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes about this designation'
    )
    
    @api.depends('member_designation_ids')
    def _compute_member_count(self):
        """Compute the number of members with this designation."""
        for designation in self:
            designation.member_count = len(designation.member_designation_ids.filtered('active'))
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure designation codes are unique."""
        for designation in self:
            if designation.code:
                existing = self.search([
                    ('code', '=', designation.code),
                    ('id', '!=', designation.id)
                ])
                if existing:
                    raise ValidationError(_('Designation code "%s" already exists. Codes must be unique.') % designation.code)
    
    @api.constrains('renewal_period_months')
    def _check_renewal_period(self):
        """Validate renewal period if expiration is enabled."""
        for designation in self:
            if designation.has_expiration and designation.renewal_period_months <= 0:
                raise ValidationError(_('Renewal period must be greater than 0 when expiration is enabled.'))
    
    @api.constrains('ce_hours_required')
    def _check_ce_hours(self):
        """Validate continuing education hours."""
        for designation in self:
            if designation.requires_continuing_education and designation.ce_hours_required <= 0:
                raise ValidationError(_('CE hours required must be greater than 0 when continuing education is required.'))
    
    def name_get(self):
        """Return name with code for better identification."""
        result = []
        for designation in self:
            if designation.code:
                name = f'{designation.name} ({designation.code})'
            else:
                name = designation.name
            result.append((designation.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enable search by name or code."""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)


class MemberDesignation(models.Model):
    """Junction model for member professional designations with specific details."""
    
    _name = 'ams.member.designation'
    _description = 'Member Professional Designation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'partner_id, earned_date desc'
    _rec_name = 'designation_id'
    
    # Related Records
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Member who holds this designation'
    )
    
    designation_id = fields.Many2one(
        'ams.professional.designation',
        string='Designation',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Professional designation held'
    )
    
    # Designation Details
    license_number = fields.Char(
        string='License/Certificate Number',
        tracking=True,
        help='Official license or certificate number'
    )
    
    earned_date = fields.Date(
        string='Date Earned',
        tracking=True,
        help='Date when this designation was earned'
    )
    
    expiration_date = fields.Date(
        string='Expiration Date',
        tracking=True,
        help='Date when this designation expires'
    )
    
    issuing_jurisdiction = fields.Char(
        string='Issuing Jurisdiction',
        help='State, province, or country where issued'
    )
    
    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
        ('inactive', 'Inactive')
    ], string='Status', default='active', required=True, tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Whether this designation record is active'
    )
    
    # Computed Fields
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True,
        help='Whether this designation has expired'
    )
    
    days_until_expiration = fields.Integer(
        string='Days Until Expiration',
        compute='_compute_days_until_expiration',
        help='Number of days until expiration'
    )
    
    # Notes
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this designation'
    )
    
    @api.depends('expiration_date')
    def _compute_is_expired(self):
        """Compute if designation is expired."""
        today = fields.Date.context_today(self)
        for member_designation in self:
            if member_designation.expiration_date:
                member_designation.is_expired = member_designation.expiration_date < today
            else:
                member_designation.is_expired = False
    
    @api.depends('expiration_date')
    def _compute_days_until_expiration(self):
        """Compute days until expiration."""
        today = fields.Date.context_today(self)
        for member_designation in self:
            if member_designation.expiration_date:
                delta = member_designation.expiration_date - today
                member_designation.days_until_expiration = delta.days
            else:
                member_designation.days_until_expiration = 0
    
    @api.constrains('earned_date', 'expiration_date')
    def _check_dates(self):
        """Validate date logic."""
        for member_designation in self:
            if (member_designation.earned_date and member_designation.expiration_date 
                and member_designation.earned_date > member_designation.expiration_date):
                raise ValidationError(_('Earned date cannot be after expiration date.'))
    
    @api.model
    def _cron_update_expired_designations(self):
        """Cron job to update status of expired designations."""
        today = fields.Date.context_today(self)
        expired_designations = self.search([
            ('expiration_date', '<', today),
            ('status', '=', 'active')
        ])
        expired_designations.write({'status': 'expired'})
        _logger.info(f'Updated {len(expired_designations)} expired designations')
        
    def action_renew_designation(self):
        """Action to renew an expired designation."""
        self.ensure_one()
        if self.designation_id.has_expiration and self.designation_id.renewal_period_months:
            # Calculate new expiration date
            if self.expiration_date:
                new_expiration = fields.Date.add(self.expiration_date, months=self.designation_id.renewal_period_months)
            else:
                new_expiration = fields.Date.add(fields.Date.context_today(self), months=self.designation_id.renewal_period_months)
            
            self.write({
                'expiration_date': new_expiration,
                'status': 'active'
            })
            
            self.message_post(
                body=_('Designation renewed until %s') % new_expiration,
                message_type='notification'
            )