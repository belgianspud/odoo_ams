# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class AMSSubscription(models.Model):
    """Extend AMS Subscription with accounting functionality"""
    _inherit = 'ams.subscription'
    
    # ==============================================
    # ACCOUNTING INTEGRATION FIELDS
    # ==============================================
    
    # Journal entries related to this subscription
    move_ids = fields.One2many(
        'ams.account.move',
        'subscription_id',
        string='Journal Entries',
        readonly=True,
        help='All journal entries related to this subscription'
    )
    
    move_count = fields.Integer(
        string='Journal Entries Count',
        compute='_compute_move_count'
    )
    
    # Revenue recognition
    revenue_recognition_ids = fields.One2many(
        'ams.revenue.recognition',
        'subscription_id',
        string='Revenue Recognition Entries',
        readonly=True
    )
    
    revenue_recognition_count = fields.Integer(
        string='Revenue Recognition Count',
        compute='_compute_revenue_recognition_count'
    )
    
    # Financial amounts
    total_invoiced_amount = fields.Float(
        string='Total Invoiced',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Total amount invoiced for this subscription'
    )
    
    total_recognized_revenue = fields.Float(
        string='Total Recognized Revenue',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Total revenue recognized to date'
    )
    
    deferred_revenue_balance = fields.Float(
        string='Deferred Revenue Balance',
        compute='_compute_financial_amounts',
        store=True,
        digits='Account',
        help='Remaining deferred revenue balance'
    )
    
    # Accounting status
    accounting_setup_complete = fields.Boolean(
        string='Accounting Setup Complete',
        compute='_compute_accounting_setup_complete',
        help='All required accounting accounts are configured'
    )
    
    # Revenue recognition settings
    auto_recognize_revenue = fields.Boolean(
        string='Auto Recognize Revenue',
        default=True,
        help='Automatically create revenue recognition entries'
    )
    
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_date',
        help='Date when next revenue recognition is due'
    )
    
    # Last accounting activities
    last_journal_entry_date = fields.Datetime(
        string='Last Journal Entry Date',
        compute='_compute_last_activities',
        help='Date of last journal entry'
    )
    
    last_revenue_recognition_date = fields.Date(
        string='Last Revenue Recognition Date',
        compute='_compute_last_activities',
        help='Date of last revenue recognition'
    )
    
    @api.depends('move_ids')
    def _compute_move_count(self):
        """Compute number of journal entries"""
        for subscription in self:
            subscription.move_count = len(subscription.move_ids)
    
    @api.depends('revenue_recognition_ids')
    def _compute_revenue_recognition_count(self):
        """Compute number of revenue recognition entries"""
        for subscription in self:
            subscription.revenue_recognition_count = len(subscription.revenue_recognition_ids)
    
    @api.depends('move_ids.amount_total', 'revenue_recognition_ids.recognition_amount')
    def _compute_financial_amounts(self):
        """Compute financial amounts"""
        for subscription in self:
            # Total invoiced (from subscription journal entries)
            subscription_moves = subscription.move_ids.filtered(
                lambda m: m.move_type == 'subscription' and m.state == 'posted'
            )
            subscription.total_invoiced_amount = sum(subscription_moves.mapped('amount_total'))
            
            # Total recognized revenue
            posted_recognitions = subscription.revenue_recognition_ids.filtered(
                lambda r: r.state == 'posted'
            )
            subscription.total_recognized_revenue = sum(posted_recognitions.mapped('recognition_amount'))
            
            # Deferred revenue balance
            subscription.deferred_revenue_balance = (
                subscription.total_invoiced_amount - subscription.total_recognized_revenue
            )
    
    @api.depends('product_id.product_tmpl_id.financial_setup_complete')
    def _compute_accounting_setup_complete(self):
        """Check if accounting setup is complete"""
        for subscription in self:
            if subscription.product_id and subscription.product_id.product_tmpl_id:
                subscription.accounting_setup_complete = subscription.product_id.product_tmpl_id.financial_setup_complete
            else:
                subscription.accounting_setup_complete = False
    
    @api.depends('revenue_recognition_ids', 'subscription_period', 'last_revenue_recognition_date')
    def _compute_next_recognition_date(self):
        """Compute next revenue recognition date"""
        for subscription in self:
            if not subscription.auto_recognize_revenue or subscription.state != 'active':
                subscription.next_recognition_date = False
                continue
            
            last_recognition = subscription.revenue_recognition_ids.filtered(
                lambda r: r.state == 'posted'
            ).sorted('recognition_date', reverse=True)
            
            if last_recognition:
                last_date = last_recognition[0].recognition_date
            else:
                last_date = subscription.start_date or fields.Date.today()
            
            # Calculate next date based on subscription period
            if subscription.subscription_period == 'monthly':
                subscription.next_recognition_date = last_date + relativedelta(months=1)
            elif subscription.subscription_period == 'quarterly':
                subscription.next_recognition_date = last_date + relativedelta(months=3)
            elif subscription.subscription_period == 'semi_annual':
                subscription.next_recognition_date = last_date + relativedelta(months=6)
            elif subscription.subscription_period == 'annual':
                subscription.next_recognition_date = last_date + relativedelta(years=1)
            else:
                subscription.next_recognition_date = False
    
    @api.depends('move_ids.posted_date', 'revenue_recognition_ids.recognition_date')
    def _compute_last_activities(self):
        """Compute last accounting activities"""
        for subscription in self:
            # Last journal entry
            posted_moves = subscription.move_ids.filtered(lambda m: m.state == 'posted')
            if posted_moves:
                subscription.last_journal_entry_date = max(posted_moves.mapped('posted_date'))
            else:
                subscription.last_journal_entry_date = False
            
            # Last revenue recognition
            posted_recognitions = subscription.revenue_recognition_ids.filtered(lambda r: r.state == 'posted')
            if posted_recognitions:
                subscription.last_revenue_recognition_date = max(posted_recognitions.mapped('recognition_date'))
            else:
                subscription.last_revenue_recognition_date = False
    
    def action_view_journal_entries(self):
        """View journal entries for this subscription"""
        self.ensure_one()
        
        return {
            'name': f'Journal Entries - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
                'search_default_subscription_id': self.id,
            }
        }
    
    def action_view_revenue_recognition(self):
        """View revenue recognition entries for this subscription"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognition - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
                'search_default_subscription_id': self.id,
            }
        }
    
    def action_create_initial_journal_entry(self):
        """Create initial journal entry for subscription"""
        self.ensure_one()
        
        if not self.accounting_setup_complete:
            raise UserError('Accounting setup is not complete for this subscription')
        
        # Check if initial entry already exists
        existing_entry = self.move_ids.filtered(
            lambda m: m.move_type == 'subscription' and m.state in ['draft', 'posted']
        )
        if existing_entry:
            raise UserError('Initial journal entry already exists')
        
        # Get invoice amount (use product price if not available)
        invoice_amount = self.product_id.list_price
        if not invoice_amount:
            raise UserError('Cannot determine invoice amount for subscription')
        
        # Create journal entry
        move = self.env['ams.account.move'].create_subscription_entry(
            subscription=self,
            invoice_amount=invoice_amount,
            description=f'Initial payment - {self.name}'
        )
        
        self.message_post(body=f'Initial journal entry created: {move.name}')
        
        return {
            'name': 'Initial Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_revenue_recognition(self):
        """Create revenue recognition entry"""
        self.ensure_one()
        
        if not self.accounting_setup_complete:
            raise UserError('Accounting setup is not complete for this subscription')
        
        if not self.auto_recognize_revenue:
            raise UserError('Auto revenue recognition is disabled for this subscription')
        
        # Check if we need deferred revenue accounting
        product = self.product_id.product_tmpl_id
        if product.revenue_recognition_method != 'subscription':
            raise UserError('This subscription does not use subscription-based revenue recognition')
        
        # Calculate current month period
        today = fields.Date.today()
        period_start = date(today.year, today.month, 1)
        
        # Calculate period end
        if today.month == 12:
            period_end = date(today.year + 1, 1, 1) - relativedelta(days=1)
        else:
            period_end = date(today.year, today.month + 1, 1) - relativedelta(days=1)
        
        # Check if recognition already exists for this period
        existing = self.revenue_recognition_ids.filtered(
            lambda r: r.period_start <= today <= r.period_end and r.state != 'cancelled'
        )
        if existing:
            raise UserError(f'Revenue recognition already exists for current period: {existing[0].name}')
        
        # Calculate recognition amount
        total_amount = self.product_id.list_price
        if self.subscription_period == 'monthly':
            recognition_amount = total_amount
        elif self.subscription_period == 'quarterly':
            recognition_amount = total_amount / 3
        elif self.subscription_period == 'semi_annual':
            recognition_amount = total_amount / 6
        elif self.subscription_period == 'annual':
            recognition_amount = total_amount / 12
        else:
            raise UserError(f'Unsupported subscription period: {self.subscription_period}')
        
        # Create revenue recognition
        recognition_vals = {
            'subscription_id': self.id,
            'recognition_date': period_end,
            'period_start': period_start,
            'period_end': period_end,
            'total_subscription_amount': total_amount,
            'recognition_amount': recognition_amount,
            'recognition_method': 'monthly',
            'auto_post': True,
        }
        
        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
        
        self.message_post(body=f'Revenue recognition created: {recognition.name}')
        
        return {
            'name': 'Revenue Recognition',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'res_id': recognition.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_setup_accounting(self):
        """Set up accounting for this subscription"""
        self.ensure_one()
        
        return {
            'name': f'Accounting Setup - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.accounting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
            }
        }
    
    @api.model
    def create_from_invoice_payment_enhanced(self, invoice_line):
        """Enhanced subscription creation with accounting integration"""
        # Call original method
        subscription = super().create_from_invoice_payment(invoice_line)
        
        if not subscription:
            return False
        
        # Create initial accounting entries if accounting is set up
        try:
            if subscription.accounting_setup_complete:
                # Create initial journal entry
                invoice_amount = invoice_line.price_subtotal
                move = self.env['ams.account.move'].create_subscription_entry(
                    subscription=subscription,
                    invoice_amount=invoice_amount,
                    description=f'Payment from invoice {invoice_line.move_id.name}'
                )
                
                # Auto-post if configured
                if move.journal_id.auto_post:
                    move.action_post()
                
                subscription.message_post(
                    body=f'Accounting entry created automatically: {move.name}'
                )
        except Exception as e:
            # Log error but don't fail subscription creation
            subscription.message_post(
                body=f'Warning: Could not create accounting entry: {str(e)}'
            )
        
        return subscription
    
    def _handle_state_change_accounting(self, old_state, new_state):
        """Handle accounting implications of state changes"""
        self.ensure_one()
        
        if not self.accounting_setup_complete:
            return
        
        # Handle specific state transitions
        if old_state == 'active' and new_state in ['suspended', 'terminated']:
            self._handle_subscription_suspension()
        elif old_state in ['suspended', 'paused'] and new_state == 'active':
            self._handle_subscription_reactivation()
        elif new_state == 'terminated':
            self._handle_subscription_termination()
    
    def _handle_subscription_suspension(self):
        """Handle accounting when subscription is suspended"""
        # Stop revenue recognition for suspended subscriptions
        pending_recognitions = self.revenue_recognition_ids.filtered(
            lambda r: r.state == 'draft' and r.recognition_date >= fields.Date.today()
        )
        
        if pending_recognitions:
            pending_recognitions.action_cancel()
            self.message_post(
                body=f'Cancelled {len(pending_recognitions)} pending revenue recognition entries due to suspension'
            )
    
    def _handle_subscription_reactivation(self):
        """Handle accounting when subscription is reactivated"""
        # Resume revenue recognition if needed
        if self.auto_recognize_revenue and self.next_recognition_date:
            if self.next_recognition_date <= fields.Date.today():
                try:
                    self.action_create_revenue_recognition()
                except Exception as e:
                    self.message_post(
                        body=f'Could not auto-create revenue recognition on reactivation: {str(e)}'
                    )
    
    def _handle_subscription_termination(self):
        """Handle accounting when subscription is terminated"""
        # Check for remaining deferred revenue
        if self.deferred_revenue_balance > 0.01:  # Allow for rounding
            # Create adjustment entry to recognize remaining revenue or write off
            self._create_termination_adjustment()
    
    def _create_termination_adjustment(self):
        """Create adjustment entry for terminated subscription"""
        if self.deferred_revenue_balance <= 0.01:
            return
        
        # Get accounts
        product = self.product_id.product_tmpl_id
        deferred_revenue_account = product.get_deferred_revenue_account()
        
        # For termination, we might recognize remaining revenue or write it off
        # This is a business decision - for now, recognize remaining revenue
        revenue_account = product.get_revenue_account()
        
        # Get journal
        journal = self.env['ams.account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            self.message_post(body='Could not create termination adjustment: No general journal found')
            return
        
        # Create adjustment entry
        description = f'Termination adjustment - {self.name} (remaining deferred revenue)'
        
        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': description,
            'move_type': 'adjustment',
            'subscription_id': self.id,
            'partner_id': self.partner_id.id,
            'line_ids': [
                # Debit Deferred Revenue (clear remaining balance)
                (0, 0, {
                    'account_id': deferred_revenue_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.deferred_revenue_balance,
                    'credit': 0.0,
                    'name': description,
                }),
                # Credit Revenue (recognize remaining or write off)
                (0, 0, {
                    'account_id': revenue_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.deferred_revenue_balance,
                    'name': description,
                }),
            ]
        }
        
        move = self.env['ams.account.move'].create(move_vals)
        move.action_post()
        
        self.message_post(
            body=f'Termination adjustment created: {move.name} (${self.deferred_revenue_balance:.2f})'
        )
    
    def write(self, vals):
        """Override write to handle state changes"""
        # Track state changes for accounting
        state_changes = {}
        if 'state' in vals:
            for subscription in self:
                state_changes[subscription.id] = {
                    'old_state': subscription.state,
                    'new_state': vals['state']
                }
        
        result = super().write(vals)
        
        # Handle accounting implications of state changes
        for subscription in self:
            if subscription.id in state_changes:
                old_state = state_changes[subscription.id]['old_state']
                new_state = state_changes[subscription.id]['new_state']
                if old_state != new_state:
                    subscription._handle_state_change_accounting(old_state, new_state)
        
        return result
    
    @api.model
    def _cron_process_revenue_recognition(self):
        """Cron job to process revenue recognition for all subscriptions"""
        # Get subscriptions that need revenue recognition
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('auto_recognize_revenue', '=', True),
            ('accounting_setup_complete', '=', True),
            ('next_recognition_date', '<=', fields.Date.today()),
        ])
        
        processed = 0
        errors = []
        
        for subscription in subscriptions:
            try:
                subscription.action_create_revenue_recognition()
                processed += 1
            except Exception as e:
                errors.append(f'{subscription.name}: {str(e)}')
        
        # Log results
        if processed > 0 or errors:
            message = f'Revenue Recognition Processing Complete:\n'
            message += f'- Processed: {processed} subscriptions\n'
            if errors:
                message += f'- Errors: {len(errors)}\n'
                for error in errors[:5]:  # Limit to first 5 errors
                    message += f'  * {error}\n'
                if len(errors) > 5:
                    message += f'  * ... and {len(errors) - 5} more errors\n'
            
            # Create system notification
            self.env['mail.mail'].create({
                'subject': 'AMS Revenue Recognition Processing',
                'body_html': f'<pre>{message}</pre>',
                'email_to': self.env.user.partner_id.email,
            }).send()
    
    def get_financial_summary(self):
        """Get financial summary for this subscription"""
        self.ensure_one()
        
        return {
            'subscription_name': self.name,
            'total_invoiced': self.total_invoiced_amount,
            'total_recognized': self.total_recognized_revenue,
            'deferred_balance': self.deferred_revenue_balance,
            'recognition_percentage': (
                (self.total_recognized_revenue / self.total_invoiced_amount * 100) 
                if self.total_invoiced_amount > 0 else 0
            ),
            'journal_entries_count': self.move_count,
            'revenue_recognition_count': self.revenue_recognition_count,
            'next_recognition_date': self.next_recognition_date,
            'accounting_setup_complete': self.accounting_setup_complete,
        }


class AMSPaymentHistory(models.Model):
    """Extend Payment History with accounting integration"""
    _inherit = 'ams.payment.history'
    
    # Related journal entry
    journal_entry_id = fields.Many2one(
        'ams.account.move',
        string='Journal Entry',
        readonly=True,
        help='Journal entry created for this payment'
    )
    
    def _handle_payment_success(self):
        """Enhanced payment success handling with accounting"""
        result = super()._handle_payment_success()
        
        # Create accounting entry for successful payment
        for payment in self:
            if payment.subscription_id.accounting_setup_complete and not payment.journal_entry_id:
                try:
                    move = self.env['ams.account.move'].create_subscription_entry(
                        subscription=payment.subscription_id,
                        invoice_amount=payment.amount,
                        description=f'Payment received - {payment.subscription_id.name}'
                    )
                    
                    payment.journal_entry_id = move.id
                    
                    if move.journal_id.auto_post:
                        move.action_post()
                
                except Exception as e:
                    payment.subscription_id.message_post(
                        body=f'Warning: Could not create journal entry for payment: {str(e)}'
                    )
        
        return result
    
    def _handle_payment_failure(self):
        """Enhanced payment failure handling with accounting"""
        result = super()._handle_payment_failure()
        
        # Handle accounting implications of payment failures
        for payment in self:
            if payment.subscription_id.accounting_setup_complete:
                # Stop revenue recognition for failed payments
                subscription = payment.subscription_id
                if subscription.state == 'active':
                    # Don't automatically change state, but flag for attention
                    subscription.message_post(
                        body=f'Payment failure recorded - review revenue recognition: {payment.failure_reason}'
                    )
        
        return result