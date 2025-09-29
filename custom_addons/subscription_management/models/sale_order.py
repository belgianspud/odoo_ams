# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    subscription_id = fields.Many2one(
        'subscription.subscription', 
        'Subscription', 
        copy=False,
        index=True,
        help='Subscription created from this sales order'
    )
    has_subscription_products = fields.Boolean(
        'Has Subscription Products', 
        compute='_compute_has_subscription_products',
        store=True,
        help='This order contains subscription products'
    )
    subscription_count = fields.Integer(
        'Subscription Count',
        compute='_compute_subscription_count'
    )
    
    @api.depends('order_line.product_id.product_tmpl_id.is_subscription')
    def _compute_has_subscription_products(self):
        """Check if order has any subscription products"""
        for order in self:
            order.has_subscription_products = any(
                line.product_id.product_tmpl_id.is_subscription 
                for line in order.order_line
            )
    
    @api.depends('subscription_id')
    def _compute_subscription_count(self):
        """Count subscriptions linked to this order"""
        for order in self:
            order.subscription_count = 1 if order.subscription_id else 0
    
    def action_confirm(self):
        """Override to create subscriptions when order is confirmed"""
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            if order.has_subscription_products and not order.subscription_id:
                try:
                    order._create_subscription_from_order()
                except Exception as e:
                    _logger.error(f"Error creating subscription from order {order.name}: {e}")
                    # Don't block the order confirmation, just log the error
                    order.message_post(
                        body=f"Warning: Could not automatically create subscription. Error: {str(e)}",
                        message_type='comment'
                    )
        
        return res
    
    def action_view_subscription(self):
        """Action to view the subscription created from this order"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_('No subscription has been created for this order yet.'))
        
        return {
            'name': _('Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }
    
    def _create_subscription_from_order(self):
        """Create subscription from sales order"""
        self.ensure_one()
        
        subscription_lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.is_subscription
        )
        
        if not subscription_lines:
            return
        
        # Group by subscription plan
        plans_data = {}
        
        for line in subscription_lines:
            product = line.product_id.product_tmpl_id
            
            # Find the subscription plan for this product
            plan = self.env['subscription.plan'].search([
                ('product_template_id', '=', product.id),
                ('active', '=', True)
            ], limit=1)
            
            if not plan:
                _logger.warning(f"No active subscription plan found for product {product.name} in order {self.name}")
                continue
            
            if plan.id not in plans_data:
                plans_data[plan.id] = {
                    'plan': plan,
                    'lines': []
                }
            
            plans_data[plan.id]['lines'].append(line)
        
        # Create subscription (we'll create only one subscription even if multiple plans)
        # You could modify this to create multiple subscriptions if needed
        if plans_data:
            plan_id = list(plans_data.keys())[0]  # Get first plan
            subscription = self._create_subscription(plans_data[plan_id]['plan'], plans_data[plan_id]['lines'])
            
            # If there are multiple plans, log a warning
            if len(plans_data) > 1:
                _logger.warning(f"Order {self.name} has multiple subscription plans. Only creating subscription for first plan.")
                self.message_post(
                    body=f"Note: This order contains multiple subscription plans. Subscription created for {plans_data[plan_id]['plan'].name}.",
                    message_type='comment'
                )
    
    def _create_subscription(self, plan, order_lines):
        """Create a single subscription from plan and order lines"""
        self.ensure_one()
        
        # Check if subscription already exists for this order
        if self.subscription_id:
            _logger.info(f"Subscription already exists for order {self.name}")
            return self.subscription_id
        
        # Check if active subscription already exists for this partner and plan
        existing = self.env['subscription.subscription'].search([
            ('partner_id', '=', self.partner_id.id),
            ('plan_id', '=', plan.id),
            ('state', 'in', ['active', 'trial'])
        ], limit=1)
        
        if existing:
            _logger.warning(f"Active subscription {existing.name} already exists for partner {self.partner_id.name} and plan {plan.name}")
            self.subscription_id = existing.id
            self.message_post(
                body=f"Cannot create new subscription: Customer already has active subscription {existing.name} for this plan.",
                message_type='notification'
            )
            raise UserError(_(
                'Customer already has an active subscription (%s) for plan %s. '
                'Please cancel or modify the existing subscription before creating a new one.'
            ) % (existing.name, plan.name))
        
        # Determine start date
        start_date = fields.Date.today()
        
        # Create subscription
        subscription_vals = {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'plan_id': plan.id,
            'date_start': start_date,
            'state': 'draft',
        }
        
        subscription = self.env['subscription.subscription'].create(subscription_vals)
        
        # Link order to subscription
        self.subscription_id = subscription.id
        
        # Create subscription lines from order lines
        for order_line in order_lines:
            self.env['subscription.line'].create({
                'subscription_id': subscription.id,
                'product_id': order_line.product_id.id,
                'name': order_line.name,
                'quantity': order_line.product_uom_qty,
                'price_unit': order_line.price_unit,
            })
        
        # Link subscription to order in chatter
        subscription.message_post(
            body=f"Subscription created from sales order <a href='#' data-oe-model='sale.order' data-oe-id='{self.id}'>{self.name}</a>",
            message_type='notification'
        )
        
        self.message_post(
            body=f"Subscription <a href='#' data-oe-model='subscription.subscription' data-oe-id='{subscription.id}'>{subscription.name}</a> created",
            message_type='notification'
        )
        
        # Determine whether to start trial or activate immediately
        # Only activate if order is paid or invoiced
        if self.invoice_status == 'invoiced':
            # Check if any invoice is paid
            paid_invoices = self.invoice_ids.filtered(lambda inv: inv.payment_state == 'paid')
            if paid_invoices:
                if plan.trial_period > 0:
                    subscription.action_start_trial()
                else:
                    subscription.action_activate()
                
                # Send welcome email
                send_welcome = self.env['ir.config_parameter'].sudo().get_param(
                    'subscription.send_welcome_email', 'True'
                )
                if send_welcome == 'True':
                    template = self.env.ref(
                        'subscription_management.email_template_subscription_welcome',
                        raise_if_not_found=False
                    )
                    if template:
                        template.send_mail(subscription.id, force_send=False)
        
        _logger.info(f"Created subscription {subscription.name} from order {self.name}")
        
        return subscription


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    is_subscription = fields.Boolean(
        related='product_id.product_tmpl_id.is_subscription',
        string='Is Subscription',
        store=True
    )
    subscription_plan_id = fields.Many2one(
        'subscription.plan',
        string='Subscription Plan',
        compute='_compute_subscription_plan',
        store=True
    )
    
    @api.depends('product_id', 'is_subscription')
    def _compute_subscription_plan(self):
        """Get the subscription plan for this product"""
        for line in self:
            if line.is_subscription:
                plan = self.env['subscription.plan'].search([
                    ('product_template_id', '=', line.product_id.product_tmpl_id.id),
                    ('active', '=', True)
                ], limit=1)
                line.subscription_plan_id = plan.id
            else:
                line.subscription_plan_id = False
    
    @api.onchange('product_id')
    def _onchange_product_id_subscription(self):
        """Update description for subscription products"""
        if self.is_subscription and self.subscription_plan_id:
            plan = self.subscription_plan_id
            
            # Add subscription details to the line description
            description_parts = [self.name]
            
            if plan.billing_period:
                description_parts.append(f"Billing: {plan.billing_period}")
            
            if plan.trial_period > 0:
                description_parts.append(f"Trial: {plan.trial_period} days")
            
            self.name = " - ".join(description_parts)