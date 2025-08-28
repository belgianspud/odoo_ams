from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSCancellationReason(models.Model):
    """Predefined cancellation reasons for participation terminations."""
    _name = 'ams.cancellation.reason'
    _description = 'Cancellation Reason'
    _order = 'sequence, name'

    name = fields.Char(
        string='Reason Name',
        required=True,
        help='Display name for cancellation reason'
    )
    
    code = fields.Char(
        string='Unique Code',
        required=True,
        help='System code for this reason (uppercase, no spaces)'
    )
    
    category = fields.Selection([
        ('voluntary', 'Voluntary'),
        ('involuntary', 'Involuntary'),
        ('administrative', 'Administrative')
    ], string='Category', required=True, default='voluntary',
       help='General category for reporting and analytics')
    
    description = fields.Text(
        string='Detailed Description',
        help='Full explanation of this cancellation reason'
    )
    
    sequence = fields.Integer(
        string='Display Order',
        default=10,
        help='Order for display in selection lists'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive reasons are hidden but preserved for historical data'
    )
    
    # Processing Rules
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='Whether this reason requires supervisor approval'
    )
    
    allows_reinstatement = fields.Boolean(
        string='Allows Reinstatement',
        default=True,
        help='Whether participation can be reinstated after this reason'
    )
    
    refund_eligible = fields.Boolean(
        string='Refund Eligible',
        default=False,
        help='Whether this reason typically qualifies for refund'
    )
    
    internal_notes = fields.Text(
        string='Internal Processing Notes',
        help='Staff guidance for handling this cancellation reason'
    )
    
    # Statistics
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        help='Number of participations cancelled with this reason'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Cancellation reason code must be unique.'),
        ('name_unique', 'UNIQUE(name)', 'Cancellation reason name must be unique.'),
    ]

    @api.constrains('code')
    def _check_code_format(self):
        """Ensure code follows naming conventions."""
        for record in self:
            if record.code:
                if not record.code.isupper():
                    raise ValidationError("Reason code must be uppercase.")
                if ' ' in record.code:
                    raise ValidationError("Reason code cannot contain spaces.")
                if not record.code.replace('_', '').isalnum():
                    raise ValidationError("Reason code can only contain letters, numbers, and underscores.")

    @api.depends('code')
    def _compute_usage_count(self):
        """Compute how many times this reason has been used."""
        for record in self:
            record.usage_count = self.env['ams.participation'].search_count([
                ('cancellation_reason_id', '=', record.id)
            ])

    def name_get(self):
        """Custom display name with category indicator."""
        result = []
        for record in self:
            if record.category:
                category_indicator = {
                    'voluntary': '●',
                    'involuntary': '▲', 
                    'administrative': '■'
                }.get(record.category, '')
                name = f"{category_indicator} {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    @api.model
    def get_reasons_by_category(self, category):
        """Return all active reasons for a specific category."""
        return self.search([
            ('category', '=', category),
            ('active', '=', True)
        ])

    @api.model
    def get_voluntary_reasons(self):
        """Return all voluntary cancellation reasons."""
        return self.get_reasons_by_category('voluntary')

    @api.model
    def get_involuntary_reasons(self):
        """Return all involuntary cancellation reasons."""
        return self.get_reasons_by_category('involuntary')

    @api.model
    def get_administrative_reasons(self):
        """Return all administrative cancellation reasons."""
        return self.get_reasons_by_category('administrative')

    def action_view_participations(self):
        """Open participations cancelled with this reason."""
        self.ensure_one()
        return {
            'name': f'Participations Cancelled: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'tree,form',
            'domain': [('cancellation_reason_id', '=', self.id)],
            'context': {'search_default_cancelled': 1},
        }