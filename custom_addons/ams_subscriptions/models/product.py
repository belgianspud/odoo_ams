from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type')
    is_subscription_product = fields.Boolean('Is Subscription Product')
    
    def action_create_subscription(self):
        """Action to create subscription from product"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Subscription',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'context': {
                'default_subscription_type_id': self.subscription_type_id.id,
                'default_product_id': self.product_variant_id.id,
                'default_amount': self.list_price,
            }
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """Override to create subscriptions for subscription products"""
        result = super()._action_launch_stock_rule(previous_product_uom_qty)
        
        for line in self:
            if line.product_id.is_subscription_product and line.order_id.state == 'sale':
                line._create_subscription_from_sale()
        
        return result
    
    def _create_subscription_from_sale(self):
        """Create subscription from sale order line"""
        if not self.product_id.subscription_type_id:
            return
            
        subscription_vals = {
            'partner_id': self.order_id.partner_id.id,
            'subscription_type_id': self.product_id.subscription_type_id.id,
            'product_id': self.product_id.id,
            'name': f"{self.product_id.name} - {self.order_id.partner_id.name}",
            'sale_order_line_id': self.id,
            'amount': self.price_unit,
            'start_date': fields.Date.today(),
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        return subscription

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    subscription_id = fields.Many2one('ams.subscription', 'Related Subscription')