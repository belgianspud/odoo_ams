# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AmsRelationshipType(models.Model):
    _name = 'ams.relationship.type'
    _description = 'Relationship Type Definition'
    _order = 'sequence, name'

    name = fields.Char(
        string='Relationship Name',
        required=True,
        help="Name of the relationship (e.g., Spouse, Employee, Board Member)"
    )
    code = fields.Char(
        string='Relationship Code',
        required=True,
        help="Short code for the relationship (e.g., SPOUSE, EMPLOYEE)"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of this relationship type"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order in which relationships are displayed"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to hide this relationship type from selection"
    )

    # Reciprocal relationship configuration
    reciprocal_type_id = fields.Many2one(
        'ams.relationship.type',
        string='Reciprocal Relationship',
        help="The reciprocal relationship type (e.g., Employee <-> Employer)"
    )
    is_symmetric = fields.Boolean(
        string='Is Symmetric',
        default=False,
        help="True if this relationship is the same in both directions (e.g., Spouse)"
    )
    auto_create_reciprocal = fields.Boolean(
        string='Auto Create Reciprocal',
        default=True,
        help="Automatically create the reciprocal relationship when this one is created"
    )

    # Relationship constraints
    allow_multiple = fields.Boolean(
        string='Allow Multiple',
        default=True,
        help="Allow a partner to have multiple relationships of this type"
    )
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help="Relationships of this type require approval before becoming active"
    )
    is_hierarchical = fields.Boolean(
        string='Is Hierarchical',
        default=False,
        help="This relationship represents a hierarchy (parent/child, manager/employee)"
    )

    # Applicability
    individual_to_individual = fields.Boolean(
        string='Individual to Individual',
        default=True,
        help="This relationship can exist between two individuals"
    )
    individual_to_organization = fields.Boolean(
        string='Individual to Organization',
        default=True,
        help="This relationship can exist between an individual and organization"
    )
    organization_to_organization = fields.Boolean(
        string='Organization to Organization',
        default=False,
        help="This relationship can exist between two organizations"
    )

    # Relationship tracking
    relationship_ids = fields.One2many(
        'ams.partner.relationship',
        'relationship_type_id',
        string='Relationships'
    )
    relationship_count = fields.Integer(
        string='Relationship Count',
        compute='_compute_relationship_count'
    )

    # Display and behavior settings
    display_on_partner_form = fields.Boolean(
        string='Display on Partner Form',
        default=True,
        help="Show this relationship type on partner forms"
    )
    color = fields.Integer(
        string='Color',
        help="Color for this relationship type in views"
    )
    icon = fields.Char(
        string='Icon',
        help="FontAwesome icon for this relationship type"
    )

    @api.depends('relationship_ids')
    def _compute_relationship_count(self):
        """Compute number of active relationships for this type"""
        for rel_type in self:
            rel_type.relationship_count = len(rel_type.relationship_ids.filtered('active'))

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure relationship codes are unique"""
        for rel_type in self:
            if rel_type.code:
                duplicate = self.search([
                    ('code', '=', rel_type.code),
                    ('id', '!=', rel_type.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Relationship code '%s' already exists. Codes must be unique.") % rel_type.code
                    )

    @api.constrains('reciprocal_type_id', 'is_symmetric')
    def _check_reciprocal_relationship(self):
        """Validate reciprocal relationship configuration"""
        for rel_type in self:
            if rel_type.is_symmetric:
                # Symmetric relationships should point to themselves as reciprocal
                if rel_type.reciprocal_type_id and rel_type.reciprocal_type_id != rel_type:
                    raise ValidationError(
                        _("Symmetric relationship '%s' should not have a different reciprocal type.") % rel_type.name
                    )
            elif rel_type.reciprocal_type_id:
                # Non-symmetric relationships should have different reciprocal types
                if rel_type.reciprocal_type_id == rel_type:
                    raise ValidationError(
                        _("Non-symmetric relationship '%s' cannot be its own reciprocal.") % rel_type.name
                    )

    def name_get(self):
        """Custom name display including code"""
        result = []
        for rel_type in self:
            if rel_type.code:
                name = f"[{rel_type.code}] {rel_type.name}"
            else:
                name = rel_type.name
            result.append((rel_type.id, name))
        return result

    @api.model
    def create(self, vals):
        """Override create to handle symmetric relationships"""
        rel_type = super().create(vals)
        
        # Handle symmetric relationships
        if rel_type.is_symmetric and not rel_type.reciprocal_type_id:
            rel_type.reciprocal_type_id = rel_type.id
            
        return rel_type

    def write(self, vals):
        """Override write to handle symmetric relationship changes"""
        result = super().write(vals)
        
        # Handle symmetric relationship changes
        if 'is_symmetric' in vals:
            for rel_type in self:
                if rel_type.is_symmetric:
                    rel_type.reciprocal_type_id = rel_type.id
                elif rel_type.reciprocal_type_id == rel_type:
                    rel_type.reciprocal_type_id = False
                    
        return result

    def action_view_relationships(self):
        """Action to view all relationships of this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relationships: %s') % self.name,
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form',
            'domain': [('relationship_type_id', '=', self.id)],
            'context': {'default_relationship_type_id': self.id}
        }

    def get_reciprocal_type(self):
        """Get the reciprocal relationship type"""
        self.ensure_one()
        if self.is_symmetric:
            return self
        return self.reciprocal_type_id

    @api.model
    def get_applicable_types(self, partner_from_type, partner_to_type):
        """
        Get relationship types applicable between two partner types
        
        Args:
            partner_from_type: 'individual' or 'organization'
            partner_to_type: 'individual' or 'organization'
            
        Returns:
            recordset of applicable relationship types
        """
        domain = [('active', '=', True)]
        
        if partner_from_type == 'individual' and partner_to_type == 'individual':
            domain.append(('individual_to_individual', '=', True))
        elif partner_from_type == 'individual' and partner_to_type == 'organization':
            domain.append(('individual_to_organization', '=', True))
        elif partner_from_type == 'organization' and partner_to_type == 'individual':
            # Use reciprocal logic - find types where individual_to_organization is True
            domain.append(('individual_to_organization', '=', True))
        elif partner_from_type == 'organization' and partner_to_type == 'organization':
            domain.append(('organization_to_organization', '=', True))
            
        return self.search(domain)

    @api.model
    def create_default_types(self):
        """Create default relationship types if they don't exist"""
        default_types = [
            {
                'name': 'Spouse',
                'code': 'SPOUSE',
                'description': 'Married couple or domestic partners',
                'is_symmetric': True,
                'allow_multiple': False,
                'individual_to_individual': True,
                'individual_to_organization': False,
                'organization_to_organization': False,
                'icon': 'fa-heart',
                'sequence': 10
            },
            {
                'name': 'Child',
                'code': 'CHILD',
                'description': 'Parent-child relationship',
                'is_symmetric': False,
                'allow_multiple': True,
                'is_hierarchical': True,
                'individual_to_individual': True,
                'individual_to_organization': False,
                'organization_to_organization': False,
                'icon': 'fa-child',
                'sequence': 20
            },
            {
                'name': 'Parent',
                'code': 'PARENT',
                'description': 'Parent-child relationship (reverse)',
                'is_symmetric': False,
                'allow_multiple': True,
                'is_hierarchical': True,
                'individual_to_individual': True,
                'individual_to_organization': False,
                'organization_to_organization': False,
                'icon': 'fa-user',
                'sequence': 21
            },
            {
                'name': 'Employee',
                'code': 'EMPLOYEE',
                'description': 'Employment relationship',
                'is_symmetric': False,
                'allow_multiple': False,
                'is_hierarchical': True,
                'individual_to_individual': False,
                'individual_to_organization': True,
                'organization_to_organization': False,
                'icon': 'fa-briefcase',
                'sequence': 30
            },
            {
                'name': 'Employer',
                'code': 'EMPLOYER',
                'description': 'Employment relationship (reverse)',
                'is_symmetric': False,
                'allow_multiple': True,
                'is_hierarchical': True,
                'individual_to_individual': False,
                'individual_to_organization': True,
                'organization_to_organization': False,
                'icon': 'fa-building',
                'sequence': 31
            }
        ]
        
        created_types = {}
        for type_data in default_types:
            existing = self.search([('code', '=', type_data['code'])], limit=1)
            if not existing:
                created_types[type_data['code']] = self.create(type_data)
            else:
                created_types[type_data['code']] = existing
                
        # Set up reciprocal relationships
        if 'CHILD' in created_types and 'PARENT' in created_types:
            created_types['CHILD'].reciprocal_type_id = created_types['PARENT'].id
            created_types['PARENT'].reciprocal_type_id = created_types['CHILD'].id
            
        if 'EMPLOYEE' in created_types and 'EMPLOYER' in created_types:
            created_types['EMPLOYEE'].reciprocal_type_id = created_types['EMPLOYER'].id
            created_types['EMPLOYER'].reciprocal_type_id = created_types['EMPLOYEE'].id
            
        return created_types