from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSPaymentPlan(models.Model):
    """
    Payment plan model for members with outstanding balances
    """
    _name = 'ams.payment.plan'
    _description = 'AMS Payment Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'plan_number'

    # ========================
    # BASIC INFORMATION
    # ========================
    
    plan_number = fields.Char('Plan Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    name = fields.Char('Plan Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'Member', required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
        related='company_id.currency_id', readonly=True)
    
    # ========================
    # FINANCIAL CONFIGURATION
    # ========================
    
    # Amount Details
    total_amount = fields.Float('Total Amount', required=True, tracking=True,
        help="Total amount to be paid through the payment plan")
    down_payment = fields.Float('Down Payment', default=0.0, tracking=True,
        help="Initial payment amount")
    remaining_amount = fields.Float('Remaining Amount', 
        compute='_compute_amounts', store=True,
        help="Amount remaining to be paid in installments")
    
    # Payment Schedule Configuration
    number_of_payments = fields.Integer('Number of Payments', required=True, 
        default=6, tracking=True,
        help="Number of installment payments")
    payment_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('custom', 'Custom')
    ], string='Payment Frequency', default='monthly', required=True, tracking=True)
    
    custom_frequency_days = fields.Integer('Custom Frequency (Days)', default=30,
        help="Number of days between payments for custom frequency")
    
    # Payment Amount Calculation
    payment_amount_type = fields.Selection([
        ('equal', 'Equal Installments'),
        ('graduated', 'Graduated Payments'),
        ('custom', 'Custom Amounts')
    ], string='Payment Amount Type', default='equal', tracking=True)
    
    # Interest and Fees
    interest_rate = fields.Float('Interest Rate (%)', default=0.0,
        help="Annual interest rate for the payment plan")
    setup_fee = fields.Float('Setup Fee', default=0.0,
        help="One-time setup fee for the payment plan")
    late_fee_amount = fields.Float('Late Fee Amount', default=25.0,
        help="Fee charged for late payments")
    grace_period_days = fields.Integer('Grace Period (Days)', default=5,
        help="Grace period before late fees apply")
    
    # ========================
    # DATES AND SCHEDULE
    # ========================
    
    # Date Management
    start_date = fields.Date('Start Date', required=True, 
        default=fields.Date.today, tracking=True)
    first_payment_date = fields.Date('First Payment Date', required=True,
        tracking=True)
    end_date = fields.Date('End Date', compute='_compute_end_date', store=True)
    
    # Auto-Payment Configuration
    auto_payment_enabled = fields.Boolean('Auto Payment Enabled', default=False,
        help="Automatically charge payments when due")
    payment_method_id = fields.Many2one('ams.saved.payment.method', 
        'Payment Method', help="Saved payment method for auto-payments")
    
    # ========================
    # STATUS AND TRACKING
    # ========================
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Status', default='draft', tracking=True)
    
    # Progress Tracking
    payments_made = fields.Integer('Payments Made', 
        compute='_compute_progress', store=True)
    amount_paid = fields.Float('Amount Paid', 
        compute='_compute_progress', store=True)
    amount_remaining = fields.Float('Amount Remaining', 
        compute='_compute_progress', store=True)
    completion_percentage = fields.Float('Completion %', 
        compute='_compute_progress', store=True)
    
    # Default Tracking
    missed_payments = fields.Integer('Missed Payments', default=0)
    consecutive_missed = fields.Integer('Consecutive Missed', default=0)
    last_payment_date = fields.Date('Last Payment Date')
    next_payment_date = fields.Date('Next Payment Date')
    
    # ========================
    # RELATIONSHIPS
    # ========================
    
    # Related Records
    payment_line_ids = fields.One2many('ams.payment.plan.line', 
        'payment_plan_id', 'Payment Schedule')
    payment_ids = fields.One2many('account.payment', 'payment_plan_id', 
        'Payments Made')
    invoice_ids = fields.Many2many('account.move', 'payment_plan_invoice_rel',
        'plan_id', 'invoice_id', 'Related Invoices',
        help="Invoices included in this payment plan")
    
    # Approval and Authorization
    approved_by = fields.Many2one('res.users', 'Approved By')
    approval_date = fields.Datetime('Approval Date')
    approval_notes = fields.Text('Approval Notes')
    
    # ========================
    # TERMS AND CONDITIONS
    # ========================
    
    # Agreement Terms
    terms_and_conditions = fields.Html('Terms and Conditions')
    member_agreed = fields.Boolean('Member Agreed to Terms', default=False)
    agreement_date = fields.Datetime('Agreement Date')
    agreement_ip_address = fields.Char('Agreement IP Address')
    
    # Contact Information
    contact_preference = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mail', 'Postal Mail'),
        ('sms', 'SMS')
    ], string='Contact Preference', default='email')
    
    reminder_days_before = fields.Integer('Reminder Days Before', default=3,
        help="Days before payment due to send reminder")
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    @api.depends('total_amount', 'down_payment')
    def _compute_amounts(self):
        for plan in self:
            plan.remaining_amount = plan.total_amount - plan.down_payment
    
    @api.depends('first_payment_date', 'number_of_payments', 'payment_frequency')
    def _compute_end_date(self):
        for plan in self:
            if plan.first_payment_date and plan.number_of_payments > 0:
                if plan.payment_frequency == 'weekly':
                    plan.end_date = plan.first_payment_date + timedelta(
                        weeks=plan.number_of_payments - 1)
                elif plan.payment_frequency == 'biweekly':
                    plan.end_date = plan.first_payment_date + timedelta(
                        weeks=(plan.number_of_payments - 1) * 2)
                elif plan.payment_frequency == 'monthly':
                    plan.end_date = plan.first_payment_date + relativedelta(
                        months=plan.number_of_payments - 1)
                elif plan.payment_frequency == 'quarterly':
                    plan.end_date = plan.first_payment_date + relativedelta(
                        months=(plan.number_of_payments - 1) * 3)
                elif plan.payment_frequency == 'custom':
                    plan.end_date = plan.first_payment_date + timedelta(
                        days=plan.custom_frequency_days * (plan.number_of_payments - 1))
                else:
                    plan.end_date = False
            else:
                plan.end_date = False
    
    @api.depends('payment_line_ids', 'payment_line_ids.state', 'payment_line_ids.amount')
    def _compute_progress(self):
        for plan in self:
            completed_lines = plan.payment_line_ids.filtered(
                lambda l: l.state == 'paid')
            
            plan.payments_made = len(completed_lines)
            plan.amount_paid = sum(completed_lines.mapped('amount'))
            plan.amount_remaining = plan.total_amount - plan.amount_paid
            
            if plan.total_amount > 0:
                plan.completion_percentage = (plan.amount_paid / plan.total_amount) * 100
            else:
                plan.completion_percentage = 0.0
    
    # ========================
    # CRUD OPERATIONS
    # ========================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('plan_number', _('New')) == _('New'):
                vals['plan_number'] = self.env['ir.sequence'].next_by_code(
                    'ams.payment.plan') or _('New')
        
        plans = super().create(vals_list)
        
        for plan in plans:
            # Auto-generate plan name if not provided
            if not plan.name:
                plan.name = f"Payment Plan - {plan.partner_id.name}"
        
        return plans
    
    # ========================
    # BUSINESS METHODS
    # ========================
    
    def action_activate(self):
        """Activate the payment plan and generate schedule"""
        for plan in self:
            if plan.state != 'draft':
                raise UserError(_('Only draft payment plans can be activated.'))
            
            # Validate configuration
            plan._validate_payment_plan()
            
            # Generate payment schedule
            plan._generate_payment_schedule()
            
            # Update partner payment plan reference
            plan.partner_id.write({
                'has_payment_plan': True,
                'payment_plan_id': plan.id
            })
            
            plan.state = 'active'
            plan.message_post(body=_('Payment plan activated.'))
    
    def action_suspend(self):
        """Suspend the payment plan"""
        for plan in self:
            if plan.state != 'active':
                raise UserError(_('Only active payment plans can be suspended.'))
            
            plan.state = 'suspended'
            plan.message_post(body=_('Payment plan suspended.'))
    
    def action_resume(self):
        """Resume suspended payment plan"""
        for plan in self:
            if plan.state != 'suspended':
                raise UserError(_('Only suspended payment plans can be resumed.'))
            
            plan.state = 'active'
            plan._reschedule_remaining_payments()
            plan.message_post(body=_('Payment plan resumed.'))
    
    def action_cancel(self):
        """Cancel the payment plan"""
        for plan in self:
            if plan.state in ['completed', 'cancelled']:
                raise UserError(_('Cannot cancel completed or already cancelled plans.'))
            
            # Cancel pending payment lines
            pending_lines = plan.payment_line_ids.filtered(
                lambda l: l.state == 'pending')
            pending_lines.write({'state': 'cancelled'})
            
            plan.state = 'cancelled'
            plan.partner_id.write({
                'has_payment_plan': False,
                'payment_plan_id': False
            })
            
            plan.message_post(body=_('Payment plan cancelled.'))
    
    def action_complete(self):
        """Mark payment plan as completed"""
        for plan in self:
            if plan.amount_remaining > 0.01:  # Allow for rounding
                raise UserError(_('Cannot complete plan with remaining balance.'))
            
            plan.state = 'completed'
            plan.partner_id.write({
                'has_payment_plan': False,
                'payment_plan_id': False
            })
            
            plan.message_post(body=_('Payment plan completed successfully.'))
    
    def action_default(self):
        """Mark payment plan as defaulted"""
        for plan in self:
            plan.state = 'defaulted'
            plan.message_post(body=_('Payment plan marked as defaulted.'))
            
            # Create activity for collections
            plan.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Payment Plan Default: {plan.plan_number}',
                note=f'Payment plan has been marked as defaulted. '
                     f'Missed payments: {plan.missed_payments}',
                user_id=self.env.ref('base.group_account_manager').users[0].id 
                       if self.env.ref('base.group_account_manager').users 
                       else self.env.user.id
            )
    
    def _validate_payment_plan(self):
        """Validate payment plan configuration"""
        if self.total_amount <= 0:
            raise UserError(_('Total amount must be greater than zero.'))
        
        if self.down_payment < 0:
            raise UserError(_('Down payment cannot be negative.'))
        
        if self.down_payment >= self.total_amount:
            raise UserError(_('Down payment cannot exceed total amount.'))
        
        if self.number_of_payments <= 0:
            raise UserError(_('Number of payments must be greater than zero.'))
        
        if self.remaining_amount <= 0:
            raise UserError(_('Remaining amount must be greater than zero.'))
        
        if self.payment_frequency == 'custom' and self.custom_frequency_days <= 0:
            raise UserError(_('Custom frequency days must be greater than zero.'))
        
        if self.interest_rate < 0:
            raise UserError(_('Interest rate cannot be negative.'))
    
    def _generate_payment_schedule(self):
        """Generate payment schedule lines"""
        # Clear existing lines
        self.payment_line_ids.unlink()
        
        if self.remaining_amount <= 0:
            return
        
        # Calculate payment amounts
        payment_amounts = self._calculate_payment_amounts()
        
        # Generate schedule
        current_date = self.first_payment_date
        
        for i, amount in enumerate(payment_amounts):
            line_vals = {
                'payment_plan_id': self.id,
                'sequence': i + 1,
                'due_date': current_date,
                'amount': amount,
                'principal_amount': self._calculate_principal_amount(amount, i),
                'interest_amount': self._calculate_interest_amount(amount, i),
                'state': 'pending'
            }
            
            self.env['ams.payment.plan.line'].create(line_vals)
            
            # Calculate next payment date
            current_date = self._calculate_next_payment_date(current_date)
        
        # Update next payment date
        first_pending = self.payment_line_ids.filtered(
            lambda l: l.state == 'pending').sorted('due_date')
        if first_pending:
            self.next_payment_date = first_pending[0].due_date
    
    def _calculate_payment_amounts(self):
        """Calculate payment amounts based on type"""
        if self.payment_amount_type == 'equal':
            return self._calculate_equal_payments()
        elif self.payment_amount_type == 'graduated':
            return self._calculate_graduated_payments()
        elif self.payment_amount_type == 'custom':
            return self._calculate_custom_payments()
        else:
            return self._calculate_equal_payments()
    
    def _calculate_equal_payments(self):
        """Calculate equal payment amounts"""
        if self.interest_rate > 0:
            # Calculate payments with interest
            monthly_rate = self.interest_rate / 100 / 12
            payment_amount = (self.remaining_amount * monthly_rate * 
                            (1 + monthly_rate) ** self.number_of_payments) / \
                           ((1 + monthly_rate) ** self.number_of_payments - 1)
        else:
            # Simple equal payments without interest
            payment_amount = self.remaining_amount / self.number_of_payments
        
        return [payment_amount] * self.number_of_payments
    
    def _calculate_graduated_payments(self):
        """Calculate graduated payment amounts (increasing over time)"""
        base_payment = self.remaining_amount / (self.number_of_payments * 1.5)
        increment = base_payment / self.number_of_payments
        
        payments = []
        for i in range(self.number_of_payments):
            payment = base_payment + (increment * i)
            payments.append(payment)
        
        # Adjust last payment to ensure total equals remaining amount
        total_calculated = sum(payments)
        if total_calculated != self.remaining_amount:
            payments[-1] += (self.remaining_amount - total_calculated)
        
        return payments
    
    def _calculate_custom_payments(self):
        """Calculate custom payment amounts (to be implemented per business rules)"""
        # Placeholder for custom payment calculation logic
        return self._calculate_equal_payments()
    
    def _calculate_principal_amount(self, payment_amount, payment_index):
        """Calculate principal portion of payment"""
        if self.interest_rate <= 0:
            return payment_amount
        
        # Simplified calculation - would need more complex logic for accurate amortization
        remaining_balance = self.remaining_amount - (payment_amount * payment_index)
        interest_portion = remaining_balance * (self.interest_rate / 100 / 12)
        return payment_amount - interest_portion
    
    def _calculate_interest_amount(self, payment_amount, payment_index):
        """Calculate interest portion of payment"""
        if self.interest_rate <= 0:
            return 0.0
        
        remaining_balance = self.remaining_amount - (payment_amount * payment_index)
        return remaining_balance * (self.interest_rate / 100 / 12)
    
    def _calculate_next_payment_date(self, current_date):
        """Calculate next payment date based on frequency"""
        if self.payment_frequency == 'weekly':
            return current_date + timedelta(weeks=1)
        elif self.payment_frequency == 'biweekly':
            return current_date + timedelta(weeks=2)
        elif self.payment_frequency == 'monthly':
            return current_date + relativedelta(months=1)
        elif self.payment_frequency == 'quarterly':
            return current_date + relativedelta(months=3)
        elif self.payment_frequency == 'custom':
            return current_date + timedelta(days=self.custom_frequency_days)
        else:
            return current_date + relativedelta(months=1)
    
    def _reschedule_remaining_payments(self):
        """Reschedule remaining payments after suspension"""
        pending_lines = self.payment_line_ids.filtered(
            lambda l: l.state == 'pending').sorted('sequence')
        
        if not pending_lines:
            return
        
        # Start from today or the original next payment date, whichever is later
        start_date = max(fields.Date.today(), self.next_payment_date or fields.Date.today())
        current_date = start_date
        
        for line in pending_lines:
            line.due_date = current_date
            current_date = self._calculate_next_payment_date(current_date)
        
        # Update next payment date
        self.next_payment_date = pending_lines[0].due_date
    
    def process_payment(self, amount, payment_date=None):
        """Process a payment against the plan"""
        if not payment_date:
            payment_date = fields.Date.today()
        
        if self.state not in ['active', 'suspended']:
            raise UserError(_('Cannot process payment for inactive plan.'))
        
        # Find the next due payment line
        due_lines = self.payment_line_ids.filtered(
            lambda l: l.state == 'pending' and l.due_date <= payment_date
        ).sorted('due_date')
        
        if not due_lines:
            raise UserError(_('No payments are currently due.'))
        
        # Apply payment to the earliest due line
        line = due_lines[0]
        line.record_payment(amount, payment_date)
        
        # Update plan tracking
        self.last_payment_date = payment_date
        self.consecutive_missed = 0
        
        # Update next payment date
        next_pending = self.payment_line_ids.filtered(
            lambda l: l.state == 'pending').sorted('due_date')
        if next_pending:
            self.next_payment_date = next_pending[0].due_date
        else:
            # All payments completed
            self.action_complete()
        
        self.message_post(
            body=_('Payment of %s processed for line %s.') % (amount, line.sequence))
        
        return line
    
    def action_view_payments(self):
        """View all payments made for this plan"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Payments - {self.plan_number}',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('payment_plan_id', '=', self.id)],
            'context': {'default_payment_plan_id': self.id}
        }
    
    def action_view_schedule(self):
        """View payment schedule"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Payment Schedule - {self.plan_number}',
            'res_model': 'ams.payment.plan.line',
            'view_mode': 'tree,form',
            'domain': [('payment_plan_id', '=', self.id)],
            'context': {'default_payment_plan_id': self.id}
        }
    
    @api.model
    def _cron_process_overdue_payments(self):
        """Cron job to process overdue payment plan payments"""
        today = fields.Date.today()
        
        # Find overdue payment lines
        overdue_lines = self.env['ams.payment.plan.line'].search([
            ('state', '=', 'pending'),
            ('due_date', '<', today),
            ('payment_plan_id.state', '=', 'active')
        ])
        
        processed_plans = set()
        
        for line in overdue_lines:
            plan = line.payment_plan_id
            
            if plan.id in processed_plans:
                continue
            
            # Check grace period
            grace_end = line.due_date + timedelta(days=plan.grace_period_days)
            
            if today > grace_end:
                # Apply late fee
                if plan.late_fee_amount > 0:
                    line._apply_late_fee()
                
                # Update missed payment counters
                plan.missed_payments += 1
                plan.consecutive_missed += 1
                
                # Check if plan should be defaulted
                if plan.consecutive_missed >= 3:  # Configurable threshold
                    plan.action_default()
                
                # Send overdue notice
                plan._send_overdue_notice(line)
            
            processed_plans.add(plan.id)
        
        return len(processed_plans)
    
    def _send_overdue_notice(self, overdue_line):
        """Send overdue payment notice"""
        template = self.env.ref('ams_accounting.email_template_payment_plan_overdue', False)
        if template:
            ctx = {
                'payment_plan': self,
                'overdue_line': overdue_line,
                'days_overdue': (fields.Date.today() - overdue_line.due_date).days
            }
            template.with_context(ctx).send_mail(self.id, force_send=False)
    
    # ========================
    # CONSTRAINTS
    # ========================
    
    @api.constrains('total_amount', 'down_payment')
    def _check_amounts(self):
        for plan in self:
            if plan.total_amount <= 0:
                raise ValidationError(_('Total amount must be positive.'))
            if plan.down_payment < 0:
                raise ValidationError(_('Down payment cannot be negative.'))
            if plan.down_payment >= plan.total_amount:
                raise ValidationError(_('Down payment cannot exceed total amount.'))
    
    @api.constrains('number_of_payments')
    def _check_number_of_payments(self):
        for plan in self:
            if plan.number_of_payments <= 0:
                raise ValidationError(_('Number of payments must be positive.'))
    
    @api.constrains('interest_rate')
    def _check_interest_rate(self):
        for plan in self:
            if plan.interest_rate < 0:
                raise ValidationError(_('Interest rate cannot be negative.'))
    
    @api.constrains('first_payment_date', 'start_date')
    def _check_dates(self):
        for plan in self:
            if plan.first_payment_date < plan.start_date:
                raise ValidationError(_('First payment date cannot be before start date.'))


class AMSPaymentPlanLine(models.Model):
    """
    Individual payment plan installments
    """
    _name = 'ams.payment.plan.line'
    _description = 'AMS Payment Plan Line'
    _order = 'payment_plan_id, sequence'
    _rec_name = 'display_name'
    
    # Basic Information
    payment_plan_id = fields.Many2one('ams.payment.plan', 'Payment Plan', 
        required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='payment_plan_id.partner_id', 
        store=True, readonly=True)
    company_id = fields.Many2one('res.company', related='payment_plan_id.company_id', 
        store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='payment_plan_id.currency_id', 
        store=True, readonly=True)
    
    # Sequence and Identification
    sequence = fields.Integer('Payment #', required=True)
    display_name = fields.Char('Name', compute='_compute_display_name', store=True)
    
    # Payment Details
    due_date = fields.Date('Due Date', required=True)
    amount = fields.Float('Total Amount', required=True)
    principal_amount = fields.Float('Principal Amount', default=0.0)
    interest_amount = fields.Float('Interest Amount', default=0.0)
    late_fee_amount = fields.Float('Late Fee', default=0.0)
    total_amount_due = fields.Float('Total Due', compute='_compute_total_due', store=True)
    
    # Payment Tracking
    payment_date = fields.Date('Payment Date')
    amount_paid = fields.Float('Amount Paid', default=0.0)
    payment_id = fields.Many2one('account.payment', 'Payment Record')
    payment_reference = fields.Char('Payment Reference')
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)
    
    # Additional Information
    notes = fields.Text('Notes')
    reminder_sent = fields.Boolean('Reminder Sent', default=False)
    reminder_date = fields.Date('Reminder Date')
    
    @api.depends('payment_plan_id', 'sequence')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"Payment {line.sequence} - {line.payment_plan_id.plan_number}"
    
    @api.depends('amount', 'late_fee_amount')
    def _compute_total_due(self):
        for line in self:
            line.total_amount_due = line.amount + line.late_fee_amount
    
    def record_payment(self, amount_paid, payment_date=None, payment_reference=None):
        """Record a payment against this line"""
        if not payment_date:
            payment_date = fields.Date.today()
        
        if self.state in ['paid', 'cancelled']:
            raise UserError(_('Cannot record payment for %s line.') % self.state)
        
        self.amount_paid += amount_paid
        self.payment_date = payment_date
        
        if payment_reference:
            self.payment_reference = payment_reference
        
        # Update state based on amount paid
        if self.amount_paid >= self.total_amount_due:
            self.state = 'paid'
        elif self.amount_paid > 0:
            self.state = 'partial'
        
        # Check if overdue
        if payment_date > self.due_date and self.state != 'paid':
            self.state = 'overdue'
    
    def _apply_late_fee(self):
        """Apply late fee to this payment line"""
        if self.late_fee_amount == 0 and self.payment_plan_id.late_fee_amount > 0:
            self.late_fee_amount = self.payment_plan_id.late_fee_amount
            self.state = 'overdue'
    
    def action_send_reminder(self):
        """Send payment reminder for this line"""
        template = self.env.ref('ams_accounting.email_template_payment_plan_reminder', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.reminder_sent = True
            self.reminder_date = fields.Date.today()
    
    def action_record_payment(self):
        """Action to record payment manually"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Record Payment',
            'res_model': 'ams.payment.plan.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_line_id': self.id,
                'default_amount': self.total_amount_due - self.amount_paid,
            }
        }