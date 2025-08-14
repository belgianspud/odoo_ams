# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSExtendGracePeriodWizard(models.TransientModel):
    """Wizard for Extending Grace Periods for Overdue Invoices"""
    _name = 'ams.extend.grace.period.wizard'
    _description = 'AMS Extend Grace Period Wizard'
    
    # =============================================================================
    # BASIC INFORMATION
    # =============================================================================
    
    # Target Records
    apply_to = fields.Selection([
        ('single_invoice', 'Single Invoice'),
        ('subscription', 'All Subscription Invoices'),
        ('customer', 'All Customer Invoices'),
        ('multiple_invoices', 'Selected Invoices'),
    ], string='Apply To', default='single_invoice', required=True)
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')],
        help='Specific invoice to extend grace period'
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        help='Subscription to extend grace period for all invoices'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help='Customer to extend grace period for all invoices'
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        'extend_grace_wizard_invoice_rel',
        'wizard_id', 'invoice_id',
        string='Selected Invoices',
        domain=[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    )
    
    # =============================================================================
    # CURRENT STATUS INFORMATION
    # =============================================================================
    
    current_grace_end = fields.Date(
        string='Current Grace Period End',
        readonly=True,
        help='Current grace period end date'
    )
    
    current_due_date = fields.Date(
        string='Current Due Date',
        readonly=True,
        help='Original invoice due date'
    )
    
    days_overdue = fields.Integer(
        string='Days Overdue',
        readonly=True,
        help='Number of days the invoice is overdue'
    )
    
    current_status = fields.Char(
        string='Current Status',
        readonly=True,
        help='Current payment/dunning status'
    )
    
    # =============================================================================
    # EXTENSION CONFIGURATION
    # =============================================================================
    
    extension_type = fields.Selection([
        ('days', 'Extend by Days'),
        ('date', 'Extend to Specific Date'),
        ('payment_plan', 'Set up Payment Plan'),
        ('indefinite', 'Indefinite Extension'),
    ], string='Extension Type', default='days', required=True)
    
    extension_days = fields.Integer(
        string='Extension Days',
        default=30,
        help='Number of days to extend grace period'
    )
    
    new_grace_end_date = fields.Date(
        string='New Grace Period End',
        help='New grace period end date'
    )
    
    # Payment Plan Options
    enable_payment_plan = fields.Boolean(
        string='Enable Payment Plan',
        help='Set up installment payment plan'
    )
    
    payment_plan_installments = fields.Integer(
        string='Number of Installments',
        default=3,
        help='Number of payment installments'
    )
    
    payment_plan_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], string='Payment Frequency', default='monthly')
    
    first_payment_date = fields.Date(
        string='First Payment Date',
        help='Date of first installment payment'
    )
    
    # =============================================================================
    # BUSINESS JUSTIFICATION
    # =============================================================================
    
    reason_category = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('financial_hardship', 'Financial Hardship'),
        ('technical_issue', 'Technical Issue'),
        ('billing_error', 'Billing Error'),
        ('good_customer', 'Good Customer Relationship'),
        ('large_account', 'Large Account Accommodation'),
        ('seasonal_business', 'Seasonal Business'),
        ('payment_processing', 'Payment Processing Issue'),
        ('dispute_resolution', 'Dispute Resolution'),
        ('covid_relief', 'COVID-19 Relief'),
        ('other', 'Other'),
    ], string='Reason Category', required=True)
    
    reason_details = fields.Text(
        string='Detailed Reason',
        required=True,
        help='Detailed explanation for the grace period extension'
    )
    
    customer_communication = fields.Text(
        string='Customer Communication',
        help='Record of communication with customer'
    )
    
    # =============================================================================
    # APPROVAL AND AUTHORIZATION
    # =============================================================================
    
    requires_approval = fields.Boolean(
        string='Requires Management Approval',
        compute='_compute_requires_approval',
        help='Extension requires management approval'
    )
    
    approval_level = fields.Selection([
        ('team_lead', 'Team Lead'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('c_level', 'C-Level'),
    ], string='Required Approval Level',
    compute='_compute_approval_level')
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help='User who approved this extension'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date',
        help='Date and time of approval'
    )
    
    approval_notes = fields.Text(
        string='Approval Notes',
        help='Notes from approver'
    )
    
    # =============================================================================
    # IMPACT ASSESSMENT
    # =============================================================================
    
    total_amount_affected = fields.Monetary(
        string='Total Amount Affected',
        currency_field='currency_id',
        compute='_compute_impact_assessment',
        help='Total amount of invoices affected'
    )
    
    affected_invoice_count = fields.Integer(
        string='Affected Invoices',
        compute='_compute_impact_assessment',
        help='Number of invoices affected'
    )
    
    customer_payment_history = fields.Text(
        string='Payment History Summary',
        compute='_compute_customer_history',
        help='Summary of customer payment history'
    )
    
    risk_assessment = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ], string='Risk Assessment',
    compute='_compute_risk_assessment',
    help='Risk assessment for this extension')
    
    # =============================================================================
    # CONDITIONS AND MONITORING
    # =============================================================================
    
    set_conditions = fields.Boolean(
        string='Set Extension Conditions',
        help='Set specific conditions for the grace period extension'
    )
    
    condition_ids = fields.One2many(
        'ams.grace.extension.condition',
        'wizard_id',
        string='Extension Conditions'
    )
    
    # Monitoring
    enhanced_monitoring = fields.Boolean(
        string='Enhanced Monitoring',
        default=True,
        help='Enable enhanced monitoring during grace period'
    )
    
    escalation_threshold = fields.Selection([
        ('immediate', 'Immediate'),
        ('3_days', '3 Days Before'),
        ('7_days', '7 Days Before'),
        ('14_days', '14 Days Before'),
    ], string='Escalation Threshold', default='7_days',
    help='When to escalate if conditions are not met')
    
    # =============================================================================
    # CUSTOMER COMMUNICATION
    # =============================================================================
    
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help='Send notification to customer about grace period extension'
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Notification Template',
        domain="[('model', '=', 'account.move')]"
    )
    
    include_payment_link = fields.Boolean(
        string='Include Payment Link',
        default=True,
        help='Include payment portal link in notification'
    )
    
    custom_message = fields.Text(
        string='Custom Message',
        help='Additional message to include in notification'
    )
    
    # =============================================================================
    # DUNNING PROCESS HANDLING
    # =============================================================================
    
    pause_dunning = fields.Boolean(
        string='Pause Dunning Process',
        default=True,
        help='Pause active dunning processes during grace period'
    )
    
    reset_dunning_level = fields.Boolean(
        string='Reset Dunning Level',
        help='Reset dunning level to start fresh after grace period'
    )
    
    auto_resume_dunning = fields.Boolean(
        string='Auto-Resume Dunning',
        default=True,
        help='Automatically resume dunning if grace period expires without payment'
    )
    
    # =============================================================================
    # FIELDS AND METADATA
    # =============================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
    
    extension_summary = fields.Text(
        string='Extension Summary',
        readonly=True,
        help='Summary of the proposed extension'
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('extension_days', 'total_amount_affected', 'reason_category')
    def _compute_requires_approval(self):
        """Determine if extension requires approval"""
        for wizard in self:
            # Business rules for approval requirement
            requires_approval = False
            
            # Extensions over 30 days require approval
            if wizard.extension_days > 30:
                requires_approval = True
            
            # Large amounts require approval
            if wizard.total_amount_affected > 10000:  # Configurable threshold
                requires_approval = True
            
            # Certain reason categories always require approval
            high_risk_reasons = ['financial_hardship', 'dispute_resolution', 'other']
            if wizard.reason_category in high_risk_reasons:
                requires_approval = True
            
            wizard.requires_approval = requires_approval
    
    @api.depends('extension_days', 'total_amount_affected')
    def _compute_approval_level(self):
        """Determine required approval level"""
        for wizard in self:
            if not wizard.requires_approval:
                wizard.approval_level = False
            elif wizard.total_amount_affected > 50000 or wizard.extension_days > 90:
                wizard.approval_level = 'director'
            elif wizard.total_amount_affected > 20000 or wizard.extension_days > 60:
                wizard.approval_level = 'manager'
            else:
                wizard.approval_level = 'team_lead'
    
    @api.depends('apply_to', 'invoice_id', 'subscription_id', 'partner_id', 'invoice_ids')
    def _compute_impact_assessment(self):
        """Compute impact assessment"""
        for wizard in self:
            invoices = wizard._get_affected_invoices()
            wizard.affected_invoice_count = len(invoices)
            wizard.total_amount_affected = sum(invoices.mapped('amount_residual'))
    
    @api.depends('partner_id', 'invoice_id')
    def _compute_customer_history(self):
        """Compute customer payment history summary"""
        for wizard in self:
            if wizard.partner_id:
                customer = wizard.partner_id
            elif wizard.invoice_id:
                customer = wizard.invoice_id.partner_id
            else:
                wizard.customer_payment_history = ""
                continue
            
            # Get payment history summary
            history = wizard._analyze_payment_history(customer)
            wizard.customer_payment_history = history
    
    @api.depends('total_amount_affected', 'customer_payment_history', 'extension_days')
    def _compute_risk_assessment(self):
        """Compute risk assessment"""
        for wizard in self:
            risk_score = 0
            
            # Amount risk
            if wizard.total_amount_affected > 50000:
                risk_score += 3
            elif wizard.total_amount_affected > 20000:
                risk_score += 2
            elif wizard.total_amount_affected > 5000:
                risk_score += 1
            
            # Extension length risk
            if wizard.extension_days > 90:
                risk_score += 3
            elif wizard.extension_days > 60:
                risk_score += 2
            elif wizard.extension_days > 30:
                risk_score += 1
            
            # Customer history risk (would need payment history analysis)
            # For now, just basic assessment
            
            if risk_score >= 5:
                wizard.risk_assessment = 'critical'
            elif risk_score >= 3:
                wizard.risk_assessment = 'high'
            elif risk_score >= 1:
                wizard.risk_assessment = 'medium'
            else:
                wizard.risk_assessment = 'low'
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('apply_to')
    def _onchange_apply_to(self):
        """Clear fields when apply_to changes"""
        if self.apply_to != 'single_invoice':
            self.invoice_id = False
        if self.apply_to != 'subscription':
            self.subscription_id = False
        if self.apply_to != 'customer':
            self.partner_id = False
        if self.apply_to != 'multiple_invoices':
            self.invoice_ids = [(5, 0, 0)]
        
        self._update_current_status()
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Update current status when invoice changes"""
        self._update_current_status()
    
    @api.onchange('extension_type', 'extension_days')
    def _onchange_extension_settings(self):
        """Update calculated dates when extension settings change"""
        if self.extension_type == 'days' and self.extension_days:
            base_date = self.current_grace_end or fields.Date.today()
            self.new_grace_end_date = base_date + timedelta(days=self.extension_days)
        elif self.extension_type == 'indefinite':
            self.new_grace_end_date = False
        
        self._generate_extension_summary()
    
    @api.onchange('new_grace_end_date')
    def _onchange_new_grace_end_date(self):
        """Update extension days when date changes"""
        if self.new_grace_end_date and self.current_grace_end:
            delta = self.new_grace_end_date - self.current_grace_end
            self.extension_days = delta.days
        
        self._generate_extension_summary()
    
    @api.onchange('enable_payment_plan')
    def _onchange_enable_payment_plan(self):
        """Set default payment plan dates"""
        if self.enable_payment_plan and not self.first_payment_date:
            self.first_payment_date = fields.Date.today() + timedelta(days=7)
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('extension_days')
    def _check_extension_days(self):
        """Validate extension days"""
        for wizard in self:
            if wizard.extension_type == 'days' and wizard.extension_days <= 0:
                raise ValidationError(_('Extension days must be positive'))
            if wizard.extension_days > 365:
                raise ValidationError(_('Extension cannot exceed 365 days'))
    
    @api.constrains('new_grace_end_date')
    def _check_new_grace_end_date(self):
        """Validate new grace end date"""
        for wizard in self:
            if (wizard.extension_type == 'date' and 
                wizard.new_grace_end_date and 
                wizard.new_grace_end_date <= fields.Date.today()):
                raise ValidationError(_('New grace period end must be in the future'))
    
    @api.constrains('payment_plan_installments')
    def _check_payment_plan(self):
        """Validate payment plan"""
        for wizard in self:
            if wizard.enable_payment_plan:
                if wizard.payment_plan_installments < 2 or wizard.payment_plan_installments > 12:
                    raise ValidationError(_('Payment plan must have 2-12 installments'))
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _update_current_status(self):
        """Update current status fields"""
        if self.apply_to == 'single_invoice' and self.invoice_id:
            invoice = self.invoice_id
            self.current_grace_end = invoice.grace_period_end
            self.current_due_date = invoice.invoice_date_due
            
            if invoice.invoice_date_due:
                self.days_overdue = max(0, (fields.Date.today() - invoice.invoice_date_due).days)
            
            # Build status string
            status_parts = []
            if invoice.payment_state == 'paid':
                status_parts.append('Paid')
            elif invoice.payment_state == 'partial':
                status_parts.append('Partially Paid')
            else:
                status_parts.append('Unpaid')
            
            if invoice.is_overdue:
                status_parts.append(f'Overdue ({self.days_overdue} days)')
            
            if invoice.in_dunning_process:
                status_parts.append(f'Dunning Level {invoice.dunning_level}')
            
            self.current_status = ', '.join(status_parts)
        else:
            self._clear_current_status()
    
    def _clear_current_status(self):
        """Clear current status fields"""
        self.current_grace_end = False
        self.current_due_date = False
        self.days_overdue = 0
        self.current_status = ""
    
    def _get_affected_invoices(self):
        """Get invoices that will be affected by the extension"""
        if self.apply_to == 'single_invoice' and self.invoice_id:
            return self.invoice_id
        elif self.apply_to == 'subscription' and self.subscription_id:
            return self.subscription_id.subscription_invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state in ['not_paid', 'partial']
            )
        elif self.apply_to == 'customer' and self.partner_id:
            return self.env['account.move'].search([
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ])
        elif self.apply_to == 'multiple_invoices' and self.invoice_ids:
            return self.invoice_ids
        else:
            return self.env['account.move']
    
    def _analyze_payment_history(self, customer):
        """Analyze customer payment history"""
        # Get paid invoices from last 12 months
        cutoff_date = fields.Date.today() - timedelta(days=365)
        paid_invoices = self.env['account.move'].search([
            ('partner_id', '=', customer.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'paid'),
            ('invoice_date', '>=', cutoff_date)
        ])
        
        # Get overdue invoices
        overdue_invoices = self.env['account.move'].search([
            ('partner_id', '=', customer.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('is_overdue', '=', True)
        ])
        
        history_lines = []
        history_lines.append(f"Total invoices (12 months): {len(paid_invoices)}")
        
        if paid_invoices:
            total_paid = sum(paid_invoices.mapped('amount_total'))
            history_lines.append(f"Total paid amount: {total_paid:.2f}")
            
            # Calculate average payment delay
            payment_delays = []
            for invoice in paid_invoices:
                if invoice.invoice_date_due and invoice.payment_date:
                    delay = (invoice.payment_date.date() - invoice.invoice_date_due).days
                    if delay > 0:
                        payment_delays.append(delay)
            
            if payment_delays:
                avg_delay = sum(payment_delays) / len(payment_delays)
                history_lines.append(f"Average payment delay: {avg_delay:.1f} days")
            else:
                history_lines.append("Payments typically on time")
        
        history_lines.append(f"Currently overdue invoices: {len(overdue_invoices)}")
        
        if overdue_invoices:
            overdue_amount = sum(overdue_invoices.mapped('amount_residual'))
            history_lines.append(f"Total overdue amount: {overdue_amount:.2f}")
        
        return "\n".join(history_lines)
    
    def _generate_extension_summary(self):
        """Generate summary of the proposed extension"""
        if not self.apply_to:
            self.extension_summary = ""
            return
        
        summary_lines = []
        
        # Header
        summary_lines.append("=== GRACE PERIOD EXTENSION SUMMARY ===")
        
        # Target
        if self.apply_to == 'single_invoice' and self.invoice_id:
            summary_lines.append(f"Target: Invoice {self.invoice_id.name}")
            summary_lines.append(f"Customer: {self.invoice_id.partner_id.name}")
            summary_lines.append(f"Amount: {self.invoice_id.amount_residual:.2f}")
        elif self.apply_to == 'subscription' and self.subscription_id:
            summary_lines.append(f"Target: All invoices for subscription {self.subscription_id.name}")
        elif self.apply_to == 'customer' and self.partner_id:
            summary_lines.append(f"Target: All invoices for customer {self.partner_id.name}")
        elif self.apply_to == 'multiple_invoices':
            summary_lines.append(f"Target: {len(self.invoice_ids)} selected invoices")
        
        summary_lines.append("")
        
        # Extension details
        if self.extension_type == 'days':
            summary_lines.append(f"Extension: {self.extension_days} days")
            if self.current_grace_end:
                summary_lines.append(f"Current grace end: {self.current_grace_end}")
            if self.new_grace_end_date:
                summary_lines.append(f"New grace end: {self.new_grace_end_date}")
        elif self.extension_type == 'date':
            summary_lines.append(f"Extend to: {self.new_grace_end_date}")
        elif self.extension_type == 'indefinite':
            summary_lines.append("Extension: Indefinite")
        
        # Payment plan
        if self.enable_payment_plan:
            summary_lines.append("")
            summary_lines.append(f"Payment Plan: {self.payment_plan_installments} {self.payment_plan_frequency} installments")
            if self.first_payment_date:
                summary_lines.append(f"First payment: {self.first_payment_date}")
        
        # Impact
        summary_lines.append("")
        summary_lines.append(f"Total amount affected: {self.total_amount_affected:.2f}")
        summary_lines.append(f"Number of invoices: {self.affected_invoice_count}")
        summary_lines.append(f"Risk assessment: {self.risk_assessment or 'Not calculated'}")
        
        # Reason
        if self.reason_category:
            summary_lines.append("")
            summary_lines.append(f"Reason: {self.reason_category.replace('_', ' ').title()}")
        
        # Approval
        if self.requires_approval:
            summary_lines.append("")
            summary_lines.append(f"Requires approval: {self.approval_level.replace('_', ' ').title()}")
        
        self.extension_summary = "\n".join(summary_lines)
    
    # =============================================================================
    # MAIN ACTIONS
    # =============================================================================
    
    def action_request_approval(self):
        """Request approval for grace period extension"""
        self.ensure_one()
        
        if not self.requires_approval:
            raise UserError(_('This extension does not require approval'))
        
        # Create approval request activity
        approval_users = self._get_approval_users()
        if not approval_users:
            raise UserError(_('No approval users found for level: %s') % self.approval_level)
        
        for user in approval_users:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': f'Approve Grace Period Extension - {self.reason_category}',
                'note': f'''
Grace period extension request:
Target: {self.apply_to}
Amount: {self.total_amount_affected:.2f}
Extension: {self.extension_days} days
Reason: {self.reason_details}
Risk: {self.risk_assessment}
''',
                'res_model': 'ams.extend.grace.period.wizard',
                'res_id': self.id,
                'user_id': user.id,
                'date_deadline': fields.Date.today() + timedelta(days=1),
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Approval request sent'),
                'type': 'success',
            }
        }
    
    def action_approve_extension(self):
        """Approve the grace period extension"""
        self.ensure_one()
        
        if not self._can_approve():
            raise UserError(_('You do not have permission to approve this extension'))
        
        self.approved_by = self.env.user.id
        self.approval_date = fields.Datetime.now()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Extension approved'),
                'type': 'success',
            }
        }
    
    def action_apply_extension(self):
        """Apply the grace period extension"""
        self.ensure_one()
        
        # Validate before applying
        self._validate_before_apply()
        
        # Get affected invoices
        invoices = self._get_affected_invoices()
        if not invoices:
            raise UserError(_('No invoices found to extend grace period'))
        
        # Apply extension to invoices
        extension_results = self._apply_grace_extension(invoices)
        
        # Handle dunning processes
        if self.pause_dunning:
            self._pause_dunning_processes(invoices)
        
        # Create payment plan if requested
        if self.enable_payment_plan:
            self._create_payment_plan(invoices)
        
        # Set up monitoring conditions
        if self.set_conditions:
            self._create_monitoring_conditions()
        
        # Send customer notification
        if self.notify_customer:
            self._send_customer_notification(invoices)
        
        # Log the extension
        self._log_grace_extension(invoices, extension_results)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Grace period extended for %d invoice(s)') % len(invoices),
                'type': 'success',
            }
        }
    
    # =============================================================================
    # IMPLEMENTATION METHODS
    # =============================================================================
    
    def _validate_before_apply(self):
        """Validate before applying extension"""
        if self.requires_approval and not self.approved_by:
            raise UserError(_('Extension requires approval before applying'))
        
        if not self.reason_details:
            raise UserError(_('Detailed reason is required'))
        
        if self.extension_type == 'date' and not self.new_grace_end_date:
            raise UserError(_('New grace end date is required'))
        
        if self.enable_payment_plan and not self.first_payment_date:
            raise UserError(_('First payment date is required for payment plan'))
    
    def _apply_grace_extension(self, invoices):
        """Apply grace period extension to invoices"""
        results = {
            'extended_count': 0,
            'total_amount': 0,
            'errors': []
        }
        
        for invoice in invoices:
            try:
                # Calculate new grace end date
                if self.extension_type == 'days':
                    current_grace = invoice.grace_period_end or invoice.invoice_date_due or fields.Date.today()
                    new_grace_end = current_grace + timedelta(days=self.extension_days)
                elif self.extension_type == 'date':
                    new_grace_end = self.new_grace_end_date
                elif self.extension_type == 'indefinite':
                    new_grace_end = False
                else:
                    new_grace_end = invoice.grace_period_end
                
                # Update invoice
                invoice.write({
                    'grace_period_end': new_grace_end,
                    'suspend_service_date': new_grace_end + timedelta(days=7) if new_grace_end else False,
                })
                
                # Log the extension on the invoice
                invoice.message_post(
                    body=f'Grace period extended. New end date: {new_grace_end or "Indefinite"}. Reason: {self.reason_category}',
                    subject='Grace Period Extended'
                )
                
                results['extended_count'] += 1
                results['total_amount'] += invoice.amount_residual
                
            except Exception as e:
                results['errors'].append(f'Invoice {invoice.name}: {str(e)}')
                _logger.error(f'Error extending grace period for invoice {invoice.name}: {str(e)}')
        
        return results
    
    def _pause_dunning_processes(self, invoices):
        """Pause active dunning processes"""
        dunning_processes = self.env['ams.dunning.process'].search([
            ('invoice_id', 'in', invoices.ids),
            ('state', '=', 'active')
        ])
        
        for process in dunning_processes:
            process.action_pause()
            process.message_post(
                body=f'Dunning paused due to grace period extension: {self.reason_category}'
            )
    
    def _create_payment_plan(self, invoices):
        """Create payment plan for invoices"""
        total_amount = sum(invoices.mapped('amount_residual'))
        installment_amount = total_amount / self.payment_plan_installments
        
        payment_dates = []
        current_date = self.first_payment_date
        
        for i in range(self.payment_plan_installments):
            payment_dates.append(current_date)
            
            # Calculate next payment date
            if self.payment_plan_frequency == 'weekly':
                current_date += timedelta(weeks=1)
            elif self.payment_plan_frequency == 'bi_weekly':
                current_date += timedelta(weeks=2)
            elif self.payment_plan_frequency == 'monthly':
                current_date += timedelta(days=30)  # Approximate
        
        # Create payment plan record
        payment_plan = self.env['ams.payment.plan'].create({
            'partner_id': invoices[0].partner_id.id,
            'total_amount': total_amount,
            'installment_count': self.payment_plan_installments,
            'installment_amount': installment_amount,
            'frequency': self.payment_plan_frequency,
            'start_date': self.first_payment_date,
            'invoice_ids': [(6, 0, invoices.ids)],
            'grace_extension_wizard_id': self.id,
        })
        
        # Create installment records
        for i, payment_date in enumerate(payment_dates):
            self.env['ams.payment.plan.installment'].create({
                'payment_plan_id': payment_plan.id,
                'sequence': i + 1,
                'due_date': payment_date,
                'amount': installment_amount,
            })
        
        return payment_plan
    
    def _create_monitoring_conditions(self):
        """Create monitoring conditions"""
        for condition in self.condition_ids:
            # Create actual monitoring record
            self.env['ams.grace.period.monitoring'].create({
                'invoice_ids': [(6, 0, self._get_affected_invoices().ids)],
                'condition_type': condition.condition_type,
                'condition_value': condition.condition_value,
                'monitor_until': self.new_grace_end_date,
                'escalation_threshold': self.escalation_threshold,
                'wizard_id': self.id,
            })
    
    def _send_customer_notification(self, invoices):
        """Send notification to customer"""
        template = self.notification_template_id
        if not template:
            template = self.env.ref('ams_subscription_billing.email_template_grace_period_extended', False)
        
        if template:
            for invoice in invoices:
                ctx = {
                    'custom_message': self.custom_message,
                    'extension_days': self.extension_days,
                    'new_grace_end': self.new_grace_end_date,
                    'include_payment_link': self.include_payment_link,
                    'payment_plan': self.enable_payment_plan,
                }
                
                template.with_context(ctx).send_mail(invoice.id, force_send=True)
    
    def _log_grace_extension(self, invoices, results):
        """Log the grace period extension"""
        log_message = f'''
Grace Period Extension Applied:
- Invoices affected: {results['extended_count']}
- Total amount: {results['total_amount']:.2f}
- Extension type: {self.extension_type}
- Extension days: {self.extension_days}
- Reason: {self.reason_category}
- Applied by: {self.env.user.name}
- Date: {fields.Datetime.now()}
'''
        
        if results['errors']:
            log_message += f"\nErrors: {len(results['errors'])}"
        
        # Log on customer
        customer = invoices[0].partner_id if invoices else False
        if customer:
            customer.message_post(
                body=log_message,
                subject='Grace Period Extension Applied'
            )
        
        _logger.info(f'Grace period extension applied: {results}')
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _get_approval_users(self):
        """Get users who can approve this level"""
        # This would typically get users from groups or roles
        # For now, return users with accounting manager rights
        return self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('account.group_account_manager').id])
        ])
    
    def _can_approve(self):
        """Check if current user can approve"""
        approval_users = self._get_approval_users()
        return self.env.user in approval_users
    
    def action_preview_notification(self):
        """Preview customer notification"""
        self.ensure_one()
        
        if not self.notify_customer:
            raise UserError(_('Customer notification is not enabled'))
        
        invoices = self._get_affected_invoices()
        if not invoices:
            raise UserError(_('No invoices found for preview'))
        
        # Use first invoice for preview
        sample_invoice = invoices[0]
        
        return {
            'name': _('Notification Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.email.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.notification_template_id.id,
                'default_res_model': 'account.move',
                'default_res_id': sample_invoice.id,
                'default_custom_message': self.custom_message,
            }
        }


class AMSGraceExtensionCondition(models.TransientModel):
    """Conditions for Grace Period Extensions"""
    _name = 'ams.grace.extension.condition'
    _description = 'AMS Grace Extension Condition'
    
    wizard_id = fields.Many2one(
        'ams.extend.grace.period.wizard',
        string='Extension Wizard',
        required=True,
        ondelete='cascade'
    )
    
    condition_type = fields.Selection([
        ('partial_payment', 'Partial Payment Required'),
        ('communication', 'Regular Communication'),
        ('payment_plan_compliance', 'Payment Plan Compliance'),
        ('no_new_orders', 'No New Orders'),
        ('credit_hold', 'Credit Hold'),
        ('insurance_verification', 'Insurance Verification'),
        ('documentation', 'Required Documentation'),
        ('other', 'Other Condition'),
    ], string='Condition Type', required=True)
    
    condition_value = fields.Char(
        string='Condition Details',
        required=True,
        help='Specific details of the condition'
    )
    
    due_date = fields.Date(
        string='Due Date',
        help='Date by which condition must be met'
    )
    
    is_mandatory = fields.Boolean(
        string='Mandatory',
        default=True,
        help='Condition must be met to continue grace period'
    )
    
    description = fields.Text(
        string='Description',
        help='Additional description of the condition'
    )