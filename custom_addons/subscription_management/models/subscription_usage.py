# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SubscriptionUsage(models.Model):
    _name = 'subscription.usage'
    _description = 'Subscription Usage'
    _order = 'date desc'
    
    subscription_id = fields.Many2one('subscription.subscription', 'Subscription',
                                      required=True, ondelete='cascade', index=True)
    date = fields.Date('Date', required=True, default=fields.Date.today, index=True)
    usage_type = fields.Char('Usage Type', required=True)
    quantity = fields.Float('Quantity', required=True)
    description = fields.Text('Description')
    
    # Billing
    billable = fields.Boolean('Billable', default=True)
    price_unit = fields.Float('Unit Price')
    price_total = fields.Float('Total Price', compute='_compute_price_total', store=True)
    
    @api.depends('quantity', 'price_unit')
    def _compute_price_total(self):
        for usage in self:
            usage.price_total = usage.quantity * usage.price_unit