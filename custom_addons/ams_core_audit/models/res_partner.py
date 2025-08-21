# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extend res.partner with audit trail functionality and smart buttons."""
    
    _inherit = ['res.partner', 'ams.audit.mixin']
    
    # Audit configuration for partner model
    _audit_enabled = True
    _audit_category = 'member_data'
    _audit_sensitive_fields = [
        'date_of_birth', 'gender', 'nationality', 'tax_id_registration',
        'license_certification_number', 'alternate_emails'
    ]
    _audit_privacy_fields = [
        'email', 'phone', 'mobile', 'street', 'street2', 'city', 'zip',
        'date_of_birth', 'gender', 'nationality', 'alternate_emails'
    ]
    _audit_exclude_fields = [
        'write_date', 'write_uid', 'create_date', 'create_uid', '__last_update',
        'message_ids', 'activity_ids', 'message_follower_ids'
    ]
    
    # Additional audit-related computed fields specific to partners
    sensitive_audit_count = fields.Integer(
        string='Sensitive Audit Count',
        compute='_compute_sensitive_audit_count',
        help='Number of audit entries involving sensitive data'
    )
    
    privacy_audit_count = fields.Integer(
        string='Privacy Audit Count',
        compute='_compute_privacy_audit_count',
        help='Number of audit entries with privacy impact'
    )
    
    last_profile_change = fields.Datetime(
        string='Last Profile Change',
        compute='_compute_last_profile_change',
        help='Date of last significant profile change'
    )
    
    @api.depends('id')
    def _compute_sensitive_audit_count(self):
        """Compute the number of sensitive audit log entries."""
        for partner in self:
            if partner.id:
                count = self.env['ams.audit.log'].search_count([
                    ('model_name', '=', 'res.partner'),
                    ('record_id', '=', partner.id),
                    ('is_sensitive', '=', True)
                ])
                partner.sensitive_audit_count = count
            else:
                partner.sensitive_audit_count = 0
    
    @api.depends('id')
    def _compute_privacy_audit_count(self):
        """Compute the number of privacy-related audit log entries."""
        for partner in self:
            if partner.id:
                count = self.env['ams.audit.log'].search_count([
                    ('model_name', '=', 'res.partner'),
                    ('record_id', '=', partner.id),
                    ('privacy_impact', '=', True)
                ])
                partner.privacy_audit_count = count
            else:
                partner.privacy_audit_count = 0
    
    @api.depends('id')
    def _compute_last_profile_change(self):
        """Compute the date of last significant profile change."""
        for partner in self:
            if partner.id:
                # Look for write operations (excluding system fields)
                last_log = self.env['ams.audit.log'].search([
                    ('model_name', '=', 'res.partner'),
                    ('record_id', '=', partner.id),
                    ('action', '=', 'write')
                ], order='timestamp desc', limit=1)
                partner.last_profile_change = last_log.timestamp if last_log else False
            else:
                partner.last_profile_change = False
    
    def _get_audit_category(self):
        """Override to provide more specific categorization for partners."""
        if self.is_member:
            return 'member_data'
        elif self.is_company:
            return 'organization_data'
        else:
            return 'contact_data'
    
    def _determine_risk_level(self, action, field_changes=None):
        """Override to provide partner-specific risk assessment."""
        # Start with base risk level
        risk_level = super()._determine_risk_level(action, field_changes)
        
        # Increase risk for member-related changes
        if self.is_member and field_changes:
            member_critical_fields = [
                'member_id', 'member_status', 'is_member', 'member_since',
                'license_certification_number', 'professional_designation_ids'
            ]
            if any(field in member_critical_fields for field in field_changes.keys()):
                if risk_level == 'low':
                    risk_level = 'medium'
                elif risk_level == 'medium':
                    risk_level = 'high'
        
        # Increase risk for email changes (important for member communications)
        if field_changes and 'email' in field_changes:
            if risk_level == 'low':
                risk_level = 'medium'
        
        return risk_level
    
    def action_view_audit_trail(self):
        """Action to view complete audit trail for this partner."""
        self.ensure_one()
        
        # Include audit logs for related records
        domain = [
            '|',
            '&', ('model_name', '=', 'res.partner'), ('record_id', '=', self.id),
            ('related_partner_id', '=', self.id)
        ]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Audit Trail - %s') % self.name,
            'res_model': 'ams.audit.log',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_related_partner_id': self.id,
                'search_default_group_model': 1,
                'search_default_this_month': 1,
            },
            'target': 'current',
        }
    
    def action_view_sensitive_audit_logs(self):
        """Action to view sensitive data audit logs for this partner."""
        self.ensure_one()
        
        domain = [
            '|',
            '&', ('model_name', '=', 'res.partner'), ('record_id', '=', self.id),
            ('related_partner_id', '=', self.id),
            ('is_sensitive', '=', True)
        ]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sensitive Data Audit - %s') % self.name,
            'res_model': 'ams.audit.log',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_related_partner_id': self.id,
                'search_default_high_risk': 1,
            },
            'target': 'current',
        }
    
    def action_view_privacy_audit_logs(self):
        """Action to view privacy-related audit logs for this partner."""
        self.ensure_one()
        
        domain = [
            '|',
            '&', ('model_name', '=', 'res.partner'), ('record_id', '=', self.id),
            ('related_partner_id', '=', self.id),
            ('privacy_impact', '=', True)
        ]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Privacy Audit - %s') % self.name,
            'res_model': 'ams.audit.log',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'default_related_partner_id': self.id,
                'search_default_privacy_impact': 1,
            },
            'target': 'current',
        }
    
    def create_audit_event(self, event_type, description, notes=None, risk_level='medium'):
        """Create a custom audit event for this partner."""
        self.ensure_one()
        
        return self.env['ams.audit.log'].create_audit_log(
            model_name=self._name,
            record_id=self.id,
            action='other',
            description=description,
            category=self._get_audit_category(),
            risk_level=risk_level,
            related_partner_id=self.id,
            notes=notes
        )
    
    def get_audit_compliance_status(self):
        """Get audit compliance status for this partner."""
        self.ensure_one()
        
        # Get recent audit activity (last 90 days)
        recent_logs = self.env['ams.audit.log'].search([
            '|',
            '&', ('model_name', '=', 'res.partner'), ('record_id', '=', self.id),
            ('related_partner_id', '=', self.id),
            ('timestamp', '>=', fields.Datetime.now() - fields.timedelta(days=90))
        ])
        
        # Check for unreviewed high-risk entries
        unreviewed_high_risk = recent_logs.filtered(
            lambda l: l.risk_level in ['high', 'critical'] and 
                     l.requires_review and not l.reviewed
        )
        
        # Check for sensitive data access
        sensitive_access = recent_logs.filtered('is_sensitive')
        
        # Check for privacy-impacting changes
        privacy_changes = recent_logs.filtered('privacy_impact')
        
        status = {
            'total_entries': len(recent_logs),
            'unreviewed_high_risk': len(unreviewed_high_risk),
            'sensitive_access_count': len(sensitive_access),
            'privacy_changes_count': len(privacy_changes),
            'compliance_score': 100,  # Start with perfect score
            'issues': [],
            'recommendations': []
        }
        
        # Reduce compliance score based on issues
        if unreviewed_high_risk:
            status['compliance_score'] -= 30
            status['issues'].append(f"{len(unreviewed_high_risk)} unreviewed high-risk entries")
            status['recommendations'].append("Review and approve high-risk audit entries")
        
        if len(sensitive_access) > 10:  # Threshold for excessive sensitive access
            status['compliance_score'] -= 20
            status['issues'].append("Excessive sensitive data access")
            status['recommendations'].append("Review sensitive data access patterns")
        
        if len(privacy_changes) > 5:  # Threshold for frequent privacy changes
            status['compliance_score'] -= 15
            status['issues'].append("Frequent privacy-related changes")
            status['recommendations'].append("Ensure proper privacy change procedures")
        
        # Determine overall status
        if status['compliance_score'] >= 90:
            status['overall_status'] = 'compliant'
        elif status['compliance_score'] >= 70:
            status['overall_status'] = 'warning'
        else:
            status['overall_status'] = 'non_compliant'
        
        return status
    
    @api.model
    def _audit_member_status_change(self, partner_id, old_status, new_status, reason=None):
        """Create audit log for member status changes."""
        partner = self.browse(partner_id)
        description = f"Member status changed from '{old_status}' to '{new_status}'"
        
        field_changes = {
            'member_status': {
                'old': old_status,
                'new': new_status
            }
        }
        
        notes = f"Status change reason: {reason}" if reason else None
        
        return self.env['ams.audit.log'].create_audit_log(
            model_name='res.partner',
            record_id=partner_id,
            action='write',
            description=description,
            field_changes=field_changes,
            category='member_data',
            risk_level='medium',
            related_partner_id=partner_id,
            notes=notes
        )
    
    @api.model
    def _audit_data_export(self, partner_ids, export_type, exported_fields, user_justification=None):
        """Create audit logs for data export operations."""
        partners = self.browse(partner_ids)
        
        for partner in partners:
            description = f"Data exported: {export_type} (fields: {', '.join(exported_fields)})"
            
            notes = f"Export justification: {user_justification}" if user_justification else None
            
            self.env['ams.audit.log'].create_audit_log(
                model_name='res.partner',
                record_id=partner.id,
                action='export',
                description=description,
                category='privacy',
                risk_level='medium',
                is_sensitive=any(field in partner._get_audit_sensitive_fields() for field in exported_fields),
                privacy_impact=any(field in partner._get_audit_privacy_fields() for field in exported_fields),
                related_partner_id=partner.id,
                notes=notes
            )
    
    def write(self, vals):
        """Override write to add partner-specific audit logic."""
        # Check for member status changes
        if 'member_status' in vals:
            for partner in self:
                old_status = partner.member_status
                new_status = vals['member_status']
                if old_status != new_status:
                    # This will be logged by the mixin, but we can add additional context
                    pass
        
        # Check for email changes (critical for member communications)
        if 'email' in vals:
            for partner in self:
                if partner.email != vals['email']:
                    # Create additional audit entry for email changes
                    self.env['ams.audit.log'].create_audit_log(
                        model_name=self._name,
                        record_id=partner.id,
                        action='write',
                        description=f"Email changed from '{partner.email}' to '{vals['email']}'",
                        category='member_data',
                        risk_level='medium',
                        privacy_impact=True,
                        related_partner_id=partner.id,
                        notes="Email address is critical for member communications"
                    )
        
        return super(ResPartner, self).write(vals)