# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_ams_subscriptions(self):
        """Create AMS subscriptions or add seats after order confirmation."""
        for order in self:
            for line in order.order_line:
                product = line.product_id.product_tmpl_id
                if product.ams_product_type == 'none':
                    continue  # Not an AMS product

                # -----------------------------
                # Handle Enterprise Seat Add-ons
                # -----------------------------
                if product.is_seat_addon:
                    # Find active enterprise subscription for this partner
                    enterprise_sub = self.env['ams.subscription'].search([
                        ('partner_id', '=', order.partner_id.id),
                        ('subscription_type', '=', 'enterprise'),
                        ('state', '=', 'active'),
                    ], limit=1)
                    if enterprise_sub:
                        enterprise_sub.extra_seats += int(line.product_uom_qty)
                        enterprise_sub._compute_total_seats()
                        enterprise_sub.message_post(
                            body=f"{int(line.product_uom_qty)} seats added via sale order {order.name}."
                        )
                        continue  # Skip subscription creation for seat add-ons

                # -----------------------------
                # Create a new subscription
                # -----------------------------
                self.env['ams.subscription'].create({
                    'name': f"Subscription for {order.partner_id.name} - {product.name}",
                    'subscription_type': product.ams_product_type,
                    'tier_id': product.subscription_tier_id.id,
                    'partner_id': order.partner_id.id,
                    'account_id': order.partner_id.parent_id.id if order.partner_id.parent_id else False,
                    'start_date': fields.Date.today(),
                    'paid_through_date': fields.Date.today(),  # Will be updated on payment
                    'base_seats': product.subscription_tier_id.default_seats if product.ams_product_type == 'enterprise' else 0,
                    'extra_seats': 0,
                    'state': 'active',
                    'product_id': line.product_id.id,
                })

    def action_confirm(self):
        """Override: trigger subscription creation after confirming the sale."""
        res = super().action_confirm()
        self._create_ams_subscriptions()
        return res
