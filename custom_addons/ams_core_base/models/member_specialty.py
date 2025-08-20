# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MemberSpecialty(models.Model):
    _name = 'ams.member.specialty'
    _description = 'Member Specialties and Practice Areas'
    _order = 'category, sequence, name'
    _rec_name = 'name'

    # ===== BASIC INFORMATION =====
    name = fields.Char(
        string='Specialty Name',
        required=True,
        translate=True,
        help="Name of the specialty or practice area"
    )

    code = fields.Char(
        string='Code',
        help="Short code or abbreviation for the specialty"
    )

    description = fields.Text(
        string='Description',
        translate=True,
        help="Detailed description of the specialty area"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for displaying specialties"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this specialty"
    )

    # ===== CLASSIFICATION =====
    category = fields.Selection([
        ('medical', 'Medical'),
        ('surgical', 'Surgical'),
        ('engineering', 'Engineering'),
        ('legal', 'Legal'),
        ('business', 'Business'),
        ('aviation', 'Aviation'),
        ('science', 'Science'),
        ('technology', 'Technology'),
        ('education', 'Education'),
        ('research', 'Research'),
        ('clinical', 'Clinical'),
        ('administrative', 'Administrative'),
        ('regulatory', 'Regulatory'),
        ('consulting', 'Consulting'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')

    specialty_type = fields.Selection([
        ('practice_area', 'Practice Area'),
        ('subspecialty', 'Subspecialty'),
        ('certification_area', 'Certification Area'),
        ('interest_area', 'Interest Area'),
        ('expertise', 'Area of Expertise'),
        ('industry_focus', 'Industry Focus'),
    ], string='Specialty Type', required=True, default='practice_area')

    # ===== HIERARCHY =====
    parent_id = fields.Many2one(
        'ams.member.specialty',
        string='Parent Specialty',
        help="Parent specialty for hierarchical organization"
    )

    child_ids = fields.One2many(
        'ams.member.specialty',
        'parent_id',
        string='Sub-specialties'
    )

    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        store=True,
        help="Hierarchy level (0=root, 1=child, etc.)"
    )

    # ===== PROFESSIONAL REQUIREMENTS =====
    requires_certification = fields.Boolean(
        string='Requires Certification',
        default=False,
        help="Check if this specialty requires specific certification"
    )

    required_designation_ids = fields.Many2many(
        'ams.professional.designation',
        'specialty_designation_rel',
        'specialty_id',
        'designation_id',
        string='Required Designations',
        help="Professional designations required for this specialty"
    )

    min_experience_years = fields.Integer(
        string='Minimum Experience (Years)',
        default=0,
        help="Minimum years of experience required"
    )

    # ===== EDUCATION & TRAINING =====
    training_required = fields.Boolean(
        string='Training Required',
        default=False,
        help="Check if specialized training is required"
    )

    training_description = fields.Text(
        string='Training Description',
        help="Description of required training or education"
    )

    # ===== MEMBER RELATIONSHIPS =====
    member_ids = fields.Many2many(
        'res.partner',
        'partner_specialty_rel',
        'specialty_id',
        'partner_id',
        string='Members with this Specialty'
    )

    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True,
        help="Number of members with this specialty"
    )

    # ===== INDUSTRY & ASSOCIATIONS =====
    industry_sectors = fields.Char(
        string='Industry Sectors',
        help="Relevant industry sectors for this specialty"
    )

    related_associations = fields.Text(
        string='Related Associations',
        help="Other professional associations relevant to this specialty"
    )

    # ===== REGULATORY INFORMATION =====
    regulatory_body = fields.Char(
        string='Regulatory Body',
        help="Primary regulatory body overseeing this specialty"
    )

    license_required = fields.Boolean(
        string='License Required',
        default=False,
        help="Check if a specific license is required"
    )

    # ===== TAGS AND KEYWORDS =====
    keyword_tags = fields.Char(
        string='Keywords',
        help="Search keywords and tags (comma-separated)"
    )

    # ===== METADATA =====
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

    notes = fields.Text(
        string='Notes',
        help="Additional notes about this specialty"
    )

    @api.depends('parent_id')
    def _compute_level(self):
        """Compute hierarchy level"""
        for specialty in self:
            level = 0
            current = specialty.parent_id
            while current:
                level += 1
                current = current.parent_id
                if level > 10:  # Prevent infinite loops
                    break
            specialty.level = level

    @api.depends('member_ids')
    def _compute_member_count(self):
        """Compute the number of members with this specialty"""
        for specialty in self:
            specialty.member_count = len(specialty.member_ids)

    @api.constrains('parent_id')
    def _check_no_circular_hierarchy(self):
        """Prevent circular parent-child relationships"""
        for specialty in self:
            if specialty.parent_id:
                current = specialty.parent_id
                visited = {specialty.id}
                while current:
                    if current.id in visited:
                        raise ValidationError(_("Circular hierarchy detected in specialty '%s'") % specialty.name)
                    visited.add(current.id)
                    current = current.parent_id

    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure specialty codes are unique within the same category"""
        for specialty in self:
            if specialty.code:
                existing = self.search([
                    ('code', '=ilike', specialty.code),
                    ('category', '=', specialty.category),
                    ('id', '!=', specialty.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_("Specialty code '%s' already exists in category '%s' for '%s'") % 
                                        (specialty.code, specialty.category, existing.name))

    @api.constrains('min_experience_years')
    def _check_experience_years(self):
        """Validate experience years are reasonable"""
        for specialty in self:
            if specialty.min_experience_years < 0:
                raise ValidationError(_("Minimum experience years cannot be negative"))
            if specialty.min_experience_years > 50:
                raise ValidationError(_("Minimum experience years cannot exceed 50"))

    @api.model
    def create(self, vals):
        """Override create to set last_updated"""
        vals['last_updated'] = fields.Datetime.now()
        return super(MemberSpecialty, self).create(vals)

    def write(self, vals):
        """Override write to update last_updated timestamp"""
        vals['last_updated'] = fields.Datetime.now()
        return super(MemberSpecialty, self).write(vals)

    def name_get(self):
        """Override name_get to include hierarchy and code"""
        result = []
        for specialty in self:
            name_parts = []
            
            # Add hierarchy prefix
            if specialty.level > 0:
                name_parts.append('  ' * specialty.level + '↳ ')
            
            # Add code if exists
            if specialty.code:
                name_parts.append(f"[{specialty.code}] ")
            
            # Add name
            name_parts.append(specialty.name)
            
            # Add parent context if it's a child
            if specialty.parent_id:
                name_parts.append(f" ({specialty.parent_id.name})")
            
            result.append((specialty.id, ''.join(name_parts)))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to search name, code, and keywords"""
        args = args or []
        if name:
            domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('keyword_tags', operator, name),
                ('description', operator, name)
            ]
            specialties = self.search(domain + args, limit=limit)
            return specialties.name_get()
        return super(MemberSpecialty, self).name_search(
            name=name, args=args, operator=operator, limit=limit)

    def action_view_members(self):
        """Action to view members with this specialty"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Members with {self.name} Specialty',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('specialty_ids', 'in', self.id)],
            'context': {'default_specialty_ids': [(6, 0, [self.id])]},
        }

    def action_view_children(self):
        """Action to view child specialties"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sub-specialties of {self.name}',
            'res_model': 'ams.member.specialty',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id, 'default_category': self.category},
        }

    def action_create_child_specialty(self):
        """Action to create a child specialty"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'New Sub-specialty of {self.name}',
            'res_model': 'ams.member.specialty',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_parent_id': self.id,
                'default_category': self.category,
                'default_specialty_type': 'subspecialty',
            },
        }

    @api.model
    def get_root_specialties(self):
        """Get all root-level specialties (no parent)"""
        return self.search([('parent_id', '=', False)], order='category, sequence, name')

    @api.model
    def get_specialties_by_category(self, category):
        """Get all specialties in a specific category"""
        return self.search([('category', '=', category)], order='sequence, name')

    @api.model
    def get_popular_specialties(self, limit=10):
        """Get most popular specialties by member count"""
        return self.search([], order='member_count desc', limit=limit)

    def get_full_hierarchy_name(self):
        """Get full hierarchical name including all parents"""
        self.ensure_one()
        names = [self.name]
        current = self.parent_id
        while current:
            names.insert(0, current.name)
            current = current.parent_id
        return ' → '.join(names)

    @api.model
    def search_by_keywords(self, keywords):
        """Search specialties by keywords"""
        if not keywords:
            return self.browse()
        
        keywords = keywords.split(',') if isinstance(keywords, str) else keywords
        domain = []
        
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword:
                domain.extend([
                    '|', '|', '|',
                    ('name', 'ilike', keyword),
                    ('description', 'ilike', keyword),
                    ('keyword_tags', 'ilike', keyword),
                    ('industry_sectors', 'ilike', keyword),
                ])
        
        return self.search(domain)

    def toggle_active(self):
        """Toggle active status"""
        for specialty in self:
            specialty.active = not specialty.active

    @api.model
    def cleanup_unused_specialties(self):
        """Remove specialties with no members (admin utility)"""
        unused = self.search([('member_count', '=', 0), ('active', '=', False)])
        if unused:
            _logger.info(f"Cleaning up {len(unused)} unused specialties")
            unused.unlink()
        return len(unused)