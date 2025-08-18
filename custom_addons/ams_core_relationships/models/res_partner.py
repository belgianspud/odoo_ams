# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    # Household fields
    household_id = fields.Many2one(
        'ams.household',
        string='Household',
        help="Household this partner belongs to"
    )
    is_household_primary = fields.Boolean(
        string='Is Household Primary',
        compute='_compute_household_role',
        store=True,
        help="True if this partner is the primary contact for their household"
    )
    is_household_billing = fields.Boolean(
        string='Is Household Billing',
        compute='_compute_household_role',
        store=True,
        help="True if this partner is the billing contact for their household"
    )

    # Relationship fields
    relationship_from_ids = fields.One2many(
        'ams.partner.relationship',
        'partner_from_id',
        string='Relationships From'
    )
    relationship_to_ids = fields.One2many(
        'ams.partner.relationship',
        'partner_to_id',
        string='Relationships To'
    )
    relationship_count = fields.Integer(
        string='Relationship Count',
        compute='_compute_relationship_count'
    )

    # Computed relationship fields
    spouse_id = fields.Many2one(
        'res.partner',
        string='Spouse',
        compute='_compute_family_relationships',
        help="Current spouse or partner"
    )
    parent_ids = fields.Many2many(
        'res.partner',
        string='Parents',
        compute='_compute_family_relationships',
        help="Parents of this person"
    )
    child_ids = fields.Many2many(
        'res.partner',
        string='Children',
        compute='_compute_family_relationships',
        help="Children of this person"
    )
    employer_id = fields.Many2one(
        'res.partner',
        string='Employer',
        compute='_compute_employment_relationships',
        help="Current employer organization"
    )
    employee_ids = fields.Many2many(
        'res.partner',
        string='Employees',
        compute='_compute_employment_relationships',
        help="Current employees (for organizations)"
    )

    # Family information
    birthdate_date = fields.Date(
        string='Birth Date',
        help="Date of birth"
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], string='Gender')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('separated', 'Separated'),
        ('domestic_partner', 'Domestic Partner')
    ], string='Marital Status')

    # Emergency contact information
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name'
    )
    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone'
    )
    emergency_contact_relationship = fields.Char(
        string='Emergency Contact Relationship'
    )

    @api.depends('household_id', 'household_id.primary_contact_id', 'household_id.billing_contact_id')
    def _compute_household_role(self):
        """Compute household role flags"""
        for partner in self:
            if partner.household_id:
                partner.is_household_primary = (partner.household_id.primary_contact_id == partner)
                partner.is_household_billing = (partner.household_id.billing_contact_id == partner)
            else:
                partner.is_household_primary = False
                partner.is_household_billing = False

    @api.depends('relationship_from_ids', 'relationship_to_ids')
    def _compute_relationship_count(self):
        """Compute total number of relationships"""
        for partner in self:
            active_from = partner.relationship_from_ids.filtered(lambda r: r.active and r.is_current)
            active_to = partner.relationship_to_ids.filtered(lambda r: r.active and r.is_current)
            partner.relationship_count = len(active_from) + len(active_to)

    @api.depends('relationship_from_ids', 'relationship_to_ids')
    def _compute_family_relationships(self):
        """Compute family relationship fields"""
        for partner in self:
            # Get current active relationships
            current_relationships = (partner.relationship_from_ids + partner.relationship_to_ids).filtered(
                lambda r: r.active and r.is_current
            )
            
            # Find spouse
            spouse_rel = current_relationships.filtered(lambda r: r.relationship_type_id.code == 'SPOUSE')
            if spouse_rel:
                if spouse_rel[0].partner_from_id == partner:
                    partner.spouse_id = spouse_rel[0].partner_to_id
                else:
                    partner.spouse_id = spouse_rel[0].partner_from_id
            else:
                partner.spouse_id = False
                
            # Find parents
            parent_rels = current_relationships.filtered(
                lambda r: r.relationship_type_id.code == 'PARENT' and r.partner_from_id == partner
            )
            partner.parent_ids = parent_rels.mapped('partner_to_id')
            
            # Find children
            child_rels = current_relationships.filtered(
                lambda r: r.relationship_type_id.code == 'CHILD' and r.partner_from_id == partner
            )
            partner.child_ids = child_rels.mapped('partner_to_id')

    @api.depends('relationship_from_ids', 'relationship_to_ids')
    def _compute_employment_relationships(self):
        """Compute employment relationship fields"""
        for partner in self:
            current_relationships = (partner.relationship_from_ids + partner.relationship_to_ids).filtered(
                lambda r: r.active and r.is_current
            )
            
            if not partner.is_company:
                # For individuals, find employer
                employer_rel = current_relationships.filtered(
                    lambda r: r.relationship_type_id.code == 'EMPLOYEE' and r.partner_from_id == partner
                )
                partner.employer_id = employer_rel[0].partner_to_id if employer_rel else False
                partner.employee_ids = False
            else:
                # For companies, find employees
                employee_rels = current_relationships.filtered(
                    lambda r: r.relationship_type_id.code == 'EMPLOYEE' and r.partner_to_id == partner
                )
                partner.employee_ids = employee_rels.mapped('partner_from_id')
                partner.employer_id = False

    def write(self, vals):
        """Override write to handle household changes"""
        # Track household changes for audit
        old_households = {partner.id: partner.household_id for partner in self}
        
        result = super().write(vals)
        
        # Log household changes
        if 'household_id' in vals:
            for partner in self:
                old_household = old_households.get(partner.id)
                new_household = partner.household_id
                
                if old_household != new_household:
                    try:
                        if new_household:
                            description = f"Added to household: {new_household.name}"
                        else:
                            description = f"Removed from household: {old_household.name if old_household else 'Unknown'}"
                            
                        self.env['ams.audit.log'].log_activity(
                            partner_id=partner.id,
                            activity_type='updated',
                            description=description,
                            model_name='res.partner',
                            record_id=partner.id,
                            field_name='household_id',
                            old_value=old_household.name if old_household else '',
                            new_value=new_household.name if new_household else ''
                        )
                    except Exception as e:
                        _logger.warning(f"Failed to log household change: {e}")
        
        return result

    def action_view_relationships(self):
        """Action to view all relationships for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Relationships for %s') % self.name,
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form',
            'domain': [
                '|',
                ('partner_from_id', '=', self.id),
                ('partner_to_id', '=', self.id)
            ],
            'context': {
                'default_partner_from_id': self.id,
                'search_default_active': 1
            }
        }

    def action_create_relationship(self):
        """Action to create a new relationship"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Relationship'),
            'res_model': 'ams.partner.relationship',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_from_id': self.id
            }
        }

    def action_view_household(self):
        """Action to view household details"""
        self.ensure_one()
        if not self.household_id:
            raise ValidationError(_("This partner is not part of any household."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Household Details'),
            'res_model': 'ams.household',
            'view_mode': 'form',
            'res_id': self.household_id.id,
            'target': 'current'
        }

    def action_create_household(self):
        """Action to create a new household with this partner"""
        self.ensure_one()
        
        household_name = f"{self.name} Household"
        household = self.env['ams.household'].create({
            'name': household_name,
            'primary_contact_id': self.id
        })
        
        self.household_id = household.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Household Details'),
            'res_model': 'ams.household',
            'view_mode': 'form',
            'res_id': household.id,
            'target': 'current'
        }

    def action_add_to_household(self):
        """Action to add this partner to an existing household"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add to Household'),
            'res_model': 'ams.household.add.member.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id
            }
        }

    def action_remove_from_household(self):
        """Remove this partner from their household"""
        self.ensure_one()
        if not self.household_id:
            raise ValidationError(_("This partner is not part of any household."))
            
        household_name = self.household_id.name
        self.household_id = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Partner removed from household: %s') % household_name,
                'type': 'success'
            }
        }

    def get_relationships_by_type(self, relationship_type_code, direction='both'):
        """
        Get relationships of a specific type for this partner
        
        Args:
            relationship_type_code: Code of the relationship type
            direction: 'from', 'to', or 'both'
            
        Returns:
            recordset of relationships
        """
        self.ensure_one()
        
        domain = [
            ('relationship_type_id.code', '=', relationship_type_code),
            ('active', '=', True),
            ('is_current', '=', True)
        ]
        
        if direction in ['from', 'both']:
            from_domain = domain + [('partner_from_id', '=', self.id)]
        if direction in ['to', 'both']:
            to_domain = domain + [('partner_to_id', '=', self.id)]
            
        if direction == 'from':
            return self.env['ams.partner.relationship'].search(from_domain)
        elif direction == 'to':
            return self.env['ams.partner.relationship'].search(to_domain)
        else:  # both
            from_rels = self.env['ams.partner.relationship'].search(from_domain)
            to_rels = self.env['ams.partner.relationship'].search(to_domain)
            return from_rels | to_rels

    def get_related_partners(self, relationship_type_code=None, direction='both'):
        """
        Get partners related to this partner
        
        Args:
            relationship_type_code: Optional relationship type code to filter
            direction: 'from', 'to', or 'both'
            
        Returns:
            recordset of related partners
        """
        self.ensure_one()
        
        domain = [
            ('active', '=', True),
            ('is_current', '=', True)
        ]
        
        if relationship_type_code:
            domain.append(('relationship_type_id.code', '=', relationship_type_code))
            
        if direction in ['from', 'both']:
            from_domain = domain + [('partner_from_id', '=', self.id)]
        if direction in ['to', 'both']:
            to_domain = domain + [('partner_to_id', '=', self.id)]
            
        relationships = self.env['ams.partner.relationship']
        if direction == 'from':
            relationships = self.env['ams.partner.relationship'].search(from_domain)
            return relationships.mapped('partner_to_id')
        elif direction == 'to':
            relationships = self.env['ams.partner.relationship'].search(to_domain)
            return relationships.mapped('partner_from_id')
        else:  # both
            from_rels = self.env['ams.partner.relationship'].search(from_domain)
            to_rels = self.env['ams.partner.relationship'].search(to_domain)
            return from_rels.mapped('partner_to_id') | to_rels.mapped('partner_from_id')

    def create_relationship_to(self, partner_to, relationship_type_code, **kwargs):
        """
        Create a relationship from this partner to another partner
        
        Args:
            partner_to: Target partner (ID or record)
            relationship_type_code: Code of the relationship type
            **kwargs: Additional relationship data
            
        Returns:
            created relationship record
        """
        self.ensure_one()
        
        if isinstance(partner_to, int):
            partner_to_id = partner_to
        else:
            partner_to_id = partner_to.id
            
        return self.env['ams.partner.relationship'].create_relationship(
            self.id, partner_to_id, relationship_type_code, **kwargs
        )

    def get_household_members(self, exclude_self=False):
        """
        Get other members of this partner's household
        
        Args:
            exclude_self: Whether to exclude this partner from results
            
        Returns:
            recordset of household members
        """
        self.ensure_one()
        
        if not self.household_id:
            return self.env['res.partner']
            
        members = self.household_id.member_ids.filtered('active')
        
        if exclude_self:
            members = members - self
            
        return members

    def get_family_tree(self, max_depth=3):
        """
        Get family tree for this partner
        
        Args:
            max_depth: Maximum depth to traverse
            
        Returns:
            dictionary with family tree structure
        """
        self.ensure_one()
        
        def _get_family_level(partner, current_depth, visited):
            if current_depth > max_depth or partner.id in visited:
                return {}
                
            visited.add(partner.id)
            
            family_data = {
                'partner': partner,
                'spouse': partner.spouse_id,
                'parents': [],
                'children': []
            }
            
            # Get parents
            for parent in partner.parent_ids:
                if parent.id not in visited:
                    family_data['parents'].append(_get_family_level(parent, current_depth + 1, visited))
                    
            # Get children
            for child in partner.child_ids:
                if child.id not in visited:
                    family_data['children'].append(_get_family_level(child, current_depth + 1, visited))
                    
            return family_data
            
        return _get_family_level(self, 0, set())

    @api.model
    def merge_partner_relationships(self, partner_to_keep, partners_to_merge):
        """
        Merge relationships when merging partners
        
        Args:
            partner_to_keep: Partner record to keep
            partners_to_merge: Partner records to merge into the kept partner
        """
        # Update all relationships pointing to merged partners
        for partner in partners_to_merge:
            # Update relationships where merged partner is 'from'
            partner.relationship_from_ids.write({'partner_from_id': partner_to_keep.id})
            
            # Update relationships where merged partner is 'to'
            partner.relationship_to_ids.write({'partner_to_id': partner_to_keep.id})
            
            # Update household membership
            if partner.household_id and not partner_to_keep.household_id:
                partner_to_keep.household_id = partner.household_id
                
        # Remove duplicate relationships that may have been created
        all_relationships = partner_to_keep.relationship_from_ids | partner_to_keep.relationship_to_ids
        for rel in all_relationships:
            duplicates = all_relationships.filtered(
                lambda r: r.id != rel.id and
                r.partner_from_id == rel.partner_from_id and
                r.partner_to_id == rel.partner_to_id and
                r.relationship_type_id == rel.relationship_type_id
            )
            if duplicates:
                # Keep the most recent one
                duplicates[:-1].unlink()

    def get_age(self):
        """Get age of the partner in years"""
        self.ensure_one()
        if not self.birthdate_date:
            return None
            
        today = fields.Date.today()
        return int((today - self.birthdate_date).days / 365.25)

    def is_adult(self):
        """Check if partner is an adult (18+ years old)"""
        age = self.get_age()
        return age is None or age >= 18  # Assume adult if no birthdate

    def get_emergency_contact_info(self):
        """Get emergency contact information"""
        self.ensure_one()
        
        # First try explicit emergency contact fields
        if self.emergency_contact_name:
            return {
                'name': self.emergency_contact_name,
                'phone': self.emergency_contact_phone,
                'relationship': self.emergency_contact_relationship
            }
            
        # Fall back to spouse if available
        if self.spouse_id:
            return {
                'name': self.spouse_id.name,
                'phone': self.spouse_id.phone or self.spouse_id.mobile,
                'relationship': 'Spouse'
            }
            
        # Fall back to parents if available
        if self.parent_ids:
            parent = self.parent_ids[0]
            return {
                'name': parent.name,
                'phone': parent.phone or parent.mobile,
                'relationship': 'Parent'
            }
            
        return None