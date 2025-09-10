# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AMSParticipationHistory(models.Model):
    """History tracking for participation status changes and important events."""
    
    _name = 'ams.participation.history'
    _inherit = ['mail.thread']
    _description = 'AMS Participation History'
    _order = 'change_date desc, id desc'
    _rec_name = 'change_summary'

    # ========================================================================
    # CORE FIELDS
    # ========================================================================

    participation_id = fields.Many2one(
        'ams.participation',
        string="Participation",
        required=True,
        ondelete='cascade',
        index=True,
        help="Participation record this history entry relates to"
    )

    # ========================================================================
    # STATUS CHANGE TRACKING
    # ========================================================================

    old_status = fields.Selection([
        ('', 'None'),
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string="Previous Status", required=True,
       help="Status before the change")

    new_status = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string="New Status", required=True,
       help="Status after the change")

    # ========================================================================
    # CHANGE METADATA
    # ========================================================================

    change_date = fields.Datetime(
        string="Change Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When this change occurred"
    )

    changed_by = fields.Many2one(
        'res.users',
        string="Changed By",
        required=True,
        default=lambda self: self.env.user,
        help="User who made this change"
    )

    reason = fields.Text(
        string="Change Reason",
        help="Explanation for why this change was made"
    )

    automated = fields.Boolean(
        string="System Generated Change",
        default=False,
        index=True,
        help="Whether this change was made automatically by the system"
    )

    # ========================================================================
    # ADDITIONAL CONTEXT FIELDS
    # ========================================================================

    ip_address = fields.Char(
        string="IP Address",
        help="IP address of user who made the change (for audit purposes)"
    )

    user_agent = fields.Char(
        string="User Agent",
        help="Browser/client information (for audit purposes)"
    )

    session_id = fields.Char(
        string="Session ID",
        help="User session identifier (for audit purposes)"
    )

    # ========================================================================
    # RELATED FIELDS FOR EASY FILTERING
    # ========================================================================

    partner_id = fields.Many2one(
        'res.partner',
        related='participation_id.partner_id',
        string="Member",
        store=True,
        index=True,
        help="Member associated with this participation"
    )

    participation_type = fields.Selection(
        related='participation_id.participation_type',
        string="Participation Type",
        store=True,
        index=True,
        help="Type of participation"
    )

    company_id = fields.Many2one(
        'res.partner',
        related='participation_id.company_id',
        string="Organization",
        store=True,
        help="Organization associated with participation"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    change_summary = fields.Char(
        string="Change Summary",
        compute='_compute_change_summary',
        store=True,
        help="Human-readable summary of this change"
    )

    status_direction = fields.Selection([
        ('activation', 'Activation'),
        ('deactivation', 'Deactivation'),
        ('lateral', 'Lateral Change'),
        ('escalation', 'Status Escalation'),
        ('recovery', 'Status Recovery')
    ], string="Change Direction",
       compute='_compute_status_direction',
       store=True,
       help="Type of status change that occurred")

    is_significant_change = fields.Boolean(
        string="Significant Change",
        compute='_compute_is_significant_change',
        store=True,
        help="Whether this represents a significant status change"
    )

    days_in_previous_status = fields.Integer(
        string="Days in Previous Status",
        compute='_compute_days_in_previous_status',
        store=True,
        help="Number of days the participation spent in the previous status"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('participation_id', 'old_status', 'new_status', 'change_date', 'automated', 'changed_by')
    def _compute_change_summary(self):
        """Compute human-readable change summary."""
        for record in self:
            if record.participation_id and record.new_status:
                member_name = record.participation_id.partner_id.display_name or "Unknown Member"
                
                # Format old status
                old_status_display = dict(record._fields['old_status'].selection).get(record.old_status, 'None') if record.old_status else 'None'
                new_status_display = dict(record._fields['new_status'].selection).get(record.new_status, 'Unknown')
                
                # Create summary based on change type
                if not record.old_status:  # Initial creation
                    summary = f"{member_name}: Created as {new_status_display}"
                else:
                    summary = f"{member_name}: {old_status_display} → {new_status_display}"
                
                # Add automation indicator
                if record.automated:
                    summary += " (Auto)"
                
                # Add date
                if record.change_date:
                    summary += f" on {record.change_date.strftime('%Y-%m-%d')}"
                
                record.change_summary = summary
            else:
                record.change_summary = "Incomplete History Record"

    @api.depends('old_status', 'new_status')
    def _compute_status_direction(self):
        """Determine the type of status change."""
        # Define status hierarchy for analysis
        status_hierarchy = {
            '': 0,
            'prospect': 1,
            'active': 5,
            'grace': 3,
            'suspended': 2,
            'cancelled': 1,
            'terminated': 1
        }
        
        for record in self:
            old_level = status_hierarchy.get(record.old_status, 0)
            new_level = status_hierarchy.get(record.new_status, 0)
            
            if not record.old_status:  # Initial creation
                if record.new_status == 'active':
                    record.status_direction = 'activation'
                else:
                    record.status_direction = 'lateral'
            elif record.new_status == 'active' and record.old_status != 'active':
                record.status_direction = 'activation'
            elif record.old_status == 'active' and record.new_status in ['grace', 'suspended', 'terminated', 'cancelled']:
                record.status_direction = 'deactivation'
            elif new_level > old_level:
                record.status_direction = 'recovery'
            elif new_level < old_level:
                record.status_direction = 'escalation'
            else:
                record.status_direction = 'lateral'

    @api.depends('status_direction', 'old_status', 'new_status')
    def _compute_is_significant_change(self):
        """Determine if this represents a significant business change."""
        significant_changes = [
            ('prospect', 'active'),      # New activation
            ('active', 'grace'),         # Expiration
            ('active', 'suspended'),     # Suspension  
            ('active', 'terminated'),    # Termination
            ('active', 'cancelled'),     # Cancellation
            ('grace', 'active'),         # Recovery from grace
            ('suspended', 'active'),     # Recovery from suspension
            ('grace', 'suspended'),      # Grace to suspension
            ('suspended', 'terminated'), # Suspension to termination
            ('', 'active'),              # Initial activation
        ]
        
        for record in self:
            change_tuple = (record.old_status, record.new_status)
            record.is_significant_change = change_tuple in significant_changes

    @api.depends('participation_id', 'change_date')
    def _compute_days_in_previous_status(self):
        """Calculate how long the participation was in the previous status."""
        for record in self:
            if not record.participation_id or not record.change_date:
                record.days_in_previous_status = 0
                continue
            
            # Find the previous history record for this participation
            previous_history = self.search([
                ('participation_id', '=', record.participation_id.id),
                ('change_date', '<', record.change_date),
                ('id', '!=', record.id)
            ], order='change_date desc', limit=1)
            
            if previous_history:
                time_diff = record.change_date - previous_history.change_date
                record.days_in_previous_status = time_diff.days
            else:
                # If no previous history, calculate from participation begin_date
                if record.participation_id.begin_date:
                    time_diff = record.change_date.date() - record.participation_id.begin_date
                    record.days_in_previous_status = time_diff.days
                else:
                    record.days_in_previous_status = 0

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    @api.constrains('old_status', 'new_status')
    def _check_status_change_validity(self):
        """Validate that status changes are logically valid."""
        for record in self:
            # Allow any status change for now, but we could add business rules here
            # For example, prevent direct transitions from 'terminated' to 'active'
            if record.old_status == 'terminated' and record.new_status == 'active':
                # This might require special approval or be blocked entirely
                pass  # Allow for flexibility
            
            # Ensure new_status is always provided
            if not record.new_status:
                raise ValidationError(_("New status is required for all history records"))

    @api.constrains('participation_id', 'change_date')
    def _check_chronological_order(self):
        """Ensure history records maintain chronological order."""
        for record in self:
            if record.participation_id and record.change_date:
                # Check for future history records that would be out of order
                future_records = self.search([
                    ('participation_id', '=', record.participation_id.id),
                    ('change_date', '>', record.change_date),
                    ('id', '!=', record.id)
                ])
                
                if future_records:
                    # This is acceptable - we're adding a historical record
                    pass
                
                # Check that we're not creating a record before the participation begin_date
                if (record.participation_id.begin_date and 
                    record.change_date.date() < record.participation_id.begin_date):
                    raise ValidationError(_(
                        "History record date (%s) cannot be before participation begin date (%s)"
                    ) % (record.change_date.date(), record.participation_id.begin_date))

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to capture additional audit information."""
        for vals in vals_list:
            # Capture audit information from request context if available
            request = getattr(self.env.context, 'request', None)
            if request and hasattr(request, 'httprequest'):
                if not vals.get('ip_address'):
                    vals['ip_address'] = request.httprequest.environ.get('REMOTE_ADDR')
                if not vals.get('user_agent'):
                    vals['user_agent'] = request.httprequest.environ.get('HTTP_USER_AGENT')
                if not vals.get('session_id') and hasattr(request, 'session'):
                    vals['session_id'] = str(request.session.sid)[:50]  # Truncate for storage
        
        return super().create(vals_list)

    # History records should generally not be updated or deleted for audit integrity
    def write(self, vals):
        """Restrict modification of history records to maintain audit trail."""
        # Only allow updates to reason field and other non-critical fields
        allowed_fields = {'reason', 'ip_address', 'user_agent', 'session_id'}
        
        if any(field not in allowed_fields for field in vals.keys()):
            if not self.env.user.has_group('base.group_system'):
                raise ValidationError(_(
                    "History records cannot be modified to maintain audit integrity. "
                    "Only system administrators can make exceptional changes."
                ))
        
        return super().write(vals)

    def unlink(self):
        """Restrict deletion of history records to maintain audit trail."""
        if not self.env.user.has_group('base.group_system'):
            raise ValidationError(_(
                "History records cannot be deleted to maintain audit integrity. "
                "Only system administrators can make exceptional deletions."
            ))
        
        return super().unlink()

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    @api.model
    def get_participation_timeline(self, participation_id):
        """Get complete timeline for a participation."""
        history_records = self.search([
            ('participation_id', '=', participation_id)
        ], order='change_date asc')
        
        timeline = []
        for record in history_records:
            timeline.append({
                'date': record.change_date,
                'old_status': record.old_status,
                'new_status': record.new_status,
                'reason': record.reason,
                'changed_by': record.changed_by.name,
                'automated': record.automated,
                'days_in_previous': record.days_in_previous_status,
                'significant': record.is_significant_change,
            })
        
        return timeline

    @api.model
    def get_status_change_statistics(self, date_from=None, date_to=None, participation_type=None):
        """Get statistics about status changes for reporting."""
        domain = []
        
        if date_from:
            domain.append(('change_date', '>=', date_from))
        if date_to:
            domain.append(('change_date', '<=', date_to))
        if participation_type:
            domain.append(('participation_type', '=', participation_type))
        
        records = self.search(domain)
        
        # Count changes by type
        stats = {
            'total_changes': len(records),
            'automated_changes': len(records.filtered('automated')),
            'significant_changes': len(records.filtered('is_significant_change')),
            'by_direction': {},
            'by_new_status': {},
            'by_user': {},
        }
        
        # Group by status direction
        for direction in ['activation', 'deactivation', 'lateral', 'escalation', 'recovery']:
            count = len(records.filtered(lambda r: r.status_direction == direction))
            stats['by_direction'][direction] = count
        
        # Group by new status
        for status in ['prospect', 'active', 'grace', 'suspended', 'terminated', 'cancelled']:
            count = len(records.filtered(lambda r: r.new_status == status))
            stats['by_new_status'][status] = count
        
        # Group by user (top 10)
        user_counts = {}
        for record in records:
            user_name = record.changed_by.name if record.changed_by else 'System'
            user_counts[user_name] = user_counts.get(user_name, 0) + 1
        
        # Sort and take top 10
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['by_user'] = dict(sorted_users)
        
        return stats

    def action_view_participation(self):
        """Action to view the related participation record."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participation Details'),
            'res_model': 'ams.participation',
            'res_id': self.participation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_add_reason(self):
        """Action to add or update the reason for this history record."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Change Reason'),
            'res_model': 'ams.participation.history.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_history_id': self.id,
                'default_current_reason': self.reason,
            }
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            result.append((record.id, record.change_summary))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search."""
        args = args or []
        
        if name:
            # Search in change summary, member name, and reason
            domain = [
                '|', '|', '|',
                ('change_summary', operator, name),
                ('partner_id.name', operator, name),
                ('partner_id.display_name', operator, name),
                ('reason', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)