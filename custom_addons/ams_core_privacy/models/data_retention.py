# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DataRetentionPolicy(models.Model):
    _name = 'ams.data.retention.policy'
    _description = 'Data Retention Policies'
    _order = 'sequence, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ===== BASIC INFORMATION =====
    name = fields.Char(
        string='Policy Name',
        required=True,
        tracking=True,
        help="Name of the data retention policy"
    )

    code = fields.Char(
        string='Policy Code',
        help="Short code for the policy"
    )

    description = fields.Text(
        string='Description',
        help="Detailed description of the retention policy"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for applying policies"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="Uncheck to deactivate this policy"
    )

    # ===== POLICY SCOPE =====
    model_name = fields.Selection(
        '_get_model_selection',
        string='Applies to Model',
        required=True,
        tracking=True,
        help="Which data model this policy applies to"
    )

    domain_filter = fields.Text(
        string='Domain Filter',
        default="[]",
        help="Odoo domain filter to specify which records (JSON format)"
    )

    # ===== RETENTION SETTINGS =====
    retention_period_type = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Period Type', required=True, default='years', tracking=True)

    retention_period_value = fields.Integer(
        string='Retention Period',
        required=True,
        default=7,
        tracking=True,
        help="Number of periods to retain data"
    )

    retention_period_display = fields.Char(
        string='Retention Period',
        compute='_compute_retention_period_display',
        help="Human readable retention period"
    )

    # ===== TRIGGER CONDITIONS =====
    trigger_field = fields.Selection(
        '_get_date_field_selection',
        string='Trigger Field',
        required=True,
        help="Date field that determines when retention period starts"
    )

    additional_conditions = fields.Text(
        string='Additional Conditions',
        help="Additional conditions that must be met for deletion"
    )

    # ===== REGULATORY BASIS =====
    regulatory_basis = fields.Selection([
        ('gdpr', 'GDPR (EU)'),
        ('ccpa', 'CCPA (California)'),
        ('hipaa', 'HIPAA (Healthcare)'),
        ('sox', 'Sarbanes-Oxley'),
        ('association_rules', 'Association Rules'),
        ('legal_requirement', 'Legal Requirement'),
        ('business_practice', 'Business Practice'),
    ], string='Regulatory Basis', tracking=True)

    legal_citation = fields.Text(
        string='Legal Citation',
        help="Specific legal or regulatory citation"
    )

    # ===== EXECUTION SETTINGS =====
    auto_execute = fields.Boolean(
        string='Auto Execute',
        default=False,
        tracking=True,
        help="Automatically delete records when retention period expires"
    )

    require_approval = fields.Boolean(
        string='Require Approval',
        default=True,
        tracking=True,
        help="Require manual approval before deletion"
    )

    notification_days_before = fields.Integer(
        string='Notification Days',
        default=30,
        help="Days before deletion to send notification"
    )

    # ===== EXCEPTIONS =====
    legal_hold_exemption = fields.Boolean(
        string='Legal Hold Exemption',
        default=True,
        help="Exempt records under legal hold from deletion"
    )

    member_status_exemptions = fields.Char(
        string='Member Status Exemptions',
        help="Member statuses exempt from deletion (comma-separated)"
    )

    # ===== STATISTICS =====
    records_eligible = fields.Integer(
        string='Records Eligible',
        compute='_compute_eligible_records',
        help="Number of records eligible for deletion"
    )

    last_executed = fields.Datetime(
        string='Last Executed',
        readonly=True,
        help="When this policy was last executed"
    )

    records_deleted_last_run = fields.Integer(
        string='Records Deleted (Last Run)',
        readonly=True,
        help="Number of records deleted in last execution"
    )

    total_records_deleted = fields.Integer(
        string='Total Records Deleted',
        readonly=True,
        help="Total number of records deleted by this policy"
    )

    # ===== METADATA =====
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        help="User who approved this policy"
    )

    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        help="When this policy was approved"
    )

    @api.model
    def _get_model_selection(self):
        """Get list of models for retention policies"""
        # Core AMS models that commonly need retention policies
        models = [
            ('res.partner', 'Partners/Members'),
            ('ams.member.profile', 'Member Profiles'),
            ('ams.privacy.consent', 'Privacy Consents'),
            ('ams.audit.log', 'Audit Logs'),
            ('mail.message', 'Messages'),
            ('mail.mail', 'Emails'),
        ]
        
        # Add other installed models
        try:
            installed_models = self.env['ir.model'].search([
                ('model', 'like', 'ams.%'),
                ('transient', '=', False)
            ])
            for model in installed_models:
                if (model.model, model.name) not in models:
                    models.append((model.model, model.name))
        except:
            pass
        
        return models

    @api.model
    def _get_date_field_selection(self):
        """Get common date fields for trigger conditions"""
        return [
            ('create_date', 'Creation Date'),
            ('write_date', 'Last Update Date'),
            ('member_since', 'Member Since Date'),
            ('last_activity_date', 'Last Activity Date'),
            ('expiry_date', 'Expiry Date'),
            ('withdrawal_date', 'Withdrawal Date'),
            ('timestamp', 'Timestamp'),
        ]

    @api.depends('retention_period_type', 'retention_period_value')
    def _compute_retention_period_display(self):
        """Compute human readable retention period"""
        for policy in self:
            if policy.retention_period_value and policy.retention_period_type:
                unit = policy.retention_period_type
                value = policy.retention_period_value
                if value == 1:
                    unit = unit.rstrip('s')  # Remove plural
                policy.retention_period_display = f"{value} {unit}"
            else:
                policy.retention_period_display = ""

    @api.depends('model_name', 'domain_filter', 'trigger_field', 'retention_period_type', 'retention_period_value')
    def _compute_eligible_records(self):
        """Compute number of records eligible for deletion"""
        for policy in self:
            try:
                if policy.model_name and policy.trigger_field:
                    count = policy._get_eligible_records_count()
                    policy.records_eligible = count
                else:
                    policy.records_eligible = 0
            except Exception as e:
                _logger.warning(f"Failed to compute eligible records for policy {policy.name}: {e}")
                policy.records_eligible = 0

    def _get_eligible_records_count(self):
        """Get count of records eligible for deletion"""
        self.ensure_one()
        
        if not self.model_name:
            return 0
        
        # Calculate cutoff date
        cutoff_date = self._calculate_cutoff_date()
        if not cutoff_date:
            return 0
        
        # Build domain
        try:
            domain = eval(self.domain_filter) if self.domain_filter else []
        except:
            domain = []
        
        # Add date condition
        domain.append((self.trigger_field, '<', cutoff_date))
        
        # Add exemptions
        if self.member_status_exemptions:
            exemptions = [s.strip() for s in self.member_status_exemptions.split(',')]
            if self.model_name == 'res.partner':
                domain.append(('member_status', 'not in', exemptions))
        
        # Add legal hold exemption
        if self.legal_hold_exemption and self.model_name == 'res.partner':
            domain.append(('legal_hold', '!=', True))
        
        try:
            return self.env[self.model_name].search_count(domain)
        except Exception as e:
            _logger.warning(f"Error counting eligible records: {e}")
            return 0

    def _calculate_cutoff_date(self):
        """Calculate the cutoff date for retention"""
        self.ensure_one()
        
        if not self.retention_period_value or not self.retention_period_type:
            return None
        
        today = datetime.now()
        
        if self.retention_period_type == 'days':
            cutoff = today - timedelta(days=self.retention_period_value)
        elif self.retention_period_type == 'months':
            # Approximate months as 30 days
            cutoff = today - timedelta(days=self.retention_period_value * 30)
        elif self.retention_period_type == 'years':
            # Approximate years as 365 days
            cutoff = today - timedelta(days=self.retention_period_value * 365)
        else:
            return None
        
        return cutoff

    @api.constrains('retention_period_value')
    def _check_retention_period(self):
        """Validate retention period"""
        for policy in self:
            if policy.retention_period_value <= 0:
                raise ValidationError(_("Retention period must be positive"))
            if policy.retention_period_value > 100:
                raise ValidationError(_("Retention period cannot exceed 100 years"))

    @api.constrains('domain_filter')
    def _check_domain_filter(self):
        """Validate domain filter syntax"""
        for policy in self:
            if policy.domain_filter:
                try:
                    domain = eval(policy.domain_filter)
                    if not isinstance(domain, list):
                        raise ValidationError(_("Domain filter must be a valid list"))
                except Exception as e:
                    raise ValidationError(_("Invalid domain filter syntax: %s") % str(e))

    def action_preview_eligible_records(self):
        """Preview records eligible for deletion"""
        self.ensure_one()
        
        if not self.model_name:
            raise UserError(_("Please specify a model for this policy"))
        
        # Calculate cutoff date
        cutoff_date = self._calculate_cutoff_date()
        if not cutoff_date:
            raise UserError(_("Cannot calculate cutoff date"))
        
        # Build domain
        try:
            domain = eval(self.domain_filter) if self.domain_filter else []
        except:
            domain = []
        
        domain.append((self.trigger_field, '<', cutoff_date))
        
        # Add exemptions
        if self.member_status_exemptions:
            exemptions = [s.strip() for s in self.member_status_exemptions.split(',')]
            if self.model_name == 'res.partner':
                domain.append(('member_status', 'not in', exemptions))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Records Eligible for Deletion: {self.name}',
            'res_model': self.model_name,
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
            'help': f"<p>Records eligible for deletion under policy: {self.name}</p>"
                   f"<p>Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}</p>"
                   f"<p>Retention period: {self.retention_period_display}</p>",
        }

    def action_execute_policy(self):
        """Execute the retention policy"""
        self.ensure_one()
        
        if not self.active:
            raise UserError(_("Cannot execute inactive policy"))
        
        if self.require_approval and not self.approved_by:
            raise UserError(_("This policy requires approval before execution"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Execute Retention Policy'),
            'res_model': 'ams.data.retention.execute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_policy_id': self.id},
        }

    def action_approve_policy(self):
        """Approve the policy for execution"""
        self.ensure_one()
        
        if not self.env.user.has_group('ams_core_base.group_ams_admin'):
            raise UserError(_("Only administrators can approve retention policies"))
        
        self.write({
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        
        # Log approval
        self.message_post(
            body=_("Retention policy approved by %s") % self.env.user.name,
            subject=_("Policy Approved"),
        )
        
        return True

    def _execute_deletion(self, dry_run=False):
        """Execute the actual deletion"""
        self.ensure_one()
        
        # Calculate cutoff date
        cutoff_date = self._calculate_cutoff_date()
        if not cutoff_date:
            return 0, []
        
        # Build domain
        try:
            domain = eval(self.domain_filter) if self.domain_filter else []
        except:
            domain = []
        
        domain.append((self.trigger_field, '<', cutoff_date))
        
        # Add exemptions
        if self.member_status_exemptions:
            exemptions = [s.strip() for s in self.member_status_exemptions.split(',')]
            if self.model_name == 'res.partner':
                domain.append(('member_status', 'not in', exemptions))
        
        # Add legal hold exemption
        if self.legal_hold_exemption and self.model_name == 'res.partner':
            domain.append(('legal_hold', '!=', True))
        
        # Find records
        try:
            records = self.env[self.model_name].search(domain)
        except Exception as e:
            _logger.error(f"Error finding records for deletion: {e}")
            return 0, [str(e)]
        
        deleted_count = len(records)
        errors = []
        
        if not dry_run and records:
            try:
                # Log before deletion
                for record in records:
                    self.env['ams.audit.log'].sudo().create({
                        'model_name': record._name,
                        'record_id': record.id,
                        'operation': 'unlink',
                        'description': f'Deleted by retention policy: {self.name}',
                        'user_id': self.env.user.id,
                        'data': str({
                            'policy': self.name,
                            'cutoff_date': cutoff_date.isoformat(),
                            'record_name': record.display_name,
                        }),
                        'timestamp': fields.Datetime.now(),
                        'risk_level': 'high',
                        'privacy_impact': True,
                    })
                
                # Delete records
                records.unlink()
                
                # Update policy statistics
                self.write({
                    'last_executed': fields.Datetime.now(),
                    'records_deleted_last_run': deleted_count,
                    'total_records_deleted': self.total_records_deleted + deleted_count,
                })
                
                _logger.info(f"Retention policy {self.name} deleted {deleted_count} records")
                
            except Exception as e:
                errors.append(str(e))
                _logger.error(f"Error executing retention policy {self.name}: {e}")
        
        return deleted_count, errors

    @api.model
    def run_scheduled_policies(self):
        """Run all active auto-execute policies"""
        policies = self.search([
            ('active', '=', True),
            ('auto_execute', '=', True),
        ])
        
        total_deleted = 0
        for policy in policies:
            try:
                deleted_count, errors = policy._execute_deletion()
                total_deleted += deleted_count
                
                if errors:
                    policy.message_post(
                        body=_("Errors during execution: %s") % ', '.join(errors),
                        subject=_("Policy Execution Errors"),
                    )
            except Exception as e:
                _logger.error(f"Failed to execute policy {policy.name}: {e}")
        
        return total_deleted

    def name_get(self):
        """Override name_get for better display"""
        result = []
        for policy in self:
            name = policy.name
            if policy.retention_period_display:
                name += f" ({policy.retention_period_display})"
            if not policy.active:
                name += " (Archived)"
            result.append((policy.id, name))
        return result


class DataRetentionExecution(models.Model):
    _name = 'ams.data.retention.execution'
    _description = 'Data Retention Execution Log'
    _order = 'execution_date desc'
    _rec_name = 'display_name'

    # ===== BASIC INFORMATION =====
    policy_id = fields.Many2one(
        'ams.data.retention.policy',
        string='Policy',
        required=True,
        ondelete='cascade'
    )

    execution_date = fields.Datetime(
        string='Execution Date',
        required=True,
        default=fields.Datetime.now
    )

    executed_by = fields.Many2one(
        'res.users',
        string='Executed By',
        required=True,
        default=lambda self: self.env.user
    )

    # ===== EXECUTION RESULTS =====
    records_found = fields.Integer(
        string='Records Found',
        help="Number of records found eligible for deletion"
    )

    records_deleted = fields.Integer(
        string='Records Deleted',
        help="Number of records actually deleted"
    )

    execution_status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ], string='Status', required=True, default='success')

    error_messages = fields.Text(
        string='Error Messages',
        help="Any error messages during execution"
    )

    # ===== COMPUTED FIELDS =====
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('policy_id', 'execution_date')
    def _compute_display_name(self):
        """Compute display name"""
        for execution in self:
            if execution.policy_id and execution.execution_date:
                date_str = execution.execution_date.strftime('%Y-%m-%d %H:%M')
                execution.display_name = f"{execution.policy_id.name} - {date_str}"
            else:
                execution.display_name = "New Execution"