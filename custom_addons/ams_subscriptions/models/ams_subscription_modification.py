# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionModification(models.Model):
    """
    Enhanced AMS Subscription Modification Model - Layer 2 Architecture
    
    Tracks and manages subscription modifications including upgrades, downgrades,
    pauses, seat changes, and other lifecycle modifications.
    
    Layer 2 Responsibilities:
    - Modification workflow and approval management
    - Proration calculations using billing periods
    - Integration with payment processing
    - Customer portal modification requests
    - Audit trail and modification history
    - Integration with subscription lifecycle automation
    """
    _name = 'ams.subscription.modification'
    _description = 'AMS Subscription Modification - Enhanced'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'modification_date desc, create_date desc'

    # ========================================================================
    # CORE MODIFICATION FIELDS
    # ========================================================================
    
    name = fields.Char(
        string='Modification Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.subscription.modification') or 'New',
        required=True,
        tracking=True,
        help='Unique reference for this modification'
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='The subscription being modified'
    )
    
    # Related subscription fields for easier access
    subscription_name = fields.Char(
        related='subscription_id.name',
        string='Subscription Name',
        store=True,
        help='Name of the subscription being modified'
    )
    
    partner_id = fields.Many2one(
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        help='Customer who owns the subscription'
    )
    
    subscription_state = fields.Selection(
        related='subscription_id.state',
        string='Subscription Status',
        store=True,
        help='Current subscription status'
    )

    # ========================================================================
    # MODIFICATION TYPE AND DETAILS (Layer 2 - Enhanced)
    # ========================================================================
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('cancellation', 'Cancellation'),
        ('seat_change', 'Seat Change'),
        ('tier_change', 'Tier Change'),
        ('billing_change', 'Billing Period Change'),
        ('reactivation', 'Reactivation'),
        ('suspension', 'Administrative Suspension'),
        ('termination', 'Administrative Termination'),
    ], string='Modification Type', 
       required=True, 
       tracking=True,
       help='Type of modification being performed')
    
    modification_date = fields.Date(
        string='Modification Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
        help='Date when the modification was requested/initiated'
    )
    
    effective_date = fields.Date(
        string='Effective Date',
        tracking=True,
        help='Date when the modification takes effect'
    )
    
    reason = fields.Text(
        string='Reason for Modification',
        required=True,
        tracking=True,
        help='Detailed explanation of why this modification is being made'
    )

    # ========================================================================
    # TIER AND PRODUCT CHANGES (Layer 2 - Enhanced with base integration)
    # ========================================================================
    
    old_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Previous Tier',
        help='Tier before the modification'
    )
    
    new_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='New Tier',
        help='Tier after the modification'
    )
    
    # Enhanced tier comparison fields
    tier_upgrade = fields.Boolean(
        string='Is Tier Upgrade',
        compute='_compute_tier_comparison',
        store=True,
        help='Whether this is a tier upgrade'
    )
    
    tier_downgrade = fields.Boolean(
        string='Is Tier Downgrade', 
        compute='_compute_tier_comparison',
        store=True,
        help='Whether this is a tier downgrade'
    )

    # Product changes (for product behavior modifications)
    old_product_id = fields.Many2one(
        'product.product',
        string='Previous Product',
        help='Product before modification'
    )
    
    new_product_id = fields.Many2one(
        'product.product',
        string='New Product',
        help='Product after modification'
    )

    # ========================================================================
    # BILLING AND PRORATION (Layer 2 - Enhanced with billing periods)
    # ========================================================================
    
    # Enhanced billing period integration
    old_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string='Previous Billing Period',
        help='Billing period before modification'
    )
    
    new_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string='New Billing Period',
        help='Billing period after modification'
    )
    
    proration_amount = fields.Monetary(
        string='Proration Amount',
        currency_field='currency_id',
        tracking=True,
        help='Amount charged (+) or credited (-) for the modification'
    )
    
    proration_method = fields.Selection([
        ('none', 'No Proration'),
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('full_period', 'Full Period'),
    ], string='Proration Method',
       default='daily',
       help='Method used for calculating proration')
    
    proration_calculation = fields.Text(
        string='Proration Calculation Details',
        help='Detailed breakdown of how proration was calculated'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for financial amounts'
    )

    # ========================================================================
    # ENTERPRISE SEAT CHANGES (Layer 2)
    # ========================================================================
    
    old_seat_count = fields.Integer(
        string='Previous Seats',
        help='Number of seats before modification'
    )
    
    new_seat_count = fields.Integer(
        string='New Seats',
        help='Number of seats after modification'
    )
    
    seat_change_amount = fields.Integer(
        string='Seat Change',
        compute='_compute_seat_changes',
        store=True,
        help='Net change in seat count (+ added, - removed)'
    )
    
    affected_seats = fields.One2many(
        'ams.subscription.seat',
        'modification_id',
        string='Affected Seats',
        help='Seat assignments affected by this modification'
    )

    # ========================================================================
    # WORKFLOW AND APPROVAL (Layer 2 - Enhanced)
    # ========================================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ], string='Status',
       default='draft',
       required=True,
       tracking=True,
       help='Current status of the modification')
    
    approval_required = fields.Boolean(
        string='Requires Approval',
        compute='_compute_approval_required',
        store=True,
        help='Whether this modification requires staff approval'
    )
    
    approved_by_user_id = fields.Many2one(
        'res.users',
        string='Approved By',
        tracking=True,
        help='User who approved this modification'
    )
    
    approved_date = fields.Datetime(
        string='Approval Date',
        tracking=True,
        help='When the modification was approved'
    )
    
    applied_date = fields.Datetime(
        string='Applied Date',
        tracking=True,
        help='When the modification was actually applied'
    )
    
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
        help='Reason why the modification was cancelled'
    )

    # ========================================================================
    # USER AND ORIGIN TRACKING (Layer 2)
    # ========================================================================
    
    requested_by_user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True,
        help='User who initiated this modification'
    )
    
    origin = fields.Selection([
        ('manual', 'Manual (Staff)'),
        ('portal', 'Customer Portal'),
        ('api', 'API/Integration'),
        ('system', 'System/Automated'),
        ('bulk', 'Bulk Operation'),
    ], string='Origin',
       default='manual',
       tracking=True,
       help='How this modification was initiated')
    
    portal_request = fields.Boolean(
        string='Portal Request',
        default=False,
        help='Modification was requested through customer portal'
    )

    # ========================================================================
    # PAYMENT AND FINANCIAL TRACKING (Layer 2)
    # ========================================================================
    
    proration_invoice_id = fields.Many2one(
        'account.move',
        string='Proration Invoice',
        help='Invoice created for proration charges'
    )
    
    refund_invoice_id = fields.Many2one(
        'account.move',
        string='Refund Invoice',
        help='Credit note/refund invoice created for this modification'
    )
    
    payment_required = fields.Boolean(
        string='Payment Required',
        compute='_compute_payment_required',
        store=True,
        help='Whether additional payment is required'
    )
    
    payment_status = fields.Selection([
        ('not_required', 'No Payment Required'),
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ], string='Payment Status',
       compute='_compute_payment_status',
       store=True,
       help='Status of payment for this modification')

    # ========================================================================
    # COMPUTED FIELDS (Layer 2)
    # ========================================================================
    
    @api.depends('old_tier_id', 'new_tier_id')
    def _compute_tier_comparison(self):
        """Determine if modification is upgrade/downgrade"""
        for modification in self:
            if modification.old_tier_id and modification.new_tier_id:
                # Simple comparison based on sequence/id for now
                # Could be enhanced with tier value comparison
                old_seq = modification.old_tier_id.sequence or 0
                new_seq = modification.new_tier_id.sequence or 0
                
                modification.tier_upgrade = new_seq > old_seq
                modification.tier_downgrade = new_seq < old_seq
            else:
                modification.tier_upgrade = False
                modification.tier_downgrade = False
    
    @api.depends('old_seat_count', 'new_seat_count')
    def _compute_seat_changes(self):
        """Calculate net seat change"""
        for modification in self:
            if modification.old_seat_count and modification.new_seat_count:
                modification.seat_change_amount = modification.new_seat_count - modification.old_seat_count
            else:
                modification.seat_change_amount = 0
    
    @api.depends('modification_type', 'proration_amount', 'subscription_id.tier_id.requires_approval')
    def _compute_approval_required(self):
        """Determine if modification requires approval"""
        for modification in self:
            requires_approval = False
            
            # Check tier-based approval requirements
            if modification.subscription_id.tier_id.requires_approval:
                requires_approval = True
            
            # High-value modifications require approval
            if modification.proration_amount and abs(modification.proration_amount) > 500:
                requires_approval = True
            
            # Certain modification types always require approval
            if modification.modification_type in ['cancellation', 'suspension', 'termination']:
                requires_approval = True
            
            # Downgrades might require approval
            if modification.modification_type == 'downgrade' and modification.tier_downgrade:
                requires_approval = True
            
            modification.approval_required = requires_approval
    
    @api.depends('proration_amount')
    def _compute_payment_required(self):
        """Determine if additional payment is needed"""
        for modification in self:
            modification.payment_required = modification.proration_amount > 0
    
    @api.depends('proration_invoice_id.payment_state', 'payment_required')
    def _compute_payment_status(self):
        """Compute payment status based on invoice status"""
        for modification in self:
            if not modification.payment_required:
                modification.payment_status = 'not_required'
            elif modification.proration_amount < 0:
                # Credit/refund scenario
                modification.payment_status = 'refunded' if modification.refund_invoice_id else 'pending'
            elif modification.proration_invoice_id:
                # Map invoice payment states to our payment status
                invoice_state = modification.proration_invoice_id.payment_state
                state_mapping = {
                    'not_paid': 'pending',
                    'in_payment': 'pending', 
                    'paid': 'paid',
                    'partial': 'pending',
                    'reversed': 'failed',
                }
                modification.payment_status = state_mapping.get(invoice_state, 'pending')
            else:
                modification.payment_status = 'pending'

    # ========================================================================
    # ONCHANGE METHODS (Layer 2)
    # ========================================================================
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Populate fields from subscription"""
        if self.subscription_id:
            self.old_tier_id = self.subscription_id.tier_id.id
            self.old_billing_period_id = self.subscription_id.billing_period_id.id
            self.old_seat_count = self.subscription_id.total_seats
            self.old_product_id = self.subscription_id.product_id.id
    
    @api.onchange('modification_type')
    def _onchange_modification_type(self):
        """Set defaults based on modification type"""
        if self.modification_type == 'pause':
            self.reason = self.reason or 'Customer requested pause'
            self.proration_method = 'none'
        elif self.modification_type == 'resume':
            self.reason = self.reason or 'Customer requested resume'
            self.proration_method = 'none'
        elif self.modification_type == 'cancellation':
            self.reason = self.reason or 'Customer requested cancellation'
            self.effective_date = self.effective_date or fields.Date.today()
    
    @api.onchange('new_tier_id')
    def _onchange_new_tier_id(self):
        """Calculate proration when tier changes"""
        if self.subscription_id and self.new_tier_id and self.old_tier_id:
            self._calculate_proration()
    
    @api.onchange('new_seat_count')
    def _onchange_new_seat_count(self):
        """Calculate seat change proration"""
        if (self.modification_type == 'seat_change' and 
            self.subscription_id and 
            self.old_seat_count and 
            self.new_seat_count):
            self._calculate_seat_proration()

    # ========================================================================
    # PRORATION CALCULATIONS (Layer 2 - Enhanced with billing periods)
    # ========================================================================
    
    def _calculate_proration(self):
        """Calculate proration amount using ams_billing_periods integration"""
        self.ensure_one()
        
        if not (self.subscription_id and self.old_tier_id and self.new_tier_id):
            return
        
        try:
            # Get product prices (assuming tiers link to products)
            old_product = self._get_tier_product(self.old_tier_id)
            new_product = self._get_tier_product(self.new_tier_id)
            
            if not old_product or not new_product:
                self.proration_amount = 0.0
                self.proration_calculation = "Unable to determine product prices for proration"
                return
            
            # Calculate using billing period if available
            if self.subscription_id.billing_period_id:
                self.proration_amount = self._calculate_billing_period_proration(
                    old_product, new_product
                )
            else:
                # Fallback to simple calculation
                self.proration_amount = self._calculate_simple_proration(
                    old_product, new_product
                )
                
        except Exception as e:
            _logger.error(f"Error calculating proration for modification {self.id}: {str(e)}")
            self.proration_amount = 0.0
            self.proration_calculation = f"Error calculating proration: {str(e)}"
    
    def _calculate_billing_period_proration(self, old_product, new_product):
        """Enhanced proration using ams_billing_periods"""
        subscription = self.subscription_id
        billing_period = subscription.billing_period_id
        
        # Get remaining days in current period
        today = fields.Date.today()
        if subscription.paid_through_date and subscription.paid_through_date > today:
            days_remaining = (subscription.paid_through_date - today).days
        else:
            days_remaining = 0
        
        # Get total period days using billing period
        try:
            if hasattr(billing_period, 'get_period_days'):
                period_days = billing_period.get_period_days()
            else:
                # Fallback calculation
                period_days = self._estimate_period_days(billing_period)
        except AttributeError:
            period_days = 365  # Annual fallback
        
        # Calculate price difference
        price_difference = new_product.list_price - old_product.list_price
        
        # Calculate proration based on method
        if self.proration_method == 'daily':
            daily_rate = price_difference / period_days
            proration = daily_rate * days_remaining
        elif self.proration_method == 'monthly':
            monthly_rate = price_difference / (period_days / 30)
            months_remaining = days_remaining / 30
            proration = monthly_rate * months_remaining
        elif self.proration_method == 'full_period':
            proration = price_difference
        else:
            proration = 0.0
        
        # Build calculation explanation
        self.proration_calculation = self._build_proration_explanation(
            old_product, new_product, days_remaining, period_days, proration
        )
        
        return proration
    
    def _calculate_simple_proration(self, old_product, new_product):
        """Simple proration fallback"""
        price_difference = new_product.list_price - old_product.list_price
        
        # Simple daily proration assuming annual billing
        subscription = self.subscription_id
        today = fields.Date.today()
        
        if subscription.paid_through_date and subscription.paid_through_date > today:
            days_remaining = (subscription.paid_through_date - today).days
            daily_rate = price_difference / 365
            proration = daily_rate * days_remaining
        else:
            proration = price_difference
        
        self.proration_calculation = f"Simple proration: ${price_difference:.2f} price difference, prorated for remaining period"
        return proration
    
    def _calculate_seat_proration(self):
        """Calculate proration for seat changes"""
        if self.old_seat_count >= self.new_seat_count:
            # Seat reduction - credit
            seat_reduction = self.old_seat_count - self.new_seat_count
            # Get seat price from product or tier configuration
            seat_price = self._get_seat_price()
            
            # Calculate remaining period
            days_remaining = self._get_remaining_period_days()
            period_days = self._get_total_period_days()
            
            # Prorate the credit
            daily_seat_rate = seat_price / period_days
            self.proration_amount = -(daily_seat_rate * seat_reduction * days_remaining)
            
            self.proration_calculation = (
                f"Seat reduction: {seat_reduction} seats × ${seat_price:.2f} per seat "
                f"= ${seat_reduction * seat_price:.2f}, prorated for {days_remaining} remaining days "
                f"= ${abs(self.proration_amount):.2f} credit"
            )
        else:
            # Seat addition - charge
            seat_addition = self.new_seat_count - self.old_seat_count
            seat_price = self._get_seat_price()
            
            days_remaining = self._get_remaining_period_days()
            period_days = self._get_total_period_days()
            
            daily_seat_rate = seat_price / period_days
            self.proration_amount = daily_seat_rate * seat_addition * days_remaining
            
            self.proration_calculation = (
                f"Seat addition: {seat_addition} seats × ${seat_price:.2f} per seat "
                f"= ${seat_addition * seat_price:.2f}, prorated for {days_remaining} remaining days "
                f"= ${self.proration_amount:.2f} charge"
            )

    # ========================================================================
    # HELPER METHODS (Layer 2)
    # ========================================================================
    
    def _get_tier_product(self, tier):
        """Get the product associated with a tier"""
        # This would need to be implemented based on your tier/product relationship
        # For now, we'll try to find a product that references this tier
        products = self.env['product.template'].search([
            ('subscription_tier_id', '=', tier.id)
        ], limit=1)
        
        return products[0] if products else None
    
    def _get_seat_price(self):
        """Get price per seat for enterprise subscriptions"""
        # Look for seat add-on products
        seat_products = self.env['product.template'].search([
            ('is_seat_addon', '=', True)
        ], limit=1)
        
        return seat_products[0].list_price if seat_products else 25.0  # Default
    
    def _get_remaining_period_days(self):
        """Get remaining days in current billing period"""
        subscription = self.subscription_id
        today = fields.Date.today()
        
        if subscription.paid_through_date and subscription.paid_through_date > today:
            return (subscription.paid_through_date - today).days
        return 0
    
    def _get_total_period_days(self):
        """Get total days in billing period"""
        billing_period = self.subscription_id.billing_period_id
        if billing_period:
            return self._estimate_period_days(billing_period)
        return 365  # Annual fallback
    
    def _estimate_period_days(self, billing_period):
        """Estimate period days from billing period configuration"""
        if hasattr(billing_period, 'period_unit') and hasattr(billing_period, 'period_value'):
            if billing_period.period_unit == 'month':
                return billing_period.period_value * 30
            elif billing_period.period_unit == 'year':
                return billing_period.period_value * 365
        return 365  # Default to annual
    
    def _build_proration_explanation(self, old_product, new_product, days_remaining, period_days, proration):
        """Build detailed proration explanation"""
        price_diff = new_product.list_price - old_product.list_price
        
        explanation = f"""
Proration Calculation:
- Old Product: {old_product.name} (${old_product.list_price:.2f})
- New Product: {new_product.name} (${new_product.list_price:.2f})
- Price Difference: ${price_diff:.2f}
- Days Remaining: {days_remaining} of {period_days} total period days
- Proration Method: {self.proration_method}
- Final Amount: ${proration:.2f}
        """.strip()
        
        return explanation

    # ========================================================================
    # WORKFLOW METHODS (Layer 2 - Enhanced)
    # ========================================================================
    
    def action_request(self):
        """Move modification to requested state"""
        for modification in self:
            if modification.state != 'draft':
                raise UserError(_("Only draft modifications can be requested"))
            
            modification.state = 'pending_approval' if modification.approval_required else 'confirmed'
            modification.message_post(body="Modification requested")
    
    def action_approve(self):
        """Approve the modification"""
        for modification in self:
            if modification.state != 'pending_approval':
                raise UserError(_("Only pending modifications can be approved"))
            
            if not self.env.user.has_group('ams_subscriptions.group_ams_subscription_admin'):
                raise UserError(_("Only AMS Subscription Admins can approve modifications"))
            
            modification.write({
                'state': 'approved',
                'approved_by_user_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            
            modification.message_post(body=f"Modification approved by {self.env.user.name}")
            
            # Auto-confirm if no payment required
            if not modification.payment_required:
                modification.action_confirm()
    
    def action_confirm(self):
        """Confirm the modification"""
        for modification in self:
            if modification.state not in ['requested', 'approved']:
                raise UserError(_("Only requested or approved modifications can be confirmed"))
            
            modification.state = 'confirmed'
            modification.message_post(body="Modification confirmed, ready to apply")
            
            # Auto-apply if immediate effective date
            if not modification.effective_date or modification.effective_date <= fields.Date.today():
                modification.action_apply()
    
    def action_apply(self):
        """Apply the modification to the subscription"""
        for modification in self:
            if modification.state != 'confirmed':
                raise UserError(_("Only confirmed modifications can be applied"))
            
            try:
                # Apply the modification based on type
                modification._apply_modification()
                
                modification.write({
                    'state': 'applied',
                    'applied_date': fields.Datetime.now(),
                })
                
                modification.message_post(body="Modification successfully applied to subscription")
                
            except Exception as e:
                modification.write({
                    'state': 'failed',
                    'cancellation_reason': str(e),
                })
                raise UserError(f"Failed to apply modification: {str(e)}")
    
    def action_cancel(self):
        """Cancel the modification"""
        for modification in self:
            if modification.state in ['applied', 'cancelled']:
                raise UserError(_("Cannot cancel applied or already cancelled modifications"))
            
            modification.state = 'cancelled'
            modification.message_post(body=f"Modification cancelled: {modification.cancellation_reason or 'No reason provided'}")
    
    def _apply_modification(self):
        """Apply the specific modification to the subscription"""
        self.ensure_one()
        subscription = self.subscription_id
        
        if self.modification_type == 'upgrade' or self.modification_type == 'downgrade':
            subscription.tier_id = self.new_tier_id.id
            if self.new_billing_period_id:
                subscription.billing_period_id = self.new_billing_period_id.id
                
        elif self.modification_type == 'pause':
            subscription.action_pause_subscription()
            
        elif self.modification_type == 'resume':
            subscription.action_resume_subscription()
            
        elif self.modification_type == 'cancellation':
            subscription.auto_renew = False
            if self.effective_date and self.effective_date <= fields.Date.today():
                subscription.action_terminate()
                
        elif self.modification_type == 'seat_change':
            if self.new_seat_count:
                seat_diff = self.new_seat_count - subscription.total_seats
                if seat_diff > 0:
                    subscription.extra_seats += seat_diff
                elif seat_diff < 0:
                    # Handle seat reduction - might need to deactivate seats
                    self._handle_seat_reduction(abs(seat_diff))
                    
        elif self.modification_type == 'tier_change':
            subscription.tier_id = self.new_tier_id.id
            
        elif self.modification_type == 'billing_change':
            if self.new_billing_period_id:
                subscription.billing_period_id = self.new_billing_period_id.id
                
        elif self.modification_type == 'reactivation':
            subscription.action_reactivate()
            
        elif self.modification_type == 'suspension':
            subscription.action_suspend()
            
        elif self.modification_type == 'termination':
            subscription.action_terminate()
        
        # Create proration invoice if needed
        if self.proration_amount != 0:
            self._create_proration_invoice()
    
    def _handle_seat_reduction(self, reduction_count):
        """Handle reduction of enterprise seats"""
        subscription = self.subscription_id
        active_seats = subscription.seat_ids.filtered('active').sorted('assigned_date', reverse=True)
        
        seats_to_deactivate = active_seats[:reduction_count]
        for seat in seats_to_deactivate:
            seat.write({
                'active': False,
                'deactivated_date': fields.Date.today(),
                'deactivated_by_user_id': self.env.user.id,
                'deactivation_reason': 'subscription_change',
                'modification_id': self.id,
            })
        
        subscription.extra_seats = max(0, subscription.extra_seats - reduction_count)
    
    def _create_proration_invoice(self):
        """Create invoice for proration charges/credits"""
        if not self.proration_amount:
            return
            
        # This would integrate with the accounting module
        # For now, just log the need for invoice creation
        self.message_post(
            body=f"Proration invoice needed: ${self.proration_amount:.2f}\n"
                 f"Calculation: {self.proration_calculation}"
        )

    # ========================================================================
    # PORTAL AND CUSTOMER METHODS (Layer 2)
    # ========================================================================
    
    @api.model
    def create_portal_modification(self, subscription_id, modification_data):
        """Create modification from customer portal request"""
        subscription = self.env['ams.subscription'].browse(subscription_id)
        
        if not subscription.allow_modifications:
            raise UserError(_("This subscription does not allow customer modifications"))
        
        # Create modification with portal origin
        modification_vals = {
            'subscription_id': subscription_id,
            'modification_type': modification_data.get('modification_type'),
            'reason': modification_data.get('reason', 'Customer portal request'),
            'new_tier_id': modification_data.get('new_tier_id'),
            'new_seat_count': modification_data.get('new_seat_count'),
            'origin': 'portal',
            'portal_request': True,
            'requested_by_user_id': self.env.user.id,
        }
        
        modification = self.create(modification_vals)
        
        # Auto-request the modification
        modification.action_request()
        
        return modification

    # ========================================================================
    # NAME AND DISPLAY METHODS (Layer 2)
    # ========================================================================
    
    def name_get(self):
        """Enhanced name display"""
        result = []
        for modification in self:
            name = f"{modification.name} - {modification.modification_type.title()}"
            
            if modification.subscription_name:
                name = f"{name} ({modification.subscription_name})"
            
            if modification.state != 'applied':
                name = f"{name} [{modification.state.title()}]"
            
            result.append((modification.id, name))
        
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search"""
        args = args or []
        
        if name:
            domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('subscription_name', operator, name),
                ('reason', operator, name),
                ('modification_type', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


# ========================================================================
# RELATED MODEL ENHANCEMENTS
# ========================================================================

class AMSSubscriptionSeat(models.Model):
    """Add modification tracking to seats"""
    _inherit = 'ams.subscription.seat'
    
    modification_id = fields.Many2one(
        'ams.subscription.modification',
        string='Related Modification',
        help='Modification that affected this seat'
    )


class AMSSubscription(models.Model):
    """Add modification convenience method to subscription"""
    _inherit = 'ams.subscription'
    
    def action_modify_subscription(self, new_tier_id, modification_type='upgrade'):
        """Convenience method to create and process modification"""
        modification_vals = {
            'subscription_id': self.id,
            'modification_type': modification_type,
            'old_tier_id': self.tier_id.id,
            'new_tier_id': new_tier_id,
            'reason': f'Subscription {modification_type} via action method',
        }
        
        modification = self.env['ams.subscription.modification'].create(modification_vals)
        modification.action_request()
        
        return modification