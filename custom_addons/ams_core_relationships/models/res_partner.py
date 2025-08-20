# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ===== RELATIONSHIP FIELDS =====
    relationship_ids = fields.One2many(
        'ams.partner.relationship',
        'partner_a_id',
        string='Relationships',
        help="All relationships where this partner is Partner A"
    )

    inverse_relationship_ids = fields.One2many(
        'ams.partner.relationship',
        'partner_b_id',
        string='Inverse Relationships',
        help="All relationships where this partner is Partner B"
    )

    # ===== COMPUTED RELATIONSHIP FIELDS =====
    all_relationships_count = fields.Integer(
        string='Total Relationships',
        compute='_compute_relationship_counts',
        help="Total number of active relationships"
    )

    active_relationships_count = fields.Integer(
        string='Active Relationships',
        compute='_compute_relationship_counts',
        help="Number of currently active relationships"
    )

    # ===== EMPLOYMENT RELATIONSHIPS =====
    current_employer_id = fields.Many2one(
        'res.partner',
        string='Current Employer',
        compute='_compute_employment_relationships',
        store=True,
        help="Current employer organization"
    )

    employees_ids = fields.Many2many(
        'res.partner',
        string='Employees',
        compute='_compute_employment_relationships',
        help="Current employees of this organization"
    )

    supervisors_ids = fields.Many2many(
        'res.partner',
        string='Supervisors',
        compute='_compute_employment_relationships',
        help="Current supervisors"
    )

    subordinates_ids = fields.Many2many(
        'res.partner',
        string='Subordinates',
        compute='_compute_employment_relationships',
        help="Current subordinates"
    )

    # ===== FAMILY RELATIONSHIPS =====
    spouse_id = fields.Many2one(
        'res.partner',
        string='Spouse',
        compute='_compute_family_relationships',
        store=True,
        help="Current spouse"
    )

    children_ids = fields.Many2many(
        'res.partner',
        string='Children',
        compute='_compute_family_relationships',
        help="Children"
    )

    parents_ids = fields.Many2many(
        'res.partner',
        string='Parents',
        compute='_compute_family_relationships',
        help="Parents"
    )

    siblings_ids = fields.Many2many(
        'res.partner',
        string='Siblings',
        compute='_compute_family_relationships',
        help="Siblings"
    )

    # ===== HOUSEHOLD RELATIONSHIPS =====
    household_members_ids = fields.Many2many(
        'res.partner',
        string='Household Members',
        compute='_compute_household_relationships',
        help="Members of the same household"
    )

    dependents_ids = fields.Many2many(
        'res.partner',
        string='Dependents',
        compute='_compute_household_relationships',
        help="Financial dependents"
    )

    guardians_ids = fields.Many2many(
        'res.partner',
        string='Guardians',
        compute='_compute_household_relationships',
        help="Legal guardians"
    )

    # ===== EMERGENCY CONTACTS =====
    primary_emergency_contact_id = fields.Many2one(
        'res.partner',
        string='Primary Emergency Contact',
        compute='_compute_emergency_contacts',
        store=True,
        help="Primary emergency contact person"
    )

    emergency_contacts_ids = fields.Many2many(
        'res.partner',
        string='Emergency Contacts',
        compute='_compute_emergency_contacts',
        help="All emergency contacts"
    )

    # ===== PROFESSIONAL RELATIONSHIPS =====
    colleagues_ids = fields.Many2many(
        'res.partner',
        string='Colleagues',
        compute='_compute_professional_relationships',
        help="Professional colleagues"
    )

    mentors_ids = fields.Many2many(
        'res.partner',
        string='Mentors',
        compute='_compute_professional_relationships',
        help="Professional mentors"
    )

    mentees_ids = fields.Many2many(
        'res.partner',
        string='Mentees',
        compute='_compute_professional_relationships',
        help="People this person mentors"
    )

    referrers_ids = fields.Many2many(
        'res.partner',
        string='Referrers',
        compute='_compute_professional_relationships',
        help="People who referred this member"
    )

    # ===== BUSINESS RELATIONSHIPS =====
    clients_ids = fields.Many2many(
        'res.partner',
        string='Clients',
        compute='_compute_business_relationships',
        help="Business clients"
    )

    vendors_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        compute='_compute_business_relationships',
        help="Business vendors"
    )

    partners_ids = fields.Many2many(
        'res.partner',
        string='Business Partners',
        compute='_compute_business_relationships',
        help="Business partners"
    )

    @api.depends('relationship_ids', 'inverse_relationship_ids')
    def _compute_relationship_counts(self):
        """Compute relationship counts"""
        for partner in self:
            all_rels = partner.relationship_ids + partner.inverse_relationship_ids
            partner.all_relationships_count = len(all_rels)
            partner.active_relationships_count = len(all_rels.filtered('is_active'))

    @api.depends('relationship_ids.is_active', 'inverse_relationship_ids.is_active')
    def _compute_employment_relationships(self):
        """Compute employment-related relationships"""
        for partner in self:
            # Get employment relationship types
            employment_types = self.env['ams.relationship.type'].search([
                ('category', '=', 'employment')
            ])
            
            # Current employer (where this partner is employed)
            employer_rel = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Employed by', 'Works for'] and
                r.relationship_type_id in employment_types
            )
            partner.current_employer_id = employer_rel[0].partner_a_id if employer_rel else False
            
            # Employees (where this partner employs others)
            employee_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Employs', 'Manages'] and
                r.relationship_type_id in employment_types
            )
            partner.employees_ids = employee_rels.mapped('partner_b_id')
            
            # Supervisors (where this partner reports to others)
            supervisor_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Supervises', 'Manages'] and
                r.relationship_type_id in employment_types
            )
            partner.supervisors_ids = supervisor_rels.mapped('partner_a_id')
            
            # Subordinates (where others report to this partner)
            subordinate_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Supervises', 'Manages'] and
                r.relationship_type_id in employment_types
            )
            partner.subordinates_ids = subordinate_rels.mapped('partner_b_id')

    @api.depends('relationship_ids.is_active', 'inverse_relationship_ids.is_active')
    def _compute_family_relationships(self):
        """Compute family relationships"""
        for partner in self:
            family_types = self.env['ams.relationship.type'].search([
                ('category', '=', 'family')
            ])
            
            # Spouse
            spouse_rel = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Spouse of', 'Married to'] and
                r.relationship_type_id in family_types
            )
            if spouse_rel:
                spouse_partner = spouse_rel[0].partner_b_id if spouse_rel[0].partner_a_id == partner else spouse_rel[0].partner_a_id
                partner.spouse_id = spouse_partner
            else:
                partner.spouse_id = False
            
            # Children (where this partner is parent)
            children_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Parent of', 'Father of', 'Mother of'] and
                r.relationship_type_id in family_types
            )
            partner.children_ids = children_rels.mapped('partner_b_id')
            
            # Parents (where this partner is child)
            parent_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Parent of', 'Father of', 'Mother of'] and
                r.relationship_type_id in family_types
            )
            partner.parents_ids = parent_rels.mapped('partner_a_id')
            
            # Siblings
            sibling_rels = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Sibling of', 'Brother of', 'Sister of'] and
                r.relationship_type_id in family_types
            )
            siblings = []
            for rel in sibling_rels:
                sibling = rel.partner_b_id if rel.partner_a_id == partner else rel.partner_a_id
                siblings.append(sibling.id)
            partner.siblings_ids = [(6, 0, siblings)]

    @api.depends('relationship_ids.is_active', 'inverse_relationship_ids.is_active')
    def _compute_household_relationships(self):
        """Compute household relationships"""
        for partner in self:
            household_types = self.env['ams.relationship.type'].search([
                ('category', '=', 'household')
            ])
            
            # Household members
            household_rels = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Household member', 'Lives with'] and
                r.relationship_type_id in household_types
            )
            household_members = []
            for rel in household_rels:
                member = rel.partner_b_id if rel.partner_a_id == partner else rel.partner_a_id
                household_members.append(member.id)
            partner.household_members_ids = [(6, 0, household_members)]
            
            # Dependents (where this partner supports others)
            dependent_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Guardian of', 'Supports'] and
                r.relationship_type_id in household_types
            )
            partner.dependents_ids = dependent_rels.mapped('partner_b_id')
            
            # Guardians (where others support this partner)
            guardian_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Guardian of', 'Supports'] and
                r.relationship_type_id in household_types
            )
            partner.guardians_ids = guardian_rels.mapped('partner_a_id')

    @api.depends('relationship_ids.emergency_contact', 'inverse_relationship_ids.emergency_contact')
    def _compute_emergency_contacts(self):
        """Compute emergency contacts"""
        for partner in self:
            # All emergency contacts (both directions)
            emergency_rels = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and r.emergency_contact
            )
            
            emergency_contacts = []
            primary_emergency = False
            
            for rel in emergency_rels:
                contact = rel.partner_b_id if rel.partner_a_id == partner else rel.partner_a_id
                emergency_contacts.append(contact.id)
                
                # Find primary emergency contact
                if rel.primary_contact and not primary_emergency:
                    primary_emergency = contact
            
            partner.emergency_contacts_ids = [(6, 0, emergency_contacts)]
            partner.primary_emergency_contact_id = primary_emergency

    @api.depends('relationship_ids.is_active', 'inverse_relationship_ids.is_active')
    def _compute_professional_relationships(self):
        """Compute professional relationships"""
        for partner in self:
            professional_types = self.env['ams.relationship.type'].search([
                ('category', '=', 'professional')
            ])
            
            # Colleagues
            colleague_rels = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Colleague of', 'Works with'] and
                r.relationship_type_id in professional_types
            )
            colleagues = []
            for rel in colleague_rels:
                colleague = rel.partner_b_id if rel.partner_a_id == partner else rel.partner_a_id
                colleagues.append(colleague.id)
            partner.colleagues_ids = [(6, 0, colleagues)]
            
            # Mentors (where this partner is mentored)
            mentor_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Mentors', 'Advises'] and
                r.relationship_type_id in professional_types
            )
            partner.mentors_ids = mentor_rels.mapped('partner_a_id')
            
            # Mentees (where this partner mentors others)
            mentee_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Mentors', 'Advises'] and
                r.relationship_type_id in professional_types
            )
            partner.mentees_ids = mentee_rels.mapped('partner_b_id')
            
            # Referrers (where others referred this partner)
            referrer_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Referred', 'Recommended'] and
                r.relationship_type_id in professional_types
            )
            partner.referrers_ids = referrer_rels.mapped('partner_a_id')

    @api.depends('relationship_ids.is_active', 'inverse_relationship_ids.is_active')
    def _compute_business_relationships(self):
        """Compute business relationships"""
        for partner in self:
            business_types = self.env['ams.relationship.type'].search([
                ('category', '=', 'business')
            ])
            
            # Clients (where this partner serves others)
            client_rels = partner.relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Serves', 'Client of'] and
                r.relationship_type_id in business_types
            )
            partner.clients_ids = client_rels.mapped('partner_b_id')
            
            # Vendors (where others serve this partner)
            vendor_rels = partner.inverse_relationship_ids.filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Serves', 'Vendor to'] and
                r.relationship_type_id in business_types
            )
            partner.vendors_ids = vendor_rels.mapped('partner_a_id')
            
            # Business partners
            partner_rels = (partner.relationship_ids + partner.inverse_relationship_ids).filtered(
                lambda r: r.is_active and 
                r.relationship_type_id.name in ['Partner with', 'Business partner'] and
                r.relationship_type_id in business_types
            )
            business_partners = []
            for rel in partner_rels:
                business_partner = rel.partner_b_id if rel.partner_a_id == partner else rel.partner_a_id
                business_partners.append(business_partner.id)
            partner.partners_ids = [(6, 0, business_partners)]

    def action_create_relationship(self):
        """Action to create a new relationship"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'New Relationship for {self.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_a_id': self.id},
        }

    def action_view_all_relationships(self):
        """Action to view all relationships for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'All Relationships for {self.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,form,kanban',
            'domain': ['|', ('partner_a_id', '=', self.id), ('partner_b_id', '=', self.id)],
            'context': {'default_partner_a_id': self.id},
        }

    def action_view_employment_chart(self):
        """Action to view employment organizational chart"""
        self.ensure_one()
        if not self.current_employer_id and not self.employees_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No employment relationships found'),
                    'type': 'warning',
                }
            }
        
        # Return network visualization or tree view
        return {
            'type': 'ir.actions.act_window',
            'name': f'Employment Network for {self.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'tree,kanban',
            'domain': [
                ('relationship_type_id.category', '=', 'employment'),
                '|', 
                ('partner_a_id', '=', self.id), 
                ('partner_b_id', '=', self.id)
            ],
        }

    def action_view_family_tree(self):
        """Action to view family relationships"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Family Tree for {self.name}',
            'res_model': 'ams.partner.relationship',
            'view_mode': 'kanban,tree',
            'domain': [
                ('relationship_type_id.category', '=', 'family'),
                '|', 
                ('partner_a_id', '=', self.id), 
                ('partner_b_id', '=', self.id)
            ],
        }

    def get_relationship_summary(self):
        """Get a summary of all relationships for this partner"""
        self.ensure_one()
        
        summary = {
            'total_relationships': self.all_relationships_count,
            'active_relationships': self.active_relationships_count,
            'employment': {
                'employer': self.current_employer_id.name if self.current_employer_id else None,
                'employees_count': len(self.employees_ids),
                'supervisors_count': len(self.supervisors_ids),
                'subordinates_count': len(self.subordinates_ids),
            },
            'family': {
                'spouse': self.spouse_id.name if self.spouse_id else None,
                'children_count': len(self.children_ids),
                'parents_count': len(self.parents_ids),
                'siblings_count': len(self.siblings_ids),
            },
            'household': {
                'household_members_count': len(self.household_members_ids),
                'dependents_count': len(self.dependents_ids),
                'guardians_count': len(self.guardians_ids),
            },
            'emergency': {
                'primary_contact': self.primary_emergency_contact_id.name if self.primary_emergency_contact_id else None,
                'emergency_contacts_count': len(self.emergency_contacts_ids),
            },
            'professional': {
                'colleagues_count': len(self.colleagues_ids),
                'mentors_count': len(self.mentors_ids),
                'mentees_count': len(self.mentees_ids),
            },
            'business': {
                'clients_count': len(self.clients_ids),
                'vendors_count': len(self.vendors_ids),
                'partners_count': len(self.partners_ids),
            },
        }
        
        return summary

    def find_relationship_path(self, target_partner_id, max_depth=3):
        """Find relationship path between this partner and another"""
        self.ensure_one()
        target_partner = self.env['res.partner'].browse(target_partner_id)
        
        if not target_partner.exists():
            return []
        
        visited = set()
        path = []
        
        def dfs(current_partner, target, current_path, depth):
            if depth > max_depth or current_partner.id in visited:
                return False
            
            visited.add(current_partner.id)
            current_path.append(current_partner)
            
            if current_partner.id == target.id:
                return True
            
            # Check all relationships
            for rel in current_partner.relationship_ids.filtered('is_active'):
                if dfs(rel.partner_b_id, target, current_path, depth + 1):
                    return True
            
            for rel in current_partner.inverse_relationship_ids.filtered('is_active'):
                if dfs(rel.partner_a_id, target, current_path, depth + 1):
                    return True
            
            current_path.pop()
            return False
        
        if dfs(self, target_partner, path, 0):
            return path
        else:
            return []