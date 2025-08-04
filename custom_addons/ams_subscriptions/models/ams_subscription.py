# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class AMSSubscription(models.Model):
    _inherit = 'ams.subscription'

    # Enhanced state management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('grace', 'Grace'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    # Modification tracking
    allow_modifications = fields.Boolean(
        string='Allow Modifications',
        default=True,
        help='Allow customer to upgrade/downgrade this subscription'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Pausing',
        default=True,
        help='Allow customer to pause this subscription'
    )
    
    paused_date = fields.Date(
        string='Paused Date',
        help='Date when subscription was paused'
    )
    
    pause_reason = fields.Text(
        string='Pause Reason',
        help='Reason for pausing subscription'
    )
    
    resume_date = fields.Date(
        string='Resume Date',
        help='Date when subscription should resume'
    )
    
    # Payment tracking
    payment_issues = fields.Boolean(
        string='Payment Issues',
        default=False,
        help='This subscription has payment issues'
    )
    
    last_payment_failure = fields.Datetime(
        string='Last Payment Failure'
    )
    
    last_successful_payment = fields.Datetime(
        string='Last Successful Payment'
    )
    
    # Modification history
    modification_ids = fields.One2many(
        'ams.subscription.modification',
        'subscription_id',
        string='Modification History'
    )
    
    # Current period tracking for prorations
    current_period_start = fields.Date(
        string='Current Period Start',
        help='Start date of current billing period'
    )
    
    current_period_end = fields.Date(
        string='Current Period End',
        help='End date of current billing period'
    )

    @api.depends('paid_through_date', 'tier_id.grace_days', 'tier_id.suspend_days', 'tier_id.terminate_days', 'state')
    def _compute_lifecycle_dates(self):
        """Enhanced lifecycle computation that respects paused state"""
        for sub in self:
            if sub.state == 'paused':
                # Paused subscriptions don't progress through lifecycle
                sub.grace_end_date = False
                sub.suspend_end_date = False  
                sub.terminate_date = False
            elif sub.paid_through_date and sub.tier_id:
                sub.grace_end_date = sub.paid_through_date + timedelta(days=sub.tier_id.grace_days or 30)
                sub.suspend_end_date = sub.grace_end_date + timedelta(days=sub.tier_id.suspend_days or 60)
                sub.terminate_date = sub.suspend_end_date + timedelta(days=sub.tier_id.terminate_days or 30)
            else:
                sub.grace_end_date = False
                sub.suspend_end_date = False
                sub.terminate_date = False

    def action_pause_subscription(self):
        """Pause an active subscription"""
        for sub in self:
            if sub.state != 'active':
                raise UserError(f"Can only pause active subscriptions. Current state: {sub.state}")
            
            if not sub.allow_pausing:
                raise UserError("This subscription type does not allow pausing.")
            
            # Create pause modification record
            self._create_modification_record('pause', sub.tier_id, sub.tier_id, 'Subscription paused by user')
            
            sub.write({
                'state': 'paused',
                'paused_date': fields.Date.today(),
            })
            
            sub.message_post(body="Subscription paused by user")

    def action_resume_subscription(self):
        """Resume a paused subscription"""
        for sub in self:
            if sub.state != 'paused':
                raise UserError(f"Can only resume paused subscriptions. Current state: {sub.state}")
            
            # Calculate extension of paid_through_date based on pause duration
            if sub.paused_date:
                pause_duration = fields.Date.today() - sub.paused_date
                if sub.paid_through_date:
                    sub.paid_through_date = sub.paid_through_date + pause_duration
            
            # Create resume modification record
            self._create_modification_record('resume', sub.tier_id, sub.tier_id, 'Subscription resumed by user')
            
            sub.write({
                'state': 'active',
                'resume_date': fields.Date.today(),
                'paused_date': False,
                'pause_reason': False,
            })
            
            sub.message_post(body="Subscription resumed by user")

    def action_upgrade_subscription(self):
        """Open wizard to upgrade subscription"""
        self.ensure_one()
        
        if not self.allow_modifications:
            raise UserError("This subscription does not allow modifications.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upgrade Subscription',
            'res_model': 'ams.subscription.modification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_modification_type': 'upgrade',
                'default_current_tier_id': self.tier_id.id,
            }
        }

    def action_downgrade_subscription(self):
        """Open wizard to downgrade subscription"""
        self.ensure_one()
        
        if not self.allow_modifications:
            raise UserError("This subscription does not allow modifications.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Downgrade Subscription',
            'res_model': 'ams.subscription.modification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_modification_type': 'downgrade',
                'default_current_tier_id': self.tier_id.id,
            }
        }

    def action_modify_subscription(self, new_tier_id, modification_type='upgrade'):
        """Perform subscription modification with prorated billing"""
        self.ensure_one()
        
        if not self.allow_modifications:
            raise UserError("This subscription does not allow modifications.")
        
        new_tier = self.env['ams.subscription.tier'].browse(new_tier_id)
        old_tier = self.tier_id
        
        if new_tier.subscription_type != old_tier.subscription_type:
            raise UserError("Cannot change subscription type during modification.")
        
        # Calculate proration
        proration_amount = self._calculate_proration(old_tier, new_tier, modification_type)
        
        # Create modification record
        modification = self._create_modification_record(
            modification_type, old_tier, new_tier, 
            f"Subscription {modification_type}d from {old_tier.name} to {new_tier.name}",
            proration_amount
        )
        
        # Update subscription
        self.tier_id = new_tier.id
        
        # Handle enterprise seat changes
        if new_tier.subscription_type == 'enterprise':
            self.base_seats = new_tier.default_seats
        
        # Create invoice for proration if needed
        if proration_amount != 0:
            self._create_proration_invoice(modification, proration_amount, modification_type)
        
        self.message_post(
            body=f"Subscription {modification_type}d from {old_tier.name} to {new_tier.name}. "
                 f"Proration: ${proration_amount:.2f}"
        )
        
        return modification

    def _calculate_proration(self, old_tier, new_tier, modification_type):
        """Calculate prorated amount for subscription modification"""
        self.ensure_one()
        
        # Get product prices for tiers
        old_product = self.env['product.template'].search([
            ('subscription_tier_id', '=', old_tier.id)
        ], limit=1)
        new_product = self.env['product.template'].search([
            ('subscription_tier_id', '=', new_tier.id)
        ], limit=1)
        
        if not old_product or not new_product:
            return 0.0
        
        # Calculate daily rates
        period_days = self._get_period_days(old_tier.period_length)
        old_daily_rate = old_product.list_price / period_days
        new_daily_rate = new_product.list_price / period_days
        
        # Calculate remaining days in current period
        today = fields.Date.today()
        if self.paid_through_date and self.paid_through_date > today:
            remaining_days = (self.paid_through_date - today).days
        else:
            remaining_days = 0
        
        if remaining_days <= 0:
            return 0.0
        
        # Calculate proration
        old_remaining_value = old_daily_rate * remaining_days
        new_remaining_value = new_daily_rate * remaining_days
        
        proration_amount = new_remaining_value - old_remaining_value
        
        return round(proration_amount, 2)

    def _get_period_days(self, period_length):
        """Get number of days in a billing period"""
        period_mapping = {
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
        }
        return period_mapping.get(period_length, 365)

    def _create_modification_record(self, modification_type, old_tier, new_tier, reason, proration_amount=0.0):
        """Create a record of subscription modification"""
        return self.env['ams.subscription.modification'].create({
            'subscription_id': self.id,
            'modification_type': modification_type,
            'old_tier_id': old_tier.id,
            'new_tier_id': new_tier.id,
            'modification_date': fields.Date.today(),
            'reason': reason,
            'proration_amount': proration_amount,
            'user_id': self.env.user.id,
        })

    def _create_proration_invoice(self, modification, proration_amount, modification_type):
        """Create invoice for proration amount"""
        if abs(proration_amount) < 0.01:  # Skip tiny amounts
            return
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice' if proration_amount > 0 else 'out_refund',
            'partner_id': self.partner_id.id,
            'invoice_origin': f"Subscription {modification_type}: {self.name}",
            'invoice_line_ids': [(0, 0, {
                'name': f"Subscription {modification_type} proration: {modification.old_tier_id.name} → {modification.new_tier_id.name}",
                'quantity': 1,
                'price_unit': abs(proration_amount),
                'account_id': self._get_income_account().id,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        modification.proration_invoice_id = invoice.id
        
        return invoice

    def _get_income_account(self):
        """Get income account for subscription invoices"""
        # Get from product or use default
        if self.product_id:
            return self.product_id.product_tmpl_id.get_product_accounts()['income']
        
        # Fallback to default income account
        return self.env['account.account'].search([
            ('user_type_id.name', '=', 'Income'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    def action_request_cancellation(self):
        """Request cancellation with feedback"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Subscription',
            'res_model': 'ams.subscription.cancellation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
            }
        }


class AMSSubscriptionModification(models.Model):
    """Track subscription modifications (upgrades, downgrades, pauses, etc.)"""
    _name = 'ams.subscription.modification'
    _description = 'AMS Subscription Modification'
    _order = 'modification_date desc'
    _inherit = ['mail.thread']

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('cancellation', 'Cancellation'),
        ('seat_change', 'Seat Change'),
    ], string='Modification Type', required=True)
    
    modification_date = fields.Date(
        string='Modification Date',
        default=fields.Date.today,
        required=True
    )
    
    old_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Previous Tier'
    )
    
    new_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='New Tier'
    )
    
    reason = fields.Text(
        string='Reason',
        required=True
    )
    
    proration_amount = fields.Float(
        string='Proration Amount',
        help='Amount charged/credited for the modification'
    )
    
    proration_invoice_id = fields.Many2one(
        'account.move',
        string='Proration Invoice'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Modified By',
        default=lambda self: self.env.user
    )
    
    # For seat changes
    old_seat_count = fields.Integer(string='Previous Seats')
    new_seat_count = fields.Integer(string='New Seats')


class AMSSubscriptionModificationWizard(models.TransientModel):
    """Wizard for subscription modifications"""
    _name = 'ams.subscription.modification.wizard'
    _description = 'Subscription Modification Wizard'

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True
    )
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
    ], string='Modification Type', required=True)
    
    current_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Current Tier',
        readonly=True
    )
    
    new_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='New Tier',
        required=True
    )
    
    reason = fields.Text(
        string='Reason for Change',
        required=True
    )
    
    proration_amount = fields.Float(
        string='Proration Amount',
        readonly=True,
        help='Amount that will be charged/credited'
    )
    
    proration_explanation = fields.Text(
        string='Proration Explanation',
        readonly=True
    )

    @api.onchange('new_tier_id')
    def _onchange_new_tier_id(self):
        """Calculate proration when tier changes"""
        if self.subscription_id and self.new_tier_id:
            self.proration_amount = self.subscription_id._calculate_proration(
                self.current_tier_id, self.new_tier_id, self.modification_type
            )
            
            if self.proration_amount > 0:
                self.proration_explanation = f"You will be charged ${self.proration_amount:.2f} for the upgrade."
            elif self.proration_amount < 0:
                self.proration_explanation = f"You will receive a credit of ${abs(self.proration_amount):.2f} for the downgrade."
            else:
                self.proration_explanation = "No additional charges or credits."

    def action_confirm_modification(self):
        """Confirm the subscription modification"""
        self.ensure_one()
        
        modification = self.subscription_id.action_modify_subscription(
            self.new_tier_id.id, 
            self.modification_type
        )
        
        # Update modification reason
        modification.reason = self.reason
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Subscription {self.modification_type} completed successfully!',
                'type': 'success',
                'sticky': False,
            }
        }


class AMSSubscriptionCancellationWizard(models.TransientModel):
    """Wizard for subscription cancellation with feedback"""
    _name = 'ams.subscription.cancellation.wizard'
    _description = 'Subscription Cancellation Wizard'

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True
    )
    
    cancellation_reason = fields.Selection([
        ('too_expensive', 'Too Expensive'),
        ('not_using', 'Not Using Enough'),
        ('missing_features', 'Missing Features'),
        ('poor_service', 'Poor Customer Service'),
        ('competitor', 'Found Better Alternative'),
        ('business_closed', 'Business Closed/Changed'),
        ('other', 'Other'),
    ], string='Reason for Cancellation', required=True)
    
    detailed_feedback = fields.Text(
        string='Additional Feedback',
        help='Please provide any additional details about your cancellation'
    )
    
    effective_date = fields.Selection([
        ('immediate', 'Cancel Immediately'),
        ('period_end', 'Cancel at End of Current Period'),
    ], string='When to Cancel', default='period_end', required=True)
    
    request_refund = fields.Boolean(
        string='Request Refund',
        help='Check if you would like to request a refund for unused portion'
    )

    def action_confirm_cancellation(self):
        """Confirm the subscription cancellation"""
        self.ensure_one()
        
        subscription = self.subscription_id
        
        # Create cancellation modification record
        modification = subscription._create_modification_record(
            'cancellation',
            subscription.tier_id,
            subscription.tier_id,
            f"Cancelled by customer. Reason: {dict(self._fields['cancellation_reason'].selection)[self.cancellation_reason]}. "
            f"Feedback: {self.detailed_feedback or 'None provided'}"
        )
        
        # Set cancellation based on effective date
        if self.effective_date == 'immediate':
            subscription.action_terminate()
        else:
            # Schedule cancellation at period end
            subscription.auto_renew = False
            subscription.message_post(
                body=f"Subscription scheduled for cancellation at period end ({subscription.paid_through_date}). "
                     f"Reason: {dict(self._fields['cancellation_reason'].selection)[self.cancellation_reason]}"
            )
        
        # Handle refund request
        if self.request_refund:
            # Create task/ticket for manual review
            subscription.message_post(
                body="Customer requested refund for unused portion. Manual review required.",
                message_type='notification'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Cancellation request submitted successfully. You will receive confirmation via email.',
                'type': 'success',
                'sticky': False,
            }
        }