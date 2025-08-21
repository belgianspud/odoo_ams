# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AuditLog(models.Model):
    """Core audit logging model for tracking all data changes across AMS modules."""
    
    _name = 'ams.audit.log'
    _description = 'AMS Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'description'
    
    # Core Audit Information
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help='When the audited action occurred'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        index=True,
        help='User who performed the action'
    )
    
    model_name = fields.Char(
        string='Model',
        required=True,
        index=True,
        help='Technical model name (e.g., res.partner)'
    )
    
    model_description = fields.Char(
        string='Model Description',
        help='Human-readable model description'
    )
    
    record_id = fields.Integer(
        string='Record ID',
        required=True,
        index=True,
        help='ID of the record that was modified'
    )
    
    record_name = fields.Char(
        string='Record Name',
        help='Display name of the record at time of audit'
    )
    
    # Action Information
    action = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('read', 'Read'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('merge', 'Merge'),
        ('archive', 'Archive'),
        ('restore', 'Restore'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('other', 'Other')
    ], string='Action', required=True, index=True, help='Type of action performed')
    
    description = fields.Char(
        string='Description',
        required=True,
        help='Brief description of the action'
    )
    
    # Change Details
    field_changes = fields.Text(
        string='Field Changes',
        help='JSON representation of field changes (old_value -> new_value)'
    )
    
    field_changes_json = fields.Json(
        string='Field Changes JSON',
        help='Structured field changes data'
    )
    
    # Context Information
    ip_address = fields.Char(
        string='IP Address',
        help='IP address of the user who performed the action'
    )
    
    user_agent = fields.Char(
        string='User Agent',
        help='Browser/client user agent string'
    )
    
    session_id = fields.Char(
        string='Session ID',
        help='User session identifier'
    )
    
    # Classification
    category = fields.Selection([
        ('member_data', 'Member Data'),
        ('financial', 'Financial'),
        ('privacy', 'Privacy & Consent'),
        ('security', 'Security'),
        ('configuration', 'Configuration'),
        ('professional', 'Professional Credentials'),
        ('membership', 'Membership'),
        ('communication', 'Communications'),
        ('system', 'System'),
        ('other', 'Other')
    ], string='Category', index=True, help='Category of the audited action')
    
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Risk Level', default='low', index=True, 
       help='Risk assessment of the action')
    
    # Flags
    is_sensitive = fields.Boolean(
        string='Sensitive Data',
        default=False,
        index=True,
        help='Whether this audit entry involves sensitive data'
    )
    
    is_system_operation = fields.Boolean(
        string='System Operation',
        default=False,
        help='Whether this was a system-generated operation'
    )
    
    privacy_impact = fields.Boolean(
        string='Privacy Impact',
        default=False,
        index=True,
        help='Whether this action has privacy implications'
    )
    
    requires_review = fields.Boolean(
        string='Requires Review',
        default=False,
        index=True,
        help='Whether this audit entry requires manual review'
    )
    
    # Review Information
    reviewed = fields.Boolean(
        string='Reviewed',
        default=False,
        index=True,
        help='Whether this audit entry has been reviewed'
    )
    
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        help='User who reviewed this audit entry'
    )
    
    reviewed_date = fields.Datetime(
        string='Reviewed Date',
        help='When this audit entry was reviewed'
    )
    
    # Related Records
    related_partner_id = fields.Many2one(
        'res.partner',
        string='Related Member',
        index=True,
        help='Partner/member this audit entry relates to'
    )
    
    related_model = fields.Char(
        string='Related Model',
        help='Related model if this audit entry affects multiple records'
    )
    
    related_record_id = fields.Integer(
        string='Related Record ID',
        help='Related record ID if applicable'
    )
    
    # Additional Information
    notes = fields.Text(
        string='Notes',
        help='Additional notes or comments about this audit entry'
    )
    
    retention_date = fields.Date(
        string='Retention Date',
        compute='_compute_retention_date',
        store=True,
        help='Date when this audit log can be safely deleted'
    )
    
    # Record Reference for Generic Access
    record_reference = fields.Reference(
        string='Record Reference',
        selection='_get_model_selection',
        help='Direct reference to the audited record'
    )
    
    @api.model
    def _get_model_selection(self):
        """Get list of models for reference field."""
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]
    
    @api.depends('timestamp', 'category', 'risk_level')
    def _compute_retention_date(self):
        """Compute retention date based on category and risk level."""
        for log in self:
            base_date = log.timestamp.date() if log.timestamp else fields.Date.today()
            
            # Default retention periods in years
            retention_years = 7  # Default 7 years
            
            # Adjust based on category
            if log.category in ['financial', 'privacy']:
                retention_years = 10  # Financial and privacy data kept longer
            elif log.category == 'security':
                retention_years = 5   # Security logs kept for 5 years
            elif log.category == 'system':
                retention_years = 2   # System logs kept for 2 years
            
            # Adjust based on risk level
            if log.risk_level == 'critical':
                retention_years += 3  # Critical events kept longer
            elif log.risk_level == 'high':
                retention_years += 1
            
            log.retention_date = base_date + timedelta(days=retention_years * 365)
    
    @api.model
    def create_audit_log(self, model_name, record_id, action, description, 
                        field_changes=None, category=None, risk_level='low',
                        is_sensitive=False, privacy_impact=False, 
                        related_partner_id=None, notes=None):
        """
        Create an audit log entry.
        
        Args:
            model_name (str): Technical model name
            record_id (int): ID of the record
            action (str): Action performed
            description (str): Description of the action
            field_changes (dict): Dictionary of field changes
            category (str): Category of the action
            risk_level (str): Risk level assessment
            is_sensitive (bool): Whether sensitive data is involved
            privacy_impact (bool): Whether privacy is impacted
            related_partner_id (int): Related partner ID
            notes (str): Additional notes
        """
        try:
            # Get model description
            model_obj = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
            model_description = model_obj.name if model_obj else model_name
            
            # Get record name if record still exists
            record_name = None
            if action != 'unlink':
                try:
                    record = self.env[model_name].browse(record_id)
                    if record.exists():
                        record_name = record.display_name
                except Exception:
                    record_name = f'Record #{record_id}'
            
            # Get request context information
            request = getattr(self.env, 'request', None)
            ip_address = None
            user_agent = None
            session_id = None
            
            if request:
                ip_address = request.httprequest.environ.get('REMOTE_ADDR')
                user_agent = request.httprequest.environ.get('HTTP_USER_AGENT')
                session_id = getattr(request.session, 'sid', None)
            
            # Determine if review is required
            requires_review = (
                risk_level in ['high', 'critical'] or 
                is_sensitive or 
                privacy_impact or
                action in ['unlink', 'merge', 'export']
            )
            
            # Prepare field changes
            field_changes_text = None
            field_changes_json = None
            if field_changes:
                field_changes_json = field_changes
                field_changes_text = json.dumps(field_changes, indent=2, default=str)
            
            # Create record reference if possible
            record_reference = None
            if action != 'unlink':
                try:
                    record_reference = f'{model_name},{record_id}'
                except Exception:
                    pass
            
            # Create audit log entry
            audit_log = self.create({
                'model_name': model_name,
                'model_description': model_description,
                'record_id': record_id,
                'record_name': record_name,
                'action': action,
                'description': description,
                'field_changes': field_changes_text,
                'field_changes_json': field_changes_json,
                'category': category or 'other',
                'risk_level': risk_level,
                'is_sensitive': is_sensitive,
                'privacy_impact': privacy_impact,
                'requires_review': requires_review,
                'related_partner_id': related_partner_id,
                'notes': notes,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'session_id': session_id,
                'record_reference': record_reference,
            })
            
            _logger.info(f'Audit log created: {description} for {model_name}#{record_id}')
            return audit_log
            
        except Exception as e:
            _logger.error(f'Failed to create audit log: {str(e)}')
            # Don't raise exception to avoid breaking the original operation
            return False
    
    def action_mark_reviewed(self):
        """Mark audit log entry as reviewed."""
        for log in self:
            if not log.reviewed:
                log.write({
                    'reviewed': True,
                    'reviewed_by': self.env.user.id,
                    'reviewed_date': fields.Datetime.now(),
                })
                log.message_post(body=_('Audit entry marked as reviewed'))
    
    def action_view_record(self):
        """Open the audited record if it still exists."""
        self.ensure_one()
        if self.action == 'unlink':
            raise ValidationError(_('Cannot view deleted record'))
        
        try:
            record = self.env[self.model_name].browse(self.record_id)
            if not record.exists():
                raise ValidationError(_('Record no longer exists'))
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('View Record'),
                'res_model': self.model_name,
                'res_id': self.record_id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            raise ValidationError(_('Cannot open record: %s') % str(e))
    
    @api.model
    def cleanup_old_logs(self, days_to_keep=None):
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            days_to_keep (int): Override default retention period
        """
        if not self.env.user.has_group('ams_core_audit.group_audit_manager'):
            raise AccessError(_('Only audit managers can clean up logs'))
        
        if days_to_keep:
            cutoff_date = fields.Date.today() - timedelta(days=days_to_keep)
            domain = [('timestamp', '<', cutoff_date)]
        else:
            domain = [('retention_date', '<', fields.Date.today())]
        
        old_logs = self.search(domain)
        count = len(old_logs)
        
        if old_logs:
            # Archive instead of delete for compliance
            old_logs.write({'notes': 'Archived by automated cleanup'})
            _logger.info(f'Archived {count} old audit log entries')
        
        return count
    
    @api.model
    def get_audit_summary(self, model_name=None, record_id=None, days=30):
        """Get audit summary for a specific record or model."""
        domain = [('timestamp', '>=', fields.Datetime.now() - timedelta(days=days))]
        
        if model_name:
            domain.append(('model_name', '=', model_name))
        if record_id:
            domain.append(('record_id', '=', record_id))
        
        logs = self.search(domain)
        
        summary = {
            'total_entries': len(logs),
            'by_action': {},
            'by_user': {},
            'by_category': {},
            'by_risk_level': {},
            'sensitive_count': len(logs.filtered('is_sensitive')),
            'requires_review_count': len(logs.filtered(lambda l: l.requires_review and not l.reviewed)),
        }
        
        for log in logs:
            # Count by action
            summary['by_action'][log.action] = summary['by_action'].get(log.action, 0) + 1
            
            # Count by user
            user_name = log.user_id.name
            summary['by_user'][user_name] = summary['by_user'].get(user_name, 0) + 1
            
            # Count by category
            summary['by_category'][log.category] = summary['by_category'].get(log.category, 0) + 1
            
            # Count by risk level
            summary['by_risk_level'][log.risk_level] = summary['by_risk_level'].get(log.risk_level, 0) + 1
        
        return summary
    
    def name_get(self):
        """Return descriptive name for audit log entries."""
        result = []
        for log in self:
            name = f"{log.action.title()} {log.model_description or log.model_name}"
            if log.record_name:
                name += f" - {log.record_name}"
            name += f" ({log.timestamp.strftime('%Y-%m-%d %H:%M')})"
            result.append((log.id, name))
        return result
    
    @api.model
    def _cron_cleanup_old_logs(self):
        """Cron job to clean up old audit logs."""
        try:
            count = self.cleanup_old_logs()
            _logger.info(f'Audit log cleanup completed: {count} entries archived')
        except Exception as e:
            _logger.error(f'Audit log cleanup failed: {str(e)}')
    
    # Security: Prevent modification of audit logs
    def write(self, vals):
        """Override write to prevent modification of audit logs except for review."""
        allowed_fields = {'reviewed', 'reviewed_by', 'reviewed_date', 'notes'}
        
        if not self.env.user.has_group('ams_core_audit.group_audit_manager'):
            # Only allow review fields for non-managers
            if not set(vals.keys()).issubset(allowed_fields):
                raise AccessError(_('Audit logs cannot be modified'))
        
        return super(AuditLog, self).write(vals)
    
    def unlink(self):
        """Override unlink to prevent deletion of audit logs."""
        if not self.env.user.has_group('ams_core_audit.group_audit_manager'):
            raise AccessError(_('Audit logs cannot be deleted'))
        
        # Log the deletion of audit logs
        for log in self:
            self.create_audit_log(
                model_name='ams.audit.log',
                record_id=log.id,
                action='unlink',
                description=f'Audit log deleted: {log.description}',
                category='system',
                risk_level='high',
                notes=f'Original log: {log.model_name}#{log.record_id} - {log.action}'
            )
        
        return super(AuditLog, self).unlink()