# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SubscriptionLine(models.Model):
    _name = 'subscription.line'
    _description = 'Subscription Line'
    
    subscription_id = fields.Many2one('subscription.subscription', 'Subscription',
                                      required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    name = fields.Text('Description', required=True)
    quantity = fields.Float('Quantity', default=1.0)
    price_unit = fields.Float('Unit Price')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True)
    
    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price