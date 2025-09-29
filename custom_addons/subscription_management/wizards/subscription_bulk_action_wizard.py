# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionBulkActionWizard(models.TransientModel):
    _name = 'subscription.bulk.action.wizard'
    _description = 'Bulk Subscription Actions'

    action = fields.Selection([
        ('suspend', 'Suspend Subscriptions'),
        ('activate', 'Activate Subscriptions'),
        ('cancel', 'Cancel Subscriptions'),
        ('send_reminder', 'Send Billing Reminders'),
        ('update_price', 'Update Prices'),
    ], string='Action', required=True)

    subscription_ids = fields.Many2many('subscription.subscription', string='Subscriptions')
    reason = fields.Text('Reason')
    new_price = fields.Float('New Price')
    price_increase_percent = fields.Float('Price Increase (%)')
    send_email = fields.Boolean('Send Email Notifications', default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        subscription_ids = self.env.context.get('active_ids', [])
        res['subscription_ids'] = [(6, 0, subscription_ids)]
        return res

    def action_execute_bulk(self):
        """Execute bulk action"""
        if not self.subscription_ids:
            raise UserError(_("No subscriptions selected"))

        if self.action == 'suspend':
            return self._bulk_suspend()
        elif self.action == 'activate':
            return self._bulk_activate()
        elif self.action == 'cancel':
            return self._bulk_cancel()
        elif self.action == 'send_reminder':
            return self._bulk_send_reminders()
        elif self.action == 'update_price':
            return self._bulk_update_price()

    def _bulk_suspend(self):
        """Bulk suspend subscriptions"""
        count = 0
        for subscription in self.subscription_ids:
            if subscription.state in ('active', 'trial'):
                subscription.action_suspend()
                if self.reason:
                    subscription.message_post(
                        body=f"Bulk suspension: {self.reason}",
                        message_type='comment'
                    )
                count += 1
        
        return self._show_result_message(f"{count} subscriptions suspended")

    def _bulk_activate(self):
        """Bulk activate subscriptions"""
        count = 0
        for subscription in self.subscription_ids:
            if subscription.state in ('draft', 'suspended'):
                subscription.action_activate()
                count += 1
        
        return self._show_result_message(f"{count} subscriptions activated")

    def _bulk_cancel(self):
        """Bulk cancel subscriptions"""
        count = 0
        for subscription in self.subscription_ids:
            if subscription.state not in ('cancelled', 'expired'):
                subscription.action_cancel()
                if self.reason:
                    subscription.message_post(
                        body=f"Bulk cancellation: {self.reason}",
                        message_type='comment'
                    )
                count += 1
        
        return self._show_result_message(f"{count} subscriptions cancelled")

    def _bulk_send_reminders(self):
        """Bulk send billing reminders"""
        template = self.env.ref('subscription_management.email_template_subscription_billing_reminder', 
                               raise_if_not_found=False)
        count = 0
        
        if template:
            for subscription in self.subscription_ids:
                if subscription.state == 'active':
                    template.send_mail(subscription.id, force_send=False)
                    count += 1
        
        return self._show_result_message(f"Billing reminders sent to {count} customers")

    def _bulk_update_price(self):
        """Bulk update subscription prices"""
        count = 0
        for subscription in self.subscription_ids:
            if self.new_price > 0:
                subscription.write({'price': self.new_price})
            elif self.price_increase_percent != 0:
                new_price = subscription.price * (1 + self.price_increase_percent / 100)
                subscription.write({'price': new_price})
            
            subscription.message_post(
                body=f"Price updated via bulk action",
                message_type='comment'
            )
            count += 1
        
        return self._show_result_message(f"{count} subscription prices updated")

    def _show_result_message(self, message):
        """Show result message"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Action Completed'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }