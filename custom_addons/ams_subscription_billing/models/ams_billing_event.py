# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingEvent(models.Model):
    """Simplified Billing Event - Individual billing occurrences"""
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
        ('manual_billing', 'Manual Billing'),
        ('adjustment_billing', 'Adjustment Billing'),
    ], string='Event Type', required=True, tracking=True, default='regular_billing')
    
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
    
    # Error Information
    error_message = fields.Text(
        string='Error Message',
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
        related='billing_schedule_id.auto_generate_invoice',
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
        
        return super().create(vals_list)
    
    def _calculate_billing_period(self, event_date, subscription_period):
        """Calculate billing period dates"""
        if subscription_period == 'monthly':
            start = event_date.replace(day=1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        elif subscription_period == 'quarterly':
            quarter = ((event_date.month - 1) // 3) + 1
            start = event_date.replace(month=(quarter - 1) * 3 + 1, day=1)
            end = start + relativedelta(months=3) - timedelta(days=1)
        elif subscription_period == 'annual':
            start = event_date.replace(month=1, day=1)
            end = event_date.replace(month=12, day=31)
        else:
            # Default to monthly
            start = event_date.replace(day=1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        
        return {'start': start, 'end': end}
    
    # Actions
    def action_process(self):
        """Process the billing event - simplified version"""
        for event in self:
            if event.state != 'pending':
                raise UserError(_('Only pending events can be processed'))
            
            event.state = 'processing'
            event.processed_date = fields.Datetime.now()
            event.processed_by = self.env.user.id
            
            try:
                # Simple processing - mainly for manual events
                # Regular events are processed by billing schedule
                
                if event.event_type == 'manual_billing':
                    # Generate invoice if not already generated
                    if not event.invoice_id and event.auto_invoice:
                        invoice = event._generate_simple_invoice()
                        if invoice:
                            event.invoice_id = invoice.id
                            event.invoice_amount = invoice.amount_total
                            
                            # Send invoice if configured
                            if event.auto_send_invoice:
                                event._send_invoice(invoice)
                
                event.state = 'completed'
                event.message_post(body=_('Billing event processed successfully'))
                
            except Exception as e:
                event.state = 'failed'
                event.error_message = str(e)
                event.message_post(body=_('Billing event failed: %s') % str(e))
                _logger.error(f'Billing event {event.name} failed: {str(e)}')
    
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
    
    # Simple Invoice Generation
    def _generate_simple_invoice(self):
        """Generate simple invoice for this billing event"""
        self.ensure_one()
        
        subscription = self.subscription_id
        
        # Prepare invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': subscription.partner_id.id,
            'billing_schedule_id': self.billing_schedule_id.id,
            'billing_event_id': self.id,
            'subscription_id': subscription.id,
            'invoice_date': self.event_date,
            'ref': f'Billing Event: {self.name}',
            'narration': self.description,
        }
        
        # Prepare invoice line
        line_vals = {
            'product_id': subscription.product_id.id,
            'name': f'{subscription.product_id.name} - {self.billing_period_start} to {self.billing_period_end}',
            'quantity': subscription.quantity or 1,
            'price_unit': subscription.price,
        }
        
        invoice_vals['invoice_line_ids'] = [(0, 0, line_vals)]
        
        # Create and post invoice
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        return invoice
    
    def _send_invoice(self, invoice):
        """Send invoice to customer"""
        try:
            invoice.action_invoice_sent()
            self.invoice_sent = True
            self.invoice_sent_date = fields.Datetime.now()
            _logger.info(f'Invoice {invoice.name} sent successfully')
        except Exception as e:
            _logger.error(f'Error sending invoice {invoice.name}: {str(e)}')
    
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
    
    # Batch Processing (Simplified)
    @api.model
    def cron_process_pending_billing_events(self):
        """Simplified cron job to process pending billing events"""
        pending_events = self.search([
            ('state', '=', 'pending'),
            ('event_date', '<=', fields.Date.today()),
            ('event_type', '=', 'manual_billing')  # Only process manual events
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
    
    # Analytics and Reporting (Basic)
    def get_event_summary(self):
        """Get basic summary of billing event"""
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
        }