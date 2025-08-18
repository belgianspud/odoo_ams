# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AmsPartnerRelationship(models.Model):
    _name = 'ams.partner.relationship'
    _description = 'Partner Relationship'
    _order = 'partner_from_id, relationship_type_id, partner_to_id'
    _rec_name = 'display_name'

    # Core relationship fields
    partner_from_id = fields.Many2one(
        'res.partner',
        string='From Partner',
        required=True,
        ondelete='cascade',
        help="The partner who has this relationship"
    )
    partner_to_id = fields.Many2one(
        'res.partner',
        string='To Partner',
        required=True,
        ondelete='cascade',
        help="The partner who is the target of this relationship"
    )
    relationship_type_id = fields.Many2one(
        'ams.relationship.type',
        string='Relationship Type',
        required=True,
        ondelete='cascade',
        help="Type of relationship between the partners"
    )

    # Relationship details
    date_start = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        help="When this relationship began"
    )
    date_end = fields.Date(
        string='End Date',
        help="When this relationship ended (leave blank for ongoing)"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Whether this relationship is currently active"
    )
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this relationship"
    )

    # Status and approval
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help="User who approved this relationship"
    )
    approved_date = fields.Datetime(
        string='Approval Date',
        help="When this relationship was approved"
    )

    # Reciprocal relationship
    reciprocal_relationship_id = fields.Many2one(
        'ams.partner.relationship',
        string='Reciprocal Relationship',
        help="The corresponding reciprocal relationship record"
    )
    has_reciprocal = fields.Boolean(
        string='Has Reciprocal',
        compute='_compute_has_reciprocal',
        store=True,
        help="True if this relationship has a reciprocal relationship"
    )

    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    is_current = fields.Boolean(
        string='Is Current',
        compute='_compute_is_current',
        store=True,
        help="True if this relationship is currently active"
    )
    partner_from_type = fields.Selection(
        related='partner_from_id.company_type',
        string='From Type',
        store=True
    )
    partner_to_type = fields.Selection(
        related='partner_to_id.company_type',
        string='To Type',
        store=True
    )

    # Hierarchy fields
    is_hierarchical = fields.Boolean(
        related='relationship_type_id.is_hierarchical',
        string='Is Hierarchical'
    )
    hierarchy_level = fields.Integer(
        string='Hierarchy Level',
        default=0,
        help="Level in organizational hierarchy (0 = top level)"
    )

    @api.depends('partner_from_id.name', 'relationship_type_id.name', 'partner_to_id.name')
    def _compute_display_name(self):
        """Compute display name for relationship"""
        for relationship in self:
            if relationship.partner_from_id and relationship.relationship_type_id and relationship.partner_to_id:
                relationship.display_name = (
                    f"{relationship.partner_from_id.name} - "
                    f"{relationship.relationship_type_id.name} - "
                    f"{relationship.partner_to_id.name}"
                )
            else:
                relationship.display_name = _("Partner Relationship")

    @api.depends('active', 'date_start', 'date_end', 'state')
    def _compute_is_current(self):
        """Compute if this relationship is currently active"""
        today = fields.Date.today()
        for relationship in self:
            relationship.is_current = (
                relationship.active and
                relationship.state in ['active', 'approved'] and
                relationship.date_start <= today and
                (not relationship.date_end or relationship.date_end >= today)
            )

    @api.depends('reciprocal_relationship_id')
    def _compute_has_reciprocal(self):
        """Compute if this relationship has a reciprocal relationship"""
        for relationship in self:
            relationship.has_reciprocal = bool(relationship.reciprocal_relationship_id)

    @api.constrains('partner_from_id', 'partner_to_id')
    def _check_different_partners(self):
        """Ensure partners are different"""
        for relationship in self:
            if relationship.partner_from_id == relationship.partner_to_id:
                raise ValidationError(
                    _("A partner cannot have a relationship with themselves.")
                )

    @api.constrains('date_start', 'date_end')
    def _check_date_consistency(self):
        """Ensure date consistency"""
        for relationship in self:
            if relationship.date_end and relationship.date_start:
                if relationship.date_end < relationship.date_start:
                    raise ValidationError(
                        _("End date cannot be before start date.")
                    )

    @api.constrains('partner_from_id', 'partner_to_id', 'relationship_type_id', 'date_start', 'date_end')
    def _check_relationship_constraints(self):
        """Check relationship type constraints"""
        for relationship in self:
            rel_type = relationship.relationship_type_id
            
            # Check partner type compatibility
            from_type = 'individual' if not relationship.partner_from_id.is_company else 'organization'
            to_type = 'individual' if not relationship.partner_to_id.is_company else 'organization'
            
            valid = False
            if from_type == 'individual' and to_type == 'individual' and rel_type.individual_to_individual:
                valid = True
            elif from_type == 'individual' and to_type == 'organization' and rel_type.individual_to_organization:
                valid = True
            elif from_type == 'organization' and to_type == 'individual' and rel_type.individual_to_organization:
                valid = True
            elif from_type == 'organization' and to_type == 'organization' and rel_type.organization_to_organization:
                valid = True
                
            if not valid:
                raise ValidationError(
                    _("Relationship type '%s' is not applicable between %s and %s.") 
                    % (rel_type.name, from_type, to_type)
                )

            # Check multiple relationship constraint
            if not rel_type.allow_multiple:
                existing = self.search([
                    ('partner_from_id', '=', relationship.partner_from_id.id),
                    ('relationship_type_id', '=', rel_type.id),
                    ('active', '=', True),
                    ('state', 'in', ['active', 'approved']),
                    ('id', '!=', relationship.id),
                    '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', relationship.date_start)
                ])
                if existing:
                    raise ValidationError(
                        _("Partner '%s' already has an active '%s' relationship.") 
                        % (relationship.partner_from_id.name, rel_type.name)
                    )

    @api.model
    def create(self, vals):
        """Override create to handle reciprocal relationships and approval workflow"""
        relationship = super().create(vals)
        
        # Handle approval workflow
        if relationship.relationship_type_id.requires_approval:
            relationship.state = 'pending'
        else:
            relationship.state = 'active'
            
        # Create reciprocal relationship if needed
        if relationship.relationship_type_id.auto_create_reciprocal:
            relationship._create_reciprocal_relationship()
            
        # Log relationship creation
        try:
            self.env['ams.audit.log'].log_activity(
                partner_id=relationship.partner_from_id.id,
                activity_type='created',
                description=f"Created relationship: {relationship.display_name}",
                model_name=self._name,
                record_id=relationship.id
            )
        except Exception as e:
            _logger.warning(f"Failed to log relationship creation: {e}")
            
        return relationship

    def write(self, vals):
        """Override write to handle state changes and reciprocal updates"""
        # Track state changes
        for relationship in self:
            old_state = relationship.state
            
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for relationship in self:
                if vals['state'] == 'approved' and old_state == 'pending':
                    relationship.approved_by = self.env.user.id
                    relationship.approved_date = fields.Datetime.now()
                    
                # Update reciprocal relationship state
                if relationship.reciprocal_relationship_id:
                    relationship.reciprocal_relationship_id.write({'state': vals['state']})
                    
        # Handle date or active changes for reciprocal
        if any(field in vals for field in ['date_start', 'date_end', 'active']):
            for relationship in self:
                if relationship.reciprocal_relationship_id:
                    reciprocal_vals = {}
                    if 'date_start' in vals:
                        reciprocal_vals['date_start'] = vals['date_start']
                    if 'date_end' in vals:
                        reciprocal_vals['date_end'] = vals['date_end']
                    if 'active' in vals:
                        reciprocal_vals['active'] = vals['active']
                    if reciprocal_vals:
                        relationship.reciprocal_relationship_id.write(reciprocal_vals)
                        
        return result

    def unlink(self):
        """Override unlink to handle reciprocal relationship deletion"""
        reciprocal_relationships = self.mapped('reciprocal_relationship_id').filtered(lambda r: r.id)
        
        # Log relationship deletion
        for relationship in self:
            try:
                self.env['ams.audit.log'].log_activity(
                    partner_id=relationship.partner_from_id.id,
                    activity_type='deleted',
                    description=f"Deleted relationship: {relationship.display_name}",
                    model_name=self._name,
                    record_id=relationship.id
                )
            except Exception as e:
                _logger.warning(f"Failed to log relationship deletion: {e}")
        
        result = super().unlink()
        
        # Delete reciprocal relationships
        if reciprocal_relationships:
            reciprocal_relationships.unlink()
            
        return result

    def _create_reciprocal_relationship(self):
        """Create the reciprocal relationship"""
        self.ensure_one()
        
        if self.reciprocal_relationship_id:
            return self.reciprocal_relationship_id
            
        reciprocal_type = self.relationship_type_id.get_reciprocal_type()
        if not reciprocal_type:
            return False
            
        # Check if reciprocal already exists
        existing_reciprocal = self.search([
            ('partner_from_id', '=', self.partner_to_id.id),
            ('partner_to_id', '=', self.partner_from_id.id),
            ('relationship_type_id', '=', reciprocal_type.id),
            ('active', '=', True)
        ], limit=1)
        
        if existing_reciprocal:
            self.reciprocal_relationship_id = existing_reciprocal.id
            existing_reciprocal.reciprocal_relationship_id = self.id
            return existing_reciprocal
            
        # Create new reciprocal relationship
        reciprocal_vals = {
            'partner_from_id': self.partner_to_id.id,
            'partner_to_id': self.partner_from_id.id,
            'relationship_type_id': reciprocal_type.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'active': self.active,
            'state': self.state,
            'notes': self.notes,
            'reciprocal_relationship_id': self.id
        }
        
        reciprocal = self.with_context(skip_reciprocal=True).create(reciprocal_vals)
        self.reciprocal_relationship_id = reciprocal.id
        
        return reciprocal

    def action_approve(self):
        """Approve pending relationships"""
        for relationship in self:
            if relationship.state == 'pending':
                relationship.write({
                    'state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now()
                })
        return True

    def action_activate(self):
        """Activate approved relationships"""
        for relationship in self:
            if relationship.state in ['draft', 'approved']:
                relationship.state = 'active'
        return True

    def action_end(self):
        """End active relationships"""
        for relationship in self:
            if relationship.state == 'active':
                relationship.write({
                    'state': 'ended',
                    'date_end': fields.Date.today(),
                    'active': False
                })
        return True

    def action_cancel(self):
        """Cancel relationships"""
        for relationship in self:
            if relationship.state not in ['ended', 'cancelled']:
                relationship.write({
                    'state': 'cancelled',
                    'active': False
                })
        return True

    def action_view_reciprocal(self):
        """View the reciprocal relationship"""
        self.ensure_one()
        if not self.reciprocal_relationship_id:
            raise UserError(_("This relationship does not have a reciprocal relationship."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reciprocal Relationship'),
            'res_model': 'ams.partner.relationship',
            'view_mode': 'form',
            'res_id': self.reciprocal_relationship_id.id,
            'target': 'current'
        }

    @api.model
    def get_partner_relationships(self, partner_id, relationship_type_code=None, active_only=True):
        """
        Get relationships for a partner
        
        Args:
            partner_id: ID of the partner
            relationship_type_code: Optional relationship type code to filter
            active_only: Whether to return only active relationships
            
        Returns:
            recordset of relationships
        """
        domain = [
            '|',
            ('partner_from_id', '=', partner_id),
            ('partner_to_id', '=', partner_id)
        ]
        
        if active_only:
            domain.extend([('active', '=', True), ('is_current', '=', True)])
            
        if relationship_type_code:
            domain.append(('relationship_type_id.code', '=', relationship_type_code))
            
        return self.search(domain)

    @api.model
    def get_related_partners(self, partner_id, relationship_type_code=None, direction='both'):
        """
        Get partners related to a given partner
        
        Args:
            partner_id: ID of the partner
            relationship_type_code: Optional relationship type code to filter
            direction: 'from', 'to', or 'both'
            
        Returns:
            recordset of related partners
        """
        domain = []
        
        if direction in ['from', 'both']:
            domain.append(('partner_from_id', '=', partner_id))
        if direction in ['to', 'both']:
            if domain:
                domain = ['|'] + domain
            domain.append(('partner_to_id', '=', partner_id))
            
        domain.extend([('active', '=', True), ('is_current', '=', True)])
        
        if relationship_type_code:
            domain.append(('relationship_type_id.code', '=', relationship_type_code))
            
        relationships = self.search(domain)
        
        # Get the related partners
        related_partners = self.env['res.partner']
        for rel in relationships:
            if rel.partner_from_id.id == partner_id:
                related_partners |= rel.partner_to_id
            else:
                related_partners |= rel.partner_from_id
                
        return related_partners

    @api.model
    def create_relationship(self, partner_from_id, partner_to_id, relationship_type_code, **kwargs):
        """
        Convenience method to create a relationship
        
        Args:
            partner_from_id: ID of the from partner
            partner_to_id: ID of the to partner
            relationship_type_code: Code of the relationship type
            **kwargs: Additional relationship data
            
        Returns:
            created relationship record
        """
        rel_type = self.env['ams.relationship.type'].search([
            ('code', '=', relationship_type_code),
            ('active', '=', True)
        ], limit=1)
        
        if not rel_type:
            raise UserError(_("Relationship type '%s' not found.") % relationship_type_code)
            
        vals = {
            'partner_from_id': partner_from_id,
            'partner_to_id': partner_to_id,
            'relationship_type_id': rel_type.id,
        }
        vals.update(kwargs)
        
        return self.create(vals)