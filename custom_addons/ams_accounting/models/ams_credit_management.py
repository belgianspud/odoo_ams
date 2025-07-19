# -*- coding: utf-8 -*-
#############################################################################
#
#    AMS Accounting - Credit Management System
#    Comprehensive credit hold and usage tracking for member accounts
#
#############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSCreditHold(models.Model):
    """
    Model for managing credit holds and reservations on member accounts
    """
    _name = 'ams.credit.hold'
    _description = 'AMS Credit Hold'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'hold_number'

    # ========================
    # BASIC INFORMATION
    # ========================
    
    hold_number = fields.Char('Hold Number', required=True, copy=False, 
        readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', 'Member', required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', 
        readonly=True)
    
    # Credit Limit Reference
    credit_limit_id = fields.Many2one('ams.credit.limit', 'Credit Limit', 
        domain="[('partner_id', '=', partner_id)]")
    
    # ========================
    # HOLD DETAILS
    # ========================
    
    # Hold Amount and Type
    hold_amount = fields.Float('Hold Amount', required=True, tracking=True)
    original_hold_amount = fields.Float('Original Hold Amount', readonly=True)
    remaining_hold_amount = fields.Float('Remaining Hold Amount', 
        compute='_compute_remaining_amount', store=True)
    
    hold_type = fields.Selection([
        ('authorization', 'Payment Authorization'),
        ('reservation', 'Credit Reservation'),
        ('security', 'Security Hold'),
        ('dispute', 'Dispute Hold'),
        ('collection', 'Collection Hold'),
        ('compliance', 'Compliance Hold'),
        ('fraud_prevention', 'Fraud Prevention'),
        ('manual', 'Manual Hold'),
        ('system', 'System Hold'),
        ('other', 'Other')
    ], string='Hold Type', default='reservation', required=True, tracking=True)
    
    # Hold Reason and Description
    reason_category = fields.Selection([
        ('payment_authorization', 'Payment Authorization'),
        ('subscription_upgrade', 'Subscription Upgrade'),
        ('service_reservation', 'Service Reservation'),
        ('payment_dispute', 'Payment Dispute'),
        ('chargeback', 'Chargeback'),
        ('overdue_payment', 'Overdue Payment'),
        ('fraud_alert', 'Fraud Alert'),
        ('compliance_check', 'Compliance Check'),
        ('manual_review', 'Manual Review'),
        ('system_maintenance', 'System Maintenance'),
        ('other', 'Other')
    ], string='Reason Category', required=True, tracking=True)
    
    description = fields.Text('Hold Description', required=True, tracking=True)
    internal_notes = fields.Text('Internal Notes')
    
    # ========================
    # DATE MANAGEMENT
    # ========================
    
    # Hold Timing
    hold_date = fields.Datetime('Hold Date', required=True, 
        default=fields.Datetime.now, tracking=True)
    release_date = fields.Datetime('Release Date', tracking=True)
    expiry_date = fields.Datetime('Auto-Release Date',
        help="Date when hold will be automatically released")
    
    # Duration Settings
    hold_duration_type = fields.Selection([
        ('indefinite', 'Indefinite'),
        ('temporary', 'Temporary'),
        ('auto_release', 'Auto Release')
    ], string='Duration Type', default='temporary', tracking=True)
    
    hold_duration_days = fields.Integer('Hold Duration (Days)', default=30,
        help="Duration for temporary holds")
    
    # ========================
    # AUTHORIZATION AND APPROVAL
    # ========================
    
    # Authorization Tracking
    authorized_by = fields.Many2one('res.users', 'Authorized By', 
        required=True, default=lambda self: self.env.user, tracking=True)
    authorization_date = fields.Datetime('Authorization Date', 
        default=fields.Datetime.now, tracking=True)
    authorization_notes = fields.Text('Authorization Notes')
    
    # Release Authorization
    release_authorized_by = fields.Many2one('res.users', 'Release Authorized By', tracking=True)
    release_authorization_date = fields.Datetime('Release Authorization Date', tracking=True)
    release_notes = fields.Text('Release Notes')
    
    # Approval Requirements
    requires_manager_approval = fields.Boolean('Requires Manager Approval', 
        compute='_compute_approval_requirements', store=True)
    approved_by = fields.Many2one('res.users', 'Approved By', tracking=True)
    approval_date = fields.Datetime('Approval Date', tracking=True)
    
    # ========================
    # STATUS TRACKING
    # ========================
    
    # Hold Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('partial_release', 'Partially Released'),
        ('released', 'Released'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Usage Tracking
    used_amount = fields.Float('Used Amount', compute='_compute_usage', store=True)
    usage_count = fields.Integer('Usage Count', compute='_compute_usage', store=True)
    
    # ========================
    # RELATED TRANSACTIONS
    # ========================
    
    # Related Records
    invoice_id = fields.Many2one('account.move', 'Related Invoice',
        help="Invoice that triggered this hold")
    payment_id = fields.Many2one('account.payment', 'Related Payment',
        help="Payment that triggered this hold")
    subscription_id = fields.Many2one('ams.subscription', 'Related Subscription',
        help="Subscription that triggered this hold")
    
    # Hold Usage Records
    usage_ids = fields.One2many('ams.credit.hold.usage', 'hold_id', 'Hold Usage')
    
    # Source and Reference
    source_document = fields.Reference([
        ('account.move', 'Invoice'),
        ('account.payment', 'Payment'),
        ('ams.subscription', 'Subscription'),
        ('ams.subscription.modification', 'Subscription Modification'),
    ], string='Source Document')
    
    external_reference = fields.Char('External Reference',
        help="Reference from external system (payment processor, etc.)")
    
    # ========================
    # ESCALATION AND ALERTS
    # ========================
    
    # Alert Configuration
    alert_before_expiry_days = fields.Integer('Alert Before Expiry (Days)', default=3)
    alert_sent = fields.Boolean('Alert Sent', default=False)
    alert_date = fields.Datetime('Alert Date')
    
    # Escalation Settings
    escalation_required = fields.Boolean('Escalation Required', default=False)
    escalated_to = fields.Many2one('res.users', 'Escalated To')
    escalation_date = fields.Datetime('Escalation Date')
    escalation_reason = fields.Text('Escalation Reason')
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    @api.depends('hold_amount', 'used_amount')
    def _compute_remaining_amount(self):
        for hold in self:
            hold.remaining_hold_amount = hold.hold_amount - hold.used_amount
    
    @api.depends('usage_ids', 'usage_ids.amount')
    def _compute_usage(self):
        for hold in self:
            usage_records = hold.usage_ids.filtered(lambda u: u.state == 'applied')
            hold.used_amount = sum(usage_records.mapped('amount'))
            hold.usage_count = len(usage_records)
    
    @api.depends('hold_amount', 'hold_type')
    def _compute_approval_requirements(self):
        for hold in self:
            # Require manager approval for large holds or sensitive types
            large_amount = hold.hold_amount > 1000.0  # Configurable threshold
            sensitive_type = hold.hold_type in ['security', 'dispute', 'fraud_prevention']
            
            hold.requires_manager_approval = large_amount or sensitive_type
    
    # ========================
    # CRUD OPERATIONS
    # ========================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('hold_number', _('New')) == _('New'):
                vals['hold_number'] = self.env['ir.sequence'].next_by_code(
                    'ams.credit.hold') or _('New')
            
            # Set original hold amount
            if 'hold_amount' in vals:
                vals['original_hold_amount'] = vals['hold_amount']
        
        holds = super().create(vals_list)
        
        for hold in holds:
            # Set expiry date for temporary holds
            if hold.hold_duration_type == 'temporary' and hold.hold_duration_days > 0:
                hold.expiry_date = hold.hold_date + timedelta(days=hold.hold_duration_days)
            elif hold.hold_duration_type == 'auto_release' and hold.hold_duration_days > 0:
                hold.expiry_date = hold.hold_date + timedelta(days=hold.hold_duration_days)
            
            # Check approval requirements
            if hold.requires_manager_approval:
                hold.state = 'pending_approval'
                hold._create_approval_activity()
        
        return holds
    
    def _create_approval_activity(self):
        """Create approval activity for manager"""
        manager_user = self._get_manager_user()
        if manager_user:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Credit Hold Approval Required: {self.hold_number}',
                note=f'Credit hold of {self.hold_amount} requires manager approval.\n'
                     f'Type: {self.hold_type}\nReason: {self.description}',
                user_id=manager_user.id
            )
    
    def _get_manager_user(self):
        """Get manager user for approval"""
        manager_group = self.env.ref('ams_accounting.group_ams_accounting_manager', False)
        if manager_group and manager_group.users:
            return manager_group.users[0]
        return self.env.user
    
    # ========================
    # WORKFLOW ACTIONS
    # ========================
    
    def action_activate(self):
        """Activate the credit hold"""
        for hold in self:
            if hold.state not in ['draft', 'pending_approval']:
                raise UserError(_('Only draft or pending holds can be activated.'))
            
            if hold.requires_manager_approval and not hold.approved_by:
                raise UserError(_('Manager approval required before activation.'))
            
            # Validate credit availability
            if not hold._validate_credit_availability():
                raise UserError(_('Insufficient credit available for hold.'))
            
            hold.state = 'active'
            hold.message_post(body=_('Credit hold activated.'))
            
            # Create credit usage record
            hold._create_usage_record('hold_applied', hold.hold_amount, 
                'Credit hold applied')
    
    def action_approve(self):
        """Approve the credit hold"""
        for hold in self:
            if hold.state != 'pending_approval':
                raise UserError(_('Only pending holds can be approved.'))
            
            hold.approved_by = self.env.user.id
            hold.approval_date = fields.Datetime.now()
            hold.state = 'draft'  # Return to draft for activation
            
            hold.message_post(body=_('Credit hold approved by %s.') % self.env.user.name)
            
            # Auto-activate if no other requirements
            if not hold.requires_manager_approval or hold.approved_by:
                hold.action_activate()
    
    def action_reject(self):
        """Reject the credit hold"""
        for hold in self:
            if hold.state != 'pending_approval':
                raise UserError(_('Only pending holds can be rejected.'))
            
            hold.state = 'cancelled'
            hold.message_post(body=_('Credit hold rejected by %s.') % self.env.user.name)
    
    def action_release(self, release_amount=None, reason=None):
        """Release the credit hold (full or partial)"""
        for hold in self:
            if hold.state not in ['active', 'partial_release']:
                raise UserError(_('Only active holds can be released.'))
            
            if release_amount is None:
                release_amount = hold.remaining_hold_amount
            
            if release_amount > hold.remaining_hold_amount:
                raise UserError(_('Cannot release more than remaining hold amount.'))
            
            # Create release usage record
            hold._create_usage_record('hold_released', release_amount, 
                reason or 'Credit hold released')
            
            # Update hold status
            if hold.remaining_hold_amount <= 0.01:  # Allow for rounding
                hold.state = 'released'
                hold.release_date = fields.Datetime.now()
                hold.release_authorized_by = self.env.user.id
                hold.release_authorization_date = fields.Datetime.now()
            else:
                hold.state = 'partial_release'
            
            hold.message_post(
                body=_('Credit hold released: %s') % release_amount)
    
    def action_expire(self):
        """Expire the credit hold"""
        for hold in self:
            if hold.state not in ['active', 'partial_release']:
                return  # Already processed
            
            # Release any remaining hold amount
            if hold.remaining_hold_amount > 0:
                hold.action_release(hold.remaining_hold_amount, 'Automatic expiry')
            
            hold.state = 'expired'
            hold.message_post(body=_('Credit hold expired automatically.'))
    
    def action_cancel(self):
        """Cancel the credit hold"""
        for hold in self:
            if hold.state in ['released', 'expired']:
                raise UserError(_('Cannot cancel released or expired holds.'))
            
            # Release any used amount
            if hold.used_amount > 0:
                hold.action_release(hold.remaining_hold_amount, 'Hold cancelled')
            
            hold.state = 'cancelled'
            hold.message_post(body=_('Credit hold cancelled.'))
    
    def action_extend_expiry(self, additional_days):
        """Extend the expiry date of the hold"""
        for hold in self:
            if hold.state not in ['active', 'partial_release']:
                raise UserError(_('Only active holds can be extended.'))
            
            if hold.expiry_date:
                hold.expiry_date = hold.expiry_date + timedelta(days=additional_days)
            else:
                hold.expiry_date = fields.Datetime.now() + timedelta(days=additional_days)
            
            hold.message_post(
                body=_('Credit hold extended by %d days.') % additional_days)
    
    # ========================
    # BUSINESS LOGIC
    # ========================
    
    def _validate_credit_availability(self):
        """Validate that credit is available for the hold"""
        if not self.credit_limit_id:
            return True  # No credit limit set
        
        # Check if credit limit has sufficient available credit
        available_credit = self.credit_limit_id.credit_available
        return available_credit >= self.hold_amount
    
    def _create_usage_record(self, usage_type, amount, description):
        """Create a credit hold usage record"""
        usage_vals = {
            'hold_id': self.id,
            'usage_type': usage_type,
            'amount': amount,
            'description': description,
            'usage_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'state': 'applied'
        }
        
        return self.env['ams.credit.hold.usage'].create(usage_vals)
    
    def use_hold_amount(self, amount, description, source_document=None):
        """Use a portion of the hold amount"""
        if self.state not in ['active', 'partial_release']:
            raise UserError(_('Hold must be active to use amount.'))
        
        if amount > self.remaining_hold_amount:
            raise UserError(_('Requested amount exceeds remaining hold amount.'))
        
        # Create usage record
        usage = self._create_usage_record('amount_used', amount, description)
        
        if source_document:
            usage.source_document = source_document
        
        self.message_post(
            body=_('Hold amount used: %s - %s') % (amount, description))
        
        return usage
    
    @api.model
    def _cron_process_expired_holds(self):
        """Cron job to process expired holds"""
        now = fields.Datetime.now()
        
        # Find expired holds
        expired_holds = self.search([
            ('state', 'in', ['active', 'partial_release']),
            ('expiry_date', '<=', now),
            ('expiry_date', '!=', False)
        ])
        
        for hold in expired_holds:
            try:
                hold.action_expire()
            except Exception as e:
                _logger.error(f"Failed to expire hold {hold.hold_number}: {str(e)}")
        
        return len(expired_holds)
    
    @api.model
    def _cron_send_expiry_alerts(self):
        """Send alerts for holds approaching expiry"""
        alert_date = fields.Datetime.now() + timedelta(days=3)  # Default 3 days
        
        holds_to_alert = self.search([
            ('state', 'in', ['active', 'partial_release']),
            ('expiry_date', '<=', alert_date),
            ('expiry_date', '!=', False),
            ('alert_sent', '=', False)
        ])
        
        for hold in holds_to_alert:
            try:
                hold._send_expiry_alert()
                hold.alert_sent = True
                hold.alert_date = fields.Datetime.now()
            except Exception as e:
                _logger.error(f"Failed to send alert for hold {hold.hold_number}: {str(e)}")
        
        return len(holds_to_alert)
    
    def _send_expiry_alert(self):
        """Send expiry alert for this hold"""
        template = self.env.ref('ams_accounting.email_template_credit_hold_expiry', False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    # ========================
    # VIEW ACTIONS
    # ========================
    
    def action_view_usage_history(self):
        """View usage history for this hold"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Usage History - {self.hold_number}',
            'res_model': 'ams.credit.hold.usage',
            'view_mode': 'tree,form',
            'domain': [('hold_id', '=', self.id)],
            'context': {'default_hold_id': self.id}
        }
    
    def action_partial_release(self):
        """Action for partial release of hold"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partial Release',
            'res_model': 'ams.credit.hold.release.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hold_id': self.id,
                'default_release_amount': self.remaining_hold_amount,
                'default_max_amount': self.remaining_hold_amount,
            }
        }
    
    # ========================
    # CONSTRAINTS
    # ========================
    
    @api.constrains('hold_amount')
    def _check_hold_amount(self):
        for hold in self:
            if hold.hold_amount <= 0:
                raise ValidationError(_('Hold amount must be positive.'))
    
    @api.constrains('hold_duration_days')
    def _check_hold_duration(self):
        for hold in self:
            if hold.hold_duration_type in ['temporary', 'auto_release'] and hold.hold_duration_days <= 0:
                raise ValidationError(_('Hold duration must be positive for temporary holds.'))
    
    @api.constrains('expiry_date', 'hold_date')
    def _check_expiry_date(self):
        for hold in self:
            if hold.expiry_date and hold.expiry_date <= hold.hold_date:
                raise ValidationError(_('Expiry date must be after hold date.'))


class AMSCreditHoldUsage(models.Model):
    """
    Track individual usage events against credit holds
    """
    _name = 'ams.credit.hold.usage'
    _description = 'AMS Credit Hold Usage'
    _order = 'usage_date desc'
    _rec_name = 'display_name'
    
    # Basic Information
    hold_id = fields.Many2one('ams.credit.hold', 'Credit Hold', 
        required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='hold_id.partner_id', 
        store=True, readonly=True)
    
    # Usage Details
    usage_type = fields.Selection([
        ('hold_applied', 'Hold Applied'),
        ('hold_released', 'Hold Released'),
        ('amount_used', 'Amount Used'),
        ('hold_expired', 'Hold Expired'),
        ('hold_cancelled', 'Hold Cancelled'),
        ('adjustment', 'Manual Adjustment')
    ], string='Usage Type', required=True)
    
    amount = fields.Float('Amount', required=True)
    description = fields.Text('Description', required=True)
    
    # Timing
    usage_date = fields.Datetime('Usage Date', required=True, default=fields.Datetime.now)
    
    # Authorization
    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('reversed', 'Reversed')
    ], string='Status', default='draft')
    
    # Related Documents
    source_document = fields.Reference([
        ('account.move', 'Invoice'),
        ('account.payment', 'Payment'),
        ('ams.subscription', 'Subscription'),
    ], string='Source Document')
    
    # Display name
    display_name = fields.Char('Name', compute='_compute_display_name', store=True)
    
    @api.depends('usage_type', 'amount', 'usage_date')
    def _compute_display_name(self):
        for usage in self:
            usage.display_name = f"{usage.usage_type} - {usage.amount} - {usage.usage_date.strftime('%Y-%m-%d')}"
    
    def action_reverse(self):
        """Reverse this usage record"""
        for usage in self:
            if usage.state != 'applied':
                raise UserError(_('Only applied usage can be reversed.'))
            
            # Create reverse record
            reverse_vals = {
                'hold_id': usage.hold_id.id,
                'usage_type': 'adjustment',
                'amount': -usage.amount,
                'description': f'Reversal of: {usage.description}',
                'usage_date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'state': 'applied'
            }
            
            self.create(reverse_vals)
            usage.state = 'reversed'


class AMSCreditUsage(models.Model):
    """
    Model for tracking credit usage history across all credit activities
    """
    _name = 'ams.credit.usage'
    _description = 'AMS Credit Usage History'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    # Basic Information
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', 
        readonly=True)
    
    # Credit Limit Reference
    credit_limit_id = fields.Many2one('ams.credit.limit', 'Credit Limit')
    
    # Usage Details
    usage_type = fields.Selection([
        ('credit_increase', 'Credit Limit Increase'),
        ('credit_decrease', 'Credit Limit Decrease'),
        ('invoice_created', 'Invoice Created'),
        ('payment_received', 'Payment Received'),
        ('credit_note_issued', 'Credit Note Issued'),
        ('hold_applied', 'Credit Hold Applied'),
        ('hold_released', 'Credit Hold Released'),
        ('adjustment', 'Manual Adjustment'),
        ('system_correction', 'System Correction')
    ], string='Usage Type', required=True)
    
    usage_amount = fields.Float('Usage Amount', required=True,
        help="Positive for credit increases, negative for decreases")
    
    description = fields.Text('Description', required=True)
    reference = fields.Char('Reference',
        help="External reference number or document reference")
    
    # Balances
    previous_balance = fields.Float('Previous Balance')
    new_balance = fields.Float('New Balance')
    
    # Related Documents
    invoice_id = fields.Many2one('account.move', 'Related Invoice')
    payment_id = fields.Many2one('account.payment', 'Related Payment')
    hold_id = fields.Many2one('ams.credit.hold', 'Related Hold')
    
    # Source Document
    source_document = fields.Reference([
        ('account.move', 'Invoice'),
        ('account.payment', 'Payment'),
        ('ams.credit.hold', 'Credit Hold'),
        ('ams.credit.limit', 'Credit Limit'),
    ], string='Source Document')
    
    # Display and Categorization
    display_name = fields.Char('Name', compute='_compute_display_name', store=True)
    
    @api.depends('usage_type', 'usage_amount', 'create_date')
    def _compute_display_name(self):
        for usage in self:
            date_str = usage.create_date.strftime('%Y-%m-%d')
            usage.display_name = f"{usage.usage_type} - {usage.usage_amount} - {date_str}"
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically calculate balances"""
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id:
                # Get previous balance
                last_usage = self.search([
                    ('partner_id', '=', partner_id)
                ], order='create_date desc', limit=1)
                
                previous_balance = last_usage.new_balance if last_usage else 0.0
                vals['previous_balance'] = previous_balance
                vals['new_balance'] = previous_balance + vals.get('usage_amount', 0.0)
        
        return super().create(vals_list)
    
    @api.model
    def create_usage_record(self, partner_id, usage_type, amount, description, 
                           reference=None, source_document=None, **kwargs):
        """Helper method to create usage records"""
        vals = {
            'partner_id': partner_id,
            'usage_type': usage_type,
            'usage_amount': amount,
            'description': description,
            'reference': reference,
            'source_document': source_document,
        }
        vals.update(kwargs)
        
        return self.create(vals)
    
    def name_get(self):
        result = []
        for usage in self:
            name = f"{usage.usage_type}: {usage.usage_amount} - {usage.description[:50]}"
            result.append((usage.id, name))
        return result