# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

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

    total_seats = fields.Integer(string='Total Seats', default=0)
    used_seats = fields.Integer(string='Used Seats', compute='_compute_used_seats', store=True)

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
