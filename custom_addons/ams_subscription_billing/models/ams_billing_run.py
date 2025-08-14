# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingRun(models.Model):
    """Billing Run for batch processing multiple billing schedules"""
    _name = 'ams.billing.run'
    _description = 'AMS Billing Run'
    _order = 'run_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Run Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.billing.run') or 'New'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Description of this billing run'
    )
    
    # Run Configuration
    run_date = fields.Date(
        string='Run Date',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True
    )
    
    billing_cutoff_date = fields.Date(
        string='Billing Cutoff Date',
        required=True,
        default=fields.Date.today,
        help='Process schedules due on or before this date'
    )
    
    run_type = fields.Selection([
        ('manual', 'Manual Run'),
        ('scheduled', 'Scheduled Run'),
        ('retry', 'Retry Run'),
        ('test', 'Test Run'),
    ], string='Run Type', default='manual', required=True, tracking=True)
    
    # Filtering Options
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        'ams_billing_run_partner_rel',
        'run_id', 'partner_id',
        string='Specific Customers',
        help='Leave empty to process all customers'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        'ams_billing_run_product_rel',
        'run_id', 'product_id',
        string='Specific Products',
        help='Leave empty to process all products'
    )
    
    subscription_state_filter = fields.Selection([
        ('active', 'Active Only'),
        ('all', 'All States'),
        ('active_grace', 'Active and Grace'),
    ], string='Subscription Filter', default='active')
    
    # Processing Options
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        help='Number of schedules to process in each batch'
    )
    
    auto_invoice = fields.Boolean(
        string='Generate Invoices',
        default=True,
        help='Automatically generate invoices during run'
    )
    
    auto_send_invoice = fields.Boolean(
        string='Send Invoices',
        default=True,
        help='Automatically send invoices to customers'
    )
    
    auto_payment = fields.Boolean(
        string='Process Payments',
        default=False,
        help='Attempt automatic payment processing'
    )
    
    # State and Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Execution Information
    start_time = fields.Datetime(
        string='Start Time',
        readonly=True
    )
    
    end_time = fields.Datetime(
        string='End Time',
        readonly=True
    )
    
    duration = fields.Float(
        string='Duration (minutes)',
        compute='_compute_duration',
        store=True,
        help='Duration of the billing run in minutes'
    )
    
    executed_by = fields.Many2one(
        'res.users',
        string='Executed By',
        readonly=True
    )
    
    # Statistics
    schedules_processed = fields.Integer(
        string='Schedules Processed',
        readonly=True
    )
    
    schedules_found = fields.Integer(
        string='Schedules Found',
        readonly=True
    )
    
    invoices_generated = fields.Integer(
        string='Invoices Generated',
        readonly=True
    )
    
    invoices_sent = fields.Integer(
        string='Invoices Sent',
        readonly=True
    )
    
    payments_processed = fields.Integer(
        string='Payments Processed',
        readonly=True
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        readonly=True,
        help='Total amount of invoices generated'
    )
    
    success_count = fields.Integer(
        string='Successful Processes',
        readonly=True
    )
    
    error_count = fields.Integer(
        string='Failed Processes',
        readonly=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    
    # Related Records
    billing_event_ids = fields.One2many(
        'ams.billing.event',
        'billing_run_id',
        string='Billing Events'
    )
    
    invoice_ids = fields.One2many(
        'account.move',
        'billing_run_id',
        string='Generated Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    error_log_ids = fields.One2many(
        'ams.billing.error',
        'billing_run_id',
        string='Error Log'
    )
    
    # Log and Results
    execution_log = fields.Text(
        string='Execution Log',
        readonly=True
    )
    
    # Computed Fields
    @api.depends('name', 'run_date', 'run_type')
    def _compute_display_name(self):
        """Compute display name for the billing run"""
        for run in self:
            if run.run_date:
                run.display_name = f"{run.name} - {run.run_date} ({run.run_type.title()})"
            else:
                run.display_name = run.name or 'New Billing Run'
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        """Compute duration of the billing run"""
        for run in self:
            if run.start_time and run.end_time:
                delta = run.end_time - run.start_time
                run.duration = delta.total_seconds() / 60.0  # Convert to minutes
            else:
                run.duration = 0.0
    
    # Validation
    @api.constrains('batch_size')
    def _check_batch_size(self):
        """Validate batch size"""
        for run in self:
            if run.batch_size <= 0:
                raise ValidationError(_('Batch size must be greater than zero'))
            if run.batch_size > 1000:
                raise ValidationError(_('Batch size cannot exceed 1000'))
    
    @api.constrains('billing_cutoff_date', 'run_date')
    def _check_dates(self):
        """Validate dates"""
        for run in self:
            if run.billing_cutoff_date and run.run_date:
                if run.billing_cutoff_date > run.run_date:
                    raise ValidationError(_('Billing cutoff date cannot be after run date'))
    
    # Actions
    def action_start_run(self):
        """Start the billing run"""
        for run in self:
            if run.state != 'draft':
                raise UserError(_('Only draft runs can be started'))
            
            run.state = 'running'
            run.start_time = fields.Datetime.now()
            run.executed_by = self.env.user.id
            
            # Process billing in background
            run._process_billing_run()
    
    def action_cancel_run(self):
        """Cancel the billing run"""
        for run in self:
            if run.state not in ['draft', 'running']:
                raise UserError(_('Only draft or running runs can be cancelled'))
            
            run.state = 'cancelled'
            run.end_time = fields.Datetime.now()
            
            run.message_post(body=_('Billing run cancelled'))
    
    def action_retry_failed(self):
        """Retry failed billing processes"""
        self.ensure_one()
        
        if self.state != 'completed':
            raise UserError(_('Only completed runs with errors can be retried'))
        
        if self.error_count == 0:
            raise UserError(_('No failed processes to retry'))
        
        # Create new retry run
        retry_run = self.copy({
            'name': f"{self.name} - Retry",
            'run_type': 'retry',
            'run_date': fields.Date.today(),
            'state': 'draft',
        })
        
        return {
            'name': _('Retry Billing Run'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.run',
            'res_id': retry_run.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # Core Processing Logic
    def _process_billing_run(self):
        """Main billing run processing logic"""
        self.ensure_one()
        
        try:
            # Initialize counters
            self._reset_counters()
            
            # Find schedules to process
            schedules = self._find_schedules_to_process()
            self.schedules_found = len(schedules)
            
            if not schedules:
                self._complete_run_with_message('No billing schedules found to process')
                return
            
            self._log(f'Found {len(schedules)} schedules to process')
            
            # Process schedules in batches
            self._process_schedules_in_batches(schedules)
            
            # Complete the run
            self._complete_run()
            
        except Exception as e:
            self._fail_run(str(e))
            _logger.error(f'Billing run {self.name} failed: {str(e)}')
    
    def _reset_counters(self):
        """Reset all counters for the run"""
        self.write({
            'schedules_processed': 0,
            'schedules_found': 0,
            'invoices_generated': 0,
            'invoices_sent': 0,
            'payments_processed': 0,
            'total_amount': 0,
            'success_count': 0,
            'error_count': 0,
            'execution_log': '',
        })
    
    def _find_schedules_to_process(self):
        """Find billing schedules that should be processed"""
        domain = [
            ('state', '=', 'active'),
            ('next_billing_date', '<=', self.billing_cutoff_date),
            ('company_id', '=', self.company_id.id),
        ]
        
        # Apply subscription state filter
        if self.subscription_state_filter == 'active':
            domain.append(('subscription_id.state', '=', 'active'))
        elif self.subscription_state_filter == 'active_grace':
            domain.append(('subscription_id.state', 'in', ['active', 'grace']))
        
        # Apply partner filter
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        # Apply product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        return self.env['ams.billing.schedule'].search(domain)
    
    def _process_schedules_in_batches(self, schedules):
        """Process schedules in batches"""
        total_schedules = len(schedules)
        batch_count = 0
        
        # Process in batches
        for i in range(0, total_schedules, self.batch_size):
            batch = schedules[i:i + self.batch_size]
            batch_count += 1
            
            self._log(f'Processing batch {batch_count}: schedules {i+1}-{min(i+self.batch_size, total_schedules)}')
            
            self._process_batch(batch)
            
            # Commit after each batch to avoid long transactions
            self.env.cr.commit()
    
    def _process_batch(self, schedules):
        """Process a batch of schedules"""
        for schedule in schedules:
            try:
                result = self._process_single_schedule(schedule)
                self._update_counters_for_success(result)
                
            except Exception as e:
                self._handle_processing_error(schedule, str(e))
    
    def _process_single_schedule(self, schedule):
        """Process a single billing schedule"""
        # Create billing event
        billing_event = self.env['ams.billing.event'].create({
            'billing_schedule_id': schedule.id,
            'subscription_id': schedule.subscription_id.id,
            'billing_run_id': self.id,
            'event_date': self.run_date,
            'event_type': 'batch_billing',
            'description': f'Batch billing run: {self.name}',
            'state': 'pending',
        })
        
        result = {
            'billing_event': billing_event,
            'invoice': None,
            'payment': None,
            'success': True,
        }
        
        # Generate invoice if enabled
        if self.auto_invoice:
            invoice = schedule._generate_invoice(billing_event)
            result['invoice'] = invoice
            
            if invoice:
                # Send invoice if enabled
                if self.auto_send_invoice:
                    try:
                        schedule._send_invoice(invoice)
                        result['invoice_sent'] = True
                    except Exception as e:
                        self._log(f'Failed to send invoice {invoice.name}: {str(e)}')
                
                # Process payment if enabled
                if self.auto_payment and schedule.payment_method_id:
                    try:
                        payment_result = schedule._process_automatic_payment(invoice)
                        result['payment'] = payment_result
                    except Exception as e:
                        self._log(f'Failed to process payment for invoice {invoice.name}: {str(e)}')
        
        # Update schedule billing dates
        schedule.last_billing_date = self.run_date
        schedule._calculate_next_billing_date(self.run_date)
        
        # Mark billing event as completed
        billing_event.state = 'completed'
        
        return result
    
    def _update_counters_for_success(self, result):
        """Update counters for successful processing"""
        self.schedules_processed += 1
        self.success_count += 1
        
        if result.get('invoice'):
            self.invoices_generated += 1
            self.total_amount += result['invoice'].amount_total
            
            if result.get('invoice_sent'):
                self.invoices_sent += 1
        
        if result.get('payment'):
            self.payments_processed += 1
    
    def _handle_processing_error(self, schedule, error_message):
        """Handle processing error for a schedule"""
        self.error_count += 1
        
        # Create error log
        self.env['ams.billing.error'].create({
            'billing_run_id': self.id,
            'billing_schedule_id': schedule.id,
            'subscription_id': schedule.subscription_id.id,
            'error_type': 'processing_error',
            'error_message': error_message,
            'error_date': fields.Datetime.now(),
        })
        
        self._log(f'Error processing schedule {schedule.name}: {error_message}')
    
    def _complete_run(self):
        """Complete the billing run"""
        self.state = 'completed'
        self.end_time = fields.Datetime.now()
        
        summary = (
            f'Billing run completed:\n'
            f'- Schedules found: {self.schedules_found}\n'
            f'- Schedules processed: {self.schedules_processed}\n'
            f'- Invoices generated: {self.invoices_generated}\n'
            f'- Invoices sent: {self.invoices_sent}\n'
            f'- Payments processed: {self.payments_processed}\n'
            f'- Total amount: {self.total_amount}\n'
            f'- Successful: {self.success_count}\n'
            f'- Errors: {self.error_count}\n'
            f'- Duration: {self.duration:.2f} minutes'
        )
        
        self._log(summary)
        self.message_post(body=summary)
    
    def _complete_run_with_message(self, message):
        """Complete run with a specific message"""
        self.state = 'completed'
        self.end_time = fields.Datetime.now()
        self._log(message)
        self.message_post(body=message)
    
    def _fail_run(self, error_message):
        """Mark run as failed"""
        self.state = 'failed'
        self.end_time = fields.Datetime.now()
        self._log(f'Run failed: {error_message}')
        self.message_post(body=f'Billing run failed: {error_message}')
    
    def _log(self, message):
        """Add message to execution log"""
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f'[{timestamp}] {message}'
        
        if self.execution_log:
            self.execution_log += f'\n{log_entry}'
        else:
            self.execution_log = log_entry
    
    # View Actions
    def action_view_invoices(self):
        """View invoices generated by this run"""
        self.ensure_one()
        
        return {
            'name': _('Invoices - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('billing_run_id', '=', self.id)],
            'context': {'default_billing_run_id': self.id},
        }
    
    def action_view_billing_events(self):
        """View billing events from this run"""
        self.ensure_one()
        
        return {
            'name': _('Billing Events - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.event',
            'view_mode': 'list,form',
            'domain': [('billing_run_id', '=', self.id)],
            'context': {'default_billing_run_id': self.id},
        }
    
    def action_view_errors(self):
        """View errors from this run"""
        self.ensure_one()
        
        return {
            'name': _('Errors - %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.error',
            'view_mode': 'list,form',
            'domain': [('billing_run_id', '=', self.id)],
            'context': {'default_billing_run_id': self.id},
        }
    
    # Reporting
    def get_run_summary(self):
        """Get summary of billing run results"""
        self.ensure_one()
        
        return {
            'run_id': self.id,
            'run_name': self.name,
            'run_date': self.run_date,
            'state': self.state,
            'duration': self.duration,
            'schedules_found': self.schedules_found,
            'schedules_processed': self.schedules_processed,
            'invoices_generated': self.invoices_generated,
            'invoices_sent': self.invoices_sent,
            'payments_processed': self.payments_processed,
            'total_amount': self.total_amount,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / max(self.schedules_processed, 1)) * 100,
        }


class AMSBillingError(models.Model):
    """Billing Error Log"""
    _name = 'ams.billing.error'
    _description = 'AMS Billing Error Log'
    _order = 'error_date desc'
    
    billing_run_id = fields.Many2one(
        'ams.billing.run',
        string='Billing Run',
        ondelete='cascade',
        index=True
    )
    
    billing_schedule_id = fields.Many2one(
        'ams.billing.schedule',
        string='Billing Schedule',
        ondelete='cascade'
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        ondelete='cascade'
    )
    
    error_type = fields.Selection([
        ('processing_error', 'Processing Error'),
        ('invoice_error', 'Invoice Generation Error'),
        ('payment_error', 'Payment Processing Error'),
        ('email_error', 'Email Sending Error'),
        ('validation_error', 'Validation Error'),
    ], string='Error Type', required=True)
    
    error_message = fields.Text(
        string='Error Message',
        required=True
    )
    
    error_date = fields.Datetime(
        string='Error Date',
        required=True,
        default=fields.Datetime.now
    )
    
    resolved = fields.Boolean(
        string='Resolved',
        default=False
    )
    
    resolution_notes = fields.Text(
        string='Resolution Notes'
    )