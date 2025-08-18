# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError
import logging
import json

_logger = logging.getLogger(__name__)


class AmsAuditLog(models.Model):
    _name = 'ams.audit.log'
    _description = 'AMS Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'display_name'

    # Core audit fields
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        ondelete='cascade',
        help="Partner record this audit entry relates to"
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='set null',
        help="User who performed the action"
    )
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        help="When the action occurred"
    )
    
    # Activity details
    activity_type = fields.Selection([
        ('created', 'Record Created'),
        ('updated', 'Record Updated'),
        ('deleted', 'Record Deleted'),
        ('status_changed', 'Status Changed'),
        ('role_assigned', 'Role Assigned'),
        ('role_deactivated', 'Role Deactivated'),
        ('preference_created', 'Preference Created'),
        ('preference_updated', 'Preference Updated'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('export', 'Data Export'),
        ('import', 'Data Import'),
        ('merge', 'Record Merge'),
        ('security_event', 'Security Event'),
        ('system_event', 'System Event'),
        ('other', 'Other Activity')
    ], string='Activity Type', required=True,
    help="Type of activity that was performed")
    
    description = fields.Text(
        string='Description',
        required=True,
        help="Detailed description of what happened"
    )
    
    # Technical details
    model_name = fields.Char(
        string='Model Name',
        help="Technical name of the model that was affected"
    )
    record_id = fields.Integer(
        string='Record ID',
        help="ID of the specific record that was affected"
    )
    field_name = fields.Char(
        string='Field Name',
        help="Specific field that was changed (for field-level auditing)"
    )
    old_value = fields.Text(
        string='Old Value',
        help="Previous value before change"
    )
    new_value = fields.Text(
        string='New Value',
        help="New value after change"
    )
    
    # Session and security details
    session_id = fields.Char(
        string='Session ID',
        help="User session identifier"
    )
    ip_address = fields.Char(
        string='IP Address',
        help="IP address from which the action was performed"
    )
    user_agent = fields.Text(
        string='User Agent',
        help="Browser user agent string"
    )
    
    # Additional context
    context_data = fields.Text(
        string='Context Data',
        help="Additional context information in JSON format"
    )
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Risk Level', default='low',
    help="Risk level of this activity for security monitoring")
    
    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    age_days = fields.Integer(
        string='Age (Days)',
        compute='_compute_age_days',
        help="Days since this audit entry was created"
    )

    @api.depends('activity_type', 'partner_id.name', 'description')
    def _compute_display_name(self):
        """Compute display name for audit log entry"""
        for log in self:
            if log.partner_id:
                log.display_name = f"{log.activity_type} - {log.partner_id.name}"
            else:
                log.display_name = f"{log.activity_type} - {log.description[:50]}..."

    @api.depends('timestamp')
    def _compute_age_days(self):
        """Compute age of audit entry in days"""
        now = fields.Datetime.now()
        for log in self:
            if log.timestamp:
                delta = now - log.timestamp
                log.age_days = delta.days
            else:
                log.age_days = 0

    @api.model
    def create(self, vals):
        """Override create to add automatic context data"""
        # Add session and request context automatically
        try:
            if hasattr(self.env, 'request') and self.env.request:
                request = self.env.request
                if not vals.get('session_id') and hasattr(request, 'session'):
                    vals['session_id'] = request.session.sid
                if not vals.get('ip_address') and hasattr(request, 'httprequest'):
                    vals['ip_address'] = request.httprequest.environ.get('REMOTE_ADDR')
                if not vals.get('user_agent') and hasattr(request, 'httprequest'):
                    vals['user_agent'] = request.httprequest.environ.get('HTTP_USER_AGENT')
        except Exception as e:
            _logger.debug(f"Could not extract request context for audit log: {e}")

        # Ensure timestamp is set
        if not vals.get('timestamp'):
            vals['timestamp'] = fields.Datetime.now()

        # Ensure user is set
        if not vals.get('user_id'):
            vals['user_id'] = self.env.user.id

        return super().create(vals)

    def write(self, vals):
        """Override write to prevent modification of audit logs"""
        if self.env.user.has_group('ams_core.group_ams_admin'):
            return super().write(vals)
        else:
            raise AccessError(_("Audit log entries cannot be modified for data integrity."))

    def unlink(self):
        """Override unlink to prevent deletion of audit logs"""
        if self.env.user.has_group('ams_core.group_ams_admin'):
            return super().unlink()
        else:
            raise AccessError(_("Audit log entries cannot be deleted for data integrity."))

    @api.model
    def log_activity(self, partner_id=None, activity_type='other', description='',
                     model_name=None, record_id=None, field_name=None,
                     old_value=None, new_value=None, risk_level='low',
                     context_data=None):
        """
        Convenience method to create audit log entries
        
        Args:
            partner_id: ID of related partner
            activity_type: Type of activity (from selection)
            description: Description of what happened
            model_name: Technical model name
            record_id: ID of affected record
            field_name: Name of changed field
            old_value: Previous value
            new_value: New value
            risk_level: Risk level (low, medium, high, critical)
            context_data: Additional context as dict
        """
        vals = {
            'activity_type': activity_type,
            'description': description,
            'risk_level': risk_level
        }
        
        if partner_id:
            vals['partner_id'] = partner_id
        if model_name:
            vals['model_name'] = model_name
        if record_id:
            vals['record_id'] = record_id
        if field_name:
            vals['field_name'] = field_name
        if old_value is not None:
            vals['old_value'] = str(old_value)
        if new_value is not None:
            vals['new_value'] = str(new_value)
        if context_data:
            vals['context_data'] = json.dumps(context_data)

        try:
            return self.create(vals)
        except Exception as e:
            _logger.error(f"Failed to create audit log entry: {e}")
            return False

    @api.model
    def log_member_activity(self, partner, activity_type, description='', **kwargs):
        """
        Log member-specific activities
        
        Args:
            partner: partner record or ID
            activity_type: type of activity
            description: description of activity
            **kwargs: additional parameters for log_activity
        """
        partner_id = partner.id if hasattr(partner, 'id') else partner
        return self.log_activity(
            partner_id=partner_id,
            activity_type=activity_type,
            description=description,
            **kwargs
        )

    @api.model
    def log_security_event(self, event_type, description, risk_level='medium', **kwargs):
        """
        Log security-related events
        
        Args:
            event_type: type of security event
            description: description of the event
            risk_level: risk level of the event
            **kwargs: additional parameters
        """
        return self.log_activity(
            activity_type='security_event',
            description=f"{event_type}: {description}",
            risk_level=risk_level,
            **kwargs
        )

    @api.model
    def get_partner_activity_history(self, partner_id, limit=None, activity_types=None):
        """
        Get activity history for a specific partner
        
        Args:
            partner_id: ID of the partner
            limit: maximum number of records to return
            activity_types: list of activity types to filter by
        
        Returns:
            recordset of audit log entries
        """
        domain = [('partner_id', '=', partner_id)]
        
        if activity_types:
            domain.append(('activity_type', 'in', activity_types))
            
        return self.search(domain, limit=limit, order='timestamp desc')

    @api.model
    def get_recent_activities(self, days=7, activity_types=None, risk_levels=None):
        """
        Get recent activities for monitoring dashboard
        
        Args:
            days: number of days to look back
            activity_types: list of activity types to include
            risk_levels: list of risk levels to include
        
        Returns:
            recordset of recent audit log entries
        """
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        domain = [('timestamp', '>=', cutoff_date)]
        
        if activity_types:
            domain.append(('activity_type', 'in', activity_types))
        if risk_levels:
            domain.append(('risk_level', 'in', risk_levels))
            
        return self.search(domain, order='timestamp desc')

    @api.model
    def get_security_alerts(self, days=1):
        """
        Get recent security alerts for monitoring
        
        Args:
            days: number of days to look back
        
        Returns:
            recordset of security-related audit entries
        """
        return self.get_recent_activities(
            days=days,
            activity_types=['security_event'],
            risk_levels=['high', 'critical']
        )

    def action_view_related_activities(self):
        """Action to view all activities for the same partner"""
        self.ensure_one()
        if not self.partner_id:
            return {}
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activities for %s') % self.partner_id.name,
            'res_model': 'ams.audit.log',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id}
        }

    @api.model
    def cleanup_old_logs(self, days=365):
        """
        Clean up audit logs older than specified days
        Only call this method with appropriate permissions
        
        Args:
            days: number of days to retain logs
        
        Returns:
            number of deleted records
        """
        if not self.env.user.has_group('ams_core.group_ams_admin'):
            raise AccessError(_("Only administrators can clean up audit logs."))
            
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        old_logs = self.search([('timestamp', '<', cutoff_date)])
        count = len(old_logs)
        
        if old_logs:
            # Log the cleanup activity first
            self.log_activity(
                activity_type='system_event',
                description=f"Cleaned up {count} audit log entries older than {days} days",
                risk_level='low'
            )
            old_logs.unlink()
            
        return count

    @api.model
    def export_audit_trail(self, partner_id=None, date_from=None, date_to=None):
        """
        Export audit trail for compliance purposes
        
        Args:
            partner_id: specific partner to export (optional)
            date_from: start date for export
            date_to: end date for export
        
        Returns:
            list of dictionaries with audit data
        """
        domain = []
        
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if date_from:
            domain.append(('timestamp', '>=', date_from))
        if date_to:
            domain.append(('timestamp', '<=', date_to))
            
        logs = self.search(domain, order='timestamp desc')
        
        export_data = []
        for log in logs:
            export_data.append({
                'timestamp': log.timestamp.isoformat() if log.timestamp else '',
                'user': log.user_id.name if log.user_id else '',
                'partner': log.partner_id.name if log.partner_id else '',
                'activity_type': log.activity_type,
                'description': log.description,
                'model_name': log.model_name or '',
                'record_id': log.record_id or '',
                'field_name': log.field_name or '',
                'old_value': log.old_value or '',
                'new_value': log.new_value or '',
                'ip_address': log.ip_address or '',
                'risk_level': log.risk_level
            })
            
        # Log the export activity
        self.log_activity(
            activity_type='export',
            description=f"Exported {len(export_data)} audit log entries",
            risk_level='medium'
        )
        
        return export_data

    @api.model
    def get_audit_statistics(self, days=30):
        """
        Get audit statistics for dashboard
        
        Args:
            days: number of days to analyze
        
        Returns:
            dictionary with statistics
        """
        cutoff_date = fields.Datetime.now() - fields.timedelta(days=days)
        domain = [('timestamp', '>=', cutoff_date)]
        
        logs = self.search(domain)
        
        stats = {
            'total_activities': len(logs),
            'by_type': {},
            'by_risk_level': {},
            'by_user': {},
            'unique_partners': len(logs.mapped('partner_id')),
            'security_events': len(logs.filtered(lambda l: l.activity_type == 'security_event'))
        }
        
        # Count by activity type
        for activity_type in logs.mapped('activity_type'):
            stats['by_type'][activity_type] = len(logs.filtered(lambda l: l.activity_type == activity_type))
            
        # Count by risk level
        for risk_level in logs.mapped('risk_level'):
            stats['by_risk_level'][risk_level] = len(logs.filtered(lambda l: l.risk_level == risk_level))
            
        # Count by user (top 10)
        user_counts = {}
        for user in logs.mapped('user_id'):
            if user:
                user_counts[user.name] = len(logs.filtered(lambda l: l.user_id == user))
        stats['by_user'] = dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return stats