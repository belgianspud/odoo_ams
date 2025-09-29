# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    subscription_id = fields.Many2one('subscription.subscription', 'Subscription',
                                     copy=False, index=True,
                                     help='Subscription that generated this invoice')