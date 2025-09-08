from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSParticipationHistory(models.Model):
    """Track participation status changes with complete audit trail."""
    _name = 'ams.participation.history'
    _description = 'Participation History'
    _order = 'change_date desc, id desc'
    _rec_name = 'display_name'

    # Status choices (must match ams.participation status field)
    STATUS_SELECTION = [
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ]

    participation_id = fields.Many2one(
        'ams.participation',
        string='Related Participation',
        required=True,
        ondelete='cascade',
        help='Participation record this history entry belongs to'
    )
    
    # Related fields for easier reporting
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='participation_id.partner_id',
        store=True,
        help='Member associated with this participation'
    )
    
    participation_type = fields.Selection(
        string='Participation Type',
        related='participation_id.participation_type',
        store=True,
        help='Type of participation'
    )
    
    old_status = fields.Selection(
        STATUS_SELECTION,
        string='Previous Status',
        required=True,
        help='Status before the change'
    )
    
    new_status = fields.Selection(
        STATUS_SELECTION,
        string='New Status',
        required=True,
        help='Status after the change'
    )
    
    change_date = fields.Datetime(
        string='Change Date',
        required=True,
        default=fields.Datetime.now,
        help='When the status change occurred'
    )
    
    changed_by = fields.Many2one(
        'res.users',
        string='Changed By',
        required=True,
        default=lambda self: self.env.user,
        help='User who made the change'
    )
    
    reason = fields.Text(
        string='Change Reason',
        help='Explanation for this status change'
    )
    
    automated = fields.Boolean(
        string='System Generated',
        default=False,
        help='Whether this change was made automatically by the system'
    )
    
    # Additional tracking fields
    effective_date = fields.Date(
        string='Effective Date',
        help='When this change takes effect (may differ from change date)'
    )
    
    reference_document = fields.Char(
        string='Reference Document',
        help='Invoice number, payment reference, or other document reference'
    )
    
    previous_values = fields.Json(
        string='Previous Field Values',
        help='JSON store of other changed field values'
    )
    
    # Display fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    status_change_description = fields.Char(
        string='Status Change',
        compute='_compute_status_change_description',
        store=True
    )

    @api.depends('participation_id', 'old_status', 'new_status', 'change_date')
    def _compute_display_name(self):
        """Compute display name for history records."""
        for record in self:
            if record.participation_id and record.old_status and record.new_status:
                partner_name = record.participation_id.partner_id.name or record.participation_id.company_id.name
                change_date = record.change_date.strftime('%Y-%m-%d %H:%M') if record.change_date else 'Unknown'
                record.display_name = f"{partner_name}: {record.old_status} → {record.new_status} ({change_date})"
            else:
                record.display_name = "History Entry"

    @api.depends('old_status', 'new_status')
    def _compute_status_change_description(self):
        """Compute human-readable status change description."""
        status_labels = dict(self.STATUS_SELECTION)
        for record in self:
            if record.old_status and record.new_status:
                old_label = status_labels.get(record.old_status, record.old_status)
                new_label = status_labels.get(record.new_status, record.new_status)
                record.status_change_description = f"{old_label} → {new_label}"
            else:
                record.status_change_description = "Status Change"

    @api.constrains('old_status', 'new_status')
    def _check_status_change(self):
        """Validate that status actually changed."""
        for record in self:
            if record.old_status == record.new_status:
                raise ValidationError(
                    "Cannot create history record: old status and new status are the same."
                )

    @api.constrains('change_date', 'effective_date')
    def _check_dates(self):
        """Validate date relationships."""
        for record in self:
            if record.effective_date and record.change_date:
                change_date_only = record.change_date.date()
                if record.effective_date < change_date_only:
                    raise ValidationError(
                        "Effective date cannot be before change date."
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set effective date if not provided."""
        for vals in vals_list:
            # Set effective date to change date if not provided
            if not vals.get('effective_date') and vals.get('change_date'):
                change_datetime = fields.Datetime.to_datetime(vals['change_date'])
                vals['effective_date'] = change_datetime.date()
        return super().create(vals_list)

    def name_get(self):
        """Custom name_get using display_name."""
        result = []
        for record in self:
            result.append((record.id, record.display_name))
        return result

    @api.model
    def create_history_entry(self, participation, old_status, new_status, reason=None, automated=False, reference_document=None):
        """Helper method to create history entries with validation."""
        if old_status == new_status:
            return False
            
        vals = {
            'participation_id': participation.id,
            'old_status': old_status,
            'new_status': new_status,
            'reason': reason,
            'automated': automated,
            'reference_document': reference_document,
        }
        
        return self.create(vals)

    def action_view_participation(self):
        """Open the related participation record."""
        self.ensure_one()
        return {
            'name': 'Participation',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'res_id': self.participation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def get_status_changes_for_period(self, date_from, date_to, participation_type=None):
        """Get status changes for a specific period, optionally filtered by type."""
        domain = [
            ('change_date', '>=', date_from),
            ('change_date', '<=', date_to),
        ]
        
        if participation_type:
            domain.append(('participation_type', '=', participation_type))
            
        return self.search(domain)

    @api.model
    def get_member_history(self, partner_id):
        """Get all history entries for a specific member."""
        return self.search([('partner_id', '=', partner_id)])

    def get_status_transition_counts(self, date_from=None, date_to=None):
        """Get counts of status transitions for analytics."""
        domain = []
        if date_from:
            domain.append(('change_date', '>=', date_from))
        if date_to:
            domain.append(('change_date', '<=', date_to))
            
        records = self.search(domain)
        transition_counts = {}
        
        for record in records:
            transition = f"{record.old_status}_to_{record.new_status}"
            transition_counts[transition] = transition_counts.get(transition, 0) + 1
            
        return transition_counts