# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AmsContactRole(models.Model):
    _name = 'ams.contact.role'
    _description = 'Contact Role Definition'
    _order = 'sequence, name'

    name = fields.Char(
        string='Role Name',
        required=True,
        help="Name of the contact role (e.g., Primary Contact, Billing Contact)"
    )
    code = fields.Char(
        string='Role Code',
        required=True,
        help="Short code for the role (e.g., PRIMARY, BILLING)"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of this contact role"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order in which roles are displayed"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to hide this role from selection"
    )
    is_primary = fields.Boolean(
        string='Is Primary Role',
        default=False,
        help="Check if this is the primary contact role (only one should be primary)"
    )
    allow_multiple = fields.Boolean(
        string='Allow Multiple',
        default=True,
        help="Allow multiple contacts to have this role for the same organization"
    )
    for_individuals = fields.Boolean(
        string='For Individuals',
        default=True,
        help="This role can be assigned to individual contacts"
    )
    for_organizations = fields.Boolean(
        string='For Organizations',
        default=True,
        help="This role can be assigned to organizations"
    )

    # Role assignment tracking
    assignment_ids = fields.One2many(
        'ams.contact.role.assignment',
        'role_id',
        string='Role Assignments'
    )
    assignment_count = fields.Integer(
        string='Assignment Count',
        compute='_compute_assignment_count'
    )

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        """Compute number of active assignments for this role"""
        for role in self:
            role.assignment_count = len(role.assignment_ids.filtered('active'))

    @api.constrains('is_primary')
    def _check_single_primary_role(self):
        """Ensure only one role is marked as primary"""
        if self.is_primary:
            other_primary = self.search([
                ('is_primary', '=', True),
                ('id', '!=', self.id)
            ], limit=1)
            if other_primary:
                raise ValidationError(
                    _("Only one contact role can be marked as primary. "
                      "Role '%s' is already set as primary.") % other_primary.name
                )

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure role codes are unique"""
        for role in self:
            if role.code:
                duplicate = self.search([
                    ('code', '=', role.code),
                    ('id', '!=', role.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Role code '%s' already exists. Role codes must be unique.") % role.code
                    )

    def name_get(self):
        """Custom name display including code"""
        result = []
        for role in self:
            if role.code:
                name = f"[{role.code}] {role.name}"
            else:
                name = role.name
            result.append((role.id, name))
        return result

    def action_view_assignments(self):
        """Action to view all assignments for this role"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Role Assignments: %s') % self.name,
            'res_model': 'ams.contact.role.assignment',
            'view_mode': 'tree,form',
            'domain': [('role_id', '=', self.id)],
            'context': {'default_role_id': self.id}
        }


class AmsContactRoleAssignment(models.Model):
    _name = 'ams.contact.role.assignment'
    _description = 'Contact Role Assignment'
    _order = 'organization_id, role_id, partner_id'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        ondelete='cascade',
        help="The contact person assigned to this role"
    )
    organization_id = fields.Many2one(
        'res.partner',
        string='Organization',
        required=True,
        domain="[('is_company', '=', True)]",
        ondelete='cascade',
        help="The organization for which this contact has the role"
    )
    role_id = fields.Many2one(
        'ams.contact.role',
        string='Role',
        required=True,
        ondelete='cascade',
        help="The role assigned to this contact"
    )
    
    # Assignment details
    date_assigned = fields.Date(
        string='Date Assigned',
        default=fields.Date.today,
        help="Date when this role was assigned"
    )
    date_end = fields.Date(
        string='End Date',
        help="Date when this role assignment ends (leave blank for ongoing)"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to deactivate this role assignment"
    )
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this role assignment"
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
        help="True if this assignment is currently active"
    )

    @api.depends('partner_id.name', 'role_id.name', 'organization_id.name')
    def _compute_display_name(self):
        """Compute display name for role assignment"""
        for assignment in self:
            if assignment.partner_id and assignment.role_id and assignment.organization_id:
                assignment.display_name = (
                    f"{assignment.partner_id.name} - {assignment.role_id.name} "
                    f"@ {assignment.organization_id.name}"
                )
            else:
                assignment.display_name = _("Role Assignment")

    @api.depends('active', 'date_assigned', 'date_end')
    def _compute_is_current(self):
        """Compute if this assignment is currently active"""
        today = fields.Date.today()
        for assignment in self:
            assignment.is_current = (
                assignment.active and
                assignment.date_assigned <= today and
                (not assignment.date_end or assignment.date_end >= today)
            )

    @api.constrains('partner_id', 'organization_id', 'role_id', 'date_assigned', 'date_end')
    def _check_assignment_validity(self):
        """Validate role assignment constraints"""
        for assignment in self:
            # Check if contact is individual when role requires it
            if assignment.role_id and not assignment.role_id.for_individuals:
                if not assignment.partner_id.is_company:
                    raise ValidationError(
                        _("Role '%s' cannot be assigned to individuals.") % assignment.role_id.name
                    )

            # Check if dates are logical
            if assignment.date_end and assignment.date_assigned:
                if assignment.date_end < assignment.date_assigned:
                    raise ValidationError(
                        _("End date cannot be before assignment date.")
                    )

            # Check for multiple assignments if role doesn't allow it
            if assignment.role_id and not assignment.role_id.allow_multiple:
                overlapping = self.search([
                    ('organization_id', '=', assignment.organization_id.id),
                    ('role_id', '=', assignment.role_id.id),
                    ('active', '=', True),
                    ('id', '!=', assignment.id),
                    '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', assignment.date_assigned)
                ])
                if overlapping:
                    raise ValidationError(
                        _("Role '%s' does not allow multiple assignments for the same organization.") 
                        % assignment.role_id.name
                    )

    @api.model
    def create(self, vals):
        """Override create to log assignment creation"""
        assignment = super().create(vals)
        try:
            self.env['ams.audit.log'].create({
                'partner_id': assignment.partner_id.id,
                'activity_type': 'role_assigned',
                'description': f"Assigned role '{assignment.role_id.name}' for organization '{assignment.organization_id.name}'",
                'user_id': self.env.user.id,
                'timestamp': fields.Datetime.now()
            })
        except Exception as e:
            _logger.warning(f"Failed to log role assignment: {e}")
        return assignment

    def write(self, vals):
        """Override write to log assignment changes"""
        if 'active' in vals and not vals['active']:
            # Log role deactivation
            for assignment in self:
                try:
                    self.env['ams.audit.log'].create({
                        'partner_id': assignment.partner_id.id,
                        'activity_type': 'role_deactivated',
                        'description': f"Deactivated role '{assignment.role_id.name}' for organization '{assignment.organization_id.name}'",
                        'user_id': self.env.user.id,
                        'timestamp': fields.Datetime.now()
                    })
                except Exception as e:
                    _logger.warning(f"Failed to log role deactivation: {e}")
        
        return super().write(vals)

    def action_deactivate(self):
        """Action to deactivate role assignment"""
        self.write({'active': False, 'date_end': fields.Date.today()})
        return True

    def action_reactivate(self):
        """Action to reactivate role assignment"""
        self.write({'active': True, 'date_end': False})
        return True

    @api.model
    def get_organization_contacts(self, organization_id, role_code=None):
        """Get contacts for an organization, optionally filtered by role"""
        domain = [
            ('organization_id', '=', organization_id),
            ('active', '=', True),
            ('is_current', '=', True)
        ]
        if role_code:
            domain.append(('role_id.code', '=', role_code))
        
        return self.search(domain)

    @api.model
    def get_primary_contact(self, organization_id):
        """Get primary contact for an organization"""
        primary_role = self.env['ams.contact.role'].search([('is_primary', '=', True)], limit=1)
        if primary_role:
            assignment = self.search([
                ('organization_id', '=', organization_id),
                ('role_id', '=', primary_role.id),
                ('active', '=', True),
                ('is_current', '=', True)
            ], limit=1)
            return assignment.partner_id if assignment else False
        return False