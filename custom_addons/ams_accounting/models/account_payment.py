from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """
    Enhanced payment model with AMS-specific features and automation
    """
    _inherit = 'account.payment'
    
    # AMS Integration Fields
    ams_subscription_id = fields.Many2one('ams.subscription', 'Related AMS Subscription')
    ams_member_id = fields.Many2one('res.partner', 'AMS Member', compute='_compute_ams_member')
    ams_chapter_id = fields.Many2one('ams.chapter', 'AMS Chapter')
    
    # Payment Classification
    is_ams_payment = fields.Boolean('Is AMS Payment', compute='_compute_ams_payment_type', store=True)
    ams_payment_type = fields.Selection([
        ('subscription', 'Subscription Payment'),
        ('renewal', 'Renewal Payment'),
        ('chapter_fee', 'Chapter Fee Payment'),
        ('donation', 'Donation Payment'),
        ('late_fee', 'Late Fee Payment'),
        ('refund', 'Refund Payment'),
        ('other', 'Other AMS Payment')
    ], string='AMS Payment Type', compute='_compute_ams_payment_type', store=True)
    
    # Payment Method Details
    payment_processor = fields.Selection([
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('square', 'Square'),
        ('authorize_net', 'Authorize.Net'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('other', 'Other')
    ], string='Payment Processor')
    
    payment_processor_ref = fields.Char('Processor Reference')
    payment_gateway_fee = fields.Float('Gateway Fee')
    net_payment_amount = fields.Float('Net Payment Amount', compute='_compute_net_amount', store=True)
    
    # Recurring Payment Configuration
    is_recurring_payment = fields.Boolean('Is Recurring Payment', default=False)
    recurring_payment_id = fields.Many2one('ams.recurring.payment', 'Recurring Payment Setup')
    next_payment_date = fields.Date('Next Payment Date')
    
    # Auto-Payment Configuration
    is_autopay = fields.Boolean('Auto Payment', default=False)
    autopay_token = fields.Char('Auto-Pay Token')
    autopay_last_four = fields.Char('Card Last 4 Digits')
    autopay_expiry = fields.Date('Card Expiry Date')
    
    # Member Experience
    member_payment_method_saved = fields.Boolean('Payment Method Saved', default=False)
    member_notification_sent = fields.Boolean('Member Notification Sent', default=False)
    receipt_sent = fields.Boolean('Receipt Sent', default=False)
    
    # Financial Analytics
    payment_delay_days = fields.Integer('Payment Delay (Days)', compute='_compute_payment_metrics')
    is_early_payment = fields.Boolean('Early Payment', compute='_compute_payment_metrics')
    payment_source = fields.Selection([
        ('online', 'Online Portal'),
        ('pos', 'Point of Sale'),
        ('manual', 'Manual Entry'),
        ('import', 'Bank Import'),
        ('recurring', 'Recurring/Auto'),
        ('mobile', 'Mobile App')
    ], string='Payment Source', default='manual')
    
    # Payment Plan Integration
    payment_plan_line_id = fields.Many2one('ams.payment.plan.line', 'Payment Plan Line')
    is_payment_plan_payment = fields.Boolean('Payment Plan Payment', compute='_compute_payment_plan_info')
    
    # Risk Management
    risk_score = fields.Float('Risk Score', default=0.0,
        help="Risk score for this payment (0-100, higher = riskier)")
    requires_verification = fields.Boolean('Requires Verification', default=False)
    verification_status = fields.Selection([
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('manual_review', 'Manual Review Required')
    ], string='Verification Status', default='pending')
    
    @api.depends('partner_id')
    def _compute_ams_member(self):
        for payment in self:
            if payment.partner_id and payment.partner_id.total_subscription_count > 0:
                payment.ams_member_id = payment.partner_id.id
            else:
                payment.ams_member_id = False
    
    @api.depends('reconciled_invoice_ids', 'ams_subscription_id')
    def _compute_ams_payment_type(self):
        for payment in self:
            payment.is_ams_payment = False
            payment.ams_payment_type = False
            
            # Check if payment is related to AMS invoices
            ams_invoices = payment.reconciled_invoice_ids.filtered(
                lambda inv: inv.is_ams_subscription_invoice or 
                           inv.ams_subscription_id or 
                           inv.ams_chapter_id
            )
            
            if ams_invoices or payment.ams_subscription_id:
                payment.is_ams_payment = True
                
                # Determine payment type
                if ams_invoices.filtered('is_ams_renewal_invoice'):
                    payment.ams_payment_type = 'renewal'
                elif ams_invoices.filtered('is_ams_chapter_fee'):
                    payment.ams_payment_type = 'chapter_fee'
                elif ams_invoices.filtered('is_ams_donation'):
                    payment.ams_payment_type = 'donation'
                elif ams_invoices.filtered('is_ams_subscription_invoice'):
                    payment.ams_payment_type = 'subscription'
                elif payment.payment_type == 'outbound':
                    payment.ams_payment_type = 'refund'
                else:
                    payment.ams_payment_type = 'other'
    
    @api.depends('amount', 'payment_gateway_fee')
    def _compute_net_amount(self):
        for payment in self:
            payment.net_payment_amount = payment.amount - payment.payment_gateway_fee
    
    @api.depends('reconciled_invoice_ids', 'date')
    def _compute_payment_metrics(self):
        for payment in self:
            payment.payment_delay_days = 0
            payment.is_early_payment = False
            
            if payment.reconciled_invoice_ids:
                # Get the primary invoice
                invoice = payment.reconciled_invoice_ids[0]
                
                if invoice.invoice_date_due:
                    delay = (payment.date - invoice.invoice_date_due).days
                    payment.payment_delay_days = delay
                    payment.is_early_payment = delay < 0
    
    @api.depends('payment_plan_line_id')
    def _compute_payment_plan_info(self):
        for payment in self:
            payment.is_payment_plan_payment = bool(payment.payment_plan_line_id)
    
    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        
        for payment in payments:
            # Auto-populate AMS fields
            payment._populate_ams_fields()
            
            # Calculate risk score
            payment._calculate_risk_score()
            
            # Process auto-payment setup
            if payment.is_autopay:
                payment._setup_autopay()
        
        return payments
    
    def action_post(self):
        """Override post action to add AMS-specific logic"""
        # Validate payment if it's an AMS payment
        for payment in self:
            if payment.is_ams_payment:
                payment._validate_ams_payment()
        
        # Standard posting
        result = super().action_post()
        
        # AMS-specific post-processing
        for payment in self:
            payment._process_ams_post_actions()
        
        return result
    
    def _populate_ams_fields(self):
        """Populate AMS fields from related invoices or context"""
        if self.reconciled_invoice_ids:
            invoice = self.reconciled_invoice_ids[0]
            
            if invoice.ams_subscription_id:
                self.ams_subscription_id = invoice.ams_subscription_id.id
                
            if invoice.ams_chapter_id:
                self.ams_chapter_id = invoice.ams_chapter_id.id
    
    def _calculate_risk_score(self):
        """Calculate risk score for the payment"""
        if not self.is_ams_payment:
            return
        
        risk_score = 0.0
        
        # Amount-based risk
        if self.amount > 1000:
            risk_score += 10
        elif self.amount > 5000:
            risk_score += 20
        
        # Payment method risk
        if self.payment_processor in ['cash', 'other']:
            risk_score += 15
        elif self.payment_processor in ['check']:
            risk_score += 10
        elif self.payment_processor in ['bank_transfer']:
            risk_score += 5
        
        # Partner payment history
        if self.partner_id:
            failed_payments = self.search_count([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'cancelled'),
                ('create_date', '>=', fields.Datetime.now() - relativedelta(months=6))
            ])
            risk_score += failed_payments * 5
        
        # First-time payment risk
        if self.partner_id:
            previous_payments = self.search_count([
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'posted'),
                ('id', '!=', self.id)
            ])
            
            if previous_payments == 0:
                risk_score += 15
        
        self.risk_score = min(100, risk_score)
        
        # Set verification requirement
        if self.risk_score > 50:
            self.requires_verification = True
    
    def _setup_autopay(self):
        """Setup auto-payment configuration"""
        if not self.autopay_token:
            return
        
        # Create or update recurring payment setup
        if not self.recurring_payment_id and self.ams_subscription_id:
            recurring_vals = {
                'partner_id': self.partner_id.id,
                'subscription_id': self.ams_subscription_id.id,
                'payment_method': self.payment_processor,
                'amount': self.amount,
                'frequency': self.ams_subscription_id.recurring_period,
                'autopay_token': self.autopay_token,
                'next_payment_date': self._calculate_next_payment_date(),
                'state': 'active'
            }
            
            recurring_payment = self.env['ams.recurring.payment'].create(recurring_vals)
            self.recurring_payment_id = recurring_payment.id
    
    def _calculate_next_payment_date(self):
        """Calculate next payment date for recurring payments"""
        if not self.ams_subscription_id:
            return False
        
        if self.ams_subscription_id.recurring_period == 'monthly':
            return self.date + relativedelta(months=1)
        elif self.ams_subscription_id.recurring_period == 'quarterly':
            return self.date + relativedelta(months=3)
        elif self.ams_subscription_id.recurring_period == 'yearly':
            return self.date + relativedelta(years=1)
        
        return False
    
    def _validate_ams_payment(self):
        """Validate AMS payment before posting"""
        # Check for duplicate payments
        if self.payment_processor_ref:
            duplicate = self.search([
                ('payment_processor_ref', '=', self.payment_processor_ref),
                ('payment_processor', '=', self.payment_processor),
                ('id', '!=', self.id),
                ('state', '!=', 'cancelled')
            ])
            
            if duplicate:
                raise UserError(_('Duplicate payment detected. Reference %s already exists.') % self.payment_processor_ref)
        
        # Validate payment amount against invoice
        if self.reconciled_invoice_ids:
            total_invoice_amount = sum(self.reconciled_invoice_ids.mapped('amount_residual'))
            if abs(self.amount - total_invoice_amount) > 0.01:  # Allow for rounding
                if self.amount > total_invoice_amount:
                    _logger.warning(f"Overpayment detected: Payment {self.amount}, Invoice {total_invoice_amount}")
    
    def _process_ams_post_actions(self):
        """Process AMS-specific actions after posting"""
        # Update subscription status
        if self.ams_subscription_id and self.ams_payment_type == 'renewal':
            self.ams_subscription_id.action_confirm_renewal()
        
        # Update payment plan
        if self.payment_plan_line_id:
            self.payment_plan_line_id.write({
                'state': 'paid',
                'payment_id': self.id,
                'payment_date': self.date
            })
        
        # Send receipts and notifications
        if not self.receipt_sent:
            self._send_payment_receipt()
        
        # Update member payment method
        if self.member_payment_method_saved and self.autopay_token:
            self._save_member_payment_method()
        
        # Process referral bonuses or loyalty points
        self._process_member_rewards()
    
    def _send_payment_receipt(self):
        """Send payment receipt to member"""
        if not self.partner_id.email or self.partner_id.suppress_financial_emails:
            return
        
        template = self.env.ref('ams_accounting.email_template_payment_receipt', False)
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                self.receipt_sent = True
                self.member_notification_sent = True
                _logger.info(f"Payment receipt sent for payment {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send payment receipt for {self.name}: {str(e)}")
    
    def _save_member_payment_method(self):
        """Save payment method for future use"""
        if not self.autopay_token:
            return
        
        # Create or update saved payment method
        saved_method_vals = {
            'partner_id': self.partner_id.id,
            'payment_processor': self.payment_processor,
            'token': self.autopay_token,
            'last_four': self.autopay_last_four,
            'expiry_date': self.autopay_expiry,
            'is_default': True,
            'is_active': True
        }
        
        # Deactivate other default methods
        existing_methods = self.env['ams.saved.payment.method'].search([
            ('partner_id', '=', self.partner_id.id),
            ('is_default', '=', True)
        ])
        existing_methods.write({'is_default': False})
        
        # Create new method
        self.env['ams.saved.payment.method'].create(saved_method_vals)
    
    def _process_member_rewards(self):
        """Process member rewards for this payment"""
        if not self.is_ams_payment or not self.partner_id:
            return
        
        # Simple loyalty points system (can be extended)
        points = int(self.amount / 10)  # 1 point per $10
        
        if points > 0:
            self.partner_id.loyalty_points = (self.partner_id.loyalty_points or 0) + points
            
            # Log the reward
            self.message_post(
                body=_('Member earned %d loyalty points for this payment.') % points
            )
    
    def action_verify_payment(self):
        """Manually verify a payment"""
        if self.verification_status == 'verified':
            raise UserError(_('Payment is already verified.'))
        
        self.verification_status = 'verified'
        self.message_post(body=_('Payment manually verified by %s.') % self.env.user.name)
    
    def action_flag_for_review(self):
        """Flag payment for manual review"""
        self.verification_status = 'manual_review'
        self.message_post(body=_('Payment flagged for manual review.'))
        
        # Create activity for finance team
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Review Payment: {self.name}',
            note=f'Payment flagged for manual review. Risk score: {self.risk_score}',
            user_id=self.env.ref('base.group_account_manager').users[0].id if self.env.ref('base.group_account_manager').users else self.env.user.id
        )
    
    def action_setup_autopay(self):
        """Setup auto-payment for member"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Setup Auto-Payment',
            'res_model': 'ams.autopay.setup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_payment_id': self.id,
            }
        }
    
    def action_view_related_subscription(self):
        """View related subscription"""
        if not self.ams_subscription_id:
            raise UserError(_('No subscription associated with this payment.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Subscription',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.ams_subscription_id.id,
        }
    
    @api.model
    def _cron_process_recurring_payments(self):
        """Cron job to process recurring payments"""
        today = fields.Date.today()
        
        # Find recurring payments due today
        due_payments = self.env['ams.recurring.payment'].search([
            ('state', '=', 'active'),
            ('next_payment_date', '<=', today)
        ])
        
        processed_count = 0
        failed_count = 0
        
        for recurring in due_payments:
            try:
                payment = recurring.process_payment()
                if payment:
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                _logger.error(f"Failed to process recurring payment {recurring.id}: {str(e)}")
                failed_count += 1
        
        _logger.info(f"Processed {processed_count} recurring payments, {failed_count} failed")
        return {'processed': processed_count, 'failed': failed_count}
    
    @api.model
    def get_ams_payment_analytics(self, date_from=None, date_to=None):
        """Get AMS payment analytics for dashboard"""
        if not date_from:
            date_from = fields.Date.today().replace(month=1, day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        domain = [
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('is_ams_payment', '=', True)
        ]
        
        payments = self.search(domain)
        
        analytics = {
            'total_payments': len(payments),
            'total_amount': sum(payments.mapped('amount')),
            'total_fees': sum(payments.mapped('payment_gateway_fee')),
            'net_amount': sum(payments.mapped('net_payment_amount')),
            'average_payment': sum(payments.mapped('amount')) / len(payments) if payments else 0,
            'payment_types': {},
            'payment_processors': {},
            'early_payments': len(payments.filtered('is_early_payment')),
            'recurring_payments': len(payments.filtered('is_recurring_payment')),
            'autopay_payments': len(payments.filtered('is_autopay')),
            'high_risk_payments': len(payments.filtered(lambda p: p.risk_score > 50)),
        }
        
        # Payment type breakdown
        for payment_type in ['subscription', 'renewal', 'chapter_fee', 'donation', 'other']:
            type_payments = payments.filtered(lambda p: p.ams_payment_type == payment_type)
            analytics['payment_types'][payment_type] = {
                'count': len(type_payments),
                'amount': sum(type_payments.mapped('amount'))
            }
        
        # Payment processor breakdown
        for processor in payments.mapped('payment_processor'):
            if processor:
                processor_payments = payments.filtered(lambda p: p.payment_processor == processor)
                analytics['payment_processors'][processor] = {
                    'count': len(processor_payments),
                    'amount': sum(processor_payments.mapped('amount'))
                }
        
        return analytics


class AMSRecurringPayment(models.Model):
    """
    Model for managing recurring payment setups
    """
    _name = 'ams.recurring.payment'
    _description = 'AMS Recurring Payment'
    _order = 'next_payment_date'
    
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    subscription_id = fields.Many2one('ams.subscription', 'Subscription')
    
    payment_method = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('other', 'Other')
    ], string='Payment Method', required=True)
    
    amount = fields.Float('Amount', required=True)
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Frequency', required=True)
    
    next_payment_date = fields.Date('Next Payment Date', required=True)
    last_payment_date = fields.Date('Last Payment Date')
    
    autopay_token = fields.Char('Auto-Pay Token')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    payment_ids = fields.One2many('account.payment', 'recurring_payment_id', 'Generated Payments')
    failed_attempts = fields.Integer('Failed Attempts', default=0)
    
    def process_payment(self):
        """Process recurring payment"""
        if self.state != 'active':
            return False
        
        try:
            # Create payment
            payment_vals = {
                'partner_id': self.partner_id.id,
                'amount': self.amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'journal_id': self._get_payment_journal().id,
                'recurring_payment_id': self.id,
                'is_recurring_payment': True,
                'is_autopay': True,
                'autopay_token': self.autopay_token,
                'payment_processor': self.payment_method,
                'payment_source': 'recurring',
                'date': fields.Date.today(),
                'ref': f'Recurring payment - {self.subscription_id.name if self.subscription_id else self.partner_id.name}'
            }
            
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()
            
            # Update recurring payment
            self.last_payment_date = fields.Date.today()
            self.next_payment_date = self._calculate_next_payment_date()
            self.failed_attempts = 0
            
            return payment
            
        except Exception as e:
            self.failed_attempts += 1
            
            if self.failed_attempts >= 3:
                self.state = 'suspended'
                
            _logger.error(f"Recurring payment failed: {str(e)}")
            return False
    
    def _get_payment_journal(self):
        """Get appropriate payment journal"""
        journal = self.env['account.journal'].search([
            ('type', '=', 'cash'),
            ('is_ams_journal', '=', True),
            ('ams_journal_type', '=', 'payment')
        ], limit=1)
        
        if not journal:
            journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        
        return journal
    
    def _calculate_next_payment_date(self):
        """Calculate next payment date"""
        if self.frequency == 'monthly':
            return self.next_payment_date + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            return self.next_payment_date + relativedelta(months=3)
        elif self.frequency == 'yearly':
            return self.next_payment_date + relativedelta(years=1)
        
        return self.next_payment_date


class AMSSavedPaymentMethod(models.Model):
    """
    Model for saving member payment methods
    """
    _name = 'ams.saved.payment.method'
    _description = 'AMS Saved Payment Method'
    
    partner_id = fields.Many2one('res.partner', 'Member', required=True)
    payment_processor = fields.Selection([
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('square', 'Square'),
        ('authorize_net', 'Authorize.Net')
    ], string='Payment Processor', required=True)
    
    token = fields.Char('Token', required=True)
    last_four = fields.Char('Last 4 Digits')
    expiry_date = fields.Date('Expiry Date')
    
    is_default = fields.Boolean('Default Method', default=False)
    is_active = fields.Boolean('Active', default=True)
    
    _sql_constraints = [
        ('unique_token', 'unique(token, payment_processor)', 'Payment method token must be unique!'),
    ]