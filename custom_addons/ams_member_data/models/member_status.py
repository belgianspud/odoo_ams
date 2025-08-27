from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSMemberStatus(models.Model):
    """Track member lifecycle status."""
    _name = 'ams.member.status'
    _description = 'Member Status'
    _order = 'sequence, name'

    name = fields.Char(
        string='Status Name',
        required=True,
        help='Status name (Prospect, Active, Grace, Lapsed, etc.)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique identifier for this status'
    )
    
    is_active = fields.Boolean(
        string='Is Active Member',
        default=False,
        help='Members with this status count as active members'
    )
    
    sequence = fields.Integer(
        string='Lifecycle Order',
        required=True,
        default=10,
        help='Order in the membership lifecycle progression'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this status'
    )
    
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color used in kanban views (0-11)'
    )
    
    # Statistics
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count',
        help='Number of members with this status'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Member status code must be unique.'),
        ('name_unique', 'UNIQUE(name)', 'Member status name must be unique.'),
    ]

    @api.constrains('color')
    def _check_color_range(self):
        """Ensure color is within valid range for kanban."""
        for record in self:
            if record.color < 0 or record.color > 11:
                raise ValidationError(
                    "Color must be between 0 and 11 for proper kanban display."
                )

    @api.depends('code')
    def _compute_member_count(self):
        """Compute the number of members with this status."""
        for record in self:
            record.member_count = self.env['res.partner'].search_count([
                ('member_status_id', '=', record.id)
            ])

    def name_get(self):
        """Custom display name with code."""
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def get_active_statuses(self):
        """Return all statuses that count as active membership."""
        return self.search([('is_active', '=', True)])

    @api.model
    def get_default_prospect_status(self):
        """Return the default prospect status."""
        return self.search([('code', '=', 'prospect')], limit=1)

    @api.model
    def get_default_active_status(self):
        """Return the default active status.""" 
        return self.search([('code', '=', 'active')], limit=1)