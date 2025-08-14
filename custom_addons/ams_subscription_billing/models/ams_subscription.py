# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    """Extend AMS Subscription with Billing Functionality"""
    _inherit = 'ams.subscription'

    # =============================================================================
    # BILLING CONFIGURATION FIELDS
    # =============================================================================
    
    # Auto-Billing Settings
    enable_auto_billing = fields.Boolean(
        string='Enable Auto Billing',
        default=True,
        help='Automatically generate invoices for this subscription',
        tracking=True
    )
    
    enable_auto_payment = fields.Boolean(
        string='Enable Auto Payment',
        default=False,
        help='Automatically attempt payment processing',
        tracking=True
    )
    
    auto_send_invoices = fields.Boolean(
        string='Auto Send Invoices',
        default=True,
        help='Automatically send invoices to customer'
    )
    
    # Payment Configuration
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Default Payment Method',
        help='Stored payment method for auto-billing'
    )
    
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Terms',
        help='Payment terms for this subscription'
    )
    
    # Billing Calendar
    billing_day = fields.Integer(
        string='Billing Day',
        default=1,
        help='Preferred day of month for billing (1-28)'
    )
    
    next_billing_date = fields.Date(
        string='Next Billing Date',
        index=True,
        tracking=True,
        help='Date when next invoice will be generated'
    )
    
    last_billing_date = fields.Date(
        string='Last Billing Date',
        readonly=True,
        help='Date of last successful billing'
    )
    
    # Dunning Configuration
    dunning_sequence_id = fields.Many2one(
        'ams.dunning.sequence',
        string='Dunning Sequence',
        help='Dunning sequence to use for payment failures'
    )
    
    skip_dunning = fields.Boolean(
        string='Skip Dunning Process',
        default=False,
        help='Skip dunning process for this subscription'
    )
    
    # =============================================================================
    # BILLING STATUS AND STATISTICS
    # =============================================================================
    
    # Payment Status
    payment_status = fields.Selection([
        ('current', 'Current'),
        ('past_due', 'Past Due'),
        ('failed', 'Payment Failed'),
        ('dunning', 'In Dunning Process'),
        ('suspended', 'Suspended for Non-Payment'),
    ], string='Payment Status', compute='_compute_payment_status', store=True)
    
    has_payment_issues = fields.Boolean(
        string='Has Payment Issues',
        compute='_compute_payment_status',
        store=True,
        help='Customer has active payment issues'
    )
    
    days_past_due = fields.Integer(
        string='Days Past Due',
        compute='_compute_payment_status',
        store=True
    )
    
    # Billing Statistics
    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_billing_stats',
        currency_field='currency_id',
        store=True
    )
    
    failed_payment_count = fields.Integer(
        string='Failed Payment Count',
        compute='_compute_billing_stats',
        store=True
    )
    
    # Grace Period
    grace_period_end = fields.Date(
        string='Grace Period End',
        help='End date of current grace period'
    )
    
    is_in_grace_period = fields.Boolean(
        string='In Grace Period',
        compute='_compute_grace_status',
        store=True
    )
    
    # Access Control During Billing Issues
    access_level = fields.Selection([
        ('full', 'Full Access'),
        ('limited', 'Limited Access'),
        ('view_only', 'View Only'),
        ('no_access', 'No Access'),
    ], string='Current Access Level', default='full',
    help='Current access level based on payment status')
    
    restricted_features = fields.Text(
        string='Restricted Features',
        help='List of features currently restricted due to payment issues'
    )
    
    # =============================================================================
    # RELATED BILLING RECORDS
    # =============================================================================
    
    # Billing Records
    billing_schedule_ids = fields.One2many(
        'ams.billing.schedule',
        'subscription_id',
        string='Billing Schedules'
    )
    
    billing_event_ids = fields.One2many(
        'ams.billing.event',
        'subscription_id',
        string='Billing Events'
    )
    
    payment_retry_ids = fields.One2many(
        'ams.payment.retry',
        'subscription_id',
        string='Payment Retries'
    )
    
    dunning_process_ids = fields.One2many(
        'ams.dunning.process',
        'subscription_id',
        string='Dunning Processes'
    )
    
    proration_calculation_ids = fields.One2many(
        'ams.proration.calculation',
        'subscription_id',
        string='Proration Calculations'
    )
    
    # Invoice tracking
    subscription_invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Subscription Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('subscription_invoice_ids', 'payment_retry_ids', 'dunning_process_ids')
    def _compute_payment_status(self):
        """Compute payment status based on invoices and processes"""
        for subscription in self:
            # Get unpaid invoices
            unpaid_invoices = subscription.subscription_invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state in ['not_paid', 'partial']
            )
            
            # Check for active dunning processes
            active_dunning = subscription.dunning_process_ids.filtered(
                lambda dp: dp.state == 'active'
            )
            
            # Check for failed payment retries
            failed_retries = subscription.payment_retry_ids.filtered(
                lambda pr: pr.state == 'failed'
            )
            
            if subscription.state == 'suspended' and (unpaid_invoices or active_dunning):
                subscription.payment_status = 'suspended'
                subscription.has_payment_issues = True
            elif active_dunning:
                subscription.payment_status = 'dunning'
                subscription.has_payment_issues = True
            elif failed_retries:
                subscription.payment_status = 'failed'
                subscription.has_payment_issues = True
            elif unpaid_invoices:
                # Check if any invoice is past due
                past_due_invoices = unpaid_invoices.filtered(
                    lambda inv: inv.invoice_date_due and inv.invoice_date_due < fields.Date.today()
                )
                if past_due_invoices:
                    subscription.payment_status = 'past_due'
                    subscription.has_payment_issues = True
                    # Calculate days past due
                    oldest_due = min(past_due_invoices.mapped('invoice_date_due'))
                    subscription.days_past_due = (fields.Date.today() - oldest_due).days
                else:
                    subscription.payment_status = 'current'
                    subscription.has_payment_issues = False
                    subscription.days_past_due = 0
            else:
                subscription.payment_status = 'current'
                subscription.has_payment_issues = False
                subscription.days_past_due = 0
    
    @api.depends('subscription_invoice_ids', 'payment_retry_ids')
    def _compute_billing_stats(self):
        """Compute billing statistics"""
        for subscription in self:
            invoices = subscription.subscription_invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
            )
            
            subscription.total_invoiced = sum(invoices.mapped('amount_total'))
            subscription.total_paid = sum(invoices.mapped('amount_paid'))
            subscription.outstanding_balance = subscription.total_invoiced - subscription.total_paid
            
            # Count failed payment attempts
            subscription.failed_payment_count = len(
                subscription.payment_retry_ids.filtered(lambda pr: pr.state == 'failed')
            )
    
    @api.depends('grace_period_end')
    def _compute_grace_status(self):
        """Compute if subscription is in grace period"""
        today = fields.Date.today()
        for subscription in self:
            subscription.is_in_grace_period = (
                subscription.grace_period_end and 
                today <= subscription.grace_period_end
            )
    
    # =============================================================================
    # VALIDATION AND CONSTRAINTS
    # =============================================================================
    
    @api.constrains('billing_day')
    def _check_billing_day(self):
        """Validate billing day"""
        for subscription in self:
            if subscription.billing_day and not (1 <= subscription.billing_day <= 28):
                raise ValidationError(_('Billing day must be between 1 and 28'))
    
    @api.constrains('enable_auto_payment', 'payment_method_id')
    def _check_auto_payment_method(self):
        """Validate auto payment configuration"""
        for subscription in self:
            if subscription.enable_auto_payment and not subscription.payment_method_id:
                raise ValidationError(_('Payment method is required when auto payment is enabled'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('enable_auto_billing')
    def _onchange_enable_auto_billing(self):
        """Handle auto billing enablement"""
        if self.enable_auto_billing and not self.next_billing_date:
            self._calculate_next_billing_date()
    
    @api.onchange('subscription_period', 'billing_day')
    def _onchange_billing_configuration(self):
        """Recalculate billing dates when configuration changes"""
        if self.enable_auto_billing:
            self._calculate_next_billing_date()
    
    # =============================================================================
    # BILLING ACTIONS
    # =============================================================================
    
    def action_enable_billing(self):
        """Enable auto-billing for this subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_('Only active subscriptions can have billing enabled'))
            
            subscription.enable_auto_billing = True
            
            # Create billing schedule if it doesn't exist
            if not subscription.billing_schedule_ids:
                subscription._create_billing_schedule()
            
            # Calculate next billing date
            subscription._calculate_next_billing_date()
            
            subscription.message_post(body=_('Auto-billing enabled'))
    
    def action_disable_billing(self):
        """Disable auto-billing for this subscription"""
        for subscription in self:
            subscription.enable_auto_billing = False
            
            # Pause billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'active'
            )
            active_schedules.action_pause()
            
            subscription.message_post(body=_('Auto-billing disabled'))
    
    def action_bill_now(self):
        """Manually trigger billing for this subscription"""
        for subscription in self:
            if not subscription.enable_auto_billing:
                raise UserError(_('Auto-billing must be enabled to bill now'))
            
            # Find or create billing schedule
            schedule = subscription._get_or_create_billing_schedule()
            
            # Process billing
            result = schedule.process_billing()
            
            if result.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Billing processed successfully'),
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('Billing failed: %s') % result.get('error', 'Unknown error'),
                        'type': 'danger',
                    }
                }
    
    def action_setup_payment_method(self):
        """Open wizard to setup payment method"""
        self.ensure_one()
        
        return {
            'name': _('Setup Payment Method'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.payment.method.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
    
    def action_retry_failed_payments(self):
        """Retry failed payments for this subscription"""
        self.ensure_one()
        
        failed_retries = self.payment_retry_ids.filtered(
            lambda pr: pr.state in ['pending', 'failed'] and pr.current_attempt < pr.max_retry_attempts
        )
        
        if not failed_retries:
            raise UserError(_('No failed payments to retry'))
        
        for retry in failed_retries:
            retry.action_retry_now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Retrying %d failed payments') % len(failed_retries),
                'type': 'info',
            }
        }
    
    def action_start_dunning_process(self):
        """Manually start dunning process"""
        self.ensure_one()
        
        # Find unpaid invoices
        unpaid_invoices = self.subscription_invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.payment_state in ['not_paid', 'partial']
        )
        
        if not unpaid_invoices:
            raise UserError(_('No unpaid invoices to start dunning process'))
        
        # Get dunning sequence
        sequence = self.dunning_sequence_id or self._get_default_dunning_sequence()
        
        if not sequence:
            raise UserError(_('No dunning sequence configured'))
        
        # Create dunning process for each unpaid invoice
        processes_created = 0
        for invoice in unpaid_invoices:
            existing_process = self.dunning_process_ids.filtered(
                lambda dp: dp.invoice_id == invoice and dp.state == 'active'
            )
            
            if not existing_process:
                self.env['ams.dunning.process'].create({
                    'subscription_id': self.id,
                    'invoice_id': invoice.id,
                    'dunning_sequence_id': sequence.id,
                    'failure_date': invoice.invoice_date_due or invoice.invoice_date,
                    'failure_reason': 'payment_overdue',
                    'failed_amount': invoice.amount_residual,
                })
                processes_created += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Started dunning process for %d invoice(s)') % processes_created,
                'type': 'success',
            }
        }
    
    def action_suspend_for_non_payment(self):
        """Suspend subscription for non-payment"""
        for subscription in self:
            if subscription.state == 'suspended':
                raise UserError(_('Subscription is already suspended'))
            
            # Set grace period end if not set
            if not subscription.grace_period_end:
                sequence = subscription.dunning_sequence_id or subscription._get_default_dunning_sequence()
                grace_days = sequence.grace_period_days if sequence else 7
                subscription.grace_period_end = fields.Date.today() + timedelta(days=grace_days)
            
            # Suspend the subscription
            subscription.action_suspend()
            
            # Set access level
            subscription.access_level = 'limited'
            subscription.restricted_features = 'Limited access due to payment issues'
            
            subscription.message_post(body=_('Subscription suspended for non-payment'))
    
    def action_reactivate_after_payment(self):
        """Reactivate subscription after payment received"""
        for subscription in self:
            if subscription.state != 'suspended':
                raise UserError(_('Only suspended subscriptions can be reactivated'))
            
            # Check if payment issues are resolved
            if subscription.has_payment_issues:
                raise UserError(_('Cannot reactivate subscription with outstanding payment issues'))
            
            # Reactivate the subscription
            subscription.action_reactivate()
            
            # Restore full access
            subscription.access_level = 'full'
            subscription.restricted_features = False
            subscription.grace_period_end = False
            
            # Cancel active dunning processes
            active_dunning = subscription.dunning_process_ids.filtered(
                lambda dp: dp.state == 'active'
            )
            active_dunning.action_complete()
            
            subscription.message_post(body=_('Subscription reactivated after payment'))
    
    # =============================================================================
    # BILLING LIFECYCLE OVERRIDES
    # =============================================================================
    
    def action_activate(self):
        """Override activation to setup billing"""
        result = super().action_activate()
        
        for subscription in self:
            # Enable auto-billing by default for new subscriptions
            if not subscription.enable_auto_billing:
                subscription.enable_auto_billing = True
            
            # Create billing schedule
            if subscription.enable_auto_billing and not subscription.billing_schedule_ids:
                subscription._create_billing_schedule()
            
            # Calculate next billing date
            subscription._calculate_next_billing_date()
        
        return result
    
    def action_suspend(self):
        """Override suspension to handle billing"""
        result = super().action_suspend()
        
        for subscription in self:
            # Pause billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'active'
            )
            active_schedules.action_pause()
            
            # Handle proration if mid-cycle
            if subscription.enable_auto_billing:
                subscription._handle_suspension_proration()
        
        return result
    
    def action_reactivate(self):
        """Override reactivation to handle billing"""
        result = super().action_reactivate()
        
        for subscription in self:
            # Resume billing schedules
            paused_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state == 'paused'
            )
            paused_schedules.action_resume()
            
            # Handle reactivation billing
            if subscription.enable_auto_billing:
                subscription._handle_reactivation_billing()
        
        return result
    
    def action_terminate(self):
        """Override termination to handle billing"""
        for subscription in self:
            # Handle early termination proration
            if subscription.enable_auto_billing:
                subscription._handle_termination_proration()
            
            # Cancel billing schedules
            active_schedules = subscription.billing_schedule_ids.filtered(
                lambda s: s.state in ['active', 'paused']
            )
            active_schedules.action_cancel()
            
            # Cancel pending payment retries
            pending_retries = subscription.payment_retry_ids.filtered(
                lambda pr: pr.state == 'pending'
            )
            pending_retries.action_cancel()
            
            # Complete dunning processes
            active_dunning = subscription.dunning_process_ids.filtered(
                lambda dp: dp.state == 'active'
            )
            active_dunning.action_complete()
        
        result = super().action_terminate()
        return result
    
    # =============================================================================
    # SUBSCRIPTION MODIFICATION HANDLING
    # =============================================================================
    
    def action_upgrade_product(self, new_product, effective_date=None):
        """Handle product upgrade with proration"""
        self.ensure_one()
        
        if not effective_date:
            effective_date = fields.Date.today()
        
        # Create proration calculation
        proration = self.env['ams.proration.calculation'].calculate_upgrade_proration(
            self, new_product, effective_date
        )
        
        # Apply proration
        proration.action_approve()
        proration.action_apply()
        
        # Update subscription
        old_product = self.product_id
        self.product_id = new_product.id
        self.price = new_product.list_price
        
        self.message_post(
            body=_('Product upgraded from %s to %s. Proration: %s') % (
                old_product.name, new_product.name, proration.name
            )
        )
        
        return proration
    
    def action_downgrade_product(self, new_product, effective_date=None):
        """Handle product downgrade with proration"""
        self.ensure_one()
        
        if not effective_date:
            effective_date = fields.Date.today()
        
        # Create proration calculation
        proration = self.env['ams.proration.calculation'].create({
            'subscription_id': self.id,
            'original_product_id': self.product_id.id,
            'new_product_id': new_product.id,
            'proration_type': 'downgrade',
            'effective_date': effective_date,
            'original_price': self.price,
            'new_price': new_product.list_price,
        })
        
        proration.action_calculate()
        proration.action_approve()
        proration.action_apply()
        
        # Update subscription
        old_product = self.product_id
        self.product_id = new_product.id
        self.price = new_product.list_price
        
        self.message_post(
            body=_('Product downgraded from %s to %s. Proration: %s') % (
                old_product.name, new_product.name, proration.name
            )
        )
        
        return proration
    
    def action_add_seats(self, additional_seats, effective_date=None):
        """Add enterprise seats with proration"""
        self.ensure_one()
        
        if not effective_date:
            effective_date = fields.Date.today()
        
        # Create proration calculation
        proration = self.env['ams.proration.calculation'].calculate_seat_addition_proration(
            self, additional_seats, effective_date
        )
        
        # Apply proration
        proration.action_approve()
        proration.action_apply()
        
        # Update subscription
        old_quantity = self.quantity or 1
        self.quantity = old_quantity + additional_seats
        
        self.message_post(
            body=_('Added %d seats (from %d to %d). Proration: %s') % (
                additional_seats, old_quantity, self.quantity, proration.name
            )
        )
        
        return proration
    
    # =============================================================================
    # BILLING HELPER METHODS
    # =============================================================================
    
    def _create_billing_schedule(self):
        """Create billing schedule for this subscription"""
        self.ensure_one()
        
        schedule = self.env['ams.billing.schedule'].create({
            'subscription_id': self.id,
            'billing_frequency': self.subscription_period,
            'billing_day': self.billing_day or 1,
            'start_date': fields.Date.today(),
            'next_billing_date': self.next_billing_date or fields.Date.today(),
            'auto_invoice': True,
            'auto_payment': self.enable_auto_payment,
            'auto_send_invoice': self.auto_send_invoices,
            'payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
            'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
        })
        
        return schedule
    
    def _get_or_create_billing_schedule(self):
        """Get existing or create new billing schedule"""
        self.ensure_one()
        
        schedule = self.billing_schedule_ids.filtered(lambda s: s.state == 'active')
        if not schedule:
            schedule = self._create_billing_schedule()
            schedule.action_activate()
        
        return schedule[:1]  # Return only the first one
    
    def _calculate_next_billing_date(self):
        """Calculate next billing date based on subscription period"""
        for subscription in self:
            if not subscription.enable_auto_billing:
                continue
            
            today = fields.Date.today()
            
            # Use start date as base if no last billing date
            base_date = subscription.last_billing_date or subscription.start_date or today
            
            # Calculate next date based on subscription period
            if subscription.subscription_period == 'monthly':
                next_date = base_date + timedelta(days=30)  # Approximate
                if subscription.billing_day:
                    try:
                        next_date = next_date.replace(day=subscription.billing_day)
                    except ValueError:
                        next_date = next_date.replace(day=min(subscription.billing_day, 28))
            elif subscription.subscription_period == 'quarterly':
                next_date = base_date + timedelta(days=90)  # Approximate
            elif subscription.subscription_period == 'annual':
                next_date = base_date + timedelta(days=365)  # Approximate
            else:
                next_date = base_date + timedelta(days=30)
            
            # Ensure next date is in the future
            if next_date <= today:
                next_date = today + timedelta(days=1)
            
            subscription.next_billing_date = next_date
    
    def _get_default_dunning_sequence(self):
        """Get default dunning sequence for this subscription"""
        self.ensure_one()
        
        # Find applicable sequences
        sequences = self.env['ams.dunning.sequence'].get_applicable_sequences(self)
        
        return sequences[:1] if sequences else False
    
    def _handle_suspension_proration(self):
        """Handle proration for subscription suspension"""
        self.ensure_one()
        
        # Create suspension credit if mid-cycle
        if self.last_billing_date:
            remaining_days = self._calculate_remaining_billing_days()
            if remaining_days > 0:
                proration = self.env['ams.proration.calculation'].create({
                    'subscription_id': self.id,
                    'original_product_id': self.product_id.id,
                    'proration_type': 'suspension_credit',
                    'effective_date': fields.Date.today(),
                    'original_price': self.price,
                    'original_quantity': self.quantity or 1,
                })
                
                proration.action_calculate()
                proration.action_approve()
                proration.action_apply()
    
    def _handle_reactivation_billing(self):
        """Handle billing for subscription reactivation"""
        self.ensure_one()
        
        # Calculate next billing date
        self._calculate_next_billing_date()
        
        # Create reactivation charge if applicable
        # This could be implemented based on business rules
        pass
    
    def _handle_termination_proration(self):
        """Handle proration for early termination"""
        self.ensure_one()
        
        # Create early termination credit if applicable
        if self.last_billing_date and self.next_billing_date:
            remaining_days = (self.next_billing_date - fields.Date.today()).days
            if remaining_days > 0:
                proration = self.env['ams.proration.calculation'].create({
                    'subscription_id': self.id,
                    'original_product_id': self.product_id.id,
                    'proration_type': 'early_termination',
                    'effective_date': fields.Date.today(),
                    'original_price': self.price,
                    'original_quantity': self.quantity or 1,
                })
                
                proration.action_calculate()
                proration.action_approve()
                proration.action_apply()
    
    def _calculate_remaining_billing_days(self):
        """Calculate remaining days in current billing period"""
        self.ensure_one()
        
        if not self.next_billing_date:
            return 0
        
        today = fields.Date.today()
        if self.next_billing_date <= today:
            return 0
        
        return (self.next_billing_date - today).days
    
    def _create_billing_invoice(self, billing_date=None, billing_event=None):
        """Create billing invoice for this subscription"""
        self.ensure_one()
        
        if not billing_date:
            billing_date = fields.Date.today()
        
        # Calculate billing period
        period_start = billing_date
        if self.subscription_period == 'monthly':
            period_end = period_start + timedelta(days=30)
        elif self.subscription_period == 'quarterly':
            period_end = period_start + timedelta(days=90)
        elif self.subscription_period == 'annual':
            period_end = period_start + timedelta(days=365)
        else:
            period_end = period_start + timedelta(days=30)
        
        # Prepare invoice values
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'subscription_id': self.id,
            'invoice_date': billing_date,
            'ref': f'Subscription: {self.name}',
            'narration': f'Subscription billing for period {period_start} to {period_end}',
        }
        
        # Add payment terms if configured
        if self.payment_term_id:
            invoice_vals['invoice_payment_term_id'] = self.payment_term_id.id
        
        # Add billing event reference
        if billing_event:
            invoice_vals['billing_event_id'] = billing_event.id
        
        # Prepare invoice line
        line_vals = {
            'product_id': self.product_id.id,
            'name': f'{self.product_id.name} - {period_start} to {period_end}',
            'quantity': self.quantity or 1,
            'price_unit': self.price,
        }
        
        # Add product-specific accounting
        if hasattr(self.product_id.product_tmpl_id, 'ams_revenue_account_id'):
            if self.product_id.product_tmpl_id.ams_revenue_account_id:
                line_vals['account_id'] = self.product_id.product_tmpl_id.ams_revenue_account_id.id
        
        invoice_vals['invoice_line_ids'] = [(0, 0, line_vals)]
        
        # Create and post invoice
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        return invoice
    
    # =============================================================================
    # VIEW ACTIONS
    # =============================================================================
    
    def action_view_billing_schedules(self):
        """View billing schedules"""
        self.ensure_one()
        
        return {
            'name': _('Billing Schedules - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.schedule',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_billing_events(self):
        """View billing events"""
        self.ensure_one()
        
        return {
            'name': _('Billing Events - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.event',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_invoices(self):
        """View subscription invoices"""
        self.ensure_one()
        
        return {
            'name': _('Invoices - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_payment_retries(self):
        """View payment retries"""
        self.ensure_one()
        
        return {
            'name': _('Payment Retries - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.payment.retry',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_dunning_processes(self):
        """View dunning processes"""
        self.ensure_one()
        
        return {
            'name': _('Dunning Processes - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.dunning.process',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_proration_calculations(self):
        """View proration calculations"""
        self.ensure_one()
        
        return {
            'name': _('Proration Calculations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.proration.calculation',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }