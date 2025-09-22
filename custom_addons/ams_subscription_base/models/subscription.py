from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Plan'
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Plan Name',
        required=True,
        help="Name of the subscription plan"
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Short code for the subscription plan"
    )
    description = fields.Text(
        string='Description',
        help="Description of the subscription plan"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this subscription plan"
    )
    
    # Product and Pricing
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', '=', 'service')],
        help="Product used for billing this subscription"
    )
    duration_months = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=12,
        help="Duration of subscription period in months"
    )
    price = fields.Monetary(
        string='Price',
        related='product_id.list_price',
        readonly=True,
        help="Price from the related product"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Renewal Settings
    auto_renew = fields.Boolean(
        string='Auto Renew',
        default=True,
        help="Automatically renew subscriptions when they expire"
    )
    renewal_notice_days = fields.Integer(
        string='Renewal Notice (Days)',
        default=30,
        help="Days before expiry to send renewal notice"
    )
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help="Days after expiry before marking as lapsed"
    )
    
    # Statistics
    subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_count',
        help="Number of active subscriptions for this plan"
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_total_revenue',
        currency_field='currency_id',
        help="Total revenue from this subscription plan"
    )

    def _compute_subscription_count(self):
        for plan in self:
            plan.subscription_count = self.env['subscription.subscription'].search_count([
                ('plan_id', '=', plan.id),
                ('state', 'in', ['active', 'grace'])
            ])

    def _compute_total_revenue(self):
        for plan in self:
            subscriptions = self.env['subscription.subscription'].search([
                ('plan_id', '=', plan.id)
            ])
            invoices = subscriptions.mapped('invoice_ids').filtered(
                lambda inv: inv.state == 'posted'
            )
            plan.total_revenue = sum(invoices.mapped('amount_total'))

    @api.constrains('duration_months')
    def _check_duration(self):
        for record in self:
            if record.duration_months <= 0:
                raise ValidationError(_("Duration must be greater than 0 months."))

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Code must be unique. Another plan already uses this code."))

    def action_view_subscriptions(self):
        """View subscriptions for this plan"""
        self.ensure_one()
        return {
            'name': f"Subscriptions - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }


class Subscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription'
    _order = 'start_date desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Subscriber',
        required=True,
        tracking=True,
        help="The contact this subscription belongs to"
    )
    plan_id = fields.Many2one(
        'subscription.plan',
        string='Subscription Plan',
        required=True,
        tracking=True,
        help="The subscription plan"
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Date when subscription becomes active"
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        help="Date when subscription expires"
    )
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_next_renewal_date',
        store=True,
        help="Date when subscription should be renewed"
    )
    
    # Status and Configuration
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    auto_renew = fields.Boolean(
        string='Auto Renew',
        related='plan_id.auto_renew',
        readonly=False,
        tracking=True,
        help="Automatically renew this subscription"
    )
    
    # Financial
    invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Related Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    last_invoice_id = fields.Many2one(
        'account.move',
        string='Last Invoice',
        compute='_compute_last_invoice'
    )
    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='plan_id.currency_id',
        readonly=True
    )
    
    # Computed fields
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry'
    )
    is_renewable = fields.Boolean(
        string='Is Renewable',
        compute='_compute_is_renewable',
        help="True if subscription can be renewed"
    )

    @api.depends('partner_id.name', 'plan_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.plan_id:
                record.display_name = f"{record.partner_id.name} - {record.plan_id.name}"
            else:
                record.display_name = "New Subscription"

    @api.depends('end_date', 'auto_renew', 'state')
    def _compute_next_renewal_date(self):
        for record in self:
            if record.auto_renew and record.state in ['active', 'grace'] and record.end_date:
                record.next_renewal_date = record.end_date
            else:
                record.next_renewal_date = False

    @api.depends('end_date')
    def _compute_days_until_expiry(self):
        today = fields.Date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_until_expiry = delta.days
            else:
                record.days_until_expiry = 0

    @api.depends('state', 'end_date', 'balance_due')
    def _compute_is_renewable(self):
        today = fields.Date.today()
        for record in self:
            record.is_renewable = (
                record.state in ['active', 'grace', 'lapsed'] and
                record.balance_due <= 0
            )

    @api.depends('invoice_ids')
    def _compute_last_invoice(self):
        for record in self:
            invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            record.last_invoice_id = invoices and max(invoices, key=lambda inv: inv.invoice_date) or False

    @api.depends('invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.state')
    def _compute_financial_totals(self):
        for record in self:
            invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            record.total_invoiced = sum(invoices.mapped('amount_total'))
            record.balance_due = sum(invoices.mapped('amount_residual'))
            record.total_paid = record.total_invoiced - record.balance_due

    @api.onchange('plan_id', 'start_date')
    def _onchange_plan_dates(self):
        if self.plan_id and self.start_date:
            self.end_date = self.start_date + relativedelta(months=self.plan_id.duration_months)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_("Start date cannot be after end date."))

    def action_activate(self):
        """Activate subscription"""
        for record in self:
            if record.state == 'draft':
                # Create initial invoice
                record._create_invoice()
            record.state = 'active'

    def action_cancel(self):
        """Cancel subscription"""
        self.write({'state': 'cancelled', 'auto_renew': False})

    def action_renew(self):
        """Manually renew subscription"""
        for record in self:
            if not record.is_renewable:
                raise UserError(_("Subscription cannot be renewed. Please check payment status."))
            
            # Create renewal invoice
            invoice = record._create_invoice()
            
            # Extend subscription period
            new_end_date = record.end_date + relativedelta(months=record.plan_id.duration_months)
            record.write({
                'end_date': new_end_date,
                'state': 'active'
            })
            
            return {
                'name': _('Renewal Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def _create_invoice(self):
        """Create invoice for subscription"""
        self.ensure_one()
        
        if not self.plan_id.product_id:
            raise UserError(_("No product defined for subscription plan %s") % self.plan_id.name)
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.plan_id.product_id.id,
                'name': f"{self.plan_id.name} - {self.start_date} to {self.end_date}",
                'quantity': 1,
                'price_unit': self.plan_id.product_id.list_price,
                'account_id': self.plan_id.product_id.categ_id.property_account_income_categ_id.id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        return invoice

    @api.model
    def process_renewals(self):
        """Cron job method to process subscription renewals"""
        today = fields.Date.today()
        
        # Find subscriptions due for renewal
        renewals = self.search([
            ('auto_renew', '=', True),
            ('state', '=', 'active'),
            ('end_date', '<=', today),
            ('balance_due', '<=', 0)  # Only renew if paid up
        ])
        
        renewed_count = 0
        for subscription in renewals:
            try:
                # Create renewal invoice
                subscription._create_invoice()
                
                # Extend subscription
                new_end_date = subscription.end_date + relativedelta(months=subscription.plan_id.duration_months)
                subscription.end_date = new_end_date
                
                renewed_count += 1
                _logger.info(f"Auto-renewed subscription {subscription.id} for {subscription.partner_id.name}")
                
            except Exception as e:
                _logger.error(f"Failed to renew subscription {subscription.id}: {str(e)}")
        
        # Update statuses based on dates
        self._update_subscription_statuses()
        
        _logger.info(f"Processed {renewed_count} subscription renewals")

    @api.model
    def _update_subscription_statuses(self):
        """Update subscription statuses based on dates"""
        today = fields.Date.today()
        
        # Find subscriptions that should be in grace period
        grace_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        
        for subscription in grace_subscriptions:
            grace_end = subscription.end_date + timedelta(days=subscription.plan_id.grace_period_days)
            if today <= grace_end:
                subscription.state = 'grace'
            else:
                subscription.state = 'lapsed'
        
        _logger.info(f"Updated {len(grace_subscriptions)} subscription statuses")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Subscriptions'
    )
    current_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Current Subscription',
        compute='_compute_current_subscription'
    )
    has_active_subscription = fields.Boolean(
        string='Has Active Subscription',
        compute='_compute_current_subscription'
    )

    @api.depends('subscription_ids.state')
    def _compute_current_subscription(self):
        for partner in self:
            active_subscription = partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'grace']
            )
            if active_subscription:
                partner.current_subscription_id = active_subscription[0]
                partner.has_active_subscription = True
            else:
                partner.current_subscription_id = False
                partner.has_active_subscription = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Related Subscription',
        help="Subscription this invoice is related to"
    )