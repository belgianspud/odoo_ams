# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSBillingRunWizard(models.TransientModel):
    """Wizard for Creating and Configuring Billing Runs"""
    _name = 'ams.billing.run.wizard'
    _description = 'AMS Billing Run Wizard'
    
    # =============================================================================
    # BASIC CONFIGURATION
    # =============================================================================
    
    name = fields.Char(
        string='Run Name',
        required=True,
        default=lambda self: self._get_default_run_name()
    )
    
    description = fields.Text(
        string='Description',
        help='Description of this billing run'
    )
    
    run_type = fields.Selection([
        ('manual', 'Manual Run'),
        ('scheduled', 'Scheduled Run'),
        ('retry', 'Retry Failed'),
        ('test', 'Test Run'),
        ('emergency', 'Emergency Run'),
    ], string='Run Type', default='manual', required=True)
    
    run_date = fields.Date(
        string='Run Date',
        required=True,
        default=fields.Date.today
    )
    
    billing_cutoff_date = fields.Date(
        string='Billing Cutoff Date',
        required=True,
        default=fields.Date.today,
        help='Process schedules due on or before this date'
    )
    
    # =============================================================================
    # FILTERING OPTIONS
    # =============================================================================
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    filter_type = fields.Selection([
        ('all', 'All Subscriptions'),
        ('customers', 'Specific Customers'),
        ('products', 'Specific Products'),
        ('categories', 'Product Categories'),
        ('subscription_types', 'Subscription Types'),
        ('custom', 'Custom Filter'),
    ], string='Filter Type', default='all', required=True)
    
    # Customer Filters
    partner_ids = fields.Many2many(
        'res.partner',
        'billing_run_wizard_partner_rel',
        'wizard_id', 'partner_id',
        string='Specific Customers'
    )
    
    partner_category_ids = fields.Many2many(
        'res.partner.category',
        'billing_run_wizard_partner_category_rel',
        'wizard_id', 'category_id',
        string='Customer Categories'
    )
    
    # Product Filters
    product_ids = fields.Many2many(
        'product.product',
        'billing_run_wizard_product_rel',
        'wizard_id', 'product_id',
        string='Specific Products'
    )
    
    product_category_ids = fields.Many2many(
        'product.category',
        'billing_run_wizard_product_category_rel',
        'wizard_id', 'category_id',
        string='Product Categories'
    )
    
    # Subscription Filters
    subscription_types = fields.Selection([
        ('individual', 'Individual'),
        ('enterprise', 'Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
    ], string='Subscription Types')
    
    subscription_state_filter = fields.Selection([
        ('active', 'Active Only'),
        ('all', 'All States'),
        ('active_grace', 'Active and Grace'),
    ], string='Subscription State Filter', default='active')
    
    billing_frequency_filter = fields.Selection([
        ('all', 'All Frequencies'),
        ('monthly', 'Monthly Only'),
        ('quarterly', 'Quarterly Only'),
        ('annual', 'Annual Only'),
    ], string='Billing Frequency Filter', default='all')
    
    # Date Range Filters
    filter_by_date_range = fields.Boolean(
        string='Filter by Date Range',
        help='Only include subscriptions within date range'
    )
    
    date_range_start = fields.Date(
        string='Date Range Start'
    )
    
    date_range_end = fields.Date(
        string='Date Range End'
    )
    
    # Amount Filters
    filter_by_amount = fields.Boolean(
        string='Filter by Amount Range',
        help='Only include subscriptions within amount range'
    )
    
    amount_min = fields.Monetary(
        string='Minimum Amount',
        currency_field='currency_id'
    )
    
    amount_max = fields.Monetary(
        string='Maximum Amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # =============================================================================
    # PROCESSING OPTIONS
    # =============================================================================
    
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
    
    skip_failed_customers = fields.Boolean(
        string='Skip Previously Failed Customers',
        default=False,
        help='Skip customers who had failures in recent runs'
    )
    
    failure_lookback_days = fields.Integer(
        string='Failure Lookback Days',
        default=7,
        help='Days to look back for customer failures'
    )
    
    # =============================================================================
    # PREVIEW AND VALIDATION
    # =============================================================================
    
    preview_generated = fields.Boolean(
        string='Preview Generated',
        default=False,
        readonly=True
    )
    
    preview_count = fields.Integer(
        string='Schedules Found',
        readonly=True
    )
    
    preview_total_amount = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        readonly=True
    )
    
    preview_details = fields.Text(
        string='Preview Details',
        readonly=True
    )
    
    # =============================================================================
    # NOTIFICATION OPTIONS
    # =============================================================================
    
    notify_completion = fields.Boolean(
        string='Notify on Completion',
        default=True,
        help='Send notification when run completes'
    )
    
    notification_emails = fields.Char(
        string='Notification Emails',
        help='Comma-separated email addresses for notifications'
    )
    
    notify_on_errors = fields.Boolean(
        string='Notify on Errors',
        default=True,
        help='Send notification if run has errors'
    )
    
    # =============================================================================
    # ADVANCED OPTIONS
    # =============================================================================
    
    dry_run = fields.Boolean(
        string='Dry Run',
        default=False,
        help='Simulate the run without making changes'
    )
    
    force_processing = fields.Boolean(
        string='Force Processing',
        default=False,
        help='Force processing even if some validations fail'
    )
    
    parallel_processing = fields.Boolean(
        string='Enable Parallel Processing',
        default=False,
        help='Process batches in parallel (requires configuration)'
    )
    
    max_parallel_jobs = fields.Integer(
        string='Max Parallel Jobs',
        default=3,
        help='Maximum number of parallel processing jobs'
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    estimated_duration = fields.Char(
        string='Estimated Duration',
        compute='_compute_estimated_duration',
        help='Estimated time to complete the run'
    )
    
    @api.depends('preview_count', 'batch_size', 'auto_payment')
    def _compute_estimated_duration(self):
        """Compute estimated duration based on preview"""
        for wizard in self:
            if wizard.preview_count > 0:
                # Rough estimates based on batch size and processing options
                batches = (wizard.preview_count + wizard.batch_size - 1) // wizard.batch_size
                
                # Base time per batch (seconds)
                base_time = 30
                if wizard.auto_payment:
                    base_time += 20  # Payment processing adds time
                if wizard.auto_send_invoice:
                    base_time += 10  # Email sending adds time
                
                total_seconds = batches * base_time
                
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
            if wizard.batch_size <= 0 or wizard.batch_size > 1000:
                raise ValidationError(_('Batch size must be between 1 and 1000'))
    
    @api.constrains('billing_cutoff_date', 'run_date')
    def _check_dates(self):
        """Validate dates"""
        for wizard in self:
            if wizard.billing_cutoff_date > wizard.run_date:
                raise ValidationError(_('Billing cutoff date cannot be after run date'))
    
    @api.constrains('date_range_start', 'date_range_end')
    def _check_date_range(self):
        """Validate date range"""
        for wizard in self:
            if (wizard.filter_by_date_range and 
                wizard.date_range_start and wizard.date_range_end and
                wizard.date_range_end <= wizard.date_range_start):
                raise ValidationError(_('Date range end must be after start'))
    
    @api.constrains('amount_min', 'amount_max')
    def _check_amount_range(self):
        """Validate amount range"""
        for wizard in self:
            if (wizard.filter_by_amount and 
                wizard.amount_min is not False and wizard.amount_max is not False and
                wizard.amount_max <= wizard.amount_min):
                raise ValidationError(_('Maximum amount must be greater than minimum'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('filter_type')
    def _onchange_filter_type(self):
        """Clear filters when filter type changes"""
        if self.filter_type != 'customers':
            self.partner_ids = [(5, 0, 0)]
            self.partner_category_ids = [(5, 0, 0)]
        
        if self.filter_type != 'products':
            self.product_ids = [(5, 0, 0)]
        
        if self.filter_type != 'categories':
            self.product_category_ids = [(5, 0, 0)]
        
        # Clear preview when filters change
        self.preview_generated = False
        self.preview_count = 0
        self.preview_total_amount = 0
        self.preview_details = ""
    
    @api.onchange('run_type')
    def _onchange_run_type(self):
        """Adjust default settings based on run type"""
        if self.run_type == 'test':
            self.dry_run = True
            self.auto_payment = False
            self.auto_send_invoice = False
        elif self.run_type == 'retry':
            # For retry runs, focus on failed customers
            self.skip_failed_customers = False
            self.auto_payment = True
        elif self.run_type == 'emergency':
            self.force_processing = True
            self.notify_on_errors = True
    
    @api.onchange('auto_payment')
    def _onchange_auto_payment(self):
        """Update estimated duration when auto payment changes"""
        # Trigger recomputation
        self._compute_estimated_duration()
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_default_run_name(self):
        """Generate default run name"""
        today = fields.Date.today()
        return f"Billing Run - {today}"
    
    # =============================================================================
    # PREVIEW FUNCTIONALITY
    # =============================================================================
    
    def action_generate_preview(self):
        """Generate preview of billing run"""
        self.ensure_one()
        
        # Find schedules that would be processed
        schedules = self._find_billing_schedules()
        
        # Calculate totals
        total_amount = sum(schedule.subscription_id.price * (schedule.subscription_id.quantity or 1) 
                          for schedule in schedules)
        
        # Generate preview details
        details = self._generate_preview_details(schedules)
        
        # Update preview fields
        self.write({
            'preview_generated': True,
            'preview_count': len(schedules),
            'preview_total_amount': total_amount,
            'preview_details': details,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Preview generated: %d schedules found, total amount: %s') % (
                    len(schedules), total_amount
                ),
                'type': 'info',
            }
        }
    
    def _find_billing_schedules(self):
        """Find billing schedules based on filters"""
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
        
        # Apply billing frequency filter
        if self.billing_frequency_filter != 'all':
            domain.append(('billing_frequency', '=', self.billing_frequency_filter))
        
        # Apply customer filters
        if self.filter_type == 'customers' and self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.partner_category_ids:
            partner_domain = [('category_id', 'in', self.partner_category_ids.ids)]
            partners = self.env['res.partner'].search(partner_domain)
            domain.append(('partner_id', 'in', partners.ids))
        
        # Apply product filters
        if self.filter_type == 'products' and self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        if self.filter_type == 'categories' and self.product_category_ids:
            product_domain = [('categ_id', 'in', self.product_category_ids.ids)]
            products = self.env['product.product'].search(product_domain)
            domain.append(('product_id', 'in', products.ids))
        
        # Apply subscription type filter
        if self.subscription_types:
            # This would depend on how subscription types are stored
            # Assuming it's a field on the product template
            if hasattr(self.env['product.template'], 'ams_product_type'):
                domain.append(('product_id.product_tmpl_id.ams_product_type', '=', self.subscription_types))
        
        # Apply date range filter
        if self.filter_by_date_range and self.date_range_start and self.date_range_end:
            domain.extend([
                ('subscription_id.start_date', '>=', self.date_range_start),
                ('subscription_id.start_date', '<=', self.date_range_end),
            ])
        
        # Apply amount filter
        if self.filter_by_amount:
            if self.amount_min is not False:
                domain.append(('subscription_id.price', '>=', self.amount_min))
            if self.amount_max is not False:
                domain.append(('subscription_id.price', '<=', self.amount_max))
        
        # Skip failed customers if requested
        if self.skip_failed_customers:
            failed_partner_ids = self._get_recently_failed_customers()
            if failed_partner_ids:
                domain.append(('partner_id', 'not in', failed_partner_ids))
        
        return self.env['ams.billing.schedule'].search(domain)
    
    def _get_recently_failed_customers(self):
        """Get customers who had billing failures recently"""
        cutoff_date = fields.Date.today() - timedelta(days=self.failure_lookback_days)
        
        failed_retries = self.env['ams.payment.retry'].search([
            ('state', '=', 'failed'),
            ('original_failure_date', '>=', cutoff_date),
        ])
        
        failed_dunning = self.env['ams.dunning.process'].search([
            ('state', '=', 'active'),
            ('failure_date', '>=', cutoff_date),
        ])
        
        partner_ids = set()
        partner_ids.update(failed_retries.mapped('partner_id.id'))
        partner_ids.update(failed_dunning.mapped('partner_id.id'))
        
        return list(partner_ids)
    
    def _generate_preview_details(self, schedules):
        """Generate detailed preview text"""
        if not schedules:
            return "No billing schedules found with current filters."
        
        details = []
        details.append(f"Found {len(schedules)} billing schedules:")
        details.append("")
        
        # Group by billing frequency
        frequency_groups = {}
        for schedule in schedules:
            freq = schedule.billing_frequency
            if freq not in frequency_groups:
                frequency_groups[freq] = []
            frequency_groups[freq].append(schedule)
        
        for frequency, freq_schedules in frequency_groups.items():
            details.append(f"• {frequency.title()}: {len(freq_schedules)} schedules")
        
        details.append("")
        
        # Group by subscription state
        state_groups = {}
        for schedule in schedules:
            state = schedule.subscription_id.state
            if state not in state_groups:
                state_groups[state] = []
            state_groups[state].append(schedule)
        
        details.append("By subscription state:")
        for state, state_schedules in state_groups.items():
            details.append(f"• {state.title()}: {len(state_schedules)} schedules")
        
        details.append("")
        
        # Amount breakdown
        amounts = [schedule.subscription_id.price * (schedule.subscription_id.quantity or 1) 
                  for schedule in schedules]
        
        details.append("Amount breakdown:")
        details.append(f"• Minimum: {min(amounts):.2f}")
        details.append(f"• Maximum: {max(amounts):.2f}")
        details.append(f"• Average: {sum(amounts) / len(amounts):.2f}")
        details.append(f"• Total: {sum(amounts):.2f}")
        
        return "\n".join(details)
    
    # =============================================================================
    # MAIN ACTIONS
    # =============================================================================
    
    def action_create_billing_run(self):
        """Create and start billing run"""
        self.ensure_one()
        
        # Validate configuration
        self._validate_billing_run_config()
        
        # Create billing run record
        billing_run = self._create_billing_run_record()
        
        # Start the run if not dry run
        if not self.dry_run:
            billing_run.action_start_run()
        
        return {
            'name': _('Billing Run'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.run',
            'res_id': billing_run.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_schedule_billing_run(self):
        """Schedule billing run for later execution"""
        self.ensure_one()
        
        # Validate configuration
        self._validate_billing_run_config()
        
        # Create billing run record
        billing_run = self._create_billing_run_record()
        
        # Create scheduled action for later execution
        scheduled_action = self._create_scheduled_action(billing_run)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Billing run scheduled successfully'),
                'type': 'success',
            }
        }
    
    def _validate_billing_run_config(self):
        """Validate billing run configuration"""
        if not self.preview_generated:
            raise UserError(_('Please generate preview before creating billing run'))
        
        if self.preview_count == 0:
            raise UserError(_('No billing schedules found with current filters'))
        
        if self.filter_type == 'customers' and not self.partner_ids:
            raise UserError(_('Please select customers for customer filter'))
        
        if self.filter_type == 'products' and not self.product_ids:
            raise UserError(_('Please select products for product filter'))
        
        if self.filter_type == 'categories' and not self.product_category_ids:
            raise UserError(_('Please select categories for category filter'))
        
        if self.auto_payment and self.run_type == 'test':
            raise UserError(_('Auto payment cannot be enabled for test runs'))
    
    def _create_billing_run_record(self):
        """Create billing run record"""
        vals = {
            'name': self.name,
            'description': self.description,
            'run_date': self.run_date,
            'billing_cutoff_date': self.billing_cutoff_date,
            'run_type': self.run_type,
            'company_id': self.company_id.id,
            'batch_size': self.batch_size,
            'auto_invoice': self.auto_invoice,
            'auto_send_invoice': self.auto_send_invoice,
            'auto_payment': self.auto_payment,
        }
        
        # Add filter information
        if self.filter_type == 'customers':
            vals['partner_ids'] = [(6, 0, self.partner_ids.ids)]
        elif self.filter_type == 'products':
            vals['product_ids'] = [(6, 0, self.product_ids.ids)]
        
        if self.subscription_state_filter:
            vals['subscription_state_filter'] = self.subscription_state_filter
        
        return self.env['ams.billing.run'].create(vals)
    
    def _create_scheduled_action(self, billing_run):
        """Create scheduled action for billing run"""
        return self.env['ir.cron'].create({
            'name': f'Scheduled Billing Run: {billing_run.name}',
            'model_id': self.env.ref('ams_subscription_billing.model_ams_billing_run').id,
            'code': f'model.browse({billing_run.id}).action_start_run()',
            'interval_number': 1,
            'interval_type': 'minutes',
            'nextcall': self.run_date,
            'active': True,
            'numbercall': 1,  # Run only once
        })
    
    # =============================================================================
    # UTILITY ACTIONS
    # =============================================================================
    
    def action_export_preview(self):
        """Export preview to CSV"""
        self.ensure_one()
        
        if not self.preview_generated:
            raise UserError(_('Please generate preview first'))
        
        schedules = self._find_billing_schedules()
        
        # Create CSV data
        csv_data = self._create_csv_export(schedules)
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'billing_run_preview_{self.id}.csv',
            'type': 'binary',
            'datas': csv_data,
            'res_model': 'ams.billing.run.wizard',
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    def _create_csv_export(self, schedules):
        """Create CSV export of schedules"""
        import csv
        import io
        import base64
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Customer', 'Subscription', 'Product', 'Amount', 'Quantity',
            'Billing Frequency', 'Next Billing Date', 'Subscription State'
        ])
        
        # Write data
        for schedule in schedules:
            subscription = schedule.subscription_id
            writer.writerow([
                subscription.partner_id.name,
                subscription.name,
                subscription.product_id.name,
                subscription.price,
                subscription.quantity or 1,
                schedule.billing_frequency,
                schedule.next_billing_date,
                subscription.state,
            ])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        return base64.b64encode(csv_content.encode('utf-8'))
    
    def action_copy_filters(self):
        """Copy current filters to create similar run"""
        self.ensure_one()
        
        return {
            'name': _('New Billing Run'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.run.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_filter_type': self.filter_type,
                'default_partner_ids': [(6, 0, self.partner_ids.ids)],
                'default_product_ids': [(6, 0, self.product_ids.ids)],
                'default_product_category_ids': [(6, 0, self.product_category_ids.ids)],
                'default_subscription_state_filter': self.subscription_state_filter,
                'default_billing_frequency_filter': self.billing_frequency_filter,
                'default_batch_size': self.batch_size,
                'default_auto_invoice': self.auto_invoice,
                'default_auto_send_invoice': self.auto_send_invoice,
                'default_auto_payment': self.auto_payment,
            }
        }
    
    def action_save_as_template(self):
        """Save current configuration as template"""
        self.ensure_one()
        
        return {
            'name': _('Save Billing Run Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.run.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_wizard_id': self.id,
            }
        }