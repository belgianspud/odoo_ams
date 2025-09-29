# -*- coding: utf-8 -*-

from odoo import models, fields


class SubscriptionTag(models.Model):
    _name = 'subscription.tag'
    _description = 'Subscription Tag'
    _order = 'name'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color', default=0)
    active = fields.Boolean('Active', default=True)
    subscription_ids = fields.Many2many('subscription.subscription', string='Subscriptions')