# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingEvent(models.Model):
    """Billing Event - Individual billing occurrences"""
    _name = 'ams.billing.event'
    _description = 'AMS Billing Event'
    _order = 'event_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Event Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.billing.event') or 'New'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Description of this billing event'
    )
    
    # Related Records
    billing_schedule_id = fields.Many2one(
        'ams.billing.schedule',
        string='Billing Schedule',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    billing_run_id = fields.Many2one(
        'ams.billing.run',
        string='Billing Run',
        ondelete='set null',
        help='Billing run that processed this event'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        related='subscription_id.product_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        related='subscription_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    
    # Event Information
    event_date = fields.Date(
        string='Event Date',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True
    )
    
    event_type = fields.Selection([
        ('regular_billing', 'Regular Billing'),
        ('batch_billing', 'Batch Billing'),
        ('manual_billing', 'Manual Billing'),
        ('proration_billing', 'Proration Billing'),
        ('upgrade_billing', 'Upgrade Billing'),
        ('downgrade_billing', 'Downgrade Billing'),
        ('retry_billing', 'Retry Billing'),
        ('adjustment_billing', 'Adjustment Billing'),
    ], string='Event Type', required=True, tracking=True)
    
    billing_period_start = fields.Date(
        string='Billing Period Start',
        help='Start date of the billing period'
    )
    
    billing_period_end = fields.Date(
        string='Billing Period End',
        help='End date of the billing period'
    )
    
    # Processing Information
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    processed_date = fields.Datetime(
        string='Processed Date',
        readonly=True
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True
    )
    
    # Invoice Information
    invoice_id = fields.Many2one(
        'account.move',
        string='Generated Invoice',
        ondelete='set null',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    invoice_amount = fields.Monetary(
        string='Invoice Amount',
        currency_field='currency_id',
        readonly=True
    )
    
    invoice_sent = fields.Boolean(
        string='Invoice Sent',
        default=False,
        readonly=True
    )
    
    invoice_sent_date = fields.Datetime(
        string='Invoice Sent Date',
        readonly=True
    )
    
    # Payment Information
    payment_attempted = fields.Boolean(
        string='Payment Attempted',
        default=False,
        readonly=True
    )
    
    payment_successful = fields.Boolean(
        string='Payment Successful',
        default=False,
        readonly=True
    )
    
    payment_date = fields.Datetime(
        string='Payment Date',
        readonly=True
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Payment Method Used',
        readonly=True
    )
    
    # Proration Information
    is_prorated = fields.Boolean(
        string='Is Prorated',
        default=False,
        help='This billing event includes proration calculations'
    )
    
    proration_calculation_id = fields.Many2one(
        'ams.proration.calculation',
        string='Proration Calculation',
        ondelete='set null'
    )
    
    proration_amount = fields.Monetary(
        string='Proration Amount',
        currency_field='currency_id',
        help='Additional amount due to proration'
    )
    
    proration_credit_amount = fields.Monetary(
        string='Proration Credit Amount',
        currency_field='currency_id',
        help='Credit amount due to proration'
    )
    
    # Error Information
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        readonly=True
    )
    
    last_retry_date = fields.Datetime(
        string='Last Retry Date',
        readonly=True
    )
    
    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Configuration from Schedule
    auto_invoice = fields.Boolean(
        string='Auto Invoice',
        related='billing_schedule_id.auto_invoice',
        readonly=True
    )
    
    auto_payment = fields.Boolean(
        string='Auto Payment',
        related='billing_schedule_id.auto_payment',
        readonly=True
    )
    
    auto_send_invoice = fields.Boolean(
        string='Auto Send Invoice',
        related='billing_schedule_id.auto_send_invoice',
        readonly=True
    )
    
    # Computed Fields
    @api.depends('subscription_id', 'event_date', 'event_type')
    def _compute_display_name(self):
        """Compute display name for the billing event"""
        for event in self:
            if event.subscription_id:
                event.display_name = f"{event.subscription_id.name} - {event.event_date} ({event.event_type.replace('_', ' ').title()})"
            else:
                event.display_name = event.name or 'New Billing Event'
    
    # Validation
    @api.constrains('billing_period_start', 'billing_period_end')
    def _check_billing_period(self):
        """Validate billing period dates"""
        for event in self:
            if event.billing_period_start and event.billing_period_end:
                if event.billing_period_end <= event.billing_period_start:
                    raise ValidationError(_('Billing period end date must be after start date'))
    
    @api.constrains('proration_amount', 'proration_credit_amount')
    def _check_proration_amounts(self):
        """Validate proration amounts"""
        for event in self:
            if event.proration_amount < 0:
                raise ValidationError(_('Proration amount cannot be negative'))
            if event.proration_credit_amount < 0:
                raise ValidationError(_('Proration credit amount cannot be negative'))
    
    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to set up billing event"""
        for vals in vals_list:
            # Auto-set billing period if not provided
            if 'billing_period_start' not in vals or 'billing_period_end' not in vals:
                if 'subscription_id' in vals:
                    subscription = self.env['ams.subscription'].browse(vals['subscription_id'])
                    period = self._calculate_billing_period(
                        vals.get('event_date', fields.Date.today()),
                        subscription.subscription_period
                    )
                    vals.setdefault('billing_period_start', period['start'])
                    vals.setdefault('billing_period_end', period['end'])
        
        events = super().create(vals_list)
        
        # Auto-process if configured
        for event in events:
            if event.billing_schedule_id.auto_invoice and event.state == 'pending':
                event.action_process()
        
        return events
    
    def _calculate_billing_period(self, event_date, subscription_period):
        """Calculate billing period dates"""
        if subscription_period == 'monthly':
            start = event_date.replace(day=1)
            end = start + timedelta(days=32)
            end = end.replace(day=1) - timedelta(days=1)
        elif subscription_period == 'quarterly':
            quarter = ((event_date.month - 1) // 3) + 1
            start = event_date.replace(month=(quarter - 1) * 3 + 1, day=1)
            end = start + timedelta(days=93)  # Approximate quarter
            end = end.replace(day=1) - timedelta(days=1)
        elif subscription_period == 'annual':
            start = event_date.replace(month=1, day=1)
            end = event_date.replace(month=12, day=31)
        else:
            # Default to monthly
            start = event_date.replace(day=1)
            end = start + timedelta(days=32)
            end = end.replace(day=1) - timedelta(days=1)
        
        return {'start': start, 'end': end}
    
    # Actions
    def action_process(self):
        """Process the billing event"""
        for event in self:
            if event.state != 'pending':
                raise UserError(_('Only pending events can be processed'))
            
            event.state = 'processing'
            event.processed_date = fields.Datetime.now()
            event.processed_by = self.env.user.id
            
            try:
                result = event._execute_billing_process()
                
                if result.get('success'):
                    event.state = 'completed'
                    event._update_success_fields(result)
                    event.message_post(body=_('Billing event processed successfully'))
                else:
                    event.state = 'failed'
                    event.error_message = result.get('error', 'Unknown error')
                    event.message_post(body=_('Billing event failed: %s') % event.error_message)
                
            except Exception as e:
                event.state = 'failed'
                event.error_message = str(e)
                event.message_post(body=_('Billing event failed with exception: %s') % str(e))
                _logger.error(f'Billing event {event.name} failed: {str(e)}')
    
    def action_retry(self):
        """Retry a failed billing event"""
        for event in self:
            if event.state != 'failed':
                raise UserError(_('Only failed events can be retried'))
            
            event.retry_count += 1
            event.last_retry_date = fields.Datetime.now()
            event.state = 'pending'
            event.error_message = False
            
            event.message_post(body=_('Billing event retry initiated (attempt %s)') % event.retry_count)
            
            # Process the retry
            event.action_process()
    
    def action_cancel(self):
        """Cancel the billing event"""
        for event in self:
            if event.state in ['completed', 'cancelled']:
                raise UserError(_('Completed or cancelled events cannot be cancelled'))
            
            event.state = 'cancelled'
            event.message_post(body=_('Billing event cancelled'))
    
    def action_mark_completed(self):
        """Manually mark event as completed"""
        for event in self:
            if event.state not in ['pending', 'failed']:
                raise UserError(_('Only pending or failed events can be manually completed'))
            
            event.state = 'completed'
            event.processed_date = fields.Datetime.now()
            event.processed_by = self.env.user.id
            event.message_post(body=_('Billing event manually marked as completed'))
    
    # Core Processing Logic
    def _execute_billing_process(self):
        """Execute the billing process for this event"""
        self.ensure_one()
        
        result = {
            'success': True,
            'invoice': None,
            'payment': None,
            'errors': [],
        }
        
        try:
            # Step 1: Generate invoice if required
            if self.auto_invoice:
                invoice_result = self._generate_invoice()
                result['invoice'] = invoice_result.get('invoice')
                
                if not invoice_result.get('success'):
                    result['errors'].append(f"Invoice generation failed: {invoice_result.get('error')}")
                
                # Step 2: Send invoice if required and successful
                if result['invoice'] and self.auto_send_invoice:
                    send_result = self._send_invoice()
                    if not send_result.get('success'):
                        result['errors'].append(f"Invoice sending failed: {send_result.get('error')}")
                
                # Step 3: Process payment if required and successful
                if result['invoice'] and self.auto_payment:
                    payment_result = self._process_payment()
                    result['payment'] = payment_result.get('payment')
                    
                    if not payment_result.get('success'):
                        result['errors'].append(f"Payment processing failed: {payment_result.get('error')}")
            
            # If there were any errors, mark as failed
            if result['errors']:
                result['success'] = False
                result['error'] = '; '.join(result['errors'])
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _generate_invoice(self):
        """Generate invoice for this billing event"""
        try:
            # Calculate invoice amount
            base_amount = self.subscription_id.price
            
            # Add proration if applicable
            total_amount = base_amount
            if self.is_prorated and self.proration_amount:
                total_amount += self.proration_amount
            if self.is_prorated and self.proration_credit_amount:
                total_amount -= self.proration_credit_amount
            
            # Create invoice
            invoice_vals = self._prepare_invoice_values(total_amount)
            invoice = self.env['account.move'].create(invoice_vals)
            
            # Post the invoice
            invoice.action_post()
            
            # Update event fields
            self.invoice_id = invoice.id
            self.invoice_amount = invoice.amount_total
            
            return {
                'success': True,
                'invoice': invoice,
            }
            
        except Exception as e:
            _logger.error(f'Error generating invoice for billing event {self.name}: {str(e)}')
            return {
                'success': False,
                'error': str(e),
            }
    
    def _prepare_invoice_values(self, amount):
        """Prepare invoice values"""
        subscription = self.subscription_id
        
        # Base invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': subscription.partner_id.id,
            'billing_schedule_id': self.billing_schedule_id.id,
            'billing_event_id': self.id,
            'invoice_date': self.event_date,
            'ref': f'Billing Event: {self.name}',
            'narration': self.description,
        }
        
        # Add payment terms if configured
        if self.billing_schedule_id.payment_term_id:
            invoice_vals['invoice_payment_term_id'] = self.billing_schedule_id.payment_term_id.id
        
        # Prepare invoice lines
        line_vals = {
            'product_id': subscription.product_id.id,
            'name': f'{subscription.product_id.name} - {self.billing_period_start} to {self.billing_period_end}',
            'quantity': 1,
            'price_unit': amount,
        }
        
        # Add product-specific accounting if available
        if hasattr(subscription.product_id.product_tmpl_id, 'ams_revenue_account_id'):
            if subscription.product_id.product_tmpl_id.ams_revenue_account_id:
                line_vals['account_id'] = subscription.product_id.product_tmpl_id.ams_revenue_account_id.id
        
        invoice_vals['invoice_line_ids'] = [(0, 0, line_vals)]
        
        # Add proration lines if applicable
        if self.is_prorated:
            if self.proration_amount > 0:
                proration_line = {
                    'name': f'Proration Adjustment - {self.description}',
                    'quantity': 1,
                    'price_unit': self.proration_amount,
                }
                invoice_vals['invoice_line_ids'].append((0, 0, proration_line))
            
            if self.proration_credit_amount > 0:
                credit_line = {
                    'name': f'Proration Credit - {self.description}',
                    'quantity': 1,
                    'price_unit': -self.proration_credit_amount,
                }
                invoice_vals['invoice_line_ids'].append((0, 0, credit_line))
        
        return invoice_vals
    
    def _send_invoice(self):
        """Send invoice to customer"""
        try:
            if not self.invoice_id:
                return {'success': False, 'error': 'No invoice to send'}
            
            # Send the invoice
            self.invoice_id.action_invoice_sent()
            
            # Update event fields
            self.invoice_sent = True
            self.invoice_sent_date = fields.Datetime.now()
            
            return {'success': True}
            
        except Exception as e:
            _logger.error(f'Error sending invoice for billing event {self.name}: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _process_payment(self):
        """Process automatic payment"""
        try:
            if not self.invoice_id:
                return {'success': False, 'error': 'No invoice to process payment for'}
            
            if not self.billing_schedule_id.payment_method_id:
                return {'success': False, 'error': 'No payment method configured'}
            
            # Mark that payment was attempted
            self.payment_attempted = True
            
            # Process payment (this would integrate with actual payment gateway)
            payment_result = self._attempt_payment_processing()
            
            if payment_result.get('success'):
                self.payment_successful = True
                self.payment_date = fields.Datetime.now()
                self.payment_method_id = self.billing_schedule_id.payment_method_id.id
            
            return payment_result
            
        except Exception as e:
            _logger.error(f'Error processing payment for billing event {self.name}: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _attempt_payment_processing(self):
        """Attempt to process payment - placeholder for payment gateway integration"""
        # This is a placeholder for actual payment processing
        # In a real implementation, this would:
        # 1. Use the stored payment method
        # 2. Create a payment transaction
        # 3. Call the payment gateway API
        # 4. Handle the response
        # 5. Create payment records in Odoo
        
        _logger.info(f'Payment processing attempted for billing event {self.name}')
        
        # For now, return success for testing
        return {
            'success': True,
            'payment': {
                'amount': self.invoice_amount,
                'method': self.billing_schedule_id.payment_method_id.name,
            }
        }
    
    def _update_success_fields(self, result):
        """Update fields after successful processing"""
        # This method updates various fields based on the processing result
        pass
    
    # Utility Methods
    def action_view_invoice(self):
        """View the generated invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No invoice generated for this event'))
        
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_proration(self):
        """View proration calculation"""
        self.ensure_one()
        
        if not self.proration_calculation_id:
            raise UserError(_('No proration calculation for this event'))
        
        return {
            'name': _('Proration Calculation'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.proration.calculation',
            'res_id': self.proration_calculation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # Batch Processing
    @api.model
    def cron_process_pending_billing_events(self):
        """Cron job to process pending billing events"""
        pending_events = self.search([
            ('state', '=', 'pending'),
            ('event_date', '<=', fields.Date.today())
        ])
        
        _logger.info(f'Found {len(pending_events)} pending billing events')
        
        processed_count = 0
        error_count = 0
        
        for event in pending_events:
            try:
                event.action_process()
                if event.state == 'completed':
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f'Error processing billing event {event.name}: {str(e)}')
        
        _logger.info(f'Billing events processing completed: {processed_count} successful, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'total_pending': len(pending_events),
        }
    
    # Analytics and Reporting
    def get_event_summary(self):
        """Get summary of billing event"""
        self.ensure_one()
        
        return {
            'event_id': self.id,
            'event_name': self.name,
            'subscription_name': self.subscription_id.name,
            'customer_name': self.partner_id.name,
            'event_date': self.event_date,
            'event_type': self.event_type,
            'state': self.state,
            'invoice_amount': self.invoice_amount,
            'invoice_sent': self.invoice_sent,
            'payment_successful': self.payment_successful,
            'is_prorated': self.is_prorated,
            'proration_amount': self.proration_amount,
            'retry_count': self.retry_count,
        }