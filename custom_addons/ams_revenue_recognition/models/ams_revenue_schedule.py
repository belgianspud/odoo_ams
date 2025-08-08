# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSRevenueSchedule(models.Model):
    """Revenue Recognition Schedule for AMS Subscriptions"""
    _name = 'ams.revenue.schedule'
    _description = 'AMS Revenue Recognition Schedule'
    _order = 'start_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Schedule Name',
        required=True,
        tracking=True,
        help='Name of the revenue recognition schedule'
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Related AMS subscription'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='subscription_id.partner_id',
        store=True,
        help='Customer from subscription'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='subscription_id.product_id',
        store=True,
        help='Product from subscription'
    )
    
    # Revenue Details
    total_contract_value = fields.Float(
        string='Total Contract Value',
        required=True,
        tracking=True,
        help='Total amount to be recognized over the contract period'
    )
    
    recognized_revenue = fields.Float(
        string='Recognized Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Total revenue recognized to date'
    )
    
    remaining_revenue = fields.Float(
        string='Remaining Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Revenue remaining to be recognized'
    )
    
    deferred_revenue_balance = fields.Float(
        string='Deferred Revenue Balance',
        compute='_compute_revenue_amounts',
        store=True,
        help='Current deferred revenue liability balance'
    )
    
    # Schedule Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        help='Date when revenue recognition begins'
    )
    
    end_date = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        help='Date when revenue recognition ends'
    )
    
    last_recognition_date = fields.Date(
        string='Last Recognition Date',
        help='Date of most recent revenue recognition'
    )
    
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_date',
        store=True,
        help='Date of next scheduled revenue recognition'
    )
    
    # Recognition Configuration
    recognition_method = fields.Selection([
        ('straight_line', 'Straight Line'),
        ('daily', 'Daily Recognition'),
        ('milestone', 'Milestone Based'),
        ('usage', 'Usage Based'),
    ], string='Recognition Method', default='straight_line', required=True,
       tracking=True, help='Method used for revenue recognition')
    
    recognition_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], string='Recognition Frequency', default='monthly', required=True,
       help='How often revenue is recognized')
    
    period_count = fields.Integer(
        string='Total Periods',
        compute='_compute_period_count',
        store=True,
        help='Total number of recognition periods'
    )
    
    periods_completed = fields.Integer(
        string='Periods Completed',
        compute='_compute_periods_completed',
        store=True,
        help='Number of recognition periods completed'
    )
    
    periods_remaining = fields.Integer(
        string='Periods Remaining',
        compute='_compute_periods_remaining',
        store=True,
        help='Number of recognition periods remaining'
    )
    
    # Status and Control
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
       help='Current status of the recognition schedule')
    
    is_auto_recognition = fields.Boolean(
        string='Auto Recognition',
        default=True,
        help='Automatically recognize revenue based on schedule'
    )
    
    # Related Records
    invoice_id = fields.Many2one(
        'account.move',
        string='Source Invoice',
        help='Invoice that created this recognition schedule'
    )
    
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Source Invoice Line',
        help='Invoice line that created this recognition schedule'
    )
    
    recognition_ids = fields.One2many(
        'ams.revenue.recognition',
        'schedule_id',
        string='Recognition Entries',
        help='Individual revenue recognition entries'
    )
    
    modification_ids = fields.One2many(
        'ams.contract.modification',
        'schedule_id',
        string='Contract Modifications',
        help='Contract modifications affecting this schedule'
    )
    
    # Accounting References
    deferred_account_id = fields.Many2one(
        'account.account',
        string='Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Account holding deferred revenue'
    )
    
    revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='Account for recognized revenue'
    )
    
    # Performance Obligation Tracking (ASC 606)
    performance_obligation_id = fields.Char(
        string='Performance Obligation ID',
        help='Unique identifier for performance obligation tracking'
    )
    
    contract_start_date = fields.Date(
        string='Contract Start Date',
        help='Start date of the underlying contract'
    )
    
    contract_end_date = fields.Date(
        string='Contract End Date',
        help='End date of the underlying contract'
    )
    
    # Proration and Adjustments
    is_prorated = fields.Boolean(
        string='Prorated Schedule',
        default=False,
        help='This schedule was created from a partial period'
    )
    
    proration_factor = fields.Float(
        string='Proration Factor',
        default=1.0,
        help='Factor applied for partial period recognition (0.0 to 1.0)'
    )
    
    original_schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Original Schedule',
        help='Reference to original schedule if this is a modification'
    )
    
    # Computed Fields
    completion_percentage = fields.Float(
        string='Completion %',
        compute='_compute_completion_percentage',
        store=True,
        help='Percentage of revenue recognition completed'
    )
    
    daily_recognition_amount = fields.Float(
        string='Daily Recognition Amount',
        compute='_compute_daily_amount',
        store=True,
        help='Amount to recognize per day'
    )
    
    monthly_recognition_amount = fields.Float(
        string='Monthly Recognition Amount',
        compute='_compute_monthly_amount',
        store=True,
        help='Amount to recognize per month'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this revenue schedule belongs to'
    )
    
    # Technical Fields
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    create_date = fields.Datetime(string='Created on', readonly=True)
    
    # Constraints and Validations
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate date ranges"""
        for schedule in self:
            if schedule.end_date <= schedule.start_date:
                raise ValidationError("End date must be after start date.")
            
            # Check for reasonable duration (not more than 10 years)
            max_duration = schedule.start_date + relativedelta(years=10)
            if schedule.end_date > max_duration:
                raise ValidationError("Recognition period cannot exceed 10 years.")
    
    @api.constrains('total_contract_value')
    def _check_contract_value(self):
        """Validate contract value"""
        for schedule in self:
            if schedule.total_contract_value <= 0:
                raise ValidationError("Total contract value must be positive.")
    
    @api.constrains('proration_factor')
    def _check_proration_factor(self):
        """Validate proration factor"""
        for schedule in self:
            if not (0.0 <= schedule.proration_factor <= 1.0):
                raise ValidationError("Proration factor must be between 0.0 and 1.0.")
    
    # Computed Methods
    @api.depends('recognition_ids.recognized_amount')
    def _compute_revenue_amounts(self):
        """Compute revenue amounts based on recognition entries"""
        for schedule in self:
            recognized = sum(schedule.recognition_ids.filtered(
                lambda r: r.state == 'posted'
            ).mapped('recognized_amount'))
            
            schedule.recognized_revenue = recognized
            schedule.remaining_revenue = schedule.total_contract_value - recognized
            schedule.deferred_revenue_balance = schedule.remaining_revenue
    
    @api.depends('start_date', 'end_date', 'recognition_frequency')
    def _compute_period_count(self):
        """Compute total number of recognition periods"""
        for schedule in self:
            if not schedule.start_date or not schedule.end_date:
                schedule.period_count = 0
                continue
                
            if schedule.recognition_frequency == 'daily':
                schedule.period_count = (schedule.end_date - schedule.start_date).days + 1
            elif schedule.recognition_frequency == 'weekly':
                schedule.period_count = ((schedule.end_date - schedule.start_date).days // 7) + 1
            elif schedule.recognition_frequency == 'monthly':
                # Calculate months between dates
                months = (schedule.end_date.year - schedule.start_date.year) * 12
                months += schedule.end_date.month - schedule.start_date.month
                schedule.period_count = months + 1
            elif schedule.recognition_frequency == 'quarterly':
                months = (schedule.end_date.year - schedule.start_date.year) * 12
                months += schedule.end_date.month - schedule.start_date.month
                schedule.period_count = (months // 3) + 1
            else:
                schedule.period_count = 1
    
    @api.depends('recognition_ids', 'recognition_frequency')
    def _compute_periods_completed(self):
        """Compute number of completed recognition periods"""
        for schedule in self:
            completed_entries = schedule.recognition_ids.filtered(
                lambda r: r.state == 'posted'
            )
            schedule.periods_completed = len(completed_entries)
    
    @api.depends('period_count', 'periods_completed')
    def _compute_periods_remaining(self):
        """Compute remaining recognition periods"""
        for schedule in self:
            schedule.periods_remaining = max(0, schedule.period_count - schedule.periods_completed)
    
    @api.depends('periods_completed', 'period_count')
    def _compute_completion_percentage(self):
        """Compute completion percentage"""
        for schedule in self:
            if schedule.period_count > 0:
                schedule.completion_percentage = (schedule.periods_completed / schedule.period_count) * 100
            else:
                schedule.completion_percentage = 0.0
    
    @api.depends('last_recognition_date', 'recognition_frequency', 'state')
    def _compute_next_recognition_date(self):
        """Compute next recognition date"""
        for schedule in self:
            if schedule.state not in ['active'] or schedule.completion_percentage >= 100:
                schedule.next_recognition_date = False
                continue
                
            if schedule.last_recognition_date:
                base_date = schedule.last_recognition_date
            else:
                base_date = schedule.start_date
                
            if schedule.recognition_frequency == 'daily':
                next_date = base_date + timedelta(days=1)
            elif schedule.recognition_frequency == 'weekly':
                next_date = base_date + timedelta(weeks=1)
            elif schedule.recognition_frequency == 'monthly':
                next_date = base_date + relativedelta(months=1)
            elif schedule.recognition_frequency == 'quarterly':
                next_date = base_date + relativedelta(months=3)
            else:
                next_date = False
                
            # Don't go past end date
            if next_date and next_date <= schedule.end_date:
                schedule.next_recognition_date = next_date
            else:
                schedule.next_recognition_date = False
    
    @api.depends('total_contract_value', 'start_date', 'end_date')
    def _compute_daily_amount(self):
        """Compute daily recognition amount"""
        for schedule in self:
            if schedule.start_date and schedule.end_date and schedule.total_contract_value:
                days = (schedule.end_date - schedule.start_date).days + 1
                schedule.daily_recognition_amount = schedule.total_contract_value / days if days > 0 else 0
            else:
                schedule.daily_recognition_amount = 0
    
    @api.depends('daily_recognition_amount')
    def _compute_monthly_amount(self):
        """Compute monthly recognition amount"""
        for schedule in self:
            # Approximate monthly amount (daily * 30.44 average days per month)
            schedule.monthly_recognition_amount = schedule.daily_recognition_amount * 30.44
    
    # CRUD Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create method"""
        for vals in vals_list:
            # Auto-generate name if not provided
            if not vals.get('name'):
                subscription = self.env['ams.subscription'].browse(vals.get('subscription_id'))
                vals['name'] = f"Revenue Schedule - {subscription.name}"
            
            # Set performance obligation ID
            if not vals.get('performance_obligation_id'):
                vals['performance_obligation_id'] = f"PO-{vals.get('subscription_id', 'NEW')}-{date.today().strftime('%Y%m%d')}"
        
        schedules = super().create(vals_list)
        
        for schedule in schedules:
            schedule._setup_accounting_references()
            
        return schedules
    
    def write(self, vals):
        """Enhanced write method"""
        result = super().write(vals)
        
        # If key fields changed, update recognition entries
        if any(field in vals for field in ['total_contract_value', 'start_date', 'end_date', 'recognition_frequency']):
            for schedule in self:
                if schedule.state == 'active':
                    schedule._regenerate_future_recognitions()
        
        return result
    
    # Business Logic Methods
    def action_activate(self):
        """Activate the revenue recognition schedule"""
        for schedule in self:
            if schedule.state != 'draft':
                raise UserError(f"Cannot activate schedule in {schedule.state} state.")
            
            schedule._validate_for_activation()
            schedule.state = 'active'
            schedule._generate_recognition_entries()
            
            schedule.message_post(body="Revenue recognition schedule activated.")
    
    def action_pause(self):
        """Pause the revenue recognition schedule"""
        for schedule in self:
            if schedule.state != 'active':
                raise UserError(f"Cannot pause schedule in {schedule.state} state.")
            
            schedule.state = 'paused'
            schedule.message_post(body="Revenue recognition schedule paused.")
    
    def action_resume(self):
        """Resume a paused revenue recognition schedule"""
        for schedule in self:
            if schedule.state != 'paused':
                raise UserError(f"Cannot resume schedule in {schedule.state} state.")
            
            schedule.state = 'active'
            schedule._generate_recognition_entries()
            schedule.message_post(body="Revenue recognition schedule resumed.")
    
    def action_complete(self):
        """Mark schedule as completed"""
        for schedule in self:
            if schedule.remaining_revenue > 0.01:  # Allow for rounding differences
                raise UserError("Cannot complete schedule with remaining revenue.")
            
            schedule.state = 'completed'
            schedule.message_post(body="Revenue recognition schedule completed.")
    
    def action_cancel(self):
        """Cancel the revenue recognition schedule"""
        for schedule in self:
            if schedule.state == 'completed':
                raise UserError("Cannot cancel a completed schedule.")
            
            # Cancel any draft recognition entries
            draft_recognitions = schedule.recognition_ids.filtered(lambda r: r.state == 'draft')
            draft_recognitions.unlink()
            
            schedule.state = 'cancelled'
            schedule.message_post(body="Revenue recognition schedule cancelled.")
    
    def _validate_for_activation(self):
        """Validate schedule can be activated"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError("Schedule must be linked to a subscription.")
        
        if not self.total_contract_value or self.total_contract_value <= 0:
            raise UserError("Total contract value must be positive.")
        
        if not self.start_date or not self.end_date:
            raise UserError("Start and end dates are required.")
        
        if not self.deferred_account_id or not self.revenue_account_id:
            raise UserError("Deferred revenue and revenue accounts must be configured.")
    
    def _setup_accounting_references(self):
        """Setup accounting account references"""
        self.ensure_one()
        
        product = self.product_id.product_tmpl_id
        
        # Set deferred revenue account
        if not self.deferred_account_id and product.ams_deferred_account_id:
            self.deferred_account_id = product.ams_deferred_account_id
        
        # Set revenue account
        if not self.revenue_account_id and product.ams_revenue_account_id:
            self.revenue_account_id = product.ams_revenue_account_id
    
    def _generate_recognition_entries(self):
        """Generate future recognition entries"""
        self.ensure_one()
        
        if self.state != 'active':
            return
        
        # Find last recognition date
        last_recognition = self.recognition_ids.filtered(
            lambda r: r.state == 'posted'
        ).sorted('recognition_date', reverse=True)
        
        if last_recognition:
            next_date = self._get_next_recognition_date(last_recognition[0].recognition_date)
        else:
            next_date = self.start_date
        
        # Generate entries until end date
        entries_created = 0
        while next_date and next_date <= self.end_date and entries_created < 100:  # Safety limit
            # Check if entry already exists
            existing = self.recognition_ids.filtered(
                lambda r: r.recognition_date == next_date
            )
            
            if not existing:
                recognition_amount = self._calculate_recognition_amount(next_date)
                if recognition_amount > 0:
                    self.env['ams.revenue.recognition'].create({
                        'schedule_id': self.id,
                        'recognition_date': next_date,
                        'planned_amount': recognition_amount,
                        'state': 'draft',
                    })
                    entries_created += 1
            
            next_date = self._get_next_recognition_date(next_date)
        
        _logger.info(f"Generated {entries_created} recognition entries for schedule {self.id}")
    
    def _get_next_recognition_date(self, current_date):
        """Get next recognition date based on frequency"""
        if self.recognition_frequency == 'daily':
            return current_date + timedelta(days=1)
        elif self.recognition_frequency == 'weekly':
            return current_date + timedelta(weeks=1)
        elif self.recognition_frequency == 'monthly':
            return current_date + relativedelta(months=1)
        elif self.recognition_frequency == 'quarterly':
            return current_date + relativedelta(months=3)
        else:
            return None
    
    def _calculate_recognition_amount(self, recognition_date):
        """Calculate recognition amount for a specific date"""
        self.ensure_one()
        
        if self.recognition_method == 'straight_line':
            return self.daily_recognition_amount
        else:
            # Other methods can be implemented here
            return self.daily_recognition_amount
    
    def _regenerate_future_recognitions(self):
        """Regenerate future recognition entries after schedule changes"""
        self.ensure_one()
        
        # Delete draft future recognitions
        future_drafts = self.recognition_ids.filtered(
            lambda r: r.state == 'draft' and r.recognition_date >= date.today()
        )
        future_drafts.unlink()
        
        # Regenerate
        self._generate_recognition_entries()
    
    @api.model
    def create_from_subscription(self, subscription):
        """Create revenue recognition schedule from subscription"""
        if not subscription.product_id.product_tmpl_id.use_ams_accounting:
            return False
        
        # Calculate contract value from latest invoice
        contract_value = 0.0
        if subscription.invoice_line_id:
            contract_value = subscription.invoice_line_id.price_subtotal
        elif subscription.product_id:
            contract_value = subscription.product_id.list_price
        
        if contract_value <= 0:
            _logger.warning(f"Cannot create revenue schedule for subscription {subscription.id}: no contract value")
            return False
        
        # Determine recognition period
        start_date = subscription.start_date or date.today()
        if subscription.paid_through_date:
            end_date = subscription.paid_through_date
        else:
            # Default to annual recognition
            end_date = start_date + relativedelta(years=1) - timedelta(days=1)
        
        vals = {
            'subscription_id': subscription.id,
            'total_contract_value': contract_value,
            'start_date': start_date,
            'end_date': end_date,
            'contract_start_date': start_date,
            'contract_end_date': end_date,
            'invoice_id': subscription.invoice_id.id if subscription.invoice_id else False,
            'invoice_line_id': subscription.invoice_line_id.id if subscription.invoice_line_id else False,
            'state': 'active',
        }
        
        schedule = self.create(vals)
        schedule.action_activate()
        
        return schedule
    
    # Automated Processing
    @api.model
    def cron_process_revenue_recognition(self):
        """Cron job to process revenue recognition"""
        today = date.today()
        
        # Find schedules with recognition due
        schedules_to_process = self.search([
            ('state', '=', 'active'),
            ('is_auto_recognition', '=', True),
            ('next_recognition_date', '<=', today),
        ])
        
        processed_count = 0
        error_count = 0
        
        for schedule in schedules_to_process:
            try:
                # Find recognition entries ready for processing
                ready_recognitions = schedule.recognition_ids.filtered(
                    lambda r: r.state == 'draft' and r.recognition_date <= today
                )
                
                for recognition in ready_recognitions:
                    recognition.action_recognize()
                    processed_count += 1
                    
                # Update last recognition date
                if ready_recognitions:
                    latest_date = max(ready_recognitions.mapped('recognition_date'))
                    schedule.last_recognition_date = latest_date
                    
            except Exception as e:
                error_count += 1
                _logger.error(f"Error processing revenue recognition for schedule {schedule.id}: {str(e)}")
                
                # Create activity for manual review
                schedule.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary='Revenue Recognition Error',
                    note=f'Automated revenue recognition failed: {str(e)}',
                    user_id=1  # Admin user
                )
        
        _logger.info(f"Revenue recognition cron completed: {processed_count} processed, {error_count} errors")
        
        return {
            'processed': processed_count,
            'errors': error_count
        }