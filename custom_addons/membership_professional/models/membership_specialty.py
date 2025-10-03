# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipSpecialty(models.Model):
    """
    Professional Specialties & Focus Areas
    """
    _name = 'membership.specialty'
    _description = 'Professional Specialty'
    _order = 'sequence, name'
    _parent_name = 'parent_id'
    _parent_store = True

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Specialty Name',
        required=True,
        translate=True,
        help='Name of specialty (e.g., Cardiology, Structural Engineering)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique code for this specialty'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive specialties are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description of this specialty'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # HIERARCHY
    # ==========================================
    
    parent_id = fields.Many2one(
        'membership.specialty',
        string='Parent Specialty',
        index=True,
        ondelete='restrict',
        help='Parent specialty for hierarchical organization'
    )
    
    parent_path = fields.Char(index=True)
    
    child_ids = fields.One2many(
        'membership.specialty',
        'parent_id',
        string='Sub-Specialties'
    )
    
    child_count = fields.Integer(
        string='Sub-Specialty Count',
        compute='_compute_child_count'
    )

    @api.depends('child_ids')
    def _compute_child_count(self):
        """Count child specialties"""
        for specialty in self:
            specialty.child_count = len(specialty.child_ids)

    # ==========================================
    # CLASSIFICATION
    # ==========================================
    
    specialty_type = fields.Selection([
        ('medical', 'Medical Specialty'),
        ('engineering', 'Engineering Discipline'),
        ('scientific', 'Scientific Field'),
        ('business', 'Business Area'),
        ('legal', 'Legal Practice Area'),
        ('education', 'Educational Field'),
        ('other', 'Other'),
    ], string='Specialty Type',
       default='other',
       help='Type of specialty')
    
    certification_available = fields.Boolean(
        string='Board Certification Available',
        default=False,
        help='Board certification or similar credential available'
    )
    
    certification_credential_id = fields.Many2one(
        'membership.credential',
        string='Related Credential',
        help='Credential associated with this specialty'
    )

    # ==========================================
    # STATISTICS & ASSOCIATIONS
    # ==========================================
    
    partner_count = fields.Integer(
        string='Member Count',
        compute='_compute_partner_count',
        help='Number of members with this specialty'
    )
    
    category_ids = fields.Many2many(
        'membership.category',
        'specialty_category_rel',
        'specialty_id',
        'category_id',
        string='Relevant Categories',
        help='Member categories relevant to this specialty'
    )

    @api.depends('code')  # Dummy dependency
    def _compute_partner_count(self):
        """Count members with this specialty"""
        for specialty in self:
            specialty.partner_count = self.env['res.partner'].search_count([
                ('specialty_ids', 'in', [specialty.id])
            ])

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_view_members(self):
        """View members with this specialty"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('specialty_ids', 'in', [self.id])],
            'context': {'default_specialty_ids': [(6, 0, [self.id])]},
        }

    def get_all_children(self, recursive=True):
        """Get all child specialties"""
        self.ensure_one()
        
        children = self.child_ids
        
        if recursive:
            for child in self.child_ids:
                children |= child.get_all_children(recursive=True)
        
        return children

    def name_get(self):
        """Custom name display with hierarchy"""
        result = []
        for record in self:
            if record.parent_id:
                name = f"{record.parent_id.name} / {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure specialty code is unique"""
        for specialty in self:
            if self.search_count([
                ('code', '=', specialty.code),
                ('id', '!=', specialty.id)
            ]) > 0:
                raise ValidationError(
                    _("Specialty code must be unique. '%s' is already used.") % specialty.code
                )

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Prevent circular parent relationships"""
        if not self._check_recursion():
            raise ValidationError(_(
                'You cannot create recursive specialties.'
            ))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Specialty code must be unique!'),
    ]