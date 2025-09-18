# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionRenewal(models.Model):
    """
    AMS Subscription Renewal management for professional associations.
    Handles renewal workflows, reminders, and automated processing.
    """
    _name = 'ams.subscription.renewal'
    _description = 'AMS Subscription Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_due_date asc, id desc'

    # ========================================================================
    # CORE RENEWAL FIELDS
    # ========================================================================

    name = fields.Char(
        string="Renewal Reference",
        required=True,
        copy=False,
        default=lambda self: _('New Renewal'),
        help="Unique reference for this renewal"
    )

    subscription_id = fields.Many2one(
        'sale.subscription',
        string="Subscription",
        required=True,
        ondelete='cascade',
        help="Subscription to be renewed"
    )

    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string="Customer",
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        'product.template',
        string="Subscription Product",
        required=True,
        domain=[('ams_product_behavior', '=', 'subscription')],
        help="Subscription product being renewed"
    )

    billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Billing Period",
        required=True,
        help="Billing period for renewal"
    )

    # ========================================================================
    # RENEWAL DATE MANAGEMENT
    # ========================================================================

    current_period_end = fields.Date(
        string="Current Period End",
        required=True,
        help="End date of current subscription period"
    )

    renewal_due_date = fields.Date(
        string="Renewal Due Date",
        required=True,
        help="Date when renewal is due"
    )

    grace_period_end = fields.Date(
        string="Grace Period End",
        compute='_compute_grace_period_end',
        store=True,
        help="End of grace period for renewal"
    )

    renewal_processed_date = fields.Date(
        string="Renewal Processed Date",
        help="Date when renewal was processed"
    )

    next_renewal_due = fields.Date(
        string="Next Renewal Due",
        compute='_compute_next_renewal_due',
        store=True,
        help="Next renewal due date after this renewal"
    )

    days_until_renewal = fields.Integer(
        string="Days Until Renewal",
        compute='_compute_days_until_renewal',
        help="Number of days until renewal is due"
    )

    is_overdue = fields.Boolean(
        string="Is Overdue",
        compute='_compute_overdue_status',
        help="Whether renewal is overdue"
    )

    # ========================================================================
    # RENEWAL PRICING AND TERMS
    # ========================================================================

    current_price = fields.Monetary(
        string="Current Price",
        help="Current subscription price"
    )

    renewal_price = fields.Monetary(
        string="Renewal Price",
        compute='_compute_renewal_pricing',
        store=True,
        help="Calculated renewal price"
    )

    member_discount_amount = fields.Monetary(
        string="Member Discount",
        compute='_compute_renewal_pricing',
        store=True,
        help="Member discount for renewal"
    )

    price_increase_amount = fields.Monetary(
        string="Price Increase",
        compute='_compute_renewal_pricing',
        store=True,
        help="Price increase from current period"
    )

    price_increase_percent = fields.Float(
        string="Price Increase %",
        compute='_compute_renewal_pricing',
        store=True,
        help="Percentage price increase"
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        string="Currency",
        store=True,
        readonly=True
    )

    # ========================================================================
    # RENEWAL STATUS AND PROCESSING
    # ========================================================================

    state = fields.Selection([
        ('pending', 'Pending Renewal'),
        ('reminded', 'Reminder Sent'),
        ('processing', 'Processing Renewal'),
        ('renewed', 'Renewed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('grace_period', 'In Grace Period'),
    ], string="Status",
       default='pending',
       tracking=True,
       help="Current renewal status")

    renewal_method = fields.Selection([
        ('manual', 'Manual Renewal'),
        ('automatic', 'Automatic Renewal'),
        ('member_portal', 'Member Portal Self-Service'),
    ], string="Renewal Method",
       help="Method used for renewal processing")

    auto_renewal_enabled = fields.Boolean(
        string="Auto Renewal Enabled",
        related='product_id.subscription_auto_renewal',
        help="Whether automatic renewal is enabled"
    )

    renewal_terms_accepted = fields.Boolean(
        string="Terms Accepted",
        default=False,
        help="Whether customer has accepted renewal terms"
    )

    renewal_terms_date = fields.Date(
        string="Terms Acceptance Date",
        help="Date when renewal terms were accepted"
    )

    # ========================================================================
    # MEMBER AND CUSTOMER INFORMATION
    # ========================================================================

    is_member_renewal = fields.Boolean(
        string="Member Renewal",
        compute='_compute_member_status',
        store=True,
        help="Whether this is a member renewal"
    )

    member_status = fields.Selection(
        related='partner_id.membership_status',
        string="Member Status",
        store=True,
        readonly=True
    )

    membership_expiry_date = fields.Date(
        string="Membership Expiry",
        related='partner_id.membership_expiry_date',
        help="Current membership expiry date"
    )

    # ========================================================================
    # RENEWAL COMMUNICATION AND REMINDERS
    # ========================================================================

    reminder_count = fields.Integer(
        string="Reminders Sent",
        default=0,
        help="Number of renewal reminders sent"
    )

    last_reminder_date = fields.Date(
        string="Last Reminder Date",
        help="Date of last renewal reminder"
    )

    reminder_schedule = fields.Char(
        string="Reminder Schedule",
        related='product_id.subscription_renewal_reminder_days',
        help="Scheduled reminder days (comma-separated)"
    )

    next_reminder_date = fields.Date(
        string="Next Reminder Date",
        compute='_compute_next_reminder_date',
        store=True,
        help="Date for next scheduled reminder"
    )

    renewal_welcome_sent = fields.Boolean(
        string="Welcome Email Sent",
        default=False,
        help="Whether renewal welcome email has been sent"
    )

    # ========================================================================
    # RENEWAL HISTORY AND TRACKING
    # ========================================================================

    previous_renewal_id = fields.Many2one(
        'ams.subscription.renewal',
        string="Previous Renewal",
        help="Link to previous renewal record"
    )

    renewal_count = fields.Integer(
        string="Renewal Count",
        default=1,
        help="Number of times this subscription has been renewed"
    )

    first_subscription_date = fields.Date(
        string="First Subscription Date",
        help="Date when subscription was first created"
    )

    customer_lifetime_value = fields.Monetary(
        string="Customer Lifetime Value",
        compute='_compute_customer_lifetime_value',
        help="Total value from this customer's subscriptions"
    )

    # ========================================================================
    # RENEWAL NOTES AND COMMUNICATION
    # ========================================================================

    renewal_notes = fields.Text(
        string="Renewal Notes",
        help="Internal notes about this renewal"
    )

    customer_renewal_message = fields.Text(
        string="Customer Message",
        help="Message from customer regarding renewal"
    )

    renewal_terms_notes = fields.Text(
        string="Terms and Conditions Notes",
        help="Special terms and conditions for this renewal"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('renewal_due_date', 'product_id.subscription_grace_period')
    def _compute_grace_period_end(self):
        """Calculate grace period end date."""
        for renewal in self:
            if renewal.renewal_due_date and renewal.product_id.subscription_grace_period:
                renewal.grace_period_end = renewal.renewal_due_date + timedelta(
                    days=renewal.product_id.subscription_grace_period
                )
            else:
                renewal.grace_period_end = renewal.renewal_due_date

    @api.depends('renewal_due_date', 'billing_period_id')
    def _compute_next_renewal_due(self):
        """Calculate next renewal due date."""
        for renewal in self:
            if renewal.renewal_due_date and renewal.billing_period_id:
                renewal.next_renewal_due = renewal.billing_period_id.calculate_next_date(
                    renewal.renewal_due_date
                )
            else:
                renewal.next_renewal_due = False

    @api.depends('renewal_due_date')
    def _compute_days_until_renewal(self):
        """Calculate days until renewal."""
        today = fields.Date.today()
        for renewal in self:
            if renewal.renewal_due_date:
                delta = renewal.renewal_due_date - today
                renewal.days_until_renewal = delta.days
            else:
                renewal.days_until_renewal = 0

    @api.depends('renewal_due_date', 'grace_period_end', 'state')
    def _compute_overdue_status(self):
        """Determine if renewal is overdue."""
        today = fields.Date.today()
        for renewal in self:
            if renewal.state in ['renewed', 'cancelled']:
                renewal.is_overdue = False
            elif renewal.grace_period_end:
                renewal.is_overdue = today > renewal.grace_period_end
            else:
                renewal.is_overdue = today > renewal.renewal_due_date

    @api.depends('partner_id', 'product_id', 'current_price')
    def _compute_renewal_pricing(self):
        """Calculate renewal pricing including discounts and increases."""
        for renewal in self:
            if not renewal.partner_id or not renewal.product_id:
                renewal.renewal_price = 0.0
                renewal.member_discount_amount = 0.0
                renewal.price_increase_amount = 0.0
                renewal.price_increase_percent = 0.0
                continue

            # Get current pricing for partner
            pricing = renewal.product_id.calculate_subscription_pricing_for_partner(
                renewal.partner_id
            )
            
            renewal.renewal_price = pricing.get('base_price', 0.0)
            renewal.member_discount_amount = pricing.get('member_savings', 0.0)
            
            # Calculate price increase
            if renewal.current_price > 0:
                renewal.price_increase_amount = renewal.renewal_price - renewal.current_price
                renewal.price_increase_percent = (
                    renewal.price_increase_amount / renewal.current_price * 100
                )
            else:
                renewal.price_increase_amount = 0.0
                renewal.price_increase_percent = 0.0

    @api.depends('partner_id.is_member', 'partner_id.membership_status')
    def _compute_member_status(self):
        """Determine if this is a member renewal."""
        for renewal in self:
            renewal.is_member_renewal = (
                renewal.partner_id.is_member and 
                renewal.partner_id.membership_status == 'active'
            )

    @api.depends('reminder_schedule', 'renewal_due_date', 'reminder_count', 'last_reminder_date')
    def _compute_next_reminder_date(self):
        """Calculate next reminder date based on schedule."""
        for renewal in self:
            if not renewal.reminder_schedule or renewal.state in ['renewed', 'cancelled']:
                renewal.next_reminder_date = False
                continue

            try:
                reminder_days = [int(d.strip()) for d in renewal.reminder_schedule.split(',')]
                reminder_days.sort(reverse=True)  # Sort descending
                
                # Find next reminder day
                for days_before in reminder_days:
                    reminder_date = renewal.renewal_due_date - timedelta(days=days_before)
                    
                    # Check if this reminder hasn't been sent yet
                    if (reminder_date > fields.Date.today() or
                        not renewal.last_reminder_date or
                        reminder_date > renewal.last_reminder_date):
                        renewal.next_reminder_date = reminder_date
                        break
                else:
                    renewal.next_reminder_date = False
                    
            except (ValueError, AttributeError):
                renewal.next_reminder_date = False

    @api.depends('partner_id')
    def _compute_customer_lifetime_value(self):
        """Calculate customer lifetime value from all subscriptions."""
        for renewal in self:
            if not renewal.partner_id:
                renewal.customer_lifetime_value = 0.0
                continue

            # Sum all billing amounts for this customer's subscriptions
            billing_total = self.env['ams.subscription.billing'].search([
                ('partner_id', '=', renewal.partner_id.id),
                ('state', 'in', ['billed', 'paid'])
            ]).mapped('total_amount')
            
            renewal.customer_lifetime_value = sum(billing_total)

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Update fields when subscription changes."""
        if self.subscription_id:
            # Get subscription details
            if self.subscription_id.template_id and self.subscription_id.template_id.product_id:
                self.product_id = self.subscription_id.template_id.product_id.product_tmpl_id
            
            # Set dates from subscription
            self.current_period_end = self.subscription_id.date
            self.renewal_due_date = self.subscription_id.date
            self.current_price = self.subscription_id.recurring_total

    @api.onchange('renewal_due_date')
    def _onchange_renewal_due_date(self):
        """Update state when renewal due date changes."""
        if self.renewal_due_date:
            today = fields.Date.today()
            if self.renewal_due_date < today and self.state == 'pending':
                if self.grace_period_end and today <= self.grace_period_end:
                    self.state = 'grace_period'
                else:
                    self.state = 'expired'

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create with renewal reference generation."""
        for vals in vals_list:
            if vals.get('name', _('New Renewal')) == _('New Renewal'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.subscription.renewal') or _('New Renewal')
        
        renewals = super().create(vals_list)
        
        # Log renewal creation and schedule reminders
        for renewal in renewals:
            _logger.info(f"Created subscription renewal: {renewal.name} due {renewal.renewal_due_date}")
            
            # Schedule first reminder if auto-renewal is enabled
            if renewal.auto_renewal_enabled:
                renewal._schedule_renewal_reminders()
        
        return renewals

    def write(self, vals):
        """Enhanced write with state change tracking."""
        # Track state changes
        if 'state' in vals:
            for renewal in self:
                if renewal.state != vals['state']:
                    renewal.message_post(
                        body=_("Renewal status changed from %s to %s") % (
                            dict(self._fields['state'].selection)[renewal.state],
                            dict(self._fields['state'].selection)[vals['state']]
                        )
                    )
        
        return super().write(vals)

    # ========================================================================
    # RENEWAL PROCESSING METHODS
    # ========================================================================

    def process_renewal(self, renewal_method='automatic'):
        """
        Process subscription renewal.
        
        Args:
            renewal_method (str): Method used for renewal
            
        Returns:
            bool: Success status
        """
        self.ensure_one()
        
        if self.state not in ['pending', 'reminded', 'grace_period']:
            raise UserError(_("Only pending renewals can be processed"))
        
        try:
            self.write({
                'state': 'processing',
                'renewal_method': renewal_method,
            })
            
            # Create new billing cycle
            billing = self._create_renewal_billing()
            
            if billing:
                # Update subscription dates
                self._update_subscription_dates()
                
                # Update renewal status
                self.write({
                    'state': 'renewed',
                    'renewal_processed_date': fields.Date.today(),
                    'renewal_terms_accepted': True,
                    'renewal_terms_date': fields.Date.today(),
                })
                
                # Send renewal confirmation
                self._send_renewal_confirmation()
                
                # Create next renewal record
                self._create_next_renewal()
                
                _logger.info(f"Successfully processed renewal {self.name}")
                return True
            
        except Exception as e:
            self.write({'state': 'pending'})  # Reset state on failure
            _logger.error(f"Failed to process renewal {self.name}: {e}")
            raise UserError(_("Renewal processing failed: %s") % str(e))
        
        return False

    def _create_renewal_billing(self):
        """
        Create billing record for renewal.
        
        Returns:
            ams.subscription.billing: Created billing record
        """
        self.ensure_one()
        
        billing_vals = {
            'subscription_id': self.subscription_id.id,
            'product_id': self.product_id.id,
            'billing_period_id': self.billing_period_id.id,
            'billing_date': self.renewal_due_date,
            'period_start_date': self.renewal_due_date,
            'period_end_date': self.next_renewal_due - timedelta(days=1) if self.next_renewal_due else self.renewal_due_date + timedelta(days=365),
            'billing_type': 'recurring',
            'base_amount': self.renewal_price,
            'state': 'scheduled',
        }
        
        billing = self.env['ams.subscription.billing'].create(billing_vals)
        
        # Calculate billing amounts
        billing.calculate_billing_amounts()
        
        return billing

    def _update_subscription_dates(self):
        """Update subscription with new renewal dates."""
        self.ensure_one()
        
        if self.subscription_id:
            # Update subscription end date
            new_end_date = self.next_renewal_due if self.next_renewal_due else self.renewal_due_date + timedelta(days=365)
            
            self.subscription_id.write({
                'date': new_end_date,
            })

    def _create_next_renewal(self):
        """Create next renewal record."""
        self.ensure_one()
        
        if not self.next_renewal_due:
            return False
        
        next_renewal_vals = {
            'subscription_id': self.subscription_id.id,
            'product_id': self.product_id.id,
            'billing_period_id': self.billing_period_id.id,
            'current_period_end': self.next_renewal_due,
            'renewal_due_date': self.next_renewal_due,
            'current_price': self.renewal_price,
            'previous_renewal_id': self.id,
            'renewal_count': self.renewal_count + 1,
            'first_subscription_date': self.first_subscription_date or self.subscription_id.date_start,
        }
        
        return self.env['ams.subscription.renewal'].create(next_renewal_vals)

    # ========================================================================
    # REMINDER AND COMMUNICATION METHODS
    # ========================================================================

    def send_renewal_reminder(self, force_send=False):
        """
        Send renewal reminder to customer.
        
        Args:
            force_send (bool): Force send even if not scheduled
            
        Returns:
            bool: Success status
        """
        self.ensure_one()
        
        if not force_send and self.next_reminder_date != fields.Date.today():
            return False
        
        if not self.partner_id.email:
            _logger.warning(f"No email address for renewal reminder {self.name}")
            return False
        
        # Get appropriate email template
        template = self._get_renewal_reminder_template()
        
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                
                self.write({
                    'reminder_count': self.reminder_count + 1,
                    'last_reminder_date': fields.Date.today(),
                    'state': 'reminded' if self.state == 'pending' else self.state,
                })
                
                _logger.info(f"Sent renewal reminder for {self.name}")
                return True
                
            except Exception as e:
                _logger.error(f"Failed to send renewal reminder for {self.name}: {e}")
                return False
        
        return False

    def _get_renewal_reminder_template(self):
        """Get appropriate renewal reminder email template."""
        self.ensure_one()
        
        # Try product-specific template first
        if self.product_id.subscription_renewal_reminder_template_id:
            return self.product_id.subscription_renewal_reminder_template_id
        
        # Try default template
        template = self.env.ref('ams_subscriptions_products.renewal_reminder_template', False)
        return template

    def _send_renewal_confirmation(self):
        """Send renewal confirmation to customer."""
        self.ensure_one()
        
        if not self.partner_id.email:
            return False
        
        # Get renewal confirmation template
        template = self._get_renewal_confirmation_template()
        
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                
                self.write({
                    'renewal_welcome_sent': True,
                })
                
                return True
                
            except Exception as e:
                _logger.error(f"Failed to send renewal confirmation for {self.name}: {e}")
        
        return False

    def _get_renewal_confirmation_template(self):
        """Get renewal confirmation email template."""
        self.ensure_one()
        
        # Try product-specific template
        if self.product_id.subscription_welcome_template_id:
            return self.product_id.subscription_welcome_template_id
        
        # Try default template
        template = self.env.ref('ams_subscriptions_products.renewal_confirmation_template', False)
        return template

    def _schedule_renewal_reminders(self):
        """Schedule all renewal reminders based on product configuration."""
        self.ensure_one()
        
        if not self.reminder_schedule:
            return False
        
        try:
            reminder_days = [int(d.strip()) for d in self.reminder_schedule.split(',')]
            
            # Create scheduled actions or activities for reminders
            for days_before in reminder_days:
                reminder_date = self.renewal_due_date - timedelta(days=days_before)
                
                if reminder_date >= fields.Date.today():
                    # Create activity for reminder
                    self.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=reminder_date,
                        summary=_('Send Renewal Reminder'),
                        note=_('Send renewal reminder for subscription %s') % self.subscription_id.name,
                        user_id=self.env.user.id,
                    )
            
            return True
            
        except (ValueError, AttributeError):
            _logger.warning(f"Invalid reminder schedule for renewal {self.name}: {self.reminder_schedule}")
            return False

    # ========================================================================
    # RENEWAL AUTOMATION METHODS
    # ========================================================================

    @api.model
    def process_automatic_renewals(self):
        """Process all automatic renewals due today."""
        auto_renewals = self.search([
            ('state', 'in', ['pending', 'reminded', 'grace_period']),
            ('auto_renewal_enabled', '=', True),
            ('renewal_due_date', '<=', fields.Date.today()),
        ])
        
        success_count = 0
        error_count = 0
        
        for renewal in auto_renewals:
            try:
                if renewal.process_renewal('automatic'):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                _logger.error(f"Auto-renewal failed for {renewal.name}: {e}")
                error_count += 1
        
        _logger.info(
            f"Processed automatic renewals: {success_count} successful, {error_count} failed"
        )
        
        return {
            'success_count': success_count,
            'error_count': error_count,
        }

    @api.model
    def send_scheduled_reminders(self):
        """Send all scheduled renewal reminders for today."""
        due_reminders = self.search([
            ('state', 'in', ['pending', 'reminded']),
            ('next_reminder_date', '=', fields.Date.today()),
        ])
        
        sent_count = 0
        error_count = 0
        
        for renewal in due_reminders:
            if renewal.send_renewal_reminder():
                sent_count += 1
            else:
                error_count += 1
        
        _logger.info(
            f"Sent renewal reminders: {sent_count} successful, {error_count} failed"
        )
        
        return {
            'sent_count': sent_count,
            'error_count': error_count,
        }

    @api.model
    def update_overdue_renewals(self):
        """Update status of overdue renewals."""
        # Move pending/reminded renewals to grace period
        grace_renewals = self.search([
            ('state', 'in', ['pending', 'reminded']),
            ('renewal_due_date', '<', fields.Date.today()),
            ('grace_period_end', '>=', fields.Date.today()),
        ])
        
        grace_renewals.write({'state': 'grace_period'})
        
        # Move renewals past grace period to expired
        expired_renewals = self.search([
            ('state', '!=', 'expired'),
            ('grace_period_end', '<', fields.Date.today()),
            ('state', 'not in', ['renewed', 'cancelled']),
        ])
        
        expired_renewals.write({'state': 'expired'})
        
        _logger.info(
            f"Updated overdue renewals: {len(grace_renewals)} to grace period, "
            f"{len(expired_renewals)} to expired"
        )
        
        return {
            'grace_period_count': len(grace_renewals),
            'expired_count': len(expired_renewals),
        }

    # ========================================================================
    # QUERY AND UTILITY METHODS
    # ========================================================================

    @api.model
    def get_renewals_due_soon(self, days_ahead=30):
        """Get renewals due within specified days."""
        cutoff_date = fields.Date.today() + timedelta(days=days_ahead)
        
        return self.search([
            ('state', 'in', ['pending', 'reminded']),
            ('renewal_due_date', '<=', cutoff_date),
        ])

    @api.model
    def get_overdue_renewals(self):
        """Get all overdue renewals."""
        return self.search([
            ('state', 'in', ['grace_period', 'expired']),
        ])

    @api.model
    def get_member_renewals(self, member_status='active'):
        """Get renewals for members with specific status."""
        return self.search([
            ('is_member_renewal', '=', True),
            ('member_status', '=', member_status),
        ])

    def cancel_renewal(self):
        """Cancel renewal."""
        for renewal in self:
            if renewal.state in ['renewed']:
                raise UserError(_("Cannot cancel completed renewals"))
            
            renewal.write({
                'state': 'cancelled',
                'renewal_processed_date': fields.Date.today(),
            })
            
            # Cancel related activities
            renewal.activity_ids.action_done()

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('renewal_due_date', 'current_period_end')
    def _check_renewal_dates(self):
        """Validate renewal dates."""
        for renewal in self:
            if renewal.renewal_due_date and renewal.current_period_end:
                if renewal.renewal_due_date < renewal.current_period_end:
                    raise ValidationError(
                        _("Renewal due date cannot be before current period end date")
                    )

    @api.constrains('renewal_count')
    def _check_renewal_count(self):
        """Validate renewal count."""
        for renewal in self:
            if renewal.renewal_count < 1:
                raise ValidationError(_("Renewal count must be at least 1"))

    # ========================================================================
    # REPORTING AND ANALYTICS
    # ========================================================================

    def get_renewal_summary(self):
        """Get summary of renewal details."""
        self.ensure_one()
        
        return {
            'renewal_reference': self.name,
            'subscription': self.subscription_id.name,
            'customer': self.partner_id.name,
            'product': self.product_id.name,
            'due_date': self.renewal_due_date,
            'days_until_due': self.days_until_renewal,
            'current_price': self.current_price,
            'renewal_price': self.renewal_price,
            'price_increase': self.price_increase_amount,
            'price_increase_percent': self.price_increase_percent,
            'member_discount': self.member_discount_amount,
            'state': dict(self._fields['state'].selection)[self.state],
            'is_member': self.is_member_renewal,
            'is_overdue': self.is_overdue,
            'auto_renewal': self.auto_renewal_enabled,
            'reminders_sent': self.reminder_count,
            'lifetime_value': self.customer_lifetime_value,
        }

    @api.model
    def get_renewal_analytics(self, date_from=None, date_to=None):
        """Get renewal analytics for reporting."""
        domain = []
        
        if date_from:
            domain.append(('renewal_due_date', '>=', date_from))
        if date_to:
            domain.append(('renewal_due_date', '<=', date_to))
        
        renewals = self.search(domain)
        
        return {
            'total_renewals': len(renewals),
            'member_renewals': len(renewals.filtered('is_member_renewal')),
            'auto_renewals': len(renewals.filtered('auto_renewal_enabled')),
            'overdue_renewals': len(renewals.filtered('is_overdue')),
            'total_renewal_value': sum(renewals.mapped('renewal_price')),
            'average_renewal_price': sum(renewals.mapped('renewal_price')) / len(renewals) if renewals else 0,
            'price_increases': len(renewals.filtered(lambda r: r.price_increase_amount > 0)),
            'average_price_increase': sum(renewals.mapped('price_increase_amount')) / len(renewals) if renewals else 0,
            'by_state': {
                state: len(renewals.filtered(lambda r: r.state == state))
                for state in dict(self._fields['state'].selection).keys()
            },
            'by_method': {
                method: len(renewals.filtered(lambda r: r.renewal_method == method))
                for method in dict(self._fields['renewal_method'].selection).keys()
                if method
            },
            'customer_lifetime_value': sum(renewals.mapped('customer_lifetime_value')),
        }