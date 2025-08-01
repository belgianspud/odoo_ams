# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # For chatter and tracking

    name = fields.Char(string='Subscription Name', required=True, tracking=True)
    
    # Link to Customer / Account
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    account_id = fields.Many2one('res.partner', string='Account', help='Used for enterprise memberships')

    # Product and Sale Info
    product_id = fields.Many2one('product.product', string='Product', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')

    # Subscription Type and Tier
    subscription_type = fields.Selection([
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('seat', 'Enterprise Seat Add-On'),
    ], string='Subscription Type', required=True)

    tier_id = fields.Many2one('ams.subscription.tier', string='Tier / Level')

    # Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    paid_through_date = fields.Date(string='Paid Through Date')
    grace_end_date = fields.Date(string='Grace Period End')
    suspend_end_date = fields.Date(string='Suspension End')
    terminate_date = fields.Date(string='Termination Date')

    # Enterprise Seat Management
    base_seats = fields.Integer(string='Base Seats', default=0)
    extra_seats = fields.Integer(string='Extra Seats', default=0)
    total_seats = fields.Integer(string='Total Seats', compute='_compute_total_seats', store=True)

    seat_ids = fields.One2many('ams.subscription.seat', 'subscription_id', string='Assigned Seats')

    # Flags
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    is_free = fields.Boolean(string='Free Subscription', default=False)

    @api.depends('base_seats', 'extra_seats')
    def _compute_total_seats(self):
        for sub in self:
            sub.total_seats = (sub.base_seats or 0) + (sub.extra_seats or 0)

    def action_activate(self):
        for sub in self:
            sub.state = 'active'
            if not sub.paid_through_date:
                # Default to 1 year if not set; can be overridden by tier or product period
                sub.paid_through_date = date.today() + timedelta(days=365)

    def action_set_grace(self):
        self.write({'state': 'grace'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_terminate(self):
        self.write({'state': 'terminated'})

    # ------------------------------------------------
    # Subscription Lifecycle & Renewal Automation
    # ------------------------------------------------
    def _cron_process_subscription_lifecycle(self):
        """Run daily: Move subscriptions through Active -> Grace -> Suspended -> Terminated."""
        today = fields.Date.today()
        subs = self.search([('state', '!=', 'terminated')])
        for sub in subs:
            tier = sub.tier_id
            if not tier or tier.is_free:
                continue  # free subscriptions do not expire

            grace_end = sub.paid_through_date + timedelta(days=tier.grace_days)
            suspend_end = grace_end + timedelta(days=tier.suspend_days)

            if today > suspend_end:
                sub.state = 'terminated'
            elif today > grace_end:
                sub.state = 'suspended'
            elif today > sub.paid_through_date:
                sub.state = 'grace'
            else:
                sub.state = 'active'

    def _cron_generate_renewal_invoices(self):
        """Run daily: Auto-generate renewal invoices 2 weeks before paid_through_date."""
        today = fields.Date.today()
        renew_window = today + timedelta(days=14)
        subs = self.search([('state', '=', 'active'), ('paid_through_date', '<=', renew_window)])

        for sub in subs:
            # Avoid duplicate renewal invoices
            existing_invoice = self.env['account.move'].search([
                ('invoice_origin', '=', sub.name),
                ('state', '=', 'draft'),
            ], limit=1)
            if existing_invoice:
                continue

            # Create a draft invoice
            product = self.env['product.product'].search([('id','=',sub.product_id.id)], limit=1)
            if not product:
                continue

            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': sub.partner_id.id,
                'invoice_origin': sub.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': product.list_price,
                })],
            }
            invoice = self.env['account.move'].create(move_vals)

            # Optional: email notification could be added here
            sub.message_post(body=f"Renewal invoice {invoice.name or invoice.id} generated.")