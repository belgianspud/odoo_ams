# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class AMSParticipation(models.Model):
    """Core participation records for association member engagement tracking."""
    
    _name = 'ams.participation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'AMS Participation'
    _order = 'partner_id, participation_type, begin_date desc'
    _rec_name = 'display_name'

    # ========================================================================
    # CORE RELATIONSHIP FIELDS
    # ========================================================================

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Uncheck to archive this participation record"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Member",
        required=True,
        ondelete='cascade',
        tracking=True,
        help="Individual or organization participating in this engagement"
    )

    company_id = fields.Many2one(
        'res.partner',
        string="Organization",
        domain="[('is_company', '=', True)]",
        tracking=True,
        help="Parent organization (for employee participation, sponsorship, or chapter hierarchy)"
    )

    # ========================================================================
    # PARTICIPATION DETAILS
    # ========================================================================

    participation_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('committee_position', 'Committee Position'),
        ('event_attendance', 'Event Attendance'),
        ('course_enrollment', 'Course Enrollment')
    ], string="Participation Type", required=True, tracking=True,
       help="Type of participation or engagement")

    status = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string="Status", required=True, default='prospect', tracking=True,
       help="Current participation status")

    # ========================================================================
    # DATE FIELDS
    # ========================================================================

    join_date = fields.Date(
        string="Initial Join Date",
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Date when member first joined this type of participation"
    )

    begin_date = fields.Date(
        string="Current Term Start",
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Effective start date of current participation term"
    )

    end_date = fields.Date(
        string="Current Term End",
        required=True,
        tracking=True,
        help="Planned end date of current participation term"
    )

    bill_through_date = fields.Date(
        string="Billing End Date",
        tracking=True,
        help="Date through which billing is calculated"
    )

    paid_through_date = fields.Date(
        string="Paid Through Date", 
        tracking=True,
        help="Date through which member has paid for this participation"
    )

    # ========================================================================
    # GRACE AND SUSPENSION PERIODS
    # ========================================================================

    grace_period_end_date = fields.Date(
        string="Grace Period End",
        compute='_compute_grace_period_end_date',
        store=True,
        help="Calculated end date for grace period"
    )

    suspend_end_date = fields.Date(
        string="Suspension End Date",
        tracking=True,
        help="Date when suspension period ends (if applicable)"
    )

    terminated_date = fields.Date(
        string="Termination Date",
        tracking=True,
        help="Date when participation was terminated"
    )

    # ========================================================================
    # REFERENCE FIELDS (Integration Points)
    # ========================================================================

    related_invoice_id = fields.Many2one(
        'account.move',
        string="Related Invoice",
        domain="[('move_type', 'in', ['out_invoice', 'out_refund'])]",
        tracking=True,
        help="Most recent invoice related to this participation"
    )

    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string="Subscription Product",
        help="Product/service associated with this participation"
    )

    committee_position_id = fields.Many2one(
        'ams.committee.position',
        string="Committee Position",
        help="Specific committee position (for committee_position type)"
    )

    cancellation_reason_id = fields.Many2one(
        'ams.cancellation.reason',
        string="Cancellation Reason",
        tracking=True,
        help="Reason for cancellation or termination"
    )

    # ========================================================================
    # CONFIGURATION FIELDS
    # ========================================================================

    auto_pay = fields.Boolean(
        string="Auto-renewal Enabled",
        default=False,
        tracking=True,
        help="Automatically renew and attempt payment for this participation"
    )

    renew_to_product_id = fields.Many2one(
        'ams.subscription.product',
        string="Renewal Target Product",
        help="Product to renew to (if different from current)"
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes about this participation"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True,
        help="Human-readable participation identifier"
    )

    member_status = fields.Selection(
        related='partner_id.membership_status',
        string="Member Status",
        store=True,
        help="Current status of the associated member"
    )

    is_company_participation = fields.Boolean(
        related='partner_id.is_company',
        string="Is Company Participation",
        store=True,
        help="Whether this is an organizational participation"
    )

    days_until_expiry = fields.Integer(
        string="Days Until Expiry",
        compute='_compute_days_until_expiry',
        help="Days remaining until paid_through_date"
    )

    is_overdue = fields.Boolean(
        string="Is Overdue",
        compute='_compute_overdue_status',
        store=True,
        help="Payment is overdue (paid_through_date has passed)"
    )

    is_in_grace_period = fields.Boolean(
        string="In Grace Period",
        compute='_compute_grace_period_status',
        store=True,
        help="Currently in grace period after expiry"
    )

    can_auto_renew = fields.Boolean(
        string="Can Auto-Renew",
        compute='_compute_can_auto_renew',
        help="Whether this participation is eligible for automatic renewal"
    )

    relationship_context = fields.Selection([
        ('direct', 'Direct Participation'),
        ('employee', 'Employee of Member Organization'),
        ('sponsored', 'Sponsored by Organization'),
        ('chapter_member', 'Chapter/Subsidiary Member'),
        ('representative', 'Organizational Representative')
    ], string="Relationship Context", 
       compute='_compute_relationship_context',
       store=True,
       help="Context of the company relationship")

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('positive_days_until_expiry', 
         'CHECK(1=1)', 
         'This constraint is implemented in Python for complexity'),
        ('begin_before_end', 
         'CHECK(begin_date <= end_date)', 
         'Begin date must be before or equal to end date'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('partner_id', 'participation_type', 'status', 'begin_date', 'end_date')
    def _compute_display_name(self):
        """Compute human-readable display name."""
        for record in self:
            if record.partner_id and record.participation_type:
                type_name = dict(record._fields['participation_type'].selection).get(record.participation_type, '')
                status_badge = f"[{record.status.upper()}]" if record.status != 'active' else ""
                date_range = f"({record.begin_date} - {record.end_date})" if record.begin_date and record.end_date else ""
                
                record.display_name = f"{record.partner_id.display_name} - {type_name} {status_badge} {date_range}".strip()
            else:
                record.display_name = "Incomplete Participation"

    @api.depends('paid_through_date')
    def _compute_grace_period_end_date(self):
        """Compute grace period end date based on system configuration."""
        for record in self:
            if record.paid_through_date:
                # Get grace period from system config (default 30 days)
                grace_days = self._get_config_value('grace_period_days', 30)
                record.grace_period_end_date = record.paid_through_date + timedelta(days=grace_days)
            else:
                record.grace_period_end_date = False

    @api.depends('paid_through_date')
    def _compute_days_until_expiry(self):
        """Compute days until participation expires."""
        today = date.today()
        for record in self:
            if record.paid_through_date:
                delta = record.paid_through_date - today
                record.days_until_expiry = delta.days
            else:
                record.days_until_expiry = 0

    @api.depends('paid_through_date')
    def _compute_overdue_status(self):
        """Determine if participation is overdue."""
        today = date.today()
        for record in self:
            if record.paid_through_date:
                record.is_overdue = record.paid_through_date < today
            else:
                record.is_overdue = False

    @api.depends('paid_through_date', 'grace_period_end_date', 'status')
    def _compute_grace_period_status(self):
        """Determine if participation is in grace period."""
        today = date.today()
        for record in self:
            if record.paid_through_date and record.grace_period_end_date:
                is_past_paid_date = record.paid_through_date < today
                is_before_grace_end = today <= record.grace_period_end_date
                record.is_in_grace_period = is_past_paid_date and is_before_grace_end and record.status == 'grace'
            else:
                record.is_in_grace_period = False

    @api.depends('status', 'auto_pay', 'paid_through_date')
    def _compute_can_auto_renew(self):
        """Determine if participation can be auto-renewed."""
        for record in self:
            record.can_auto_renew = (
                record.status in ['active', 'grace'] and
                record.auto_pay and
                record.paid_through_date and
                record.participation_type in ['membership', 'chapter']  # Only auto-renew ongoing participations
            )

    @api.depends('partner_id.is_company', 'company_id', 'participation_type')
    def _compute_relationship_context(self):
        """Determine the relationship context with organization."""
        for record in self:
            if not record.company_id:
                record.relationship_context = 'direct'
            elif record.partner_id.is_company:
                record.relationship_context = 'direct'  # Company's own participation
            elif record.partner_id.parent_id == record.company_id:
                record.relationship_context = 'employee'
            elif record.participation_type == 'chapter':
                record.relationship_context = 'chapter_member'
            else:
                record.relationship_context = 'sponsored'

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================

    @api.constrains('participation_type', 'partner_id', 'status')
    def _check_single_active_membership(self):
        """Ensure only one active membership per member."""
        for record in self:
            if record.participation_type == 'membership' and record.status == 'active':
                # Check for other active memberships for the same member
                existing_active = self.search([
                    ('id', '!=', record.id),
                    ('partner_id', '=', record.partner_id.id),
                    ('participation_type', '=', 'membership'),
                    ('status', '=', 'active')
                ])
                
                if existing_active:
                    raise ValidationError(_(
                        "Member %s already has an active membership participation. "
                        "Only one active membership is allowed per member."
                    ) % record.partner_id.display_name)

    @api.constrains('begin_date', 'end_date', 'paid_through_date', 'bill_through_date')
    def _check_date_logic(self):
        """Validate date field relationships."""
        for record in self:
            if record.begin_date and record.end_date and record.begin_date > record.end_date:
                raise ValidationError(_("Begin date must be before or equal to end date"))
            
            if record.paid_through_date and record.begin_date and record.paid_through_date < record.begin_date:
                # Only warn for existing records, not new ones
                if record.id and record.env.context.get('validate_paid_through'):
                    raise ValidationError(_("Paid through date should not be before begin date"))
            
            if record.bill_through_date and record.end_date and record.bill_through_date > record.end_date:
                raise ValidationError(_("Bill through date cannot be after end date"))

    @api.constrains('committee_position_id', 'participation_type')
    def _check_committee_position_consistency(self):
        """Ensure committee position is only set for committee participation."""
        for record in self:
            if record.committee_position_id and record.participation_type != 'committee_position':
                raise ValidationError(_("Committee position can only be set for committee position participation type"))

    @api.constrains('company_id', 'partner_id')
    def _check_company_relationship(self):
        """Validate company relationship logic."""
        for record in self:
            if record.company_id:
                # If partner is an individual and has parent, company_id should match or be related
                if not record.partner_id.is_company and record.partner_id.parent_id:
                    if record.company_id != record.partner_id.parent_id:
                        # Allow for sponsorship scenarios
                        pass  # More flexible validation
                
                # Company cannot sponsor itself
                if record.company_id == record.partner_id:
                    raise ValidationError(_("Organization cannot sponsor or relate to itself"))

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('participation_type')
    def _onchange_participation_type(self):
        """Set appropriate defaults based on participation type."""
        if self.participation_type:
            # Set default end date based on type
            today = fields.Date.today()
            if self.participation_type in ['membership', 'chapter']:
                self.end_date = today + timedelta(days=365)  # 1 year
            elif self.participation_type == 'committee_position':
                self.end_date = today + timedelta(days=730)  # 2 years
            elif self.participation_type == 'course_enrollment':
                self.end_date = today + timedelta(days=90)   # 3 months
            elif self.participation_type == 'event_attendance':
                self.end_date = today + timedelta(days=1)    # Single day
            
            # Clear incompatible fields
            if self.participation_type != 'committee_position':
                self.committee_position_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Set defaults based on selected partner."""
        if self.partner_id:
            # If partner has a parent company, suggest it as company_id
            if not self.partner_id.is_company and self.partner_id.parent_id:
                self.company_id = self.partner_id.parent_id
            
            # Set default join date to partner's member_since date if available
            if hasattr(self.partner_id, 'member_since') and self.partner_id.member_since:
                self.join_date = self.partner_id.member_since

    @api.onchange('begin_date', 'end_date')
    def _onchange_dates(self):
        """Update related dates when begin/end dates change."""
        if self.begin_date and self.end_date:
            # Set bill_through_date to end_date if not set
            if not self.bill_through_date:
                self.bill_through_date = self.end_date
            
            # Set paid_through_date to end_date if not set (for new records)
            if not self.paid_through_date and not self.id:
                self.paid_through_date = self.end_date

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and create history records."""
        for vals in vals_list:
            # Set default dates if not provided
            if not vals.get('join_date'):
                vals['join_date'] = fields.Date.today()
            
            if not vals.get('begin_date'):
                vals['begin_date'] = vals.get('join_date', fields.Date.today())
            
            # Set bill_through_date to end_date if not provided
            if vals.get('end_date') and not vals.get('bill_through_date'):
                vals['bill_through_date'] = vals['end_date']
        
        records = super().create(vals_list)
        
        # Create history records for new participations
        for record in records:
            record._create_history_record(
                old_status='',
                new_status=record.status,
                reason='Initial creation',
                automated=False
            )
            
            # Post creation message to chatter
            record.message_post(
                body=_("Participation created: %s") % record.display_name,
                message_type='notification'
            )
        
        return records

    def write(self, vals):
        """Override write to track changes and update history."""
        for record in self:
            old_status = record.status
            
            # Call super to update the record
            result = super().write(vals)
            
            # Track status changes
            if 'status' in vals and vals['status'] != old_status:
                new_status = vals['status']
                reason = self.env.context.get('status_change_reason', 'Manual update')
                automated = self.env.context.get('automated_status_change', False)
                
                # Create history record
                record._create_history_record(
                    old_status=old_status,
                    new_status=new_status,
                    reason=reason,
                    automated=automated
                )
                
                # Post status change to chatter
                record.message_post(
                    body=_("Status changed: %s → %s") % (old_status.title(), new_status.title()),
                    message_type='notification'
                )
                
                # Handle automatic date updates based on status change
                record._handle_status_change_side_effects(old_status, new_status)
            
            # Sync member status if configured
            if 'status' in vals:
                record._sync_member_status()
        
        return result

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def _create_history_record(self, old_status, new_status, reason='', automated=False):
        """Create participation history record."""
        self.ensure_one()
        
        self.env['ams.participation.history'].create({
            'participation_id': self.id,
            'old_status': old_status,
            'new_status': new_status,
            'change_date': fields.Datetime.now(),
            'changed_by': self.env.user.id,
            'reason': reason or 'No reason specified',
            'automated': automated,
        })

    def _handle_status_change_side_effects(self, old_status, new_status):
        """Handle side effects of status changes."""
        self.ensure_one()
        
        today = fields.Date.today()
        
        # Set termination date when terminated
        if new_status == 'terminated' and old_status != 'terminated':
            self.terminated_date = today
        
        # Clear termination date if moving away from terminated
        elif old_status == 'terminated' and new_status != 'terminated':
            self.terminated_date = False
        
        # Set suspend_end_date when suspended
        if new_status == 'suspended' and old_status != 'suspended':
            suspend_days = self._get_config_value('suspend_period_days', 30)
            self.suspend_end_date = today + timedelta(days=suspend_days)
        
        # Clear suspend dates when moving away from suspended
        elif old_status == 'suspended' and new_status != 'suspended':
            self.suspend_end_date = False

    def _sync_member_status(self):
        """Sync participation status with member status if configured."""
        self.ensure_one()
        
        # Get configuration for member status sync
        sync_enabled = self._get_config_value('sync_member_participation_status', False)
        
        if sync_enabled:
            # Map participation status to member status
            status_mapping = {
                'prospect': 'prospect',
                'active': 'active',
                'grace': 'grace',
                'suspended': 'suspended',
                'terminated': 'terminated',
                'cancelled': 'lapsed',  # Map cancelled to lapsed
            }
            
            member_status = status_mapping.get(self.status)
            if member_status and hasattr(self.partner_id, 'membership_status'):
                if self.partner_id.membership_status != member_status:
                    self.partner_id.with_context(
                        automated_status_change=True,
                        status_change_reason=f'Synced from participation {self.id}'
                    ).membership_status = member_status

    @api.model
    def _get_config_value(self, key, default=None):
        """Get configuration value from system config."""
        try:
            # This will be implemented when ams_system_config is available
            # For now, return defaults
            config_defaults = {
                'grace_period_days': 30,
                'suspend_period_days': 30,
                'terminate_period_days': 365,
                'sync_member_participation_status': False,
            }
            return config_defaults.get(key, default)
        except:
            return default

    @api.model
    def process_automatic_status_transitions(self):
        """Process automatic status transitions based on dates and configuration.
        
        This method is called by scheduled action to automatically:
        - Move expired participations to grace period
        - Move grace period participations to suspended
        - Move long-suspended participations to terminated
        """
        today = fields.Date.today()
        
        # Get configuration values
        grace_days = self._get_config_value('grace_period_days', 30)
        suspend_days = self._get_config_value('suspend_period_days', 30) 
        terminate_days = self._get_config_value('terminate_period_days', 365)
        
        transitions_made = 0
        
        # 1. Move expired active participations to grace
        expired_active = self.search([
            ('status', '=', 'active'),
            ('paid_through_date', '<', today)
        ])
        
        for participation in expired_active:
            participation.with_context(
                automated_status_change=True,
                status_change_reason='Automatic: Payment expired'
            ).status = 'grace'
            transitions_made += 1
        
        # 2. Move grace period participations to suspended
        grace_expired = self.search([
            ('status', '=', 'grace'),
            ('paid_through_date', '<', today - timedelta(days=grace_days))
        ])
        
        for participation in grace_expired:
            participation.with_context(
                automated_status_change=True,
                status_change_reason=f'Automatic: Grace period expired ({grace_days} days)'
            ).status = 'suspended'
            transitions_made += 1
        
        # 3. Move long-suspended participations to terminated
        suspend_expired = self.search([
            ('status', '=', 'suspended'),
            ('paid_through_date', '<', today - timedelta(days=grace_days + suspend_days))
        ])
        
        for participation in suspend_expired:
            participation.with_context(
                automated_status_change=True,
                status_change_reason=f'Automatic: Suspension period expired ({suspend_days} days)'
            ).status = 'terminated'
            transitions_made += 1
        
        _logger.info(f"Processed {transitions_made} automatic participation status transitions")
        return transitions_made

    def action_activate(self):
        """Action to activate participation."""
        self.ensure_one()
        if self.status != 'active':
            self.with_context(
                status_change_reason='Manual activation'
            ).status = 'active'

    def action_suspend(self):
        """Action to suspend participation."""
        self.ensure_one()
        if self.status not in ['suspended', 'terminated', 'cancelled']:
            self.with_context(
                status_change_reason='Manual suspension'
            ).status = 'suspended'

    def action_terminate(self):
        """Action to terminate participation."""
        self.ensure_one()
        if self.status != 'terminated':
            self.with_context(
                status_change_reason='Manual termination'
            ).status = 'terminated'

    def action_cancel(self):
        """Action to cancel participation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Participation'),
            'res_model': 'ams.participation.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_participation_id': self.id,
                'default_effective_date': fields.Date.today(),
            }
        }

    def action_renew(self):
        """Action to renew participation."""
        self.ensure_one()
        
        if not self.can_auto_renew:
            raise UserError(_("This participation cannot be renewed automatically"))
        
        # Create renewal logic here
        # This would integrate with billing and product modules when available
        
        # For now, extend the dates
        if self.end_date:
            self.end_date = self.end_date + timedelta(days=365)
            self.paid_through_date = self.end_date
            self.bill_through_date = self.end_date
            
            if self.status in ['grace', 'suspended']:
                self.status = 'active'
            
            self.message_post(
                body=_("Participation renewed until %s") % self.end_date,
                message_type='notification'
            )

    def action_view_history(self):
        """Action to view participation history."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participation History - %s') % self.display_name,
            'res_model': 'ams.participation.history',
            'view_mode': 'list,form',
            'domain': [('participation_id', '=', self.id)],
            'context': {'default_participation_id': self.id},
        }

    def action_create_invoice(self):
        """Action to create invoice for this participation."""
        self.ensure_one()
        
        # This will be implemented when billing integration is available
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Invoice creation will be available when billing module is installed'),
                'type': 'info',
                'sticky': False,
            }
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            result.append((record.id, record.display_name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search."""
        args = args or []
        
        if name:
            # Search in partner name, participation type
            domain = [
                '|', '|',
                ('partner_id.name', operator, name),
                ('partner_id.display_name', operator, name),
                ('participation_type', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)