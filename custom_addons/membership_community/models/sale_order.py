# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """
    Extend Sale Order to handle membership product invoicing and activation
    """
    _inherit = 'sale.order'
    
    def action_confirm(self):
        """Override to create invoice immediately for membership products"""
        res = super().action_confirm()
        
        for order in self:
            # Check if order has membership products
            has_membership = any(
                line.product_id.product_tmpl_id.is_membership_product 
                for line in order.order_line
            )
            
            if has_membership and order.subscription_id:
                # Create invoice immediately for membership subscriptions
                if not order.invoice_ids:
                    try:
                        # Create invoice
                        invoice = order._create_invoices()
                        
                        if invoice:
                            # Auto-post the invoice
                            invoice.action_post()
                            
                            _logger.info(
                                f"Auto-created and posted invoice {invoice.name} "
                                f"for membership order {order.name}"
                            )
                            
                            # Link invoice to subscription
                            if order.subscription_id:
                                order.subscription_id.write({
                                    'last_invoice_id': invoice.id,
                                    'last_invoice_date': fields.Date.today(),
                                })
                                
                                # Add note to subscription
                                order.subscription_id.message_post(
                                    body=f"Invoice {invoice.name} created and posted from order {order.name}",
                                    message_type='notification'
                                )
                                
                    except Exception as e:
                        _logger.error(
                            f"Failed to auto-create invoice for order {order.name}: {e}"
                        )
                        order.message_post(
                            body=f"⚠️ Warning: Could not auto-create invoice. "
                                 f"Please create invoice manually to activate membership. Error: {str(e)}",
                            message_type='notification'
                        )
                        
                        # Still allow order confirmation to proceed
                        pass
        
        return res