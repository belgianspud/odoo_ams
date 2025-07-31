# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class AMSBillingPeriod(models.Model):
    _name = 'ams.billing.period'
    _description = 'AMS Billing Period'
    _order = 'period_value, period_unit'

    name = fields.Char(string='Period Name', required=True)
    period_value = fields.Integer(string='Period Value', required=True, default=1)
    period_unit = fields.Selection([
        ('month', 'Month(s)'),
        ('year', 'Year(s)')
    ], string='Period Unit', required=True, default='month')
    
    grace_days = fields.Integer(string='Default Grace Days', default=30)
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    
    def get_next_billing_date(self, start_date):
        """Calculate the next billing date based on this period"""
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        
        if self.period_unit == 'month':
            return start_date + relativedelta(months=self.period_value)
        elif self.period_unit == 'year':
            return start_date + relativedelta(years=self.period_value)
        return start_date


class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Subscription Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    account_id = fields.Many2one('res.partner', string='Account/Company', tracking=True)
    subscription_type = fields.Selection([
        ('individual', 'Individual'),
        ('enterprise', 'Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string='Subscription Type', required=True, tracking=True)

    tier_id = fields.Many2one('ams.subscription.tier', string='Subscription Tier', tracking=True)
    billing_period_id = fields.Many2one('ams.billing.period', string='Billing Period', tracking=True)
    line_ids = fields.One2many('ams.subscription.line', 'subscription_id', string='Subscription Lines')
    seat_ids = fields.One2many('ams.subscription.seat', 'subscription_id', string='Seats')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated')
    ], string='Status', default='draft', tracking=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    end_date = fields.Date(string='End Date')
    paid_through_date = fields.Date(string='Paid Through Date')
    next_billing_date = fields.Date(string='Next Billing Date', compute='_compute_next_billing_date', store=True)

    total_seats = fields.Integer(string='Total Seats', default=0)
    used_seats = fields.Integer(string='Used Seats', compute='_compute_used_seats', store=True)
    
    # Integration with Sales Orders
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    @api.depends('billing_period_id', 'paid_through_date')
    def _compute_next_billing_date(self):
        for sub in self:
            if sub.billing_period_id and sub.paid_through_date:
                sub.next_billing_date = sub.billing_period_id.get_next_billing_date(sub.paid_through_date)
            else:
                sub.next_billing_date = False

    @api.depends('seat_ids')
    def _compute_used_seats(self):
        for sub in self:
            sub.used_seats = len(sub.seat_ids)

    @api.constrains('seat_ids')
    def _check_seat_allocation(self):
        for sub in self:
            if sub.total_seats and len(sub.seat_ids) > sub.total_seats:
                raise ValueError("Cannot assign more seats than available for this subscription.")

    def action_set_active(self):
        self.write({'status': 'active'})

    def action_set_grace(self):
        self.write({'status': 'grace'})

    def action_set_suspended(self):
        self.write({'status': 'suspended'})

    def action_set_terminated(self):
        self.write({'status': 'terminated'})

    def create_renewal_invoice(self):
        """Create a renewal invoice for this subscription"""
        if not self.line_ids:
            return False
        
        invoice_vals = {
            'partner_id': self.partner_id.id or self.account_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': []
        }
        
        for line in self.line_ids:
            invoice_line_vals = {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'name': f"{line.product_id.name} - Renewal",
            }
            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))
        
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice


class AMSSubscriptionLine(models.Model):
    _name = 'ams.subscription.line'
    _description = 'AMS Subscription Line'

    subscription_id = fields.Many2one('ams.subscription', string='Subscription', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Integer(string='Quantity', default=1)
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit


class AMSSubscriptionTier(models.Model):
    _name = 'ams.subscription.tier'
    _description = 'AMS Subscription Tier'

    name = fields.Char(string='Tier Name', required=True)
    membership_type = fields.Selection([
        ('individual', 'Individual'),
        ('enterprise', 'Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string='Membership Type', required=True)

    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('none', 'No Expiration')
    ], string='Period Type', required=True, default='annual')

    billing_period_id = fields.Many2one('ams.billing.period', string='Billing Period')
    price = fields.Float(string='Price', default=0.0)
    grace_days = fields.Integer(string='Grace Days', default=30)
    suspend_days = fields.Integer(string='Suspend Days', default=60)
    terminate_days = fields.Integer(string='Terminate Days', default=30)

    benefit_product_ids = fields.Many2many('product.product', string='Benefit Products')


class AMSSubscriptionSeat(models.Model):
    _name = 'ams.subscription.seat'
    _description = 'AMS Subscription Seat'

    subscription_id = fields.Many2one('ams.subscription', string='Subscription', ondelete='cascade')
    contact_id = fields.Many2one('res.partner', string='Assigned Contact')
    assigned_date = fields.Date(string='Assigned Date', default=fields.Date.today)