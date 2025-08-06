# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class AMSRevenueRecognition(models.Model):
    """AMS Revenue Recognition Entries"""
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition'
    _order = 'recognition_date desc, id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Information
    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default='/',
        tracking=True
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False,
        default='draft', tracking=True)
    
    # Subscription Reference
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='subscription_id.partner_id',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        related='subscription_id.product_id',
        store=True,
        readonly=True
    )
    
    # Recognition Details
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
        help="Date when revenue should be recognized"
    )
    
    period_start = fields.Date(
        string='Period Start',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Start date of the revenue recognition period"
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="End date of the revenue recognition period"
    )
    
    period_days = fields.Integer(
        string='Period Days',
        compute='_compute_period_days',
        store=True,
        help="Number of days in the recognition period"
    )
    
    # Amounts
    total_subscription_amount = fields.Float(
        string='Total Subscription Amount',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        digits='Account',
        help="Total amount of the subscription"
    )
    
    recognition_amount = fields.Float(
        string='Recognition Amount',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        digits='Account',
        tracking=True,
        help="Amount to be recognized for this period"
    )
    
    recognition_percentage = fields.Float(
        string='Recognition Percentage',
        compute='_compute_recognition_percentage',
        store=True,
        digits=(12, 4),
        help="Percentage of total subscription amount being recognized"
    )
    
    # Recognition Method
    recognition_method = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ], string='Recognition Method', required=True, default='monthly',
        readonly=True, states={'draft': [('readonly', False)]})
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    
    # Accounting Configuration
    revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Revenue Account',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('account_type', 'in', ['income', 'income_membership', 'income_chapter', 'income_publication']), ('company_id', '=', company_id)]",
        tracking=True
    )
    
    deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Deferred Revenue Account',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]",
        tracking=True
    )
    
    journal_id = fields.Many2one(
        'ams.account.journal',
        string='Journal',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        tracking=True
    )
    
    journal_entry_date = fields.Date(
        string='Journal Entry Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Date for the journal entry (defaults to recognition date)"
    )
    
    # Journal Entry
    move_id = fields.Many2one(
        'ams.account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        tracking=True
    )
    
    # Automation Settings
    is_automated = fields.Boolean(
        string='Automated Entry',
        default=False,
        readonly=True,
        help="Indicates if this entry was created automatically"
    )
    
    auto_post = fields.Boolean(
        string='Auto Post',
        default=False,
        help="Automatically post this entry when confirmed"
    )
    
    # Schedule Information
    schedule_id = fields.Many2one(
        'ams.revenue.recognition.schedule',
        string='Recognition Schedule',
        readonly=True,
        help="Schedule that generated this entry"
    )
    
    schedule_line_id = fields.Many2one(
        'ams.revenue.recognition.schedule.line',
        string='Schedule Line',
        readonly=True,
        help="Specific schedule line that generated this entry"
    )
    
    sequence_number = fields.Integer(
        string='Sequence',
        help="Sequence number in the recognition schedule"
    )
    
    # Progress Information
    is_first_recognition = fields.Boolean(
        string='First Recognition',
        compute='_compute_recognition_progress',
        store=True
    )
    
    is_last_recognition = fields.Boolean(
        string='Last Recognition',
        compute='_compute_recognition_progress',
        store=True
    )
    
    # Amounts Progress
    total_schedule_amount = fields.Float(
        string='Total Schedule Amount',
        compute='_compute_recognition_progress',
        store=True,
        digits='Account'
    )
    
    cumulative_recognized_amount = fields.Float(
        string='Cumulative Recognized',
        compute='_compute_recognition_progress',
        store=True,
        digits='Account'
    )
    
    # Processing Information
    processing_notes = fields.Text(
        string='Processing Notes',
        help="Notes about the processing of this recognition entry"
    )
    
    calculation_details = fields.Html(
        string='Calculation Details',
        compute='_compute_calculation_details',
        help="Details about how the recognition amount was calculated"
    )
    
    journal_entry_preview = fields.Html(
        string='Journal Entry Preview',
        compute='_compute_journal_entry_preview',
        help="Preview of the journal entry to be created"
    )
    
    # Related Schedule Entries
    related_schedule_entries = fields.One2many(
        'ams.revenue.recognition',
        compute='_compute_related_entries',
        string='Related Entries'
    )
    
    # State Tracking
    confirmed_date = fields.Datetime(string='Confirmed Date', readonly=True)
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', readonly=True)
    posted_date = fields.Datetime(string='Posted Date', readonly=True)
    posted_by = fields.Many2one('res.users', string='Posted By', readonly=True)
    
    # Computed Methods
    @api.depends('period_start', 'period_end')
    def _compute_period_days(self):
        """Compute number of days in the period"""
        for record in self:
            if record.period_start and record.period_end:
                delta = record.period_end - record.period_start
                record.period_days = delta.days + 1
            else:
                record.period_days = 0
    
    @api.depends('recognition_amount', 'total_subscription_amount')
    def _compute_recognition_percentage(self):
        """Compute recognition percentage"""
        for record in self:
            if record.total_subscription_amount:
                record.recognition_percentage = (record.recognition_amount / record.total_subscription_amount) * 100
            else:
                record.recognition_percentage = 0.0
    
    @api.depends('subscription_id', 'schedule_id')
    def _compute_recognition_progress(self):
        """Compute recognition progress information"""
        for record in self:
            record.is_first_recognition = False
            record.is_last_recognition = False
            record.total_schedule_amount = 0.0
            record.cumulative_recognized_amount = 0.0
            
            if record.subscription_id:
                # Find all recognition entries for this subscription
                all_entries = self.search([
                    ('subscription_id', '=', record.subscription_id.id),
                    ('state', '=', 'posted')
                ], order='recognition_date')
                
                if all_entries:
                    record.is_first_recognition = (record.id == all_entries[0].id)
                    record.is_last_recognition = (record.id == all_entries[-1].id)
                    record.total_schedule_amount = sum(all_entries.mapped('recognition_amount'))
                    
                    # Calculate cumulative amount up to this entry
                    entries_before = all_entries.filtered(lambda e: e.recognition_date <= record.recognition_date)
                    record.cumulative_recognized_amount = sum(entries_before.mapped('recognition_amount'))
    
    def _compute_calculation_details(self):
        """Compute calculation details HTML"""
        for record in self:
            if record.total_subscription_amount and record.recognition_amount:
                percentage = record.recognition_percentage
                details = f"""
                <div class="o_form_label">Recognition Calculation:</div>
                <table class="table table-sm">
                    <tr><td>Total Subscription Amount:</td><td>{record.total_subscription_amount:.2f}</td></tr>
                    <tr><td>Recognition Amount:</td><td>{record.recognition_amount:.2f}</td></tr>
                    <tr><td>Recognition Percentage:</td><td>{percentage:.2f}%</td></tr>
                    <tr><td>Period Days:</td><td>{record.period_days}</td></tr>
                    <tr><td>Method:</td><td>{record.recognition_method.title()}</td></tr>
                </table>
                """
                record.calculation_details = details
            else:
                record.calculation_details = "<p>No calculation details available.</p>"
    
    def _compute_journal_entry_preview(self):
        """Compute journal entry preview"""
        for record in self:
            if record.state == 'draft':
                preview = """
                <div class="o_form_label">Journal Entry Preview:</div>
                <p><em>Confirm the entry to see journal entry preview.</em></p>
                """
            elif record.move_id:
                preview = f"""
                <div class="o_form_label">Journal Entry Created:</div>
                <p>Entry: <strong>{record.move_id.name}</strong></p>
                <p>Date: {record.move_id.date}</p>
                <p>Amount: {record.recognition_amount:.2f}</p>
                """
            else:
                preview = f"""
                <div class="o_form_label">Journal Entry to be Created:</div>
                <table class="table table-sm">
                    <tr>
                        <td>Account</td>
                        <td>Debit</td>
                        <td>Credit</td>
                    </tr>
                    <tr>
                        <td>{record.deferred_revenue_account_id.name or 'Deferred Revenue'}</td>
                        <td>{record.recognition_amount:.2f}</td>
                        <td>0.00</td>
                    </tr>
                    <tr>
                        <td>{record.revenue_account_id.name or 'Revenue'}</td>
                        <td>0.00</td>
                        <td>{record.recognition_amount:.2f}</td>
                    </tr>
                </table>
                """
            record.journal_entry_preview = preview
    
    def _compute_related_entries(self):
        """Compute related recognition entries"""
        for record in self:
            if record.subscription_id:
                related = self.search([
                    ('subscription_id', '=', record.subscription_id.id),
                    ('id', '!=', record.id)
                ], order='recognition_date')
                record.related_schedule_entries = related
            else:
                record.related_schedule_entries = self.env['ams.revenue.recognition']
    
    # Constraints and Validations
    @api.constrains('period_start', 'period_end')
    def _check_period_dates(self):
        """Validate period dates"""
        for record in self:
            if record.period_start and record.period_end:
                if record.period_start > record.period_end:
                    raise ValidationError("Period start date cannot be after period end date.")
    
    @api.constrains('recognition_amount', 'total_subscription_amount')
    def _check_amounts(self):
        """Validate amounts"""
        for record in self:
            if record.recognition_amount < 0:
                raise ValidationError("Recognition amount cannot be negative.")
            
            if record.total_subscription_amount < 0:
                raise ValidationError("Total subscription amount cannot be negative.")
            
            if record.recognition_amount > record.total_subscription_amount:
                raise ValidationError("Recognition amount cannot exceed total subscription amount.")
    
    # Lifecycle Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence numbers"""
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.revenue.recognition') or '/'
            
            # Set journal entry date if not provided
            if not vals.get('journal_entry_date'):
                vals['journal_entry_date'] = vals.get('recognition_date')
        
        return super().create(vals_list)
    
    def copy(self, default=None):
        """Override copy"""
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': '/',
            'state': 'draft',
            'move_id': False,
            'confirmed_date': False,
            'confirmed_by': False,
            'posted_date': False,
            'posted_by': False,
        })
        return super().copy(default)
    
    def unlink(self):
        """Prevent deletion of posted entries"""
        for record in self:
            if record.state == 'posted':
                raise UserError(
                    f"You cannot delete posted revenue recognition entry '{record.name}'. "
                    "You must cancel it first."
                )
            if record.move_id:
                raise UserError(
                    f"You cannot delete revenue recognition entry '{record.name}' "
                    "that has a journal entry. Cancel the entry first."
                )
        return super().unlink()
    
    # Action Methods
    def action_confirm(self):
        """Confirm the revenue recognition entry"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft entries can be confirmed.")
            
            record._validate_entry()
            
            record.write({
                'state': 'confirmed',
                'confirmed_date': fields.Datetime.now(),
                'confirmed_by': self.env.user.id,
            })
            
            # Auto-post if requested
            if record.auto_post:
                record.action_post()
    
    def action_post(self):
        """Post the revenue recognition entry"""
        for record in self:
            if record.state not in ['confirmed']:
                raise UserError("Only confirmed entries can be posted.")
            
            # Create journal entry
            record._create_journal_entry()
            
            record.write({
                'state': 'posted',
                'posted_date': fields.Datetime.now(),
                'posted_by': self.env.user.id,
            })
            
            # Update schedule line if applicable
            if record.schedule_line_id:
                record.schedule_line_id.write({'state': 'recognized'})
    
    def action_cancel(self):
        """Cancel the revenue recognition entry"""
        for record in self:
            if record.state == 'posted':
                raise UserError("Posted entries cannot be cancelled. You must reverse the journal entry first.")
            
            record.write({'state': 'cancelled'})
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state != 'cancelled':
                raise UserError("Only cancelled entries can be reset to draft.")
            if record.move_id:
                raise UserError("Entries with journal entries cannot be reset to draft.")
            
            record.write({
                'state': 'draft',
                'confirmed_date': False,
                'confirmed_by': False,
            })
    
    # Helper Methods
    def _validate_entry(self):
        """Validate entry before confirmation"""
        self.ensure_one()
        
        if not self.revenue_account_id:
            raise ValidationError("Revenue account is required.")
        
        if not self.deferred_revenue_account_id:
            raise ValidationError("Deferred revenue account is required.")
        
        if not self.journal_id:
            raise ValidationError("Journal is required.")
        
        if not self.recognition_amount:
            raise ValidationError("Recognition amount must be greater than zero.")
    
    def _create_journal_entry(self):
        """Create journal entry for revenue recognition"""
        self.ensure_one()
        
        if self.move_id:
            return self.move_id
        
        # Prepare journal entry values
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.journal_entry_date or self.recognition_date,
            'ref': f'Revenue Recognition - {self.name}',
            'move_type': 'revenue_recognition',
            'revenue_recognition_id': self.id,
            'company_id': self.company_id.id,
        }
        
        # Create the move
        move = self.env['ams.account.move'].create(move_vals)
        
        # Create journal entry lines
        line_vals = []
        
        # Debit: Deferred Revenue (decrease liability)
        line_vals.append({
            'move_id': move.id,
            'account_id': self.deferred_revenue_account_id.id,
            'partner_id': self.partner_id.id,
            'name': f'Revenue Recognition - {self.subscription_id.name}',
            'debit': self.recognition_amount,
            'credit': 0.0,
        })
        
        # Credit: Revenue (increase income)
        line_vals.append({
            'move_id': move.id,
            'account_id': self.revenue_account_id.id,
            'partner_id': self.partner_id.id,
            'name': f'Revenue Recognition - {self.subscription_id.name}',
            'debit': 0.0,
            'credit': self.recognition_amount,
        })
        
        # Create the lines
        self.env['ams.account.move.line'].create(line_vals)
        
        # Post the journal entry
        move.action_post()
        
        # Link the journal entry
        self.move_id = move.id
        
        return move
    
    # View Actions
    def action_view_journal_entry(self):
        """View the related journal entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError("No journal entry has been created yet.")
        
        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }
    
    def action_view_subscription(self):
        """View the related subscription"""
        self.ensure_one()
        return {
            'name': 'Subscription',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
        }
    
    @api.model
    def create_monthly_recognition_entries(self):
        """Automated method to create monthly recognition entries"""
        # This method would be called by cron jobs
        today = fields.Date.today()
        
        # Find active subscriptions that need recognition
        subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            # Add more filters as needed
        ])
        
        created_count = 0
        for subscription in subscriptions:
            try:
                # Check if recognition entry already exists for current month
                existing_entry = self.search([
                    ('subscription_id', '=', subscription.id),
                    ('recognition_date', '>=', today.replace(day=1)),
                    ('recognition_date', '<', (today.replace(day=1) + relativedelta(months=1))),
                ], limit=1)
                
                if not existing_entry:
                    # Create recognition entry (simplified)
                    self._create_automated_entry(subscription, today)
                    created_count += 1
                    
            except Exception as e:
                # Log error but continue processing
                subscription.message_post(
                    body=f"Failed to create revenue recognition: {str(e)}",
                    message_type='notification'
                )
        
        return created_count
    
    def _create_automated_entry(self, subscription, date):
        """Create automated recognition entry for subscription"""
        # This is a simplified version - would need more logic in real implementation
        accounting_record = self.env['ams.subscription.accounting'].search([
            ('subscription_id', '=', subscription.id)
        ], limit=1)
        
        if not accounting_record:
            return False
        
        # Calculate recognition amount (simplified)
        total_amount = 0.0
        if hasattr(subscription, 'total_invoiced_amount'):
            total_amount = subscription.total_invoiced_amount
        
        monthly_amount = total_amount / 12  # Simplified calculation
        
        # Create the entry
        entry_vals = {
            'subscription_id': subscription.id,
            'recognition_date': date,
            'period_start': date.replace(day=1),
            'period_end': (date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)),
            'total_subscription_amount': total_amount,
            'recognition_amount': monthly_amount,
            'recognition_method': 'monthly',
            'revenue_account_id': accounting_record.revenue_account_id.id,
            'deferred_revenue_account_id': accounting_record.deferred_revenue_account_id.id,
            'journal_id': accounting_record.journal_id.id,
            'is_automated': True,
            'auto_post': accounting_record.auto_post_entries,
        }
        
        entry = self.create(entry_vals)
        
        # Auto-confirm and post if configured
        if accounting_record.auto_post_entries:
            entry.action_confirm()
            if entry.state == 'confirmed':
                entry.action_post()
        
        return entry


# Revenue Recognition Schedule Model
class AMSRevenueRecognitionSchedule(models.Model):
    """Revenue Recognition Schedules for automated processing"""
    _name = 'ams.revenue.recognition.schedule'
    _description = 'AMS Revenue Recognition Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=True, readonly=True, default='/')
    
    subscription_id = fields.Many2one('ams.subscription', string='Subscription', required=True)
    partner_id = fields.Many2one('res.partner', related='subscription_id.partner_id', store=True, readonly=True)
    product_id = fields.Many2one('product.template', related='subscription_id.product_id', store=True, readonly=True)
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    
    total_amount = fields.Float(string='Total Amount', required=True, digits='Account')
    recognized_amount = fields.Float(string='Recognized Amount', compute='_compute_amounts', store=True)
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_amounts', store=True)
    recognition_percentage = fields.Float(string='Recognition %', compute='_compute_amounts', store=True)
    
    recognition_method = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], required=True, default='monthly')
    
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], required=True, default='monthly')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('complete', 'Complete'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    
    auto_create_entries = fields.Boolean(string='Auto Create Entries', default=True)
    auto_post_entries = fields.Boolean(string='Auto Post Entries', default=True)
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    
    # Configuration
    revenue_account_id = fields.Many2one('ams.account.account', string='Revenue Account', required=True)
    deferred_revenue_account_id = fields.Many2one('ams.account.account', string='Deferred Revenue Account', required=True)
    journal_id = fields.Many2one('ams.account.journal', string='Journal', required=True)
    
    # Progress tracking
    schedule_line_count = fields.Integer(string='Schedule Lines', compute='_compute_line_count')
    completed_lines = fields.Integer(string='Completed Lines', compute='_compute_line_count')
    recognition_entry_count = fields.Integer(string='Recognition Entries', compute='_compute_entry_count')
    
    next_recognition_date = fields.Date(string='Next Recognition Date', compute='_compute_next_date')
    last_recognition_date = fields.Date(string='Last Recognition Date', compute='_compute_last_date')
    
    # Processing
    last_processed_date = fields.Date(string='Last Processed Date')
    processing_log = fields.Html(string='Processing Log')
    
    # History
    activated_date = fields.Datetime(string='Activated Date')
    activated_by = fields.Many2one('res.users', string='Activated By')
    completed_date = fields.Datetime(string='Completed Date')
    completed_by = fields.Many2one('res.users', string='Completed By')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.revenue.recognition.schedule') or '/'
        return super().create(vals_list)
    
    @api.depends('total_amount')  # Simplified - would need actual recognition entries
    def _compute_amounts(self):
        for schedule in self:
            schedule.recognized_amount = 0.0
            schedule.remaining_amount = schedule.total_amount
            schedule.recognition_percentage = 0.0
    
    def _compute_line_count(self):
        for schedule in self:
            schedule.schedule_line_count = 0
            schedule.completed_lines = 0
    
    def _compute_entry_count(self):
        for schedule in self:
            schedule.recognition_entry_count = 0
    
    def _compute_next_date(self):
        for schedule in self:
            schedule.next_recognition_date = False
    
    def _compute_last_date(self):
        for schedule in self:
            schedule.last_recognition_date = False
    
    def action_activate(self):
        """Activate the schedule"""
        self.ensure_one()
        self.write({
            'state': 'active',
            'activated_date': fields.Datetime.now(),
            'activated_by': self.env.user.id,
        })
    
    def action_complete(self):
        """Mark schedule as complete"""
        self.ensure_one()
        self.write({
            'state': 'complete',
            'completed_date': fields.Datetime.now(),
            'completed_by': self.env.user.id,
        })


# Additional models for reconciliation
class AMSAccountFullReconcile(models.Model):
    """Full Reconciliation"""
    _name = 'ams.account.full.reconcile'
    _description = 'Full Reconciliation'
    
    name = fields.Char(string='Name', required=True)
    reconciled_line_ids = fields.One2many('ams.account.move.line', 'full_reconcile_id', string='Reconciled Lines')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)


class AMSAccountPartialReconcile(models.Model):
    """Partial Reconciliation"""
    _name = 'ams.account.partial.reconcile'
    _description = 'Partial Reconciliation'
    
    debit_move_id = fields.Many2one('ams.account.move.line', required=True, index=True)
    credit_move_id = fields.Many2one('ams.account.move.line', required=True, index=True)
    amount = fields.Float(required=True, digits='Account')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)