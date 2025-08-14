# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging
import math

_logger = logging.getLogger(__name__)

class AMSPaymentRetry(models.Model):
    """Payment Retry Management with Exponential Backoff"""
    _name = 'ams.payment.retry'
    _description = 'AMS Payment Retry'
    _order = 'next_retry_date asc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Retry Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.payment.retry') or 'New'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Related Records
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Failed Invoice',
        required=True,
        ondelete='cascade',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    billing_event_id = fields.Many2one(
        'ams.billing.event',
        string='Billing Event',
        ondelete='cascade',
        help='Original billing event that failed'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Payment Method',
        help='Payment method to retry with'
    )
    
    # Failure Information
    original_failure_date = fields.Datetime(
        string='Original Failure Date',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    failure_reason = fields.Selection([
        ('insufficient_funds', 'Insufficient Funds'),
        ('card_declined', 'Card Declined'),
        ('card_expired', 'Card Expired'),
        ('invalid_card', 'Invalid Card'),
        ('gateway_error', 'Gateway Error'),
        ('network_error', 'Network Error'),
        ('timeout', 'Timeout'),
        ('authentication_failed', 'Authentication Failed'),
        ('card_blocked', 'Card Blocked'),
        ('limit_exceeded', 'Limit Exceeded'),
        ('other', 'Other'),
    ], string='Failure Reason', required=True, tracking=True)
    
    failure_message = fields.Text(
        string='Failure Message',
        help='Detailed failure message from payment gateway'
    )
    
    gateway_error_code = fields.Char(
        string='Gateway Error Code',
        help='Error code from payment gateway'
    )
    
    # Retry Configuration
    max_retry_attempts = fields.Integer(
        string='Max Retry Attempts',
        default=3,
        help='Maximum number of retry attempts'
    )
    
    current_attempt = fields.Integer(
        string='Current Attempt',
        default=0,
        readonly=True
    )
    
    initial_delay_hours = fields.Integer(
        string='Initial Delay (Hours)',
        default=24,
        help='Initial delay before first retry in hours'
    )
    
    backoff_multiplier = fields.Float(
        string='Backoff Multiplier',
        default=2.0,
        help='Multiplier for exponential backoff'
    )
    
    max_delay_hours = fields.Integer(
        string='Max Delay (Hours)',
        default=168,  # 7 days
        help='Maximum delay between retries in hours'
    )
    
    # Retry Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('retrying', 'Retrying'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    next_retry_date = fields.Datetime(
        string='Next Retry Date',
        index=True,
        tracking=True
    )
    
    last_retry_date = fields.Datetime(
        string='Last Retry Date',
        readonly=True
    )
    
    # Success Information
    success_date = fields.Datetime(
        string='Success Date',
        readonly=True
    )
    
    successful_payment_id = fields.Many2one(
        'account.payment',
        string='Successful Payment',
        readonly=True
    )
    
    # Amount Information
    retry_amount = fields.Monetary(
        string='Retry Amount',
        currency_field='currency_id',
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Configuration Options
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help='Send notification to customer about retry attempts'
    )
    
    notify_admin = fields.Boolean(
        string='Notify Admin',
        default=True,
        help='Send notification to admin about retry status'
    )
    
    auto_retry_enabled = fields.Boolean(
        string='Auto Retry Enabled',
        default=True,
        help='Enable automatic retry processing'
    )
    
    # Retry History
    retry_history_ids = fields.One2many(
        'ams.payment.retry.history',
        'payment_retry_id',
        string='Retry History'
    )
    
    # Smart Retry Features
    use_smart_retry = fields.Boolean(
        string='Use Smart Retry',
        default=True,
        help='Use intelligent retry logic based on failure reason'
    )
    
    avoid_weekends = fields.Boolean(
        string='Avoid Weekends',
        default=True,
        help='Skip retries on weekends'
    )
    
    preferred_retry_time = fields.Selection([
        ('morning', 'Morning (8-12)'),
        ('afternoon', 'Afternoon (12-17)'),
        ('evening', 'Evening (17-20)'),
        ('any', 'Any Time'),
    ], string='Preferred Retry Time', default='morning')
    
    # Computed Fields
    @api.depends('subscription_id', 'invoice_id', 'failure_reason')
    def _compute_display_name(self):
        """Compute display name for the payment retry"""
        for retry in self:
            if retry.subscription_id and retry.invoice_id:
                retry.display_name = f"{retry.subscription_id.name} - {retry.invoice_id.name} ({retry.failure_reason})"
            else:
                retry.display_name = retry.name or 'New Payment Retry'
    
    # Validation
    @api.constrains('max_retry_attempts')
    def _check_max_retry_attempts(self):
        """Validate max retry attempts"""
        for retry in self:
            if retry.max_retry_attempts < 1 or retry.max_retry_attempts > 10:
                raise ValidationError(_('Max retry attempts must be between 1 and 10'))
    
    @api.constrains('backoff_multiplier')
    def _check_backoff_multiplier(self):
        """Validate backoff multiplier"""
        for retry in self:
            if retry.backoff_multiplier < 1.0 or retry.backoff_multiplier > 5.0:
                raise ValidationError(_('Backoff multiplier must be between 1.0 and 5.0'))
    
    @api.constrains('initial_delay_hours', 'max_delay_hours')
    def _check_delay_hours(self):
        """Validate delay hours"""
        for retry in self:
            if retry.initial_delay_hours < 1:
                raise ValidationError(_('Initial delay must be at least 1 hour'))
            if retry.max_delay_hours < retry.initial_delay_hours:
                raise ValidationError(_('Max delay must be greater than initial delay'))
    
    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to set up payment retry"""
        for vals in vals_list:
            # Set retry amount from invoice if not provided
            if 'retry_amount' not in vals and 'invoice_id' in vals:
                invoice = self.env['account.move'].browse(vals['invoice_id'])
                vals['retry_amount'] = invoice.amount_residual or invoice.amount_total
            
            # Set next retry date if not provided
            if 'next_retry_date' not in vals:
                vals['next_retry_date'] = self._calculate_next_retry_date(
                    vals.get('original_failure_date', fields.Datetime.now()),
                    0,  # First attempt
                    vals.get('initial_delay_hours', 24),
                    vals.get('backoff_multiplier', 2.0),
                    vals.get('max_delay_hours', 168)
                )
        
        retries = super().create(vals_list)
        
        # Apply smart retry configuration
        for retry in retries:
            if retry.use_smart_retry:
                retry._apply_smart_retry_logic()
        
        return retries
    
    def write(self, vals):
        """Enhanced write to handle state changes"""
        # Track state changes
        if 'state' in vals:
            for retry in self:
                if retry.state != vals['state']:
                    retry.message_post(
                        body=_('Payment retry state changed from %s to %s') % (
                            retry.state, vals['state']
                        )
                    )
        
        return super().write(vals)
    
    # Actions
    def action_retry_now(self):
        """Manually trigger retry now"""
        for retry in self:
            if retry.state not in ['pending', 'failed']:
                raise UserError(_('Only pending or failed retries can be manually triggered'))
            
            if retry.current_attempt >= retry.max_retry_attempts:
                raise UserError(_('Maximum retry attempts reached'))
            
            retry._execute_retry()
    
    def action_cancel(self):
        """Cancel the payment retry"""
        for retry in self:
            if retry.state in ['success', 'cancelled']:
                raise UserError(_('Cannot cancel completed or already cancelled retry'))
            
            retry.state = 'cancelled'
            retry.message_post(body=_('Payment retry cancelled'))
    
    def action_reset(self):
        """Reset retry for a fresh start"""
        for retry in self:
            if retry.state == 'success':
                raise UserError(_('Cannot reset successful retry'))
            
            retry.write({
                'state': 'pending',
                'current_attempt': 0,
                'next_retry_date': retry._calculate_next_retry_date(
                    fields.Datetime.now(), 0
                ),
                'last_retry_date': False,
                'success_date': False,
                'successful_payment_id': False,
            })
            
            retry.message_post(body=_('Payment retry reset'))
    
    def action_mark_success(self):
        """Manually mark retry as successful"""
        for retry in self:
            if retry.state == 'success':
                raise UserError(_('Retry is already successful'))
            
            retry.state = 'success'
            retry.success_date = fields.Datetime.now()
            retry.message_post(body=_('Payment retry manually marked as successful'))
    
    # Core Retry Logic
    def _execute_retry(self):
        """Execute the payment retry"""
        self.ensure_one()
        
        if self.current_attempt >= self.max_retry_attempts:
            self.state = 'failed'
            self.message_post(body=_('Maximum retry attempts reached'))
            return False
        
        self.state = 'retrying'
        self.current_attempt += 1
        self.last_retry_date = fields.Datetime.now()
        
        _logger.info(f'Executing payment retry {self.name}, attempt {self.current_attempt}')
        
        try:
            # Create retry history record
            history = self._create_retry_history()
            
            # Attempt payment processing
            result = self._attempt_payment()
            
            # Update history with result
            history.write({
                'success': result.get('success', False),
                'error_message': result.get('error'),
                'gateway_response': result.get('gateway_response'),
                'transaction_id': result.get('transaction_id'),
            })
            
            if result.get('success'):
                self._handle_success(result)
            else:
                self._handle_failure(result)
            
        except Exception as e:
            self._handle_exception(str(e))
            _logger.error(f'Exception during payment retry {self.name}: {str(e)}')
    
    def _attempt_payment(self):
        """Attempt to process the payment"""
        # This is a placeholder for actual payment processing
        # In a real implementation, this would:
        # 1. Use the stored payment method
        # 2. Create a payment transaction
        # 3. Call the payment gateway API
        # 4. Handle the response
        
        _logger.info(f'Attempting payment for retry {self.name}')
        
        # Simulate payment processing
        # In real implementation, replace with actual gateway calls
        import random
        success_rate = self._calculate_success_probability()
        
        if random.random() < success_rate:
            return {
                'success': True,
                'transaction_id': f'TXN_{self.id}_{self.current_attempt}',
                'gateway_response': 'Payment successful',
            }
        else:
            return {
                'success': False,
                'error': 'Payment failed - simulated failure',
                'gateway_response': 'Declined',
            }
    
    def _calculate_success_probability(self):
        """Calculate success probability based on failure reason and attempt"""
        base_probability = 0.3  # 30% base success rate
        
        # Adjust based on failure reason
        reason_adjustments = {
            'insufficient_funds': 0.4,  # Higher chance after delay
            'card_declined': 0.2,       # Lower chance
            'gateway_error': 0.7,       # Higher chance - temporary issue
            'network_error': 0.8,       # Very high chance - temporary issue
            'timeout': 0.6,             # Good chance - temporary issue
        }
        
        probability = reason_adjustments.get(self.failure_reason, base_probability)
        
        # Decrease with each attempt
        probability *= (0.8 ** (self.current_attempt - 1))
        
        return min(probability, 0.9)  # Cap at 90%
    
    def _handle_success(self, result):
        """Handle successful payment retry"""
        self.state = 'success'
        self.success_date = fields.Datetime.now()
        
        # Create payment record
        if result.get('transaction_id'):
            payment = self._create_payment_record(result)
            self.successful_payment_id = payment.id
        
        # Notify stakeholders
        if self.notify_customer:
            self._notify_customer_success()
        
        if self.notify_admin:
            self._notify_admin_success()
        
        self.message_post(body=_('Payment retry successful on attempt %s') % self.current_attempt)
        
        _logger.info(f'Payment retry {self.name} successful on attempt {self.current_attempt}')
    
    def _handle_failure(self, result):
        """Handle failed payment retry"""
        if self.current_attempt >= self.max_retry_attempts:
            self.state = 'failed'
            self.message_post(body=_('Payment retry failed after %s attempts') % self.max_retry_attempts)
            
            # Notify about final failure
            if self.notify_admin:
                self._notify_admin_final_failure()
        else:
            # Schedule next retry
            self.state = 'pending'
            self.next_retry_date = self._calculate_next_retry_date()
            
            self.message_post(body=_('Payment retry attempt %s failed, next retry scheduled for %s') % (
                self.current_attempt, self.next_retry_date
            ))
    
    def _handle_exception(self, error_message):
        """Handle exception during retry"""
        self.state = 'pending'  # Keep it pending for manual review
        self.message_post(body=_('Payment retry encountered exception: %s') % error_message)
    
    def _create_retry_history(self):
        """Create retry history record"""
        return self.env['ams.payment.retry.history'].create({
            'payment_retry_id': self.id,
            'attempt_number': self.current_attempt,
            'attempt_date': fields.Datetime.now(),
            'amount': self.retry_amount,
            'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
        })
    
    def _create_payment_record(self, result):
        """Create payment record for successful transaction"""
        return self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.retry_amount,
            'currency_id': self.currency_id.id,
            'payment_date': fields.Date.today(),
            'ref': f'Payment Retry Success: {self.name}',
            'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
        })
    
    # Retry Scheduling
    def _calculate_next_retry_date(self, base_date=None, attempt=None, 
                                  initial_delay=None, multiplier=None, max_delay=None):
        """Calculate next retry date using exponential backoff"""
        if not base_date:
            base_date = self.last_retry_date or self.original_failure_date
        if attempt is None:
            attempt = self.current_attempt
        if initial_delay is None:
            initial_delay = self.initial_delay_hours
        if multiplier is None:
            multiplier = self.backoff_multiplier
        if max_delay is None:
            max_delay = self.max_delay_hours
        
        # Calculate exponential backoff delay
        delay_hours = initial_delay * (multiplier ** attempt)
        delay_hours = min(delay_hours, max_delay)  # Cap at max delay
        
        next_date = base_date + timedelta(hours=delay_hours)
        
        # Apply time preferences and weekend avoidance
        next_date = self._adjust_retry_date(next_date)
        
        return next_date
    
    def _adjust_retry_date(self, target_date):
        """Adjust retry date for preferences and business rules"""
        adjusted_date = target_date
        
        # Avoid weekends if configured
        if self.avoid_weekends and adjusted_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            # Move to next Monday
            days_to_add = 7 - adjusted_date.weekday()
            adjusted_date = adjusted_date + timedelta(days=days_to_add)
        
        # Adjust for preferred time
        if self.preferred_retry_time == 'morning':
            adjusted_date = adjusted_date.replace(hour=9, minute=0, second=0, microsecond=0)
        elif self.preferred_retry_time == 'afternoon':
            adjusted_date = adjusted_date.replace(hour=14, minute=0, second=0, microsecond=0)
        elif self.preferred_retry_time == 'evening':
            adjusted_date = adjusted_date.replace(hour=18, minute=0, second=0, microsecond=0)
        
        return adjusted_date
    
    def _apply_smart_retry_logic(self):
        """Apply intelligent retry logic based on failure reason"""
        # Adjust retry parameters based on failure reason
        if self.failure_reason == 'insufficient_funds':
            # Longer delays for insufficient funds
            self.initial_delay_hours = 48
            self.max_retry_attempts = 4
        elif self.failure_reason in ['gateway_error', 'network_error', 'timeout']:
            # Shorter delays for temporary issues
            self.initial_delay_hours = 2
            self.backoff_multiplier = 1.5
        elif self.failure_reason == 'card_expired':
            # Fewer attempts for expired cards
            self.max_retry_attempts = 2
            self.initial_delay_hours = 72  # Give time to update
        elif self.failure_reason == 'card_declined':
            # Standard retry with notification
            self.notify_customer = True
        
        # Recalculate next retry date with new parameters
        self.next_retry_date = self._calculate_next_retry_date()
    
    # Notification Methods
    def _notify_customer_success(self):
        """Notify customer of successful payment"""
        template = self.env.ref('ams_subscription_billing.email_template_payment_success', False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _notify_admin_success(self):
        """Notify admin of successful payment retry"""
        _logger.info(f'Payment retry {self.name} successful - notifying admin')
    
    def _notify_admin_final_failure(self):
        """Notify admin of final retry failure"""
        _logger.warning(f'Payment retry {self.name} failed after all attempts - admin notification required')
    
    # Batch Processing
    @api.model
    def cron_process_due_retries(self):
        """Cron job to process due payment retries"""
        now = fields.Datetime.now()
        
        # Find retries that are due
        due_retries = self.search([
            ('state', '=', 'pending'),
            ('auto_retry_enabled', '=', True),
            ('next_retry_date', '<=', now),
            ('current_attempt', '<', self.max_retry_attempts),
        ])
        
        _logger.info(f'Found {len(due_retries)} payment retries due for processing')
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for retry in due_retries:
            try:
                retry._execute_retry()
                processed_count += 1
                
                if retry.state == 'success':
                    success_count += 1
                elif retry.state == 'failed':
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                _logger.error(f'Error processing payment retry {retry.name}: {str(e)}')
        
        _logger.info(f'Payment retry processing completed: {processed_count} processed, {success_count} successful, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'success_count': success_count,
            'error_count': error_count,
            'total_due': len(due_retries),
        }
    
    # Utility Methods
    def action_view_retry_history(self):
        """View retry history"""
        self.ensure_one()
        
        return {
            'name': _('Retry History - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.payment.retry.history',
            'view_mode': 'list,form',
            'domain': [('payment_retry_id', '=', self.id)],
            'context': {'default_payment_retry_id': self.id},
        }
    
    def action_view_invoice(self):
        """View related invoice"""
        self.ensure_one()
        
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def get_retry_summary(self):
        """Get summary of retry attempts"""
        self.ensure_one()
        
        return {
            'retry_id': self.id,
            'retry_name': self.name,
            'subscription_name': self.subscription_id.name,
            'customer_name': self.partner_id.name,
            'failure_reason': self.failure_reason,
            'retry_amount': self.retry_amount,
            'current_attempt': self.current_attempt,
            'max_attempts': self.max_retry_attempts,
            'state': self.state,
            'next_retry_date': self.next_retry_date,
            'success_date': self.success_date,
        }


class AMSPaymentRetryHistory(models.Model):
    """Payment Retry History - Track individual retry attempts"""
    _name = 'ams.payment.retry.history'
    _description = 'AMS Payment Retry History'
    _order = 'attempt_date desc'
    
    payment_retry_id = fields.Many2one(
        'ams.payment.retry',
        string='Payment Retry',
        required=True,
        ondelete='cascade'
    )
    
    attempt_number = fields.Integer(
        string='Attempt Number',
        required=True
    )
    
    attempt_date = fields.Datetime(
        string='Attempt Date',
        required=True,
        default=fields.Datetime.now
    )
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='payment_retry_id.currency_id',
        store=True,
        readonly=True
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Payment Method'
    )
    
    success = fields.Boolean(
        string='Success',
        default=False
    )
    
    error_message = fields.Text(
        string='Error Message'
    )
    
    gateway_response = fields.Text(
        string='Gateway Response'
    )
    
    transaction_id = fields.Char(
        string='Transaction ID'
    )
    
    response_time_ms = fields.Integer(
        string='Response Time (ms)',
        help='Response time from payment gateway in milliseconds'
    )