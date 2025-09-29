# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionSubscription(models.Model):
    _name = 'subscription.subscription'
    _description = 'Subscription'
    _order = 'date_start desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Subscription Reference', required=True, copy=False,
                       readonly=True, default=lambda x: _('New'))
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', 'Customer', required=True,
                                 tracking=True, index=True)
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address')
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address')
    
    # Company
    company_id = fields.Many2one(
        'res.company', 
        'Company',
        default=lambda self: self.env.company,
        compute='_compute_company_id',
        store=True,
        readonly=False
    )
    
    # Plan and Pricing
    plan_id = fields.Many2one('subscription.plan', 'Subscription Plan',
                              required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  related='plan_id.currency_id', store=True)
    
    # Subscription Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True, index=True)
    
    # Dates
    date_start = fields.Date('Start Date', required=True, tracking=True,
                             default=fields.Date.today)
    date_end = fields.Date('End Date', tracking=True)
    trial_end_date = fields.Date('Trial End Date', compute='_compute_trial_end_date',
                                 store=True)
    next_billing_date = fields.Date('Next Billing Date', 
                                    compute='_compute_next_billing_date',
                                    store=True)
    
    # Billing
    price = fields.Float('Price', related='plan_id.price', store=True)
    last_invoice_id = fields.Many2one('account.move', 'Last Invoice')
    last_invoice_date = fields.Date('Last Invoice Date')
    
    # Payment Retry & Dunning
    payment_retry_count = fields.Integer('Payment Retry Count', default=0, tracking=True)
    last_payment_error = fields.Text('Last Payment Error')
    payment_retry_date = fields.Date('Next Payment Retry')
    dunning_level = fields.Selection([
        ('none', 'No Dunning'),
        ('soft', 'Soft Dunning'),
        ('hard', 'Hard Dunning'),
        ('final', 'Final Notice'),
    ], default='none', string='Dunning Level', tracking=True)
    failed_invoice_ids = fields.One2many('account.move', 'subscription_id',
                                         domain=[('payment_state', '=', 'not_paid')],
                                         string='Failed Invoices')
    failed_invoice_count = fields.Integer('Failed Invoices', compute='_compute_failed_invoice_count')
    
    # Usage Tracking
    current_usage = fields.Float('Current Usage')
    usage_limit = fields.Float('Usage Limit', related='plan_id.included_usage')
    usage_overage = fields.Float('Usage Overage', compute='_compute_usage_overage')
    
    # Relations
    line_ids = fields.One2many('subscription.line', 'subscription_id',
                               'Subscription Lines')
    usage_ids = fields.One2many('subscription.usage', 'subscription_id',
                                'Usage Records')
    invoice_ids = fields.One2many('account.move', 'subscription_id',
                                  'Invoices')
    tag_ids = fields.Many2many('subscription.tag', string='Tags')
    
    # Counts
    invoice_count = fields.Integer('Invoice Count', compute='_compute_invoice_count')
    
    # Portal Access
    access_token = fields.Char('Access Token', copy=False)
    
    # Coupon
    coupon_id = fields.Many2one('subscription.coupon', 'Applied Coupon')
    original_price = fields.Float('Original Price')
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_active_subscription',
         'CHECK(1=1)',
         'Customer already has an active subscription for this plan!')
    ]
    
    @api.constrains('partner_id', 'plan_id', 'state')
    def _check_duplicate_active_subscription(self):
        """Prevent duplicate active subscriptions for the same partner and plan"""
        for subscription in self:
            if subscription.state in ('active', 'trial'):
                duplicate = self.search([
                    ('partner_id', '=', subscription.partner_id.id),
                    ('plan_id', '=', subscription.plan_id.id),
                    ('state', 'in', ('active', 'trial')),
                    ('id', '!=', subscription.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(_(
                        'Customer %s already has an active subscription (%s) for plan %s. '
                        'Please cancel or modify the existing subscription instead.'
                    ) % (subscription.partner_id.name, duplicate.name, subscription.plan_id.name))
    
    @api.model
    def create(self, vals):
        """Override create to set dates based on billing type"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('subscription.subscription') or _('New')
        
        subscription = super(SubscriptionSubscription, self).create(vals)
        
        # Set subscription dates after creation
        subscription._set_subscription_dates()
        
        return subscription
    
    def write(self, vals):
        """Override write to update dates when plan changes"""
        result = super(SubscriptionSubscription, self).write(vals)
        
        # If plan changed, recalculate dates
        if 'plan_id' in vals or 'date_start' in vals:
            for subscription in self:
                if subscription.plan_id and subscription.date_start:
                    # Only update end date if calendar-based
                    if subscription.plan_id.billing_type == 'calendar' and not vals.get('date_end'):
                        subscription.date_end = subscription.plan_id.get_subscription_end_date(
                            subscription.date_start
                        )
        
        return result
    
    @api.depends('partner_id')
    def _compute_company_id(self):
        """Set company from partner or use default"""
        for subscription in self:
            if not subscription.company_id:
                # Try to get company from partner
                if subscription.partner_id and subscription.partner_id.company_id:
                    subscription.company_id = subscription.partner_id.company_id
                else:
                    # Fallback to default company
                    subscription.company_id = self.env.company
    
    @api.depends('plan_id.trial_period', 'date_start')
    def _compute_trial_end_date(self):
        for subscription in self:
            if subscription.plan_id.trial_period > 0 and subscription.date_start:
                subscription.trial_end_date = subscription.date_start + relativedelta(
                    days=subscription.plan_id.trial_period
                )
            else:
                subscription.trial_end_date = False
    
    @api.depends('date_start', 'plan_id', 'last_invoice_date', 'state', 'plan_id.billing_type')
    def _compute_next_billing_date(self):
        for subscription in self:
            if subscription.state in ('active', 'trial') and subscription.plan_id:
                if subscription.last_invoice_date:
                    base_date = subscription.last_invoice_date
                else:
                    base_date = subscription.trial_end_date or subscription.date_start
                
                if base_date:
                    subscription.next_billing_date = subscription.plan_id.get_next_billing_date(base_date)
                else:
                    subscription.next_billing_date = False
            else:
                subscription.next_billing_date = False
    
    @api.depends('current_usage', 'usage_limit')
    def _compute_usage_overage(self):
        for subscription in self:
            if subscription.usage_limit > 0:
                subscription.usage_overage = max(0, subscription.current_usage - subscription.usage_limit)
            else:
                subscription.usage_overage = 0
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)
    
    @api.depends('failed_invoice_ids')
    def _compute_failed_invoice_count(self):
        for subscription in self:
            subscription.failed_invoice_count = len(subscription.failed_invoice_ids)
    
    @api.onchange('plan_id', 'date_start')
    def _onchange_plan_set_end_date(self):
        """Automatically set end date when plan or start date changes"""
        if self.plan_id and self.date_start and not self.date_end:
            # Set end date based on billing type
            self.date_end = self.plan_id.get_subscription_end_date(self.date_start)
    
    def _set_subscription_dates(self):
        """Set subscription dates based on plan billing type"""
        self.ensure_one()
        
        if not self.date_start:
            self.date_start = fields.Date.today()
        
        # Set end date if not already set
        if not self.date_end and self.plan_id:
            self.date_end = self.plan_id.get_subscription_end_date(self.date_start)
        
        # Set next billing date
        if self.state in ('active', 'trial'):
            if self.last_invoice_date:
                base_date = self.last_invoice_date
            else:
                base_date = self.trial_end_date or self.date_start
            
            if base_date:
                self.next_billing_date = self.plan_id.get_next_billing_date(base_date)
    
    def get_renewal_date(self):
        """Get the date when renewal should be offered"""
        self.ensure_one()
        
        if not self.date_end:
            return False
        
        # For calendar-based subscriptions, offer renewal closer to period end
        if self.plan_id.billing_type == 'calendar':
            if self.plan_id.billing_period == 'yearly':
                # Offer renewal 2 months before year end
                return self.date_end - relativedelta(months=2)
            elif self.plan_id.billing_period == 'quarterly':
                # Offer renewal 2 weeks before quarter end
                return self.date_end - relativedelta(weeks=2)
            else:
                # Offer renewal 1 week before month end
                return self.date_end - relativedelta(weeks=1)
        else:
            # Anniversary-based: offer renewal 1 week before
            return self.date_end - relativedelta(days=7)
    
    def should_offer_renewal(self):
        """Check if renewal should be offered now"""
        self.ensure_one()
        
        if self.state not in ('active', 'trial'):
            return False
        
        if not self.date_end:
            return False
        
        renewal_date = self.get_renewal_date()
        if not renewal_date:
            return False
        
        return fields.Date.today() >= renewal_date
    
    def action_start_trial(self):
        """Start trial period"""
        self.ensure_one()
        if self.plan_id.trial_period > 0:
            self.state = 'trial'
        else:
            self.state = 'active'
        self._create_initial_invoice()
    
    def action_activate(self):
        """Activate subscription"""
        self.ensure_one()
        self.state = 'active'
        # Reset dunning when reactivated
        self.dunning_level = 'none'
        self.payment_retry_count = 0
        if not self.last_invoice_date:
            self._create_initial_invoice()
    
    def action_suspend(self):
        """Suspend subscription"""
        self.ensure_one()
        self.state = 'suspended'
    
    def action_cancel(self):
        """Cancel subscription"""
        self.ensure_one()
        self.state = 'cancelled'
        self.date_end = fields.Date.today()
    
    def action_renew(self):
        """Renew subscription - handle calendar vs anniversary billing"""
        self.ensure_one()
        
        if self.plan_id.auto_renew:
            # Calculate new end date based on billing type
            if self.plan_id.billing_type == 'calendar':
                # For calendar-based, set to next calendar period end
                current_end = self.date_end or self.date_start
                
                if self.plan_id.billing_period == 'yearly':
                    # Next year end
                    self.date_end = date(current_end.year + 1, 12, 31)
                elif self.plan_id.billing_period == 'quarterly':
                    # Next quarter end
                    next_quarter_start = current_end + relativedelta(days=1)
                    self.date_end = self.plan_id._get_calendar_based_billing_date(next_quarter_start)
                elif self.plan_id.billing_period == 'monthly':
                    # Next month end
                    next_month_start = current_end + relativedelta(days=1)
                    self.date_end = self.plan_id._get_calendar_based_billing_date(next_month_start)
                else:
                    # For daily/weekly, use anniversary
                    self.date_end = self.plan_id.get_next_billing_date(current_end)
            else:
                # Anniversary-based: add billing period to current end date
                self.date_end = self.plan_id.get_next_billing_date(
                    self.date_end or self.date_start
                )
            
            if self.state == 'expired':
                self.state = 'active'
            
            self.message_post(
                body=f"Subscription renewed until {self.date_end}",
                message_type='notification'
            )
    
    def action_view_invoices(self):
        """Action to view subscription invoices"""
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_view_failed_invoices(self):
        """Action to view failed invoices"""
        return {
            'name': _('Failed Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.failed_invoice_ids.ids)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_retry_payment(self):
        """Manually retry payment for failed invoices"""
        self.ensure_one()
        
        for invoice in self.failed_invoice_ids:
            if invoice.state == 'posted' and invoice.payment_state == 'not_paid':
                # Here you would integrate with your payment provider
                # For now, we'll just log it
                _logger.info(f"Manual payment retry requested for invoice {invoice.name}")
                
                # Create activity for follow-up
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f'Follow up on payment for {invoice.name}',
                    user_id=self.env.user.id
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment Retry'),
                'message': _('Payment retry has been initiated. Please follow up manually.'),
                'type': 'info',
                'sticky': False,
            }
        }
    
    def _create_initial_invoice(self):
        """Create the initial invoice for the subscription"""
        if self.state == 'trial' and self.plan_id.trial_price == 0:
            return
        
        invoice_vals = self._prepare_invoice_vals()
        invoice = self.env['account.move'].create(invoice_vals)
        
        self.last_invoice_id = invoice.id
        self.last_invoice_date = fields.Date.today()
        
        return invoice
    
    def _prepare_invoice_vals(self):
        """Prepare invoice values"""
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'subscription_id': self.id,
            'invoice_origin': self.name,
            'company_id': self.company_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.plan_id.product_template_id.product_variant_id.id,
                'name': f"Subscription: {self.plan_id.name}",
                'quantity': 1,
                'price_unit': self.plan_id.trial_price if self.state == 'trial' else self.plan_id.price,
            })],
        }
    
    def add_usage(self, usage_type, quantity, description=None, price_unit=0.0):
        """Add usage record to subscription"""
        self.ensure_one()
        usage_vals = {
            'subscription_id': self.id,
            'usage_type': usage_type,
            'quantity': quantity,
            'description': description or f"{usage_type}: {quantity}",
            'price_unit': price_unit,
        }
        usage = self.env['subscription.usage'].create(usage_vals)
        
        # Update current usage
        self.current_usage += quantity
        
        return usage
    
    # ==========================================
    # Payment Failure & Dunning Methods
    # ==========================================
    
    def _process_failed_payment(self, invoice):
        """Handle failed payment with retry logic and dunning"""
        self.ensure_one()
        
        max_retries = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.settings.max_billing_retries', '3'
        ))
        grace_period = int(self.env['ir.config_parameter'].sudo().get_param(
            'subscription.settings.grace_period_days', '7'
        ))
        
        self.payment_retry_count += 1
        self.last_payment_error = f"Payment failed for invoice {invoice.name} on {fields.Date.today()}"
        
        _logger.warning(f"Payment failed for subscription {self.name}. Retry count: {self.payment_retry_count}")
        
        # Determine dunning level and actions
        if self.payment_retry_count >= max_retries:
            # Final attempt failed - suspend subscription
            self.dunning_level = 'final'
            self.action_suspend()
            self._send_dunning_email('final_notice')
            self.message_post(
                body=f"Subscription suspended due to {max_retries} failed payment attempts.",
                message_type='notification'
            )
            
        elif self.payment_retry_count >= 2:
            # Second retry - hard dunning
            self.dunning_level = 'hard'
            self._send_dunning_email('hard_dunning')
            
        else:
            # First retry - soft dunning
            self.dunning_level = 'soft'
            self._send_dunning_email('soft_dunning')
        
        # Schedule next retry
        retry_days = self.payment_retry_count * 3  # 3, 6, 9 days
        self.payment_retry_date = fields.Date.today() + timedelta(days=retry_days)
        
        # Create activity for sales team to follow up
        if self.payment_retry_count >= 2:
            self.activity_schedule(
                'mail.mail_activity_data_call',
                summary=f'Payment Failed - Contact Customer ({self.payment_retry_count} attempts)',
                note=f'Customer {self.partner_id.name} has failed payment {self.payment_retry_count} times. Please contact them.',
                user_id=self.env.ref('base.user_admin').id  # Assign to admin or sales manager
            )
    
    def _process_successful_payment(self, invoice):
        """Reset dunning state when payment succeeds"""
        self.ensure_one()
        
        if self.dunning_level != 'none' or self.payment_retry_count > 0:
            _logger.info(f"Payment successful for subscription {self.name}. Resetting dunning state.")
            
            self.write({
                'payment_retry_count': 0,
                'dunning_level': 'none',
                'last_payment_error': False,
                'payment_retry_date': False,
            })
            
            # Reactivate if suspended
            if self.state == 'suspended':
                self.action_activate()
            
            self.message_post(
                body=f"Payment successful for invoice {invoice.name}. Dunning cleared.",
                message_type='notification'
            )
    
    def _send_dunning_email(self, email_type):
        """Send dunning notification email"""
        template_map = {
            'soft_dunning': 'subscription_management.email_template_payment_failed_soft',
            'hard_dunning': 'subscription_management.email_template_payment_failed_hard',
            'final_notice': 'subscription_management.email_template_payment_failed_final',
        }
        
        template_ref = template_map.get(email_type)
        if not template_ref:
            return
        
        template = self.env.ref(template_ref, raise_if_not_found=False)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                _logger.info(f"Sent {email_type} email for subscription {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send {email_type} email for subscription {self.name}: {e}")
    
    @api.model
    def _cron_retry_failed_payments(self):
        """Cron job to retry failed payments"""
        today = fields.Date.today()
        
        subscriptions = self.search([
            ('payment_retry_date', '<=', today),
            ('payment_retry_count', '>', 0),
            ('payment_retry_count', '<', 3),
            ('state', 'in', ['active', 'trial'])
        ])
        
        _logger.info(f"Retrying payments for {len(subscriptions)} subscriptions")
        
        for subscription in subscriptions:
            try:
                # Find the last failed invoice
                failed_invoice = subscription.failed_invoice_ids[:1]
                if failed_invoice:
                    # Here you would trigger payment retry with your payment provider
                    # For now, we'll just log it and create an activity
                    _logger.info(f"Retrying payment for subscription {subscription.name}, invoice {failed_invoice.name}")
                    
                    # In a real implementation, you would:
                    # 1. Call payment provider API to retry payment
                    # 2. Update invoice payment state based on response
                    # 3. Call _process_successful_payment or _process_failed_payment
                    
            except Exception as e:
                _logger.error(f"Error retrying payment for subscription {subscription.name}: {e}")
    
    @api.model
    def _cron_check_renewals(self):
        """Check for subscriptions that need renewal and send reminders"""
        today = fields.Date.today()
        
        # Find subscriptions that should offer renewal
        subscriptions = self.search([
            ('state', 'in', ['active', 'trial']),
            ('date_end', '!=', False)
        ])
        
        renewal_count = 0
        reminder_count = 0
        
        for subscription in subscriptions:
            try:
                if subscription.should_offer_renewal():
                    # Check if reminder already sent recently
                    last_message = subscription.message_ids.filtered(
                        lambda m: 'Renewal reminder sent' in (m.body or '')
                    )[:1]
                    
                    # Only send reminder once per week
                    send_reminder = True
                    if last_message:
                        days_since_last = (today - last_message.date.date()).days
                        if days_since_last < 7:
                            send_reminder = False
                    
                    if send_reminder:
                        # Send renewal reminder email
                        template = self.env.ref(
                            'subscription_management.email_template_subscription_renewal_reminder',
                            raise_if_not_found=False
                        )
                        if template:
                            template.send_mail(subscription.id, force_send=False)
                            subscription.message_post(
                                body=f"Renewal reminder sent for subscription ending on {subscription.date_end}",
                                message_type='notification'
                            )
                            reminder_count += 1
                        
                        # Create activity for sales team
                        subscription.activity_schedule(
                            'mail.mail_activity_data_call',
                            summary=f'Follow up on renewal for {subscription.partner_id.name}',
                            note=f'Subscription {subscription.name} is due for renewal on {subscription.date_end}. Contact customer to confirm renewal.',
                            date_deadline=subscription.date_end - relativedelta(days=3),
                            user_id=self.env.ref('base.user_admin').id
                        )
                        renewal_count += 1
                        
            except Exception as e:
                _logger.error(f"Error checking renewal for subscription {subscription.name}: {e}")
        
        _logger.info(f"Renewal check completed: {renewal_count} subscriptions due for renewal, {reminder_count} reminders sent")
    
    # ==========================================
    # Existing Cron Methods
    # ==========================================
    
    @api.model
    def _cron_process_billing(self):
        """Process billing for subscriptions due today"""
        today = fields.Date.today()
        subscriptions = self.search([
            ('state', 'in', ['active', 'trial']),
            ('next_billing_date', '<=', today)
        ])
        
        _logger.info(f"Processing billing for {len(subscriptions)} subscriptions")
        
        for subscription in subscriptions:
            try:
                subscription._process_billing()
            except Exception as e:
                _logger.error(f"Error processing billing for subscription {subscription.name}: {e}")
    
    def _process_billing(self):
        """Process billing for this subscription"""
        self.ensure_one()
        
        if self.state not in ('active', 'trial'):
            return
        
        # Create invoice
        invoice_vals = self._prepare_invoice_vals()
        
        # Add usage overage if applicable
        if self.usage_overage > 0 and self.plan_id.usage_price > 0:
            overage_line = {
                'product_id': self.plan_id.product_template_id.product_variant_id.id,
                'name': f"Usage overage: {self.usage_overage} {self.plan_id.usage_unit}",
                'quantity': self.usage_overage,
                'price_unit': self.plan_id.usage_price,
            }
            invoice_vals['invoice_line_ids'].append((0, 0, overage_line))
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Update subscription
        self.last_invoice_id = invoice.id
        self.last_invoice_date = fields.Date.today()
        
        # Reset usage for next period
        if self.plan_id.usage_based:
            self.current_usage = 0
        
        # Post invoice automatically (optional)
        try:
            invoice.action_post()
        except Exception as e:
            _logger.warning(f"Could not auto-post invoice {invoice.name}: {e}")
        
        # Send invoice by email
        self._send_invoice_email(invoice)
        
        return invoice
    
    def _send_invoice_email(self, invoice):
        """Send invoice by email"""
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        if template:
            try:
                template.send_mail(invoice.id, force_send=True)
            except Exception as e:
                _logger.error(f"Failed to send invoice email for {invoice.name}: {e}")
    
    @api.model
    def _cron_check_trial_expiry(self):
        """Check for trial subscriptions that are expiring"""
        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        
        # Find trials expiring tomorrow (send reminder)
        trials_expiring = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '=', tomorrow)
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_trial_expiry', 
                               raise_if_not_found=False)
        if template:
            for subscription in trials_expiring:
                try:
                    template.send_mail(subscription.id, force_send=False)
                except Exception as e:
                    _logger.error(f"Failed to send trial expiry email for {subscription.name}: {e}")
        
        # Find trials that expired today (convert to active)
        trials_expired = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '<=', today)
        ])
        
        for subscription in trials_expired:
            subscription.action_activate()
    
    @api.model
    def _cron_check_expiry(self):
        """Check for subscriptions that have expired"""
        today = fields.Date.today()
        
        expired_subscriptions = self.search([
            ('state', 'in', ['active', 'suspended']),
            ('date_end', '<=', today),
            ('date_end', '!=', False)
        ])
        
        for subscription in expired_subscriptions:
            subscription.state = 'expired'
    
    @api.model
    def _cron_auto_renew(self):
        """Process auto-renewals for expiring subscriptions"""
        today = fields.Date.today()
        renew_date = today + relativedelta(days=7)  # Renew 7 days before expiry
        
        subscriptions_to_renew = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', renew_date),
            ('date_end', '!=', False),
            ('plan_id.auto_renew', '=', True)
        ])
        
        for subscription in subscriptions_to_renew:
            subscription.action_renew()
    
    @api.model
    def _cron_send_billing_reminders(self):
        """Send billing reminders for upcoming billing"""
        today = fields.Date.today()
        reminder_date = today + relativedelta(days=3)  # Remind 3 days before billing
        
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('next_billing_date', '=', reminder_date)
        ])
        
        template = self.env.ref('subscription_management.email_template_subscription_billing_reminder', 
                               raise_if_not_found=False)
        if template:
            for subscription in subscriptions:
                try:
                    template.send_mail(subscription.id, force_send=False)
                except Exception as e:
                    _logger.error(f"Failed to send billing reminder for {subscription.name}: {e}")
    
    @api.model
    def _cron_update_usage_metrics(self):
        """Update usage metrics for all active subscriptions"""
        active_subscriptions = self.search([('state', '=', 'active')])
        
        for subscription in active_subscriptions:
            # Custom logic to calculate usage
            pass
    
    def _get_portal_return_action(self):
        """Return the action to display when returning from payment"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/subscriptions/%s' % self.id,
            'target': 'self',
        }