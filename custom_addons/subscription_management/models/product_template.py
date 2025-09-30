# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_subscription = fields.Boolean('Subscription',
                                     help='Check this if the product is used for subscriptions')
    subscription_plan_ids = fields.One2many('subscription.plan', 'product_template_id',
                                            'Subscription Plans',
                                            help='Subscription plans using this product')
    subscription_plan_count = fields.Integer('Plan Count', compute='_compute_subscription_plan_count')
    
    def _compute_subscription_plan_count(self):
        for product in self:
            product.subscription_plan_count = len(product.subscription_plan_ids)