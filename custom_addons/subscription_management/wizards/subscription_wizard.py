# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class SubscriptionWizard(models.TransientModel):
    _name = 'subscription.wizard'
    _description = 'Subscription Management Wizard'

    action_type = fields.Selection([
        ('create', 'Create Subscription'),
        ('modify', 'Modify Subscription'),
        ('cancel', 'Cancel Subscription'),
        ('suspend', 'Suspend Subscription'),
        ('renew', 'Renew Subscription'),
        ('change_plan', 'Change Plan'),
    ], string='Action', required=True)

    # Customer Information
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    
    # Plan Information
    plan_id = fields.Many2one('subscription.plan', 'Subscription Plan', required=True)
    new_plan_id = fields.Many2one('subscription.plan', 'New Plan')
    
    # Subscription Information
    subscription_id = fields.Many2one('subscription.subscription', 'Subscription')
    start_date = fields.Date('Start Date', default=fields.Date.today)
    end_date = fields.Date('End Date')
    
    # Pricing
    price_override = fields.Float('Price Override')
    use_price_override = fields.Boolean('Override Price')
    
    # Options
    send_email = fields.Boolean('Send Email Notification', default=True)
    create_invoice = fields.Boolean('Create Invoice Immediately', default=True)
    prorate_billing = fields.Boolean('Prorate Billing', default=True)
    
    # Cancellation/Suspension Reason
    reason = fields.Text('Reason')
    effective_date = fields.Date('Effective Date', default=fields.Date.today)
    
    # Results
    result_subscription_id = fields.Many2one('subscription.subscription', 'Result Subscription', readonly=True)
    result_message = fields.Text('Result Message', readonly=True)

    @api.onchange('action_type')
    def _onchange_action_type(self):
        if self.action_type in ('modify', 'cancel', 'suspend', 'renew', 'change_plan'):
            # Get subscription from context
            subscription_id = self.env.context.get('active_id')
            if subscription_id:
                self.subscription_id = subscription_id
                subscription = self.env['subscription.subscription'].browse(subscription_id)
                self.partner_id = subscription.partner_id
                self.plan_id = subscription.plan_id

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        if self.plan_id and not self.use_price_override:
            self.price_override = self.plan_id.price

    def action_execute(self):
        """Execute the selected action"""
        if self.action_type == 'create':
            return self._action_create_subscription()
        elif self.action_type == 'modify':
            return self._action_modify_subscription()
        elif self.action_type == 'cancel':
            return self._action_cancel_subscription()
        elif self.action_type == 'suspend':
            return self._action_suspend_subscription()
        elif self.action_type == 'renew':
            return self._action_renew_subscription()
        elif self.action_type == 'change_plan':
            return self._action_change_plan()

    def _action_create_subscription(self):
        """Create new subscription"""
        subscription_vals = {
            'partner_id': self.partner_id.id,
            'plan_id': self.plan_id.id,
            'date_start': self.start_date,
            'date_end': self.end_date,
        }
        
        subscription = self.env['subscription.subscription'].create(subscription_vals)
        
        # Override price if requested
        if self.use_price_override:
            subscription.write({'price': self.price_override})
        
        # Start trial or activate
        if self.plan_id.trial_period > 0:
            subscription.action_start_trial()
        else:
            subscription.action_activate()
        
        # Create invoice if requested
        if self.create_invoice:
            subscription._create_initial_invoice()
        
        # Send email if requested
        if self.send_email:
            self._send_notification_email(subscription, 'welcome')
        
        self.result_subscription_id = subscription
        self.result_message = f"Subscription {subscription.name} created successfully"
        
        return self._return_result_action()

    def _action_modify_subscription(self):
        """Modify existing subscription"""
        if not self.subscription_id:
            raise UserError(_("No subscription selected"))
        
        # Update subscription
        vals = {}
        if self.end_date:
            vals['date_end'] = self.end_date
        if self.use_price_override:
            vals['price'] = self.price_override
        
        if vals:
            self.subscription_id.write(vals)
        
        self.result_subscription_id = self.subscription_id
        self.result_message = f"Subscription {self.subscription_id.name} modified successfully"
        
        return self._return_result_action()

    def _action_cancel_subscription(self):
        """Cancel subscription"""
        if not self.subscription_id:
            raise UserError(_("No subscription selected"))
        
        # Set effective date
        if self.effective_date:
            self.subscription_id.date_end = self.effective_date
        
        self.subscription_id.action_cancel()
        
        # Add reason to chatter
        if self.reason:
            self.subscription_id.message_post(
                body=f"Cancellation reason: {self.reason}",
                message_type='comment'
            )
        
        # Send email if requested
        if self.send_email:
            self._send_notification_email(self.subscription_id, 'cancelled')
        
        self.result_subscription_id = self.subscription_id
        self.result_message = f"Subscription {self.subscription_id.name} cancelled"
        
        return self._return_result_action()

    def _action_suspend_subscription(self):
        """Suspend subscription"""
        if not self.subscription_id:
            raise UserError(_("No subscription selected"))
        
        self.subscription_id.action_suspend()
        
        # Add reason to chatter
        if self.reason:
            self.subscription_id.message_post(
                body=f"Suspension reason: {self.reason}",
                message_type='comment'
            )
        
        self.result_subscription_id = self.subscription_id
        self.result_message = f"Subscription {self.subscription_id.name} suspended"
        
        return self._return_result_action()

    def _action_renew_subscription(self):
        """Renew subscription"""
        if not self.subscription_id:
            raise UserError(_("No subscription selected"))
        
        self.subscription_id.action_renew()
        
        self.result_subscription_id = self.subscription_id
        self.result_message = f"Subscription {self.subscription_id.name} renewed"
        
        return self._return_result_action()

    def _action_change_plan(self):
        """Change subscription plan"""
        if not self.subscription_id or not self.new_plan_id:
            raise UserError(_("Subscription and new plan must be selected"))
        
        old_plan = self.subscription_id.plan_id
        
        # Calculate prorated amount if needed
        prorated_amount = 0
        if self.prorate_billing:
            prorated_amount = self._calculate_proration(old_plan, self.new_plan_id)
        
        # Update subscription
        self.subscription_id.write({
            'plan_id': self.new_plan_id.id,
            'price': self.price_override if self.use_price_override else self.new_plan_id.price,
        })
        
        # Create prorated invoice if needed
        if prorated_amount != 0 and self.create_invoice:
            self._create_proration_invoice(prorated_amount)
        
        # Add note to chatter
        self.subscription_id.message_post(
            body=f"Plan changed from {old_plan.name} to {self.new_plan_id.name}",
            message_type='comment'
        )
        
        self.result_subscription_id = self.subscription_id
        self.result_message = f"Plan changed to {self.new_plan_id.name}"
        
        return self._return_result_action()

    def _calculate_proration(self, old_plan, new_plan):
        """Calculate prorated amount for plan change"""
        # This is a simplified proration calculation
        # In practice, you might want more sophisticated logic
        price_difference = new_plan.price - old_plan.price
        
        # Calculate remaining days in current billing period
        if self.subscription_id.next_billing_date:
            today = fields.Date.today()
            remaining_days = (self.subscription_id.next_billing_date - today).days
            
            # Calculate daily rate and proration
            if old_plan.billing_period == 'monthly':
                total_days = 30
            elif old_plan.billing_period == 'yearly':
                total_days = 365
            else:
                total_days = 30  # Default
            
            proration_factor = remaining_days / total_days
            return price_difference * proration_factor
        
        return price_difference

    def _create_proration_invoice(self, amount):
        """Create prorated invoice for plan change"""
        if amount == 0:
            return
        
        invoice_vals = {
            'move_type': 'out_invoice' if amount > 0 else 'out_refund',
            'partner_id': self.subscription_id.partner_id.id,
            'subscription_id': self.subscription_id.id,
            'invoice_origin': f"Plan change - {self.subscription_id.name}",
            'invoice_line_ids': [(0, 0, {
                'name': f"Plan change proration: {self.plan_id.name} → {self.new_plan_id.name}",
                'quantity': 1,
                'price_unit': abs(amount),
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice

    def _send_notification_email(self, subscription, email_type):
        """Send notification email"""
        template_mapping = {
            'welcome': 'subscription_management.email_template_subscription_welcome',
            'cancelled': 'subscription_management.email_template_subscription_cancelled',
        }
        
        template_ref = template_mapping.get(email_type)
        if template_ref:
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(subscription.id, force_send=True)

    def _return_result_action(self):
        """Return action to show result"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'res_id': self.result_subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }