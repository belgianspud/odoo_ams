# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class PartnerRelationship(models.Model):
    _name = 'ams.partner.relationship'
    _description = 'Partner Relationships'
    _rec_name = 'display_name'
    _order = 'partner_a_id, relationship_type_id, start_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ===== CORE RELATIONSHIP FIELDS =====
    partner_a_id = fields.Many2one(
        'res.partner',
        string='Partner A',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help="First partner in the relationship"
    )

    partner_b_id = fields.Many2one(
        'res.partner',
        string='Partner B',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help="Second partner in the relationship"
    )

    relationship_type_id = fields.Many2one(
        'ams.relationship.type',
        string='Relationship Type',
        required=True,
        tracking=True,
        help="Type of relationship between the partners"
    )

    # ===== BIDIRECTIONAL FIELDS =====
    inverse_relationship_id = fields.Many2one(
        'ams.partner.relationship',
        string='Inverse Relationship',
        help="The inverse relationship record (automatically created)"
    )

    is_inverse = fields.Boolean(
        string='Is Inverse',
        default=False,
        help="True if this is an automatically created inverse relationship"
    )

    # ===== TEMPORAL FIELDS =====
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        tracking=True,
        help="When this relationship started"
    )

    end_date = fields.Date(
        string='End Date',
        tracking=True,
        help="When this relationship ended (blank if current)"
    )

    is_active = fields.Boolean(
        string='Active',
        compute='_compute_is_active',
        store=True,
        help="Whether this relationship is currently active"
    )

    # ===== RELATIONSHIP DETAILS =====
    description = fields.Text(
        string='Description',
        help="Additional details about this relationship"
    )

    notes = fields.Text(
        string='Notes',
        help="Internal notes about this relationship"
    )

    # ===== CONTACT INFORMATION =====
    contact_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('rarely', 'Rarely'),
        ('never', 'Never'),
    ], string='Contact Frequency', help="How often these partners interact")

    primary_contact = fields.Boolean(
        string='Primary Contact',
        default=False,
        help="Is this the primary relationship of this type?"
    )

    emergency_contact = fields.Boolean(
        string='Emergency Contact',
        default=False,
        help="Can this person be contacted in emergencies?"
    )

    # ===== PERMISSIONS =====
    can_access_info = fields.Boolean(
        string='Can Access Info',
        default=False,
        help="Can Partner B access Partner A's information?"
    )

    can_make_decisions = fields.Boolean(
        string='Can Make Decisions',
        default=False,
        help="Can Partner B make decisions for Partner A?"
    )

    financial_responsibility = fields.Boolean(
        string='Financial Responsibility',
        default=False,
        help="Does Partner B have financial responsibility for Partner A?"
    )

    # ===== COMPUTED FIELDS =====
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help="Human-readable relationship description"
    )

    relationship_strength = fields.Selection([
        ('weak', 'Weak'),
        ('moderate', 'Moderate'),
        ('strong', 'Strong'),
        ('very_strong', 'Very Strong'),
    ], string='Relationship Strength', 
       compute='_compute_relationship_strength',
       help="Computed strength based on interaction frequency and duration")

    duration_days = fields.Integer(
        string='Duration (Days)',
        compute='_compute_duration',
        help="Number of days this relationship has lasted"
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

    @api.depends('end_date')
    def _compute_is_active(self):
        """Compute if relationship is currently active"""
        today = fields.Date.today()
        for relationship in self:
            relationship.is_active = not relationship.end_date or relationship.end_date >= today

    @api.depends('partner_a_id', 'partner_b_id', 'relationship_type_id')
    def _compute_display_name(self):
        """Compute display name for relationship"""
        for relationship in self:
            if relationship.partner_a_id and relationship.partner_b_id and relationship.relationship_type_id:
                relationship.display_name = f"{relationship.partner_a_id.name} → {relationship.relationship_type_id.name} → {relationship.partner_b_id.name}"
            else:
                relationship.display_name = "New Relationship"

    @api.depends('contact_frequency', 'start_date', 'primary_contact')
    def _compute_relationship_strength(self):
        """Compute relationship strength based on various factors"""
        for relationship in self:
            score = 0
            
            # Frequency score
            frequency_scores = {
                'daily': 4,
                'weekly': 3,
                'monthly': 2,
                'quarterly': 1,
                'annually': 1,
                'rarely': 0,
                'never': 0,
            }
            score += frequency_scores.get(relationship.contact_frequency, 0)
            
            # Duration score
            if relationship.start_date:
                days = (fields.Date.today() - relationship.start_date).days
                if days > 365:
                    score += 2
                elif days > 90:
                    score += 1
            
            # Primary contact bonus
            if relationship.primary_contact:
                score += 2
            
            # Emergency contact bonus
            if relationship.emergency_contact:
                score += 1
            
            # Map score to strength
            if score >= 7:
                relationship.relationship_strength = 'very_strong'
            elif score >= 5:
                relationship.relationship_strength = 'strong'
            elif score >= 3:
                relationship.relationship_strength = 'moderate'
            else:
                relationship.relationship_strength = 'weak'

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """Compute relationship duration in days"""
        for relationship in self:
            if relationship.start_date:
                end_date = relationship.end_date or fields.Date.today()
                relationship.duration_days = (end_date - relationship.start_date).days
            else:
                relationship.duration_days = 0

    @api.model
    def create(self, vals):
        """Override create to handle bidirectional relationships"""
        relationship = super(PartnerRelationship, self).create(vals)
        
        # Create inverse relationship if type supports it and not already inverse
        if not relationship.is_inverse and relationship.relationship_type_id.is_bidirectional:
            relationship._create_inverse_relationship()
        
        # Log audit trail
        relationship._log_relationship_audit('create', 'Relationship created')
        
        return relationship

    def write(self, vals):
        """Override write to maintain bidirectional relationships"""
        result = super(PartnerRelationship, self).write(vals)
        
        for relationship in self:
            # Update inverse relationship if needed
            if relationship.inverse_relationship_id and not relationship.is_inverse:
                inverse_vals = relationship._get_inverse_values()
                relationship.inverse_relationship_id.write(inverse_vals)
            
            # Log significant changes
            if any(field in vals for field in ['end_date', 'relationship_type_id', 'partner_a_id', 'partner_b_id']):
                relationship._log_relationship_audit('write', f'Relationship updated: {list(vals.keys())}')
        
        return result

    def unlink(self):
        """Override unlink to handle inverse relationships"""
        for relationship in self:
            # Remove inverse relationship
            if relationship.inverse_relationship_id:
                relationship.inverse_relationship_id.unlink()
            
            # Log audit trail
            relationship._log_relationship_audit('unlink', 'Relationship deleted')
        
        return super(PartnerRelationship, self).unlink()

    def _create_inverse_relationship(self):
        """Create the inverse relationship"""
        self.ensure_one()
        
        if not self.relationship_type_id.inverse_type_id:
            return
        
        inverse_vals = {
            'partner_a_id': self.partner_b_id.id,
            'partner_b_id': self.partner_a_id.id,
            'relationship_type_id': self.relationship_type_id.inverse_type_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'description': self.description,
            'is_inverse': True,
            'inverse_relationship_id': self.id,
        }
        
        inverse_relationship = self.create(inverse_vals)
        self.inverse_relationship_id = inverse_relationship.id

    def _get_inverse_values(self):
        """Get values for updating inverse relationship"""
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'description': self.description,
        }

    def _log_relationship_audit(self, operation, description):
        """Log relationship changes to audit trail"""
        try:
            self.env['ams.audit.log'].sudo().create({
                'model_name': self._name,
                'record_id': self.id,
                'operation': operation,
                'description': description,
                'user_id': self.env.user.id,
                'data': str({
                    'partner_a': self.partner_a_id.name,
                    'partner_b': self.partner_b_id.name,
                    'relationship_type': self.relationship_type_id.name,
                    'is_active': self.is_active,
                }),
                'timestamp': fields.Datetime.now(),
                'related_partner_id': self.partner_a_id.id,
                'privacy_impact': True,  # Relationships are privacy-sensitive
            })
        except Exception as e:
            _logger.warning(f"Failed to log relationship audit trail: {e}")

    @api.constrains('partner_a_id', 'partner_b_id')
    def _check_different_partners(self):
        """Ensure partners are different"""
        for relationship in self:
            if relationship.partner_a_id == relationship.partner_b_id:
                raise ValidationError(_("A partner cannot have a relationship with themselves"))

    @api.constrains('start_date', 'end_date')
    def _check_date_logic(self):
        """Ensure end date is after start date"""
        for relationship in self:
            if relationship.start_date and relationship.end_date:
                if relationship.end_date < relationship.start_date:
                    raise ValidationError(_("End date must be after start date"))

    @api.constrains('partner_a_id', 'partner_b_id', 'relationship_type_id', 'start_date')
    def _check_duplicate_relationships(self):
        """Prevent duplicate active relationships of the same type"""
        for relationship in self:
            if relationship.is_active:
                existing = self.search([
                    ('partner_a_id', '=', relationship.partner_a_id.id),
                    ('partner_b_id', '=', relationship.partner_b_id.id),
                    ('relationship_type_id', '=', relationship.relationship_type_id.id),
                    ('is_active', '=', True),
                    ('id', '!=', relationship.id),
                ])
                if existing:
                    raise ValidationError(_(
                        "An active relationship of type '%s' already exists between %s and %s"
                    ) % (
                        relationship.relationship_type_id.name,
                        relationship.partner_a_id.name,
                        relationship.partner_b_id.name
                    ))

    def action_end_relationship(self):
        """Action to end the relationship"""
        self.ensure_one()
        if self.end_date:
            raise UserError(_("This relationship has already ended"))
        
        self.write({'end_date': fields.Date.today()})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Relationship ended successfully'),
                'type': 'success',
            }
        }

    def action_reactivate_relationship(self):
        """Action to reactivate an ended relationship"""
        self.ensure_one()
        if not self.end_date:
            raise UserError(_("This relationship is already active"))
        
        self.write({'end_date': False})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Relationship reactivated successfully'),
                'type': 'success',
            }
        }

    def action_view_inverse(self):
        """Action to view the inverse relationship"""
        self.ensure_one()
        if not self.inverse_relationship_id:
            raise UserError(_("This relationship does not have an inverse"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inverse Relationship'),
            'res_model': 'ams.partner.relationship',
            'view_mode': 'form',
            'res_id': self.inverse_relationship_id.id,
            'target': 'new',
        }

    def action_view_partner_relationships(self):
        """View all relationships for Partner A"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Relationships for {self.partner_a_id.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form',
            'domain': [('partner_a_id', '=', self.partner_a_id.id)],
            'context': {'default_partner_a_id': self.partner_a_id.id},
        }

    @api.model
    def get_relationship_network(self, partner_id, max_depth=2):
        """Get relationship network for a partner"""
        network = {'nodes': [], 'edges': []}
        visited = set()
        
        def add_partner_node(partner):
            if partner.id not in visited:
                network['nodes'].append({
                    'id': partner.id,
                    'name': partner.name,
                    'is_member': partner.is_member,
                    'member_id': partner.member_id,
                })
                visited.add(partner.id)
        
        def traverse_relationships(current_partner_id, depth):
            if depth > max_depth:
                return
            
            relationships = self.search([
                ('partner_a_id', '=', current_partner_id),
                ('is_active', '=', True),
            ])
            
            for rel in relationships:
                add_partner_node(rel.partner_a_id)
                add_partner_node(rel.partner_b_id)
                
                network['edges'].append({
                    'source': rel.partner_a_id.id,
                    'target': rel.partner_b_id.id,
                    'relationship_type': rel.relationship_type_id.name,
                    'strength': rel.relationship_strength,
                })
                
                if depth < max_depth:
                    traverse_relationships(rel.partner_b_id.id, depth + 1)
        
        # Start traversal
        partner = self.env['res.partner'].browse(partner_id)
        add_partner_node(partner)
        traverse_relationships(partner_id, 0)
        
        return network

    @api.model
    def cleanup_ended_relationships(self, days=365):
        """Clean up very old ended relationships"""
        cutoff_date = fields.Date.today() - timedelta(days=days)
        old_relationships = self.search([
            ('end_date', '<', cutoff_date),
            ('is_active', '=', False),
        ])
        
        count = len(old_relationships)
        if old_relationships:
            old_relationships.unlink()
            _logger.info(f"Cleaned up {count} old relationship records")
        
        return count