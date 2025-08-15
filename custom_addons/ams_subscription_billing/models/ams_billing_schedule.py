# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingSchedule(models.Model):
    """Simplified Billing Schedule for AMS Subscriptions"""
    _name = 'ams.billing.schedule'
    _description = 'AMS Billing Schedule'
    _order = 'next_billing_date asc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Schedule Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.billing.schedule') or 'New'
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
    
    # Billing Configuration
    billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Frequency', required=True, tracking=True)
    
    # Billing Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    next_billing_date = fields.Date(
        string='Next Billing Date',
        required=True,
        index=True,
        tracking=True
    )
    
    last_billing_date = fields.Date(
        string='Last Billing Date',
        readonly=True
    )
    
    # Simple Automation Settings
    auto_generate_invoice = fields.Boolean(
        string='Auto Generate Invoice',
        default=True,
        help='Automatically generate invoices on billing date'
    )
    
    auto_send_invoice = fields.Boolean(
        string='Auto Send Invoice',
        default=True,
        help='Automatically send invoice to customer'
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Basic Statistics
    total_invoices = fields.Integer(
        string='Total Invoices',
        compute='_compute_billing_stats',
        store=True
    )
    
    total_billed_amount = fields.Monetary(
        string='Total Billed Amount',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Related Records
    billing_event_ids = fields.One2many(
        'ams.billing.event',
        'billing_schedule_id',
        string='Billing Events'
    )
    
    invoice_ids = fields.One2many(
        'account.move',
        'billing_schedule_id',
        string='Generated Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    notes = fields.Text(
        string='Notes',
        help='Internal notes about this billing schedule'
    )
    
    # Computed Fields
    @api.depends('subscription_id', 'billing_frequency', 'partner_id')
    def _compute_display_name(self):
        """Compute display name for the billing schedule"""
        for schedule in self:
            if schedule.subscription_id and schedule.partner_id:
                schedule.display_name = _("%s - %s (%s)") % (
                    schedule.partner_id.name,
                    schedule.subscription_id.name,
                    schedule.billing_frequency.title()
                )
            else:
                schedule.display_name = schedule.name or _('New Billing Schedule')
    
    @api.depends('invoice_ids')
    def _compute_billing_stats(self):
        """Compute basic billing statistics"""
        for schedule in self:
            invoices = schedule.invoice_ids.filtered(lambda i: i.state == 'posted')
            schedule.total_invoices = len(invoices)
            schedule.total_billed_amount = sum(invoices.mapped('amount_total'))
    
    # Validation
    @api.constrains('start_date', 'next_billing_date')
    def _check_dates(self):
        """Validate billing dates"""
        for schedule in self:
            if schedule.next_billing_date and schedule.start_date:
                if schedule.next_billing_date < schedule.start_date:
                    raise ValidationError(_('Next billing date cannot be before start date'))
    
    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to set up billing schedule"""
        for vals in vals_list:
            # Set billing frequency from subscription if not provided
            if 'subscription_id' in vals and not vals.get('billing_frequency'):
                subscription = self.env['ams.subscription'].browse(vals['subscription_id'])
                vals['billing_frequency'] = subscription.subscription_period
            
            # Calculate next billing date if not provided
            if not vals.get('next_billing_date') and vals.get('start_date'):
                vals['next_billing_date'] = vals['start_date']
        
        schedules = super().create(vals_list)
        
        # Auto-activate if subscription is active
        for schedule in schedules:
            if schedule.subscription_id.state == 'active' and schedule.state == 'draft':
                schedule.action_activate()
        
        return schedules
    
    # Actions
    def action_activate(self):
        """Activate the billing schedule"""
        for schedule in self:
            if schedule.state != 'draft':
                raise UserError(_('Only draft schedules can be activated'))
            
            if schedule.subscription_id.state != 'active':
                raise UserError(_('Cannot activate billing for inactive subscription'))
            
            schedule.state = 'active'
            schedule.message_post(body=_('Billing schedule activated'))
    
    def action_pause(self):
        """Pause the billing schedule"""
        for schedule in self:
            if schedule.state != 'active':
                raise UserError(_('Only active schedules can be paused'))
            
            schedule.state = 'paused'
            schedule.message_post(body=_('Billing schedule paused'))
    
    def action_resume(self):
        """Resume the billing schedule"""
        for schedule in self:
            if schedule.state != 'paused':
                raise UserError(_('Only paused schedules can be resumed'))
            
            schedule.state = 'active'
            schedule.message_post(body=_('Billing schedule resumed'))
    
    def action_cancel(self):
        """Cancel the billing schedule"""
        for schedule in self:
            if schedule.state in ['cancelled']:
                raise UserError(_('Schedule is already cancelled'))
            
            schedule.state = 'cancelled'
            schedule.message_post(body=_('Billing schedule cancelled'))
    
    # Core Billing Logic
    def calculate_next_billing_date(self, from_date=None):
        """Calculate the next billing date based on frequency"""
        self.ensure_one()
        
        if not from_date:
            from_date = self.last_billing_date or self.start_date or fields.Date.today()
        
        # Calculate next date based on frequency
        if self.billing_frequency == 'monthly':
            next_date = from_date + relativedelta(months=1)
        elif self.billing_frequency == 'quarterly':
            next_date = from_date + relativedelta(months=3)
        elif self.billing_frequency == 'semi_annual':
            next_date = from_date + relativedelta(months=6)
        elif self.billing_frequency == 'annual':
            next_date = from_date + relativedelta(years=1)
        else:
            next_date = from_date + relativedelta(months=1)
        
        self.next_billing_date = next_date
        return next_date
    
    def is_due_for_billing(self, check_date=None):
        """Check if this schedule is due for billing"""
        self.ensure_one()
        
        if not check_date:
            check_date = fields.Date.today()
        
        return (
            self.state == 'active' and
            self.next_billing_date and
            self.next_billing_date <= check_date
        )
    
    def process_billing(self, billing_date=None):
        """Process billing for this schedule - simplified version"""
        self.ensure_one()
        
        if not billing_date:
            billing_date = fields.Date.today()
        
        if not self.is_due_for_billing(billing_date):
            return {'success': False, 'error': 'Not due for billing'}
        
        _logger.info(f'Processing billing for schedule {self.name}')
        
        try:
            # Create billing event
            billing_event = self._create_billing_event(billing_date)
            
            # Generate invoice if auto_generate is enabled
            invoice = None
            if self.auto_generate_invoice:
                invoice = self._generate_invoice(billing_event)
                
                # Send invoice if auto_send is enabled
                if invoice and self.auto_send_invoice:
                    self._send_invoice(invoice)
            
            # Update billing dates
            self.last_billing_date = billing_date
            self.calculate_next_billing_date(billing_date)
            
            # Mark billing event as completed
            billing_event.state = 'completed'
            
            # Log success
            self.message_post(
                body=_('Billing processed successfully for %s') % billing_date
            )
            
            return {
                'success': True,
                'billing_event': billing_event,
                'invoice': invoice,
            }
            
        except Exception as e:
            _logger.error(f'Error processing billing for schedule {self.name}: {str(e)}')
            
            self.message_post(
                body=_('Billing processing failed: %s') % str(e),
            )
            
            return {
                'success': False,
                'error': str(e),
            }
    
    def _create_billing_event(self, billing_date):
        """Create a billing event record"""
        return self.env['ams.billing.event'].create({
            'billing_schedule_id': self.id,
            'subscription_id': self.subscription_id.id,
            'event_date': billing_date,
            'event_type': 'regular_billing',
            'description': f'Regular billing for {self.billing_frequency} subscription',
            'state': 'pending',
        })
    
    def _generate_invoice(self, billing_event):
        """Generate invoice for billing event"""
        subscription = self.subscription_id
        
        # Calculate billing period
        period_start = billing_event.event_date
        if self.billing_frequency == 'monthly':
            period_end = period_start + relativedelta(months=1) - timedelta(days=1)
        elif self.billing_frequency == 'quarterly':
            period_end = period_start + relativedelta(months=3) - timedelta(days=1)
        elif self.billing_frequency == 'semi_annual':
            period_end = period_start + relativedelta(months=6) - timedelta(days=1)
        elif self.billing_frequency == 'annual':
            period_end = period_start + relativedelta(years=1) - timedelta(days=1)
        else:
            period_end = period_start + relativedelta(months=1) - timedelta(days=1)
        
        # Prepare invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': subscription.partner_id.id,
            'billing_schedule_id': self.id,
            'billing_event_id': billing_event.id,
            'subscription_id': subscription.id,
            'invoice_date': billing_event.event_date,
            'ref': f'Subscription: {subscription.name}',
            'narration': f'Subscription billing for period {period_start} to {period_end}',
        }
        
        # Prepare invoice line
        line_vals = {
            'product_id': subscription.product_id.id,
            'name': f'{subscription.product_id.name} - {period_start} to {period_end}',
            'quantity': subscription.quantity or 1,
            'price_unit': subscription.price,
        }
        
        invoice_vals['invoice_line_ids'] = [(0, 0, line_vals)]
        
        # Create and post invoice
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        # Update billing event
        billing_event.invoice_id = invoice.id
        billing_event.invoice_amount = invoice.amount_total
        
        return invoice
    
    def _send_invoice(self, invoice):
        """Send invoice to customer"""
        try:
            invoice.action_invoice_sent()
            _logger.info(f'Invoice {invoice.name} sent successfully')
        except Exception as e:
            _logger.error(f'Error sending invoice {invoice.name}: {str(e)}')
    
    # Utility Methods
    def action_view_invoices(self):
        """View invoices generated by this schedule"""
        self.ensure_one()
        
        return {
            'name': _('Invoices - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('billing_schedule_id', '=', self.id)],
            'context': {'default_billing_schedule_id': self.id},
        }
    
    def action_view_billing_events(self):
        """View billing events for this schedule"""
        self.ensure_one()
        
        return {
            'name': _('Billing Events - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.event',
            'view_mode': 'list,form',
            'domain': [('billing_schedule_id', '=', self.id)],
            'context': {'default_billing_schedule_id': self.id},
        }
    
    def action_manual_billing(self):
        """Manually trigger billing for this schedule"""
        self.ensure_one()
        
        if self.state != 'active':
            raise UserError(_('Only active schedules can be billed manually'))
        
        result = self.process_billing()
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Billing processed successfully'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Billing failed: %s') % result.get('error', 'Unknown error'),
                    'type': 'danger',
                }
            }
    
    # Batch Processing (Simplified)
    @api.model
    def cron_process_due_billing(self):
        """Simplified cron job to process due billing schedules"""
        today = fields.Date.today()
        
        # Find all schedules due for billing
        due_schedules = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '<=', today)
        ])
        
        _logger.info(f'Found {len(due_schedules)} schedules due for billing')
        
        processed_count = 0
        error_count = 0
        
        for schedule in due_schedules:
            try:
                result = schedule.process_billing(today)
                if result.get('success'):
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f'Error processing schedule {schedule.name}: {str(e)}')
        
        _logger.info(f'Billing processing completed: {processed_count} successful, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'total_due': len(due_schedules),
        }