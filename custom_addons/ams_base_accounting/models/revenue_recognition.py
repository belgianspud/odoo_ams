# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from calendar import monthrange

class RevenueRecognition(models.Model):
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition'
    _order = 'recognition_date desc, subscription_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Reference',
        required=True,
        default='New',
        copy=False,
        tracking=True
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    partner_id = fields.Many2one(
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        related='subscription_id.product_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    # Recognition period
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when revenue should be recognized'
    )
    
    period_start = fields.Date(
        string='Period Start',
        required=True,
        tracking=True,
        help='Start date of the revenue recognition period'
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True,
        tracking=True,
        help='End date of the revenue recognition period'
    )
    
    # Amounts
    total_subscription_amount = fields.Float(
        string='Total Subscription Amount',
        required=True,
        digits='Account',
        help='Total amount paid for the subscription'
    )
    
    recognition_amount = fields.Float(
        string='Recognition Amount',
        required=True,
        digits='Account',
        tracking=True,
        help='Amount to be recognized in this period'
    )
    
    remaining_amount = fields.Float(
        string='Remaining Amount',
        compute='_compute_remaining_amount',
        store=True,
        digits='Account',
        help='Amount remaining to be recognized'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    
    # Journal entry
    move_id = fields.Many2one(
        'ams.account.move',
        string='Journal Entry',
        readonly=True,
        copy=False,
        help='Journal entry created for this revenue recognition'
    )
    
    journal_id = fields.Many2one(
        'ams.account.journal',
        string='Journal',
        help='Journal used for revenue recognition entries'
    )
    
    # Recognition method
    recognition_method = fields.Selection([
        ('monthly', 'Monthly Recognition'),
        ('daily', 'Daily Recognition'),
        ('period_end', 'End of Period'),
        ('custom', 'Custom Amount'),
    ], string='Recognition Method', required=True, default='monthly')
    
    # Automation flags
    auto_post = fields.Boolean(
        string='Auto Post',
        default=True,
        help='Automatically post journal entry when confirmed'
    )
    
    is_automated = fields.Boolean(
        string='Automated Entry',
        default=False,
        help='This entry was created automatically by the system'
    )
    
    # Related recognition entries
    parent_recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Parent Recognition',
        help='Parent recognition record for split recognitions'
    )
    
    child_recognition_ids = fields.One2many(
        'ams.revenue.recognition',
        'parent_recognition_id',
        string='Child Recognitions'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.depends('total_subscription_amount')
    def _compute_remaining_amount(self):
        """Compute remaining amount to be recognized"""
        for recognition in self:
            if recognition.subscription_id:
                # Sum all posted recognition amounts for this subscription
                posted_recognitions = self.search([
                    ('subscription_id', '=', recognition.subscription_id.id),
                    ('state', '=', 'posted'),
                    ('id', '!=', recognition.id)
                ])
                
                total_recognized = sum(posted_recognitions.mapped('recognition_amount'))
                recognition.remaining_amount = recognition.total_subscription_amount - total_recognized - recognition.recognition_amount
            else:
                recognition.remaining_amount = 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set sequence number"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.revenue.recognition') or 'REV/001'
        
        return super().create(vals_list)
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Set defaults when subscription changes"""
        if self.subscription_id:
            # Set total subscription amount from subscription
            if self.subscription_id.product_id:
                self.total_subscription_amount = self.subscription_id.product_id.list_price
            
            # Set default journal
            if not self.journal_id:
                self.journal_id = self.env['ams.account.journal'].get_revenue_recognition_journal()
    
    @api.onchange('recognition_method', 'period_start', 'period_end', 'total_subscription_amount')
    def _onchange_recognition_method(self):
        """Calculate recognition amount based on method"""
        if not all([self.recognition_method, self.period_start, self.period_end, self.total_subscription_amount]):
            return
        
        if self.recognition_method == 'monthly':
            # Calculate monthly amount
            self.recognition_amount = self._calculate_monthly_amount()
        elif self.recognition_method == 'daily':
            # Calculate daily amount for the period
            days_in_period = (self.period_end - self.period_start).days + 1
            if self.subscription_id and self.subscription_id.tier_id:
                total_days = self._get_subscription_total_days()
                if total_days > 0:
                    daily_rate = self.total_subscription_amount / total_days
                    self.recognition_amount = daily_rate * days_in_period
        elif self.recognition_method == 'period_end':
            # Recognize full amount at period end
            self.recognition_amount = self.total_subscription_amount
    
    def _calculate_monthly_amount(self):
        """Calculate monthly recognition amount"""
        if not self.subscription_id or not self.subscription_id.subscription_period:
            return 0.0
        
        period = self.subscription_id.subscription_period
        
        if period == 'monthly':
            return self.total_subscription_amount
        elif period == 'quarterly':
            return self.total_subscription_amount / 3
        elif period == 'semi_annual':
            return self.total_subscription_amount / 6
        elif period == 'annual':
            return self.total_subscription_amount / 12
        else:
            return 0.0
    
    def _get_subscription_total_days(self):
        """Get total days in subscription period"""
        if not self.subscription_id:
            return 365
        
        start_date = self.subscription_id.start_date
        end_date = self.subscription_id.paid_through_date
        
        if start_date and end_date:
            return (end_date - start_date).days + 1
        
        # Default based on subscription period
        period = self.subscription_id.subscription_period
        if period == 'monthly':
            return 30
        elif period == 'quarterly':
            return 90
        elif period == 'semi_annual':
            return 180
        elif period == 'annual':
            return 365
        else:
            return 365
    
    def action_confirm(self):
        """Confirm revenue recognition"""
        for recognition in self:
            if recognition.state != 'draft':
                raise UserError(f'Only draft recognitions can be confirmed. {recognition.name} is {recognition.state}')
            
            # Validate amounts
            if recognition.recognition_amount <= 0:
                raise UserError(f'Recognition amount must be positive for {recognition.name}')
            
            # Create journal entry
            recognition._create_journal_entry()
            
            recognition.state = 'confirmed'
            recognition.message_post(body='Revenue recognition confirmed')
    
    def action_post(self):
        """Post revenue recognition (post journal entry)"""
        for recognition in self:
            if recognition.state != 'confirmed':
                raise UserError(f'Only confirmed recognitions can be posted. {recognition.name} is {recognition.state}')
            
            if not recognition.move_id:
                raise UserError(f'No journal entry found for {recognition.name}')
            
            # Post the journal entry
            recognition.move_id.action_post()
            
            recognition.state = 'posted'
            recognition.message_post(body='Revenue recognition posted')
    
    def action_cancel(self):
        """Cancel revenue recognition"""
        for recognition in self:
            if recognition.state == 'posted':
                raise UserError(f'Cannot cancel posted revenue recognition {recognition.name}')
            
            if recognition.move_id:
                recognition.move_id.action_cancel()
            
            recognition.state = 'cancelled'
            recognition.message_post(body='Revenue recognition cancelled')
    
    def action_reset_to_draft(self):
        """Reset to draft state"""
        for recognition in self:
            if recognition.state not in ['confirmed', 'cancelled']:
                raise UserError(f'Cannot reset {recognition.name} to draft from state {recognition.state}')
            
            if recognition.move_id:
                recognition.move_id.action_draft()
            
            recognition.state = 'draft'
            recognition.message_post(body='Revenue recognition reset to draft')
    
    def _create_journal_entry(self):
        """Create journal entry for revenue recognition"""
        self.ensure_one()
        
        if self.move_id:
            raise UserError(f'Journal entry already exists for {self.name}')
        
        # Get accounts
        product = self.subscription_id.product_id.product_tmpl_id
        deferred_revenue_account = product.get_deferred_revenue_account()
        revenue_account = product.get_revenue_account()
        
        if not deferred_revenue_account or not revenue_account:
            raise UserError(f'Revenue accounts not configured for product {product.name}')
        
        # Get journal
        journal = self.journal_id or self.env['ams.account.journal'].get_revenue_recognition_journal()
        if not journal:
            raise UserError('No revenue recognition journal configured')
        
        # Create description
        description = f'Revenue recognition - {self.subscription_id.name} ({self.period_start} to {self.period_end})'
        
        # Create journal entry
        move_vals = {
            'journal_id': journal.id,
            'date': self.recognition_date,
            'ref': description,
            'move_type': 'revenue_recognition',
            'subscription_id': self.subscription_id.id,
            'revenue_recognition_id': self.id,
            'partner_id': self.partner_id.id,
            'ams_category': self.subscription_id.subscription_type if self.subscription_id.subscription_type in ['membership', 'chapter', 'publication'] else 'general',
            'auto_post': self.auto_post,
            'line_ids': [
                # Debit Deferred Revenue (decrease liability)
                (0, 0, {
                    'account_id': deferred_revenue_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.recognition_amount,
                    'credit': 0.0,
                    'name': description,
                    'subscription_id': self.subscription_id.id,
                    'revenue_recognition_id': self.id,
                }),
                # Credit Revenue (increase income)
                (0, 0, {
                    'account_id': revenue_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.recognition_amount,
                    'name': description,
                    'subscription_id': self.subscription_id.id,
                    'revenue_recognition_id': self.id,
                }),
            ]
        }
        
        move = self.env['ams.account.move'].create(move_vals)
        self.move_id = move.id
        
        return move
    
    def action_view_journal_entry(self):
        """View related journal entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError('No journal entry found')
        
        return {
            'name': 'Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def create_monthly_recognition_entries(self, date_to_process=None):
        """Create monthly revenue recognition entries for all active subscriptions"""
        if not date_to_process:
            date_to_process = fields.Date.today()
        
        # Get all active subscriptions that need revenue recognition
        subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('product_id.product_tmpl_id.revenue_recognition_method', '=', 'subscription'),
            ('start_date', '<=', date_to_process),
            ('paid_through_date', '>=', date_to_process),
        ])
        
        created_recognitions = self.env['ams.revenue.recognition']
        
        for subscription in subscriptions:
            # Check if recognition already exists for this month
            year = date_to_process.year
            month = date_to_process.month
            
            period_start = date(year, month, 1)
            period_end = date(year, month, monthrange(year, month)[1])
            
            existing = self.search([
                ('subscription_id', '=', subscription.id),
                ('period_start', '=', period_start),
                ('period_end', '=', period_end),
                ('state', '!=', 'cancelled')
            ])
            
            if existing:
                continue  # Skip if already exists
            
            # Calculate recognition amount
            product = subscription.product_id.product_tmpl_id
            total_amount = subscription.product_id.list_price
            
            # Get monthly amount based on subscription period
            if subscription.subscription_period == 'monthly':
                recognition_amount = total_amount
            elif subscription.subscription_period == 'quarterly':
                recognition_amount = total_amount / 3
            elif subscription.subscription_period == 'semi_annual':
                recognition_amount = total_amount / 6
            elif subscription.subscription_period == 'annual':
                recognition_amount = total_amount / 12
            else:
                continue  # Skip unknown periods
            
            # Create recognition entry
            recognition_vals = {
                'subscription_id': subscription.id,
                'recognition_date': period_end,
                'period_start': period_start,
                'period_end': period_end,
                'total_subscription_amount': total_amount,
                'recognition_amount': recognition_amount,
                'recognition_method': 'monthly',
                'auto_post': True,
                'is_automated': True,
                'journal_id': self.env['ams.account.journal'].get_revenue_recognition_journal().id,
            }
            
            recognition = self.create(recognition_vals)
            created_recognitions |= recognition
            
            # Auto-confirm and post if configured
            try:
                recognition.action_confirm()
                if recognition.auto_post:
                    recognition.action_post()
            except Exception as e:
                recognition.message_post(body=f'Auto-processing failed: {str(e)}')
        
        return created_recognitions
    
    @api.model
    def _cron_create_monthly_recognitions(self):
        """Cron job to create monthly revenue recognition entries"""
        try:
            recognitions = self.create_monthly_recognition_entries()
            if recognitions:
                self.env['mail.mail'].create({
                    'subject': f'Revenue Recognition: {len(recognitions)} entries created',
                    'body_html': f'<p>Created {len(recognitions)} revenue recognition entries for {fields.Date.today()}</p>',
                    'email_to': self.env.user.partner_id.email,
                }).send()
        except Exception as e:
            # Log error and send notification
            self.env['mail.mail'].create({
                'subject': 'Revenue Recognition Cron Failed',
                'body_html': f'<p>Revenue recognition cron job failed: {str(e)}</p>',
                'email_to': self.env.user.partner_id.email,
            }).send()
    
    def name_get(self):
        """Display format for revenue recognition"""
        result = []
        for recognition in self:
            name = f'{recognition.name}'
            if recognition.subscription_id:
                name += f' - {recognition.subscription_id.name}'
            if recognition.period_start and recognition.period_end:
                name += f' ({recognition.period_start} to {recognition.period_end})'
            result.append((recognition.id, name))
        return result


class RevenueRecognitionSchedule(models.Model):
    """Revenue recognition schedule for subscriptions"""
    _name = 'ams.revenue.recognition.schedule'
    _description = 'Revenue Recognition Schedule'
    _order = 'subscription_id, period_start'
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )
    
    total_amount = fields.Float(
        string='Total Amount',
        required=True,
        digits='Account'
    )
    
    schedule_line_ids = fields.One2many(
        'ams.revenue.recognition.schedule.line',
        'schedule_id',
        string='Schedule Lines'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    
    def generate_schedule(self):
        """Generate revenue recognition schedule"""
        self.ensure_one()
        
        # Clear existing lines
        self.schedule_line_ids.unlink()
        
        subscription = self.subscription_id
        if not subscription.start_date or not subscription.paid_through_date:
            raise UserError('Subscription must have start and end dates')
        
        # Calculate periods based on subscription period
        periods = self._calculate_periods()
        
        lines_vals = []
        for period_start, period_end, amount in periods:
            lines_vals.append({
                'schedule_id': self.id,
                'period_start': period_start,
                'period_end': period_end,
                'amount': amount,
                'recognition_date': period_end,
            })
        
        self.env['ams.revenue.recognition.schedule.line'].create(lines_vals)
        self.state = 'active'
    
    def _calculate_periods(self):
        """Calculate recognition periods"""
        subscription = self.subscription_id
        start_date = subscription.start_date
        end_date = subscription.paid_through_date
        period_type = subscription.subscription_period
        
        periods = []
        current_date = start_date
        
        while current_date <= end_date:
            if period_type == 'monthly':
                period_end = min(
                    current_date + relativedelta(months=1) - relativedelta(days=1),
                    end_date
                )
                amount = self.total_amount / 12 if subscription.subscription_period == 'annual' else self.total_amount
            elif period_type == 'quarterly':
                period_end = min(
                    current_date + relativedelta(months=3) - relativedelta(days=1),
                    end_date
                )
                amount = self.total_amount / 4 if subscription.subscription_period == 'annual' else self.total_amount / 3
            else:  # annual or other
                period_end = end_date
                amount = self.total_amount
            
            periods.append((current_date, period_end, amount))
            
            # Move to next period
            if period_type == 'monthly':
                current_date = current_date + relativedelta(months=1)
            elif period_type == 'quarterly':
                current_date = current_date + relativedelta(months=3)
            else:
                break  # Annual - only one period
        
        return periods


class RevenueRecognitionScheduleLine(models.Model):
    """Revenue recognition schedule line"""
    _name = 'ams.revenue.recognition.schedule.line'
    _description = 'Revenue Recognition Schedule Line'
    _order = 'period_start'
    
    schedule_id = fields.Many2one(
        'ams.revenue.recognition.schedule',
        string='Schedule',
        required=True,
        ondelete='cascade'
    )
    
    period_start = fields.Date(
        string='Period Start',
        required=True
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True
    )
    
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True
    )
    
    amount = fields.Float(
        string='Amount',
        required=True,
        digits='Account'
    )
    
    recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Recognition Entry',
        readonly=True
    )
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('recognized', 'Recognized'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending')
    
    def create_recognition_entry(self):
        """Create revenue recognition entry from schedule line"""
        self.ensure_one()
        
        if self.recognition_id:
            raise UserError('Recognition entry already exists')
        
        recognition_vals = {
            'subscription_id': self.schedule_id.subscription_id.id,
            'recognition_date': self.recognition_date,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'total_subscription_amount': self.schedule_id.total_amount,
            'recognition_amount': self.amount,
            'recognition_method': 'monthly',
            'auto_post': True,
        }
        
        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
        self.recognition_id = recognition.id
        self.state = 'recognized'
        
        return recognition