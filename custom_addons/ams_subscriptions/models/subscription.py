from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription Management'
    _order = 'create_date desc, id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Subscription Name', 
        required=True, 
        tracking=True,
        help="Descriptive name for this subscription"
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Member', 
        required=True, 
        tracking=True,
        help="The member who owns this subscription"
    )
    
    subscription_type_id = fields.Many2one(
        'ams.subscription.type', 
        string='Subscription Type', 
        required=True, 
        tracking=True,
        help="Type of subscription (membership, chapter, publication)"
    )
    
    subscription_code = fields.Selection(
        related='subscription_type_id.code', 
        store=True, 
        string='Type Code',
        help="Code representing the subscription type"
    )
    
    # Subscription Status and Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('terminated', 'Terminated'),
        ('pending_renewal', 'Pending Renewal')
    ], string='Status', default='draft', required=True, tracking=True)
    
    lifecycle_stage = fields.Selection([
        ('new', 'New Subscription'),
        ('established', 'Established'),
        ('renewal_due', 'Renewal Due'),
        ('at_risk', 'At Risk'),
        ('churned', 'Churned')
    ], string='Lifecycle Stage', compute='_compute_lifecycle_stage', store=True)
    
    # Date Management
    start_date = fields.Date(
        string='Start Date', 
        required=True, 
        default=fields.Date.today,
        tracking=True,
        help="Date when the subscription becomes active"
    )
    
    end_date = fields.Date(
        string='End Date', 
        required=True,
        tracking=True,
        help="Date when the subscription expires"
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        help="Date through which payment has been received"
    )
    
    # Recurring and Renewal Configuration
    is_recurring = fields.Boolean(
        string='Is Recurring', 
        default=False, 
        tracking=True,
        help="Whether this subscription auto-renews"
    )
    
    recurring_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('yearly', 'Yearly')
    ], string='Recurring Period', default='yearly')
    
    auto_renewal = fields.Boolean(
        string='Auto Renewal', 
        default=True,
        tracking=True,
        help="Automatically process renewal when due"
    )
    
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        tracking=True,
        help="Date when the next renewal is due"
    )
    
    renewal_reminder_days = fields.Integer(
        string='Renewal Reminder (Days)', 
        default=30,
        help="Days before renewal to send reminder"
    )
    
    renewal_reminder_sent = fields.Boolean(
        string='Renewal Reminder Sent', 
        default=False,
        help="Whether renewal reminder has been sent"
    )
    
    last_renewal_date = fields.Date(
        string='Last Renewal Date',
        readonly=True,
        help="Date of the most recent renewal"
    )
    
    # Financial Information
    amount = fields.Monetary(
        string='Amount', 
        required=True, 
        default=0.0,
        currency_field='currency_id',
        tracking=True,
        help="Subscription amount per billing period"
    )
    
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        default=lambda self: self.env.company.currency_id, 
        required=True
    )
    
    payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed')
    ], string='Payment Status', default='paid', tracking=True)
    
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        currency_field='currency_id',
        compute='_compute_financial_info',
        store=True,
        help="Amount still owed on this subscription"
    )
    
    total_paid = fields.Monetary(
        string='Total Paid',
        currency_field='currency_id',
        compute='_compute_financial_info',
        store=True,
        help="Total amount paid for this subscription"
    )
    
    lifetime_value = fields.Monetary(
        string='Lifetime Value',
        currency_field='currency_id',
        compute='_compute_financial_info',
        store=True,
        help="Total value of this subscription over its lifetime"
    )
    
    last_payment_date = fields.Date(
        string='Last Payment Date',
        compute='_compute_financial_info',
        store=True,
        help="Date of the most recent payment"
    )
    
    # Product Integration
    product_id = fields.Many2one(
        'product.product', 
        string='Related Product',
        help="Product that created this subscription"
    )
    
    sale_order_line_id = fields.Many2one(
        'sale.order.line', 
        string='Source Sale Line',
        readonly=True,
        help="Sale order line that created this subscription"
    )
    
    # Invoice Integration
    invoice_ids = fields.One2many(
        'account.move', 
        'subscription_id', 
        string='Related Invoices',
        help="All invoices related to this subscription"
    )
    
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count', 
        store=True
    )
    
    original_invoice_id = fields.Many2one(
        'account.move',
        string='Original Invoice',
        readonly=True,
        help="The original invoice that created this subscription"
    )
    
    renewal_invoice_id = fields.Many2one(
        'account.move', 
        string='Current Renewal Invoice',
        help="Invoice for the current renewal process"
    )
    
    # Hierarchy for Parent-Child Relationships (Membership -> Chapters)
    parent_subscription_id = fields.Many2one(
        'ams.subscription', 
        string='Parent Subscription',
        domain="[('subscription_code', '=', 'membership'), ('partner_id', '=', partner_id)]",
        help="Parent membership subscription for chapter subscriptions"
    )
    
    child_subscription_ids = fields.One2many(
        'ams.subscription', 
        'parent_subscription_id', 
        string='Child Subscriptions',
        help="Chapter subscriptions linked to this membership"
    )
    
    # Chapter-specific Fields
    chapter_id = fields.Many2one(
        'ams.chapter', 
        string='Chapter',
        domain="[('active', '=', True)]",
        help="Chapter associated with this subscription"
    )
    
    chapter_region = fields.Char(
        related='chapter_id.region', 
        store=True, 
        readonly=True, 
        string='Chapter Region'
    )
    
    chapter_membership_number = fields.Char(
        string='Chapter Membership Number',
        help="Unique membership number within the chapter"
    )
    
    chapter_join_date = fields.Date(
        string='Chapter Join Date',
        help="Date when member joined this chapter"
    )
    
    chapter_role = fields.Selection([
        ('member', 'Member'),
        ('volunteer', 'Volunteer'),
        ('committee', 'Committee Member'),
        ('officer', 'Officer'),
        ('board', 'Board Member')
    ], string='Chapter Role', default='member')
    
    # Publication-specific Fields
    publication_format = fields.Selection([
        ('print', 'Print'),
        ('digital', 'Digital'),
        ('both', 'Print + Digital')
    ], string='Publication Format')
    
    delivery_address = fields.Text(
        string='Delivery Address',
        help="Address for print publication delivery"
    )
    
    digital_access_email = fields.Char(
        string='Digital Access Email',
        help="Email for digital publication access"
    )
    
    archive_access = fields.Boolean(
        string='Archive Access',
        default=True,
        help="Access to publication archives"
    )
    
    # Membership-specific Fields
    membership_number = fields.Char(
        string='Membership Number',
        help="Unique membership identifier"
    )
    
    membership_tier = fields.Selection([
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('elite', 'Elite'),
        ('lifetime', 'Lifetime')
    ], string='Membership Tier')
    
    member_since = fields.Date(
        string='Member Since',
        help="Date when member first joined the association"
    )
    
    voting_rights = fields.Boolean(
        string='Voting Rights',
        default=True,
        help="Whether member has voting rights"
    )
    
    board_eligible = fields.Boolean(
        string='Board Eligible',
        default=True,
        help="Whether member is eligible for board positions"
    )
    
    # Status History and Audit Trail
    status_history_ids = fields.One2many(
        'ams.subscription.status.history',
        'subscription_id',
        string='Status History',
        help="History of status changes for this subscription"
    )
    
    status_history_count = fields.Integer(
        string='Status Changes',
        compute='_compute_status_history_count',
        store=True
    )
    
    last_status_change = fields.Datetime(
        string='Last Status Change',
        readonly=True,
        help="When the status was last changed"
    )
    
    status_change_reason = fields.Text(
        string='Status Change Reason',
        help="Reason for the most recent status change"
    )
    
    # Lifecycle Management
    days_since_expiry = fields.Integer(
        string='Days Since Expiry',
        compute='_compute_lifecycle_info',
        help="Number of days since subscription expired"
    )
    
    days_until_renewal = fields.Integer(
        string='Days Until Renewal',
        compute='_compute_lifecycle_info',
        help="Number of days until renewal is due"
    )
    
    grace_period_expires = fields.Date(
        string='Grace Period Expires',
        compute='_compute_lifecycle_info',
        help="Date when grace period ends"
    )
    
    # Rules and Automation
    applicable_rules_ids = fields.Many2many(
        'ams.subscription.rule',
        string='Applicable Rules',
        help="Rules that apply to this subscription"
    )
    
    # Communication and Preferences
    email_notifications = fields.Boolean(
        string='Email Notifications',
        default=True,
        help="Send email notifications for this subscription"
    )
    
    renewal_reminders = fields.Boolean(
        string='Renewal Reminders',
        default=True,
        help="Send renewal reminder emails"
    )
    
    marketing_emails = fields.Boolean(
        string='Marketing Emails',
        default=True,
        help="Include in marketing email campaigns"
    )
    
    # Integration and External References
    external_reference = fields.Char(
        string='External Reference',
        help="Reference number from external system"
    )
    
    legacy_member_id = fields.Char(
        string='Legacy Member ID',
        help="Member ID from previous system"
    )
    
    third_party_sync_id = fields.Char(
        string='Third Party Sync ID',
        help="ID for syncing with third-party systems"
    )
    
    api_created = fields.Boolean(
        string='Created via API',
        default=False,
        help="Whether this subscription was created via API"
    )
    
    last_api_sync = fields.Datetime(
        string='Last API Sync',
        readonly=True,
        help="When this record was last synced via API"
    )
    
    sync_status = fields.Selection([
        ('synced', 'Synced'),
        ('pending', 'Pending Sync'),
        ('error', 'Sync Error'),
        ('manual', 'Manual Only')
    ], string='Sync Status', default='manual')
    
    # Additional Information
    notes = fields.Text(
        string='Notes',
        help="Public notes about this subscription"
    )
    
    internal_notes = fields.Text(
        string='Internal Notes',
        help="Internal notes for staff use only"
    )
    
    # Backward Compatibility
    subscription_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime')
    ], string='Billing Cycle', default='yearly', help="Legacy field for backward compatibility")

    # Compute Methods
    @api.depends('state', 'start_date', 'end_date', 'next_renewal_date')
    def _compute_lifecycle_stage(self):
        """Compute the current lifecycle stage of the subscription"""
        today = fields.Date.today()
        for subscription in self:
            if subscription.state == 'draft':
                subscription.lifecycle_stage = 'new'
            elif subscription.state == 'active':
                if subscription.next_renewal_date:
                    days_to_renewal = (subscription.next_renewal_date - today).days
                    if days_to_renewal <= 30:
                        subscription.lifecycle_stage = 'renewal_due'
                    else:
                        subscription.lifecycle_stage = 'established'
                else:
                    subscription.lifecycle_stage = 'established'
            elif subscription.state in ('grace', 'suspended'):
                subscription.lifecycle_stage = 'at_risk'
            elif subscription.state in ('expired', 'cancelled', 'terminated'):
                subscription.lifecycle_stage = 'churned'
            else:
                subscription.lifecycle_stage = 'new'

    @api.depends('end_date', 'next_renewal_date', 'subscription_type_id')
    def _compute_lifecycle_info(self):
        """Compute lifecycle-related information"""
        today = fields.Date.today()
        for subscription in self:
            # Days since expiry
            if subscription.end_date and subscription.end_date < today:
                subscription.days_since_expiry = (today - subscription.end_date).days
            else:
                subscription.days_since_expiry = 0
            
            # Days until renewal
            if subscription.next_renewal_date:
                subscription.days_until_renewal = (subscription.next_renewal_date - today).days
            else:
                subscription.days_until_renewal = 0
            
            # Grace period expiry
            if subscription.state == 'grace' and subscription.end_date:
                grace_days = getattr(subscription.subscription_type_id, 'grace_period_days', 30)
                subscription.grace_period_expires = subscription.end_date + relativedelta(days=grace_days)
            else:
                subscription.grace_period_expires = False

    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.amount_total')
    def _compute_financial_info(self):
        """Compute financial information from related invoices"""
        for subscription in self:
            invoices = subscription.invoice_ids.filtered(lambda i: i.state == 'posted')
            
            # Total paid
            paid_invoices = invoices.filtered(lambda i: i.payment_state == 'paid')
            subscription.total_paid = sum(paid_invoices.mapped('amount_total'))
            
            # Outstanding balance
            unpaid_invoices = invoices.filtered(lambda i: i.payment_state in ('not_paid', 'partial'))
            subscription.outstanding_balance = sum(unpaid_invoices.mapped('amount_residual'))
            
            # Last payment date
            if paid_invoices:
                subscription.last_payment_date = max(paid_invoices.mapped('invoice_date'))
            else:
                subscription.last_payment_date = False
            
            # Lifetime value (estimated)
            if subscription.is_recurring and subscription.amount:
                years_active = 1
                if subscription.start_date:
                    years_active = max(1, (fields.Date.today() - subscription.start_date).days / 365.25)
                
                if subscription.recurring_period == 'monthly':
                    subscription.lifetime_value = subscription.amount * 12 * years_active
                elif subscription.recurring_period == 'quarterly':
                    subscription.lifetime_value = subscription.amount * 4 * years_active
                elif subscription.recurring_period == 'semiannual':
                    subscription.lifetime_value = subscription.amount * 2 * years_active
                else:  # yearly
                    subscription.lifetime_value = subscription.amount * years_active
            else:
                subscription.lifetime_value = subscription.total_paid

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Compute the number of related invoices"""
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)

    @api.depends('status_history_ids')
    def _compute_status_history_count(self):
        """Compute the number of status changes"""
        for subscription in self:
            subscription.status_history_count = len(subscription.status_history_ids)

    # Model Creation and Validation
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set up subscription properly"""
        for vals in vals_list:
            # Auto-generate subscription name if not provided
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                subscription_type = self.env['ams.subscription.type'].browse(vals.get('subscription_type_id'))
                if partner and subscription_type:
                    vals['name'] = f"{subscription_type.name} - {partner.name}"
            
            # Ensure amount has a proper default
            if 'amount' not in vals or not vals['amount']:
                vals['amount'] = 0.0
            
            # Set paid_through_date if not provided
            if not vals.get('paid_through_date') and vals.get('end_date'):
                vals['paid_through_date'] = vals['end_date']
            
            # Set next renewal date if recurring
            if vals.get('is_recurring') and vals.get('end_date') and not vals.get('next_renewal_date'):
                vals['next_renewal_date'] = vals['end_date']
            
            # Auto-set membership number for membership subscriptions
            if vals.get('subscription_code') == 'membership' and not vals.get('membership_number'):
                vals['membership_number'] = self._generate_membership_number()

        subscriptions = super().create(vals_list)
        
        # Post-creation setup
        for subscription in subscriptions:
            subscription._handle_subscription_creation()
            subscription._create_status_history_entry(
                from_status=False,
                to_status=subscription.state,
                reason="Subscription created"
            )
        
        return subscriptions

    def write(self, vals):
        """Override write to track status changes"""
        # Track status changes
        if 'state' in vals:
            for subscription in self:
                if subscription.state != vals['state']:
                    subscription._create_status_history_entry(
                        from_status=subscription.state,
                        to_status=vals['state'],
                        reason=vals.get('status_change_reason', 'Status updated')
                    )
                    vals['last_status_change'] = fields.Datetime.now()
        
        result = super().write(vals)
        
        # Handle post-write logic
        if 'state' in vals:
            self._handle_status_change(vals['state'])
        
        return result

    # Business Logic Methods
    def _handle_subscription_creation(self):
        """Handle subscription type-specific creation logic"""
        self.ensure_one()
        
        if self.subscription_code == 'membership':
            self._handle_membership_creation()
        elif self.subscription_code == 'chapter':
            self._handle_chapter_creation()
        elif self.subscription_code == 'publication':
            self._handle_publication_creation()

    def _handle_membership_creation(self):
        """Handle membership-specific creation logic"""
        self.ensure_one()
        
        # Set member_since date if not set
        if not self.member_since:
            self.member_since = self.start_date
        
        # Auto-create chapter subscriptions if configured
        if self.product_id and hasattr(self.product_id, 'auto_create_chapters') and self.product_id.auto_create_chapters:
            if hasattr(self.product_id, 'default_chapter_ids') and self.product_id.default_chapter_ids:
                self._create_chapter_subscriptions(self.product_id.default_chapter_ids)

    def _handle_chapter_creation(self):
        """Handle chapter-specific creation logic"""
        self.ensure_one()
        
        # Validate parent subscription exists for chapters
        if not self.parent_subscription_id:
            raise UserError(_("Chapter subscriptions must have a parent membership."))
        
        # Validate parent subscription is active
        if self.parent_subscription_id.state != 'active':
            raise UserError(_("Parent membership must be active to add a chapter."))
        
        # Set chapter join date
        if not self.chapter_join_date:
            self.chapter_join_date = self.start_date
        
        # Auto-set amount from chapter if not set
        if self.chapter_id and not self.amount and hasattr(self.chapter_id, 'chapter_fee'):
            self.amount = self.chapter_id.chapter_fee or 0.0

    def _handle_publication_creation(self):
        """Handle publication-specific creation logic"""
        self.ensure_one()
        
        # Set digital access email if not provided
        if not self.digital_access_email and self.publication_format in ('digital', 'both'):
            self.digital_access_email = self.partner_id.email

    def _handle_status_change(self, new_state):
        """Handle status change business logic"""
        for subscription in self:
            if new_state == 'active':
                subscription._handle_activation()
            elif new_state == 'suspended':
                subscription._handle_suspension()
            elif new_state == 'terminated':
                subscription._handle_termination()

    def _handle_activation(self):
        """Handle subscription activation"""
        self.ensure_one()
        
        # Send activation email
        self._send_activation_email()
        
        # Update member access rights
        self._update_member_access()

    def _handle_suspension(self):
        """Handle subscription suspension"""
        self.ensure_one()
        
        # Send suspension notification
        self._send_suspension_email()
        
        # Revoke member access
        self._revoke_member_access()

    def _handle_termination(self):
        """Handle subscription termination"""
        self.ensure_one()
        
        # Send termination notification
        self._send_termination_email()
        
        # Complete cleanup
        self._complete_termination_cleanup()

    # Status Management Methods
    def action_activate(self):
        """Activate the subscription"""
        self.ensure_one()
        if self.state in ('draft', 'suspended'):
            self.state = 'active'
            self.message_post(body=_("Subscription activated"))
        else:
            raise UserError(_("Cannot activate subscription in current state"))

    def action_suspend(self):
        """Suspend the subscription"""
        self.ensure_one()
        if self.state in ('active', 'grace'):
            self.state = 'suspended'
            self.status_change_reason = _("Manual suspension")
            self.message_post(body=_("Subscription suspended"))
        else:
            raise UserError(_("Cannot suspend subscription in current state"))

    def action_terminate(self):
        """Terminate the subscription"""
        self.ensure_one()
        if self.state in ('active', 'grace', 'suspended', 'expired'):
            self.state = 'terminated'
            self.status_change_reason = _("Manual termination")
            self.message_post(body=_("Subscription terminated"))
        else:
            raise UserError(_("Cannot terminate subscription in current state"))

    def action_cancel(self):
        """Cancel the subscription"""
        self.ensure_one()
        if self.state in ('draft', 'active'):
            self.state = 'cancelled'
            self.status_change_reason = _("Manual cancellation")
            self.message_post(body=_("Subscription cancelled"))
        else:
            raise UserError(_("Cannot cancel subscription in current state"))

    def action_reactivate(self):
        """Reactivate a suspended or expired subscription"""
        self.ensure_one()
        if self.state in ('suspended', 'expired'):
            self.state = 'active'
            self.status_change_reason = _("Manual reactivation")
            self.message_post(body=_("Subscription reactivated"))
        else:
            raise UserError(_("Cannot reactivate subscription in current state"))

    # Renewal Methods
    def action_renew(self):
        """Manual renewal action"""
        self.ensure_one()
        if self.is_recurring:
            return self._create_renewal_invoice()
        else:
            # For non-recurring subscriptions, extend the end date
            if self.recurring_period == 'monthly':
                self.end_date = self.end_date + relativedelta(months=1)
            elif self.recurring_period == 'quarterly':
                self.end_date = self.end_date + relativedelta(months=3)
            elif self.recurring_period == 'semiannual':
                self.end_date = self.end_date + relativedelta(months=6)
            else:  # yearly
                self.end_date = self.end_date + relativedelta(years=1)
            
            self.paid_through_date = self.end_date
            self.next_renewal_date = self.end_date
            self.message_post(body=_("Subscription renewed manually"))

    def _create_renewal_invoice(self):
        """Create renewal invoice for subscription"""
        self.ensure_one()
        
        if not self.product_id:
            raise UserError(_("No product found for subscription renewal"))
        
        # Calculate new renewal period
        new_end_date = self._calculate_next_period_end()
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'is_renewal_invoice': True,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': self.amount,
                'name': f"Renewal: {self.name} ({self.end_date} - {new_end_date})",
            })]
        }
        
        renewal_invoice = self.env['account.move'].create(invoice_vals)
        
        # Update subscription
        self.write({
            'renewal_invoice_id': renewal_invoice.id,
            'state': 'pending_renewal',
        })
        
        # Also create renewal invoices for child subscriptions
        for child in self.child_subscription_ids.filtered(lambda c: c.is_recurring and c.auto_renewal):
            child._create_renewal_invoice()
        
        self.message_post(body=_("Renewal invoice created: %s") % renewal_invoice.name)
        return renewal_invoice

    def action_confirm_renewal(self):
        """Confirm renewal and extend subscription"""
        self.ensure_one()
        
        if not self.renewal_invoice_id:
            raise UserError(_("No renewal invoice found"))
        
        if self.renewal_invoice_id.payment_state != 'paid':
            raise UserError(_("Renewal invoice must be paid before confirming renewal"))
        
        # Extend subscription period
        new_end_date = self._calculate_next_period_end()
        
        self.write({
            'end_date': new_end_date,
            'paid_through_date': new_end_date,
            'next_renewal_date': new_end_date,
            'state': 'active',
            'renewal_invoice_id': False,
            'renewal_reminder_sent': False,
            'last_renewal_date': fields.Date.today(),
        })
        
        # Also renew child subscriptions
        for child in self.child_subscription_ids:
            if child.state == 'pending_renewal':
                child.action_confirm_renewal()
        
        self.message_post(body=_("Subscription renewed until %s") % new_end_date)

    def _calculate_next_period_end(self):
        """Calculate the end date for the next period"""
        self.ensure_one()
        current_end = self.end_date or fields.Date.today()
        
        if self.recurring_period == 'monthly':
            return current_end + relativedelta(months=1)
        elif self.recurring_period == 'quarterly':
            return current_end + relativedelta(months=3)
        elif self.recurring_period == 'semiannual':
            return current_end + relativedelta(months=6)
        else:  # yearly
            return current_end + relativedelta(years=1)

    # Utility Methods
    def _generate_membership_number(self):
        """Generate a unique membership number"""
        sequence = self.env['ir.sequence'].next_by_code('ams.membership.number') or '0001'
        return f"MEM{sequence}"

    def _create_status_history_entry(self, from_status, to_status, reason):
        """Create a status history entry"""
        self.ensure_one()
        self.env['ams.subscription.status.history'].create({
            'subscription_id': self.id,
            'from_status': from_status,
            'to_status': to_status,
            'date': fields.Datetime.now(),
            'reason': reason,
            'user_id': self.env.user.id,
            'automatic': False,
        })

    def _create_chapter_subscriptions(self, chapter_ids):
        """Create chapter subscriptions for a membership"""
        self.ensure_one()
        
        if self.subscription_code != 'membership':
            return
        
        chapter_type = self.env['ams.subscription.type'].search([('code', '=', 'chapter')], limit=1)
        if not chapter_type:
            _logger.warning("No chapter subscription type found")
            return
        
        for chapter in chapter_ids:
            chapter_vals = {
                'partner_id': self.partner_id.id,
                'subscription_type_id': chapter_type.id,
                'parent_subscription_id': self.id,
                'chapter_id': chapter.id,
                'name': f"Chapter {chapter.name} - {self.partner_id.name}",
                'start_date': self.start_date,
                'end_date': self.end_date,
                'amount': getattr(chapter, 'chapter_fee', 0.0),
                'is_recurring': self.is_recurring,
                'recurring_period': self.recurring_period,
                'auto_renewal': self.auto_renewal,
                'next_renewal_date': self.next_renewal_date,
                'state': 'active',
            }
            
            self.env['ams.subscription'].create(chapter_vals)

    # Email Methods
    def _send_activation_email(self):
        """Send subscription activation email"""
        template = self.env.ref('ams_subscriptions.email_template_subscription_activated', False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_suspension_email(self):
        """Send subscription suspension email"""
        template = self.env.ref('ams_subscriptions.email_template_suspension_notification', False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_termination_email(self):
        """Send subscription termination email"""
        template = self.env.ref('ams_subscriptions.email_template_termination_notification', False)
        if template:
            template.send_mail(self.id, force_send=True)

    # Access Management
    def _update_member_access(self):
        """Update member access rights based on subscription"""
        # Implement member access logic here
        pass

    def _revoke_member_access(self):
        """Revoke member access rights"""
        # Implement access revocation logic here
        pass

    def _complete_termination_cleanup(self):
        """Complete cleanup tasks for terminated subscriptions"""
        # Implement cleanup logic here
        pass

    # View Actions
    def action_view_invoices(self):
        """Action to view related invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }

    def action_view_renewal_invoice(self):
        """Action to view renewal invoice"""
        self.ensure_one()
        if self.renewal_invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renewal Invoice'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.renewal_invoice_id.id,
                'context': {'default_partner_id': self.partner_id.id}
            }

    def action_view_partner(self):
        """Action to view the partner/member"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
        }

    def action_view_subscription_history(self):
        """Action to view subscription status history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Status History'),
            'res_model': 'ams.subscription.status.history',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
        }

    # Constraints and Validation
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate subscription dates"""
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("Start date cannot be after end date"))

    @api.constrains('amount')
    def _check_amount(self):
        """Validate subscription amount"""
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("Subscription amount cannot be negative"))

    @api.constrains('parent_subscription_id', 'subscription_code')
    def _check_parent_subscription(self):
        """Validate parent subscription requirements"""
        for record in self:
            if record.subscription_code == 'chapter' and not record.parent_subscription_id:
                raise ValidationError(_("Chapter subscriptions require a parent membership"))
            
            if record.parent_subscription_id and record.parent_subscription_id.subscription_code != 'membership':
                raise ValidationError(_("Parent subscription must be a membership type"))

    @api.constrains('chapter_id', 'subscription_code')
    def _check_chapter_requirements(self):
        """Validate chapter requirements for chapter subscriptions"""
        for record in self:
            if record.subscription_code == 'chapter' and not record.chapter_id:
                raise ValidationError(_("Chapter subscriptions must have a chapter selected"))

    # Onchange Methods
    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        """Update fields based on subscription type"""
        if self.subscription_type_id:
            # Set defaults from subscription type
            if hasattr(self.subscription_type_id, 'default_renewal_period'):
                self.recurring_period = self.subscription_type_id.default_renewal_period
            if hasattr(self.subscription_type_id, 'auto_renewal_default'):
                self.auto_renewal = self.subscription_type_id.auto_renewal_default
            
            # Clear type-specific fields
            if self.subscription_type_id.code != 'chapter':
                self.chapter_id = False
                self.parent_subscription_id = False
            if self.subscription_type_id.code != 'publication':
                self.publication_format = False

    @api.onchange('chapter_id')
    def _onchange_chapter_id(self):
        """Auto-populate amount and product when chapter is selected"""
        if self.chapter_id and self.subscription_code == 'chapter':
            if hasattr(self.chapter_id, 'chapter_fee') and self.chapter_id.chapter_fee:
                if not self.amount or self.amount == 0.0:
                    self.amount = self.chapter_id.chapter_fee
            if hasattr(self.chapter_id, 'product_template_id') and self.chapter_id.product_template_id:
                self.product_id = self.chapter_id.product_template_id.product_variant_id

    @api.onchange('is_recurring', 'recurring_period', 'end_date')
    def _onchange_renewal_settings(self):
        """Update renewal date when renewal settings change"""
        if self.is_recurring and self.end_date:
            self.next_renewal_date = self.end_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        """Update paid through date when end date changes"""
        if self.end_date and not self.paid_through_date:
            self.paid_through_date = self.end_date

    # SQL Constraints
    _sql_constraints = [
        ('amount_positive', 'CHECK(amount >= 0)', 'Subscription amount must be positive or zero'),
        ('dates_valid', 'CHECK(start_date <= end_date)', 'Start date must be before or equal to end date'),
    ]