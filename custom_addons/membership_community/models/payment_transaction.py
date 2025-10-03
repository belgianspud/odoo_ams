# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    """
    Extend payment.transaction to activate subscriptions when payment is confirmed
    """
    _inherit = 'payment.transaction'

    def _reconcile_after_done(self):
        """Override to activate memberships after payment is reconciled"""
        res = super()._reconcile_after_done()
        
        for transaction in self:
            # Find related sale orders
            if transaction.sale_order_ids:
                for order in transaction.sale_order_ids:
                    # Check if order has subscription
                    if order.subscription_id:
                        subscription = order.subscription_id
                        
                        # Activate subscription if payment is confirmed
                        if (transaction.state == 'done' and 
                            subscription.state == 'draft'):
                            
                            try:
                                # Activate the subscription
                                if subscription.plan_id.trial_period > 0:
                                    subscription.action_start_trial()
                                else:
                                    subscription.action_activate()
                                
                                _logger.info(
                                    f"Activated subscription {subscription.name} "
                                    f"from payment transaction {transaction.reference}"
                                )
                                
                                # Add note to subscription chatter
                                subscription.message_post(
                                    body=f"Subscription activated from payment transaction {transaction.reference}",
                                    message_type='notification'
                                )
                                
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
                                            _logger.error(f"Failed to send welcome email: {e}")
                                
                                # Assign member number if needed
                                if subscription.is_membership and not subscription.partner_id.member_number:
                                    member_number = self.env['ir.sequence'].next_by_code('member.number')
                                    if member_number:
                                        subscription.partner_id.member_number = member_number
                                        _logger.info(
                                            f"Assigned member number {member_number} to {subscription.partner_id.name}"
                                        )
                                
                                # Set join date if not set
                                if subscription.is_membership and not subscription.join_date:
                                    subscription.join_date = subscription.date_start or fields.Date.today()
                                
                            except Exception as e:
                                _logger.error(
                                    f"Failed to activate subscription {subscription.name}: {e}"
                                )
                                # Post error to subscription chatter
                                subscription.message_post(
                                    body=f"⚠️ Automatic activation failed: {str(e)}. Please activate manually.",
                                    message_type='notification'
                                )
        
        return res