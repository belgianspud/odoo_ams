# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscription(models.Model):
    """
    Enhanced AMS Subscription Model - Layer 2 Architecture
    
    Focuses on subscription lifecycle management, customer experience, and 
    integration with ams_products_base and ams_billing_periods.
    
    Layer 2 Responsibilities:
    - Subscription lifecycle states and automation
    - Payment tracking and NSF management  
    - Customer portal integration and self-service
    - Enterprise seat management
    - Modification and cancellation workflows
    - Integration with billing periods for accurate dating
    """
    _name = 'ams.subscription'
    _description = 'AMS Subscription - Enhanced'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'start_date desc, name'
    
    # ========================================================================
    # CORE SUBSCRIPTION FIELDS
    # ========================================================================
    
    name = fields.Char(
        string='Subscription Name',
        required=True,
        tracking=True,
        help='Descriptive name for this subscription'
    )
    
    # Customer and Account Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        help='Primary customer/contact for this subscription'
    )
    
    account_id = fields.Many2one(
        'res.partner',
        string='Account',
        help='Account holder (used for enterprise subscriptions where partner_id is the employee)'
    )
    
    # Product Integration (Layer 2 - integrates with ams_products_base)
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help='Product variant that created this subscription'
    )
    
    product_template_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=True,
        help='Product template for easier filtering and reporting'
    )
    
    # Enhanced integration with ams_products_base
    product_behavior = fields.Selection(
        related='product_template_id.ams_product_behavior',
        string='Product Behavior',
        store=True,
        help='Product behavior from ams_products_base'
    )
    
    billing_period_id = fields.Many2one(
        'ams.billing.period',
        string='Billing Period',
        related='product_template_id.default_billing_period_id',
        store=True,
        help='Billing period from ams_billing_periods module'
    )
    
    # Sale Order Integration
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Source Sale Order',
        help='Sale order that created this subscription'
    )
    
    sale_order_line_id = fields.Many2one(
        'sale.order.line', 
        string='Source Sale Line',
        help='Specific sale order line that created this subscription'
    )
    
    # Invoice Integration  
    invoice_id = fields.Many2one(
        'account.move',
        string='Source Invoice',
        help='Invoice that activated this subscription'
    )
    
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Source Invoice Line',
        help='Specific invoice line that activated this subscription'
    )
    
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='Payment Status',
        store=True,
        help='Current payment status of the source invoice'
    )

    # ========================================================================
    # SUBSCRIPTION TYPE AND CONFIGURATION
    # ========================================================================
    
    subscription_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication Subscription'),
    ], string='Subscription Type',
       required=True,
       tracking=True,
       help='Type of subscription for different business logic')
    
    tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Subscription Tier',
        domain="[('subscription_type', '=', subscription_type)]",
        help='Tier defining benefits and lifecycle rules'
    )

    # ========================================================================
    # ENHANCED STATE MANAGEMENT (Layer 2)
    # ========================================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status',
       default='draft',
       required=True,
       tracking=True,
       help='Current subscription lifecycle state')
    
    # Enhanced date tracking with billing period integration
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
        help='When the subscription began'
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        tracking=True,
        help='Customer has access through this date'
    )
    
    next_billing_date = fields.Date(
        string='Next Billing Date',
        compute='_compute_next_billing_date',
        store=True,
        help='When the next invoice should be generated'
    )
    
    expiration_date = fields.Date(
        string='Expiration Date',
        compute='_compute_expiration_date',
        store=True,
        help='When subscription will expire if not renewed'
    )
    
    # Lifecycle transition dates (Layer 2 automation)
    grace_end_date = fields.Date(
        string='Grace Period Ends',
        compute='_compute_lifecycle_dates',
        store=True,
        help='When grace period ends and subscription moves to suspended'
    )
    
    suspension_end_date = fields.Date(
        string='Suspension Ends',
        compute='_compute_lifecycle_dates', 
        store=True,
        help='When suspension ends and subscription is terminated'
    )
    
    # State change tracking
    last_state_change = fields.Datetime(
        string='Last State Change',
        default=fields.Datetime.now,
        help='When the subscription state was last modified'
    )
    
    state_change_reason = fields.Text(
        string='State Change Reason',
        help='Reason for the most recent state change'
    )

    # ========================================================================
    # ENTERPRISE SEAT MANAGEMENT (Layer 2)
    # ========================================================================
    
    base_seats = fields.Integer(
        string='Base Seats',
        default=0,
        help='Number of seats included with base subscription'
    )
    
    extra_seats = fields.Integer(
        string='Additional Seats',
        default=0,
        help='Extra seats purchased beyond base allocation'
    )
    
    total_seats = fields.Integer(
        string='Total Seats',
        compute='_compute_total_seats',
        store=True,
        help='Total seats available (base + extra)'
    )
    
    seat_ids = fields.One2many(
        'ams.subscription.seat',
        'subscription_id',
        string='Seat Assignments',
        help='Individual seat assignments for enterprise subscriptions'
    )
    
    used_seats = fields.Integer(
        string='Used Seats',
        compute='_compute_seat_usage',
        store=True,
        help='Number of seats currently assigned'
    )
    
    available_seats = fields.Integer(
        string='Available Seats',
        compute='_compute_seat_usage',
        store=True,
        help='Number of unassigned seats remaining'
    )

    # ========================================================================
    # CUSTOMER PERMISSIONS AND CONTROLS (Layer 2)
    # ========================================================================
    
    auto_renew = fields.Boolean(
        string='Auto-Renew',
        default=True,
        tracking=True,
        help='Automatically generate renewal invoices before expiration'
    )
    
    allow_modifications = fields.Boolean(
        string='Allow Customer Modifications',
        default=True,
        help='Allow customer to modify subscription via portal'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Customer Pausing',
        default=True,
        help='Allow customer to pause subscription via portal'
    )
    
    # Customer service flags
    is_free = fields.Boolean(
        string='Free Subscription',
        default=False,
        help='No payment required for this subscription'
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='Changes to this subscription require staff approval'
    )

    # ========================================================================
    # PAYMENT AND BILLING TRACKING (Layer 2)
    # ========================================================================
    
    payment_issues = fields.Boolean(
        string='Has Payment Issues',
        default=False,
        tracking=True,
        help='Recent payment failures or NSF issues'
    )
    
    last_successful_payment = fields.Datetime(
        string='Last Successful Payment',
        help='Most recent successful payment date'
    )
    
    last_payment_failure = fields.Datetime(
        string='Last Payment Failure',
        help='Most recent payment failure date'
    )
    
    payment_failure_count = fields.Integer(
        string='Payment Failure Count',
        default=0,
        help='Number of consecutive payment failures'
    )
    
    # Payment history tracking
    payment_history_ids = fields.One2many(
        'ams.payment.history',
        'subscription_id',
        string='Payment History',
        help='Complete payment history for this subscription'
    )

    # ========================================================================
    # MODIFICATION AND HISTORY TRACKING (Layer 2)
    # ========================================================================
    
    modification_ids = fields.One2many(
        'ams.subscription.modification',
        'subscription_id',
        string='Modification History',
        help='History of subscription changes'
    )
    
    # Enhanced membership year computation with billing periods
    membership_year = fields.Char(
        string='Membership Year',
        compute='_compute_membership_year',
        store=True,
        help='Year this subscription covers'
    )

    # ========================================================================
    # COMPUTED FIELDS (Layer 2)
    # ========================================================================
    
    @api.depends('base_seats', 'extra_seats')
    def _compute_total_seats(self):
        """Calculate total available seats"""
        for subscription in self:
            subscription.total_seats = subscription.base_seats + subscription.extra_seats
    
    @api.depends('seat_ids.active', 'total_seats')
    def _compute_seat_usage(self):
        """Calculate seat usage statistics"""
        for subscription in self:
            active_seats = subscription.seat_ids.filtered('active')
            subscription.used_seats = len(active_seats)
            subscription.available_seats = max(0, subscription.total_seats - subscription.used_seats)
    
    @api.depends('paid_through_date', 'billing_period_id')
    def _compute_next_billing_date(self):
        """Calculate next billing date using ams_billing_periods"""
        for subscription in self:
            if subscription.paid_through_date and subscription.billing_period_id:
                try:
                    # Use billing period to calculate next billing date
                    subscription.next_billing_date = subscription.billing_period_id.calculate_next_date(
                        subscription.paid_through_date
                    )
                except AttributeError:
                    # Fallback if billing period doesn't have calculate_next_date
                    subscription.next_billing_date = subscription.paid_through_date + relativedelta(days=1)
            else:
                subscription.next_billing_date = False
    
    @api.depends('paid_through_date')
    def _compute_expiration_date(self):
        """Calculate when subscription expires"""
        for subscription in self:
            # Expiration date is the same as paid through date
            subscription.expiration_date = subscription.paid_through_date
    
    @api.depends('paid_through_date', 'product_template_id.grace_days', 'product_template_id.suspend_days')
    def _compute_lifecycle_dates(self):
        """Calculate lifecycle transition dates"""
        for subscription in self:
            if subscription.paid_through_date:
                # Grace period end
                grace_days = subscription.product_template_id.grace_days or 30
                subscription.grace_end_date = subscription.paid_through_date + timedelta(days=grace_days)
                
                # Suspension end (termination date)
                suspend_days = subscription.product_template_id.suspend_days or 60
                subscription.suspension_end_date = subscription.grace_end_date + timedelta(days=suspend_days)
            else:
                subscription.grace_end_date = False
                subscription.suspension_end_date = False
    
    @api.depends('paid_through_date', 'start_date')
    def _compute_membership_year(self):
        """Calculate membership year using billing periods"""
        for subscription in self:
            if subscription.paid_through_date:
                subscription.membership_year = str(subscription.paid_through_date.year)
            elif subscription.start_date:
                subscription.membership_year = str(subscription.start_date.year)
            else:
                subscription.membership_year = str(date.today().year)

    # ========================================================================
    # ONCHANGE METHODS (Layer 2)
    # ========================================================================
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-populate fields based on product configuration"""
        if self.product_id and self.product_id.product_tmpl_id:
            product_tmpl = self.product_id.product_tmpl_id
            
            # Set subscription type based on product behavior  
            behavior_mapping = {
                'membership': 'individual',
                'subscription': 'publication', 
                'publication': 'publication',
                'event': 'individual',
                'digital': 'individual',
                'certification': 'individual',
            }
            
            # Check for enterprise indicators
            if (getattr(product_tmpl, 'default_seat_count', 1) > 1 or
                'enterprise' in product_tmpl.name.lower()):
                self.subscription_type = 'enterprise'
                self.base_seats = getattr(product_tmpl, 'default_seat_count', 5)
            else:
                self.subscription_type = behavior_mapping.get(product_tmpl.ams_product_behavior, 'individual')
                self.base_seats = 0
            
            # Set tier if product has default tier
            if hasattr(product_tmpl, 'subscription_tier_id') and product_tmpl.subscription_tier_id:
                self.tier_id = product_tmpl.subscription_tier_id.id
            
            # Set customer permissions from product
            self.allow_modifications = getattr(product_tmpl, 'allow_mid_cycle_changes', True)
            self.allow_pausing = getattr(product_tmpl, 'allow_pausing', True)
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Set account_id for enterprise subscriptions"""
        if self.partner_id:
            if self.subscription_type == 'enterprise':
                # For enterprise, account is usually the company
                if self.partner_id.parent_id:
                    self.account_id = self.partner_id.parent_id.id
                else:
                    self.account_id = self.partner_id.id
            else:
                # For individual, account same as partner
                self.account_id = self.partner_id.id

    # ========================================================================
    # SUBSCRIPTION LIFECYCLE METHODS (Layer 2 Core Functionality)
    # ========================================================================
    
    def action_activate(self):
        """Activate subscription with enhanced date calculation"""
        for subscription in self:
            if subscription.state != 'draft':
                raise UserError(_("Only draft subscriptions can be activated"))
            
            # Set dates using billing periods if available
            if not subscription.paid_through_date:
                subscription.paid_through_date = subscription._calculate_period_end_date()
            
            subscription.write({
                'state': 'active',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription activated',
            })
            
            subscription.message_post(body=f"Subscription activated. Paid through: {subscription.paid_through_date}")
            
            # Update partner current subscription tracking
            subscription._update_partner_current_subscription()
    
    def action_pause_subscription(self):
        """Pause active subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_("Only active subscriptions can be paused"))
            
            if not subscription.allow_pausing:
                raise UserError(_("This subscription does not allow pausing"))
            
            subscription.write({
                'state': 'paused',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription paused by customer',
            })
            
            # Create modification record
            self.env['ams.subscription.modification'].create({
                'subscription_id': subscription.id,
                'modification_type': 'pause',
                'reason': 'Customer requested pause',
                'modification_date': fields.Date.today(),
                'state': 'applied',
            })
            
            subscription.message_post(body="Subscription paused by customer")
    
    def action_resume_subscription(self):
        """Resume paused subscription"""
        for subscription in self:
            if subscription.state != 'paused':
                raise UserError(_("Only paused subscriptions can be resumed"))
            
            subscription.write({
                'state': 'active',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription resumed by customer',
            })
            
            # Create modification record
            self.env['ams.subscription.modification'].create({
                'subscription_id': subscription.id,
                'modification_type': 'resume',
                'reason': 'Customer resumed subscription',
                'modification_date': fields.Date.today(),
                'state': 'applied',
            })
            
            subscription.message_post(body="Subscription resumed by customer")
    
    def action_set_grace(self):
        """Move subscription to grace period"""
        for subscription in self:
            if subscription.state not in ['active', 'paused']:
                continue
                
            subscription.write({
                'state': 'grace',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription expired - grace period started',
            })
            
            subscription.message_post(body=f"Grace period started. Ends: {subscription.grace_end_date}")
    
    def action_suspend(self):
        """Suspend subscription after grace period"""
        for subscription in self:
            if subscription.state not in ['grace', 'active']:
                continue
                
            subscription.write({
                'state': 'suspended',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Grace period expired - subscription suspended',
            })
            
            subscription.message_post(body=f"Subscription suspended. Final termination: {subscription.suspension_end_date}")
    
    def action_terminate(self):
        """Terminate subscription permanently"""
        for subscription in self:
            subscription.write({
                'state': 'terminated',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription permanently terminated',
            })
            
            # Clear partner current subscription tracking
            subscription._clear_partner_current_subscription()
            
            subscription.message_post(body="Subscription permanently terminated")
    
    def action_reactivate(self):
        """Reactivate terminated/suspended subscription"""
        for subscription in self:
            if subscription.state not in ['suspended', 'terminated', 'grace']:
                raise UserError(_("Can only reactivate suspended, terminated, or grace period subscriptions"))
            
            # Extend paid through date when reactivating
            if not subscription.paid_through_date or subscription.paid_through_date < fields.Date.today():
                subscription.paid_through_date = subscription._calculate_period_end_date()
            
            subscription.write({
                'state': 'active',
                'last_state_change': fields.Datetime.now(),
                'state_change_reason': 'Subscription reactivated',
                'payment_issues': False,
                'payment_failure_count': 0,
            })
            
            subscription._update_partner_current_subscription()
            subscription.message_post(body=f"Subscription reactivated. New expiration: {subscription.paid_through_date}")

    # ========================================================================
    # PAYMENT PROCESSING METHODS (Layer 2)
    # ========================================================================
    
    @api.model
    def create_from_invoice_payment(self, invoice_line, payment_date=None):
        """
        Enhanced subscription creation from invoice payment using Layer 2 integration.
        Uses ams_products_base and ams_billing_periods for accurate processing.
        """
        if not payment_date:
            payment_date = fields.Date.today()
        
        product_tmpl = invoice_line.product_id.product_tmpl_id
        
        # Check if this is a subscription product using ams_products_base
        if not getattr(product_tmpl, 'is_subscription_product', False):
            _logger.debug(f"Product {product_tmpl.name} is not a subscription product")
            return False
        
        # Check if subscription already exists for this invoice line
        existing_sub = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing_sub:
            existing_sub._process_payment_received(payment_date)
            return existing_sub
        
        # Use product template method for subscription creation (delegates to Layer 2)
        try:
            # Create a fake sale line for subscription creation
            fake_sale_line = self.env['sale.order.line'].new({
                'product_id': invoice_line.product_id.id,
                'product_uom_qty': invoice_line.quantity,
                'order_id': self.env['sale.order'].new({
                    'partner_id': invoice_line.move_id.partner_id.id,
                }),
            })
            
            subscription = product_tmpl.create_subscription_from_sale_order_line(fake_sale_line)
            
            if subscription:
                # Update with invoice information  
                subscription.write({
                    'invoice_id': invoice_line.move_id.id,
                    'invoice_line_id': invoice_line.id,
                    'sale_order_id': False,  # Clear fake sale order
                    'sale_order_line_id': False,
                })
                
                # Process the payment
                subscription._process_payment_received(payment_date)
                
                _logger.info(f"Created subscription {subscription.id} from invoice payment {invoice_line.move_id.name}")
                return subscription
                
        except Exception as e:
            _logger.error(f"Failed to create subscription from invoice payment: {str(e)}")
            return False
        
        return False
    
    def _process_payment_received(self, payment_date):
        """Process successful payment with enhanced Layer 2 logic"""
        self.ensure_one()
        
        # Clear payment issues
        self.write({
            'payment_issues': False,
            'payment_failure_count': 0,
            'last_successful_payment': fields.Datetime.now(),
        })
        
        # Extend subscription if needed
        if not self.paid_through_date or self.paid_through_date <= payment_date:
            new_end_date = self._calculate_period_end_date(payment_date)
            self.paid_through_date = new_end_date
        
        # Reactivate if in grace or suspended
        if self.state in ['grace', 'suspended']:
            self.action_reactivate()
        elif self.state == 'draft':
            self.action_activate()
        
        # Create payment history record
        self.env['ams.payment.history'].create({
            'subscription_id': self.id,
            'invoice_id': self.invoice_id.id,
            'invoice_line_id': self.invoice_line_id.id,
            'payment_date': fields.Datetime.now(),
            'amount': self.product_id.lst_price,
            'payment_status': 'success',
            'payment_method': 'invoice',
        })
        
        self.message_post(
            body=f"Payment received on {payment_date}. "
                 f"Subscription extended through {self.paid_through_date}"
        )
    
    def _process_payment_failure(self, failure_reason='Payment failed'):
        """Process payment failure with enhanced tracking"""
        self.ensure_one()
        
        self.write({
            'payment_issues': True,
            'payment_failure_count': self.payment_failure_count + 1,
            'last_payment_failure': fields.Datetime.now(),
        })
        
        # Auto-suspend if configured and too many failures
        if (self.product_template_id.auto_suspend_on_failure and 
            self.payment_failure_count >= (self.product_template_id.max_payment_retries or 3)):
            
            if self.state == 'active':
                self.action_set_grace()
        
        self.message_post(
            body=f"Payment failure #{self.payment_failure_count}: {failure_reason}"
        )

    # ========================================================================
    # HELPER METHODS (Layer 2)
    # ========================================================================
    
    def _calculate_period_end_date(self, start_date=None):
        """Calculate period end date using ams_billing_periods integration"""
        self.ensure_one()
        
        if not start_date:
            start_date = self.start_date or fields.Date.today()
        
        # Use billing period if available
        if self.billing_period_id:
            try:
                return self.billing_period_id.calculate_period_end(start_date)
            except AttributeError:
                _logger.warning(f"Billing period {self.billing_period_id.name} missing calculate_period_end method")
        
        # Fallback to annual
        return start_date + relativedelta(years=1) - relativedelta(days=1)
    
    def _update_partner_current_subscription(self):
        """Update partner's current subscription tracking"""
        self.ensure_one()
        
        if self.subscription_type == 'individual':
            self.partner_id.current_individual_subscription_id = self.id
        elif self.subscription_type == 'enterprise':
            # Update account holder
            account_partner = self.account_id or self.partner_id
            account_partner.current_enterprise_subscription_id = self.id
    
    def _clear_partner_current_subscription(self):
        """Clear partner's current subscription tracking"""
        self.ensure_one()
        
        if self.subscription_type == 'individual':
            if self.partner_id.current_individual_subscription_id.id == self.id:
                self.partner_id.current_individual_subscription_id = False
        elif self.subscription_type == 'enterprise':
            account_partner = self.account_id or self.partner_id
            if account_partner.current_enterprise_subscription_id.id == self.id:
                account_partner.current_enterprise_subscription_id = False

    # ========================================================================
    # CRON JOBS AND AUTOMATION (Layer 2)
    # ========================================================================
    
    @api.model
    def _cron_process_subscription_lifecycle(self):
        """Daily cron job to process subscription lifecycle transitions"""
        today = fields.Date.today()
        processed_count = 0
        
        # Move expired active subscriptions to grace
        expired_active = self.search([
            ('state', '=', 'active'),
            ('paid_through_date', '<', today),
        ])
        
        for subscription in expired_active:
            try:
                subscription.action_set_grace()
                processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to move subscription {subscription.id} to grace: {str(e)}")
        
        # Move expired grace subscriptions to suspended
        expired_grace = self.search([
            ('state', '=', 'grace'),
            ('grace_end_date', '<', today),
        ])
        
        for subscription in expired_grace:
            try:
                subscription.action_suspend()
                processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to suspend subscription {subscription.id}: {str(e)}")
        
        # Terminate expired suspended subscriptions
        expired_suspended = self.search([
            ('state', '=', 'suspended'),
            ('suspension_end_date', '<', today),
        ])
        
        for subscription in expired_suspended:
            try:
                subscription.action_terminate()
                processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to terminate subscription {subscription.id}: {str(e)}")
        
        _logger.info(f"Processed {processed_count} subscription lifecycle transitions")
        return processed_count
    
    @api.model 
    def _cron_generate_renewal_invoices(self):
        """Generate renewal invoices for auto-renewing subscriptions"""
        renewal_date = fields.Date.today() + timedelta(days=14)  # 14 days before expiration
        
        subscriptions_to_renew = self.search([
            ('state', '=', 'active'),
            ('auto_renew', '=', True),
            ('paid_through_date', '=', renewal_date),
        ])
        
        renewal_count = 0
        for subscription in subscriptions_to_renew:
            try:
                # Create renewal invoice (would integrate with sale/account modules)
                subscription.message_post(
                    body=f"Renewal invoice should be generated - expires {subscription.paid_through_date}"
                )
                renewal_count += 1
                
            except Exception as e:
                _logger.error(f"Failed to generate renewal invoice for subscription {subscription.id}: {str(e)}")
        
        _logger.info(f"Generated {renewal_count} renewal invoice notifications")
        return renewal_count

    # ========================================================================
    # PORTAL AND CUSTOMER METHODS (Layer 2)
    # ========================================================================
    
    def _compute_access_url(self):
        """Compute portal access URL"""
        super()._compute_access_url()
        for subscription in self:
            subscription.access_url = '/my/subscription/%s' % subscription.id

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None):
        """Get portal URL for customer access"""
        self.ensure_one()
        return f'/my/subscription/{self.id}'