from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AMSParticipation(models.Model):
    """Core participation tracking for memberships, chapters, and committees."""
    _name = 'ams.participation'
    _description = 'Member Participation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'begin_date desc, id desc'
    _rec_name = 'display_name'

    # Participation type choices
    PARTICIPATION_TYPES = [
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('committee_position', 'Committee Position'),
    ]

    # Status choices
    STATUS_SELECTION = [
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ]

    # ==========================================
    # CORE IDENTIFICATION
    # ==========================================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member (Individual)',
        help='Individual member for this participation'
    )
    
    company_id = fields.Many2one(
        'res.partner',
        string='Organization Member',
        help='Organization member (alternative to individual)'
    )
    
    participation_type = fields.Selection(
        PARTICIPATION_TYPES,
        string='Participation Type',
        required=True,
        default='membership',
        help='Type of participation'
    )
    
    status = fields.Selection(
        STATUS_SELECTION,
        string='Status',
        required=True,
        default='prospect',
        help='Current participation status',
        tracking=True
    )
    
    # ==========================================
    # FINANCIAL INTEGRATION (Optional references)
    # ==========================================
    
    related_invoice_id = fields.Many2one(
        'account.move',
        string='Associated Invoice',
        help='Invoice that created or renewed this participation'
    )
    
    # Note: These will be available when respective modules are installed
    subscription_product_id = fields.Char(
        string='Subscription Product Reference',
        help='Reference to subscription product (will be Many2one when ams_subscription_management is installed)'
    )
    
    committee_position_id = fields.Char(
        string='Committee Position Reference',
        help='Reference to committee position (will be Many2one when ams_committees_core is installed)'
    )
    
    # ==========================================
    # TEMPORAL TRACKING
    # ==========================================
    
    join_date = fields.Date(
        string='Initial Join Date',
        required=True,
        default=fields.Date.context_today,
        help='When this participation first began'
    )
    
    begin_date = fields.Date(
        string='Current Term Start',
        required=True,
        default=fields.Date.context_today,
        help='Start date of current participation term'
    )
    
    end_date = fields.Date(
        string='Current Term End',
        required=True,
        help='End date of current participation term'
    )
    
    bill_through_date = fields.Date(
        string='Billing End Date',
        required=True,
        help='Date through which participation is billed'
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        required=True,
        help='Date through which participation is paid'
    )
    
    # ==========================================
    # GRACE PERIOD AND SUSPENSION MANAGEMENT
    # ==========================================
    
    grace_period_end_date = fields.Date(
        string='Grace Period End',
        help='When grace period expires'
    )
    
    suspend_end_date = fields.Date(
        string='Suspension End Date',
        help='When suspension period ends'
    )
    
    terminated_date = fields.Date(
        string='Termination Date',
        help='When participation was terminated'
    )
    
    # ==========================================
    # RENEWAL AND AUTOMATION
    # ==========================================
    
    auto_pay = fields.Boolean(
        string='Auto-Renewal Enabled',
        default=False,
        help='Automatically renew this participation'
    )
    
    renew_to_product_id = fields.Char(
        string='Renewal Target Product Reference',
        help='Product reference for next renewal (will be Many2one when ams_subscription_management is installed)'
    )
    
    # ==========================================
    # CANCELLATION MANAGEMENT
    # ==========================================
    
    cancellation_reason_id = fields.Many2one(
        'ams.cancellation.reason',
        string='Cancellation Reason',
        help='Why this participation was cancelled'
    )
    
    # ==========================================
    # ADMINISTRATIVE
    # ==========================================
    
    notes = fields.Text(
        string='Administrative Notes',
        help='Internal notes about this participation'
    )
    
    # ==========================================
    # COMPUTED FIELDS (STORED)
    # ==========================================
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    member_display_name = fields.Char(
        string='Member Name',
        compute='_compute_member_display_name',
        store=True
    )
    
    # ==========================================
    # COMPUTED FIELDS (NOT STORED - DATE DEPENDENT)
    # ==========================================
    
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining'
        # Removed store=True because this changes daily
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired'
        # Removed store=True because this changes daily
    )
    
    is_in_grace = fields.Boolean(
        string='In Grace Period',
        compute='_compute_is_in_grace'
        # Removed store=True because this changes daily
    )
    
    is_renewable = fields.Boolean(
        string='Is Renewable',
        compute='_compute_is_renewable',
        store=True  # This can be stored as it depends on status, not current date
    )
    
    # ==========================================
    # RELATIONSHIPS
    # ==========================================
    
    history_ids = fields.One2many(
        'ams.participation.history',
        'participation_id',
        string='Status Change History',
        help='Complete history of status changes'
    )

    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('check_member_or_company', 
         'CHECK((partner_id IS NOT NULL AND company_id IS NULL) OR (partner_id IS NULL AND company_id IS NOT NULL))',
         'Participation must have either a member or organization, but not both.'),
    ]

    # ==========================================
    # COMPUTED FIELD METHODS - FIXED FOR NEW RECORDS
    # ==========================================
    
    @api.depends('partner_id', 'company_id', 'participation_type', 'status')
    def _compute_display_name(self):
        """Compute display name for participation records."""
        for record in self:
            # Handle case where record is not yet saved/created
            try:
                # Get member name safely
                member_name = None
                if record.partner_id:
                    member_name = record.partner_id.name
                elif record.company_id:
                    member_name = record.company_id.name
                
                if member_name:
                    # Get type and status labels safely
                    type_label = dict(self.PARTICIPATION_TYPES).get(record.participation_type, record.participation_type or 'Participation')
                    status_label = dict(self.STATUS_SELECTION).get(record.status, record.status or 'New')
                    record.display_name = f"{member_name} - {type_label} ({status_label})"
                else:
                    # Handle new records or records without members
                    record.display_name = f"Participation {record.id or 'New'}"
            except:
                # Fallback for any errors during computation
                record.display_name = f"Participation {record.id or 'New'}"

    @api.depends('partner_id', 'company_id')
    def _compute_member_display_name(self):
        """Compute member display name for easier reporting."""
        for record in self:
            try:
                if record.partner_id and hasattr(record.partner_id, 'name'):
                    record.member_display_name = record.partner_id.name or ''
                elif record.company_id and hasattr(record.company_id, 'name'):
                    record.member_display_name = record.company_id.name or ''
                else:
                    record.member_display_name = ''
            except:
                # Fallback for any errors during computation
                record.member_display_name = ''

    def _compute_days_remaining(self):
        """Compute days remaining until participation ends."""
        today = fields.Date.context_today(self)
        for record in self:
            try:
                if record.end_date:
                    delta = record.end_date - today
                    record.days_remaining = delta.days
                else:
                    record.days_remaining = 0
            except:
                record.days_remaining = 0

    def _compute_is_expired(self):
        """Compute if participation has expired."""
        today = fields.Date.context_today(self)
        for record in self:
            try:
                record.is_expired = record.paid_through_date and record.paid_through_date < today
            except:
                record.is_expired = False

    def _compute_is_in_grace(self):
        """Compute if participation is in grace period."""
        today = fields.Date.context_today(self)
        for record in self:
            try:
                record.is_in_grace = (
                    record.status == 'grace' and 
                    record.grace_period_end_date and 
                    record.grace_period_end_date >= today
                )
            except:
                record.is_in_grace = False

    @api.depends('status')
    def _compute_is_renewable(self):
        """Compute if participation can be renewed."""
        for record in self:
            try:
                record.is_renewable = record.status in ['active', 'grace', 'suspended']
            except:
                record.is_renewable = False

    # ==========================================
    # VALIDATION METHODS
    # ==========================================
    
    @api.constrains('partner_id', 'company_id')
    def _check_member_assignment(self):
        """Ensure exactly one member type is assigned."""
        for record in self:
            if not record.partner_id and not record.company_id:
                raise ValidationError("Participation must be assigned to either an individual or organization.")
            if record.partner_id and record.company_id:
                raise ValidationError("Participation cannot be assigned to both individual and organization.")

    @api.constrains('begin_date', 'end_date')
    def _check_date_sequence(self):
        """Validate date field relationships."""
        for record in self:
            if record.begin_date and record.end_date:
                if record.begin_date > record.end_date:
                    raise ValidationError("Begin date cannot be after end date.")
                    
            if record.join_date and record.begin_date:
                if record.join_date > record.begin_date:
                    raise ValidationError("Join date cannot be after begin date.")

    @api.constrains('bill_through_date', 'paid_through_date', 'end_date')
    def _check_billing_dates(self):
        """Validate billing date relationships."""
        for record in self:
            if record.bill_through_date and record.end_date:
                if record.bill_through_date > record.end_date + timedelta(days=30):
                    # Allow some reasonable overage
                    raise ValidationError("Bill through date significantly exceeds participation end date.")

    @api.constrains('cancellation_reason_id', 'status')
    def _check_cancellation_reason(self):
        """Ensure cancellation reason is only set for cancelled/terminated participations."""
        for record in self:
            if record.cancellation_reason_id and record.status not in ['cancelled', 'terminated']:
                raise ValidationError("Cancellation reason can only be set for cancelled or terminated participations.")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================
    
    def update_participation_status(self, new_status, reason=None, automated=False, reference_document=None):
        """Update participation status with full audit trail."""
        for record in self:
            old_status = record.status
            
            # Validate status transition
            if not record._validate_status_transition(old_status, new_status):
                raise ValidationError(f"Invalid status transition: {old_status} → {new_status}")
            
            # Check if approval required (for future enhancement)
            if record._requires_approval(old_status, new_status) and not automated:
                raise UserError(f"Status change from {old_status} to {new_status} requires approval.")
            
            # Update status
            record.status = new_status
            
            # Handle status-specific actions
            record._handle_status_change_actions(old_status, new_status)
            
            # Create history record
            record.env['ams.participation.history'].create({
                'participation_id': record.id,
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason,
                'automated': automated,
                'reference_document': reference_document,
            })
            
        return True

    def _validate_status_transition(self, old_status, new_status):
        """Validate if status transition is allowed."""
        # Define allowed transitions
        allowed_transitions = {
            'prospect': ['active', 'cancelled'],
            'active': ['grace', 'suspended', 'terminated', 'cancelled'],
            'grace': ['active', 'suspended', 'terminated', 'cancelled'],
            'suspended': ['active', 'grace', 'terminated', 'cancelled'],
            'terminated': [],  # Terminal status
            'cancelled': [],   # Terminal status
        }
        
        return new_status in allowed_transitions.get(old_status, [])

    def _requires_approval(self, old_status, new_status):
        """Check if status transition requires approval."""
        # Define transitions that require approval
        approval_required = [
            ('active', 'terminated'),
            ('grace', 'terminated'),
            ('suspended', 'terminated'),
        ]
        
        return (old_status, new_status) in approval_required

    def _handle_status_change_actions(self, old_status, new_status):
        """Execute actions required for specific status transitions."""
        self.ensure_one()
        
        # Entering grace period
        if new_status == 'grace':
            grace_days = self._get_grace_period_days()
            self.grace_period_end_date = fields.Date.context_today(self) + timedelta(days=grace_days)
        
        # Activation from prospect
        elif old_status == 'prospect' and new_status == 'active':
            self._activate_member_benefits()
        
        # Suspension handling
        elif new_status == 'suspended':
            self._suspend_member_access()
            if not self.suspend_end_date:
                # Default 90-day suspension
                self.suspend_end_date = fields.Date.context_today(self) + timedelta(days=90)
        
        # Termination processing
        elif new_status in ['terminated', 'cancelled']:
            self.terminated_date = fields.Date.context_today(self)
            self._revoke_member_access()

    def _get_grace_period_days(self):
        """Get grace period length in days."""
        # Try to get from system configuration, fallback to 30 days
        try:
            config_model = self.env['ams.config.settings']
            return int(config_model.get_global_setting('grace_period_days', 30))
        except:
            return 30

    def _activate_member_benefits(self):
        """Activate member benefits for this participation."""
        # This will be enhanced by ams_benefits_engine module
        pass

    def _suspend_member_access(self):
        """Suspend member access and benefits."""
        # This will be enhanced by portal and benefits modules
        pass

    def _revoke_member_access(self):
        """Revoke all member access and benefits."""
        # This will be enhanced by portal and benefits modules
        pass

    # ==========================================
    # ACTION METHODS
    # ==========================================
    
    def action_activate(self):
        """Quick action to activate participation."""
        for record in self:
            if record.status == 'prospect':
                record.update_participation_status('active', reason='Manual activation')
            else:
                raise UserError("Only prospect participations can be activated.")

    def action_suspend(self):
        """Quick action to suspend participation."""
        for record in self:
            if record.status in ['active', 'grace']:
                record.update_participation_status('suspended', reason='Manual suspension')
            else:
                raise UserError("Only active or grace participations can be suspended.")

    def action_cancel(self):
        """Quick action to cancel participation."""
        for record in self:
            if record.status not in ['terminated', 'cancelled']:
                # This would typically open a wizard to select cancellation reason
                record.update_participation_status('cancelled', reason='Manual cancellation')

    def action_view_history(self):
        """Open participation history view."""
        self.ensure_one()
        return {
            'name': f'Participation History - {self.member_display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation.history',
            'view_mode': 'list,form',
            'domain': [('participation_id', '=', self.id)],
            'context': {'default_participation_id': self.id},
        }

    def action_view_member(self):
        """Open related member record."""
        self.ensure_one()
        member = self.partner_id or self.company_id
        if member:
            return {
                'name': f'Member - {member.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': member.id,
                'view_mode': 'form',
                'target': 'current',
            }

    # ==========================================
    # AUTOMATED PROCESSING
    # ==========================================
    
    @api.model
    def process_participation_lifecycle(self):
        """Daily automated processing of participation lifecycle."""
        today = fields.Date.context_today(self)
        
        # Process expired participations
        expired = self.search([
            ('status', '=', 'active'),
            ('paid_through_date', '<', today)
        ])
        
        for participation in expired:
            participation.update_participation_status(
                'grace',
                reason='Automatic - Payment expired',
                automated=True
            )
        
        # Process grace period expiration
        grace_expired = self.search([
            ('status', '=', 'grace'),
            ('grace_period_end_date', '<', today)
        ])
        
        for participation in grace_expired:
            participation.update_participation_status(
                'terminated',
                reason='Automatic - Grace period expired',
                automated=True
            )
        
        # Process suspension expiration
        suspension_expired = self.search([
            ('status', '=', 'suspended'),
            ('suspend_end_date', '<=', today)
        ])
        
        for participation in suspension_expired:
            # Check if can be reactivated
            if participation.paid_through_date >= today:
                participation.update_participation_status(
                    'active',
                    reason='Automatic - Suspension period ended',
                    automated=True
                )
            else:
                participation.update_participation_status(
                    'grace',
                    reason='Automatic - Suspension ended but payment required',
                    automated=True
                )

    # ==========================================
    # SEARCH METHODS
    # ==========================================
    
    @api.model
    def get_active_participations(self, member=None):
        """Get active participations, optionally for specific member."""
        domain = [('status', 'in', ['active', 'grace'])]
        if member:
            domain.extend(['|', ('partner_id', '=', member.id), ('company_id', '=', member.id)])
        return self.search(domain)

    @api.model
    def get_expiring_participations(self, days_ahead=30):
        """Get participations expiring within specified days."""
        cutoff_date = fields.Date.context_today(self) + timedelta(days=days_ahead)
        return self.search([
            ('status', '=', 'active'),
            ('paid_through_date', '<=', cutoff_date)
        ])

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger usage count recomputation."""
        records = super().create(vals_list)
        # Trigger recomputation of usage_count on affected cancellation reasons
        reasons = records.mapped('cancellation_reason_id').filtered(lambda r: r)
        if reasons:
            reasons._compute_usage_count()
        return records

    def write(self, vals):
        """Override write to trigger usage count recomputation."""
        old_reasons = self.mapped('cancellation_reason_id')
        result = super().write(vals)
        if 'cancellation_reason_id' in vals:
            new_reasons = self.mapped('cancellation_reason_id')
            affected_reasons = (old_reasons | new_reasons).filtered(lambda r: r)
            if affected_reasons:
                affected_reasons._compute_usage_count()
        return result

    def unlink(self):
        """Override unlink to trigger usage count recomputation."""
        reasons = self.mapped('cancellation_reason_id').filtered(lambda r: r)
        result = super().unlink()
        if reasons:
            reasons._compute_usage_count()
        return result