# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange

class AMSRevenueRecognitionWizard(models.TransientModel):
    """Wizard for managing revenue recognition"""
    _name = 'ams.revenue.recognition.wizard'
    _description = 'AMS Revenue Recognition Wizard'
    
    # ==============================================
    # WIZARD TYPE AND SCOPE
    # ==============================================
    
    wizard_type = fields.Selection([
        ('single_subscription', 'Single Subscription'),
        ('bulk_subscriptions', 'Multiple Subscriptions'),
        ('schedule_management', 'Schedule Management'),
        ('recognition_adjustment', 'Recognition Adjustment'),
        ('monthly_processing', 'Monthly Processing'),
    ], string='Wizard Type', required=True, default='single_subscription',
       help='Type of revenue recognition operation')
    
    # ==============================================
    # SUBSCRIPTION SELECTION
    # ==============================================
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        help='Single subscription for revenue recognition'
    )
    
    subscription_ids = fields.Many2many(
        'ams.subscription',
        string='Subscriptions',
        help='Multiple subscriptions for bulk processing'
    )
    
    subscription_filter = fields.Selection([
        ('active', 'Active Subscriptions'),
        ('all_states', 'All States'),
        ('specific_type', 'Specific Type'),
        ('date_range', 'Date Range'),
        ('product', 'Specific Product'),
    ], string='Subscription Filter', default='active',
       help='Filter criteria for bulk operations')
    
    subscription_type_filter = fields.Selection([
        ('individual', 'Individual Memberships'),
        ('enterprise', 'Enterprise Memberships'),
        ('chapter', 'Chapters'),
        ('publication', 'Publications'),
    ], string='Subscription Type Filter',
       help='Filter by subscription type')
    
    product_filter_id = fields.Many2one(
        'product.template',
        string='Product Filter',
        domain="[('is_subscription_product', '=', True)]",
        help='Filter by specific product'
    )
    
    date_from = fields.Date(
        string='Date From',
        help='Start date for filtering'
    )
    
    date_to = fields.Date(
        string='Date To',
        help='End date for filtering'
    )
    
    # ==============================================
    # RECOGNITION PERIOD SETTINGS
    # ==============================================
    
    recognition_period = fields.Selection([
        ('current_month', 'Current Month'),
        ('next_month', 'Next Month'),
        ('specific_month', 'Specific Month'),
        ('date_range', 'Date Range'),
        ('custom', 'Custom Period'),
    ], string='Recognition Period', default='current_month',
       help='Period for revenue recognition')
    
    specific_month = fields.Date(
        string='Specific Month',
        help='Specific month for recognition (first day of month)'
    )
    
    period_start_date = fields.Date(
        string='Period Start Date',
        help='Start date for recognition period'
    )
    
    period_end_date = fields.Date(
        string='Period End Date',
        help='End date for recognition period'
    )
    
    # ==============================================
    # RECOGNITION METHOD SETTINGS
    # ==============================================
    
    recognition_method = fields.Selection([
        ('monthly', 'Monthly Recognition'),
        ('daily_proration', 'Daily Proration'),
        ('period_end', 'End of Period'),
        ('straight_line', 'Straight Line'),
        ('usage_based', 'Usage Based'),
    ], string='Recognition Method', default='monthly',
       help='Method for calculating recognition amounts')
    
    auto_post_entries = fields.Boolean(
        string='Auto Post Entries',
        default=True,
        help='Automatically post created recognition entries'
    )
    
    create_journal_entries = fields.Boolean(
        string='Create Journal Entries',
        default=True,
        help='Create corresponding journal entries'
    )
    
    # ==============================================
    # ADJUSTMENT SETTINGS
    # ==============================================
    
    adjustment_type = fields.Selection([
        ('correction', 'Correction Entry'),
        ('reversal', 'Reversal Entry'),
        ('catch_up', 'Catch-up Recognition'),
        ('write_off', 'Write-off Entry'),
    ], string='Adjustment Type',
       help='Type of adjustment to make')
    
    adjustment_amount = fields.Float(
        string='Adjustment Amount',
        digits='Account',
        help='Amount for adjustment entry'
    )
    
    adjustment_reason = fields.Text(
        string='Adjustment Reason',
        help='Reason for the adjustment'
    )
    
    # ==============================================
    # SCHEDULE MANAGEMENT
    # ==============================================
    
    schedule_action = fields.Selection([
        ('create', 'Create New Schedule'),
        ('update', 'Update Existing Schedule'),
        ('regenerate', 'Regenerate Schedule'),
        ('delete', 'Delete Schedule'),
    ], string='Schedule Action',
       help='Action to perform on recognition schedules')
    
    existing_schedule_id = fields.Many2one(
        'ams.revenue.recognition.schedule',
        string='Existing Schedule',
        help='Existing schedule to update'
    )
    
    # ==============================================
    # PROCESSING RESULTS
    # ==============================================
    
    found_subscriptions_count = fields.Integer(
        string='Found Subscriptions',
        compute='_compute_found_subscriptions',
        help='Number of subscriptions matching criteria'
    )
    
    eligible_subscriptions_count = fields.Integer(
        string='Eligible Subscriptions',
        compute='_compute_eligible_subscriptions',
        help='Number of subscriptions eligible for recognition'
    )
    
    total_recognition_amount = fields.Float(
        string='Total Recognition Amount',
        compute='_compute_total_recognition_amount',
        digits='Account',
        help='Total amount to be recognized'
    )
    
    preview_entries = fields.Text(
        string='Preview Entries',
        compute='_compute_preview_entries',
        help='Preview of entries to be created'
    )
    
    processing_summary = fields.Html(
        string='Processing Summary',
        compute='_compute_processing_summary',
        help='Summary of what will be processed'
    )
    
    # ==============================================
    # VALIDATION AND STATUS
    # ==============================================
    
    validation_messages = fields.Html(
        string='Validation Messages',
        compute='_compute_validation_messages',
        help='Validation messages and warnings'
    )
    
    can_proceed = fields.Boolean(
        string='Can Proceed',
        compute='_compute_can_proceed',
        help='Whether the operation can proceed'
    )
    
    # ==============================================
    # COMPUTATION METHODS
    # ==============================================
    
    @api.depends('subscription_filter', 'subscription_type_filter', 'product_filter_id', 'date_from', 'date_to')
    def _compute_found_subscriptions(self):
        """Compute number of subscriptions found by filters"""
        for wizard in self:
            if wizard.wizard_type == 'single_subscription':
                wizard.found_subscriptions_count = 1 if wizard.subscription_id else 0
            elif wizard.wizard_type == 'bulk_subscriptions':
                domain = wizard._get_subscription_domain()
                wizard.found_subscriptions_count = self.env['ams.subscription'].search_count(domain)
            else:
                wizard.found_subscriptions_count = 0
    
    @api.depends('found_subscriptions_count', 'recognition_period', 'recognition_method')
    def _compute_eligible_subscriptions(self):
        """Compute number of eligible subscriptions"""
        for wizard in self:
            if wizard.wizard_type in ['single_subscription', 'bulk_subscriptions']:
                # For now, assume all found subscriptions are eligible
                # In reality, this would filter based on recognition requirements
                wizard.eligible_subscriptions_count = wizard.found_subscriptions_count
            else:
                wizard.eligible_subscriptions_count = 0
    
    @api.depends('eligible_subscriptions_count', 'recognition_method', 'period_start_date', 'period_end_date')
    def _compute_total_recognition_amount(self):
        """Compute total recognition amount"""
        for wizard in self:
            if wizard.wizard_type == 'single_subscription' and wizard.subscription_id:
                wizard.total_recognition_amount = wizard._calculate_subscription_recognition_amount(wizard.subscription_id)
            elif wizard.wizard_type == 'bulk_subscriptions':
                domain = wizard._get_subscription_domain()
                subscriptions = self.env['ams.subscription'].search(domain)
                total = sum(wizard._calculate_subscription_recognition_amount(sub) for sub in subscriptions)
                wizard.total_recognition_amount = total
            else:
                wizard.total_recognition_amount = 0.0
    
    @api.depends('wizard_type', 'eligible_subscriptions_count', 'total_recognition_amount')
    def _compute_preview_entries(self):
        """Compute preview of entries to be created"""
        for wizard in self:
            if wizard.eligible_subscriptions_count == 0:
                wizard.preview_entries = 'No eligible subscriptions found'
                continue
            
            preview_parts = []
            preview_parts.append(f'Eligible Subscriptions: {wizard.eligible_subscriptions_count}')
            preview_parts.append(f'Total Recognition Amount: ${wizard.total_recognition_amount:,.2f}')
            
            if wizard.wizard_type == 'single_subscription' and wizard.subscription_id:
                sub = wizard.subscription_id
                amount = wizard._calculate_subscription_recognition_amount(sub)
                preview_parts.append(f'\nSubscription: {sub.name}')
                preview_parts.append(f'Recognition Amount: ${amount:,.2f}')
                preview_parts.append(f'Method: {dict(wizard._fields["recognition_method"].selection)[wizard.recognition_method]}')
            
            elif wizard.wizard_type == 'monthly_processing':
                preview_parts.append('\nMonthly Processing:')
                preview_parts.append(f'- Process all active subscriptions')
                preview_parts.append(f'- Create recognition entries for current period')
                preview_parts.append(f'- Auto-post: {"Yes" if wizard.auto_post_entries else "No"}')
            
            wizard.preview_entries = '\n'.join(preview_parts)
    
    @api.depends('wizard_type', 'recognition_period', 'recognition_method', 'found_subscriptions_count')
    def _compute_processing_summary(self):
        """Compute processing summary"""
        for wizard in self:
            summary_parts = ['<h4>Revenue Recognition Processing Summary</h4>']
            
            # Wizard type
            wizard_type_name = dict(wizard._fields['wizard_type'].selection)[wizard.wizard_type]
            summary_parts.append(f'<p><strong>Operation Type:</strong> {wizard_type_name}</p>')
            
            # Scope
            if wizard.wizard_type == 'single_subscription':
                if wizard.subscription_id:
                    summary_parts.append(f'<p><strong>Subscription:</strong> {wizard.subscription_id.name}</p>')
                else:
                    summary_parts.append('<p><strong>Subscription:</strong> Not selected</p>')
            elif wizard.wizard_type == 'bulk_subscriptions':
                summary_parts.append(f'<p><strong>Subscriptions Found:</strong> {wizard.found_subscriptions_count}</p>')
                if wizard.subscription_filter != 'active':
                    filter_name = dict(wizard._fields['subscription_filter'].selection)[wizard.subscription_filter]
                    summary_parts.append(f'<p><strong>Filter:</strong> {filter_name}</p>')
            
            # Recognition settings
            if wizard.recognition_period:
                period_name = dict(wizard._fields['recognition_period'].selection)[wizard.recognition_period]
                summary_parts.append(f'<p><strong>Recognition Period:</strong> {period_name}</p>')
            
            if wizard.recognition_method:
                method_name = dict(wizard._fields['recognition_method'].selection)[wizard.recognition_method]
                summary_parts.append(f'<p><strong>Recognition Method:</strong> {method_name}</p>')
            
            # Processing options
            summary_parts.append('<h5>Processing Options:</h5>')
            summary_parts.append('<ul>')
            summary_parts.append(f'<li>Auto Post Entries: {"Yes" if wizard.auto_post_entries else "No"}</li>')
            summary_parts.append(f'<li>Create Journal Entries: {"Yes" if wizard.create_journal_entries else "No"}</li>')
            summary_parts.append('</ul>')
            
            # Amounts
            if wizard.total_recognition_amount > 0:
                summary_parts.append(f'<p><strong>Total Recognition Amount:</strong> ${wizard.total_recognition_amount:,.2f}</p>')
            
            wizard.processing_summary = ''.join(summary_parts)
    
    @api.depends('wizard_type', 'subscription_id', 'recognition_period', 'period_start_date', 'period_end_date')
    def _compute_validation_messages(self):
        """Compute validation messages"""
        for wizard in self:
            messages = []
            
            # Basic validations
            if wizard.wizard_type == 'single_subscription' and not wizard.subscription_id:
                messages.append('❌ Subscription must be selected')
            
            if wizard.wizard_type == 'bulk_subscriptions' and wizard.found_subscriptions_count == 0:
                messages.append('❌ No subscriptions found matching the filter criteria')
            
            if wizard.recognition_period == 'specific_month' and not wizard.specific_month:
                messages.append('❌ Specific month must be selected')
            
            if wizard.recognition_period == 'date_range':
                if not wizard.period_start_date:
                    messages.append('❌ Period start date is required')
                if not wizard.period_end_date:
                    messages.append('❌ Period end date is required')
                if wizard.period_start_date and wizard.period_end_date and wizard.period_start_date > wizard.period_end_date:
                    messages.append('❌ Period start date must be before end date')
            
            if wizard.wizard_type == 'recognition_adjustment':
                if not wizard.adjustment_type:
                    messages.append('❌ Adjustment type is required')
                if not wizard.adjustment_reason:
                    messages.append('❌ Adjustment reason is required')
                if wizard.adjustment_amount <= 0:
                    messages.append('❌ Adjustment amount must be positive')
            
            # Business logic validations
            if wizard.wizard_type == 'single_subscription' and wizard.subscription_id:
                sub = wizard.subscription_id
                if sub.state != 'active':
                    messages.append('⚠️ Subscription is not active')
                if not sub.accounting_setup_complete:
                    messages.append('⚠️ Accounting setup is not complete for this subscription')
                if sub.deferred_revenue_balance <= 0:
                    messages.append('⚠️ No deferred revenue balance to recognize')
            
            # Company setup validations
            company = self.env.company
            if not company.ams_accounting_setup_complete:
                messages.append('⚠️ AMS accounting setup is not complete for this company')
                
            if wizard.create_journal_entries and not company.default_revenue_recognition_journal_id:
                messages.append('⚠️ No revenue recognition journal configured')
            
            if messages:
                wizard.validation_messages = '<ul><li>' + '</li><li>'.join(messages) + '</li></ul>'
            else:
                wizard.validation_messages = '<p>✓ All validations passed</p>'
    
    @api.depends('validation_messages')
    def _compute_can_proceed(self):
        """Determine if operation can proceed"""
        for wizard in self:
            # Check for any error messages (❌)
            wizard.can_proceed = '❌' not in (wizard.validation_messages or '')
    
    # ==============================================
    # ONCHANGE METHODS
    # ==============================================
    
    @api.onchange('wizard_type')
    def _onchange_wizard_type(self):
        """Update fields when wizard type changes"""
        if self.wizard_type == 'single_subscription':
            self.subscription_filter = 'active'
        elif self.wizard_type == 'monthly_processing':
            self.recognition_period = 'current_month'
            self.recognition_method = 'monthly'
            self.subscription_filter = 'active'
    
    @api.onchange('recognition_period')
    def _onchange_recognition_period(self):
        """Update dates when recognition period changes"""
        today = date.today()
        
        if self.recognition_period == 'current_month':
            self.period_start_date = date(today.year, today.month, 1)
            self.period_end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
        
        elif self.recognition_period == 'next_month':
            next_month = today + relativedelta(months=1)
            self.period_start_date = date(next_month.year, next_month.month, 1)
            self.period_end_date = date(next_month.year, next_month.month, monthrange(next_month.year, next_month.month)[1])
        
        elif self.recognition_period == 'specific_month' and self.specific_month:
            month_date = self.specific_month
            self.period_start_date = date(month_date.year, month_date.month, 1)
            self.period_end_date = date(month_date.year, month_date.month, monthrange(month_date.year, month_date.month)[1])
    
    @api.onchange('specific_month')
    def _onchange_specific_month(self):
        """Update period dates when specific month changes"""
        if self.specific_month:
            month_date = self.specific_month
            self.period_start_date = date(month_date.year, month_date.month, 1)
            self.period_end_date = date(month_date.year, month_date.month, monthrange(month_date.year, month_date.month)[1])
    
    # ==============================================
    # HELPER METHODS
    # ==============================================
    
    def _get_subscription_domain(self):
        """Get domain for subscription filtering"""
        domain = []
        
        if self.subscription_filter == 'active':
            domain.append(('state', '=', 'active'))
        elif self.subscription_filter == 'specific_type' and self.subscription_type_filter:
            domain.append(('subscription_type', '=', self.subscription_type_filter))
        elif self.subscription_filter == 'product' and self.product_filter_id:
            domain.append(('product_id.product_tmpl_id', '=', self.product_filter_id.id))
        elif self.subscription_filter == 'date_range':
            if self.date_from:
                domain.append(('start_date', '>=', self.date_from))
            if self.date_to:
                domain.append(('start_date', '<=', self.date_to))
        
        # Always include subscriptions with deferred revenue accounting
        domain.append(('product_id.product_tmpl_id.revenue_recognition_method', '=', 'subscription'))
        
        return domain
    
    def _calculate_subscription_recognition_amount(self, subscription):
        """Calculate recognition amount for a subscription"""
        if not subscription.product_id:
            return 0.0
        
        if self.recognition_method == 'monthly':
            # Calculate monthly recognition amount
            total_amount = subscription.product_id.list_price
            
            if subscription.subscription_period == 'monthly':
                return total_amount
            elif subscription.subscription_period == 'quarterly':
                return total_amount / 3
            elif subscription.subscription_period == 'semi_annual':
                return total_amount / 6
            elif subscription.subscription_period == 'annual':
                return total_amount / 12
            else:
                return total_amount / 12  # Default to monthly
        
        elif self.recognition_method == 'daily_proration':
            # Calculate based on days in period
            if not self.period_start_date or not self.period_end_date:
                return 0.0
            
            period_days = (self.period_end_date - self.period_start_date).days + 1
            total_days = self._get_subscription_total_days(subscription)
            total_amount = subscription.product_id.list_price
            
            if total_days > 0:
                return (total_amount / total_days) * period_days
            else:
                return 0.0
        
        elif self.recognition_method == 'period_end':
            # Recognize full amount at end of period
            return subscription.product_id.list_price
        
        else:
            return 0.0
    
    def _get_subscription_total_days(self, subscription):
        """Get total days in subscription period"""
        if subscription.start_date and subscription.paid_through_date:
            return (subscription.paid_through_date - subscription.start_date).days + 1
        
        # Default based on subscription period
        period_days = {
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
        }
        return period_days.get(subscription.subscription_period, 365)
    
    # ==============================================
    # ACTION METHODS
    # ==============================================
    
    def action_process_recognition(self):
        """Process revenue recognition"""
        self.ensure_one()
        
        if not self.can_proceed:
            raise UserError('Cannot proceed. Please resolve validation issues first.')
        
        try:
            if self.wizard_type == 'single_subscription':
                return self._process_single_subscription()
            elif self.wizard_type == 'bulk_subscriptions':
                return self._process_bulk_subscriptions()
            elif self.wizard_type == 'monthly_processing':
                return self._process_monthly_recognition()
            elif self.wizard_type == 'recognition_adjustment':
                return self._process_adjustment()
            elif self.wizard_type == 'schedule_management':
                return self._process_schedule_management()
            else:
                raise UserError(f'Unknown wizard type: {self.wizard_type}')
                
        except Exception as e:
            return self._show_error_message(str(e))
    
    def _process_single_subscription(self):
        """Process single subscription recognition"""
        subscription = self.subscription_id
        recognition_amount = self._calculate_subscription_recognition_amount(subscription)
        
        if recognition_amount <= 0:
            raise UserError('No amount to recognize for this subscription')
        
        # Create recognition entry
        recognition_vals = {
            'subscription_id': subscription.id,
            'recognition_date': self.period_end_date or date.today(),
            'period_start': self.period_start_date or date.today(),
            'period_end': self.period_end_date or date.today(),
            'total_subscription_amount': subscription.product_id.list_price,
            'recognition_amount': recognition_amount,
            'recognition_method': self.recognition_method,
            'auto_post': self.auto_post_entries,
        }
        
        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
        
        # Confirm and post if requested
        recognition.action_confirm()
        if self.auto_post_entries:
            recognition.action_post()
        
        return self._show_success_message('Single Subscription Processed', [recognition])
    
    def _process_bulk_subscriptions(self):
        """Process multiple subscriptions"""
        domain = self._get_subscription_domain()
        subscriptions = self.env['ams.subscription'].search(domain)
        
        if not subscriptions:
            raise UserError('No subscriptions found matching the criteria')
        
        created_recognitions = []
        errors = []
        
        for subscription in subscriptions:
            try:
                recognition_amount = self._calculate_subscription_recognition_amount(subscription)
                
                if recognition_amount > 0:
                    recognition_vals = {
                        'subscription_id': subscription.id,
                        'recognition_date': self.period_end_date or date.today(),
                        'period_start': self.period_start_date or date.today(),
                        'period_end': self.period_end_date or date.today(),
                        'total_subscription_amount': subscription.product_id.list_price,
                        'recognition_amount': recognition_amount,
                        'recognition_method': self.recognition_method,
                        'auto_post': self.auto_post_entries,
                        'is_automated': True,
                    }
                    
                    recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
                    recognition.action_confirm()
                    
                    if self.auto_post_entries:
                        recognition.action_post()
                    
                    created_recognitions.append(recognition)
                    
            except Exception as e:
                errors.append(f'{subscription.name}: {str(e)}')
        
        return self._show_bulk_processing_results(created_recognitions, errors)
    
    def _process_monthly_recognition(self):
        """Process monthly revenue recognition for all eligible subscriptions"""
        today = date.today()
        
        # Set period if not already set
        if not self.period_start_date:
            self.period_start_date = date(today.year, today.month, 1)
            self.period_end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
        
        # Use the standard monthly processing method
        created_recognitions = self.env['ams.revenue.recognition'].create_monthly_recognition_entries(
            self.period_end_date
        )
        
        return self._show_success_message('Monthly Processing Complete', created_recognitions)
    
    def _process_adjustment(self):
        """Process recognition adjustment"""
        if not self.subscription_id:
            raise UserError('Subscription is required for adjustments')
        
        # Create adjustment recognition entry
        recognition_vals = {
            'subscription_id': self.subscription_id.id,
            'recognition_date': date.today(),
            'period_start': date.today(),
            'period_end': date.today(),
            'total_subscription_amount': self.subscription_id.product_id.list_price,
            'recognition_amount': self.adjustment_amount,
            'recognition_method': 'custom',
            'auto_post': self.auto_post_entries,
        }
        
        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
        
        # Add adjustment note
        recognition.message_post(
            body=f'Adjustment Entry: {self.adjustment_type}\nReason: {self.adjustment_reason}'
        )
        
        recognition.action_confirm()
        if self.auto_post_entries:
            recognition.action_post()
        
        return self._show_success_message('Adjustment Processed', [recognition])
    
    def _process_schedule_management(self):
        """Process schedule management action"""
        # This would be implemented based on the schedule_action
        raise UserError('Schedule management functionality is not yet implemented')
    
    # ==============================================
    # RESULT DISPLAY METHODS
    # ==============================================
    
    def _show_success_message(self, title, created_items):
        """Show success message"""
        message_parts = [f'<h4>{title}</h4>']
        
        if isinstance(created_items, list) and created_items:
            message_parts.append(f'<p>Successfully created {len(created_items)} revenue recognition entries:</p>')
            message_parts.append('<ul>')
            for item in created_items[:10]:  # Limit display
                if hasattr(item, 'name'):
                    message_parts.append(f'<li>{item.name} - ${item.recognition_amount:,.2f}</li>')
            if len(created_items) > 10:
                message_parts.append(f'<li>... and {len(created_items) - 10} more entries</li>')
            message_parts.append('</ul>')
            
            total_amount = sum(item.recognition_amount for item in created_items if hasattr(item, 'recognition_amount'))
            message_parts.append(f'<p><strong>Total Recognition Amount:</strong> ${total_amount:,.2f}</p>')
        
        if self.auto_post_entries:
            message_parts.append('<p>✓ Entries have been automatically posted</p>')
        else:
            message_parts.append('<p>ℹ️ Entries created in draft status - remember to post them</p>')
        
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
    
    def _show_bulk_processing_results(self, created_recognitions, errors):
        """Show bulk processing results"""
        message_parts = ['<h4>Bulk Processing Complete</h4>']
        
        if created_recognitions:
            message_parts.append(f'<p><strong>Success:</strong> Created {len(created_recognitions)} recognition entries</p>')
            total_amount = sum(r.recognition_amount for r in created_recognitions)
            message_parts.append(f'<p><strong>Total Amount:</strong> ${total_amount:,.2f}</p>')
        
        if errors:
            message_parts.append(f'<p><strong>Errors:</strong> {len(errors)} subscriptions had errors</p>')
            message_parts.append('<ul>')
            for error in errors[:5]:  # Limit error display
                message_parts.append(f'<li>{error}</li>')
            if len(errors) > 5:
                message_parts.append(f'<li>... and {len(errors) - 5} more errors</li>')
            message_parts.append('</ul>')
        
        msg_type = 'success' if created_recognitions and not errors else 'warning' if created_recognitions else 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Processing Results',
                'message': ''.join(message_parts),
                'type': msg_type,
                'sticky': True,
            }
        }
    
    def _show_error_message(self, error):
        """Show error message"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Processing Error',
                'message': f'<p>An error occurred during revenue recognition processing:</p><p><strong>{error}</strong></p>',
                'type': 'danger',
                'sticky': True,
            }
        }
    
    def action_preview_processing(self):
        """Preview what will be processed"""
        self.ensure_one()
        
        preview_content = f"""
        <div class="o_form_view">
            <h3>Revenue Recognition Preview</h3>
            
            {self.processing_summary}
            
            <h4>Preview Details:</h4>
            <pre>{self.preview_entries}</pre>
            
            {self.validation_messages}
            
            <p><em>Click "Process Recognition" to execute this operation.</em></p>
        </div>
        """
        
        return {
            'name': 'Processing Preview',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_content': preview_content,
                'default_wizard_id': self.id,
            }
        }
    
    def action_validate_setup(self):
        """Validate current setup"""
        # Trigger recomputation of validation messages
        self._compute_validation_messages()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Results',
                'message': self.validation_messages,
                'type': 'success' if self.can_proceed else 'warning',
                'sticky': True,
            }
        }


class AMSRevenueRecognitionPreview(models.TransientModel):
    """Preview wizard for revenue recognition processing"""
    _name = 'ams.revenue.recognition.preview'
    _description = 'AMS Revenue Recognition Preview'
    
    preview_content = fields.Html(
        string='Preview',
        readonly=True
    )
    
    wizard_id = fields.Many2one(
        'ams.revenue.recognition.wizard',
        string='Recognition Wizard'
    )
    
    def action_proceed_with_processing(self):
        """Proceed with the processing"""
        if self.wizard_id:
            return self.wizard_id.action_process_recognition()
        return {'type': 'ir.actions.act_window_close'}
    
    def action_back_to_wizard(self):
        """Go back to recognition wizard"""
        if self.wizard_id:
            return {
                'name': 'Revenue Recognition Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'ams.revenue.recognition.wizard',
                'res_id': self.wizard_id.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return {'type': 'ir.actions.act_window_close'}