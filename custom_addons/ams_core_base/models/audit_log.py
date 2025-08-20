# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
from datetime import timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class AuditLog(models.Model):
    _name = 'ams.audit.log'
    _description = 'AMS Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'description'

    # ===== BASIC INFORMATION =====
    model_name = fields.Char(
        string='Model Name',
        required=True,
        index=True,
        help="Name of the model being audited"
    )

    record_id = fields.Integer(
        string='Record ID',
        required=True,
        index=True,
        help="ID of the record being audited"
    )

    operation = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('read', 'Read'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('merge', 'Merge'),
        ('archive', 'Archive'),
        ('restore', 'Restore'),
        ('other', 'Other'),
    ], string='Operation', required=True, index=True)

    description = fields.Char(
        string='Description',
        required=True,
        help="Brief description of the operation"
    )

    # ===== TIMESTAMP AND USER =====
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When the operation occurred"
    )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        help="User who performed the operation"
    )

    # ===== DATA TRACKING =====
    data = fields.Text(
        string='Data',
        help="JSON data of changes, old/new values, or operation details"
    )

    data_json = fields.Json(
        string='Structured Data',
        help="Structured JSON data for programmatic access"
    )

    # ===== CONTEXT INFORMATION =====
    ip_address = fields.Char(
        string='IP Address',
        help="IP address from where the operation was performed"
    )

    user_agent = fields.Text(
        string='User Agent',
        help="Browser/client user agent string"
    )

    session_id = fields.Char(
        string='Session ID',
        help="User session identifier"
    )

    # ===== RECORD INFORMATION =====
    record_name = fields.Char(
        string='Record Name',
        help="Display name of the affected record"
    )

    record_reference = fields.Reference(
        string='Record Reference',
        selection='_get_model_selection',
        help="Direct reference to the audited record"
    )

    # ===== RISK AND SENSITIVITY =====
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Risk Level', default='low', help="Risk level of the operation")

    is_sensitive = fields.Boolean(
        string='Sensitive Data',
        default=False,
        help="Check if this operation involved sensitive data"
    )

    privacy_impact = fields.Boolean(
        string='Privacy Impact',
        default=False,
        help="Check if this operation has privacy implications"
    )

    # ===== RELATED RECORDS =====
    related_partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        help="Partner related to this audit entry"
    )

    related_model = fields.Char(
        string='Related Model',
        help="Other model affected by this operation"
    )

    related_record_id = fields.Integer(
        string='Related Record ID',
        help="ID of related record"
    )

    # ===== STATUS AND FLAGS =====
    is_system_operation = fields.Boolean(
        string='System Operation',
        default=False,
        help="Check if this was a system-initiated operation"
    )

    requires_review = fields.Boolean(
        string='Requires Review',
        default=False,
        help="Check if this operation requires manual review"
    )

    reviewed = fields.Boolean(
        string='Reviewed',
        default=False,
        help="Check if this entry has been reviewed"
    )

    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        help="User who reviewed this audit entry"
    )

    reviewed_date = fields.Datetime(
        string='Reviewed Date',
        help="Date when this entry was reviewed"
    )

    # ===== NOTES =====
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this audit entry"
    )

    @api.model
    def _get_model_selection(self):
        """Get list of models for reference field"""
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]

    @api.model
    def create(self, vals):
        """Override create to capture additional context"""
        # Capture IP address and user agent if available
        request = self.env.context.get('request')
        if request:
            vals.update({
                'ip_address': request.httprequest.environ.get('REMOTE_ADDR'),
                'user_agent': request.httprequest.environ.get('HTTP_USER_AGENT'),
                'session_id': request.session.sid if hasattr(request, 'session') else None,
            })

        # Parse and structure JSON data if provided as string
        if vals.get('data') and not vals.get('data_json'):
            try:
                vals['data_json'] = json.loads(vals['data']) if isinstance(vals['data'], str) else vals['data']
            except (json.JSONDecodeError, TypeError):
                pass

        # Set record reference if possible
        if vals.get('model_name') and vals.get('record_id'):
            try:
                model = self.env[vals['model_name']]
                record = model.browse(vals['record_id'])
                if record.exists():
                    vals['record_reference'] = f"{vals['model_name']},{vals['record_id']}"
                    vals['record_name'] = record.display_name
                    
                    # Set related partner if the record is a partner or has a partner field
                    if vals['model_name'] == 'res.partner':
                        vals['related_partner_id'] = vals['record_id']
                    elif hasattr(record, 'partner_id') and record.partner_id:
                        vals['related_partner_id'] = record.partner_id.id
            except Exception as e:
                _logger.warning(f"Could not set record reference: {e}")

        # Determine risk level based on operation and model
        if not vals.get('risk_level'):
            vals['risk_level'] = self._calculate_risk_level(vals)

        # Set sensitivity flags
        vals.update(self._analyze_sensitivity(vals))

        return super(AuditLog, self).create(vals)

    def _calculate_risk_level(self, vals):
        """Calculate risk level based on operation and model"""
        operation = vals.get('operation')
        model_name = vals.get('model_name', '')
        
        # Critical operations
        if operation in ['unlink', 'merge']:
            return 'critical'
        
        # High risk models or operations
        if ('payment' in model_name or 'invoice' in model_name or 
            'account' in model_name or operation == 'export'):
            return 'high'
        
        # Medium risk for member data changes
        if ('partner' in model_name or 'member' in model_name) and operation == 'write':
            return 'medium'
        
        return 'low'

    def _analyze_sensitivity(self, vals):
        """Analyze if operation involves sensitive data"""
        model_name = vals.get('model_name', '')
        data_str = str(vals.get('data', '')).lower()
        
        sensitive_keywords = [
            'date_of_birth', 'ssn', 'tax_id', 'bank', 'payment',
            'salary', 'gender', 'ethnicity', 'medical', 'health'
        ]
        
        is_sensitive = any(keyword in model_name.lower() or keyword in data_str 
                          for keyword in sensitive_keywords)
        
        privacy_keywords = [
            'consent', 'privacy', 'gdpr', 'email', 'phone', 'address'
        ]
        
        privacy_impact = any(keyword in model_name.lower() or keyword in data_str 
                           for keyword in privacy_keywords)
        
        return {
            'is_sensitive': is_sensitive,
            'privacy_impact': privacy_impact,
            'requires_review': is_sensitive or vals.get('operation') in ['export', 'merge', 'unlink']
        }

    @api.model
    def log_operation(self, record, operation, description, data=None, **kwargs):
        """Convenience method to log an operation"""
        vals = {
            'model_name': record._name,
            'record_id': record.id,
            'operation': operation,
            'description': description,
            'user_id': self.env.user.id,
            'data': str(data) if data else '',
            'data_json': data if isinstance(data, dict) else None,
        }
        vals.update(kwargs)
        return self.create(vals)

    def action_mark_reviewed(self):
        """Mark audit entries as reviewed"""
        for log in self:
            if not log.reviewed:
                log.write({
                    'reviewed': True,
                    'reviewed_by': self.env.user.id,
                    'reviewed_date': fields.Datetime.now(),
                })

    def action_view_record(self):
        """Action to view the audited record"""
        self.ensure_one()
        if not self.record_reference:
            return {'type': 'ir.actions.act_window_close'}
        
        try:
            return {
                'type': 'ir.actions.act_window',
                'name': f'View {self.record_name}',
                'res_model': self.model_name,
                'view_mode': 'form',
                'res_id': self.record_id,
                'target': 'current',
            }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Record no longer exists'),
                    'type': 'warning',
                }
            }

    @api.model
    def cleanup_old_logs(self, days=365):
        """Clean up audit logs older than specified days"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([
            ('timestamp', '<', cutoff_date),
            ('requires_review', '=', False),
            ('is_sensitive', '=', False),
        ])
        
        count = len(old_logs)
        if old_logs:
            old_logs.unlink()
            _logger.info(f"Cleaned up {count} old audit log entries")
        
        return count

    @api.model
    def get_user_activity_summary(self, user_id, days=30):
        """Get activity summary for a user"""
        start_date = fields.Datetime.now() - timedelta(days=days)
        logs = self.search([
            ('user_id', '=', user_id),
            ('timestamp', '>=', start_date),
        ])
        
        summary = {
            'total_operations': len(logs),
            'operations_by_type': {},
            'models_accessed': set(),
            'sensitive_operations': 0,
            'last_activity': None,
        }
        
        for log in logs:
            # Count by operation type
            op_type = log.operation
            summary['operations_by_type'][op_type] = summary['operations_by_type'].get(op_type, 0) + 1
            
            # Track models accessed
            summary['models_accessed'].add(log.model_name)
            
            # Count sensitive operations
            if log.is_sensitive:
                summary['sensitive_operations'] += 1
            
            # Track last activity
            if not summary['last_activity'] or log.timestamp > summary['last_activity']:
                summary['last_activity'] = log.timestamp
        
        summary['models_accessed'] = list(summary['models_accessed'])
        return summary

    @api.model
    def get_model_activity_stats(self, model_name, days=30):
        """Get activity statistics for a specific model"""
        start_date = fields.Datetime.now() - timedelta(days=days)
        logs = self.search([
            ('model_name', '=', model_name),
            ('timestamp', '>=', start_date),
        ])
        
        stats = {
            'total_operations': len(logs),
            'operations_by_type': {},
            'unique_users': set(),
            'unique_records': set(),
            'sensitive_operations': 0,
        }
        
        for log in logs:
            stats['operations_by_type'][log.operation] = stats['operations_by_type'].get(log.operation, 0) + 1
            stats['unique_users'].add(log.user_id.id)
            stats['unique_records'].add(log.record_id)
            if log.is_sensitive:
                stats['sensitive_operations'] += 1
        
        stats['unique_users'] = len(stats['unique_users'])
        stats['unique_records'] = len(stats['unique_records'])
        return stats

    def name_get(self):
        """Override name_get for better display"""
        result = []
        for log in self:
            name = f"{log.timestamp.strftime('%Y-%m-%d %H:%M')} - {log.operation.title()} - {log.description}"
            if log.record_name:
                name += f" ({log.record_name})"
            result.append((log.id, name))
        return result

    @api.model
    def search_logs_by_partner(self, partner_id, days=None):
        """Search audit logs related to a specific partner"""
        domain = [('related_partner_id', '=', partner_id)]
        
        if days:
            start_date = fields.Datetime.now() - timedelta(days=days)
            domain.append(('timestamp', '>=', start_date))
        
        return self.search(domain, order='timestamp desc')