# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    subscription_ids = fields.One2many('subscription.subscription', 'partner_id',
                                       'Subscriptions')
    subscription_count = fields.Integer('Subscription Count',
                                        compute='_compute_subscription_count')
    active_subscription_count = fields.Integer('Active Subscriptions',
                                               compute='_compute_subscription_count')
    
    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)
            partner.active_subscription_count = len(partner.subscription_ids.filtered(
                lambda s: s.state == 'active'
            ))
    
    def action_view_subscriptions(self):
        """Action to view partner's subscriptions"""
        return {
            'name': 'Subscriptions',
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }