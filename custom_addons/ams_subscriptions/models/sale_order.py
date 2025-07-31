# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override to create AMS subscriptions when order is confirmed"""
        result = super().action_confirm()
        
        # Create subscriptions for AMS products
        for order in self:
            order._create_ams_subscriptions()
        
        return result

    def _create_ams_subscriptions(self):
        """Create AMS subscriptions for subscription products in this order"""
        ams_lines = self.order_line.filtered(lambda line: 
            line.product_id.ams_product_type != 'none' and 
            line.product_id.subscription_period != 'none'
        )
        
        if not ams_lines:
            return
        
        # Group by customer (partner_id) and subscription type
        subscriptions_to_create = {}
        
        for line in ams_lines:
            key = (line.order_id.partner_id.id, line.product_id.ams_product_type)
            
            if key not in subscriptions_to_create:
                # Find appropriate billing period
                billing_period = self._get_billing_period_for_product(line.product_id)
                
                subscriptions_to_create[key] = {
                    'name': f"{line.product_id.ams_product_type.title()} Subscription - {line.order_id.partner_id.name}",
                    'partner_id': line.order_id.partner_id.id,
                    'subscription_type': line.product_id.ams_product_type,
                    'billing_period_id': billing_period.id if billing_period else False,
                    'sale_order_id': self.id,
                    'status': 'active',
                    'start_date': fields.Date.today(),
                    'paid_through_date': fields.Date.today(),
                    'line_ids': []
                }
            
            # Add subscription line
            subscription_line = {
                'product_id': line.product_id.id,
                'quantity': line.product_qty,
                'price_unit': line.price_unit,
            }
            subscriptions_to_create[key]['line_ids'].append((0, 0, subscription_line))
        
        # Create the subscriptions
        for subscription_data in subscriptions_to_create.values():
            subscription = self.env['ams.subscription'].create(subscription_data)
            
            # Set the paid through date based on billing period
            if subscription.billing_period_id:
                subscription.paid_through_date = subscription.billing_period_id.get_next_billing_date(subscription.start_date)

    def _get_billing_period_for_product(self, product):
        """Get the appropriate billing period for an AMS product"""
        if product.subscription_period == 'monthly':
            return self.env.ref('ams_subscriptions.billing_period_monthly', raise_if_not_found=False)
        elif product.subscription_period == 'quarterly':
            return self.env.ref('ams_subscriptions.billing_period_quarterly', raise_if_not_found=False)
        elif product.subscription_period == 'semi_annual':
            return self.env.ref('ams_subscriptions.billing_period_semi_annual', raise_if_not_found=False)
        elif product.subscription_period == 'annual':
            return self.env.ref('ams_subscriptions.billing_period_annual', raise_if_not_found=False)
        
        # Default to annual if not specified
        return self.env.ref('ams_subscriptions.billing_period_annual', raise_if_not_found=False)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ams_subscription_id = fields.Many2one('ams.subscription', string='AMS Subscription', readonly=True)
    
    @api.onchange('product_id')
    def _onchange_product_id_ams(self):
        """Auto-set description for AMS products"""
        if self.product_id and self.product_id.ams_product_type != 'none':
            subscription_desc = ""
            if self.product_id.subscription_period != 'none':
                subscription_desc = f" ({self.product_id.subscription_period.replace('_', ' ').title()})"
            
            self.name = f"{self.product_id.name}{subscription_desc}"