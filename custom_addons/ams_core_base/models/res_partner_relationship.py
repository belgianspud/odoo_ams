# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerRelationship(models.Model):
    """Manages relationships between partners (contacts and accounts)."""
    
    _name = 'res.partner.relationship'
    _description = 'Partner Relationship'
    _order = 'partner_id, relationship_type_id'
    _rec_name = 'display_name'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        help='The primary partner in this relationship'
    )
    
    related_partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner', 
        required=True,
        ondelete='cascade',
        help='The related partner in this relationship'
    )
    
    relationship_type_id = fields.Many2one(
        'ams.lookup',
        string='Relationship Type',
        domain="[('category', '=', 'relationship_type'), ('active', '=', True)]",
        required=True,
        help='Type of relationship between partners'
    )
    
    # Date fields for relationship lifecycle
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.context_today,
        help='When this relationship started'
    )
    
    end_date = fields.Date(
        string='End Date',
        help='When this relationship ended (leave blank if active)'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this relationship is currently active'
    )
    
    # Additional relationship details
    role_title = fields.Char(
        string='Role/Title',
        help='Specific role or title in this relationship'
    )
    
    department = fields.Char(
        string='Department',
        help='Department or division (for employment relationships)'
    )
    
    is_primary = fields.Boolean(
        string='Primary Relationship',
        default=False,
        help='Mark as primary relationship of this type'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this relationship'
    )
    
    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Human readable relationship description'
    )
    
    is_current = fields.Boolean(
        string='Current',
        compute='_compute_is_current',
        store=True,
        help='Whether this relationship is currently active based on dates'
    )
    
    # Access control fields
    created_by_user_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        help='User who created this relationship'
    )
    
    @api.depends('partner_id', 'related_partner_id', 'relationship_type_id', 'role_title')
    def _compute_display_name(self):
        """Compute human-readable display name for the relationship."""
        for record in self:
            parts = []
            
            if record.partner_id:
                parts.append(record.partner_id.name)
            
            if record.relationship_type_id:
                parts.append(record.relationship_type_id.name)
            
            if record.related_partner_id:
                parts.append(record.related_partner_id.name)
            
            if record.role_title:
                parts.append(f"({record.role_title})")
            
            record.display_name = ' - '.join(parts) if parts else 'Unnamed Relationship'
    
    @api.depends('start_date', 'end_date', 'active')
    def _compute_is_current(self):
        """Determine if relationship is currently active based on dates and active flag."""
        today = fields.Date.context_today(self)
        
        for record in self:
            if not record.active:
                record.is_current = False
                continue
            
            # Check start date
            if record.start_date and record.start_date > today:
                record.is_current = False
                continue
            
            # Check end date
            if record.end_date and record.end_date < today:
                record.is_current = False
                continue
            
            record.is_current = True
    
    @api.constrains('partner_id', 'related_partner_id')
    def _check_no_self_relationship(self):
        """Prevent partner from having relationship with itself."""
        for record in self:
            if record.partner_id.id == record.related_partner_id.id:
                raise ValidationError(_('A partner cannot have a relationship with itself.'))
    
    @api.constrains('start_date', 'end_date')
    def _check_date_consistency(self):
        """Ensure end date is after start date."""
        for record in self:
            if (record.start_date and record.end_date and 
                record.start_date > record.end_date):
                raise ValidationError(_(
                    'End date (%s) must be after start date (%s).'
                ) % (record.end_date, record.start_date))
    
    @api.constrains('is_primary', 'relationship_type_id', 'partner_id')
    def _check_single_primary_per_type(self):
        """Ensure only one primary relationship per type per partner."""
        for record in self:
            if record.is_primary:
                other_primary = self.search([
                    ('partner_id', '=', record.partner_id.id),
                    ('relationship_type_id', '=', record.relationship_type_id.id),
                    ('is_primary', '=', True),
                    ('active', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_primary:
                    raise ValidationError(_(
                        'Partner %s already has a primary %s relationship with %s.'
                    ) % (record.partner_id.name, 
                         record.relationship_type_id.name,
                         other_primary.related_partner_id.name))
    
    def create_reverse_relationship(self, reverse_type_id=None):
        """Create the reverse relationship automatically."""
        self.ensure_one()
        
        # Don't create reverse if it already exists
        existing_reverse = self.search([
            ('partner_id', '=', self.related_partner_id.id),
            ('related_partner_id', '=', self.partner_id.id),
            ('relationship_type_id', '=', reverse_type_id or self.relationship_type_id.id)
        ])
        
        if existing_reverse:
            return existing_reverse
        
        # Create reverse relationship
        reverse_vals = {
            'partner_id': self.related_partner_id.id,
            'related_partner_id': self.partner_id.id,
            'relationship_type_id': reverse_type_id or self.relationship_type_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'active': self.active,
            'notes': f'Reverse of: {self.display_name}',
        }
        
        return self.create(reverse_vals)
    
    def end_relationship(self, end_date=None):
        """End this relationship (set end date and make inactive)."""
        self.ensure_one()
        
        end_date = end_date or fields.Date.context_today(self)
        
        self.write({
            'end_date': end_date,
            'active': False
        })
        
        # Also end reverse relationship if it exists
        reverse = self.search([
            ('partner_id', '=', self.related_partner_id.id),
            ('related_partner_id', '=', self.partner_id.id),
            ('active', '=', True)
        ])
        
        if reverse:
            reverse.write({
                'end_date': end_date,
                'active': False
            })
    
    @api.model
    def get_relationships_for_partner(self, partner_id, relationship_type=None, active_only=True):
        """Get all relationships for a specific partner."""
        domain = [
            '|',
            ('partner_id', '=', partner_id),
            ('related_partner_id', '=', partner_id)
        ]
        
        if relationship_type:
            domain.append(('relationship_type_id', '=', relationship_type))
        
        if active_only:
            domain.append(('is_current', '=', True))
        
        return self.search(domain)
    
    @api.model
    def get_employees_for_organization(self, organization_id):
        """Get all employees for an organization."""
        employee_type = self.env['ams.lookup'].search([
            ('category', '=', 'relationship_type'),
            ('code', '=', 'employee')
        ], limit=1)
        
        if not employee_type:
            return self.browse([])
        
        return self.search([
            ('related_partner_id', '=', organization_id),
            ('relationship_type_id', '=', employee_type.id),
            ('is_current', '=', True)
        ])
    
    @api.model 
    def get_employer_for_contact(self, contact_id):
        """Get primary employer for a contact."""
        employee_type = self.env['ams.lookup'].search([
            ('category', '=', 'relationship_type'),
            ('code', '=', 'employee')
        ], limit=1)
        
        if not employee_type:
            return self.browse([])
        
        return self.search([
            ('partner_id', '=', contact_id),
            ('relationship_type_id', '=', employee_type.id),
            ('is_primary', '=', True),
            ('is_current', '=', True)
        ], limit=1)
    
    @api.model
    def create_employment_relationship(self, employee_id, employer_id, role_title=None, department=None):
        """Helper method to create employment relationship."""
        employee_type = self.env['ams.lookup'].search([
            ('category', '=', 'relationship_type'),
            ('code', '=', 'employee')
        ], limit=1)
        
        employer_type = self.env['ams.lookup'].search([
            ('category', '=', 'relationship_type'), 
            ('code', '=', 'employer')
        ], limit=1)
        
        if not employee_type or not employer_type:
            raise ValidationError(_(
                'Employee and Employer relationship types must be configured in lookups.'
            ))
        
        # Create employee -> employer relationship
        employee_rel = self.create({
            'partner_id': employee_id,
            'related_partner_id': employer_id,
            'relationship_type_id': employee_type.id,
            'role_title': role_title,
            'department': department,
            'is_primary': True
        })
        
        # Create reverse employer -> employee relationship
        employer_rel = self.create({
            'partner_id': employer_id,
            'related_partner_id': employee_id,
            'relationship_type_id': employer_type.id,
            'role_title': role_title,
            'department': department
        })
        
        return employee_rel, employer_rel


class ResPartner(models.Model):
    """Extend res.partner with relationship helper methods."""
    
    _inherit = 'res.partner'
    
    def get_employees(self):
        """Get all employees of this organization."""
        return self.env['res.partner.relationship'].get_employees_for_organization(self.id)
    
    def get_employer(self):
        """Get primary employer of this contact."""
        return self.env['res.partner.relationship'].get_employer_for_contact(self.id)
    
    def add_employee(self, employee_id, role_title=None, department=None):
        """Add an employee to this organization."""
        return self.env['res.partner.relationship'].create_employment_relationship(
            employee_id, self.id, role_title, department
        )