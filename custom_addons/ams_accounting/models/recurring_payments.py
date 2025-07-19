from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class RecurringPayments(models.Model):
    """
    Main model for managing recurring payments and subscriptions
    """
    _name = 'recurring.payments'
    _description = 'Recurring Payments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_payment_date, partner_id'
    
    # ========================
    # BASIC INFORMATION
    # ========================
    
    name = fields.Char('Payment Plan Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True, tracking=True)
    
    # Payment Configuration
    amount = fields.Float('Payment Amount', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id, required=True)
    
    # Frequency Configuration
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('bimonthly', 'Bi-Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('custom', 'Custom Period')
    ], string='Payment Frequency', required=True, default='monthly', tracking=True)
    
    custom_period_days = fields.Integer('Custom Period (Days)', default=30,
        help="Number of days for custom frequency")
    
    # ========================
    # SUBSCRIPTION INTEGRATION
    # ========================
    
    # AMS Integration
    subscription_id = fields.Many2one('ams.subscription', 'Related AMS Subscription')
    subscription_type = fields.Selection(related='subscription_id.subscription_code', store=True)
    
    # Product/Service
    product_id = fields.Many2one('product.product', 'Product/Service')
    description = fields.Text('Payment Description')
    
    # Journal and Accounting
    journal_id = fields.Many2one('account.journal', 'Payment Journal', required=True,
        domain="[('type', 'in', ['cash', 'bank'])]")
    
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    
    # ========================
    # SCHEDULE MANAGEMENT
    # ========================
    
    # Dates
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True)
    end_date = fields.Date('End Date', tracking=True,
        help="Leave blank for indefinite recurring payments")
    next_payment_date = fields.Date('Next Payment Date', required=True, tracking=True)
    last_payment_date = fields.Date('Last Payment Date', readonly=True)
    
    # Payment Limits
    max_payments = fields.Integer('Maximum Payments',
        help="Maximum number of payments (0 = unlimited)")
    payments_made = fields.Integer('Payments Made', readonly=True, default=0)
    remaining_payments = fields.Integer('Remaining Payments', compute='_compute_remaining_payments')
    
    # ========================
    # PAYMENT METHOD
    # ========================
    
    # Payment Method Configuration
    payment_method = fields.Selection([
        ('manual', 'Manual Processing'),
        ('auto_bank', 'Automatic Bank Transfer'),
        ('auto_card', 'Automatic Credit Card'),
        ('auto_ach', 'Automatic ACH'),
        ('auto_paypal', 'PayPal Automatic'),
        ('auto_stripe', 'Stripe Automatic')
    ], string='Payment Method', required=True, default='manual', tracking=True)
    
    # Payment Details
    payment_token = fields.Char('Payment Token', 
        help="Secure token for automatic payments")
    card_last_four = fields.Char('Card Last 4 Digits')
    card_expiry_month = fields.Integer('Card Expiry Month')
    card_expiry_year = fields.Integer('Card Expiry Year')
    bank_account_number = fields.Char('Bank Account Number')
    
    # Payment Processor Information
    processor_name = fields.Char('Payment Processor')
    processor_customer_id = fields.Char('Processor Customer ID')
    processor_subscription_id = fields.Char('Processor Subscription ID')
    
    # ========================
    # STATUS AND CONTROL
    # ========================
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed')
    ], string='Status', default='draft', tracking=True)
    
    # Failure Handling
    consecutive_failures = fields.Integer('Consecutive Failures', default=0)
    max_failures = fields.Integer('Max Failed Attempts', default=3)
    last_failure_reason = fields.Text('Last Failure Reason')
    
    # Notifications
    notify_before_payment = fields.Boolean('Notify Before Payment', default=True)
    notification_days = fields.Integer('Notification Days', default=3,
        help="Days before payment to send notification")
    notify_on_success = fields.Boolean('Notify on Success', default=True)
    notify_on_failure = fields.Boolean('Notify on Failure', default=True)
    
    # ========================
    # TEMPLATE CONFIGURATION
    # ========================
    
    # Template Settings
    is_template = fields.Boolean('Is Template', default=False,
        help="Use this as a template for creating new recurring payments")
    template_name = fields.Char('Template Name')
    template_description = fields.Text('Template Description')
    
    # ========================
    # RELATIONSHIPS
    # ========================
    
    # Generated Records
    payment_ids = fields.One2many('account.payment', 'recurring_payment_id', 'Generated Payments')
    invoice_ids = fields.One2many('account.move', 'recurring_payment_id', 'Generated Invoices')
    
    # Statistics
    payment_count = fields.Integer('Payment Count', compute='_compute_payment_statistics')
    total_paid = fields.Float('Total Paid', compute='_compute_payment_statistics')
    success_rate = fields.Float('Success Rate %', compute='_compute_payment_statistics')
    
    @api.depends('max_payments', 'payments_made')
    def _compute_remaining_payments(self):
        for record in self:
            if record.max_payments > 0:
                record.remaining_payments = max(0, record.max_payments - record.payments_made)
            else:
                record.remaining_payments = 0  # Unlimited
    
    @api.depends('payment_ids')
    def _compute_payment_statistics(self):
        for record in self:
            payments = record.payment_ids
            record.payment_count = len(payments)
            
            successful_payments = payments.filtered(lambda p: p.state == 'posted')
            record.total_paid = sum(successful_payments.mapped('amount'))
            
            if payments:
                record.success_rate = (len(successful_payments) / len(payments)) * 100
            else:
                record.success_rate = 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate name if not provided
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                frequency = vals.get('frequency', 'monthly')
                vals['name'] = f"{partner.name} - {frequency.title()} Recurring Payment"
            
            # Set next payment date if not provided
            if not vals.get('next_payment_date') and vals.get('start_date'):
                vals['next_payment_date'] = vals['start_date']
        
        return super().create(vals_list)
    
    def action_activate(self):
        """Activate recurring payment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft recurring payments can be activated.'))
            
            # Validate configuration
            record._validate_configuration()
            
            # Set state and schedule first payment
            record.state = 'active'
            record._schedule_next_payment()
            
            record.message_post(body=_('Recurring payment activated.'))
    
    def action_pause(self):
        """Pause recurring payment"""
        for record in self:
            if record.state != 'active':
                raise UserError(_('Only active recurring payments can be paused.'))
            
            record.state = 'paused'
            record.message_post(body=_('Recurring payment paused.'))
    
    def action_resume(self):
        """Resume paused recurring payment"""
        for record in self:
            if record.state != 'paused':
                raise UserError(_('Only paused recurring payments can be resumed.'))
            
            record.state = 'active'
            record._schedule_next_payment()
            
            record.message_post(body=_('Recurring payment resumed.'))
    
    def action_cancel(self):
        """Cancel recurring payment"""
        for record in self:
            if record.state in ['cancelled', 'expired']:
                raise UserError(_('Recurring payment is already cancelled or expired.'))
            
            # Cancel processor subscription if exists
            if record.processor_subscription_id:
                record._cancel_processor_subscription()
            
            record.state = 'cancelled'
            record.message_post(body=_('Recurring payment cancelled.'))
    
    def _validate_configuration(self):
        """Validate recurring payment configuration"""
        if self.amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))
        
        if self.frequency == 'custom' and self.custom_period_days <= 0:
            raise UserError(_('Custom period must be greater than zero days.'))
        
        if self.max_payments > 0 and self.payments_made >= self.max_payments:
            raise UserError(_('Maximum number of payments already reached.'))
        
        if self.end_date and self.end_date < fields.Date.today():
            raise UserError(_('End date cannot be in the past.'))
        
        # Validate payment method configuration
        if self.payment_method.startswith('auto_') and not self.payment_token:
            raise UserError(_('Payment token is required for automatic payments.'))
    
    def _schedule_next_payment(self):
        """Calculate and set next payment date"""
        if not self.next_payment_date:
            self.next_payment_date = self.start_date or fields.Date.today()
            return
        
        current_date = self.next_payment_date
        
        if self.frequency == 'weekly':
            next_date = current_date + timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            next_date = current_date + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            next_date = current_date + relativedelta(months=1)
        elif self.frequency == 'bimonthly':
            next_date = current_date + relativedelta(months=2)
        elif self.frequency == 'quarterly':
            next_date = current_date + relativedelta(months=3)
        elif self.frequency == 'semiannual':
            next_date = current_date + relativedelta(months=6)
        elif self.frequency == 'annual':
            next_date = current_date + relativedelta(years=1)
        elif self.frequency == 'custom':
            next_date = current_date + timedelta(days=self.custom_period_days)
        else:
            next_date = current_date + relativedelta(months=1)
        
        self.next_payment_date = next_date
    
    def process_payment(self):
        """Process the recurring payment"""
        self.ensure_one()
        
        if self.state != 'active':
            return False
        
        # Check if payment should be processed
        if not self._should_process_payment():
            return False
        
        try:
            # Create payment record
            payment = self._create_payment_record()
            
            # Process payment based on method
            if self.payment_method == 'manual':
                success = self._process_manual_payment(payment)
            else:
                success = self._process_automatic_payment(payment)
            
            if success:
                self._handle_payment_success(payment)
            else:
                self._handle_payment_failure(payment)
            
            return payment
            
        except Exception as e:
            self._handle_payment_error(str(e))
            return False
    
    def _should_process_payment(self):
        """Check if payment should be processed today"""
        today = fields.Date.today()
        
        # Check if it's time for payment
        if self.next_payment_date > today:
            return False
        
        # Check if we've reached maximum payments
        if self.max_payments > 0 and self.payments_made >= self.max_payments:
            self.state = 'expired'
            return False
        
        # Check if we've reached end date
        if self.end_date and today > self.end_date:
            self.state = 'expired'
            return False
        
        # Check failure limits
        if self.consecutive_failures >= self.max_failures:
            self.state = 'failed'
            return False
        
        return True
    
    def _create_payment_record(self):
        """Create payment record for processing"""
        payment_vals = {
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'ref': f"Recurring Payment - {self.name}",
            'recurring_payment_id': self.id,
            'is_recurring_payment': True,
        }
        
        # Add payment method specific fields
        if self.payment_method.startswith('auto_'):
            payment_vals.update({
                'payment_token': self.payment_token,
                'payment_processor': self.processor_name,
            })
        
        return self.env['account.payment'].create(payment_vals)
    
    def _process_manual_payment(self, payment):
        """Process manual payment (mark as draft for manual confirmation)"""
        # Manual payments remain in draft state for manual processing
        return True
    
    def _process_automatic_payment(self, payment):
        """Process automatic payment through payment processor"""
        try:
            # This would integrate with actual payment processors
            # For now, simulate automatic processing
            
            if self.payment_method == 'auto_card':
                success = self._process_credit_card_payment(payment)
            elif self.payment_method == 'auto_bank':
                success = self._process_bank_transfer(payment)
            elif self.payment_method == 'auto_ach':
                success = self._process_ach_payment(payment)
            elif self.payment_method == 'auto_paypal':
                success = self._process_paypal_payment(payment)
            elif self.payment_method == 'auto_stripe':
                success = self._process_stripe_payment(payment)
            else:
                success = False
            
            if success:
                payment.action_post()
            
            return success
            
        except Exception as e:
            _logger.error(f"Automatic payment processing failed for {self.name}: {str(e)}")
            return False
    
    def _process_credit_card_payment(self, payment):
        """Process credit card payment"""
        # Implement credit card processing logic
        # This would integrate with payment gateways
        return True  # Simplified for demo
    
    def _process_bank_transfer(self, payment):
        """Process bank transfer payment"""
        # Implement bank transfer logic
        return True  # Simplified for demo
    
    def _process_ach_payment(self, payment):
        """Process ACH payment"""
        # Implement ACH processing logic
        return True  # Simplified for demo
    
    def _process_paypal_payment(self, payment):
        """Process PayPal payment"""
        # Implement PayPal integration
        return True  # Simplified for demo
    
    def _process_stripe_payment(self, payment):
        """Process Stripe payment"""
        # Implement Stripe integration
        return True  # Simplified for demo
    
    def _handle_payment_success(self, payment):
        """Handle successful payment processing"""
        # Update counters
        self.payments_made += 1
        self.last_payment_date = fields.Date.today()
        self.consecutive_failures = 0
        
        # Schedule next payment
        self._schedule_next_payment()
        
        # Send success notification
        if self.notify_on_success:
            self._send_success_notification(payment)
        
        # Update subscription if linked
        if self.subscription_id:
            self._update_subscription_on_success()
        
        # Log success
        self.message_post(
            body=_('Payment processed successfully: %s') % payment.name,
            subject=_('Payment Success')
        )
    
    def _handle_payment_failure(self, payment):
        """Handle failed payment processing"""
        self.consecutive_failures += 1
        self.last_failure_reason = f"Payment processing failed for {payment.name}"
        
        # Cancel payment record
        if payment.state != 'cancelled':
            payment.action_cancel()
        
        # Send failure notification
        if self.notify_on_failure:
            self._send_failure_notification(payment)
        
        # Check if we should suspend
        if self.consecutive_failures >= self.max_failures:
            self.state = 'failed'
            self.message_post(
                body=_('Recurring payment suspended due to consecutive failures.'),
                subject=_('Payment Suspended')
            )
        
        # Log failure
        self.message_post(
            body=_('Payment failed: %s') % self.last_failure_reason,
            subject=_('Payment Failed')
        )
    
    def _handle_payment_error(self, error_message):
        """Handle payment processing errors"""
        self.consecutive_failures += 1
        self.last_failure_reason = error_message
        
        _logger.error(f"Recurring payment error for {self.name}: {error_message}")
        
        self.message_post(
            body=_('Payment processing error: %s') % error_message,
            subject=_('Payment Error')
        )
    
    def _send_success_notification(self, payment):
        """Send payment success notification"""
        template = self.env.ref('ams_accounting.email_template_recurring_payment_success', False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _send_failure_notification(self, payment):
        """Send payment failure notification"""
        template = self.env.ref('ams_accounting.email_template_recurring_payment_failure', False)
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _update_subscription_on_success(self):
        """Update related subscription on successful payment"""
        if self.subscription_id and self.subscription_id.state == 'pending_renewal':
            self.subscription_id.action_confirm_renewal()
    
    def _cancel_processor_subscription(self):
        """Cancel subscription with payment processor"""
        # This would cancel the subscription with the external processor
        # Implementation depends on the specific processor
        pass
    
    def action_view_payments(self):
        """View generated payments"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generated Payments',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('recurring_payment_id', '=', self.id)],
            'context': {'default_recurring_payment_id': self.id}
        }
    
    def action_create_template(self):
        """Create template from this recurring payment"""
        template_vals = self.copy_data()[0]
        template_vals.update({
            'is_template': True,
            'template_name': f"{self.name} Template",
            'state': 'draft',
            'partner_id': False,
            'payments_made': 0,
            'consecutive_failures': 0,
        })
        
        template = self.create(template_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recurring Payment Template',
            'res_model': 'recurring.payments',
            'view_mode': 'form',
            'res_id': template.id,
        }
    
    @api.model
    def _cron_process_recurring_payments(self):
        """Cron job to process due recurring payments"""
        today = fields.Date.today()
        
        # Find payments due for processing
        due_payments = self.search([
            ('state', '=', 'active'),
            ('next_payment_date', '<=', today)
        ])
        
        processed_count = 0
        failed_count = 0
        
        for payment in due_payments:
            try:
                result = payment.process_payment()
                if result:
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                _logger.error(f"Failed to process recurring payment {payment.name}: {str(e)}")
                failed_count += 1
        
        _logger.info(f"Processed {processed_count} recurring payments, {failed_count} failed")
        return {'processed': processed_count, 'failed': failed_count}
    
    @api.model
    def _cron_send_payment_notifications(self):
        """Send notifications before upcoming payments"""
        notification_date = fields.Date.today() + timedelta(days=3)  # Default 3 days
        
        upcoming_payments = self.search([
            ('state', '=', 'active'),
            ('notify_before_payment', '=', True),
            ('next_payment_date', '=', notification_date)
        ])
        
        for payment in upcoming_payments:
            template = self.env.ref('ams_accounting.email_template_recurring_payment_reminder', False)
            if template:
                template.send_mail(payment.id, force_send=False)
        
        return len(upcoming_payments)
    
    @api.constrains('amount')
    def _check_amount(self):
        if self.amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero.'))
    
    @api.constrains('max_payments')
    def _check_max_payments(self):
        if self.max_payments < 0:
            raise ValidationError(_('Maximum payments cannot be negative.'))
    
    @api.constrains('custom_period_days')
    def _check_custom_period(self):
        if self.frequency == 'custom' and self.custom_period_days <= 0:
            raise ValidationError(_('Custom period must be greater than zero days.'))


class AccountPayment(models.Model):
    """
    Enhanced payment model with recurring payment integration
    """
    _inherit = 'account.payment'
    
    # Recurring Payment Integration
    recurring_payment_id = fields.Many2one('recurring.payments', 'Recurring Payment')
    is_recurring_payment = fields.Boolean('Is Recurring Payment', default=False)
    
    # Payment Processing
    payment_token = fields.Char('Payment Token')
    payment_processor = fields.Char('Payment Processor')
    processor_transaction_id = fields.Char('Processor Transaction ID')
    
    def action_view_recurring_payment(self):
        """View related recurring payment"""
        if self.recurring_payment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Recurring Payment',
                'res_model': 'recurring.payments',
                'view_mode': 'form',
                'res_id': self.recurring_payment_id.id,
            }


class AccountMove(models.Model):
    """
    Enhanced invoice model with recurring payment integration
    """
    _inherit = 'account.move'
    
    recurring_payment_id = fields.Many2one('recurring.payments', 'Recurring Payment')
    is_recurring_invoice = fields.Boolean('Is Recurring Invoice', default=False)