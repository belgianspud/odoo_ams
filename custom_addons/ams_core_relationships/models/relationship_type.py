# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class RelationshipType(models.Model):
    _name = 'ams.relationship.type'
    _description = 'Relationship Types'
    _order = 'category, sequence, name'
    _rec_name = 'name'

    # ===== BASIC INFORMATION =====
    name = fields.Char(
        string='Relationship Name',
        required=True,
        translate=True,
        help="Name of the relationship type (e.g., 'Employs', 'Spouse of')"
    )

    code = fields.Char(
        string='Code',
        help="Short code for the relationship type"
    )

    description = fields.Text(
        string='Description',
        translate=True,
        help="Detailed description of this relationship type"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for displaying relationship types"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this relationship type"
    )

    # ===== CATEGORIZATION =====
    category = fields.Selection([
        ('employment', 'Employment'),
        ('family', 'Family'),
        ('household', 'Household'),
        ('emergency', 'Emergency Contact'),
        ('professional', 'Professional'),
        ('business', 'Business'),
        ('personal', 'Personal'),
        ('legal', 'Legal'),
        ('financial', 'Financial'),
        ('medical', 'Medical'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')

    relationship_nature = fields.Selection([
        ('hierarchical', 'Hierarchical'),
        ('peer', 'Peer'),
        ('dependency', 'Dependency'),
        ('service', 'Service'),
        ('legal', 'Legal'),
        ('informal', 'Informal'),
    ], string='Relationship Nature', help="Nature of the relationship")

    # ===== BIDIRECTIONAL SETTINGS =====
    is_bidirectional = fields.Boolean(
        string='Is Bidirectional',
        default=True,
        help="Should this relationship automatically create an inverse?"
    )

    inverse_type_id = fields.Many2one(
        'ams.relationship.type',
        string='Inverse Relationship Type',
        help="The inverse relationship type (e.g., 'Employed by' for 'Employs')"
    )

    inverse_name = fields.Char(
        string='Inverse Name',
        compute='_compute_inverse_name',
        help="Name of the inverse relationship"
    )

    # ===== PERMISSIONS & ACCESS =====
    default_can_access_info = fields.Boolean(
        string='Default: Can Access Info',
        default=False,
        help="Default permission for accessing information"
    )

    default_can_make_decisions = fields.Boolean(
        string='Default: Can Make Decisions',
        default=False,
        help="Default permission for making decisions"
    )

    default_financial_responsibility = fields.Boolean(
        string='Default: Financial Responsibility',
        default=False,
        help="Default financial responsibility setting"
    )

    default_emergency_contact = fields.Boolean(
        string='Default: Emergency Contact',
        default=False,
        help="Default emergency contact setting"
    )

    # ===== VALIDATION RULES =====
    requires_same_organization = fields.Boolean(
        string='Requires Same Organization',
        default=False,
        help="Both partners must be in the same organization"
    )

    requires_different_organization = fields.Boolean(
        string='Requires Different Organization',
        default=False,
        help="Partners must be in different organizations"
    )

    allows_individual_to_individual = fields.Boolean(
        string='Individual ↔ Individual',
        default=True,
        help="Allow relationships between individuals"
    )

    allows_individual_to_organization = fields.Boolean(
        string='Individual ↔ Organization',
        default=True,
        help="Allow relationships between individual and organization"
    )

    allows_organization_to_organization = fields.Boolean(
        string='Organization ↔ Organization',
        default=True,
        help="Allow relationships between organizations"
    )

    # ===== CONSTRAINTS =====
    max_relationships_per_partner = fields.Integer(
        string='Max per Partner',
        default=0,
        help="Maximum relationships of this type per partner (0 = unlimited)"
    )

    is_exclusive = fields.Boolean(
        string='Exclusive',
        default=False,
        help="Only one active relationship of this type allowed"
    )

    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help="Relationships of this type require approval"
    )

    # ===== TEMPORAL SETTINGS =====
    has_duration_limit = fields.Boolean(
        string='Has Duration Limit',
        default=False,
        help="This relationship type has a maximum duration"
    )

    max_duration_days = fields.Integer(
        string='Max Duration (Days)',
        default=0,
        help="Maximum duration in days (0 = unlimited)"
    )

    auto_expire = fields.Boolean(
        string='Auto Expire',
        default=False,
        help="Automatically end relationships after max duration"
    )

    # ===== STATISTICS =====
    relationship_count = fields.Integer(
        string='Relationship Count',
        compute='_compute_relationship_count',
        store=True,
        help="Number of active relationships of this type"
    )

    # ===== USAGE TRACKING =====
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

    # ===== DISPLAY & FORMATTING =====
    icon = fields.Char(
        string='Icon',
        help="FontAwesome icon class for this relationship type"
    )

    color = fields.Integer(
        string='Color',
        default=0,
        help="Color for displaying this relationship type"
    )

    @api.depends('inverse_type_id.name')
    def _compute_inverse_name(self):
        """Compute the inverse relationship name"""
        for rel_type in self:
            rel_type.inverse_name = rel_type.inverse_type_id.name if rel_type.inverse_type_id else ''

    @api.depends('relationship_ids')
    def _compute_relationship_count(self):
        """Compute the number of active relationships of this type"""
        for rel_type in self:
            rel_type.relationship_count = self.env['ams.partner.relationship'].search_count([
                ('relationship_type_id', '=', rel_type.id),
                ('is_active', '=', True),
            ])

    # Add relationship_ids field for the computed count
    relationship_ids = fields.One2many(
        'ams.partner.relationship',
        'relationship_type_id',
        string='Relationships'
    )

    @api.constrains('inverse_type_id')
    def _check_inverse_relationship(self):
        """Validate inverse relationship logic"""
        for rel_type in self:
            if rel_type.is_bidirectional and not rel_type.inverse_type_id:
                raise ValidationError(_("Bidirectional relationship types must have an inverse type defined"))
            
            # Check for circular inverse relationships
            if rel_type.inverse_type_id and rel_type.inverse_type_id.inverse_type_id:
                if rel_type.inverse_type_id.inverse_type_id.id != rel_type.id:
                    raise ValidationError(_("Inverse relationship types must point to each other"))

    @api.constrains('requires_same_organization', 'requires_different_organization')
    def _check_organization_requirements(self):
        """Ensure organization requirements are not conflicting"""
        for rel_type in self:
            if rel_type.requires_same_organization and rel_type.requires_different_organization:
                raise ValidationError(_("Cannot require both same and different organizations"))

    @api.constrains('max_duration_days')
    def _check_max_duration(self):
        """Validate maximum duration"""
        for rel_type in self:
            if rel_type.has_duration_limit and rel_type.max_duration_days <= 0:
                raise ValidationError(_("Maximum duration must be positive when duration limit is enabled"))

    @api.model
    def create(self, vals):
        """Override create to set last_updated"""
        vals['last_updated'] = fields.Datetime.now()
        return super(RelationshipType, self).create(vals)

    def write(self, vals):
        """Override write to update last_updated timestamp"""
        vals['last_updated'] = fields.Datetime.now()
        return super(RelationshipType, self).write(vals)

    def name_get(self):
        """Override name_get to include category and inverse"""
        result = []
        for rel_type in self:
            name_parts = []
            
            # Add category prefix if configured
            if rel_type.category and rel_type.category != 'other':
                category_name = dict(rel_type._fields['category'].selection)[rel_type.category]
                name_parts.append(f"[{category_name}]")
            
            # Add main name
            name_parts.append(rel_type.name)
            
            # Add inverse indicator if bidirectional
            if rel_type.is_bidirectional and rel_type.inverse_type_id:
                name_parts.append(f"↔ {rel_type.inverse_type_id.name}")
            
            result.append((rel_type.id, ' '.join(name_parts)))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to search both name and code"""
        args = args or []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
            rel_types = self.search(domain + args, limit=limit)
            return rel_types.name_get()
        return super(RelationshipType, self).name_search(
            name=name, args=args, operator=operator, limit=limit)

    def action_view_relationships(self):
        """Action to view all relationships of this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Relationships: {self.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form',
            'domain': [('relationship_type_id', '=', self.id)],
            'context': {'default_relationship_type_id': self.id},
        }

    def action_create_inverse_type(self):
        """Action to create the inverse relationship type"""
        self.ensure_one()
        if self.inverse_type_id:
            raise ValidationError(_("Inverse relationship type already exists"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Create Inverse for {self.name}',
            'res_model': 'ams.relationship.type',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f"Inverse of {self.name}",
                'default_category': self.category,
                'default_is_bidirectional': True,
                'default_inverse_type_id': self.id,
                'default_relationship_nature': self.relationship_nature,
            },
        }

    def toggle_active(self):
        """Toggle active status"""
        for rel_type in self:
            rel_type.active = not rel_type.active

    @api.model
    def get_types_by_category(self, category):
        """Get all relationship types in a specific category"""
        return self.search([('category', '=', category), ('active', '=', True)], order='sequence, name')

    @api.model
    def get_employment_types(self):
        """Get employment relationship types"""
        return self.get_types_by_category('employment')

    @api.model
    def get_family_types(self):
        """Get family relationship types"""
        return self.get_types_by_category('family')

    @api.model
    def get_emergency_contact_types(self):
        """Get emergency contact relationship types"""
        return self.get_types_by_category('emergency')

    def validate_relationship_partners(self, partner_a, partner_b):
        """Validate if two partners can have this relationship type"""
        self.ensure_one()
        
        # Check individual/organization constraints
        if partner_a.is_company and partner_b.is_company:
            if not self.allows_organization_to_organization:
                raise ValidationError(_("This relationship type does not allow organization to organization relationships"))
        elif partner_a.is_company or partner_b.is_company:
            if not self.allows_individual_to_organization:
                raise ValidationError(_("This relationship type does not allow individual to organization relationships"))
        else:
            if not self.allows_individual_to_individual:
                raise ValidationError(_("This relationship type does not allow individual to individual relationships"))
        
        # Check organization requirements
        if self.requires_same_organization:
            if partner_a.parent_id != partner_b.parent_id and partner_a.id != partner_b.parent_id.id and partner_b.id != partner_a.parent_id.id:
                raise ValidationError(_("This relationship type requires partners to be in the same organization"))
        
        if self.requires_different_organization:
            if partner_a.parent_id == partner_b.parent_id or partner_a.id == partner_b.parent_id.id or partner_b.id == partner_a.parent_id.id:
                raise ValidationError(_("This relationship type requires partners to be in different organizations"))
        
        # Check exclusivity
        if self.is_exclusive:
            existing = self.env['ams.partner.relationship'].search([
                ('partner_a_id', '=', partner_a.id),
                ('relationship_type_id', '=', self.id),
                ('is_active', '=', True),
            ])
            if existing:
                raise ValidationError(_("Partner already has an exclusive relationship of this type"))
        
        # Check maximum relationships
        if self.max_relationships_per_partner > 0:
            count = self.env['ams.partner.relationship'].search_count([
                ('partner_a_id', '=', partner_a.id),
                ('relationship_type_id', '=', self.id),
                ('is_active', '=', True),
            ])
            if count >= self.max_relationships_per_partner:
                raise ValidationError(_("Partner has reached the maximum number of relationships of this type"))
        
        return True

    @api.model
    def cleanup_unused_types(self):
        """Remove relationship types with no relationships"""
        unused = self.search([('relationship_count', '=', 0), ('active', '=', False)])
        count = len(unused)
        if unused:
            unused.unlink()
            _logger.info(f"Cleaned up {count} unused relationship types")
        return count