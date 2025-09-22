from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionPaymentPlan(models.Model):
    _name = 'subscription.payment.plan'
    _description = 'Subscription Payment Plan'
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Plan Name',
        required=True,
        help="Name of the payment plan (e.g., '3 Monthly Payments')"
    )
    code = fields.Char(
        string='Code',
        help="Short code for the payment plan"
    )
    description = fields.Text(
        string='Description',
        help="Description of the payment plan terms"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this payment plan"
    )
    
    # Plan Configuration
    total_amount = fields.Monetary(
        string='Total Amount',
        required=True,
        currency_field='currency_id',
        help="Total amount to be paid across all installments"
    )
    installments = fields.Integer(
        string='Number of Installments',
        required=True,
        default=3,
        help="Number of payments to split the total amount"
    )
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biannual', 'Bi-Annual'),
        ('custom', 'Custom')
    ], string='Payment Frequency', default='monthly', required=True)
    
    custom_interval_number = fields.Integer(
        string='Custom Interval',
        default=1,
        help="Number of interval units between payments (for custom frequency)"
    )
    custom_interval_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string='Custom Interval Type', default='months')
    
    # Fees and Charges
    setup_fee = fields.Monetary(
        string='Setup Fee',
        currency_field='currency_id',
        help="One-time setup fee for payment plan"
    )
    installment_fee = fields.Monetary(
        string='Per Installment Fee',
        currency_field='currency_id',
        help="Fee charged per installment payment"
    )
    late_fee = fields.Monetary(
        string='Late Payment Fee',
        currency_field='currency_id',
        help="Fee charged for late payments"
    )
    
    # Payment Terms
    first_payment_due = fields.Selection([
        ('immediate', 'Immediately'),
        ('next_period', 'Next Payment Period'),
        ('custom', 'Custom Days')
    ], string='First Payment Due', default='immediate', required=True)
    
    custom_first_payment_days = fields.Integer(
        string='Days Until First Payment',
        default=0,
        help="Days from enrollment until first payment (for custom option)"
    )
    
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=5,
        help="Days after due date before marking as overdue"
    )
    
    # Eligibility and Restrictions
    min_total_amount = fields.Monetary(
        string='Minimum Total Amount',
        currency_field='currency_id',
        help="Minimum subscription amount to qualify for this plan"
    )
    max_total_amount = fields.Monetary(
        string='Maximum Total Amount',
        currency_field='currency_id',
        help="Maximum subscription amount for this plan (0 = no limit)"
    )
    
    subscription_plan_ids = fields.Many2many(
        'subscription.plan',
        'payment_plan_subscription_plan_rel',
        'payment_plan_id',
        'subscription_plan_id',
        string='Available for Subscription Plans',
        help="Subscription plans that can use this payment plan"
    )
    
    # Statistics
    active_payment_plans_count = fields.Integer(
        string='Active Payment Plans',
        compute='_compute_statistics'
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_statistics',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('installments', 'total_amount', 'setup_fee', 'installment_fee')
    def _compute_statistics(self):
        for plan in self:
            # Count active subscriptions using this payment plan
            active_subscriptions = self.env['subscription.subscription'].search([
                ('payment_plan_id', '=', plan.id),
                ('state', 'in', ['active', 'grace'])
            ])
            plan.active_payment_plans_count = len(active_subscriptions)
            
            # Calculate total revenue
            plan.total_revenue = sum(active_subscriptions.mapped('total_paid'))

    @api.constrains('installments')
    def _check_installments(self):
        for plan in self:
            if plan.installments < 2:
                raise ValidationError(_("Payment plan must have at least 2 installments."))
            if plan.installments > 12:
                raise ValidationError(_("Payment plan cannot have more than 12 installments."))

    @api.constrains('total_amount', 'min_total_amount', 'max_total_amount')
    def _check_amounts(self):
        for plan in self:
            if plan.total_amount <= 0:
                raise ValidationError(_("Total amount must be greater than zero."))
            
            if plan.max_total_amount > 0 and plan.min_total_amount > plan.max_total_amount:
                raise ValidationError(_("Minimum amount cannot be greater than maximum amount."))

    def calculate_installment_amount(self):
        """Calculate the amount per installment"""
        self.ensure_one()
        if self.installments > 0:
            base_amount = self.total_amount / self.installments
            return base_amount + self.installment_fee
        return 0

    def calculate_payment_schedule(self, start_date=None):
        """Calculate payment schedule for this plan"""
        self.ensure_one()
        
        if not start_date:
            start_date = fields.Date.today()
        
        schedule = []
        installment_amount = self.calculate_installment_amount()
        
        # Calculate first payment date
        if self.first_payment_due == 'immediate':
            first_payment_date = start_date
        elif self.first_payment_due == 'next_period':
            if self.frequency == 'monthly':
                first_payment_date = start_date + relativedelta(months=1)
            elif self.frequency == 'quarterly':
                first_payment_date = start_date + relativedelta(months=3)
            else:
                first_payment_date = start_date + relativedelta(months=1)
        else:  # custom
            first_payment_date = start_date + timedelta(days=self.custom_first_payment_days)
        
        # Generate schedule
        current_date = first_payment_date
        for i in range(self.installments):
            schedule.append({
                'installment_number': i + 1,
                'due_date': current_date,
                'amount': installment_amount,
                'description': f"Installment {i + 1} of {self.installments}"
            })
            
            # Calculate next payment date
            if self.frequency == 'monthly':
                current_date = current_date + relativedelta(months=1)
            elif self.frequency == 'quarterly':
                current_date = current_date + relativedelta(months=3)
            elif self.frequency == 'biannual':
                current_date = current_date + relativedelta(months=6)
            elif self.frequency == 'custom':
                if self.custom_interval_type == 'days':
                    current_date = current_date + timedelta(days=self.custom_interval_number)
                elif self.custom_interval_type == 'weeks':
                    current_date = current_date + timedelta(weeks=self.custom_interval_number)
                elif self.custom_interval_type == 'months':
                    current_date = current_date + relativedelta(months=self.custom_interval_number)
        
        return schedule

    def action_view_subscriptions(self):
        """View subscriptions using this payment plan"""
        self.ensure_one()
        return {
            'name': f"Subscriptions - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form',
            'domain': [('payment_plan_id', '=', self.id)],
            'context': {'default_payment_plan_id': self.id},
        }


class SubscriptionInstallment(models.Model):
    _name = 'subscription.installment'
    _description = 'Subscription Installment'
    _order = 'subscription_id, installment_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        help="Related subscription"
    )
    payment_plan_id = fields.Many2one(
        'subscription.payment.plan',
        string='Payment Plan',
        required=True,
        help="Payment plan this installment belongs to"
    )
    installment_number = fields.Integer(
        string='Installment #',
        required=True,
        help="Sequential number of this installment"
    )
    
    # Payment Details
    due_date = fields.Date(
        string='Due Date',
        required=True,
        tracking=True,
        help="Date when payment is due"
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        help="Amount due for this installment"
    )
    late_fee = fields.Monetary(
        string='Late Fee',
        currency_field='currency_id',
        help="Late fee applied if payment is overdue"
    )
    total_due = fields.Monetary(
        string='Total Due',
        compute='_compute_total_due',
        currency_field='currency_id',
        help="Total amount including late fees"
    )
    
    # Payment Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', required=True, tracking=True)
    
    paid_date = fields.Date(
        string='Paid Date',
        help="Date when payment was received"
    )
    paid_amount = fields.Monetary(
        string='Paid Amount',
        currency_field='currency_id',
        help="Amount actually paid"
    )
    
    # Payment Information
    payment_method = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('online', 'Online Payment'),
        ('other', 'Other')
    ], string='Payment Method', tracking=True)
    
    payment_reference = fields.Char(
        string='Payment Reference',
        help="Transaction ID, check number, etc."
    )
    
    # Related Records
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        help="Invoice generated for this installment"
    )
    
    # Automated Processing
    reminder_sent_date = fields.Date(
        string='Reminder Sent',
        help="Date when payment reminder was sent"
    )
    overdue_notice_sent_date = fields.Date(
        string='Overdue Notice Sent',
        help="Date when overdue notice was sent"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        readonly=True
    )

    @api.depends('amount', 'late_fee')
    def _compute_total_due(self):
        for installment in self:
            installment.total_due = installment.amount + installment.late_fee

    @api.constrains('installment_number', 'subscription_id')
    def _check_installment_number(self):
        for installment in self:
            # Check for duplicate installment numbers within same subscription
            existing = self.search([
                ('subscription_id', '=', installment.subscription_id.id),
                ('installment_number', '=', installment.installment_number),
                ('id', '!=', installment.id)
            ])
            if existing:
                raise ValidationError(_("Installment number must be unique within subscription."))

    def action_mark_paid(self):
        """Mark installment as paid"""
        for installment in self:
            installment.write({
                'status': 'paid',
                'paid_date': fields.Date.today(),
                'paid_amount': installment.total_due
            })
            
            # Create payment record or update invoice
            if installment.invoice_id:
                # Logic to mark invoice as paid could go here
                pass
            
            installment.message_post(body=_("Installment marked as paid."))

    def action_send_reminder(self):
        """Send payment reminder for this installment"""
        template = self.env.ref('subscription_base.email_template_installment_reminder', False)
        if template and self.subscription_id.partner_id.email:
            template.send_mail(self.id, force_send=True)
            self.reminder_sent_date = fields.Date.today()

    def action_create_invoice(self):
        """Create invoice for this installment"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_("Invoice already exists for this installment."))
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.subscription_id.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.due_date,
            'ref': f"Installment {self.installment_number} - {self.subscription_id.display_name}",
            'subscription_id': self.subscription_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': f"Installment Payment {self.installment_number}/{self.payment_plan_id.installments}",
                'quantity': 1,
                'price_unit': self.total_due,
                'account_id': self.subscription_id.plan_id.product_id.categ_id.property_account_income_categ_id.id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        
        return {
            'name': _('Installment Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def process_overdue_installments(self):
        """Cron job to process overdue installments"""
        today = fields.Date.today()
        
        # Find installments that should be marked overdue
        overdue_installments = self.search([
            ('status', '=', 'pending'),
            ('due_date', '<', today)
        ])
        
        for installment in overdue_installments:
            # Calculate grace period
            grace_end = installment.due_date + timedelta(days=installment.payment_plan_id.grace_period_days)
            
            if today > grace_end:
                # Apply late fee and mark overdue
                if installment.payment_plan_id.late_fee > 0:
                    installment.late_fee = installment.payment_plan_id.late_fee
                
                installment.status = 'overdue'
                
                # Send overdue notice
                installment._send_overdue_notice()
        
        _logger.info(f"Processed {len(overdue_installments)} overdue installments")

    def _send_overdue_notice(self):
        """Send overdue notice"""
        template = self.env.ref('subscription_base.email_template_installment_overdue', False)
        if template and self.subscription_id.partner_id.email:
            template.send_mail(self.id, force_send=True)
            self.overdue_notice_sent_date = fields.Date.today()

    @api.model
    def send_payment_reminders(self):
        """Cron job to send payment reminders"""
        reminder_days = 3  # Send reminder 3 days before due date
        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        
        # Find installments due soon that haven't had reminders sent
        upcoming_installments = self.search([
            ('status', '=', 'pending'),
            ('due_date', '=', reminder_date),
            ('reminder_sent_date', '=', False)
        ])
        
        for installment in upcoming_installments:
            installment.action_send_reminder()
        
        _logger.info(f"Sent payment reminders for {len(upcoming_installments)} installments")


class Subscription(models.Model):
    _inherit = 'subscription.subscription'

    # Payment Plan Integration
    payment_plan_id = fields.Many2one(
        'subscription.payment.plan',
        string='Payment Plan',
        help="Payment plan for this subscription"
    )
    uses_payment_plan = fields.Boolean(
        string='Uses Payment Plan',
        compute='_compute_uses_payment_plan'
    )
    
    # Installment Management
    installment_ids = fields.One2many(
        'subscription.installment',
        'subscription_id',
        string='Installments'
    )
    total_installments = fields.Integer(
        string='Total Installments',
        related='payment_plan_id.installments',
        readonly=True
    )
    paid_installments = fields.Integer(
        string='Paid Installments',
        compute='_compute_installment_statistics'
    )
    overdue_installments = fields.Integer(
        string='Overdue Installments',
        compute='_compute_installment_statistics'
    )
    next_payment_date = fields.Date(
        string='Next Payment Date',
        compute='_compute_next_payment'
    )
    next_payment_amount = fields.Monetary(
        string='Next Payment Amount',
        compute='_compute_next_payment',
        currency_field='currency_id'
    )

    @api.depends('payment_plan_id')
    def _compute_uses_payment_plan(self):
        for subscription in self:
            subscription.uses_payment_plan = bool(subscription.payment_plan_id)

    @api.depends('installment_ids.status')
    def _compute_installment_statistics(self):
        for subscription in self:
            installments = subscription.installment_ids
            subscription.paid_installments = len(installments.filtered(lambda i: i.status == 'paid'))
            subscription.overdue_installments = len(installments.filtered(lambda i: i.status == 'overdue'))

    @api.depends('installment_ids.due_date', 'installment_ids.status')
    def _compute_next_payment(self):
        for subscription in self:
            next_installment = subscription.installment_ids.filtered(
                lambda i: i.status == 'pending'
            ).sorted('due_date')
            
            if next_installment:
                subscription.next_payment_date = next_installment[0].due_date
                subscription.next_payment_amount = next_installment[0].total_due
            else:
                subscription.next_payment_date = False
                subscription.next_payment_amount = 0

    @api.onchange('payment_plan_id')
    def _onchange_payment_plan_id(self):
        if self.payment_plan_id:
            # Update subscription amount to match payment plan
            self.total_amount = self.payment_plan_id.total_amount

    def action_setup_payment_plan(self):
        """Set up installment schedule for payment plan"""
        self.ensure_one()
        
        if not self.payment_plan_id:
            raise UserError(_("No payment plan selected for this subscription."))
        
        if self.installment_ids:
            raise UserError(_("Payment plan already set up for this subscription."))
        
        # Generate payment schedule
        schedule = self.payment_plan_id.calculate_payment_schedule(self.start_date)
        
        # Create installment records
        for item in schedule:
            self.env['subscription.installment'].create({
                'subscription_id': self.id,
                'payment_plan_id': self.payment_plan_id.id,
                'installment_number': item['installment_number'],
                'due_date': item['due_date'],
                'amount': item['amount'],
                'status': 'pending'
            })
        
        self.message_post(body=_("Payment plan set up with %d installments.") % len(schedule))

    def action_view_installments(self):
        """View installments for this subscription"""
        self.ensure_one()
        return {
            'name': f"Installments - {self.display_name}",
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.installment',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }

    def action_create_all_invoices(self):
        """Create invoices for all pending installments"""
        self.ensure_one()
        pending_installments = self.installment_ids.filtered(
            lambda i: i.status == 'pending' and not i.invoice_id
        )
        
        for installment in pending_installments:
            installment.action_create_invoice()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Created invoices for %d installments') % len(pending_installments),
                'type': 'success',
            }
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Payment Plan Statistics
    total_payment_plan_subscriptions = fields.Integer(
        string='Payment Plan Subscriptions',
        compute='_compute_payment_plan_stats'
    )
    overdue_installments_count = fields.Integer(
        string='Overdue Installments',
        compute='_compute_payment_plan_stats'
    )
    next_installment_due = fields.Date(
        string='Next Installment Due',
        compute='_compute_payment_plan_stats'
    )

    @api.depends('subscription_ids.payment_plan_id', 'subscription_ids.installment_ids.status')
    def _compute_payment_plan_stats(self):
        for partner in self:
            # Count subscriptions with payment plans
            payment_plan_subs = partner.subscription_ids.filtered('payment_plan_id')
            partner.total_payment_plan_subscriptions = len(payment_plan_subs)
            
            # Count overdue installments
            all_installments = payment_plan_subs.mapped('installment_ids')
            partner.overdue_installments_count = len(all_installments.filtered(lambda i: i.status == 'overdue'))
            
            # Find next installment due date
            pending_installments = all_installments.filtered(lambda i: i.status == 'pending')
            if pending_installments:
                partner.next_installment_due = min(pending_installments.mapped('due_date'))
            else:
                partner.next_installment_due = False

    def action_view_installments(self):
        """View all installments for this partner"""
        self.ensure_one()
        installments = self.subscription_ids.mapped('installment_ids')
        return {
            'name': f"Installments - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.installment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', installments.ids)],
        }