# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

class AMSRevenueSchedule(models.Model):
    """Revenue Recognition Schedule for AMS Subscription Products"""
    _name = 'ams.revenue.schedule'
    _description = 'AMS Revenue Recognition Schedule'
    _order = 'start_date desc, id desc'
    _rec_name = 'display_name'

    # Basic Information
    display_name = fields.Char(
        string='Schedule Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Related Records
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='AMS Subscription',
        required=False,  # Some schedules might not have subscriptions
        ondelete='cascade',
        index=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Source Invoice',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Invoice Line',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='invoice_line_id.product_id',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='invoice_id.partner_id',
        store=True,
        readonly=True
    )

    # Recognition Configuration
    total_amount = fields.Monetary(
        string='Total Amount',
        required=True,
        currency_field='currency_id',
        help='Total amount to be recognized over the schedule period'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='invoice_id.currency_id',
        store=True,
        readonly=True
    )
    
    recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('straight_line', 'Straight Line Over Period'),
        ('milestone', 'Milestone Based'),
    ], string='Recognition Method', default='straight_line', required=True)
    
    recognition_date = fields.Date(
        string='Recognition Date',
        help='Temporary field for view compatibility'
    )
    
    # Date Configuration
    start_date = fields.Date(
        string='Recognition Start Date',
        required=True,
        default=fields.Date.today
    )
    
    end_date = fields.Date(
        string='Recognition End Date',
        required=True
    )
    
    period_length = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Recognition Period', default='monthly', required=True)
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Statistics and Tracking
    total_periods = fields.Integer(
        string='Total Periods',
        compute='_compute_period_stats',
        store=True,
        help='Total number of recognition periods'
    )
    
    recognized_amount = fields.Monetary(
        string='Recognized Amount',
        compute='_compute_amounts',
        currency_field='currency_id',
        store=True,
        help='Amount already recognized'
    )
    
    deferred_amount = fields.Monetary(
        string='Deferred Amount',
        compute='_compute_amounts',
        currency_field='currency_id',
        store=True,
        help='Amount still to be recognized'
    )
    
    recognition_count = fields.Integer(
        string='Recognition Entries',
        compute='_compute_recognition_count',
        help='Number of recognition entries created'
    )
    
    # Accounts from product configuration
    revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        compute='_compute_accounts',
        store=True,
        help='Account where revenue will be recognized'
    )
    
    deferred_account_id = fields.Many2one(
        'account.account', 
        string='Deferred Revenue Account',
        compute='_compute_accounts',
        store=True,
        help='Account where deferred revenue is held'
    )
    
    # One2many to recognition entries
    recognition_line_ids = fields.One2many(
        'ams.revenue.recognition',
        'schedule_id',
        string='Recognition Lines'
    )
    
    # Processing dates
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_date',
        store=True
    )
    
    last_processed_date = fields.Date(
        string='Last Processed Date',
        help='Last date revenue was recognized'
    )
    
    # Computed Fields
    @api.depends('invoice_line_id', 'product_id', 'partner_id')
    def _compute_display_name(self):
        """Compute display name for the schedule"""
        for schedule in self:
            if schedule.product_id and schedule.partner_id:
                schedule.display_name = f"{schedule.partner_id.name} - {schedule.product_id.name}"
            elif schedule.invoice_line_id:
                schedule.display_name = f"Schedule for {schedule.invoice_line_id.move_id.name}"
            else:
                schedule.display_name = f"Revenue Schedule #{schedule.id or 'New'}"
    
    @api.depends('start_date', 'end_date', 'period_length')
    def _compute_period_stats(self):
        """Compute total number of recognition periods"""
        for schedule in self:
            if schedule.start_date and schedule.end_date:
                periods = 0
                current_date = schedule.start_date
                
                while current_date <= schedule.end_date:
                    periods += 1
                    if schedule.period_length == 'monthly':
                        current_date = current_date + relativedelta(months=1)
                    elif schedule.period_length == 'quarterly':
                        current_date = current_date + relativedelta(months=3)
                    elif schedule.period_length == 'annual':
                        current_date = current_date + relativedelta(years=1)
                    else:
                        break  # Avoid infinite loop
                    
                    if periods > 120:  # Safety check for very long periods
                        break
                
                schedule.total_periods = periods
            else:
                schedule.total_periods = 0
    
    @api.depends('recognition_line_ids.recognized_amount')
    def _compute_amounts(self):
        """Compute recognized and deferred amounts"""
        for schedule in self:
            recognized = sum(schedule.recognition_line_ids.mapped('recognized_amount'))
            schedule.recognized_amount = recognized
            schedule.deferred_amount = schedule.total_amount - recognized
    
    def _compute_recognition_count(self):
        """Count recognition entries"""
        for schedule in self:
            schedule.recognition_count = len(schedule.recognition_line_ids)
    
    @api.depends('product_id.ams_revenue_account_id', 'product_id.ams_deferred_account_id')
    def _compute_accounts(self):
        """Get revenue and deferred accounts from product configuration"""
        for schedule in self:
            product_template = schedule.product_id.product_tmpl_id if schedule.product_id else False
            if product_template and product_template.use_ams_accounting:
                schedule.revenue_account_id = product_template.ams_revenue_account_id
                schedule.deferred_account_id = product_template.ams_deferred_account_id
            else:
                schedule.revenue_account_id = False
                schedule.deferred_account_id = False
    
    @api.depends('recognition_line_ids', 'recognition_line_ids.recognition_date', 'state')
    def _compute_next_recognition_date(self):
        """Compute next date when revenue should be recognized"""
        for schedule in self:
            if schedule.state not in ['active']:
                schedule.next_recognition_date = False
                continue
            
            # Find the next unprocessed recognition date
            next_line = schedule.recognition_line_ids.filtered(
                lambda l: l.state == 'pending' and l.recognition_date
            ).sorted('recognition_date')
            
            if next_line:
                schedule.next_recognition_date = next_line[0].recognition_date
            else:
                schedule.next_recognition_date = False

    # CRUD and Validation
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to automatically generate recognition lines"""
        schedules = super().create(vals_list)
        
        for schedule in schedules:
            if schedule.state == 'draft':
                schedule._generate_recognition_lines()
        
        return schedules
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate date ranges"""
        for schedule in self:
            if schedule.start_date and schedule.end_date:
                if schedule.end_date <= schedule.start_date:
                    raise UserError(_('End date must be after start date'))
    
    @api.constrains('total_amount')
    def _check_amount(self):
        """Validate amounts"""
        for schedule in self:
            if schedule.total_amount <= 0:
                raise UserError(_('Total amount must be greater than zero'))
    
    # Actions and Processing
    def action_activate(self):
        """Activate the revenue recognition schedule"""
        for schedule in self:
            if schedule.state != 'draft':
                raise UserError(_('Only draft schedules can be activated'))
            
            # Validate configuration
            if not schedule.revenue_account_id:
                raise UserError(_('Revenue account is required to activate schedule'))
            
            if schedule.recognition_method == 'straight_line' and not schedule.deferred_account_id:
                raise UserError(_('Deferred revenue account is required for straight line recognition'))
            
            # Generate recognition lines if not already done
            if not schedule.recognition_line_ids:
                schedule._generate_recognition_lines()
            
            schedule.state = 'active'
            schedule.message_post(body=_('Revenue recognition schedule activated'))
    
    def action_cancel(self):
        """Cancel the revenue recognition schedule"""
        for schedule in self:
            # Check if any revenue has been recognized
            if schedule.recognized_amount > 0:
                raise UserError(_('Cannot cancel schedule with recognized revenue. Create reversing entries first.'))
            
            # Cancel all pending recognition lines
            schedule.recognition_line_ids.filtered(lambda l: l.state == 'pending').write({'state': 'cancelled'})
            
            schedule.state = 'cancelled'
            schedule.message_post(body=_('Revenue recognition schedule cancelled'))
    
    def _generate_recognition_lines(self):
        """Generate individual recognition lines based on the schedule"""
        self.ensure_one()
        
        if self.recognition_line_ids:
            # Lines already exist
            return
        
        if self.recognition_method == 'immediate':
            # Single recognition on start date
            self._create_recognition_line(
                recognition_date=self.start_date,
                amount=self.total_amount,
                description=f"Immediate recognition - {self.product_id.name}"
            )
        elif self.recognition_method == 'straight_line':
            # Create lines for each period
            self._create_straight_line_entries()
    
    def _create_straight_line_entries(self):
        """Create straight-line recognition entries"""
        if self.total_periods <= 0:
            return
        
        amount_per_period = self.total_amount / self.total_periods
        current_date = self.start_date
        period_num = 1
        
        while current_date <= self.end_date and period_num <= self.total_periods:
            # For the last period, use remaining amount to handle rounding
            if period_num == self.total_periods:
                remaining_amount = self.total_amount - (amount_per_period * (self.total_periods - 1))
                amount = remaining_amount
            else:
                amount = amount_per_period
            
            self._create_recognition_line(
                recognition_date=current_date,
                amount=amount,
                description=f"Period {period_num} of {self.total_periods} - {self.product_id.name}"
            )
            
            # Move to next period
            if self.period_length == 'monthly':
                current_date = current_date + relativedelta(months=1)
            elif self.period_length == 'quarterly':
                current_date = current_date + relativedelta(months=3)
            elif self.period_length == 'annual':
                current_date = current_date + relativedelta(years=1)
            
            period_num += 1
    
    def _create_recognition_line(self, recognition_date, amount, description):
        """Create a single recognition line"""
        return self.env['ams.revenue.recognition'].create({
            'schedule_id': self.id,
            'recognition_date': recognition_date,
            'scheduled_amount': amount,
            'description': description,
            'state': 'pending'
        })
    
    def process_due_recognitions(self, cutoff_date=None):
        """Process revenue recognitions due up to cutoff date"""
        if not cutoff_date:
            cutoff_date = fields.Date.today()
        
        for schedule in self:
            if schedule.state != 'active':
                continue
            
            # Find due recognition lines
            due_lines = schedule.recognition_line_ids.filtered(
                lambda l: l.state == 'pending' and l.recognition_date <= cutoff_date
            )
            
            for line in due_lines:
                line.action_recognize_revenue()
            
            # Check if schedule is completed
            if schedule.deferred_amount <= 0.01:  # Allow small rounding differences
                schedule.state = 'completed'
                schedule.message_post(body=_('Revenue recognition schedule completed'))
    
    def action_view_recognition_entries(self):
        """View recognition entries for this schedule"""
        self.ensure_one()
        
        return {
            'name': f'Recognition Entries - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
        }
    
    @api.model
    def cron_process_revenue_recognition(self):
        """Cron job to process due revenue recognitions"""
        active_schedules = self.search([('state', '=', 'active')])
        
        processed_count = 0
        for schedule in active_schedules:
            try:
                initial_recognized = schedule.recognized_amount
                schedule.process_due_recognitions()
                
                if schedule.recognized_amount > initial_recognized:
                    processed_count += 1
            except Exception as e:
                # Log error but continue processing other schedules
                schedule.message_post(
                    body=f"Error processing revenue recognition: {str(e)}",
                    message_type='comment'
                )
        
        return {
            'processed_schedules': processed_count,
            'total_active': len(active_schedules),
        }