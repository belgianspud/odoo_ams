# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class AMSRevenueSchedule(models.Model):
    _name = 'ams.revenue.schedule'
    _description = 'AMS Revenue Recognition Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'
    
    name = fields.Char(string='Schedule Reference', required=True, default='New')
    
    # Related entities
    subscription_id = fields.Many2one('ams.subscription', string='Subscription', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='subscription_id.partner_id', store=True)
    product_id = fields.Many2one('product.template', string='Product', related='subscription_id.product_id', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')
    
    # Schedule configuration
    recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('straight_line', 'Straight Line (Monthly)'),
        ('manual', 'Manual Recognition'),
    ], string='Recognition Method', default='straight_line', required=True)
    
    # Amounts and periods
    total_amount = fields.Monetary(string='Total Amount', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    period_length = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Period Length', default='monthly')
    
    total_periods = fields.Integer(string='Total Periods', compute='_compute_total_periods', store=True)
    
    # Dates
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    next_recognition_date = fields.Date(string='Next Recognition Date', compute='_compute_next_recognition_date')
    last_processed_date = fields.Date(string='Last Processed Date')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Financial tracking
    recognized_amount = fields.Monetary(string='Recognized Amount', compute='_compute_amounts', store=True)
    deferred_amount = fields.Monetary(string='Deferred Amount', compute='_compute_amounts', store=True)
    
    # Accounts - Fixed the dependency issue
    revenue_account_id = fields.Many2one('account.account', string='Revenue Account', 
                                       compute='_compute_accounts', store=True)
    deferred_account_id = fields.Many2one('account.account', string='Deferred Account',
                                        compute='_compute_accounts', store=True)
    
    # Recognition lines
    recognition_line_ids = fields.One2many('ams.revenue.recognition', 'schedule_id', string='Recognition Lines')
    recognition_count = fields.Integer(string='Recognition Count', compute='_compute_recognition_count')
    
    @api.depends('start_date', 'end_date', 'period_length')
    def _compute_total_periods(self):
        """Calculate total number of recognition periods"""
        for schedule in self:
            if schedule.start_date and schedule.end_date:
                if schedule.period_length == 'monthly':
                    delta = relativedelta(schedule.end_date, schedule.start_date)
                    schedule.total_periods = delta.months + (delta.years * 12) + 1
                elif schedule.period_length == 'quarterly':
                    delta = relativedelta(schedule.end_date, schedule.start_date)
                    schedule.total_periods = ((delta.months + (delta.years * 12)) // 3) + 1
                elif schedule.period_length == 'annual':
                    delta = relativedelta(schedule.end_date, schedule.start_date)
                    schedule.total_periods = delta.years + 1
                else:
                    schedule.total_periods = 1
            else:
                schedule.total_periods = 0
    
    @api.depends('recognition_line_ids', 'recognition_line_ids.state')
    def _compute_next_recognition_date(self):
        """Calculate next recognition date"""
        for schedule in self:
            pending_lines = schedule.recognition_line_ids.filtered(lambda l: l.state == 'pending')
            if pending_lines:
                schedule.next_recognition_date = min(pending_lines.mapped('recognition_date'))
            else:
                schedule.next_recognition_date = False
    
    @api.depends('recognition_line_ids', 'recognition_line_ids.recognized_amount')
    def _compute_amounts(self):
        """Calculate recognized and deferred amounts"""
        for schedule in self:
            schedule.recognized_amount = sum(schedule.recognition_line_ids.mapped('recognized_amount'))
            schedule.deferred_amount = schedule.total_amount - schedule.recognized_amount
    
    # Fixed the dependency issue - removed non-existent field dependencies
    @api.depends('product_id')
    def _compute_accounts(self):
        """Compute revenue and deferred accounts"""
        for schedule in self:
            if schedule.product_id:
                # Get revenue account from product
                if hasattr(schedule.product_id, 'ams_revenue_account_id') and schedule.product_id.ams_revenue_account_id:
                    schedule.revenue_account_id = schedule.product_id.ams_revenue_account_id
                else:
                    # Fallback to default revenue account
                    revenue_account = self.env['account.account'].search([
                        ('account_type', '=', 'income'),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                    schedule.revenue_account_id = revenue_account
                
                # Get deferred account
                deferred_account = self.env['account.account'].search([
                    ('ams_account_category', '=', 'deferred_revenue'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                
                if not deferred_account:
                    deferred_account = self.env['account.account'].search([
                        ('account_type', '=', 'liability_current'),
                        ('name', 'ilike', 'deferred'),
                        ('company_id', '=', self.env.company.id)
                    ], limit=1)
                
                schedule.deferred_account_id = deferred_account
            else:
                schedule.revenue_account_id = False
                schedule.deferred_account_id = False
    
    @api.depends('recognition_line_ids')
    def _compute_recognition_count(self):
        """Count recognition lines"""
        for schedule in self:
            schedule.recognition_count = len(schedule.recognition_line_ids)
    
    @api.model
    def create(self, vals):
        """Auto-generate name and create recognition lines"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.revenue.schedule') or 'New'
        
        schedule = super().create(vals)
        
        if schedule.recognition_method == 'straight_line':
            schedule._create_recognition_lines()
        
        return schedule
    
    def _create_recognition_lines(self):
        """Create individual recognition lines"""
        self.ensure_one()
        
        if self.recognition_line_ids:
            # Lines already exist
            return
        
        if self.total_periods <= 0:
            return
        
        amount_per_period = self.total_amount / self.total_periods
        current_date = self.start_date
        
        recognition_lines = []
        
        for period in range(self.total_periods):
            # Calculate recognition date
            if self.period_length == 'monthly':
                recognition_date = current_date + relativedelta(months=period)
            elif self.period_length == 'quarterly':
                recognition_date = current_date + relativedelta(months=period * 3)
            elif self.period_length == 'annual':
                recognition_date = current_date + relativedelta(years=period)
            else:
                recognition_date = current_date
            
            # Ensure we don't go past end date
            if recognition_date > self.end_date:
                recognition_date = self.end_date
            
            # Description for this period
            if self.period_length == 'monthly':
                description = f"Month {period + 1} of {self.total_periods} - {recognition_date.strftime('%B %Y')}"
            else:
                description = f"Period {period + 1} of {self.total_periods} - {recognition_date.strftime('%B %Y')}"
            
            recognition_lines.append((0, 0, {
                'schedule_id': self.id,
                'subscription_id': self.subscription_id.id,
                'product_id': self.product_id.id,
                'partner_id': self.partner_id.id,
                'invoice_id': self.invoice_id.id if self.invoice_id else False,
                'recognition_date': recognition_date,
                'scheduled_amount': amount_per_period,
                'description': description,
                'revenue_account_id': self.revenue_account_id.id if self.revenue_account_id else False,
                'deferred_account_id': self.deferred_account_id.id if self.deferred_account_id else False,
            }))
        
        self.recognition_line_ids = recognition_lines
    
    def action_activate(self):
        """Activate the revenue schedule"""
        self.ensure_one()
        if not self.recognition_line_ids and self.recognition_method == 'straight_line':
            self._create_recognition_lines()
        self.state = 'active'
    
    def action_cancel(self):
        """Cancel the revenue schedule"""
        self.ensure_one()
        # Cancel any pending recognition lines
        self.recognition_line_ids.filtered(lambda l: l.state == 'pending').write({'state': 'cancelled'})
        self.state = 'cancelled'
    
    def process_due_recognitions(self):
        """Process recognition lines that are due"""
        self.ensure_one()
        due_lines = self.recognition_line_ids.filtered(
            lambda l: l.state == 'pending' and l.recognition_date <= fields.Date.today()
        )
        
        for line in due_lines:
            line.action_recognize_revenue()
        
        # Check if schedule is completed
        if all(line.state in ['recognized', 'cancelled'] for line in self.recognition_line_ids):
            self.state = 'completed'
    
    def action_view_recognition_entries(self):
        """View recognition entries for this schedule"""
        return {
            'name': f'Recognition Entries - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
        }