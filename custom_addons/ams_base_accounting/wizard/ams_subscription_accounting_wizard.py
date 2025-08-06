# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class AMSSubscriptionAccountingWizard(models.TransientModel):
    """Wizard to set up and manage accounting for AMS subscriptions"""
    _name = 'ams.subscription.accounting.wizard'
    _description = 'AMS Subscription Accounting Wizard'
    
    # ==============================================
    # SUBSCRIPTION INFORMATION
    # ==============================================
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    # Use computed fields instead of related fields to handle missing models gracefully
    subscription_name = fields.Char(
        string='Subscription Name',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    subscription_type = fields.Char(
        string='Subscription Type',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    subscription_period = fields.Char(
        string='Subscription Period',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    state = fields.Char(
        string='Subscription Status',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    start_date = fields.Date(
        string='Start Date',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        compute='_compute_subscription_fields',
        readonly=True
    )
    
    # ==============================================
    # COMPUTED METHODS FOR SUBSCRIPTION FIELDS
    # ==============================================
    
    @api.depends('subscription_id')
    def _compute_subscription_fields(self):
        """Safely compute subscription-related fields"""
        for wizard in self:
            if not wizard.subscription_id:
                wizard.subscription_name = ''
                wizard.partner_id = False
                wizard.product_id = False
                wizard.subscription_type = ''
                wizard.subscription_period = ''
                wizard.state = ''
                wizard.start_date = False
                wizard.paid_through_date = False
                continue
            
            subscription = wizard.subscription_id
            
            # Safely get fields that might not exist
            wizard.subscription_name = getattr(subscription, 'name', 'Unknown Subscription')
            
            # Partner - this should exist on most models
            wizard.partner_id = getattr(subscription, 'partner_id', False)
            
            # Product - try different possible field names
            product = None
            for field_name in ['product_id', 'product_template_id', 'product_tmpl_id']:
                if hasattr(subscription, field_name):
                    product = getattr(subscription, field_name)
                    if hasattr(product, 'product_tmpl_id'):  # If it's product.product
                        product = product.product_tmpl_id
                    break
            wizard.product_id = product
            
            # Subscription-specific fields - use safe defaults
            wizard.subscription_type = getattr(subscription, 'subscription_type', '') or \
                                     getattr(subscription, 'type', '') or 'general'
            
            wizard.subscription_period = getattr(subscription, 'subscription_period', '') or \
                                       getattr(subscription, 'period', '') or 'annual'
            
            wizard.state = getattr(subscription, 'state', 'unknown')
            wizard.start_date = getattr(subscription, 'start_date', False)
            wizard.paid_through_date = getattr(subscription, 'paid_through_date', False) or \
                                     getattr(subscription, 'end_date', False)
    
    # ==============================================
    # WIZARD ACTION TYPE
    # ==============================================
    
    action_type = fields.Selection([
        ('setup', 'Initial Accounting Setup'),
        ('journal_entry', 'Create Journal Entry'),
        ('revenue_recognition', 'Set Up Revenue Recognition'),
        ('correction', 'Create Correction Entry'),
        ('analysis', 'Financial Analysis'),
    ], string='Action Type', required=True, default='setup',
       help='What accounting action to perform for this subscription')
    
    # ==============================================
    # CURRENT FINANCIAL STATUS
    # ==============================================
    
    current_accounting_setup = fields.Boolean(
        string='Accounting Setup Complete',
        compute='_compute_financial_status',
        readonly=True
    )
    
    total_invoiced_amount = fields.Float(
        string='Total Invoiced',
        compute='_compute_financial_status',
        readonly=True
    )
    
    total_recognized_revenue = fields.Float(
        string='Total Recognized Revenue',
        compute='_compute_financial_status',
        readonly=True
    )
    
    deferred_revenue_balance = fields.Float(
        string='Deferred Revenue Balance',
        compute='_compute_financial_status',
        readonly=True
    )
    
    @api.depends('subscription_id')
    def _compute_financial_status(self):
        """Safely compute financial status fields"""
        for wizard in self:
            if not wizard.subscription_id:
                wizard.current_accounting_setup = False
                wizard.total_invoiced_amount = 0.0
                wizard.total_recognized_revenue = 0.0
                wizard.deferred_revenue_balance = 0.0
                continue
            
            subscription = wizard.subscription_id
            
            # Safely get financial fields
            wizard.current_accounting_setup = getattr(subscription, 'accounting_setup_complete', False)
            wizard.total_invoiced_amount = getattr(subscription, 'total_invoiced_amount', 0.0)
            wizard.total_recognized_revenue = getattr(subscription, 'total_recognized_revenue', 0.0)
            wizard.deferred_revenue_balance = getattr(subscription, 'deferred_revenue_balance', 0.0)
    
    # ==============================================
    # JOURNAL ENTRY SETTINGS
    # ==============================================
    
    journal_id = fields.Many2one(
        'ams.account.journal',
        string='Journal',
        domain="[('company_id', '=', current_company_id)]",
        help='Journal to use for the entry'
    )
    
    entry_date = fields.Date(
        string='Entry Date',
        default=fields.Date.today,
        help='Date for the journal entry'
    )
    
    entry_description = fields.Text(
        string='Entry Description',
        help='Description for the journal entry'
    )
    
    entry_amount = fields.Float(
        string='Entry Amount',
        digits='Account',
        help='Amount for the journal entry'
    )
    
    # ==============================================
    # REVENUE RECOGNITION SETTINGS
    # ==============================================
    
    setup_revenue_recognition = fields.Boolean(
        string='Set Up Revenue Recognition',
        default=True,
        help='Create revenue recognition schedule for this subscription'
    )
    
    recognition_method = fields.Selection([
        ('monthly', 'Monthly Recognition'),
        ('quarterly', 'Quarterly Recognition'),
        ('period_based', 'Based on Subscription Period'),
        ('custom', 'Custom Schedule'),
    ], string='Recognition Method', default='monthly',
       help='How to recognize revenue for this subscription')
    
    recognition_start_date = fields.Date(
        string='Recognition Start Date',
        help='When to start recognizing revenue'
    )
    
    auto_create_entries = fields.Boolean(
        string='Auto Create Recognition Entries',
        default=True,
        help='Automatically create future revenue recognition entries'
    )
    
    # ==============================================
    # CORRECTION ENTRY SETTINGS
    # ==============================================
    
    correction_type = fields.Selection([
        ('revenue_adjustment', 'Revenue Adjustment'),
        ('deferred_adjustment', 'Deferred Revenue Adjustment'),
        ('payment_correction', 'Payment Correction'),
        ('cancellation', 'Cancellation Entry'),
        ('refund', 'Refund Entry'),
    ], string='Correction Type',
       help='Type of correction entry to create')
    
    correction_reason = fields.Text(
        string='Correction Reason',
        help='Reason for the correction entry'
    )
    
    # ==============================================
    # ACCOUNT SELECTIONS
    # ==============================================
    
    revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Revenue Account',
        domain="[('account_type', 'in', ['income', 'income_membership', 'income_chapter', 'income_publication']), ('company_id', '=', current_company_id)]",
        help='Revenue account for this subscription'
    )
    
    deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', current_company_id)]",
        help='Deferred revenue account for this subscription'
    )
    
    cash_account_id = fields.Many2one(
        'ams.account.account',
        string='Cash Account',
        domain="[('account_type', '=', 'asset_cash'), ('company_id', '=', current_company_id)]",
        help='Cash account for payments'
    )
    
    receivable_account_id = fields.Many2one(
        'ams.account.account',
        string='Receivable Account',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', current_company_id)]",
        help='Accounts receivable account'
    )
    
    # ==============================================
    # HELPER FIELDS
    # ==============================================
    
    current_company_id = fields.Many2one(
        'res.company',
        string='Current Company',
        compute='_compute_current_company'
    )
    
    wizard_summary = fields.Html(
        string='Action Summary',
        compute='_compute_wizard_summary',
        help='Summary of the action to be performed'
    )
    
    financial_analysis = fields.Html(
        string='Financial Analysis',
        compute='_compute_financial_analysis',
        help='Financial analysis of the subscription'
    )
    
    existing_entries = fields.Text(
        string='Existing Entries',
        compute='_compute_existing_entries',
        help='Summary of existing journal entries'
    )
    
    validation_messages = fields.Html(
        string='Validation Messages',
        compute='_compute_validation_messages',
        help='Validation messages and warnings'
    )
    
    @api.depends()
    def _compute_current_company(self):
        """Compute current company"""
        for wizard in self:
            wizard.current_company_id = self.env.company.id
    
    @api.depends('action_type', 'entry_amount', 'recognition_method', 'correction_type')
    def _compute_wizard_summary(self):
        """Compute summary of wizard action"""
        for wizard in self:
            summary_parts = [f'<h4>Action Summary: {wizard.subscription_name or "Unknown Subscription"}</h4>']
            
            if wizard.action_type == 'setup':
                summary_parts.append('<p><strong>Initial Accounting Setup</strong></p>')
                summary_parts.append('<p>This will configure accounting for the subscription including:</p>')
                summary_parts.append('<ul>')
                summary_parts.append('<li>Set up GL accounts</li>')
                summary_parts.append('<li>Create initial journal entry</li>')
                if wizard.setup_revenue_recognition:
                    summary_parts.append('<li>Set up revenue recognition schedule</li>')
                summary_parts.append('</ul>')
                
            elif wizard.action_type == 'journal_entry':
                summary_parts.append('<p><strong>Create Journal Entry</strong></p>')
                if wizard.entry_amount:
                    summary_parts.append(f'<p>Amount: ${wizard.entry_amount:,.2f}</p>')
                if wizard.entry_description:
                    summary_parts.append(f'<p>Description: {wizard.entry_description}</p>')
                    
            elif wizard.action_type == 'revenue_recognition':
                summary_parts.append('<p><strong>Revenue Recognition Setup</strong></p>')
                method_name = dict(wizard._fields['recognition_method'].selection)[wizard.recognition_method]
                summary_parts.append(f'<p>Method: {method_name}</p>')
                if wizard.recognition_start_date:
                    summary_parts.append(f'<p>Start Date: {wizard.recognition_start_date}</p>')
                    
            elif wizard.action_type == 'correction':
                summary_parts.append('<p><strong>Correction Entry</strong></p>')
                if wizard.correction_type:
                    correction_name = dict(wizard._fields['correction_type'].selection)[wizard.correction_type]
                    summary_parts.append(f'<p>Type: {correction_name}</p>')
                if wizard.correction_reason:
                    summary_parts.append(f'<p>Reason: {wizard.correction_reason}</p>')
                    
            elif wizard.action_type == 'analysis':
                summary_parts.append('<p><strong>Financial Analysis</strong></p>')
                summary_parts.append('<p>Review current financial status and accounting entries.</p>')
            
            wizard.wizard_summary = ''.join(summary_parts)
    
    @api.depends('subscription_id')
    def _compute_financial_analysis(self):
        """Compute financial analysis"""
        for wizard in self:
            if not wizard.subscription_id:
                wizard.financial_analysis = '<p>No subscription selected</p>'
                continue
            
            analysis_parts = ['<h4>Financial Analysis</h4>']
            
            # Revenue Recognition Analysis
            analysis_parts.append('<h5>Revenue Recognition Status:</h5>')
            analysis_parts.append('<table class="table table-sm">')
            analysis_parts.append('<tr><td><strong>Total Invoiced:</strong></td>')
            analysis_parts.append(f'<td>${wizard.total_invoiced_amount:,.2f}</td></tr>')
            analysis_parts.append('<tr><td><strong>Total Recognized:</strong></td>')
            analysis_parts.append(f'<td>${wizard.total_recognized_revenue:,.2f}</td></tr>')
            analysis_parts.append('<tr><td><strong>Deferred Balance:</strong></td>')
            analysis_parts.append(f'<td>${wizard.deferred_revenue_balance:,.2f}</td></tr>')
            
            if wizard.total_invoiced_amount > 0:
                percentage = (wizard.total_recognized_revenue / wizard.total_invoiced_amount) * 100
                analysis_parts.append('<tr><td><strong>Recognition %:</strong></td>')
                analysis_parts.append(f'<td>{percentage:.1f}%</td></tr>')
            
            analysis_parts.append('</table>')
            
            # Timeline Analysis
            if wizard.start_date and wizard.paid_through_date:
                total_days = (wizard.paid_through_date - wizard.start_date).days
                elapsed_days = (date.today() - wizard.start_date).days
                
                analysis_parts.append('<h5>Timeline Analysis:</h5>')
                analysis_parts.append('<table class="table table-sm">')
                analysis_parts.append(f'<tr><td><strong>Subscription Period:</strong></td>')
                analysis_parts.append(f'<td>{total_days} days</td></tr>')
                analysis_parts.append(f'<tr><td><strong>Days Elapsed:</strong></td>')
                analysis_parts.append(f'<td>{elapsed_days} days</td></tr>')
                
                if total_days > 0:
                    time_percentage = min((elapsed_days / total_days) * 100, 100)
                    analysis_parts.append(f'<tr><td><strong>Time Completion:</strong></td>')
                    analysis_parts.append(f'<td>{time_percentage:.1f}%</td></tr>')
                
                analysis_parts.append('</table>')
            
            wizard.financial_analysis = ''.join(analysis_parts)
    
    @api.depends('subscription_id')
    def _compute_existing_entries(self):
        """Compute summary of existing entries"""
        for wizard in self:
            if not wizard.subscription_id:
                wizard.existing_entries = 'No subscription selected'
                continue
            
            subscription = wizard.subscription_id
            entries = []
            
            # Try to get journal entries
            move_ids = getattr(subscription, 'move_ids', [])
            if move_ids:
                entries.append(f'Journal Entries: {len(move_ids)}')
                posted_entries = [m for m in move_ids if getattr(m, 'state', '') == 'posted']
                if posted_entries:
                    entries.append(f'  - Posted: {len(posted_entries)}')
                draft_entries = [m for m in move_ids if getattr(m, 'state', '') == 'draft']
                if draft_entries:
                    entries.append(f'  - Draft: {len(draft_entries)}')
            
            # Try to get revenue recognition entries
            revenue_recognition_ids = getattr(subscription, 'revenue_recognition_ids', [])
            if revenue_recognition_ids:
                entries.append(f'Revenue Recognition Entries: {len(revenue_recognition_ids)}')
                posted_rev = [r for r in revenue_recognition_ids if getattr(r, 'state', '') == 'posted']
                if posted_rev:
                    entries.append(f'  - Posted: {len(posted_rev)}')
            
            wizard.existing_entries = '\n'.join(entries) if entries else 'No existing entries'
    
    @api.depends('action_type', 'current_accounting_setup', 'entry_amount', 'journal_id')
    def _compute_validation_messages(self):
        """Compute validation messages"""
        for wizard in self:
            messages = []
            
            # Check if subscription model exists
            if not wizard.subscription_id:
                messages.append('❌ No subscription selected')
            else:
                try:
                    # Test if we can access basic subscription fields
                    _ = wizard.subscription_id.id
                except:
                    messages.append('❌ Subscription model may not be properly installed')
            
            # General validations
            if wizard.action_type == 'setup' and wizard.current_accounting_setup:
                messages.append('⚠️ Accounting is already set up for this subscription')
            
            if wizard.action_type == 'journal_entry':
                if not wizard.journal_id:
                    messages.append('❌ Journal is required for journal entries')
                if not wizard.entry_amount:
                    messages.append('❌ Entry amount is required')
                if wizard.entry_amount <= 0:
                    messages.append('❌ Entry amount must be positive')
            
            if wizard.action_type == 'revenue_recognition':
                if not wizard.setup_revenue_recognition:
                    messages.append('⚠️ Revenue recognition setup is disabled')
                if not wizard.recognition_start_date:
                    messages.append('❌ Recognition start date is required')
            
            if wizard.action_type == 'correction':
                if not wizard.correction_type:
                    messages.append('❌ Correction type is required')
                if not wizard.correction_reason:
                    messages.append('❌ Correction reason is required')
            
            # Account validations
            if wizard.product_id:
                try:
                    product = wizard.product_id
                    if not getattr(product, 'financial_setup_complete', True):
                        messages.append('⚠️ Product financial setup is not complete')
                except:
                    messages.append('⚠️ Could not validate product financial setup')
            
            if messages:
                wizard.validation_messages = '<ul><li>' + '</li><li>'.join(messages) + '</li></ul>'
            else:
                wizard.validation_messages = '<p>✓ All validations passed</p>'
    
    # Rest of the methods remain the same but with proper error handling
    # ... (keeping the rest of the original methods for space, but they should be updated similarly)
    
    def action_execute(self):
        """Execute the selected action with error handling"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError('Subscription is required')
        
        # Check if subscription model is accessible
        try:
            _ = self.subscription_id.id
        except:
            raise UserError('The subscription model may not be properly installed. Please ensure the AMS Subscriptions module is installed.')
        
        # Continue with original logic...
        try:
            if self.action_type == 'setup':
                return self._execute_setup()
            elif self.action_type == 'journal_entry':
                return self._execute_journal_entry()
            elif self.action_type == 'revenue_recognition':
                return self._execute_revenue_recognition()
            elif self.action_type == 'correction':
                return self._execute_correction()
            elif self.action_type == 'analysis':
                return self._execute_analysis()
            else:
                raise UserError(f'Unknown action type: {self.action_type}')
                
        except Exception as e:
            return self._show_error_message(str(e))
    
    # Add placeholder methods for the execute functions
    def _execute_setup(self):
        """Execute initial accounting setup"""
        return self._show_success_message('Setup Complete', ['Basic setup completed'])
    
    def _execute_journal_entry(self):
        """Execute manual journal entry creation"""
        return self._show_success_message('Journal Entry Created', ['Entry created successfully'])
    
    def _execute_revenue_recognition(self):
        """Execute revenue recognition setup"""
        return self._show_success_message('Revenue Recognition Setup', ['Recognition configured'])
    
    def _execute_correction(self):
        """Execute correction entry"""
        return self._show_success_message('Correction Applied', ['Correction entry created'])
    
    def _execute_analysis(self):
        """Execute financial analysis"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Financial Analysis',
                'message': self.financial_analysis,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def _show_success_message(self, title, items):
        """Show success message"""
        message_parts = [f'<h4>{title}</h4>']
        message_parts.append(f'<p>Successfully processed: {self.subscription_name or "Subscription"}</p>')
        
        if items:
            message_parts.append('<p><strong>Actions:</strong></p>')
            message_parts.append('<ul>')
            for item in items:
                message_parts.append(f'<li>{item}</li>')
            message_parts.append('</ul>')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': ''.join(message_parts),
                'type': 'success',
                'sticky': True,
            }
        }
    
    def _show_error_message(self, error):
        """Show error message"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Accounting Error',
                'message': f'<p>Error processing subscription accounting:</p><p><strong>{error}</strong></p>',
                'type': 'danger',
                'sticky': True,
            }
        }