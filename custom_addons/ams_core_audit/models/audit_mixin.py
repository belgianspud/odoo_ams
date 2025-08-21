# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class AuditMixin(models.AbstractModel):
    """
    Mixin class that provides automatic audit logging for any model that inherits it.
    
    Usage:
        class MyModel(models.Model):
            _name = 'my.model'
            _inherit = ['mail.thread', 'ams.audit.mixin']
            
            # Configure audit settings
            _audit_enabled = True
            _audit_category = 'member_data'
            _audit_sensitive_fields = ['ssn', 'tax_id']
            _audit_exclude_fields = ['write_date', 'write_uid']
    """
    
    _name = 'ams.audit.mixin'
    _description = 'AMS Audit Mixin'
    
    # Audit configuration attributes (to be set in inheriting models)
    _audit_enabled = True  # Whether audit logging is enabled for this model
    _audit_category = 'other'  # Default audit category
    _audit_sensitive_fields = []  # Fields that contain sensitive data
    _audit_exclude_fields = ['write_date', 'write_uid', 'create_date', 'create_uid', '__last_update']
    _audit_privacy_fields = []  # Fields that have privacy implications
    _audit_high_risk_actions = ['unlink']  # Actions that are considered high risk
    _audit_auto_review_required = False  # Whether changes automatically require review
    
    # Audit-related computed fields
    audit_log_count = fields.Integer(
        string='Audit Log Count',
        compute='_compute_audit_log_count',
        help='Number of audit log entries for this record'
    )
    
    last_audit_date = fields.Datetime(
        string='Last Audit Date',
        compute='_compute_last_audit_date',
        help='Date of last audit log entry'
    )
    
    @api.depends('id')
    def _compute_audit_log_count(self):
        """Compute the number of audit log entries for this record."""
        for record in self:
            if record.id:
                count = self.env['ams.audit.log'].search_count([
                    ('model_name', '=', record._name),
                    ('record_id', '=', record.id)
                ])
                record.audit_log_count = count
            else:
                record.audit_log_count = 0
    
    @api.depends('id')
    def _compute_last_audit_date(self):
        """Compute the date of the last audit log entry."""
        for record in self:
            if record.id:
                last_log = self.env['ams.audit.log'].search([
                    ('model_name', '=', record._name),
                    ('record_id', '=', record.id)
                ], order='timestamp desc', limit=1)
                record.last_audit_date = last_log.timestamp if last_log else False
            else:
                record.last_audit_date = False
    
    def _get_audit_category(self):
        """Get the audit category for this model."""
        return getattr(self, '_audit_category', 'other')
    
    def _get_audit_sensitive_fields(self):
        """Get the list of sensitive fields for this model."""
        return getattr(self, '_audit_sensitive_fields', [])
    
    def _get_audit_exclude_fields(self):
        """Get the list of fields to exclude from audit logging."""
        base_exclude = ['write_date', 'write_uid', 'create_date', 'create_uid', '__last_update']
        model_exclude = getattr(self, '_audit_exclude_fields', [])
        return list(set(base_exclude + model_exclude))
    
    def _get_audit_privacy_fields(self):
        """Get the list of fields that have privacy implications."""
        return getattr(self, '_audit_privacy_fields', [])
    
    def _is_audit_enabled(self):
        """Check if audit logging is enabled for this model."""
        # Global audit setting
        global_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'ams.audit_logging_enabled', 'True'
        ).lower() == 'true'
        
        # Model-specific setting
        model_enabled = getattr(self, '_audit_enabled', True)
        
        return global_enabled and model_enabled
    
    def _should_audit_field(self, field_name):
        """Check if a specific field should be audited."""
        exclude_fields = self._get_audit_exclude_fields()
        return field_name not in exclude_fields
    
    def _is_sensitive_change(self, field_changes):
        """Check if the field changes involve sensitive data."""
        sensitive_fields = self._get_audit_sensitive_fields()
        return any(field in sensitive_fields for field in field_changes.keys())
    
    def _has_privacy_impact(self, field_changes):
        """Check if the field changes have privacy implications."""
        privacy_fields = self._get_audit_privacy_fields()
        return any(field in privacy_fields for field in field_changes.keys())
    
    def _determine_risk_level(self, action, field_changes=None):
        """Determine the risk level of an audit action."""
        # High risk actions
        high_risk_actions = getattr(self, '_audit_high_risk_actions', ['unlink'])
        if action in high_risk_actions:
            return 'high'
        
        # Check for sensitive or privacy-impacting changes
        if field_changes:
            if self._is_sensitive_change(field_changes):
                return 'high'
            if self._has_privacy_impact(field_changes):
                return 'medium'
        
        # Default to low risk
        return 'low'
    
    def _get_related_partner_id(self):
        """Get the related partner ID for audit logging."""
        # Try common partner field names
        partner_fields = ['partner_id', 'member_id', 'customer_id', 'user_id']
        
        for field_name in partner_fields:
            if hasattr(self, field_name):
                partner = getattr(self, field_name, None)
                if partner and hasattr(partner, '_name'):
                    if partner._name == 'res.partner':
                        return partner.id
                    elif partner._name == 'res.users' and hasattr(partner, 'partner_id'):
                        return partner.partner_id.id
        
        # If this is a partner record itself
        if self._name == 'res.partner':
            return self.id
        
        return None
    
    def _prepare_field_changes(self, old_values, new_values):
        """Prepare field changes for audit logging."""
        changes = {}
        exclude_fields = self._get_audit_exclude_fields()
        
        # Get all fields that might have changed
        all_fields = set(old_values.keys()) | set(new_values.keys())
        
        for field_name in all_fields:
            if not self._should_audit_field(field_name):
                continue
            
            old_val = old_values.get(field_name)
            new_val = new_values.get(field_name)
            
            # Skip if values are the same
            if old_val == new_val:
                continue
            
            # Handle different field types
            changes[field_name] = {
                'old': self._format_field_value(field_name, old_val),
                'new': self._format_field_value(field_name, new_val)
            }
        
        return changes
    
    def _format_field_value(self, field_name, value):
        """Format field value for audit logging."""
        if value is None:
            return None
        
        # Get field definition
        field_def = self._fields.get(field_name)
        if not field_def:
            return str(value)
        
        # Handle different field types
        if field_def.type == 'many2one':
            if hasattr(value, 'display_name'):
                return f"{value.display_name} (ID: {value.id})"
            else:
                return str(value)
        elif field_def.type in ['one2many', 'many2many']:
            if hasattr(value, 'mapped'):
                return [f"{rec.display_name} (ID: {rec.id})" for rec in value]
            else:
                return str(value)
        elif field_def.type == 'selection':
            if hasattr(field_def, 'selection'):
                selection_dict = dict(field_def.selection)
                return selection_dict.get(value, str(value))
        elif field_def.type == 'boolean':
            return bool(value)
        else:
            return str(value)
    
    def _create_audit_log(self, action, description, field_changes=None, notes=None):
        """Create an audit log entry for this record."""
        if not self._is_audit_enabled():
            return False
        
        # Determine audit properties
        category = self._get_audit_category()
        risk_level = self._determine_risk_level(action, field_changes)
        is_sensitive = field_changes and self._is_sensitive_change(field_changes)
        privacy_impact = field_changes and self._has_privacy_impact(field_changes)
        related_partner_id = self._get_related_partner_id()
        
        # Create audit log
        return self.env['ams.audit.log'].create_audit_log(
            model_name=self._name,
            record_id=self.id,
            action=action,
            description=description,
            field_changes=field_changes,
            category=category,
            risk_level=risk_level,
            is_sensitive=is_sensitive,
            privacy_impact=privacy_impact,
            related_partner_id=related_partner_id,
            notes=notes
        )
    
    @api.model
    def create(self, vals):
        """Override create to add audit logging."""
        # Create the record first
        record = super(AuditMixin, self).create(vals)
        
        # Create audit log
        if record._is_audit_enabled():
            try:
                # Prepare field changes (all fields are "new" for create)
                field_changes = {}
                for field_name, value in vals.items():
                    if record._should_audit_field(field_name):
                        field_changes[field_name] = {
                            'old': None,
                            'new': record._format_field_value(field_name, value)
                        }
                
                description = f"Created {record._description or record._name}: {record.display_name}"
                record._create_audit_log('create', description, field_changes)
                
            except Exception as e:
                _logger.error(f"Failed to create audit log for {record._name}#{record.id}: {str(e)}")
        
        return record
    
    def write(self, vals):
        """Override write to add audit logging."""
        if not self._is_audit_enabled():
            return super(AuditMixin, self).write(vals)
        
        # Store old values before update
        old_values = {}
        for record in self:
            old_values[record.id] = {}
            for field_name in vals.keys():
                if record._should_audit_field(field_name):
                    try:
                        old_values[record.id][field_name] = getattr(record, field_name, None)
                    except Exception:
                        old_values[record.id][field_name] = None
        
        # Perform the update
        result = super(AuditMixin, self).write(vals)
        
        # Create audit logs
        for record in self:
            try:
                # Prepare field changes
                new_values = {}
                for field_name in vals.keys():
                    if record._should_audit_field(field_name):
                        try:
                            new_values[field_name] = getattr(record, field_name, None)
                        except Exception:
                            new_values[field_name] = None
                
                field_changes = record._prepare_field_changes(
                    old_values.get(record.id, {}), 
                    new_values
                )
                
                if field_changes:  # Only log if there are actual changes
                    changed_fields = list(field_changes.keys())
                    description = f"Updated {record._description or record._name}: {record.display_name} (fields: {', '.join(changed_fields)})"
                    record._create_audit_log('write', description, field_changes)
                
            except Exception as e:
                _logger.error(f"Failed to create audit log for {record._name}#{record.id}: {str(e)}")
        
        return result
    
    def unlink(self):
        """Override unlink to add audit logging."""
        if not self._is_audit_enabled():
            return super(AuditMixin, self).unlink()
        
        # Store information before deletion
        records_info = []
        for record in self:
            try:
                # Get current field values
                current_values = {}
                for field_name in record._fields.keys():
                    if record._should_audit_field(field_name):
                        try:
                            current_values[field_name] = getattr(record, field_name, None)
                        except Exception:
                            current_values[field_name] = None
                
                # Prepare field changes (all fields become "None")
                field_changes = {}
                for field_name, value in current_values.items():
                    field_changes[field_name] = {
                        'old': record._format_field_value(field_name, value),
                        'new': None
                    }
                
                records_info.append({
                    'id': record.id,
                    'name': record.display_name,
                    'field_changes': field_changes,
                    'related_partner_id': record._get_related_partner_id()
                })
                
            except Exception as e:
                _logger.error(f"Failed to prepare audit info for {record._name}#{record.id}: {str(e)}")
        
        # Perform the deletion
        result = super(AuditMixin, self).unlink()
        
        # Create audit logs after deletion
        for info in records_info:
            try:
                description = f"Deleted {self._description or self._name}: {info['name']}"
                
                # Create audit log using the class method since record is deleted
                self.env['ams.audit.log'].create_audit_log(
                    model_name=self._name,
                    record_id=info['id'],
                    action='unlink',
                    description=description,
                    field_changes=info['field_changes'],
                    category=self._get_audit_category(),
                    risk_level='high',  # Deletions are always high risk
                    is_sensitive=self._is_sensitive_change(info['field_changes']),
                    privacy_impact=self._has_privacy_impact(info['field_changes']),
                    related_partner_id=info['related_partner_id']
                )
                
            except Exception as e:
                _logger.error(f"Failed to create audit log for deleted {self._name}#{info['id']}: {str(e)}")
        
        return result
    
    def action_view_audit_logs(self):
        """Action to view audit logs for this record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Audit Logs'),
            'res_model': 'ams.audit.log',
            'view_mode': 'tree,form',
            'domain': [('model_name', '=', self._name), ('record_id', '=', self.id)],
            'context': {
                'default_model_name': self._name,
                'default_record_id': self.id,
                'default_record_name': self.display_name,
            },
            'target': 'current',
        }
    
    def get_audit_summary(self, days=30):
        """Get audit summary for this record."""
        self.ensure_one()
        return self.env['ams.audit.log'].get_audit_summary(
            model_name=self._name,
            record_id=self.id,
            days=days
        )