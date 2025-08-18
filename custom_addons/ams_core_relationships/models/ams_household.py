# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AmsHousehold(models.Model):
    _name = 'ams.household'
    _description = 'Household Management'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string='Household Name',
        required=True,
        help="Name of the household (e.g., 'Smith Family', 'Johnson Household')"
    )
    household_id = fields.Char(
        string='Household ID',
        copy=False,
        help="Unique identifier for this household"
    )
    description = fields.Text(
        string='Description',
        help="Additional description about this household"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Whether this household is currently active"
    )

    # Household composition
    member_ids = fields.One2many(
        'res.partner',
        'household_id',
        string='Household Members'
    )
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        store=True
    )
    adult_count = fields.Integer(
        string='Adult Count',
        compute='_compute_member_counts',
        store=True
    )
    child_count = fields.Integer(
        string='Child Count',
        compute='_compute_member_counts',
        store=True
    )

    # Primary contact and address
    primary_contact_id = fields.Many2one(
        'res.partner',
        string='Primary Contact',
        domain="[('household_id', '=', id), ('is_company', '=', False)]",
        help="Primary contact person for this household"
    )
    billing_contact_id = fields.Many2one(
        'res.partner',
        string='Billing Contact',
        domain="[('household_id', '=', id), ('is_company', '=', False)]",
        help="Contact responsible for billing matters"
    )

    # Address information (computed from primary contact)
    street = fields.Char(
        string='Street',
        compute='_compute_address',
        store=True
    )
    street2 = fields.Char(
        string='Street2',
        compute='_compute_address',
        store=True
    )
    city = fields.Char(
        string='City',
        compute='_compute_address',
        store=True
    )
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        compute='_compute_address',
        store=True
    )
    zip = fields.Char(
        string='Zip',
        compute='_compute_address',
        store=True
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        compute='_compute_address',
        store=True
    )

    # Communication preferences
    email = fields.Char(
        string='Email',
        compute='_compute_contact_info',
        store=True
    )
    phone = fields.Char(
        string='Phone',
        compute='_compute_contact_info',
        store=True
    )
    mobile = fields.Char(
        string='Mobile',
        compute='_compute_contact_info',
        store=True
    )

    # Household settings
    consolidated_billing = fields.Boolean(
        string='Consolidated Billing',
        default=True,
        help="Send one consolidated bill for all household members"
    )
    consolidated_communications = fields.Boolean(
        string='Consolidated Communications',
        default=True,
        help="Send communications to primary contact only"
    )
    privacy_level = fields.Selection([
        ('public', 'Public'),
        ('members', 'Members Only'),
        ('private', 'Private')
    ], string='Privacy Level', default='members',
    help="Who can see this household information")

    # Income and demographic information (optional)
    household_income_range = fields.Selection([
        ('under_25k', 'Under $25,000'),
        ('25k_50k', '$25,000 - $50,000'),
        ('50k_75k', '$50,000 - $75,000'),
        ('75k_100k', '$75,000 - $100,000'),
        ('100k_150k', '$100,000 - $150,000'),
        ('150k_plus', 'Over $150,000'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], string='Household Income Range')

    # Dates
    date_created = fields.Date(
        string='Date Created',
        default=fields.Date.today,
        help="When this household was created"
    )
    date_dissolved = fields.Date(
        string='Date Dissolved',
        help="When this household was dissolved"
    )

    # Computed fields for member relationships
    has_spouse_relationship = fields.Boolean(
        string='Has Spouse Relationship',
        compute='_compute_relationship_info',
        help="True if household has spouse/partner relationships"
    )
    has_parent_child_relationship = fields.Boolean(
        string='Has Parent-Child Relationship',
        compute='_compute_relationship_info',
        help="True if household has parent-child relationships"
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        """Compute total number of household members"""
        for household in self:
            household.member_count = len(household.member_ids.filtered('active'))

    @api.depends('member_ids', 'member_ids.birthdate_date')
    def _compute_member_counts(self):
        """Compute adult and child counts"""
        for household in self:
            active_members = household.member_ids.filtered('active')
            today = fields.Date.today()
            
            adult_count = 0
            child_count = 0
            
            for member in active_members:
                if member.birthdate_date:
                    age = (today - member.birthdate_date).days / 365.25
                    if age >= 18:
                        adult_count += 1
                    else:
                        child_count += 1
                else:
                    # Assume adult if no birthdate
                    adult_count += 1
                    
            household.adult_count = adult_count
            household.child_count = child_count

    @api.depends('primary_contact_id', 'primary_contact_id.street', 'primary_contact_id.street2',
                 'primary_contact_id.city', 'primary_contact_id.state_id', 'primary_contact_id.zip',
                 'primary_contact_id.country_id')
    def _compute_address(self):
        """Compute address from primary contact"""
        for household in self:
            if household.primary_contact_id:
                household.street = household.primary_contact_id.street
                household.street2 = household.primary_contact_id.street2
                household.city = household.primary_contact_id.city
                household.state_id = household.primary_contact_id.state_id
                household.zip = household.primary_contact_id.zip
                household.country_id = household.primary_contact_id.country_id
            else:
                household.street = False
                household.street2 = False
                household.city = False
                household.state_id = False
                household.zip = False
                household.country_id = False

    @api.depends('primary_contact_id', 'primary_contact_id.email', 'primary_contact_id.phone',
                 'primary_contact_id.mobile')
    def _compute_contact_info(self):
        """Compute contact information from primary contact"""
        for household in self:
            if household.primary_contact_id:
                household.email = household.primary_contact_id.email
                household.phone = household.primary_contact_id.phone
                household.mobile = household.primary_contact_id.mobile
            else:
                household.email = False
                household.phone = False
                household.mobile = False

    @api.depends('member_ids')
    def _compute_relationship_info(self):
        """Compute relationship information for household"""
        for household in self:
            member_ids = household.member_ids.ids
            
            # Check for spouse relationships
            spouse_rels = self.env['ams.partner.relationship'].search([
                ('partner_from_id', 'in', member_ids),
                ('partner_to_id', 'in', member_ids),
                ('relationship_type_id.code', '=', 'SPOUSE'),
                ('active', '=', True),
                ('is_current', '=', True)
            ])
            household.has_spouse_relationship = bool(spouse_rels)
            
            # Check for parent-child relationships
            parent_child_rels = self.env['ams.partner.relationship'].search([
                ('partner_from_id', 'in', member_ids),
                ('partner_to_id', 'in', member_ids),
                ('relationship_type_id.code', 'in', ['PARENT', 'CHILD']),
                ('active', '=', True),
                ('is_current', '=', True)
            ])
            household.has_parent_child_relationship = bool(parent_child_rels)

    @api.model
    def create(self, vals):
        """Override create to auto-generate household ID"""
        if not vals.get('household_id'):
            vals['household_id'] = self._generate_household_id()
            
        household = super().create(vals)
        
        # Log household creation
        try:
            self.env['ams.audit.log'].log_activity(
                activity_type='created',
                description=f"Created household: {household.name}",
                model_name=self._name,
                record_id=household.id
            )
        except Exception as e:
            _logger.warning(f"Failed to log household creation: {e}")
            
        return household

    @api.model
    def _generate_household_id(self):
        """Generate unique household ID"""
        try:
            return self.env['ir.sequence'].next_by_code('ams.household.id') or 'HH-ERROR'
        except Exception as e:
            _logger.error(f"Error generating household ID: {e}")
            return f"HH{self.env['ams.household'].search_count([]) + 1:05d}"

    @api.constrains('primary_contact_id')
    def _check_primary_contact_in_household(self):
        """Ensure primary contact is a member of the household"""
        for household in self:
            if household.primary_contact_id and household.primary_contact_id not in household.member_ids:
                raise ValidationError(
                    _("Primary contact must be a member of the household.")
                )

    @api.constrains('billing_contact_id')
    def _check_billing_contact_in_household(self):
        """Ensure billing contact is a member of the household"""
        for household in self:
            if household.billing_contact_id and household.billing_contact_id not in household.member_ids:
                raise ValidationError(
                    _("Billing contact must be a member of the household.")
                )

    def action_add_member(self):
        """Action to add a member to the household"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Household Member'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_household_id': self.id,
                'default_is_company': False
            }
        }

    def action_remove_member(self):
        """Action to remove a member from the household"""
        self.ensure_one()
        if not self.member_ids:
            raise UserError(_("This household has no members to remove."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Remove Household Member'),
            'res_model': 'ams.household.member.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_household_id': self.id}
        }

    def action_set_primary_contact(self):
        """Action to set primary contact"""
        self.ensure_one()
        if not self.member_ids:
            raise UserError(_("This household has no members."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Set Primary Contact'),
            'res_model': 'ams.household.primary.contact.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_household_id': self.id}
        }

    def action_dissolve_household(self):
        """Dissolve the household"""
        self.ensure_one()
        
        # Remove household from all members
        self.member_ids.write({'household_id': False})
        
        # Mark as dissolved
        self.write({
            'active': False,
            'date_dissolved': fields.Date.today()
        })
        
        # Log dissolution
        try:
            self.env['ams.audit.log'].log_activity(
                activity_type='updated',
                description=f"Dissolved household: {self.name}",
                model_name=self._name,
                record_id=self.id
            )
        except Exception as e:
            _logger.warning(f"Failed to log household dissolution: {e}")
            
        return True

    def action_merge_households(self):
        """Action to merge households"""
        if len(self) < 2:
            raise UserError(_("Please select at least 2 households to merge."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Merge Households'),
            'res_model': 'ams.household.merge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_household_ids': [(6, 0, self.ids)]}
        }

    def action_view_relationships(self):
        """View relationships within the household"""
        self.ensure_one()
        member_ids = self.member_ids.ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Household Relationships'),
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form',
            'domain': [
                ('partner_from_id', 'in', member_ids),
                ('partner_to_id', 'in', member_ids),
                ('active', '=', True)
            ],
            'context': {}
        }

    @api.model
    def create_household_from_relationship(self, relationship):
        """
        Create a household from a relationship (e.g., spouse relationship)
        
        Args:
            relationship: ams.partner.relationship record
            
        Returns:
            created household record
        """
        if relationship.relationship_type_id.code == 'SPOUSE':
            # Create household for spouse relationship
            household_name = f"{relationship.partner_from_id.name} & {relationship.partner_to_id.name} Household"
        else:
            # Create household with generic name
            household_name = f"{relationship.partner_from_id.name} Household"
            
        household = self.create({
            'name': household_name,
            'primary_contact_id': relationship.partner_from_id.id
        })
        
        # Add both partners to household
        relationship.partner_from_id.household_id = household.id
        relationship.partner_to_id.household_id = household.id
        
        return household

    @api.model
    def auto_create_households(self):
        """
        Automatically create households based on relationships
        This can be run as a scheduled action
        """
        # Find spouse relationships without households
        spouse_relationships = self.env['ams.partner.relationship'].search([
            ('relationship_type_id.code', '=', 'SPOUSE'),
            ('active', '=', True),
            ('is_current', '=', True)
        ])
        
        created_households = []
        for rel in spouse_relationships:
            # Check if either partner already has a household
            if not rel.partner_from_id.household_id and not rel.partner_to_id.household_id:
                household = self.create_household_from_relationship(rel)
                created_households.append(household)
                
        return created_households

    @api.model
    def get_household_statistics(self):
        """Get household statistics"""
        stats = {}
        
        all_households = self.search([('active', '=', True)])
        stats['total_households'] = len(all_households)
        stats['avg_household_size'] = sum(h.member_count for h in all_households) / len(all_households) if all_households else 0
        
        # Count by size
        stats['single_member'] = len(all_households.filtered(lambda h: h.member_count == 1))
        stats['two_member'] = len(all_households.filtered(lambda h: h.member_count == 2))
        stats['three_plus_member'] = len(all_households.filtered(lambda h: h.member_count >= 3))
        
        # Count by relationship type
        stats['with_spouse'] = len(all_households.filtered('has_spouse_relationship'))
        stats['with_children'] = len(all_households.filtered('has_parent_child_relationship'))
        
        return stats

    def get_household_members_by_role(self):
        """Get household members organized by relationship roles"""
        self.ensure_one()
        
        members_by_role = {
            'adults': self.env['res.partner'],
            'children': self.env['res.partner'],
            'spouses': self.env['res.partner'],
            'parents': self.env['res.partner'],
            'other': self.env['res.partner']
        }
        
        today = fields.Date.today()
        
        for member in self.member_ids.filtered('active'):
            # Determine if adult or child by age
            if member.birthdate_date:
                age = (today - member.birthdate_date).days / 365.25
                if age >= 18:
                    members_by_role['adults'] |= member
                else:
                    members_by_role['children'] |= member
            else:
                members_by_role['adults'] |= member
                
            # Check for specific relationships within household
            spouse_rels = self.env['ams.partner.relationship'].search([
                ('partner_from_id', '=', member.id),
                ('partner_to_id', 'in', self.member_ids.ids),
                ('relationship_type_id.code', '=', 'SPOUSE'),
                ('active', '=', True),
                ('is_current', '=', True)
            ])
            if spouse_rels:
                members_by_role['spouses'] |= member
                
            parent_rels = self.env['ams.partner.relationship'].search([
                ('partner_from_id', '=', member.id),
                ('partner_to_id', 'in', self.member_ids.ids),
                ('relationship_type_id.code', '=', 'PARENT'),
                ('active', '=', True),
                ('is_current', '=', True)
            ])
            if parent_rels:
                members_by_role['parents'] |= member
                
        return members_by_role