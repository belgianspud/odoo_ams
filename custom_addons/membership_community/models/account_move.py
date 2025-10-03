# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Extend account.move to auto-activate membership subscriptions on payment
    """
    _inherit = 'account.move'

    def _post(self, soft=True):
        """Override post to activate memberships when invoice is posted and paid"""
        result = super()._post(soft=soft)
        
        for move in self:
            # Only process customer invoices that are paid
            if move.move_type == 'out_invoice' and move.payment_state in ('paid', 'in_payment'):
                # Find related membership subscriptions
                subscriptions = self.env['subscription.subscription'].search([
                    ('invoice_ids', 'in', move.ids),
                    ('is_membership', '=', True),
                    ('state', '=', 'draft')
                ])
                
                if subscriptions:
                    _logger.info(f"Auto-activating {len(subscriptions)} membership subscriptions from paid invoice {move.name}")
                    for subscription in subscriptions:
                        subscription.action_confirm()
        
        return result

    def _invoice_paid_hook(self):
        """Hook called when invoice payment state changes to paid"""
        result = super()._invoice_paid_hook() if hasattr(super(), '_invoice_paid_hook') else None
    
        for move in self:
            if move.move_type == 'out_invoice' and move.payment_state == 'paid':
                # Find related membership subscriptions in draft state
                subscriptions = self.env['subscription.subscription'].search([
                    ('invoice_ids', 'in', move.ids),
                    ('is_membership', '=', True),
                    ('state', '=', 'draft')
                ])
            
                # ALSO check if this invoice came from a sale order with subscription
                if not subscriptions and move.invoice_origin:
                    sale_order = self.env['sale.order'].search([
                        ('name', '=', move.invoice_origin)
                    ], limit=1)
                
                    if sale_order and sale_order.subscription_id:
                        subscriptions = sale_order.subscription_id.filtered(
                            lambda s: s.is_membership and s.state == 'draft'
                        )
            
                if subscriptions:
                    _logger.info(f"Invoice {move.name} paid - activating {len(subscriptions)} membership subscriptions")
                    for subscription in subscriptions:
                        try:
                            # Activate subscription
                            if subscription.plan_id.trial_period > 0:
                                subscription.action_start_trial()
                            else:
                                subscription.action_activate()
                        
                            _logger.info(f"Activated subscription {subscription.name} for member {subscription.partner_id.name}")
                        
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
                        
                        except Exception as e:
                            _logger.error(f"Failed to activate subscription {subscription.name}: {str(e)}")
    
        return result


class AccountPayment(models.Model):
    """
    Extend account.payment to activate memberships when payment is posted
    """
    _inherit = 'account.payment'

    def action_post(self):
        """Override to activate membership subscriptions when payment is posted"""
        result = super().action_post()
        
        for payment in self:
            # Get related invoices
            reconciled_invoices = payment.reconciled_invoice_ids
            
            for invoice in reconciled_invoices:
                if invoice.move_type == 'out_invoice' and invoice.payment_state == 'paid':
                    # Find related membership subscriptions
                    subscriptions = self.env['subscription.subscription'].search([
                        ('invoice_ids', 'in', invoice.ids),
                        ('is_membership', '=', True),
                        ('state', '=', 'draft')
                    ])
                    
                    if subscriptions:
                        _logger.info(f"Payment posted for invoice {invoice.name} - activating {len(subscriptions)} memberships")
                        for subscription in subscriptions:
                            try:
                                subscription.action_confirm()
                                _logger.info(f"Activated subscription {subscription.name} for member {subscription.partner_id.name}")
                            except Exception as e:
                                _logger.error(f"Failed to activate subscription {subscription.name}: {str(e)}")
        
        return result