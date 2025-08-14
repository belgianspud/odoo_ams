# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    """Extend Account Move (Invoice) with AMS Billing Functionality"""
    _inherit = 'account.move'

    # =============================================================================
    # BILLING-SPECIFIC FIELDS
    # =============================================================================
    
    # AMS Billing References
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='AMS Subscription',
        ondelete='set null',
        index=True,
        help='Related AMS subscription for this invoice'
    )
    
    billing_schedule_id = fields.Many2one(
        'ams.billing.schedule',
        string='Billing Schedule',
        ondelete='set null',
        help='Billing schedule that generated this invoice'
    )
    
    billing_event_id = fields.Many2one(
        'ams.billing.event',
        string='Billing Event',
        ondelete='set null',
        help='Billing event that generated this invoice'
    )
    
    billing_run_id = fields.Many2one(
        'ams.billing.run',
        string='Billing Run',
        ondelete='set null',
        help='Billing run that generated this invoice'
    )
    
    proration_calculation_id = fields.Many2one(
        'ams.proration.calculation',
        string='Proration Calculation',
        ondelete='set null',
        help='Proration calculation for this invoice'
    )
    
    # Billing Type Classification
    billing_type = fields.Selection([
        ('regular', 'Regular Billing'),
        ('proration', 'Proration Adjustment'),
        ('upgrade', 'Upgrade Charge'),
        ('downgrade', 'Downgrade Credit'),
        ('one_time', 'One-time Charge'),
        ('setup_fee', 'Setup Fee'),
        ('overage', 'Usage Overage'),
        ('penalty', 'Late Fee/Penalty'),
        ('manual', 'Manual Invoice'),
    ], string='Billing Type', default='regular',
    help='Type of billing this invoice represents')
    
    is_subscription_invoice = fields.Boolean(
        string='Is Subscription Invoice',
        compute='_compute_subscription_invoice',
        store=True,
        help='This invoice is related to subscription billing'
    )
    
    # Billing Period Information
    billing_period_start = fields.Date(
        string='Billing Period Start',
        help='Start date of the billing period covered by this invoice'
    )
    
    billing_period_end = fields.Date(
        string='Billing Period End',
        help='End date of the billing period covered by this invoice'
    )
    
    billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Frequency',
    help='Billing frequency for this subscription invoice')
    
    # Payment Processing
    auto_payment_enabled = fields.Boolean(
        string='Auto Payment Enabled',
        help='Automatic payment processing is enabled for this invoice'
    )
    
    auto_payment_attempted = fields.Boolean(
        string='Auto Payment Attempted',
        default=False,
        readonly=True
    )
    
    auto_payment_success = fields.Boolean(
        string='Auto Payment Successful',
        default=False,
        readonly=True
    )
    
    auto_payment_attempt_date = fields.Datetime(
        string='Auto Payment Attempt Date',
        readonly=True
    )
    
    auto_payment_error = fields.Text(
        string='Auto Payment Error',
        readonly=True
    )
    
    # Payment Retry Information
    payment_retry_ids = fields.One2many(
        'ams.payment.retry',
        'invoice_id',
        string='Payment Retries'
    )
    
    payment_retry_count = fields.Integer(
        string='Payment Retry Count',
        compute='_compute_payment_retry_info',
        store=True
    )
    
    has_active_retry = fields.Boolean(
        string='Has Active Payment Retry',
        compute='_compute_payment_retry_info',
        store=True
    )
    
    # Dunning Information
    dunning_process_ids = fields.One2many(
        'ams.dunning.process',
        'invoice_id',
        string='Dunning Processes'
    )
    
    in_dunning_process = fields.Boolean(
        string='In Dunning Process',
        compute='_compute_dunning_status',
        store=True
    )
    
    dunning_level = fields.Integer(
        string='Dunning Level',
        compute='_compute_dunning_status',
        store=True,
        help='Current dunning level (0 = no dunning, higher = more severe)'
    )
    
    last_dunning_date = fields.Date(
        string='Last Dunning Date',
        compute='_compute_dunning_status',
        store=True
    )
    
    # Customer Communication
    auto_sent = fields.Boolean(
        string='Automatically Sent',
        default=False,
        help='Invoice was automatically sent to customer'
    )
    
    auto_send_date = fields.Datetime(
        string='Auto Send Date',
        readonly=True
    )
    
    email_sent_count = fields.Integer(
        string='Email Sent Count',
        default=0,
        help='Number of times this invoice was emailed'
    )
    
    last_email_date = fields.Datetime(
        string='Last Email Date',
        readonly=True
    )
    
    # Access and Restrictions
    affects_service_access = fields.Boolean(
        string='Affects Service Access',
        default=True,
        help='Non-payment of this invoice affects service access'
    )
    
    grace_period_end = fields.Date(
        string='Grace Period End',
        help='Date when grace period for this invoice ends'
    )
    
    suspend_service_date = fields.Date(
        string='Service Suspension Date',
        help='Date when service will be suspended for non-payment'
    )
    
    # Financial Information
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_payment_amounts',
        currency_field='currency_id',
        store=True
    )
    
    amount_residual_signed = fields.Monetary(
        string='Amount Due (Signed)',
        compute='_compute_payment_amounts',
        currency_field='currency_id',
        store=True,
        help='Amount due with proper sign (positive for customer invoices)'
    )
    
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue_info',
        store=True
    )
    
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_overdue_info',
        store=True
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('subscription_id', 'billing_schedule_id', 'billing_event_id')
    def _compute_subscription_invoice(self):
        """Determine if this is a subscription invoice"""
        for invoice in self:
            invoice.is_subscription_invoice = bool(
                invoice.subscription_id or 
                invoice.billing_schedule_id or 
                invoice.billing_event_id
            )
    
    @api.depends('payment_retry_ids')
    def _compute_payment_retry_info(self):
        """Compute payment retry information"""
        for invoice in self:
            retries = invoice.payment_retry_ids
            invoice.payment_retry_count = len(retries)
            invoice.has_active_retry = bool(
                retries.filtered(lambda r: r.state in ['pending', 'retrying'])
            )
    
    @api.depends('dunning_process_ids')
    def _compute_dunning_status(self):
        """Compute dunning status information"""
        for invoice in self:
            active_processes = invoice.dunning_process_ids.filtered(
                lambda dp: dp.state == 'active'
            )
            
            invoice.in_dunning_process = bool(active_processes)
            
            if active_processes:
                # Get highest dunning level
                invoice.dunning_level = max(active_processes.mapped('current_step'))
                # Get most recent dunning date
                invoice.last_dunning_date = max(
                    active_processes.mapped('last_action_date'),
                    default=False
                )
            else:
                invoice.dunning_level = 0
                invoice.last_dunning_date = False
    
    @api.depends('payment_ids', 'amount_total')
    def _compute_payment_amounts(self):
        """Compute payment-related amounts"""
        for invoice in self:
            # Calculate total paid (considering payment state)
            if invoice.payment_state == 'paid':
                invoice.total_paid = invoice.amount_total
            elif invoice.payment_state == 'partial':
                invoice.total_paid = invoice.amount_total - invoice.amount_residual
            else:
                invoice.total_paid = 0.0
            
            # Calculate amount residual with proper sign
            if invoice.move_type == 'out_invoice':
                invoice.amount_residual_signed = invoice.amount_residual
            elif invoice.move_type == 'out_refund':
                invoice.amount_residual_signed = -invoice.amount_residual
            else:
                invoice.amount_residual_signed = invoice.amount_residual
    
    @api.depends('invoice_date_due', 'payment_state')
    def _compute_overdue_info(self):
        """Compute overdue information"""
        today = fields.Date.today()
        
        for invoice in self:
            if (invoice.invoice_date_due and 
                invoice.payment_state in ['not_paid', 'partial'] and
                invoice.invoice_date_due < today):
                invoice.is_overdue = True
                invoice.days_overdue = (today - invoice.invoice_date_due).days
            else:
                invoice.is_overdue = False
                invoice.days_overdue = 0
    
    # =============================================================================
    # VALIDATION AND CONSTRAINTS
    # =============================================================================
    
    @api.constrains('billing_period_start', 'billing_period_end')
    def _check_billing_period(self):
        """Validate billing period dates"""
        for invoice in self:
            if invoice.billing_period_start and invoice.billing_period_end:
                if invoice.billing_period_end <= invoice.billing_period_start:
                    raise ValidationError(_('Billing period end must be after start date'))
    
    @api.constrains('subscription_id', 'move_type')
    def _check_subscription_invoice_type(self):
        """Validate subscription invoice type"""
        for invoice in self:
            if invoice.subscription_id and invoice.move_type not in ['out_invoice', 'out_refund']:
                raise ValidationError(_('Subscription invoices must be customer invoices or refunds'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Update fields when subscription changes"""
        if self.subscription_id:
            # Set partner
            self.partner_id = self.subscription_id.partner_id
            
            # Set payment terms
            if self.subscription_id.payment_term_id:
                self.invoice_payment_term_id = self.subscription_id.payment_term_id
            
            # Set auto payment
            self.auto_payment_enabled = self.subscription_id.enable_auto_payment
            
            # Set billing type
            if not self.billing_type or self.billing_type == 'regular':
                self.billing_type = 'regular'
    
    # =============================================================================
    # BILLING LIFECYCLE METHODS
    # =============================================================================
    
    def action_post(self):
        """Override posting to handle billing workflows"""
        result = super().action_post()
        
        for invoice in self:
            if invoice.is_subscription_invoice:
                invoice._handle_subscription_invoice_posted()
        
        return result
    
    def _handle_subscription_invoice_posted(self):
        """Handle subscription invoice posting"""
        self.ensure_one()
        
        # Auto-send invoice if configured
        if (self.subscription_id and 
            self.subscription_id.auto_send_invoices and 
            not self.auto_sent):
            self._auto_send_invoice()
        
        # Schedule auto-payment if configured
        if (self.auto_payment_enabled and 
            self.subscription_id and 
            self.subscription_id.payment_method_id and
            not self.auto_payment_attempted):
            self._schedule_auto_payment()
        
        # Set grace period
        self._set_grace_period()
        
        # Update subscription billing dates
        if self.subscription_id and self.billing_type == 'regular':
            self.subscription_id.last_billing_date = self.invoice_date
    
    def _auto_send_invoice(self):
        """Automatically send invoice to customer"""
        try:
            self.action_invoice_sent()
            self.auto_sent = True
            self.auto_send_date = fields.Datetime.now()
            self.email_sent_count += 1
            self.last_email_date = fields.Datetime.now()
            
            _logger.info(f'Auto-sent invoice {self.name} to {self.partner_id.name}')
            
        except Exception as e:
            _logger.error(f'Failed to auto-send invoice {self.name}: {str(e)}')
            
            # Create activity for manual follow-up
            self.activity_schedule(
                'mail.mail_activity_data_email',
                summary=_('Failed to auto-send invoice'),
                note=_('Automatic invoice sending failed: %s') % str(e)
            )
    
    def _schedule_auto_payment(self):
        """Schedule automatic payment processing"""
        try:
            # This would typically integrate with payment processing
            # For now, create a delayed job or schedule processing
            
            self.auto_payment_attempted = True
            self.auto_payment_attempt_date = fields.Datetime.now()
            
            # Attempt payment processing
            payment_result = self._attempt_auto_payment()
            
            if payment_result.get('success'):
                self.auto_payment_success = True
                _logger.info(f'Auto-payment successful for invoice {self.name}')
            else:
                self.auto_payment_error = payment_result.get('error', 'Payment failed')
                _logger.warning(f'Auto-payment failed for invoice {self.name}: {self.auto_payment_error}')
                
                # Create payment retry if payment failed
                self._create_payment_retry(payment_result.get('error'))
                
        except Exception as e:
            self.auto_payment_error = str(e)
            _logger.error(f'Exception during auto-payment for invoice {self.name}: {str(e)}')
            
            # Create payment retry for exception
            self._create_payment_retry(str(e))
    
    def _attempt_auto_payment(self):
        """Attempt automatic payment processing"""
        # This is a placeholder for actual payment gateway integration
        # In real implementation, this would:
        # 1. Get stored payment method from subscription
        # 2. Create payment transaction with gateway
        # 3. Handle gateway response
        # 4. Create payment record in Odoo if successful
        
        if not self.subscription_id.payment_method_id:
            return {'success': False, 'error': 'No payment method configured'}
        
        # Simulate payment processing
        _logger.info(f'Attempting auto-payment for invoice {self.name}')
        
        # Return success for testing - replace with actual gateway call
        return {
            'success': False,  # Set to False to test retry logic
            'error': 'Simulated payment failure for testing',
            'transaction_id': None,
        }
    
    def _create_payment_retry(self, failure_reason):
        """Create payment retry record for failed payment"""
        if not self.subscription_id:
            return
        
        # Determine failure reason category
        failure_category = self._categorize_payment_failure(failure_reason)
        
        retry = self.env['ams.payment.retry'].create({
            'subscription_id': self.subscription_id.id,
            'invoice_id': self.id,
            'failure_reason': failure_category,
            'failure_message': failure_reason,
            'retry_amount': self.amount_residual,
            'payment_method_id': self.subscription_id.payment_method_id.id,
        })
        
        _logger.info(f'Created payment retry {retry.name} for invoice {self.name}')
        return retry
    
    def _categorize_payment_failure(self, error_message):
        """Categorize payment failure based on error message"""
        error_lower = error_message.lower()
        
        if 'insufficient' in error_lower or 'funds' in error_lower:
            return 'insufficient_funds'
        elif 'declined' in error_lower or 'denied' in error_lower:
            return 'card_declined'
        elif 'expired' in error_lower:
            return 'card_expired'
        elif 'network' in error_lower or 'connection' in error_lower:
            return 'network_error'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif 'gateway' in error_lower or 'processor' in error_lower:
            return 'gateway_error'
        else:
            return 'other'
    
    def _set_grace_period(self):
        """Set grace period for this invoice"""
        if not self.subscription_id:
            return
        
        # Get dunning sequence to determine grace period
        sequence = (self.subscription_id.dunning_sequence_id or 
                   self.subscription_id._get_default_dunning_sequence())
        
        if sequence and sequence.grace_period_days > 0:
            grace_days = sequence.grace_period_days
            self.grace_period_end = self.invoice_date_due + timedelta(days=grace_days)
            
            # Calculate suspension date
            if sequence.suspension_after_final:
                suspension_delay = sequence.suspension_delay_days or 0
                self.suspend_service_date = self.grace_period_end + timedelta(days=suspension_delay)
    
    # =============================================================================
    # PAYMENT AND DUNNING ACTIONS
    # =============================================================================
    
    def action_retry_payment(self):
        """Manually retry payment for this invoice"""
        self.ensure_one()
        
        if self.payment_state == 'paid':
            raise UserError(_('Invoice is already paid'))
        
        if not self.subscription_id:
            raise UserError(_('Payment retry is only available for subscription invoices'))
        
        if not self.subscription_id.payment_method_id:
            raise UserError(_('No payment method configured for subscription'))
        
        # Check for existing active retry
        active_retry = self.payment_retry_ids.filtered(
            lambda r: r.state in ['pending', 'retrying']
        )
        
        if active_retry:
            active_retry.action_retry_now()
        else:
            # Create new retry
            retry = self._create_payment_retry('Manual retry requested')
            retry.action_retry_now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment retry initiated'),
                'type': 'info',
            }
        }
    
    def action_start_dunning(self):
        """Start dunning process for this invoice"""
        self.ensure_one()
        
        if self.payment_state == 'paid':
            raise UserError(_('Cannot start dunning for paid invoice'))
        
        if not self.is_overdue and not self.auto_payment_attempted:
            raise UserError(_('Invoice must be overdue or have failed payment to start dunning'))
        
        # Check for existing active dunning
        active_dunning = self.dunning_process_ids.filtered(
            lambda dp: dp.state == 'active'
        )
        
        if active_dunning:
            raise UserError(_('Dunning process is already active for this invoice'))
        
        # Get dunning sequence
        if self.subscription_id:
            sequence = (self.subscription_id.dunning_sequence_id or 
                       self.subscription_id._get_default_dunning_sequence())
        else:
            sequence = self.env['ams.dunning.sequence'].search([('is_default', '=', True)], limit=1)
        
        if not sequence:
            raise UserError(_('No dunning sequence configured'))
        
        # Create dunning process
        dunning = self.env['ams.dunning.process'].create({
            'subscription_id': self.subscription_id.id if self.subscription_id else False,
            'invoice_id': self.id,
            'dunning_sequence_id': sequence.id,
            'failure_date': self.invoice_date_due or self.invoice_date,
            'failure_reason': 'payment_overdue',
            'failed_amount': self.amount_residual,
        })
        
        return {
            'name': _('Dunning Process'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.dunning.process',
            'res_id': dunning.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_suspend_service(self):
        """Suspend service for non-payment"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_('Service suspension is only available for subscription invoices'))
        
        if self.subscription_id.state == 'suspended':
            raise UserError(_('Subscription is already suspended'))
        
        # Suspend the subscription
        self.subscription_id.action_suspend_for_non_payment()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Service suspended for non-payment'),
                'type': 'warning',
            }
        }
    
    def action_extend_grace_period(self):
        """Extend grace period for this invoice"""
        self.ensure_one()
        
        return {
            'name': _('Extend Grace Period'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.extend.grace.period.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_current_grace_end': self.grace_period_end,
            }
        }
    
    # =============================================================================
    # OVERRIDE PAYMENT REGISTRATION
    # =============================================================================
    
    def _get_reconciled_info_JSON_values(self):
        """Override to handle subscription payment reconciliation"""
        result = super()._get_reconciled_info_JSON_values()
        
        # Handle subscription reactivation if fully paid
        for invoice in self:
            if (invoice.subscription_id and 
                invoice.payment_state == 'paid' and 
                invoice.subscription_id.state == 'suspended'):
                
                # Check if all invoices for subscription are paid
                unpaid_invoices = invoice.subscription_id.subscription_invoice_ids.filtered(
                    lambda inv: inv.state == 'posted' and inv.payment_state in ['not_paid', 'partial']
                )
                
                if not unpaid_invoices:
                    # All invoices paid - can reactivate
                    invoice.subscription_id.action_reactivate_after_payment()
        
        return result
    
    def register_payment(self, payment_vals):
        """Override payment registration to handle subscription logic"""
        result = super().register_payment(payment_vals)
        
        for invoice in self:
            if invoice.subscription_id:
                invoice._handle_subscription_payment_received()
        
        return result
    
    def _handle_subscription_payment_received(self):
        """Handle payment received for subscription invoice"""
        self.ensure_one()
        
        # Cancel active payment retries
        active_retries = self.payment_retry_ids.filtered(
            lambda r: r.state in ['pending', 'retrying']
        )
        active_retries.action_cancel()
        
        # Complete dunning processes if invoice is fully paid
        if self.payment_state == 'paid':
            active_dunning = self.dunning_process_ids.filtered(
                lambda dp: dp.state == 'active'
            )
            active_dunning.action_complete()
        
        # Log payment received
        self.message_post(
            body=_('Payment received for subscription invoice. Amount: %s') % payment_vals.get('amount', 0)
        )
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def action_view_subscription(self):
        """View related subscription"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_('No subscription linked to this invoice'))
        
        return {
            'name': _('Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_billing_schedule(self):
        """View related billing schedule"""
        self.ensure_one()
        
        if not self.billing_schedule_id:
            raise UserError(_('No billing schedule linked to this invoice'))
        
        return {
            'name': _('Billing Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.schedule',
            'res_id': self.billing_schedule_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_payment_retries(self):
        """View payment retries for this invoice"""
        self.ensure_one()
        
        return {
            'name': _('Payment Retries'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.payment.retry',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }
    
    def action_view_dunning_processes(self):
        """View dunning processes for this invoice"""
        self.ensure_one()
        
        return {
            'name': _('Dunning Processes'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.dunning.process',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
        }
    
    def get_payment_portal_url(self):
        """Get payment portal URL for customer"""
        self.ensure_one()
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/invoices/{self.id}"
    
    def send_payment_reminder(self):
        """Send payment reminder email"""
        self.ensure_one()
        
        if self.payment_state == 'paid':
            raise UserError(_('Invoice is already paid'))
        
        # Find payment reminder template
        template = self.env.ref('ams_subscription_billing.email_template_payment_reminder', False)
        if not template:
            raise UserError(_('Payment reminder email template not found'))
        
        # Send email
        template.send_mail(self.id, force_send=True)
        
        # Update tracking
        self.email_sent_count += 1
        self.last_email_date = fields.Datetime.now()
        
        self.message_post(body=_('Payment reminder sent to customer'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment reminder sent successfully'),
                'type': 'success',
            }
        }
    
    # =============================================================================
    # REPORTING AND ANALYTICS
    # =============================================================================
    
    def get_billing_summary(self):
        """Get billing summary for this invoice"""
        self.ensure_one()
        
        return {
            'invoice_id': self.id,
            'invoice_number': self.name,
            'subscription_name': self.subscription_id.name if self.subscription_id else None,
            'customer_name': self.partner_id.name,
            'billing_type': self.billing_type,
            'amount_total': self.amount_total,
            'amount_paid': self.total_paid,
            'amount_due': self.amount_residual,
            'payment_state': self.payment_state,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'in_dunning': self.in_dunning_process,
            'dunning_level': self.dunning_level,
            'has_retry': self.has_active_retry,
            'retry_count': self.payment_retry_count,
            'billing_period_start': self.billing_period_start,
            'billing_period_end': self.billing_period_end,
            'auto_payment_attempted': self.auto_payment_attempted,
            'auto_payment_success': self.auto_payment_success,
        }
    
    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================
    
    @api.model
    def cron_process_overdue_invoices(self):
        """Cron job to process overdue invoices"""
        today = fields.Date.today()
        
        # Find overdue subscription invoices
        overdue_invoices = self.search([
            ('is_subscription_invoice', '=', True),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('in_dunning_process', '=', False),
        ])
        
        _logger.info(f'Found {len(overdue_invoices)} overdue subscription invoices')
        
        processed_count = 0
        error_count = 0
        
        for invoice in overdue_invoices:
            try:
                # Check if grace period has ended
                if invoice.grace_period_end and today <= invoice.grace_period_end:
                    continue  # Still in grace period
                
                # Start dunning process
                invoice.action_start_dunning()
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                _logger.error(f'Error processing overdue invoice {invoice.name}: {str(e)}')
        
        _logger.info(f'Overdue invoice processing completed: {processed_count} processed, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'total_overdue': len(overdue_invoices),
        }
    
    @api.model
    def cron_send_payment_reminders(self):
        """Cron job to send payment reminders"""
        today = fields.Date.today()
        
        # Find invoices that need payment reminders
        # (e.g., due tomorrow, or due today but not yet sent reminder)
        reminder_invoices = self.search([
            ('is_subscription_invoice', '=', True),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '>=', today - timedelta(days=1)),
            ('invoice_date_due', '<=', today + timedelta(days=1)),
            ('email_sent_count', '<', 2),  # Don't spam customers
        ])
        
        _logger.info(f'Found {len(reminder_invoices)} invoices for payment reminders')
        
        sent_count = 0
        error_count = 0
        
        for invoice in reminder_invoices:
            try:
                invoice.send_payment_reminder()
                sent_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f'Error sending payment reminder for invoice {invoice.name}: {str(e)}')
        
        _logger.info(f'Payment reminder sending completed: {sent_count} sent, {error_count} errors')
        
        return {
            'sent_count': sent_count,
            'error_count': error_count,
            'total_candidates': len(reminder_invoices),
        }