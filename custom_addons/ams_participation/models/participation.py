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
        help='Current participation status'
    )
    
    # ==========================================
    # FINANCIAL INTEGRATION
    # ==========================================
    
    related_invoice_id = fields.Many2one(
        'account.move',
        string='Associated Invoice',
        help='Invoice that created or renewed this participation'
    )
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Related Subscription Product',
        help='Subscription product that defines this participation'
    )
    
    # ==========================================
    # ORGANIZATIONAL RELATIONSHIPS
    # ==========================================
    
    committee_position_id = fields.Many2one(
        'ams.committee.position',
        string='Committee Role',
        help='Specific committee position (for committee_position type)'
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
    
    renew_to_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Renewal Target Product',
        help='Product to use for next renewal (if different)'
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
    # COMPUTED FIELDS
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
    
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining'
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired'
    )
    
    is_in_grace = fields.Boolean(
        string='In Grace Period',
        compute='_compute_is_in_grace'
    )
    
    is_renewable = fields.Boolean(
        string='Is Renewable',
        compute='_compute_is_renewable'
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
    
    # Note: benefit_assignment_ids will be added by ams_benefits_engine module
    # benefit_assignment_ids = fields.One2many(
    #     'ams.participation.benefit',
    #     'participation_id',
    #     string='Assigned Benefits'
    # )

    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('check_member_or_company', 
         'CHECK((partner_id IS NOT NULL AND company_id IS NULL) OR (partner_id IS NULL AND company_id IS NOT NULL))',
         'Participation must have either a member or organization, but not both.'),
    ]

    # ==========================================
    # COMPUTED FIELD METHODS
    # ==========================================
    
    @api.depends('partner_id', 'company_id', 'participation_type', 'status')
    def _compute_display_name(self):
        """Compute display name for participation records."""
        for record in self:
            member_name = record.partner_id.name if record.partner_id else record.company_id.name
            if member_name:
                type_label = dict(record.PARTICIPATION_TYPES).get(record.participation_type, record.participation_type)
                status_label = dict(record.STATUS_SELECTION).get(record.status, record.status)
                record.display_name = f"{member_name} - {type_label} ({status_label})"
            else:
                record.display_name = f"Participation {record.id or 'New'}"

    @api.depends('partner_id', 'company_id')
    def _compute_member_display_name(self):
        """Compute member display name for easier reporting."""
        for record in self:
            record.member_display_name = record.partner_id.name if record.partner_id else record.company_id.name

    @api.depends('end_date')
    def _compute_days_remaining(self):
        """Compute days remaining until participation ends."""
        today = fields.Date.context_today(self)
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_remaining = delta.days
            else:
                record.days_remaining = 0

    @api.depends('paid_through_date')
    def _compute_is_expired(self):
        """Compute if participation has expired."""
        today = fields.Date.context_today(self)
        for record in self:
            record.is_expired = record.paid_through_date and record.paid_through_date < today

    @api.depends('status', 'grace_period_end_date')
    def _compute_is_in_grace(self):
        """Compute if participation is in grace period."""
        today = fields.Date.context_today(self)
        for record in self:
            record.is_in_grace = (
                record.status == 'grace' and 
                record.grace_period_end_date and 
                record.grace_period_end_date >= today
            )

    @api.depends('status', 'end_date')
    def _compute_is_renewable(self):
        """Compute if participation can be renewed."""
        for record in self:
            record.is_renewable = record.status in ['active', 'grace', 'suspended']

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
                    
            if record.paid_through_date and record.bill_through_date:
                # Warn if paid through date is way ahead of billing
                if record.paid_through_date > record.bill_through_date + timedelta(days=60):
                    # Log warning but don't prevent
                    pass

    @api.constrains('participation_type', 'committee_position_id')
    def _check_committee_position_consistency(self):
        """Ensure committee position is only set for committee participation types."""
        for record in self:
            if record.committee_position_id and record.participation_type != 'committee_position':
                raise ValidationError("Committee position can only be set for committee position participation type.")
            if record.participation_type == 'committee_position' and not record.committee_position_id:
                raise ValidationError("Committee position participation requires a committee position to be specified.")

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
        # Default 30 days, can be enhanced with system configuration
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
            'view_mode': 'tree,form',
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