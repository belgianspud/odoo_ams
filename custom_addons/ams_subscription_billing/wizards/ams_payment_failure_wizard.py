# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSPaymentFailureWizard(models.TransientModel):
    """Wizard for Handling Payment Failures and Setting Up Recovery Actions"""
    _name = 'ams.payment.failure.wizard'
    _description = 'AMS Payment Failure Wizard'
    
    # =============================================================================
    # BASIC INFORMATION
    # =============================================================================
    
    # Source Records
    source_type = fields.Selection([
        ('single_invoice', 'Single Invoice'),
        ('subscription', 'Subscription'),
        ('customer', 'Customer'),
        ('billing_event', 'Billing Event'),
        ('payment_retry', 'Failed Payment Retry'),
    ], string='Source Type', required=True, default='single_invoice')
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Failed Invoice',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )
    
    billing_event_id = fields.Many2one(
        'ams.billing.event',
        string='Billing Event'
    )
    
    payment_retry_id = fields.Many2one(
        'ams.payment.retry',
        string='Payment Retry'
    )
    
    # =============================================================================
    # FAILURE INFORMATION
    # =============================================================================
    
    failure_date = fields.Datetime(
        string='Failure Date',
        required=True,
        default=fields.Datetime.now
    )
    
    failure_type = fields.Selection([
        ('card_declined', 'Card Declined'),
        ('insufficient_funds', 'Insufficient Funds'),
        ('card_expired', 'Card Expired'),
        ('invalid_card', 'Invalid Card'),
        ('card_blocked', 'Card Blocked'),
        ('limit_exceeded', 'Limit Exceeded'),
        ('gateway_error', 'Gateway Error'),
        ('network_error', 'Network Error'),
        ('timeout', 'Timeout'),
        ('authentication_failed', 'Authentication Failed'),
        ('account_closed', 'Account Closed'),
        ('fraud_suspected', 'Fraud Suspected'),
        ('processing_error', 'Processing Error'),
        ('other', 'Other'),
    ], string='Failure Type', required=True)
    
    failure_reason = fields.Text(
        string='Detailed Failure Reason',
        required=True,
        help='Detailed description of the payment failure'
    )
    
    gateway_error_code = fields.Char(
        string='Gateway Error Code',
        help='Error code from payment gateway'
    )
    
    gateway_response = fields.Text(
        string='Gateway Response',
        help='Full response from payment gateway'
    )
    
    attempted_amount = fields.Monetary(
        string='Attempted Amount',
        currency_field='currency_id',
        required=True
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Failed Payment Method',
        help='Payment method that failed'
    )
    
    # =============================================================================
    # IMPACT ASSESSMENT
    # =============================================================================
    
    failure_severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Failure Severity', compute='_compute_failure_severity', store=True)
    
    customer_impact = fields.Selection([
        ('none', 'No Impact'),
        ('service_warning', 'Service Warning'),
        ('service_restriction', 'Service Restriction'),
        ('service_suspension', 'Service Suspension'),
        ('account_termination', 'Account Termination'),
    ], string='Customer Impact', compute='_compute_customer_impact', store=True)
    
    # Payment History Analysis
    previous_failures = fields.Integer(
        string='Previous Failures (30 days)',
        compute='_compute_payment_history',
        help='Number of payment failures in last 30 days'
    )
    
    consecutive_failures = fields.Integer(
        string='Consecutive Failures',
        compute='_compute_payment_history',
        help='Number of consecutive payment failures'
    )
    
    success_rate = fields.Float(
        string='Payment Success Rate (%)',
        compute='_compute_payment_history',
        help='Payment success rate over last 6 months'
    )
    
    customer_value = fields.Selection([
        ('low', 'Low Value'),
        ('medium', 'Medium Value'),
        ('high', 'High Value'),
        ('vip', 'VIP Customer'),
    ], string='Customer Value', compute='_compute_customer_value', store=True)
    
    # =============================================================================
    # RECOMMENDED ACTIONS
    # =============================================================================
    
    recommended_action = fields.Selection([
        ('immediate_retry', 'Immediate Retry'),
        ('delayed_retry', 'Delayed Retry'),
        ('payment_method_update', 'Update Payment Method'),
        ('dunning_process', 'Start Dunning Process'),
        ('manual_contact', 'Manual Customer Contact'),
        ('suspend_service', 'Suspend Service'),
        ('grace_period', 'Extend Grace Period'),
        ('payment_plan', 'Offer Payment Plan'),
        ('account_review', 'Account Review'),
        ('no_action', 'No Action Required'),
    ], string='Recommended Action', compute='_compute_recommended_action', store=True)
    
    action_priority = fields.Selection([
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
    ], string='Action Priority', compute='_compute_action_priority', store=True)
    
    # =============================================================================
    # SELECTED ACTIONS
    # =============================================================================
    
    action_type = fields.Selection([
        ('retry_payment', 'Retry Payment'),
        ('update_payment_method', 'Update Payment Method'),
        ('start_dunning', 'Start Dunning Process'),
        ('extend_grace', 'Extend Grace Period'),
        ('create_payment_plan', 'Create Payment Plan'),
        ('suspend_subscription', 'Suspend Subscription'),
        ('contact_customer', 'Contact Customer'),
        ('escalate_account', 'Escalate Account'),
        ('fraud_investigation', 'Fraud Investigation'),
        ('defer_action', 'Defer Action'),
    ], string='Selected Action', required=True)
    
    # Retry Payment Settings
    retry_delay_hours = fields.Integer(
        string='Retry Delay (Hours)',
        default=24,
        help='Hours to wait before retrying payment'
    )
    
    retry_max_attempts = fields.Integer(
        string='Max Retry Attempts',
        default=3,
        help='Maximum number of retry attempts'
    )
    
    use_exponential_backoff = fields.Boolean(
        string='Use Exponential Backoff',
        default=True,
        help='Use exponential backoff for retry delays'
    )
    
    # Grace Period Settings
    grace_period_days = fields.Integer(
        string='Grace Period Days',
        default=7,
        help='Number of days to extend grace period'
    )
    
    grace_period_reason = fields.Text(
        string='Grace Period Reason',
        help='Reason for extending grace period'
    )
    
    # Payment Plan Settings
    installment_count = fields.Integer(
        string='Number of Installments',
        default=3,
        help='Number of payment installments'
    )
    
    installment_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], string='Installment Frequency', default='monthly')
    
    first_installment_date = fields.Date(
        string='First Installment Date',
        help='Date of first installment payment'
    )
    
    # Dunning Settings
    dunning_sequence_id = fields.Many2one(
        'ams.dunning.sequence',
        string='Dunning Sequence',
        help='Dunning sequence to use'
    )
    
    start_dunning_immediately = fields.Boolean(
        string='Start Dunning Immediately',
        default=False,
        help='Start dunning process immediately'
    )
    
    # Customer Contact Settings
    contact_method = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone Call'),
        ('sms', 'SMS'),
        ('mail', 'Postal Mail'),
        ('in_person', 'In-Person Meeting'),
    ], string='Contact Method', default='email')
    
    contact_urgency = fields.Selection([
        ('low', 'Low Urgency'),
        ('medium', 'Medium Urgency'),
        ('high', 'High Urgency'),
        ('immediate', 'Immediate'),
    ], string='Contact Urgency', default='medium')
    
    contact_template_id = fields.Many2one(
        'mail.template',
        string='Contact Template',
        domain="[('model', '=', 'res.partner')]"
    )
    
    custom_message = fields.Text(
        string='Custom Message',
        help='Custom message for customer contact'
    )
    
    # =============================================================================
    # WORKFLOW SETTINGS
    # =============================================================================
    
    assign_to_user = fields.Boolean(
        string='Assign to User',
        default=True,
        help='Assign follow-up activity to user'
    )
    
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
        help='User responsible for follow-up'
    )
    
    due_date = fields.Date(
        string='Follow-up Due Date',
        default=lambda self: fields.Date.today() + timedelta(days=1),
        help='Due date for follow-up action'
    )
    
    escalation_needed = fields.Boolean(
        string='Escalation Needed',
        help='This failure requires management escalation'
    )
    
    escalation_reason = fields.Text(
        string='Escalation Reason',
        help='Reason for escalation'
    )
    
    # =============================================================================
    # FRAUD DETECTION
    # =============================================================================
    
    fraud_risk_score = fields.Float(
        string='Fraud Risk Score',
        compute='_compute_fraud_risk',
        help='Calculated fraud risk score (0-100)'
    )
    
    fraud_indicators = fields.Text(
        string='Fraud Indicators',
        compute='_compute_fraud_risk',
        help='Detected fraud indicators'
    )
    
    requires_fraud_review = fields.Boolean(
        string='Requires Fraud Review',
        compute='_compute_fraud_risk',
        help='Payment failure requires fraud review'
    )
    
    # =============================================================================
    # NOTIFICATION SETTINGS
    # =============================================================================
    
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help='Send notification to customer about payment failure'
    )
    
    notify_internal = fields.Boolean(
        string='Notify Internal Team',
        default=True,
        help='Send notification to internal team'
    )
    
    internal_notification_users = fields.Many2many(
        'res.users',
        'payment_failure_notification_rel',
        'wizard_id', 'user_id',
        string='Internal Notification Users'
    )
    
    # =============================================================================
    # METADATA
    # =============================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
    
    processed = fields.Boolean(
        string='Processed',
        default=False,
        readonly=True
    )
    
    processing_date = fields.Datetime(
        string='Processing Date',
        readonly=True
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('failure_type', 'attempted_amount', 'consecutive_failures')
    def _compute_failure_severity(self):
        """Compute failure severity based on various factors"""
        for wizard in self:
            severity_score = 0
            
            # Failure type scoring
            high_risk_types = ['fraud_suspected', 'account_closed', 'card_blocked']
            medium_risk_types = ['card_declined', 'insufficient_funds', 'limit_exceeded']
            
            if wizard.failure_type in high_risk_types:
                severity_score += 3
            elif wizard.failure_type in medium_risk_types:
                severity_score += 2
            else:
                severity_score += 1
            
            # Amount scoring
            if wizard.attempted_amount > 10000:
                severity_score += 2
            elif wizard.attempted_amount > 1000:
                severity_score += 1
            
            # Consecutive failures scoring
            if wizard.consecutive_failures >= 3:
                severity_score += 2
            elif wizard.consecutive_failures >= 2:
                severity_score += 1
            
            # Determine severity
            if severity_score >= 6:
                wizard.failure_severity = 'critical'
            elif severity_score >= 4:
                wizard.failure_severity = 'high'
            elif severity_score >= 2:
                wizard.failure_severity = 'medium'
            else:
                wizard.failure_severity = 'low'
    
    @api.depends('failure_severity', 'consecutive_failures', 'customer_value')
    def _compute_customer_impact(self):
        """Compute expected customer impact"""
        for wizard in self:
            if wizard.failure_severity == 'critical':
                wizard.customer_impact = 'service_suspension'
            elif wizard.failure_severity == 'high':
                if wizard.consecutive_failures >= 3:
                    wizard.customer_impact = 'service_suspension'
                else:
                    wizard.customer_impact = 'service_restriction'
            elif wizard.failure_severity == 'medium':
                wizard.customer_impact = 'service_warning'
            else:
                wizard.customer_impact = 'none'
    
    @api.depends('partner_id', 'subscription_id', 'invoice_id')
    def _compute_payment_history(self):
        """Compute payment history statistics"""
        for wizard in self:
            customer = wizard.partner_id or wizard.subscription_id.partner_id or wizard.invoice_id.partner_id
            
            if not customer:
                wizard.previous_failures = 0
                wizard.consecutive_failures = 0
                wizard.success_rate = 0
                continue
            
            # Get recent payment attempts
            cutoff_date = fields.Date.today() - timedelta(days=30)
            recent_retries = self.env['ams.payment.retry'].search([
                ('partner_id', '=', customer.id),
                ('original_failure_date', '>=', cutoff_date)
            ])
            
            wizard.previous_failures = len(recent_retries.filtered(lambda r: r.state == 'failed'))
            
            # Calculate consecutive failures
            recent_invoices = self.env['account.move'].search([
                ('partner_id', '=', customer.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', cutoff_date)
            ], order='invoice_date desc')
            
            consecutive = 0
            for invoice in recent_invoices:
                if invoice.auto_payment_attempted and not invoice.auto_payment_success:
                    consecutive += 1
                else:
                    break
            
            wizard.consecutive_failures = consecutive
            
            # Calculate success rate over 6 months
            six_months_ago = fields.Date.today() - timedelta(days=180)
            all_attempts = self.env['ams.payment.retry'].search([
                ('partner_id', '=', customer.id),
                ('original_failure_date', '>=', six_months_ago)
            ])
            
            if all_attempts:
                successful = len(all_attempts.filtered(lambda r: r.state == 'success'))
                wizard.success_rate = (successful / len(all_attempts)) * 100
            else:
                wizard.success_rate = 100  # No attempts = no failures
    
    @api.depends('attempted_amount', 'subscription_id', 'partner_id')
    def _compute_customer_value(self):
        """Compute customer value classification"""
        for wizard in self:
            customer = wizard.partner_id or wizard.subscription_id.partner_id or wizard.invoice_id.partner_id
            
            if not customer:
                wizard.customer_value = 'low'
                continue
            
            # Calculate customer value based on various factors
            value_score = 0
            
            # Monthly subscription value
            if wizard.subscription_id:
                monthly_value = wizard.subscription_id.price
                if wizard.subscription_id.subscription_period == 'annual':
                    monthly_value = monthly_value / 12
                elif wizard.subscription_id.subscription_period == 'quarterly':
                    monthly_value = monthly_value / 3
                
                if monthly_value > 1000:
                    value_score += 3
                elif monthly_value > 500:
                    value_score += 2
                elif monthly_value > 100:
                    value_score += 1
            
            # Total customer invoices in last year
            year_ago = fields.Date.today() - timedelta(days=365)
            customer_invoices = self.env['account.move'].search([
                ('partner_id', '=', customer.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', year_ago)
            ])
            
            total_value = sum(customer_invoices.mapped('amount_total'))
            if total_value > 50000:
                value_score += 3
            elif total_value > 20000:
                value_score += 2
            elif total_value > 5000:
                value_score += 1
            
            # Customer tenure
            if customer.create_date:
                tenure_days = (fields.Date.today() - customer.create_date.date()).days
                if tenure_days > 365 * 3:  # 3+ years
                    value_score += 2
                elif tenure_days > 365:  # 1+ years
                    value_score += 1
            
            # Determine value classification
            if value_score >= 6:
                wizard.customer_value = 'vip'
            elif value_score >= 4:
                wizard.customer_value = 'high'
            elif value_score >= 2:
                wizard.customer_value = 'medium'
            else:
                wizard.customer_value = 'low'
    
    @api.depends('failure_severity', 'customer_value', 'failure_type', 'consecutive_failures')
    def _compute_recommended_action(self):
        """Compute recommended action based on failure analysis"""
        for wizard in self:
            # High-value customers get more lenient treatment
            if wizard.customer_value in ['vip', 'high']:
                if wizard.failure_type in ['card_expired', 'card_declined']:
                    wizard.recommended_action = 'payment_method_update'
                elif wizard.failure_type == 'insufficient_funds':
                    wizard.recommended_action = 'grace_period'
                else:
                    wizard.recommended_action = 'manual_contact'
            
            # Critical failures require immediate attention
            elif wizard.failure_severity == 'critical':
                if wizard.failure_type == 'fraud_suspected':
                    wizard.recommended_action = 'account_review'
                else:
                    wizard.recommended_action = 'suspend_service'
            
            # Multiple consecutive failures
            elif wizard.consecutive_failures >= 3:
                wizard.recommended_action = 'dunning_process'
            
            # Temporary issues
            elif wizard.failure_type in ['network_error', 'timeout', 'gateway_error']:
                wizard.recommended_action = 'delayed_retry'
            
            # Payment method issues
            elif wizard.failure_type in ['card_expired', 'invalid_card']:
                wizard.recommended_action = 'payment_method_update'
            
            # Default to retry for first-time failures
            else:
                wizard.recommended_action = 'delayed_retry'
    
    @api.depends('failure_severity', 'customer_value', 'consecutive_failures')
    def _compute_action_priority(self):
        """Compute action priority"""
        for wizard in self:
            priority_score = 0
            
            # Failure severity
            severity_scores = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            priority_score += severity_scores.get(wizard.failure_severity, 0)
            
            # Customer value
            value_scores = {'low': 0, 'medium': 1, 'high': 2, 'vip': 3}
            priority_score += value_scores.get(wizard.customer_value, 0)
            
            # Consecutive failures
            if wizard.consecutive_failures >= 3:
                priority_score += 2
            elif wizard.consecutive_failures >= 2:
                priority_score += 1
            
            # Determine priority
            if priority_score >= 6:
                wizard.action_priority = 'urgent'
            elif priority_score >= 4:
                wizard.action_priority = 'high'
            elif priority_score >= 2:
                wizard.action_priority = 'medium'
            else:
                wizard.action_priority = 'low'
    
    @api.depends('failure_type', 'gateway_response', 'attempted_amount')
    def _compute_fraud_risk(self):
        """Compute fraud risk assessment"""
        for wizard in self:
            risk_score = 0
            indicators = []
            
            # High-risk failure types
            if wizard.failure_type in ['fraud_suspected', 'authentication_failed']:
                risk_score += 50
                indicators.append('High-risk failure type')
            
            # Large amount transactions
            if wizard.attempted_amount > 5000:
                risk_score += 20
                indicators.append('Large transaction amount')
            
            # Analyze gateway response for fraud indicators
            if wizard.gateway_response:
                fraud_keywords = ['fraud', 'suspicious', 'security', 'velocity', 'risk']
                if any(keyword in wizard.gateway_response.lower() for keyword in fraud_keywords):
                    risk_score += 30
                    indicators.append('Fraud keywords in gateway response')
            
            # Multiple recent failures from same customer
            if wizard.consecutive_failures >= 5:
                risk_score += 25
                indicators.append('Multiple consecutive failures')
            
            wizard.fraud_risk_score = min(risk_score, 100)
            wizard.fraud_indicators = '\n'.join(indicators) if indicators else 'No fraud indicators detected'
            wizard.requires_fraud_review = risk_score >= 70
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('source_type')
    def _onchange_source_type(self):
        """Clear source records when type changes"""
        if self.source_type != 'single_invoice':
            self.invoice_id = False
        if self.source_type != 'subscription':
            self.subscription_id = False
        if self.source_type != 'customer':
            self.partner_id = False
        if self.source_type != 'billing_event':
            self.billing_event_id = False
        if self.source_type != 'payment_retry':
            self.payment_retry_id = False
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Auto-fill fields from invoice"""
        if self.invoice_id:
            self.attempted_amount = self.invoice_id.amount_residual
            self.subscription_id = self.invoice_id.subscription_id
            self.partner_id = self.invoice_id.partner_id
            if self.invoice_id.subscription_id:
                self.payment_method_id = self.invoice_id.subscription_id.payment_method_id
    
    @api.onchange('payment_retry_id')
    def _onchange_payment_retry_id(self):
        """Auto-fill fields from payment retry"""
        if self.payment_retry_id:
            self.attempted_amount = self.payment_retry_id.retry_amount
            self.failure_type = self.payment_retry_id.failure_reason
            self.failure_reason = self.payment_retry_id.failure_message
            self.partner_id = self.payment_retry_id.partner_id
            self.subscription_id = self.payment_retry_id.subscription_id
            self.invoice_id = self.payment_retry_id.invoice_id
            self.payment_method_id = self.payment_retry_id.payment_method_id
    
    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Set default values based on selected action"""
        if self.action_type == 'retry_payment':
            if not self.retry_delay_hours:
                self.retry_delay_hours = 24
        elif self.action_type == 'extend_grace':
            if not self.grace_period_days:
                self.grace_period_days = 7
        elif self.action_type == 'create_payment_plan':
            if not self.installment_count:
                self.installment_count = 3
            if not self.first_installment_date:
                self.first_installment_date = fields.Date.today() + timedelta(days=7)
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('retry_delay_hours')
    def _check_retry_delay(self):
        """Validate retry delay"""
        for wizard in self:
            if wizard.action_type == 'retry_payment' and wizard.retry_delay_hours < 1:
                raise ValidationError(_('Retry delay must be at least 1 hour'))
    
    @api.constrains('grace_period_days')
    def _check_grace_period(self):
        """Validate grace period"""
        for wizard in self:
            if wizard.action_type == 'extend_grace' and wizard.grace_period_days < 1:
                raise ValidationError(_('Grace period must be at least 1 day'))
    
    @api.constrains('installment_count')
    def _check_installment_count(self):
        """Validate installment count"""
        for wizard in self:
            if (wizard.action_type == 'create_payment_plan' and 
                wizard.installment_count < 2):
                raise ValidationError(_('Payment plan must have at least 2 installments'))
    
    # =============================================================================
    # MAIN ACTIONS
    # =============================================================================
    
    def action_process_failure(self):
        """Process the payment failure according to selected action"""
        self.ensure_one()
        
        # Validate before processing
        self._validate_before_processing()
        
        # Record the failure
        failure_record = self._create_failure_record()
        
        # Execute selected action
        action_result = self._execute_selected_action(failure_record)
        
        # Send notifications
        if self.notify_customer:
            self._send_customer_notification(action_result)
        
        if self.notify_internal:
            self._send_internal_notification(failure_record, action_result)
        
        # Create follow-up activities
        if self.assign_to_user:
            self._create_follow_up_activity(failure_record)
        
        # Mark as processed
        self.write({
            'processed': True,
            'processing_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment failure processed successfully'),
                'type': 'success',
            }
        }
    
    def _validate_before_processing(self):
        """Validate before processing"""
        if not self.failure_reason:
            raise UserError(_('Detailed failure reason is required'))
        
        if self.action_type == 'contact_customer' and not self.contact_method:
            raise UserError(_('Contact method is required'))
        
        if self.action_type == 'start_dunning' and not self.dunning_sequence_id:
            # Try to get default dunning sequence
            if self.subscription_id:
                self.dunning_sequence_id = self.subscription_id._get_default_dunning_sequence()
            if not self.dunning_sequence_id:
                raise UserError(_('Dunning sequence is required'))
        
        if self.assign_to_user and not self.assigned_user_id:
            self.assigned_user_id = self.env.user.id
    
    def _create_failure_record(self):
        """Create payment failure record for tracking"""
        return self.env['ams.payment.failure'].create({
            'partner_id': self.partner_id.id if self.partner_id else False,
            'subscription_id': self.subscription_id.id if self.subscription_id else False,
            'invoice_id': self.invoice_id.id if self.invoice_id else False,
            'payment_retry_id': self.payment_retry_id.id if self.payment_retry_id else False,
            'failure_date': self.failure_date,
            'failure_type': self.failure_type,
            'failure_reason': self.failure_reason,
            'gateway_error_code': self.gateway_error_code,
            'gateway_response': self.gateway_response,
            'attempted_amount': self.attempted_amount,
            'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
            'failure_severity': self.failure_severity,
            'fraud_risk_score': self.fraud_risk_score,
            'action_taken': self.action_type,
            'processed_by': self.env.user.id,
        })
    
    def _execute_selected_action(self, failure_record):
        """Execute the selected action"""
        if self.action_type == 'retry_payment':
            return self._retry_payment(failure_record)
        elif self.action_type == 'update_payment_method':
            return self._update_payment_method(failure_record)
        elif self.action_type == 'start_dunning':
            return self._start_dunning_process(failure_record)
        elif self.action_type == 'extend_grace':
            return self._extend_grace_period(failure_record)
        elif self.action_type == 'create_payment_plan':
            return self._create_payment_plan(failure_record)
        elif self.action_type == 'suspend_subscription':
            return self._suspend_subscription(failure_record)
        elif self.action_type == 'contact_customer':
            return self._contact_customer(failure_record)
        elif self.action_type == 'escalate_account':
            return self._escalate_account(failure_record)
        elif self.action_type == 'fraud_investigation':
            return self._start_fraud_investigation(failure_record)
        else:
            return {'success': True, 'message': 'Action deferred'}
    
    # =============================================================================
    # ACTION IMPLEMENTATIONS
    # =============================================================================
    
    def _retry_payment(self, failure_record):
        """Set up payment retry"""
        try:
            if self.invoice_id:
                # Create or update payment retry
                existing_retry = self.invoice_id.payment_retry_ids.filtered(
                    lambda r: r.state in ['pending', 'failed']
                )
                
                if existing_retry:
                    retry = existing_retry[0]
                    retry.write({
                        'max_retry_attempts': self.retry_max_attempts,
                        'initial_delay_hours': self.retry_delay_hours,
                        'use_smart_retry': self.use_exponential_backoff,
                    })
                else:
                    retry = self.env['ams.payment.retry'].create({
                        'subscription_id': self.subscription_id.id if self.subscription_id else False,
                        'invoice_id': self.invoice_id.id,
                        'failure_reason': self.failure_type,
                        'failure_message': self.failure_reason,
                        'retry_amount': self.attempted_amount,
                        'payment_method_id': self.payment_method_id.id if self.payment_method_id else False,
                        'max_retry_attempts': self.retry_max_attempts,
                        'initial_delay_hours': self.retry_delay_hours,
                    })
                
                return {'success': True, 'retry_id': retry.id, 'message': 'Payment retry scheduled'}
            
            return {'success': False, 'message': 'No invoice to retry'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _update_payment_method(self, failure_record):
        """Initiate payment method update process"""
        try:
            # Create activity to update payment method
            if self.subscription_id:
                self.subscription_id.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary='Update Payment Method Required',
                    note=f'Payment failed: {self.failure_reason}. Customer needs to update payment method.',
                    user_id=self.assigned_user_id.id if self.assigned_user_id else self.env.user.id,
                    date_deadline=self.due_date,
                )
            
            return {'success': True, 'message': 'Payment method update initiated'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _start_dunning_process(self, failure_record):
        """Start dunning process"""
        try:
            if self.invoice_id and self.dunning_sequence_id:
                dunning = self.env['ams.dunning.process'].create({
                    'subscription_id': self.subscription_id.id if self.subscription_id else False,
                    'invoice_id': self.invoice_id.id,
                    'dunning_sequence_id': self.dunning_sequence_id.id,
                    'failure_date': self.failure_date.date(),
                    'failure_reason': 'payment_failed',
                    'failed_amount': self.attempted_amount,
                })
                
                if self.start_dunning_immediately:
                    dunning.action_process_next_step()
                
                return {'success': True, 'dunning_id': dunning.id, 'message': 'Dunning process started'}
            
            return {'success': False, 'message': 'Missing invoice or dunning sequence'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _extend_grace_period(self, failure_record):
        """Extend grace period"""
        try:
            if self.invoice_id:
                new_grace_end = fields.Date.today() + timedelta(days=self.grace_period_days)
                self.invoice_id.write({
                    'grace_period_end': new_grace_end,
                })
                
                self.invoice_id.message_post(
                    body=f'Grace period extended by {self.grace_period_days} days. Reason: {self.grace_period_reason or "Payment failure"}',
                    subject='Grace Period Extended'
                )
                
                return {'success': True, 'new_grace_end': new_grace_end, 'message': 'Grace period extended'}
            
            return {'success': False, 'message': 'No invoice to extend grace period'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _create_payment_plan(self, failure_record):
        """Create payment plan"""
        try:
            if self.invoice_id:
                # Calculate installment amount
                installment_amount = self.attempted_amount / self.installment_count
                
                # Create payment plan
                payment_plan = self.env['ams.payment.plan'].create({
                    'partner_id': self.partner_id.id,
                    'total_amount': self.attempted_amount,
                    'installment_count': self.installment_count,
                    'installment_amount': installment_amount,
                    'frequency': self.installment_frequency,
                    'start_date': self.first_installment_date,
                    'invoice_ids': [(6, 0, [self.invoice_id.id])],
                    'failure_record_id': failure_record.id,
                })
                
                # Create installments
                current_date = self.first_installment_date
                for i in range(self.installment_count):
                    self.env['ams.payment.plan.installment'].create({
                        'payment_plan_id': payment_plan.id,
                        'sequence': i + 1,
                        'due_date': current_date,
                        'amount': installment_amount,
                    })
                    
                    # Calculate next installment date
                    if self.installment_frequency == 'weekly':
                        current_date += timedelta(weeks=1)
                    elif self.installment_frequency == 'bi_weekly':
                        current_date += timedelta(weeks=2)
                    elif self.installment_frequency == 'monthly':
                        current_date += timedelta(days=30)
                
                return {'success': True, 'payment_plan_id': payment_plan.id, 'message': 'Payment plan created'}
            
            return {'success': False, 'message': 'No invoice for payment plan'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _suspend_subscription(self, failure_record):
        """Suspend subscription"""
        try:
            if self.subscription_id:
                self.subscription_id.action_suspend_for_non_payment()
                return {'success': True, 'message': 'Subscription suspended'}
            
            return {'success': False, 'message': 'No subscription to suspend'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _contact_customer(self, failure_record):
        """Contact customer"""
        try:
            if self.contact_method == 'email' and self.contact_template_id:
                self.contact_template_id.send_mail(self.partner_id.id, force_send=True)
            
            # Create activity for follow-up
            self.partner_id.activity_schedule(
                'mail.mail_activity_data_call',
                summary=f'Customer Contact Required - {self.contact_method.title()}',
                note=f'Payment failure: {self.failure_reason}\nCustom message: {self.custom_message or "None"}',
                user_id=self.assigned_user_id.id if self.assigned_user_id else self.env.user.id,
                date_deadline=self.due_date,
            )
            
            return {'success': True, 'message': 'Customer contact initiated'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _escalate_account(self, failure_record):
        """Escalate account for management review"""
        try:
            # Create escalation activity
            manager_group = self.env.ref('account.group_account_manager', False)
            if manager_group:
                managers = manager_group.users
                for manager in managers:
                    self.partner_id.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=f'Account Escalation - Payment Failure',
                        note=f'''
Account requires management attention:
Customer: {self.partner_id.name}
Failure Type: {self.failure_type}
Amount: {self.attempted_amount}
Reason: {self.escalation_reason or self.failure_reason}
Severity: {self.failure_severity}
''',
                        user_id=manager.id,
                        date_deadline=fields.Date.today() + timedelta(days=1),
                    )
            
            return {'success': True, 'message': 'Account escalated to management'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _start_fraud_investigation(self, failure_record):
        """Start fraud investigation"""
        try:
            # Create fraud investigation record
            investigation = self.env['ams.fraud.investigation'].create({
                'partner_id': self.partner_id.id,
                'payment_failure_id': failure_record.id,
                'risk_score': self.fraud_risk_score,
                'indicators': self.fraud_indicators,
                'investigation_reason': f'Payment failure with fraud indicators: {self.failure_reason}',
                'assigned_user_id': self.assigned_user_id.id if self.assigned_user_id else self.env.user.id,
            })
            
            return {'success': True, 'investigation_id': investigation.id, 'message': 'Fraud investigation started'}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    # =============================================================================
    # NOTIFICATION METHODS
    # =============================================================================
    
    def _send_customer_notification(self, action_result):
        """Send notification to customer"""
        template_ref = f'ams_subscription_billing.email_template_payment_failure_{self.action_type}'
        template = self.env.ref(template_ref, False)
        
        if not template:
            template = self.env.ref('ams_subscription_billing.email_template_payment_failure_default', False)
        
        if template and self.partner_id:
            context = {
                'failure_type': self.failure_type,
                'action_taken': self.action_type,
                'custom_message': self.custom_message,
                'action_result': action_result,
            }
            template.with_context(context).send_mail(self.partner_id.id, force_send=True)
    
    def _send_internal_notification(self, failure_record, action_result):
        """Send notification to internal team"""
        if self.internal_notification_users:
            subject = f'Payment Failure Processed - {self.partner_id.name if self.partner_id else "Unknown"}'
            body = f'''
Payment failure has been processed:

Customer: {self.partner_id.name if self.partner_id else "Unknown"}
Failure Type: {self.failure_type}
Amount: {self.attempted_amount}
Action Taken: {self.action_type}
Severity: {self.failure_severity}
Priority: {self.action_priority}

Action Result: {action_result.get('message', 'No details available')}
'''
            
            for user in self.internal_notification_users:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body.replace('\n', '<br/>'),
                    'email_to': user.email,
                }).send()
    
    def _create_follow_up_activity(self, failure_record):
        """Create follow-up activity"""
        if self.assigned_user_id:
            summary = f'Follow-up: Payment Failure - {self.action_type.replace("_", " ").title()}'
            note = f'''
Payment failure follow-up required:

Customer: {self.partner_id.name if self.partner_id else "Unknown"}
Failure: {self.failure_type} - {self.failure_reason}
Action Taken: {self.action_type}
Priority: {self.action_priority}

Next steps: {self.custom_message or "Follow up on action completion"}
'''
            
            target_model = 'res.partner'
            target_id = self.partner_id.id if self.partner_id else False
            
            if self.subscription_id:
                target_model = 'ams.subscription'
                target_id = self.subscription_id.id
            
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                'summary': summary,
                'note': note,
                'res_model': target_model,
                'res_id': target_id,
                'user_id': self.assigned_user_id.id,
                'date_deadline': self.due_date,
            })