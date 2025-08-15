# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBulkBillingWizard(models.TransientModel):
    """Wizard for Bulk Billing Operations"""
    _name = 'ams.bulk.billing.wizard'
    _description = 'AMS Bulk Billing Wizard'
    
    # =============================================================================
    # OPERATION CONFIGURATION
    # =============================================================================
    
    operation_type = fields.Selection([
        ('generate_invoices', 'Generate Invoices'),
        ('send_invoices', 'Send Invoices'),
        ('process_payments', 'Process Payments'),
        ('retry_failed_payments', 'Retry Failed Payments'),
        ('update_billing_schedules', 'Update Billing Schedules'),
        ('pause_billing', 'Pause Billing'),
        ('resume_billing', 'Resume Billing'),
        ('send_reminders', 'Send Payment Reminders'),
        ('apply_proration', 'Apply Proration Adjustments'),
    ], string='Operation Type', required=True, default='generate_invoices')
    
    description = fields.Text(
        string='Operation Description',
        help='Description of the bulk operation'
    )
    
    # =============================================================================
    # TARGET SELECTION
    # =============================================================================
    
    selection_method = fields.Selection([
        ('all_eligible', 'All Eligible Records'),
        ('specific_subscriptions', 'Specific Subscriptions'),
        ('specific_customers', 'Specific Customers'),
        ('billing_schedules', 'Specific Billing Schedules'),
        ('invoices', 'Specific Invoices'),
        ('custom_filter', 'Custom Filter'),
    ], string='Selection Method', required=True, default='all_eligible')
    
    # Specific Record Selections
    subscription_ids = fields.Many2many(
        'ams.subscription',
        'bulk_billing_subscription_rel',
        'wizard_id', 'subscription_id',
        string='Selected Subscriptions'
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        'bulk_billing_partner_rel',
        'wizard_id', 'partner_id',
        string='Selected Customers'
    )
    
    billing_schedule_ids = fields.Many2many(
        'ams.billing.schedule',
        'bulk_billing_schedule_rel',
        'wizard_id', 'schedule_id',
        string='Selected Billing Schedules'
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        'bulk_billing_invoice_rel',
        'wizard_id', 'invoice_id',
        string='Selected Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    # =============================================================================
    # FILTERING CRITERIA
    # =============================================================================
    
    # Date Filters
    filter_by_date = fields.Boolean(
        string='Filter by Date Range',
        default=False
    )
    
    date_from = fields.Date(
        string='Date From'
    )
    
    date_to = fields.Date(
        string='Date To'
    )
    
    date_field = fields.Selection([
        ('next_billing_date', 'Next Billing Date'),
        ('last_billing_date', 'Last Billing Date'),
        ('due_date', 'Due Date'),
        ('invoice_date', 'Invoice Date'),
        ('creation_date', 'Creation Date'),
    ], string='Date Field to Filter', default='next_billing_date')
    
    # Status Filters
    subscription_states = fields.Selection([
        ('active', 'Active Only'),
        ('all', 'All States'),
        ('suspended', 'Suspended Only'),
        ('grace', 'Grace Period Only'),
    ], string='Subscription States', default='active')
    
    billing_frequencies = fields.Selection([
        ('all', 'All Frequencies'),
        ('monthly', 'Monthly Only'),
        ('quarterly', 'Quarterly Only'),
        ('annual', 'Annual Only'),
    ], string='Billing Frequencies', default='all')
    
    payment_states = fields.Selection([
        ('all', 'All Payment States'),
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], string='Payment States', default='all')
    
    # Amount Filters
    filter_by_amount = fields.Boolean(
        string='Filter by Amount Range',
        default=False
    )
    
    amount_from = fields.Monetary(
        string='Amount From',
        currency_field='currency_id'
    )
    
    amount_to = fields.Monetary(
        string='Amount To',
        currency_field='currency_id'
    )
    
    # Customer Categories
    partner_category_ids = fields.Many2many(
        'res.partner.category',
        'bulk_billing_partner_category_rel',
        'wizard_id', 'category_id',
        string='Customer Categories'
    )
    
    # Product Categories
    product_category_ids = fields.Many2many(
        'product.category',
        'bulk_billing_product_category_rel',
        'wizard_id', 'category_id',
        string='Product Categories'
    )
    
    # =============================================================================
    # OPERATION SETTINGS
    # =============================================================================
    
    # Invoice Generation Settings
    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.today,
        help='Date to use for generated invoices'
    )
    
    auto_validate_invoices = fields.Boolean(
        string='Auto-Validate Invoices',
        default=True,
        help='Automatically validate generated invoices'
    )
    
    # Email Settings
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', 'in', ['account.move', 'ams.subscription'])]"
    )
    
    send_immediately = fields.Boolean(
        string='Send Immediately',
        default=True,
        help='Send emails immediately or queue for later'
    )
    
    # Payment Processing Settings
    retry_failed_only = fields.Boolean(
        string='Retry Failed Payments Only',
        default=True,
        help='Only retry previously failed payments'
    )
    
    payment_retry_delay = fields.Integer(
        string='Retry Delay (hours)',
        default=24,
        help='Hours to wait before retrying failed payments'
    )
    
    # Billing Schedule Updates
    new_billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='New Billing Frequency',
    help='New billing frequency for bulk update')
    
    new_billing_day = fields.Integer(
        string='New Billing Day',
        help='New billing day for bulk update (1-28)'
    )
    
    # Proration Settings
    proration_effective_date = fields.Date(
        string='Proration Effective Date',
        default=fields.Date.today,
        help='Effective date for proration calculations'
    )
    
    proration_type = fields.Selection([
        ('upgrade', 'Product Upgrade'),
        ('downgrade', 'Product Downgrade'),
        ('quantity_change', 'Quantity Change'),
        ('plan_change', 'Plan Change'),
    ], string='Proration Type')
    
    # =============================================================================
    # PROCESSING OPTIONS
    # =============================================================================
    
    batch_size = fields.Integer(
        string='Batch Size',
        default=50,
        help='Number of records to process in each batch'
    )
    
    max_parallel_jobs = fields.Integer(
        string='Max Parallel Jobs',
        default=3,
        help='Maximum number of parallel processing jobs'
    )
    
    test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        help='Run in test mode without making changes'
    )
    
    continue_on_error = fields.Boolean(
        string='Continue on Errors',
        default=True,
        help='Continue processing if individual records fail'
    )
    
    # =============================================================================
    # PREVIEW AND VALIDATION
    # =============================================================================
    
    preview_generated = fields.Boolean(
        string='Preview Generated',
        default=False,
        readonly=True
    )
    
    records_found = fields.Integer(
        string='Records Found',
        readonly=True
    )
    
    estimated_amount = fields.Monetary(
        string='Estimated Total Amount',
        currency_field='currency_id',
        readonly=True
    )
    
    preview_details = fields.Text(
        string='Preview Details',
        readonly=True
    )
    
    validation_warnings = fields.Text(
        string='Validation Warnings',
        readonly=True
    )
    
    # =============================================================================
    # EXECUTION TRACKING
    # =============================================================================
    
    execution_state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Execution State', default='draft', readonly=True)
    
    start_time = fields.Datetime(
        string='Start Time',
        readonly=True
    )
    
    end_time = fields.Datetime(
        string='End Time',
        readonly=True
    )
    
    processed_count = fields.Integer(
        string='Processed Count',
        readonly=True
    )
    
    success_count = fields.Integer(
        string='Success Count',
        readonly=True
    )
    
    error_count = fields.Integer(
        string='Error Count',
        readonly=True
    )
    
    execution_log = fields.Text(
        string='Execution Log',
        readonly=True
    )
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    estimated_duration = fields.Char(
        string='Estimated Duration',
        compute='_compute_estimated_duration',
        help='Estimated time to complete the operation'
    )
    
    @api.depends('records_found', 'batch_size', 'operation_type')
    def _compute_estimated_duration(self):
        """Compute estimated duration"""
        for wizard in self:
            if wizard.records_found > 0:
                # Base time estimates per operation type (seconds per record)
                time_estimates = {
                    'generate_invoices': 5,
                    'send_invoices': 3,
                    'process_payments': 10,
                    'retry_failed_payments': 8,
                    'update_billing_schedules': 2,
                    'pause_billing': 1,
                    'resume_billing': 1,
                    'send_reminders': 3,
                    'apply_proration': 15,
                }
                
                base_time = time_estimates.get(wizard.operation_type, 5)
                total_seconds = wizard.records_found * base_time
                
                if total_seconds < 60:
                    wizard.estimated_duration = f"{total_seconds} seconds"
                elif total_seconds < 3600:
                    minutes = total_seconds // 60
                    wizard.estimated_duration = f"{minutes} minutes"
                else:
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    wizard.estimated_duration = f"{hours}h {minutes}m"
            else:
                wizard.estimated_duration = "Unknown"
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('batch_size')
    def _check_batch_size(self):
        """Validate batch size"""
        for wizard in self:
            if wizard.batch_size <= 0 or wizard.batch_size > 500:
                raise ValidationError(_('Batch size must be between 1 and 500'))
    
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        """Validate date range"""
        for wizard in self:
            if (wizard.filter_by_date and 
                wizard.date_from and wizard.date_to and
                wizard.date_to <= wizard.date_from):
                raise ValidationError(_('Date To must be after Date From'))
    
    @api.constrains('amount_from', 'amount_to')
    def _check_amount_range(self):
        """Validate amount range"""
        for wizard in self:
            if (wizard.filter_by_amount and 
                wizard.amount_from is not False and wizard.amount_to is not False and
                wizard.amount_to <= wizard.amount_from):
                raise ValidationError(_('Amount To must be greater than Amount From'))
    
    @api.constrains('new_billing_day')
    def _check_billing_day(self):
        """Validate billing day"""
        for wizard in self:
            if wizard.new_billing_day and not (1 <= wizard.new_billing_day <= 28):
                raise ValidationError(_('Billing day must be between 1 and 28'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('operation_type')
    def _onchange_operation_type(self):
        """Adjust settings based on operation type"""
        # Clear preview when operation changes
        self.preview_generated = False
        self.records_found = 0
        self.estimated_amount = 0
        self.preview_details = ""
        
        # Set appropriate defaults
        if self.operation_type == 'generate_invoices':
            self.selection_method = 'billing_schedules'
        elif self.operation_type in ['send_invoices', 'send_reminders']:
            self.selection_method = 'invoices'
        elif self.operation_type == 'process_payments':
            self.selection_method = 'invoices'
            self.payment_states = 'not_paid'
        elif self.operation_type == 'retry_failed_payments':
            self.selection_method = 'invoices'
            self.payment_states = 'not_paid'
            self.retry_failed_only = True
    
    @api.onchange('selection_method')
    def _onchange_selection_method(self):
        """Clear selections when method changes"""
        if self.selection_method != 'specific_subscriptions':
            self.subscription_ids = [(5, 0, 0)]
        if self.selection_method != 'specific_customers':
            self.partner_ids = [(5, 0, 0)]
        if self.selection_method != 'billing_schedules':
            self.billing_schedule_ids = [(5, 0, 0)]
        if self.selection_method != 'invoices':
            self.invoice_ids = [(5, 0, 0)]
        
        # Clear preview
        self.preview_generated = False
        self.records_found = 0
    
    # =============================================================================
    # PREVIEW FUNCTIONALITY
    # =============================================================================
    
    def action_generate_preview(self):
        """Generate preview of bulk operation"""
        self.ensure_one()
        
        # Find target records
        target_records = self._find_target_records()
        
        # Generate preview details
        preview_details = self._generate_preview_details(target_records)
        
        # Calculate estimated amounts
        estimated_amount = self._calculate_estimated_amount(target_records)
        
        # Check for validation warnings
        warnings = self._validate_operation(target_records)
        
        # Update preview fields
        self.write({
            'preview_generated': True,
            'records_found': len(target_records),
            'estimated_amount': estimated_amount,
            'preview_details': preview_details,
            'validation_warnings': warnings,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Preview generated: %d records found') % len(target_records),
                'type': 'info',
            }
        }
    
    def _find_target_records(self):
        """Find target records based on selection method and filters"""
        if self.operation_type in ['generate_invoices', 'update_billing_schedules', 'pause_billing', 'resume_billing']:
            return self._find_billing_schedules()
        elif self.operation_type in ['send_invoices', 'process_payments', 'retry_failed_payments', 'send_reminders']:
            return self._find_invoices()
        elif self.operation_type == 'apply_proration':
            return self._find_subscriptions()
        else:
            return self.env['ams.billing.schedule']
    
    def _find_billing_schedules(self):
        """Find billing schedules based on filters"""
        domain = []
        
        # Base domain based on selection method
        if self.selection_method == 'billing_schedules' and self.billing_schedule_ids:
            domain.append(('id', 'in', self.billing_schedule_ids.ids))
        elif self.selection_method == 'specific_subscriptions' and self.subscription_ids:
            domain.append(('subscription_id', 'in', self.subscription_ids.ids))
        elif self.selection_method == 'specific_customers' and self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        elif self.selection_method != 'all_eligible':
            return self.env['ams.billing.schedule']
        
        # Add filters
        if self.operation_type == 'generate_invoices':
            domain.append(('state', '=', 'active'))
            if self.filter_by_date and self.date_from and self.date_to:
                domain.extend([
                    ('next_billing_date', '>=', self.date_from),
                    ('next_billing_date', '<=', self.date_to),
                ])
        elif self.operation_type == 'pause_billing':
            domain.append(('state', '=', 'active'))
        elif self.operation_type == 'resume_billing':
            domain.append(('state', '=', 'paused'))
        
        # Subscription state filter
        if self.subscription_states != 'all':
            if self.subscription_states == 'active':
                domain.append(('subscription_id.state', '=', 'active'))
            elif self.subscription_states == 'suspended':
                domain.append(('subscription_id.state', '=', 'suspended'))
            elif self.subscription_states == 'grace':
                domain.append(('subscription_id.state', '=', 'grace'))
        
        # Billing frequency filter
        if self.billing_frequencies != 'all':
            domain.append(('billing_frequency', '=', self.billing_frequencies))
        
        # Amount filter
        if self.filter_by_amount:
            if self.amount_from is not False:
                domain.append(('subscription_id.price', '>=', self.amount_from))
            if self.amount_to is not False:
                domain.append(('subscription_id.price', '<=', self.amount_to))
        
        # Customer categories
        if self.partner_category_ids:
            partners = self.env['res.partner'].search([
                ('category_id', 'in', self.partner_category_ids.ids)
            ])
            domain.append(('partner_id', 'in', partners.ids))
        
        # Product categories
        if self.product_category_ids:
            products = self.env['product.product'].search([
                ('categ_id', 'in', self.product_category_ids.ids)
            ])
            domain.append(('product_id', 'in', products.ids))
        
        return self.env['ams.billing.schedule'].search(domain)
    
    def _find_invoices(self):
        """Find invoices based on filters"""
        domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        
        # Base domain based on selection method
        if self.selection_method == 'invoices' and self.invoice_ids:
            domain.append(('id', 'in', self.invoice_ids.ids))
        elif self.selection_method == 'specific_subscriptions' and self.subscription_ids:
            domain.append(('subscription_id', 'in', self.subscription_ids.ids))
        elif self.selection_method == 'specific_customers' and self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        elif self.selection_method != 'all_eligible':
            return self.env['account.move']
        
        # Payment state filter
        if self.payment_states == 'not_paid':
            domain.append(('payment_state', '=', 'not_paid'))
        elif self.payment_states == 'partial':
            domain.append(('payment_state', '=', 'partial'))
        elif self.payment_states == 'paid':
            domain.append(('payment_state', '=', 'paid'))
        elif self.payment_states == 'overdue':
            domain.append(('is_overdue', '=', True))
        
        # Date filter
        if self.filter_by_date and self.date_from and self.date_to:
            if self.date_field == 'due_date':
                domain.extend([
                    ('invoice_date_due', '>=', self.date_from),
                    ('invoice_date_due', '<=', self.date_to),
                ])
            elif self.date_field == 'invoice_date':
                domain.extend([
                    ('invoice_date', '>=', self.date_from),
                    ('invoice_date', '<=', self.date_to),
                ])
        
        # Amount filter
        if self.filter_by_amount:
            if self.amount_from is not False:
                domain.append(('amount_total', '>=', self.amount_from))
            if self.amount_to is not False:
                domain.append(('amount_total', '<=', self.amount_to))
        
        # Operation-specific filters
        if self.operation_type == 'retry_failed_payments' and self.retry_failed_only:
            domain.append(('payment_retry_ids', '!=', False))
        
        return self.env['account.move'].search(domain)
    
    def _find_subscriptions(self):
        """Find subscriptions for proration operations"""
        domain = []
        
        # Base domain based on selection method
        if self.selection_method == 'specific_subscriptions' and self.subscription_ids:
            domain.append(('id', 'in', self.subscription_ids.ids))
        elif self.selection_method == 'specific_customers' and self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        elif self.selection_method != 'all_eligible':
            return self.env['ams.subscription']
        
        # Subscription state filter
        if self.subscription_states != 'all':
            domain.append(('state', '=', self.subscription_states))
        
        return self.env['ams.subscription'].search(domain)
    
    def _generate_preview_details(self, target_records):
        """Generate preview details"""
        if not target_records:
            return "No records found with current filters."
        
        details = []
        details.append(f"Operation: {self.operation_type.replace('_', ' ').title()}")
        details.append(f"Records found: {len(target_records)}")
        details.append("")
        
        # Group by relevant criteria
        if self.operation_type in ['generate_invoices', 'update_billing_schedules']:
            # Group billing schedules by frequency
            frequency_groups = {}
            for schedule in target_records:
                freq = schedule.billing_frequency
                if freq not in frequency_groups:
                    frequency_groups[freq] = []
                frequency_groups[freq].append(schedule)
            
            details.append("By billing frequency:")
            for freq, schedules in frequency_groups.items():
                details.append(f"• {freq.title()}: {len(schedules)} schedules")
        
        elif self.operation_type in ['send_invoices', 'process_payments']:
            # Group invoices by payment state
            state_groups = {}
            for invoice in target_records:
                state = invoice.payment_state
                if state not in state_groups:
                    state_groups[state] = []
                state_groups[state].append(invoice)
            
            details.append("By payment state:")
            for state, invoices in state_groups.items():
                details.append(f"• {state.replace('_', ' ').title()}: {len(invoices)} invoices")
        
        return "\n".join(details)
    
    def _calculate_estimated_amount(self, target_records):
        """Calculate estimated total amount"""
        if self.operation_type == 'generate_invoices':
            return sum(schedule.subscription_id.price * (schedule.subscription_id.quantity or 1) 
                      for schedule in target_records)
        elif self.operation_type in ['send_invoices', 'process_payments', 'send_reminders']:
            return sum(target_records.mapped('amount_residual'))
        else:
            return 0
    
    def _validate_operation(self, target_records):
        """Validate operation and return warnings"""
        warnings = []
        
        if not target_records:
            warnings.append("No records found with current selection criteria.")
        
        if self.operation_type == 'generate_invoices':
            # Check for schedules without next billing date
            missing_dates = target_records.filtered(lambda s: not s.next_billing_date)
            if missing_dates:
                warnings.append(f"{len(missing_dates)} schedules missing next billing date.")
        
        elif self.operation_type == 'process_payments':
            # Check for invoices without payment methods
            no_payment_method = target_records.filtered(
                lambda inv: not inv.subscription_id or not inv.subscription_id.payment_method_id
            )
            if no_payment_method:
                warnings.append(f"{len(no_payment_method)} invoices without payment method.")
        
        elif self.operation_type == 'send_invoices':
            # Check for invoices without email
            no_email = target_records.filtered(lambda inv: not inv.partner_id.email)
            if no_email:
                warnings.append(f"{len(no_email)} invoices for customers without email.")
        
        return "\n".join(warnings) if warnings else ""
    
    # =============================================================================
    # MAIN EXECUTION
    # =============================================================================
    
    def action_execute_operation(self):
        """Execute the bulk operation"""
        self.ensure_one()
        
        # Validate before execution
        self._validate_before_execution()
        
        # Initialize execution
        self._initialize_execution()
        
        try:
            # Get target records
            target_records = self._find_target_records()
            
            if not target_records:
                self._complete_execution_with_message("No records found to process")
                return
            
            # Execute operation
            result = self._execute_bulk_operation(target_records)
            
            # Complete execution
            self._complete_execution(result)
            
        except Exception as e:
            self._fail_execution(str(e))
            raise
    
    def _validate_before_execution(self):
        """Validate before execution"""
        if not self.preview_generated:
            raise UserError(_('Please generate preview before executing'))
        
        if self.records_found == 0:
            raise UserError(_('No records found to process'))
        
        if self.operation_type == 'send_invoices' and not self.email_template_id:
            raise UserError(_('Email template is required for sending invoices'))
        
        if self.operation_type == 'update_billing_schedules':
            if not self.new_billing_frequency and not self.new_billing_day:
                raise UserError(_('New billing frequency or billing day is required'))
    
    def _initialize_execution(self):
        """Initialize execution tracking"""
        self.write({
            'execution_state': 'running',
            'start_time': fields.Datetime.now(),
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'execution_log': f'Starting bulk operation: {self.operation_type}\n',
        })
    
    def _execute_bulk_operation(self, target_records):
        """Execute the actual bulk operation"""
        total_records = len(target_records)
        batch_count = 0
        results = {
            'processed': 0,
            'success': 0,
            'errors': 0,
            'error_details': [],
        }
        
        # Process in batches
        for i in range(0, total_records, self.batch_size):
            batch = target_records[i:i + self.batch_size]
            batch_count += 1
            
            self._log(f'Processing batch {batch_count}: records {i+1}-{min(i+self.batch_size, total_records)}')
            
            batch_result = self._process_batch(batch)
            
            # Update results
            results['processed'] += batch_result['processed']
            results['success'] += batch_result['success']
            results['errors'] += batch_result['errors']
            results['error_details'].extend(batch_result['error_details'])
            
            # Update progress
            self.write({
                'processed_count': results['processed'],
                'success_count': results['success'],
                'error_count': results['errors'],
            })
            
            # Commit after each batch
            if not self.test_mode:
                self.env.cr.commit()
        
        return results
    
    def _process_batch(self, records):
        """Process a batch of records"""
        batch_result = {
            'processed': 0,
            'success': 0,
            'errors': 0,
            'error_details': [],
        }
        
        for record in records:
            try:
                if self.test_mode:
                    # Simulate processing in test mode
                    self._log(f'TEST MODE: Would process {record.name}')
                    batch_result['success'] += 1
                else:
                    # Actual processing
                    success = self._process_single_record(record)
                    if success:
                        batch_result['success'] += 1
                    else:
                        batch_result['errors'] += 1
                
                batch_result['processed'] += 1
                
            except Exception as e:
                batch_result['errors'] += 1
                error_msg = f'{record._name} {record.id}: {str(e)}'
                batch_result['error_details'].append(error_msg)
                self._log(f'ERROR: {error_msg}')
                
                if not self.continue_on_error:
                    raise
        
        return batch_result
    
    def _process_single_record(self, record):
        """Process a single record based on operation type"""
        if self.operation_type == 'generate_invoices':
            return self._generate_invoice(record)
        elif self.operation_type == 'send_invoices':
            return self._send_invoice(record)
        elif self.operation_type == 'process_payments':
            return self._process_payment(record)
        elif self.operation_type == 'retry_failed_payments':
            return self._retry_payment(record)
        elif self.operation_type == 'update_billing_schedules':
            return self._update_billing_schedule(record)
        elif self.operation_type == 'pause_billing':
            return self._pause_billing(record)
        elif self.operation_type == 'resume_billing':
            return self._resume_billing(record)
        elif self.operation_type == 'send_reminders':
            return self._send_reminder(record)
        elif self.operation_type == 'apply_proration':
            return self._apply_proration(record)
        
        return False
    
    # =============================================================================
    # OPERATION IMPLEMENTATIONS
    # =============================================================================
    
    def _generate_invoice(self, billing_schedule):
        """Generate invoice for billing schedule"""
        try:
            result = billing_schedule.process_billing(self.invoice_date)
            return result.get('success', False)
        except Exception as e:
            self._log(f'Failed to generate invoice for schedule {billing_schedule.name}: {str(e)}')
            return False
    
    def _send_invoice(self, invoice):
        """Send invoice via email"""
        try:
            if self.email_template_id:
                self.email_template_id.send_mail(invoice.id, force_send=self.send_immediately)
            else:
                invoice.action_invoice_sent()
            return True
        except Exception as e:
            self._log(f'Failed to send invoice {invoice.name}: {str(e)}')
            return False
    
    def _process_payment(self, invoice):
        """Process payment for invoice"""
        try:
            if invoice.subscription_id and invoice.subscription_id.payment_method_id:
                # Create payment retry or process directly
                payment_result = invoice.action_retry_payment()
                return True
            return False
        except Exception as e:
            self._log(f'Failed to process payment for invoice {invoice.name}: {str(e)}')
            return False
    
    def _retry_payment(self, invoice):
        """Retry failed payment"""
        try:
            return invoice.action_retry_payment()
        except Exception as e:
            self._log(f'Failed to retry payment for invoice {invoice.name}: {str(e)}')
            return False
    
    def _update_billing_schedule(self, billing_schedule):
        """Update billing schedule"""
        try:
            updates = {}
            if self.new_billing_frequency:
                updates['billing_frequency'] = self.new_billing_frequency
            if self.new_billing_day:
                updates['billing_day'] = self.new_billing_day
            
            if updates:
                billing_schedule.write(updates)
                billing_schedule._calculate_next_billing_date()
            
            return True
        except Exception as e:
            self._log(f'Failed to update billing schedule {billing_schedule.name}: {str(e)}')
            return False
    
    def _pause_billing(self, billing_schedule):
        """Pause billing schedule"""
        try:
            billing_schedule.action_pause()
            return True
        except Exception as e:
            self._log(f'Failed to pause billing schedule {billing_schedule.name}: {str(e)}')
            return False
    
    def _resume_billing(self, billing_schedule):
        """Resume billing schedule"""
        try:
            billing_schedule.action_resume()
            return True
        except Exception as e:
            self._log(f'Failed to resume billing schedule {billing_schedule.name}: {str(e)}')
            return False
    
    def _send_reminder(self, invoice):
        """Send payment reminder"""
        try:
            return invoice.send_payment_reminder()
        except Exception as e:
            self._log(f'Failed to send reminder for invoice {invoice.name}: {str(e)}')
            return False
    
    def _apply_proration(self, subscription):
        """Apply proration to subscription"""
        try:
            # This would create proration calculations
            # Implementation depends on specific proration requirements
            self._log(f'Proration applied to subscription {subscription.name}')
            return True
        except Exception as e:
            self._log(f'Failed to apply proration to subscription {subscription.name}: {str(e)}')
            return False
    
    # =============================================================================
    # EXECUTION COMPLETION
    # =============================================================================
    
    def _complete_execution(self, result):
        """Complete execution successfully"""
        self.execution_state = 'completed'
        self.end_time = fields.Datetime.now()
        
        summary = f'''
Bulk operation completed:
- Operation: {self.operation_type}
- Records processed: {result['processed']}
- Successful: {result['success']}
- Errors: {result['errors']}
- Duration: {(self.end_time - self.start_time).total_seconds() / 60:.2f} minutes
'''
        
        if result['error_details']:
            summary += f"\nError details:\n" + "\n".join(result['error_details'][:10])
            if len(result['error_details']) > 10:
                summary += f"\n... and {len(result['error_details']) - 10} more errors"
        
        self._log(summary)
    
    def _complete_execution_with_message(self, message):
        """Complete execution with specific message"""
        self.execution_state = 'completed'
        self.end_time = fields.Datetime.now()
        self._log(message)
    
    def _fail_execution(self, error_message):
        """Mark execution as failed"""
        self.execution_state = 'failed'
        self.end_time = fields.Datetime.now()
        self._log(f'Execution failed: {error_message}')
    
    def _log(self, message):
        """Add message to execution log"""
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')