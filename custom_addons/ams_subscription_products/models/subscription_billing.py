# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionBilling(models.Model):
    """
    AMS Subscription Billing management for professional associations.
    Handles billing cycles, prorated billing, and revenue recognition.
    """
    _name = 'ams.subscription.billing'
    _description = 'AMS Subscription Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'billing_date desc, id desc'

    # ========================================================================
    # CORE BILLING FIELDS
    # ========================================================================

    name = fields.Char(
        string="Billing Reference",
        required=True,
        copy=False,
        default=lambda self: _('New Billing'),
        help="Unique reference for this billing cycle"
    )

    subscription_id = fields.Many2one(
        'sale.subscription',
        string="Subscription",
        required=True,
        ondelete='cascade',
        help="Related subscription for this billing"
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
        help="Subscription product being billed"
    )

    billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Billing Period",
        required=True,
        help="Billing period configuration for this subscription"
    )

    # ========================================================================
    # BILLING DATE MANAGEMENT
    # ========================================================================

    billing_date = fields.Date(
        string="Billing Date",
        required=True,
        default=fields.Date.today,
        help="Date when billing is processed"
    )

    period_start_date = fields.Date(
        string="Period Start Date",
        required=True,
        help="Start date of the billing period"
    )

    period_end_date = fields.Date(
        string="Period End Date",
        required=True,
        help="End date of the billing period"
    )

    next_billing_date = fields.Date(
        string="Next Billing Date",
        compute='_compute_next_billing_date',
        store=True,
        help="Calculated next billing date"
    )

    days_in_period = fields.Integer(
        string="Days in Period",
        compute='_compute_period_details',
        store=True,
        help="Total days in this billing period"
    )

    # ========================================================================
    # BILLING AMOUNT CALCULATIONS
    # ========================================================================

    base_amount = fields.Monetary(
        string="Base Amount",
        required=True,
        help="Base subscription amount before adjustments"
    )

    member_discount_amount = fields.Monetary(
        string="Member Discount",
        default=0.0,
        help="Discount applied for member pricing"
    )

    additional_discount_amount = fields.Monetary(
        string="Additional Discount",
        default=0.0,
        help="Additional subscription-specific discount"
    )

    setup_fee_amount = fields.Monetary(
        string="Setup Fee",
        default=0.0,
        help="One-time setup fee (first billing only)"
    )

    proration_adjustment = fields.Monetary(
        string="Proration Adjustment",
        default=0.0,
        help="Adjustment for partial period billing"
    )

    tax_amount = fields.Monetary(
        string="Tax Amount",
        default=0.0,
        help="Calculated tax amount"
    )

    total_amount = fields.Monetary(
        string="Total Amount",
        compute='_compute_total_amount',
        store=True,
        help="Final billing amount"
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        string="Currency",
        store=True,
        readonly=True
    )

    # ========================================================================
    # BILLING STATUS AND PROCESSING
    # ========================================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('billed', 'Billed'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string="Status", 
       default='draft',
       tracking=True,
       help="Current billing status")

    billing_type = fields.Selection([
        ('initial', 'Initial Billing'),
        ('recurring', 'Recurring Billing'),
        ('prorated', 'Prorated Billing'),
        ('adjustment', 'Billing Adjustment'),
        ('cancellation', 'Cancellation Billing'),
    ], string="Billing Type",
       required=True,
       help="Type of billing being processed")

    is_prorated = fields.Boolean(
        string="Is Prorated",
        default=False,
        help="Whether this billing includes proration"
    )

    proration_factor = fields.Float(
        string="Proration Factor",
        default=1.0,
        help="Factor used for proration calculation (1.0 = full period)"
    )

    # ========================================================================
    # ACCOUNTING AND REVENUE RECOGNITION
    # ========================================================================

    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        copy=False,
        help="Generated invoice for this billing"
    )

    payment_id = fields.Many2one(
        'account.payment',
        string="Payment",
        copy=False,
        help="Payment received for this billing"
    )

    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('monthly', 'Monthly Recognition'),
        ('service_delivery', 'Service Delivery Based'),
    ], string="Revenue Recognition Method",
       default='monthly',
       help="Method for recognizing revenue")

    deferred_revenue_amount = fields.Monetary(
        string="Deferred Revenue",
        default=0.0,
        help="Amount to be recognized as deferred revenue"
    )

    recognized_revenue_amount = fields.Monetary(
        string="Recognized Revenue",
        default=0.0,
        help="Amount of revenue already recognized"
    )

    # ========================================================================
    # MEMBER AND CUSTOMER INFORMATION
    # ========================================================================

    is_member_billing = fields.Boolean(
        string="Member Billing",
        compute='_compute_member_status',
        store=True,
        help="Whether this billing is for a member"
    )

    member_status = fields.Selection(
        related='partner_id.membership_status',
        string="Member Status",
        store=True,
        readonly=True
    )

    billing_address_id = fields.Many2one(
        'res.partner',
        string="Billing Address",
        help="Specific billing address for this subscription"
    )

    # ========================================================================
    # AUTOMATION AND NOTIFICATIONS
    # ========================================================================

    auto_billing_enabled = fields.Boolean(
        string="Auto Billing Enabled",
        default=True,
        help="Whether automatic billing is enabled"
    )

    billing_reminder_sent = fields.Boolean(
        string="Billing Reminder Sent",
        default=False,
        help="Whether billing reminder has been sent"
    )

    billing_notification_date = fields.Date(
        string="Notification Date",
        help="Date when billing notification was sent"
    )

    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
        help="Number of billing retry attempts"
    )

    last_retry_date = fields.Date(
        string="Last Retry Date",
        help="Date of last billing retry attempt"
    )

    # ========================================================================
    # NOTES AND TRACKING
    # ========================================================================

    notes = fields.Text(
        string="Billing Notes",
        help="Additional notes about this billing cycle"
    )

    billing_error_message = fields.Text(
        string="Error Message",
        help="Error message if billing failed"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('period_start_date', 'period_end_date')
    def _compute_period_details(self):
        """Calculate period-related details."""
        for billing in self:
            if billing.period_start_date and billing.period_end_date:
                billing.days_in_period = (billing.period_end_date - billing.period_start_date).days + 1
            else:
                billing.days_in_period = 0

    @api.depends('billing_date', 'billing_period_id')
    def _compute_next_billing_date(self):
        """Calculate next billing date."""
        for billing in self:
            if billing.billing_date and billing.billing_period_id:
                billing.next_billing_date = billing.billing_period_id.calculate_next_date(billing.billing_date)
            else:
                billing.next_billing_date = False

    @api.depends('base_amount', 'member_discount_amount', 'additional_discount_amount', 
                 'setup_fee_amount', 'proration_adjustment', 'tax_amount')
    def _compute_total_amount(self):
        """Calculate total billing amount."""
        for billing in self:
            subtotal = (billing.base_amount - 
                       billing.member_discount_amount - 
                       billing.additional_discount_amount +
                       billing.setup_fee_amount +
                       billing.proration_adjustment)
            billing.total_amount = subtotal + billing.tax_amount

    @api.depends('partner_id.is_member', 'partner_id.membership_status')
    def _compute_member_status(self):
        """Determine if this is member billing."""
        for billing in self:
            billing.is_member_billing = (
                billing.partner_id.is_member and 
                billing.partner_id.membership_status == 'active'
            )

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Update fields when subscription changes."""
        if self.subscription_id:
            # Get subscription product
            if self.subscription_id.template_id and self.subscription_id.template_id.product_id:
                self.product_id = self.subscription_id.template_id.product_id.product_tmpl_id
            
            # Set billing period from product
            if self.product_id and self.product_id.subscription_billing_period_id:
                self.billing_period_id = self.product_id.subscription_billing_period_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update billing configuration when product changes."""
        if self.product_id:
            # Set billing period
            if self.product_id.subscription_billing_period_id:
                self.billing_period_id = self.product_id.subscription_billing_period_id
            
            # Set revenue recognition method
            self.revenue_recognition_method = self.product_id.subscription_revenue_recognition_method

    @api.onchange('billing_period_id', 'period_start_date')
    def _onchange_billing_period(self):
        """Update period dates when billing period changes."""
        if self.billing_period_id and self.period_start_date:
            self.period_end_date = self.billing_period_id.calculate_period_end(self.period_start_date)

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create with billing reference generation."""
        for vals in vals_list:
            if vals.get('name', _('New Billing')) == _('New Billing'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.subscription.billing') or _('New Billing')
        
        billings = super().create(vals_list)
        
        # Log billing creation
        for billing in billings:
            _logger.info(
                f"Created subscription billing: {billing.name} for "
                f"subscription {billing.subscription_id.name} "
                f"(Amount: {billing.total_amount})"
            )
        
        return billings

    def write(self, vals):
        """Enhanced write with state change tracking."""
        # Track state changes
        if 'state' in vals:
            for billing in self:
                if billing.state != vals['state']:
                    billing.message_post(
                        body=_("Billing status changed from %s to %s") % (
                            dict(self._fields['state'].selection)[billing.state],
                            dict(self._fields['state'].selection)[vals['state']]
                        )
                    )
        
        return super().write(vals)

    # ========================================================================
    # BUSINESS METHODS - BILLING PROCESSING
    # ========================================================================

    def calculate_billing_amounts(self, force_recalculate=False):
        """
        Calculate all billing amounts including discounts and proration.
        
        Args:
            force_recalculate (bool): Force recalculation even if amounts exist
        """
        for billing in self:
            if billing.state == 'billed' and not force_recalculate:
                continue  # Don't recalculate completed billing
            
            # Get base product pricing
            if billing.product_id and billing.partner_id:
                pricing = billing.product_id.calculate_subscription_pricing_for_partner(
                    billing.partner_id, 
                    billing.period_start_date
                )
                
                billing.base_amount = pricing.get('base_price', 0.0)
                billing.member_discount_amount = pricing.get('member_savings', 0.0)
                billing.setup_fee_amount = pricing.get('setup_fee', 0.0) if billing.billing_type == 'initial' else 0.0
                billing.is_prorated = pricing.get('is_prorated', False)
                billing.proration_factor = pricing.get('proration_factor', 1.0)
                
                # Calculate proration adjustment
                if billing.is_prorated:
                    full_amount = billing.base_amount - billing.member_discount_amount
                    prorated_amount = full_amount * billing.proration_factor
                    billing.proration_adjustment = prorated_amount - full_amount
                
                # Calculate additional subscription discount
                if billing.product_id.subscription_member_discount_additional > 0 and billing.is_member_billing:
                    discount_rate = billing.product_id.subscription_member_discount_additional / 100
                    billing.additional_discount_amount = billing.base_amount * discount_rate
                
                # Calculate tax (basic implementation - extend as needed)
                taxable_amount = (billing.base_amount - 
                                billing.member_discount_amount - 
                                billing.additional_discount_amount +
                                billing.setup_fee_amount +
                                billing.proration_adjustment)
                
                # Apply basic tax calculation (this would integrate with Odoo tax system)
                billing.tax_amount = 0.0  # Placeholder - implement tax calculation
            
            _logger.info(f"Calculated billing amounts for {billing.name}: Total {billing.total_amount}")

    def process_billing(self):
        """
        Process the billing and create invoice.
        
        Returns:
            bool: Success status
        """
        self.ensure_one()
        
        if self.state != 'scheduled':
            raise UserError(_("Only scheduled billings can be processed"))
        
        try:
            self.write({'state': 'processing'})
            
            # Recalculate amounts
            self.calculate_billing_amounts()
            
            # Create invoice
            invoice = self._create_billing_invoice()
            
            if invoice:
                self.write({
                    'invoice_id': invoice.id,
                    'state': 'billed',
                    'billing_notification_date': fields.Date.today(),
                })
                
                # Process revenue recognition
                self._process_revenue_recognition()
                
                # Send billing notification
                self._send_billing_notification()
                
                _logger.info(f"Successfully processed billing {self.name}")
                return True
            
        except Exception as e:
            self.write({
                'state': 'failed',
                'billing_error_message': str(e),
                'last_retry_date': fields.Date.today(),
                'retry_count': self.retry_count + 1,
            })
            _logger.error(f"Failed to process billing {self.name}: {e}")
            return False
        
        return False

    def _create_billing_invoice(self):
        """
        Create invoice for this billing.
        
        Returns:
            account.move: Created invoice
        """
        self.ensure_one()
        
        if self.invoice_id:
            return self.invoice_id  # Invoice already exists
        
        # Prepare invoice values
        invoice_vals = {
            'partner_id': self.billing_address_id.id if self.billing_address_id else self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.billing_date,
            'currency_id': self.currency_id.id,
            'ref': self.name,
            'invoice_origin': self.subscription_id.name,
            'invoice_line_ids': [],
        }
        
        # Create invoice lines
        invoice_lines = []
        
        # Main subscription line
        main_line_vals = {
            'product_id': self.product_id.product_variant_id.id,
            'name': self._get_billing_description(),
            'quantity': 1.0,
            'price_unit': self.base_amount - self.member_discount_amount - self.additional_discount_amount + self.proration_adjustment,
            'account_id': self._get_revenue_account_id(),
        }
        invoice_lines.append((0, 0, main_line_vals))
        
        # Setup fee line (if applicable)
        if self.setup_fee_amount > 0:
            setup_line_vals = {
                'name': _('Setup Fee - %s') % self.product_id.name,
                'quantity': 1.0,
                'price_unit': self.setup_fee_amount,
                'account_id': self._get_revenue_account_id(),
            }
            invoice_lines.append((0, 0, setup_line_vals))
        
        invoice_vals['invoice_line_ids'] = invoice_lines
        
        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)
        
        return invoice

    def _get_billing_description(self):
        """Generate billing description for invoice."""
        self.ensure_one()
        
        description = self.product_id.name
        
        if self.period_start_date and self.period_end_date:
            description += _(' - Period: %s to %s') % (
                self.period_start_date.strftime('%m/%d/%Y'),
                self.period_end_date.strftime('%m/%d/%Y')
            )
        
        if self.is_prorated:
            description += _(' (Prorated: %.1f%%)') % (self.proration_factor * 100)
        
        return description

    def _get_revenue_account_id(self):
        """Get appropriate revenue account for billing."""
        self.ensure_one()
        
        # Use subscription-specific deferred revenue account if available
        if (self.product_id.subscription_deferred_revenue_account_id and 
            self.revenue_recognition_method != 'immediate'):
            return self.product_id.subscription_deferred_revenue_account_id.id
        
        # Use membership revenue account for membership products
        if (self.product_id.membership_revenue_account_id and 
            self.product_id.ams_product_behavior == 'membership'):
            return self.product_id.membership_revenue_account_id.id
        
        # Default to product income account
        return self.product_id.property_account_income_id.id

    def _process_revenue_recognition(self):
        """Process revenue recognition based on method."""
        self.ensure_one()
        
        if self.revenue_recognition_method == 'immediate':
            self.recognized_revenue_amount = self.total_amount - self.tax_amount
            self.deferred_revenue_amount = 0.0
        else:
            # For deferred recognition, mark full amount as deferred
            self.deferred_revenue_amount = self.total_amount - self.tax_amount
            self.recognized_revenue_amount = 0.0
            
            # Schedule recognition entries (this would trigger scheduled actions)
            self._schedule_revenue_recognition()

    def _schedule_revenue_recognition(self):
        """Schedule revenue recognition entries for deferred revenue."""
        self.ensure_one()
        
        if self.revenue_recognition_method == 'monthly' and self.days_in_period > 0:
            # Create monthly recognition schedule
            monthly_amount = self.deferred_revenue_amount / (self.days_in_period / 30.44)  # Average days per month
            
            current_date = self.period_start_date
            while current_date <= self.period_end_date:
                # This would create scheduled revenue recognition entries
                # Implementation depends on accounting module integration
                current_date += relativedelta(months=1)

    def _send_billing_notification(self):
        """Send billing notification to customer."""
        self.ensure_one()
        
        if not self.partner_id.email:
            return False
        
        # Find appropriate email template
        template = None
        if self.billing_type == 'initial':
            template = self.env.ref('ams_subscriptions_products.subscription_billing_welcome_template', False)
        else:
            template = self.env.ref('ams_subscriptions_products.subscription_billing_invoice_template', False)
        
        if template and self.invoice_id:
            template.send_mail(self.invoice_id.id, force_send=True)
            return True
        
        return False

    # ========================================================================
    # BILLING RETRY AND ERROR HANDLING
    # ========================================================================

    def retry_billing(self):
        """Retry failed billing."""
        self.ensure_one()
        
        if self.state != 'failed':
            raise UserError(_("Only failed billings can be retried"))
        
        if self.retry_count >= 3:
            raise UserError(_("Maximum retry attempts exceeded"))
        
        # Clear error message and reset to scheduled
        self.write({
            'state': 'scheduled',
            'billing_error_message': False,
        })
        
        # Process billing
        return self.process_billing()

    def cancel_billing(self):
        """Cancel billing."""
        for billing in self:
            if billing.state in ['billed', 'paid']:
                raise UserError(_("Cannot cancel completed billings"))
            
            billing.write({
                'state': 'cancelled',
                'billing_notification_date': fields.Date.today(),
            })

    # ========================================================================
    # QUERY AND UTILITY METHODS
    # ========================================================================

    @api.model
    def get_scheduled_billings(self, billing_date=None):
        """Get billings scheduled for processing."""
        if not billing_date:
            billing_date = fields.Date.today()
        
        return self.search([
            ('state', '=', 'scheduled'),
            ('billing_date', '<=', billing_date),
            ('auto_billing_enabled', '=', True),
        ])

    @api.model
    def get_failed_billings(self):
        """Get failed billings that can be retried."""
        return self.search([
            ('state', '=', 'failed'),
            ('retry_count', '<', 3),
        ])

    @api.model
    def process_scheduled_billings(self):
        """Process all scheduled billings for today."""
        scheduled_billings = self.get_scheduled_billings()
        
        success_count = 0
        error_count = 0
        
        for billing in scheduled_billings:
            if billing.process_billing():
                success_count += 1
            else:
                error_count += 1
        
        _logger.info(
            f"Processed scheduled billings: {success_count} successful, {error_count} failed"
        )
        
        return {
            'success_count': success_count,
            'error_count': error_count,
        }

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('period_start_date', 'period_end_date')
    def _check_period_dates(self):
        """Validate period dates."""
        for billing in self:
            if billing.period_start_date and billing.period_end_date:
                if billing.period_start_date > billing.period_end_date:
                    raise ValidationError(_("Period start date must be before end date"))

    @api.constrains('billing_date', 'period_start_date')
    def _check_billing_date(self):
        """Validate billing date."""
        for billing in self:
            if billing.billing_date and billing.period_start_date:
                if billing.billing_date > billing.period_start_date + timedelta(days=30):
                    # Allow some flexibility but warn about unusual billing dates
                    _logger.warning(
                        f"Billing date {billing.billing_date} is significantly after "
                        f"period start {billing.period_start_date} for {billing.name}"
                    )

    @api.constrains('proration_factor')
    def _check_proration_factor(self):
        """Validate proration factor."""
        for billing in self:
            if billing.proration_factor < 0 or billing.proration_factor > 1:
                raise ValidationError(_("Proration factor must be between 0 and 1"))

    # ========================================================================
    # REPORTING AND ANALYTICS
    # ========================================================================

    def get_billing_summary(self):
        """Get summary of billing details."""
        self.ensure_one()
        
        return {
            'billing_reference': self.name,
            'subscription': self.subscription_id.name,
            'customer': self.partner_id.name,
            'product': self.product_id.name,
            'billing_period': f"{self.period_start_date} to {self.period_end_date}",
            'billing_type': dict(self._fields['billing_type'].selection)[self.billing_type],
            'base_amount': self.base_amount,
            'discounts': self.member_discount_amount + self.additional_discount_amount,
            'setup_fee': self.setup_fee_amount,
            'proration': self.proration_adjustment,
            'tax': self.tax_amount,
            'total_amount': self.total_amount,
            'state': dict(self._fields['state'].selection)[self.state],
            'is_member': self.is_member_billing,
            'is_prorated': self.is_prorated,
        }

    @api.model
    def get_billing_analytics(self, date_from=None, date_to=None):
        """Get billing analytics for reporting."""
        domain = []
        
        if date_from:
            domain.append(('billing_date', '>=', date_from))
        if date_to:
            domain.append(('billing_date', '<=', date_to))
        
        billings = self.search(domain)
        
        return {
            'total_billings': len(billings),
            'total_amount': sum(billings.mapped('total_amount')),
            'member_billings': len(billings.filtered('is_member_billing')),
            'prorated_billings': len(billings.filtered('is_prorated')),
            'by_state': {
                state: len(billings.filtered(lambda b: b.state == state))
                for state in dict(self._fields['state'].selection).keys()
            },
            'by_type': {
                billing_type: len(billings.filtered(lambda b: b.billing_type == billing_type))
                for billing_type in dict(self._fields['billing_type'].selection).keys()
            },
            'average_amount': sum(billings.mapped('total_amount')) / len(billings) if billings else 0,
            'deferred_revenue': sum(billings.mapped('deferred_revenue_amount')),
            'recognized_revenue': sum(billings.mapped('recognized_revenue_amount')),
        }