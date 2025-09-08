# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class AMSSubscriptionCancellationWizard(models.TransientModel):
    """Wizard for subscription cancellation with feedback"""
    _name = 'ams.subscription.cancellation.wizard'
    _description = 'Subscription Cancellation Wizard'

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    # Display fields for context
    subscription_name = fields.Char(
        related='subscription_id.name',
        string='Subscription Name',
        readonly=True
    )
    
    subscription_state = fields.Selection(
        related='subscription_id.state',
        string='Current Status',
        readonly=True
    )
    
    paid_through_date = fields.Date(
        related='subscription_id.paid_through_date',
        string='Paid Through Date',
        readonly=True
    )
    
    tier_name = fields.Char(
        related='subscription_id.tier_id.name',
        string='Current Tier',
        readonly=True
    )
    
    # Cancellation details
    cancellation_reason = fields.Selection([
        ('too_expensive', 'Too Expensive'),
        ('not_using', 'Not Using Enough'),
        ('missing_features', 'Missing Features'),
        ('poor_service', 'Poor Customer Service'),
        ('competitor', 'Found Better Alternative'),
        ('business_closed', 'Business Closed/Changed'),
        ('technical_issues', 'Technical Issues'),
        ('other', 'Other'),
    ], string='Primary Reason for Cancellation', required=True,
       help='Please select the main reason for cancelling your subscription')
    
    detailed_feedback = fields.Text(
        string='Additional Feedback',
        help='Please provide any additional details that could help us improve our service'
    )
    
    effective_date = fields.Selection([
        ('immediate', 'Cancel Immediately'),
        ('period_end', 'Cancel at End of Current Period'),
    ], string='When to Cancel', default='period_end', required=True,
       help='Choose when the cancellation should take effect')
    
    request_refund = fields.Boolean(
        string='Request Refund',
        help='Check if you would like to request a refund for the unused portion (subject to terms and conditions)'
    )
    
    # Calculated fields
    refund_eligible_amount = fields.Float(
        string='Estimated Refund Amount',
        compute='_compute_refund_amount',
        help='Estimated refund amount if cancelling immediately'
    )
    
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_days_remaining',
        help='Days remaining in current billing period'
    )
    
    # Confirmation fields
    confirm_understanding = fields.Boolean(
        string='I understand that cancelling my subscription may result in immediate loss of access to services',
        required=True
    )
    
    confirm_no_reversal = fields.Boolean(
        string='I understand that this cancellation may not be reversible',
        required=True
    )

    @api.depends('subscription_id.paid_through_date', 'effective_date')
    def _compute_days_remaining(self):
        """Calculate days remaining in current period"""
        for wizard in self:
            if wizard.subscription_id.paid_through_date:
                today = fields.Date.today()
                if wizard.subscription_id.paid_through_date > today:
                    wizard.days_remaining = (wizard.subscription_id.paid_through_date - today).days
                else:
                    wizard.days_remaining = 0
            else:
                wizard.days_remaining = 0

    @api.depends('subscription_id', 'days_remaining', 'effective_date')
    def _compute_refund_amount(self):
        """Calculate estimated refund amount"""
        for wizard in self:
            wizard.refund_eligible_amount = 0.0
            
            if wizard.effective_date == 'immediate' and wizard.days_remaining > 0:
                # Simple calculation - could be enhanced with actual product pricing
                subscription = wizard.subscription_id
                if subscription.product_id and subscription.tier_id:
                    # Get the product price
                    product_price = subscription.product_id.list_price
                    
                    # Calculate daily rate based on period
                    period_days = wizard._get_period_days(subscription.tier_id.period_length)
                    daily_rate = product_price / period_days if period_days > 0 else 0
                    
                    # Calculate refund for remaining days
                    wizard.refund_eligible_amount = daily_rate * wizard.days_remaining

    def _get_period_days(self, period_length):
        """Get number of days in a billing period"""
        period_mapping = {
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
        }
        return period_mapping.get(period_length, 365)

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        subscription_id = self.env.context.get('default_subscription_id')
        if subscription_id:
            res['subscription_id'] = subscription_id
        
        return res

    @api.onchange('effective_date')
    def _onchange_effective_date(self):
        """Update refund calculation when effective date changes"""
        self._compute_refund_amount()

    def action_confirm_cancellation(self):
        """Confirm the subscription cancellation"""
        self.ensure_one()
        
        # Validate inputs
        if not self.confirm_understanding or not self.confirm_no_reversal:
            raise UserError("Please confirm your understanding of the cancellation terms.")
        
        if not self.subscription_id:
            raise UserError("No subscription selected for cancellation.")
        
        if self.subscription_id.state in ['terminated', 'cancelled']:
            raise UserError("This subscription is already cancelled or terminated.")
        
        subscription = self.subscription_id
        
        try:
            # Create cancellation modification record
            modification_vals = {
                'subscription_id': subscription.id,
                'modification_type': 'cancellation',
                'old_tier_id': subscription.tier_id.id,
                'new_tier_id': subscription.tier_id.id,
                'reason': self._build_cancellation_reason(),
                'modification_date': fields.Date.today(),
                'user_id': self.env.user.id,
            }
            
            modification = self.env['ams.subscription.modification'].create(modification_vals)
            modification.action_confirm()
            
            # Process cancellation based on effective date
            if self.effective_date == 'immediate':
                # Cancel immediately
                subscription.action_terminate()
                modification.action_apply()
                message = "Your subscription has been cancelled immediately."
            else:
                # Schedule cancellation at period end
                subscription.auto_renew = False
                subscription.message_post(
                    body=f"Subscription scheduled for cancellation at period end ({subscription.paid_through_date}). "
                         f"Reason: {dict(self._fields['cancellation_reason'].selection)[self.cancellation_reason]}"
                )
                message = f"Your subscription will be cancelled on {subscription.paid_through_date}. You will retain access until then."
            
            # Handle refund request
            if self.request_refund and self.refund_eligible_amount > 0:
                self._process_refund_request(modification)
                message += " Your refund request has been submitted for review."
            
            # Send notification email (if email templates are configured)
            self._send_cancellation_notification()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"An error occurred while cancelling the subscription: {str(e)}")

    def _build_cancellation_reason(self):
        """Build comprehensive cancellation reason text"""
        reason_text = f"Cancelled by customer via portal.\n"
        reason_text += f"Primary reason: {dict(self._fields['cancellation_reason'].selection)[self.cancellation_reason]}\n"
        
        if self.detailed_feedback:
            reason_text += f"Additional feedback: {self.detailed_feedback}\n"
        
        reason_text += f"Effective date: {self.effective_date}\n"
        
        if self.request_refund:
            reason_text += f"Refund requested: ${self.refund_eligible_amount:.2f}\n"
        
        return reason_text

    def _process_refund_request(self, modification):
        """Process refund request - create task or notification for manual review"""
        # Create a message for manual review
        self.subscription_id.message_post(
            body=f"Refund request submitted by customer.\n"
                 f"Estimated amount: ${self.refund_eligible_amount:.2f}\n"
                 f"Reason: {self.cancellation_reason}\n"
                 f"Manual review required.",
            message_type='notification'
        )
        
        # Could also create a task in project management or helpdesk ticket
        # This depends on what other modules you have installed

    def _send_cancellation_notification(self):
        """Send cancellation confirmation email to customer"""
        # This would use email templates if configured
        # For now, just log the notification
        self.subscription_id.message_post(
            body="Cancellation confirmation email should be sent to customer",
            message_type='notification'
        )

    def action_cancel(self):
        """Cancel the cancellation wizard without making changes"""
        return {'type': 'ir.actions.act_window_close'}

    def action_review_terms(self):
        """Show terms and conditions (could link to external page)"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/terms-and-conditions',  # Adjust URL as needed
            'target': 'new',
        }

    @api.onchange('cancellation_reason')
    def _onchange_cancellation_reason(self):
        """Provide helpful prompts based on cancellation reason"""
        if self.cancellation_reason == 'too_expensive':
            return {
                'warning': {
                    'title': 'Wait!',
                    'message': 'Before you cancel, check if there are any available discounts or lower-tier options that might work for you. Contact our support team for assistance.'
                }
            }
        elif self.cancellation_reason == 'missing_features':
            return {
                'warning': {
                    'title': 'Tell us more!',
                    'message': 'We\'d love to hear what features you\'re looking for. Your feedback helps us improve our service for everyone.'
                }
            }
        elif self.cancellation_reason == 'technical_issues':
            return {
                'warning': {
                    'title': 'Let us help!',
                    'message': 'Our technical support team might be able to resolve these issues quickly. Consider contacting support before cancelling.'
                }
            }