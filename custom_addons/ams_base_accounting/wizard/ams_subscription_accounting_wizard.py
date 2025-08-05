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
    
    subscription_name = fields.Char(
        related='subscription_id.name',
        string='Subscription Name',
        readonly=True
    )
    
    partner_id = fields.Many2one(
        related='subscription_id.partner_id',
        string='Customer',
        readonly=True
    )
    
    product_id = fields.Many2one(
        related='subscription_id.product_id',
        string='Product',
        readonly=True
    )
    
    subscription_type = fields.Selection(
        related='subscription_id.subscription_type',
        string='Subscription Type',
        readonly=True
    )
    
    subscription_period = fields.Selection(
        related='subscription_id.subscription_period',
        string='Subscription Period',
        readonly=True
    )
    
    state = fields.Selection(
        related='subscription_id.state',
        string='Subscription Status',
        readonly=True
    )
    
    start_date = fields.Date(
        related='subscription_id.start_date',
        string='Start Date',
        readonly=True
    )
    
    paid_through_date = fields.Date(
        related='subscription_id.paid_through_date',
        string='Paid Through Date',
        readonly=True
    )
    
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
        related='subscription_id.accounting_setup_complete',
        string='Accounting Setup Complete',
        readonly=True
    )
    
    total_invoiced_amount = fields.Float(
        related='subscription_id.total_invoiced_amount',
        string='Total Invoiced',
        readonly=True
    )
    
    total_recognized_revenue = fields.Float(
        related='subscription_id.total_recognized_revenue',
        string='Total Recognized Revenue',
        readonly=True
    )
    
    deferred_revenue_balance = fields.Float(
        related='subscription_id.deferred_revenue_balance',
        string='Deferred Revenue Balance',
        readonly=True
    )
    
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
            summary_parts = [f'<h4>Action Summary: {wizard.subscription_name}</h4>']
            
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
            
            sub = wizard.subscription_id
            analysis_parts = ['<h4>Financial Analysis</h4>']
            
            # Revenue Recognition Analysis
            analysis_parts.append('<h5>Revenue Recognition Status:</h5>')
            analysis_parts.append('<table class="table table-sm">')
            analysis_parts.append('<tr><td><strong>Total Invoiced:</strong></td>')
            analysis_parts.append(f'<td>${sub.total_invoiced_amount:,.2f}</td></tr>')
            analysis_parts.append('<tr><td><strong>Total Recognized:</strong></td>')
            analysis_parts.append(f'<td>${sub.total_recognized_revenue:,.2f}</td></tr>')
            analysis_parts.append('<tr><td><strong>Deferred Balance:</strong></td>')
            analysis_parts.append(f'<td>${sub.deferred_revenue_balance:,.2f}</td></tr>')
            
            if sub.total_invoiced_amount > 0:
                percentage = (sub.total_recognized_revenue / sub.total_invoiced_amount) * 100
                analysis_parts.append('<tr><td><strong>Recognition %:</strong></td>')
                analysis_parts.append(f'<td>{percentage:.1f}%</td></tr>')
            
            analysis_parts.append('</table>')
            
            # Timeline Analysis
            if sub.start_date and sub.paid_through_date:
                total_days = (sub.paid_through_date - sub.start_date).days
                elapsed_days = (date.today() - sub.start_date).days
                
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
            
            sub = wizard.subscription_id
            entries = []
            
            # Journal entries
            if sub.move_ids:
                entries.append(f'Journal Entries: {len(sub.move_ids)}')
                posted_entries = sub.move_ids.filtered(lambda m: m.state == 'posted')
                if posted_entries:
                    entries.append(f'  - Posted: {len(posted_entries)}')
                draft_entries = sub.move_ids.filtered(lambda m: m.state == 'draft')
                if draft_entries:
                    entries.append(f'  - Draft: {len(draft_entries)}')
            
            # Revenue recognition entries
            if sub.revenue_recognition_ids:
                entries.append(f'Revenue Recognition Entries: {len(sub.revenue_recognition_ids)}')
                posted_rev = sub.revenue_recognition_ids.filtered(lambda r: r.state == 'posted')
                if posted_rev:
                    entries.append(f'  - Posted: {len(posted_rev)}')
            
            wizard.existing_entries = '\n'.join(entries) if entries else 'No existing entries'
    
    @api.depends('action_type', 'current_accounting_setup', 'entry_amount', 'journal_id')
    def _compute_validation_messages(self):
        """Compute validation messages"""
        for wizard in self:
            messages = []
            
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
            product = wizard.subscription_id.product_id.product_tmpl_id if wizard.subscription_id else None
            if product and not product.financial_setup_complete:
                messages.append('⚠️ Product financial setup is not complete')
            
            if messages:
                wizard.validation_messages = '<ul><li>' + '</li><li>'.join(messages) + '</li></ul>'
            else:
                wizard.validation_messages = '<p>✓ All validations passed</p>'
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        subscription_id = self.env.context.get('default_subscription_id')
        if subscription_id:
            subscription = self.env['ams.subscription'].browse(subscription_id)
            
            # Set default journal based on subscription type
            if subscription.subscription_type in ['individual', 'enterprise']:
                journal = self.env.company.default_membership_journal_id
            else:
                journal = self.env['ams.account.journal'].search([
                    ('type', '=', 'general'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
            
            if journal:
                res['journal_id'] = journal.id
            
            # Set default entry amount
            if subscription.product_id:
                res['entry_amount'] = subscription.product_id.list_price
            
            # Set recognition start date
            res['recognition_start_date'] = subscription.start_date or date.today()
            
            # Set default accounts from product
            product = subscription.product_id.product_tmpl_id
            if product:
                if product.revenue_account_id:
                    res['revenue_account_id'] = product.revenue_account_id.id
                if product.deferred_revenue_account_id:
                    res['deferred_revenue_account_id'] = product.deferred_revenue_account_id.id
                if product.cash_account_id:
                    res['cash_account_id'] = product.cash_account_id.id
                if product.receivable_account_id:
                    res['receivable_account_id'] = product.receivable_account_id.id
        
        return res
    
    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Update fields when action type changes"""
        if self.action_type == 'setup':
            self.entry_description = f'Initial accounting setup - {self.subscription_name}'
            if self.subscription_id and self.subscription_id.product_id:
                self.entry_amount = self.subscription_id.product_id.list_price
        
        elif self.action_type == 'journal_entry':
            self.entry_description = f'Manual journal entry - {self.subscription_name}'
        
        elif self.action_type == 'revenue_recognition':
            if self.subscription_id and self.subscription_id.subscription_period:
                if self.subscription_id.subscription_period == 'monthly':
                    self.recognition_method = 'monthly'
                elif self.subscription_id.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                    self.recognition_method = 'period_based'
        
        elif self.action_type == 'correction':
            self.entry_description = f'Correction entry - {self.subscription_name}'
    
    @api.onchange('correction_type')
    def _onchange_correction_type(self):
        """Update fields when correction type changes"""
        if self.correction_type == 'revenue_adjustment':
            self.correction_reason = 'Revenue recognition adjustment'
        elif self.correction_type == 'deferred_adjustment':
            self.correction_reason = 'Deferred revenue balance adjustment'
        elif self.correction_type == 'payment_correction':
            self.correction_reason = 'Payment amount correction'
        elif self.correction_type == 'cancellation':
            self.correction_reason = 'Subscription cancellation entry'
        elif self.correction_type == 'refund':
            self.correction_reason = 'Customer refund processing'
    
    def action_execute(self):
        """Execute the selected action"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError('Subscription is required')
        
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
    
    def _execute_setup(self):
        """Execute initial accounting setup"""
        subscription = self.subscription_id
        
        # Create initial journal entry if amount provided
        created_items = []
        
        if self.entry_amount > 0:
            move = self.env['ams.account.move'].create_subscription_entry(
                subscription=subscription,
                invoice_amount=self.entry_amount,
                description=self.entry_description or f'Initial setup - {subscription.name}'
            )
            created_items.append(f'Journal Entry: {move.name}')
        
        # Set up revenue recognition if requested
        if self.setup_revenue_recognition:
            recognition = self._create_revenue_recognition_schedule()
            if recognition:
                created_items.append(f'Revenue Recognition: {len(recognition)} entries')
        
        # Update subscription accounting flags
        subscription.write({
            'auto_recognize_revenue': self.auto_create_entries,
        })
        
        return self._show_success_message('Accounting Setup Complete', created_items)
    
    def _execute_journal_entry(self):
        """Execute manual journal entry creation"""
        if not self.journal_id:
            raise UserError('Journal is required')
        if not self.entry_amount:
            raise UserError('Entry amount is required')
        
        # Create manual journal entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.entry_date,
            'ref': self.entry_description,
            'move_type': 'entry',
            'subscription_id': self.subscription_id.id,
            'partner_id': self.subscription_id.partner_id.id,
            'line_ids': self._prepare_journal_lines(),
        }
        
        move = self.env['ams.account.move'].create(move_vals)
        
        return self._show_journal_entry_result(move)
    
    def _execute_revenue_recognition(self):
        """Execute revenue recognition setup"""
        created_entries = self._create_revenue_recognition_schedule()
        
        if created_entries:
            return self._show_success_message(
                'Revenue Recognition Setup Complete',
                [f'Created {len(created_entries)} recognition entries']
            )
        else:
            raise UserError('No revenue recognition entries were created')
    
    def _execute_correction(self):
        """Execute correction entry"""
        if not self.correction_type:
            raise UserError('Correction type is required')
        if not self.correction_reason:
            raise UserError('Correction reason is required')
        
        # Create correction entry based on type
        move = self._create_correction_entry()
        
        return self._show_journal_entry_result(move)
    
    def _execute_analysis(self):
        """Execute financial analysis"""
        return {
            'name': f'Financial Analysis - {self.subscription_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.financial.analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.subscription_id.id,
                'default_analysis_content': self.financial_analysis,
            }
        }
    
    def _prepare_journal_lines(self):
        """Prepare journal entry lines"""
        lines = []
        
        # This is a simplified example - would be expanded based on entry type
        if self.cash_account_id and self.revenue_account_id:
            # Debit Cash
            lines.append((0, 0, {
                'account_id': self.cash_account_id.id,
                'partner_id': self.subscription_id.partner_id.id,
                'debit': self.entry_amount,
                'credit': 0.0,
                'name': self.entry_description,
            }))
            
            # Credit Revenue
            lines.append((0, 0, {
                'account_id': self.revenue_account_id.id,
                'partner_id': self.subscription_id.partner_id.id,
                'debit': 0.0,
                'credit': self.entry_amount,
                'name': self.entry_description,
            }))
        
        return lines
    
    def _create_revenue_recognition_schedule(self):
        """Create revenue recognition schedule"""
        subscription = self.subscription_id
        
        if not subscription.product_id:
            return []
        
        created_entries = []
        
        if self.recognition_method == 'monthly':
            # Create monthly recognition entries
            current_date = self.recognition_start_date or subscription.start_date
            end_date = subscription.paid_through_date
            amount = subscription.product_id.list_price
            
            if subscription.subscription_period == 'annual':
                monthly_amount = amount / 12
            elif subscription.subscription_period == 'quarterly':
                monthly_amount = amount / 3
            else:
                monthly_amount = amount
            
            while current_date <= end_date:
                period_end = min(
                    current_date + relativedelta(months=1) - relativedelta(days=1),
                    end_date
                )
                
                recognition_vals = {
                    'subscription_id': subscription.id,
                    'recognition_date': period_end,
                    'period_start': current_date,
                    'period_end': period_end,
                    'total_subscription_amount': amount,
                    'recognition_amount': monthly_amount,
                    'recognition_method': 'monthly',
                    'auto_post': self.auto_create_entries,
                }
                
                recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
                created_entries.append(recognition)
                
                current_date = current_date + relativedelta(months=1)
        
        return created_entries
    
    def _create_correction_entry(self):
        """Create correction journal entry"""
        journal = self.journal_id or self.env['ams.account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            raise UserError('No journal found for correction entry')
        
        move_vals = {
            'journal_id': journal.id,
            'date': self.entry_date,
            'ref': f'Correction: {self.correction_reason}',
            'move_type': 'adjustment',
            'subscription_id': self.subscription_id.id,
            'partner_id': self.subscription_id.partner_id.id,
            'line_ids': self._prepare_correction_lines(),
        }
        
        return self.env['ams.account.move'].create(move_vals)
    
    def _prepare_correction_lines(self):
        """Prepare correction entry lines"""
        lines = []
        
        # This would be expanded based on correction type
        if self.correction_type == 'revenue_adjustment' and self.entry_amount:
            if self.revenue_account_id and self.deferred_revenue_account_id:
                # Debit Deferred Revenue
                lines.append((0, 0, {
                    'account_id': self.deferred_revenue_account_id.id,
                    'partner_id': self.subscription_id.partner_id.id,
                    'debit': self.entry_amount,
                    'credit': 0.0,
                    'name': self.correction_reason,
                }))
                
                # Credit Revenue
                lines.append((0, 0, {
                    'account_id': self.revenue_account_id.id,
                    'partner_id': self.subscription_id.partner_id.id,
                    'debit': 0.0,
                    'credit': self.entry_amount,
                    'name': self.correction_reason,
                }))
        
        return lines
    
    def _show_success_message(self, title, items):
        """Show success message"""
        message_parts = [f'<h4>{title}</h4>']
        message_parts.append(f'<p>Successfully processed accounting for: {self.subscription_name}</p>')
        
        if items:
            message_parts.append('<p><strong>Created:</strong></p>')
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
    
    def _show_journal_entry_result(self, move):
        """Show journal entry creation result"""
        return {
            'name': f'Journal Entry Created',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
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
    
    def action_validate_setup(self):
        """Validate the current setup"""
        self.ensure_one()
        
        issues = []
        warnings = []
        
        # Validate based on action type
        if self.action_type == 'journal_entry':
            if not self.journal_id:
                issues.append('Journal is required')
            if not self.entry_amount or self.entry_amount <= 0:
                issues.append('Valid entry amount is required')
            if not self.cash_account_id or not self.revenue_account_id:
                warnings.append('Cash and revenue accounts should be configured')
        
        elif self.action_type == 'revenue_recognition':
            if not self.recognition_start_date:
                issues.append('Recognition start date is required')
            if not self.subscription_id.paid_through_date:
                issues.append('Subscription must have a paid through date')
        
        elif self.action_type == 'correction':
            if not self.correction_type:
                issues.append('Correction type is required')
            if not self.correction_reason:
                issues.append('Correction reason is required')
        
        # Show validation results
        return self._show_validation_results(issues, warnings)
    
    def _show_validation_results(self, issues, warnings):
        """Show validation results"""
        if not issues and not warnings:
            message = '✓ Setup is valid and ready to execute!'
            msg_type = 'success'
        else:
            message_parts = ['<h4>Setup Validation</h4>']
            
            if issues:
                message_parts.append('<p><strong>Issues (must be resolved):</strong></p>')
                message_parts.append('<ul>')
                for issue in issues:
                    message_parts.append(f'<li>❌ {issue}</li>')
                message_parts.append('</ul>')
            
            if warnings:
                message_parts.append('<p><strong>Warnings:</strong></p>')
                message_parts.append('<ul>')
                for warning in warnings:
                    message_parts.append(f'<li>⚠️ {warning}</li>')
                message_parts.append('</ul>')
            
            message = ''.join(message_parts)
            msg_type = 'warning' if issues else 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Results',
                'message': message,
                'type': msg_type,
                'sticky': True,
            }
        }


class AMSSubscriptionFinancialAnalysis(models.TransientModel):
    """Display detailed financial analysis for a subscription"""
    _name = 'ams.subscription.financial.analysis'
    _description = 'AMS Subscription Financial Analysis'
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    analysis_content = fields.Html(
        string='Financial Analysis',
        readonly=True
    )
    
    def action_export_analysis(self):
        """Export analysis to PDF or Excel"""
        # This would be implemented to export the analysis
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Export functionality coming soon!',
                'type': 'info',
            }
        }
    
    def action_back_to_subscription(self):
        """Go back to subscription"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }