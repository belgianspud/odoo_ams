from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSMemberType(models.Model):
    """Define membership categories and classifications."""
    _name = 'ams.member.type'
    _description = 'Member Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Type Name',
        required=True,
        help='Member type name (Individual, Organization, Student, etc.)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique identifier for this member type'
    )
    
    is_individual = fields.Boolean(
        string='Individual Type',
        default=False,
        help='True if this type is for individual members'
    )
    
    is_organization = fields.Boolean(
        string='Organization Type', 
        default=False,
        help='True if this type is for organization members'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this member type'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive member types are hidden but preserved'
    )
    
    # Statistics
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        help='Number of members with this type'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Member type code must be unique.'),
        ('name_unique', 'UNIQUE(name)', 'Member type name must be unique.'),
    ]

    @api.constrains('is_individual', 'is_organization')
    def _check_type_flags(self):
        """Ensure exactly one type flag is set."""
        for record in self:
            if not (record.is_individual or record.is_organization):
                raise ValidationError(
                    "Member type must be either Individual or Organization type."
                )
            if record.is_individual and record.is_organization:
                raise ValidationError(
                    "Member type cannot be both Individual and Organization type."
                )

    @api.depends('code')
    def _compute_member_count(self):
        """Compute the number of members with this type."""
        for record in self:
            record.member_count = self.env['res.partner'].search_count([
                ('member_type_id', '=', record.id)
            ])

    def name_get(self):
        """Custom display name with code."""
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result