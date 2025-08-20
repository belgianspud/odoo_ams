# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProfessionalDesignation(models.Model):
    _name = 'ams.professional.designation'
    _description = 'Professional Designations and Certifications'
    _order = 'sequence, name'
    _rec_name = 'name'

    # ===== BASIC INFORMATION =====
    name = fields.Char(
        string='Designation Name',
        required=True,
        translate=True,
        help="Name of the professional designation (e.g., MD, PhD, PE, CPA)"
    )

    code = fields.Char(
        string='Code',
        required=True,
        help="Short code or abbreviation for the designation"
    )

    description = fields.Text(
        string='Description',
        translate=True,
        help="Detailed description of the designation"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for displaying designations"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this designation"
    )

    # ===== CLASSIFICATION =====
    designation_type = fields.Selection([
        ('degree', 'Academic Degree'),
        ('certification', 'Professional Certification'),
        ('license', 'Professional License'),
        ('title', 'Professional Title'),
        ('membership', 'Membership Designation'),
        ('award', 'Award or Honor'),
        ('other', 'Other'),
    ], string='Designation Type', required=True, default='certification')

    category = fields.Selection([
        ('education', 'Education'),
        ('healthcare', 'Healthcare'),
        ('engineering', 'Engineering'),
        ('legal', 'Legal'),
        ('business', 'Business'),
        ('aviation', 'Aviation'),
        ('science', 'Science'),
        ('technology', 'Technology'),
        ('general', 'General'),
    ], string='Category', default='general')

    # ===== REQUIREMENTS & VALIDITY =====
    requires_license = fields.Boolean(
        string='Requires License',
        default=False,
        help="Check if this designation requires a professional license"
    )

    requires_continuing_education = fields.Boolean(
        string='Requires Continuing Education',
        default=False,
        help="Check if this designation requires ongoing CE/CME"
    )

    ce_hours_required_annual = fields.Float(
        string='Annual CE Hours Required',
        default=0.0,
        help="Number of continuing education hours required annually"
    )

    has_expiry = fields.Boolean(
        string='Has Expiry Date',
        default=False,
        help="Check if this designation expires and needs renewal"
    )

    validity_period_years = fields.Integer(
        string='Validity Period (Years)',
        default=0,
        help="Number of years the designation is valid (0 = permanent)"
    )

    # ===== ISSUING ORGANIZATION =====
    issuing_organization = fields.Char(
        string='Issuing Organization',
        help="Organization that issues this designation"
    )

    issuing_country = fields.Many2one(
        'res.country',
        string='Issuing Country',
        help="Country where this designation is issued"
    )

    website_url = fields.Char(
        string='Website URL',
        help="Official website for this designation"
    )

    # ===== MEMBER RELATIONSHIPS =====
    member_ids = fields.Many2many(
        'res.partner',
        'partner_professional_designation_rel',
        'designation_id',
        'partner_id',
        string='Members with this Designation'
    )

    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
        help="Number of members with this designation"
    )

    # ===== RELATED DESIGNATIONS =====
    prerequisite_ids = fields.Many2many(
        'ams.professional.designation',
        'designation_prerequisite_rel',
        'designation_id',
        'prerequisite_id',
        string='Prerequisites',
        help="Designations required before obtaining this one"
    )

    successor_ids = fields.Many2many(
        'ams.professional.designation',
        'designation_prerequisite_rel',
        'prerequisite_id',
        'designation_id',
        string='Leads to',
        help="Designations this one can lead to"
    )

    # ===== NOTES AND METADATA =====
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this designation"
    )

    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
        readonly=True
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        """Compute the number of members with this designation"""
        for designation in self:
            designation.member_count = len(designation.member_ids)

    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure designation codes are unique"""
        for designation in self:
            if designation.code:
                existing = self.search([
                    ('code', '=ilike', designation.code),
                    ('id', '!=', designation.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_("Designation code '%s' already exists for '%s'") % 
                                        (designation.code, existing.name))

    @api.constrains('validity_period_years')
    def _check_validity_period(self):
        """Validate validity period is reasonable"""
        for designation in self:
            if designation.validity_period_years < 0:
                raise ValidationError(_("Validity period cannot be negative"))
            if designation.validity_period_years > 50:
                raise ValidationError(_("Validity period cannot exceed 50 years"))

    @api.constrains('ce_hours_required_annual')
    def _check_ce_hours(self):
        """Validate CE hours are reasonable"""
        for designation in self:
            if designation.ce_hours_required_annual < 0:
                raise ValidationError(_("CE hours cannot be negative"))
            if designation.ce_hours_required_annual > 1000:
                raise ValidationError(_("CE hours cannot exceed 1000 per year"))

    @api.constrains('prerequisite_ids')
    def _check_no_circular_prerequisites(self):
        """Prevent circular prerequisite relationships"""
        for designation in self:
            if designation in designation.prerequisite_ids:
                raise ValidationError(_("A designation cannot be a prerequisite of itself"))
            
            # Check for circular dependencies (A requires B, B requires A)
            def check_circular(current, visited):
                if current.id in visited:
                    return True
                visited.add(current.id)
                for prereq in current.prerequisite_ids:
                    if check_circular(prereq, visited.copy()):
                        return True
                return False
            
            if check_circular(designation, set()):
                raise ValidationError(_("Circular prerequisite dependency detected"))

    @api.model
    def create(self, vals):
        """Override create to set last_updated"""
        vals['last_updated'] = fields.Datetime.now()
        return super(ProfessionalDesignation, self).create(vals)

    def write(self, vals):
        """Override write to update last_updated timestamp"""
        vals['last_updated'] = fields.Datetime.now()
        return super(ProfessionalDesignation, self).write(vals)

    def name_get(self):
        """Override name_get to include code in display"""
        result = []
        for designation in self:
            if designation.code:
                name = f"[{designation.code}] {designation.name}"
            else:
                name = designation.name
            result.append((designation.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to search both name and code"""
        args = args or []
        if name:
            # Search in both name and code fields
            domain = ['|', ('name', operator, name), ('code', operator, name)]
            designations = self.search(domain + args, limit=limit)
            return designations.name_get()
        return super(ProfessionalDesignation, self).name_search(
            name=name, args=args, operator=operator, limit=limit)

    def action_view_members(self):
        """Action to view members with this designation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Members with {self.name}',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('professional_designation_ids', 'in', self.id)],
            'context': {'default_professional_designation_ids': [(6, 0, [self.id])]},
        }

    def action_duplicate(self):
        """Action to duplicate designation with similar settings"""
        self.ensure_one()
        copy_vals = {
            'name': f"{self.name} (Copy)",
            'code': f"{self.code}_COPY",
            'description': self.description,
            'designation_type': self.designation_type,
            'category': self.category,
            'requires_license': self.requires_license,
            'requires_continuing_education': self.requires_continuing_education,
            'ce_hours_required_annual': self.ce_hours_required_annual,
            'has_expiry': self.has_expiry,
            'validity_period_years': self.validity_period_years,
            'issuing_organization': self.issuing_organization,
            'issuing_country': self.issuing_country.id if self.issuing_country else False,
        }
        new_designation = self.create(copy_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Professional Designation',
            'res_model': 'ams.professional.designation',
            'view_mode': 'form',
            'res_id': new_designation.id,
            'target': 'current',
        }

    @api.model
    def get_popular_designations(self, limit=10):
        """Get most popular designations by member count"""
        return self.search([], order='member_count desc', limit=limit)

    def toggle_active(self):
        """Toggle active status"""
        for designation in self:
            designation.active = not designation.active

    @api.model
    def cleanup_unused_designations(self):
        """Remove designations with no members (admin utility)"""
        unused = self.search([('member_count', '=', 0), ('active', '=', False)])
        if unused:
            _logger.info(f"Cleaning up {len(unused)} unused designations")
            unused.unlink()
        return len(unused)