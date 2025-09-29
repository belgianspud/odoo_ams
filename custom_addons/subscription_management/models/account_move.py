# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    subscription_id = fields.Many2one(
        'subscription.subscription',
        'Subscription',
        copy=False,
        index=True,
        help='Subscription linked to this invoice'
    )
    
    def _post(self, soft=True):
        """Override to create subscriptions when invoice is posted"""
        res = super()._post(soft=soft)
        
        for move in self:
            if move.move_type == 'out_invoice' and move.state == 'posted':
                try:
                    move._create_subscriptions_from_invoice()
                except Exception as e:
                    _logger.error(f"Error creating subscription from invoice {move.name}: {e}")
        
        return res
    
    def _create_subscriptions_from_invoice(self):
        """Create subscriptions from invoice lines with subscription products"""
        self.ensure_one()
        
        # Only process customer invoices
        if self.move_type != 'out_invoice':
            return
        
        # Check if invoice already has a subscription
        if self.subscription_id:
            _logger.info(f"Invoice {self.name} already linked to subscription {self.subscription_id.name}")
            return
        
        # Find invoice lines with subscription products
        subscription_lines = self.invoice_line_ids.filtered(
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
                _logger.warning(f"No active subscription plan found for product {product.name}")
                continue
            
            if plan.id not in plans_data:
                plans_data[plan.id] = {
                    'plan': plan,
                    'lines': []
                }
            
            plans_data[plan.id]['lines'].append(line)
        
        # Create subscription (we'll create only one subscription even if multiple plans)
        if plans_data:
            plan_id = list(plans_data.keys())[0]
            subscription = self._create_subscription(plans_data[plan_id]['plan'], plans_data[plan_id]['lines'])
            
            if len(plans_data) > 1:
                _logger.warning(f"Invoice {self.name} has multiple subscription plans. Only creating subscription for first plan.")
    
    def _create_subscription(self, plan, invoice_lines):
        """Create a single subscription from plan and invoice lines"""
        self.ensure_one()
        
        # Check if subscription already exists from sales order
        if self.invoice_origin:
            # Check if this invoice came from a sales order
            sale_order = self.env['sale.order'].search([
                ('name', '=', self.invoice_origin)
            ], limit=1)
            
            if sale_order and sale_order.subscription_id:
                _logger.info(f"Subscription {sale_order.subscription_id.name} already exists from order {sale_order.name}. Linking to invoice.")
                self.subscription_id = sale_order.subscription_id
                return sale_order.subscription_id
        
        # Check if active subscription already exists for this partner and plan
        existing = self.env['subscription.subscription'].search([
            ('partner_id', '=', self.partner_id.id),
            ('plan_id', '=', plan.id),
            ('state', 'in', ['draft', 'trial', 'active'])
        ], limit=1)
        
        if existing:
            _logger.info(f"Active subscription {existing.name} already exists for partner {self.partner_id.name} and plan {plan.name}")
            self.subscription_id = existing.id
            return existing
        
        # Determine start date
        start_date = fields.Date.today()
        
        # Create subscription
        subscription_vals = {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'plan_id': plan.id,
            'date_start': start_date,
            'state': 'draft',
            'company_id': self.company_id.id,
        }
        
        subscription = self.env['subscription.subscription'].create(subscription_vals)
        
        # Link invoice to subscription
        self.subscription_id = subscription.id
        
        # Create subscription lines from invoice lines
        for invoice_line in invoice_lines:
            self.env['subscription.line'].create({
                'subscription_id': subscription.id,
                'product_id': invoice_line.product_id.id,
                'name': invoice_line.name,
                'quantity': invoice_line.quantity,
                'price_unit': invoice_line.price_unit,
            })
        
        # Activate subscription immediately if invoice is paid
        if self.payment_state in ['paid', 'in_payment']:
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
                    try:
                        template.send_mail(subscription.id, force_send=False)
                        _logger.info(f"Sent welcome email for subscription {subscription.name}")
                    except Exception as e:
                        _logger.error(f"Failed to send welcome email for subscription {subscription.name}: {e}")
        
        _logger.info(f"Created subscription {subscription.name} for partner {self.partner_id.name}")
        
        return subscription
    
    def button_draft(self):
        """Override to handle subscription when invoice is reset to draft"""
        res = super().button_draft()
        
        for move in self:
            if move.subscription_id and move.subscription_id.state == 'draft':
                # Optionally handle subscription state
                pass
        
        return res
    
    def button_cancel(self):
        """Override to handle subscription when invoice is cancelled"""
        res = super().button_cancel()
        
        for move in self:
            if move.subscription_id:
                # Optionally suspend or cancel subscription
                if move.subscription_id.state in ['draft', 'trial']:
                    move.subscription_id.message_post(
                        body=f"Related invoice {move.name} was cancelled.",
                        message_type='notification'
                    )
        
        return res
    
    def _register_payment(self, payment_vals_list):
        """Override to activate subscription when payment is registered"""
        res = super()._register_payment(payment_vals_list)
        
        for move in self:
            if move.subscription_id and move.subscription_id.state == 'draft':
                if move.payment_state in ['paid', 'in_payment']:
                    # Activate subscription
                    if move.subscription_id.plan_id.trial_period > 0:
                        move.subscription_id.action_start_trial()
                    else:
                        move.subscription_id.action_activate()
                    
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
                            try:
                                template.send_mail(move.subscription_id.id, force_send=False)
                            except Exception as e:
                                _logger.error(f"Failed to send welcome email: {e}")
        
        return res