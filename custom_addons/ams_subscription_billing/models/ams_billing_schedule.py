# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingSchedule(models.Model):
    """Billing Schedule for AMS Subscriptions"""
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
    
    billing_day = fields.Integer(
        string='Billing Day of Month',
        default=1,
        help='Day of month to generate bills (1-28). For frequencies other than monthly, this determines the billing day.'
    )
    
    # Billing Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        help='Leave empty for ongoing billing'
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
    
    # Automation Settings
    auto_invoice = fields.Boolean(
        string='Auto Generate Invoice',
        default=True,
        help='Automatically generate invoices on billing date'
    )
    
    auto_payment = fields.Boolean(
        string='Auto Process Payment',
        default=False,
        help='Automatically attempt payment processing'
    )
    
    auto_send_invoice = fields.Boolean(
        string='Auto Send Invoice',
        default=True,
        help='Automatically send invoice to customer'
    )
    
    # Payment and Terms
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        help='Payment terms for generated invoices'
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Payment Method',
        help='Stored payment method for auto-payment'
    )
    
    # Billing Calendar
    skip_weekends = fields.Boolean(
        string='Skip Weekends',
        default=True,
        help='Move billing to next business day if falls on weekend'
    )
    
    weekend_adjustment = fields.Selection([
        ('before', 'Move to Friday Before'),
        ('after', 'Move to Monday After'),
        ('next_business_day', 'Next Business Day'),
    ], string='Weekend Adjustment', default='next_business_day')
    
    skip_holidays = fields.Boolean(
        string='Skip Holidays',
        default=False,
        help='Move billing if falls on company holidays'
    )
    
    # State and Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Statistics
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
    
    last_invoice_amount = fields.Monetary(
        string='Last Invoice Amount',
        currency_field='currency_id',
        readonly=True
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
    
    # Proration and Adjustments
    enable_proration = fields.Boolean(
        string='Enable Proration',
        default=True,
        help='Enable proration for mid-cycle changes'
    )
    
    proration_method = fields.Selection([
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('none', 'No Proration'),
    ], string='Proration Method', default='daily')
    
    # Notes and Description
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
        """Compute billing statistics"""
        for schedule in self:
            invoices = schedule.invoice_ids.filtered(lambda i: i.state == 'posted')
            schedule.total_invoices = len(invoices)
            schedule.total_billed_amount = sum(invoices.mapped('amount_total'))
    
    # Validation
    @api.constrains('billing_day')
    def _check_billing_day(self):
        """Validate billing day"""
        for schedule in self:
            if not (1 <= schedule.billing_day <= 28):
                raise ValidationError(_('Billing day must be between 1 and 28'))
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate date ranges"""
        for schedule in self:
            if schedule.start_date and schedule.end_date:
                if schedule.end_date <= schedule.start_date:
                    raise ValidationError(_('End date must be after start date'))
    
    @api.constrains('next_billing_date', 'start_date')
    def _check_next_billing_date(self):
        """Validate next billing date"""
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
    
    def write(self, vals):
        """Enhanced write to handle state changes"""
        # Track state changes for notifications
        if 'state' in vals:
            for schedule in self:
                if schedule.state != vals['state']:
                    schedule.message_post(
                        body=_('Billing schedule state changed from %s to %s') % (
                            schedule.state, vals['state']
                        )
                    )
        
        result = super().write(vals)
        
        # Update next billing date if frequency changed
        if 'billing_frequency' in vals or 'billing_day' in vals:
            for schedule in self:
                schedule._calculate_next_billing_date()
        
        return result
    
    # Actions
    def action_activate(self):
        """Activate the billing schedule"""
        for schedule in self:
            if schedule.state != 'draft':
                raise UserError(_('Only draft schedules can be activated'))
            
            # Validate configuration
            if not schedule.subscription_id:
                raise UserError(_('Subscription is required to activate billing schedule'))
            
            if schedule.subscription_id.state != 'active':
                raise UserError(_('Cannot activate billing for inactive subscription'))
            
            # Set next billing date if not set
            if not schedule.next_billing_date:
                schedule._calculate_next_billing_date()
            
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
            if schedule.state in ['cancelled', 'completed']:
                raise UserError(_('Schedule is already cancelled or completed'))
            
            schedule.state = 'cancelled'
            schedule.message_post(body=_('Billing schedule cancelled'))
    
    def action_complete(self):
        """Mark the billing schedule as completed"""
        for schedule in self:
            if schedule.state != 'active':
                raise UserError(_('Only active schedules can be completed'))
            
            schedule.state = 'completed'
            schedule.message_post(body=_('Billing schedule completed'))
    
    # Billing Logic
    def _calculate_next_billing_date(self, from_date=None):
        """Calculate the next billing date based on frequency and settings"""
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
        
        # Adjust for billing day if specified
        if self.billing_day and self.billing_day != from_date.day:
            try:
                next_date = next_date.replace(day=self.billing_day)
            except ValueError:
                # Handle month-end edge cases (e.g., billing day 31 in February)
                next_date = next_date.replace(day=min(self.billing_day, 28))
        
        # Apply calendar adjustments
        next_date = self._adjust_for_calendar(next_date)
        
        self.next_billing_date = next_date
        return next_date
    
    def _adjust_for_calendar(self, target_date):
        """Adjust billing date for weekends and holidays"""
        adjusted_date = target_date
        
        # Handle weekends
        if self.skip_weekends and adjusted_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            if self.weekend_adjustment == 'before':
                # Move to Friday before
                days_to_subtract = adjusted_date.weekday() - 4  # Friday = 4
                adjusted_date = adjusted_date - timedelta(days=days_to_subtract)
            elif self.weekend_adjustment == 'after':
                # Move to Monday after
                days_to_add = 7 - adjusted_date.weekday()
                adjusted_date = adjusted_date + timedelta(days=days_to_add)
            else:  # next_business_day
                # Move to next Monday
                if adjusted_date.weekday() == 5:  # Saturday
                    adjusted_date = adjusted_date + timedelta(days=2)
                elif adjusted_date.weekday() == 6:  # Sunday
                    adjusted_date = adjusted_date + timedelta(days=1)
        
        # Handle holidays (basic implementation - can be enhanced)
        if self.skip_holidays:
            adjusted_date = self._adjust_for_holidays(adjusted_date)
        
        return adjusted_date
    
    def _adjust_for_holidays(self, target_date):
        """Adjust for company holidays - basic implementation"""
        # This is a basic implementation. You could enhance this to:
        # 1. Check against a holiday calendar
        # 2. Use resource.calendar for business days
        # 3. Handle country-specific holidays
        
        # For now, just handle New Year's Day as an example
        if target_date.month == 1 and target_date.day == 1:
            return target_date + timedelta(days=1)
        
        return target_date
    
    def is_due_for_billing(self, check_date=None):
        """Check if this schedule is due for billing"""
        self.ensure_one()
        
        if not check_date:
            check_date = fields.Date.today()
        
        return (
            self.state == 'active' and
            self.next_billing_date and
            self.next_billing_date <= check_date and
            (not self.end_date or check_date <= self.end_date)
        )
    
    def process_billing(self, billing_date=None):
        """Process billing for this schedule"""
        self.ensure_one()
        
        if not billing_date:
            billing_date = fields.Date.today()
        
        if not self.is_due_for_billing(billing_date):
            return False
        
        _logger.info(f'Processing billing for schedule {self.name}')
        
        try:
            # Create billing event
            billing_event = self._create_billing_event(billing_date)
            
            # Generate invoice if auto_invoice is enabled
            invoice = None
            if self.auto_invoice:
                invoice = self._generate_invoice(billing_event)
                
                # Send invoice if auto_send_invoice is enabled
                if invoice and self.auto_send_invoice:
                    self._send_invoice(invoice)
                
                # Process payment if auto_payment is enabled
                if invoice and self.auto_payment and self.payment_method_id:
                    self._process_automatic_payment(invoice)
            
            # Update billing dates
            self.last_billing_date = billing_date
            self._calculate_next_billing_date(billing_date)
            
            # Log success
            self.message_post(
                body=_('Billing processed successfully for %s') % billing_date
            )
            
            return {
                'billing_event': billing_event,
                'invoice': invoice,
                'success': True,
            }
            
        except Exception as e:
            # Log error
            _logger.error(f'Error processing billing for schedule {self.name}: {str(e)}')
            
            self.message_post(
                body=_('Billing processing failed: %s') % str(e),
                message_type='comment'
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
        # This method will be implemented to create the actual invoice
        # For now, return placeholder
        _logger.info(f'Generating invoice for billing event {billing_event.id}')
        
        # Invoice generation logic will be implemented in a separate method
        # that handles all the complexities of subscription billing
        return self.subscription_id._create_billing_invoice(
            billing_date=billing_event.event_date,
            billing_event=billing_event
        )
    
    def _send_invoice(self, invoice):
        """Send invoice to customer"""
        try:
            invoice.action_invoice_sent()
            _logger.info(f'Invoice {invoice.name} sent successfully')
        except Exception as e:
            _logger.error(f'Error sending invoice {invoice.name}: {str(e)}')
    
    def _process_automatic_payment(self, invoice):
        """Process automatic payment for invoice"""
        try:
            # This will integrate with payment processing
            # For now, just log the attempt
            _logger.info(f'Attempting automatic payment for invoice {invoice.name}')
            
            # Payment processing logic will be implemented
            # This would typically:
            # 1. Use the stored payment method
            # 2. Create a payment transaction
            # 3. Handle success/failure
            # 4. Update invoice status
            
        except Exception as e:
            _logger.error(f'Error processing automatic payment for invoice {invoice.name}: {str(e)}')
    
    # Batch Processing
    @api.model
    def cron_process_due_billing(self):
        """Cron job to process due billing schedules"""
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
        
        # Log summary
        _logger.info(f'Billing processing completed: {processed_count} successful, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'total_due': len(due_schedules),
        }
    
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