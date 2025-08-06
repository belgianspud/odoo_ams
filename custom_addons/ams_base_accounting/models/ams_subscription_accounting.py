# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSSubscriptionAccounting(models.Model):
    """Bridge model connecting subscriptions to accounting configuration"""
    _name = 'ams.subscription.accounting'
    _description = 'AMS Subscription Accounting Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    
    # Subscription Reference
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    # Related Subscription Information (safe references)
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='subscription_id.partner_id',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        related='subscription_id.product_id',
        store=True,
        readonly=True
    )
    
    subscription_name = fields.Char(
        string='Subscription Name',
        related='subscription_id.name',
        store=True,
        readonly=True
    )
    
    subscription_state = fields.Selection(
        string='Subscription State',
        related='subscription_id.state',
        store=True,
        readonly=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Accounting Configuration
    revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Revenue Account',
        required=True,
        domain="[('account_type', 'in', ['income', 'income_membership', 'income_chapter', 'income_publication']), ('company_id', '=', company_id)]",
        tracking=True,
        help="Account for recognizing subscription revenue"
    )
    
    deferred_revenue_account_id = fields.Many2one(
        'ams.account.account',
        string='Deferred Revenue Account',
        required=True,
        domain="[('account_type', '=', 'liability_deferred_revenue'), ('company_id', '=', company_id)]",
        tracking=True,
        help="Account for storing unearned subscription revenue"
    )
    
    receivable_account_id = fields.Many2one(
        'ams.account.account',
        string='Receivable Account',
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', company_id)]",
        help="Account for subscription receivables"
    )
    
    # Journal Configuration
    journal_id = fields.Many2one(
        'ams.account.journal',
        string='Journal',
        required=True,
        domain="[('company_id', '=', company_id)]",
        tracking=True,
        help="Journal for subscription accounting entries"
    )
    
    revenue_recognition_journal_id = fields.Many2one(
        'ams.account.journal',
        string='Revenue Recognition Journal',
        domain="[('company_id', '=', company_id)]",
        help="Specific journal for revenue recognition entries"
    )
    
    # Revenue Recognition Settings
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('subscription', 'Subscription-based'),
        ('milestone', 'Milestone-based'),
        ('percentage', 'Percentage Completion'),
    ], string='Revenue Recognition Method', 
       default='subscription', required=True, tracking=True)
    
    recognition_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Recognition Frequency', default='monthly', tracking=True)
    
    # Automation Settings
    auto_create_entries = fields.Boolean(
        string='Auto-Create Entries',
        default=True,
        help="Automatically create accounting entries for subscription events"
    )
    
    auto_post_entries = fields.Boolean(
        string='Auto-Post Entries',
        default=True,
        help="Automatically post created accounting entries"
    )
    
    auto_revenue_recognition = fields.Boolean(
        string='Auto Revenue Recognition',
        default=True,
        help="Automatically create revenue recognition entries"
    )
    
    # Financial Status
    setup_complete = fields.Boolean(
        string='Setup Complete',
        compute='_compute_setup_status',
        store=True,
        help="Indicates if accounting setup is complete"
    )
    
    setup_issues = fields.Text(
        string='Setup Issues',
        compute='_compute_setup_status',
        help="List of issues preventing complete setup"
    )
    
    # Financial Data (computed from subscription - safe references)
    total_subscription_value = fields.Float(
        string='Total Subscription Value',
        compute='_compute_financial_data',
        store=True,
        digits='Account'
    )
    
    total_recognized_revenue = fields.Float(
        string='Total Recognized Revenue',
        compute='_compute_financial_data',
        store=True,
        digits='Account'
    )
    
    deferred_revenue_balance = fields.Float(
        string='Deferred Revenue Balance',
        compute='_compute_financial_data',
        store=True,
        digits='Account'
    )
    
    recognition_percentage = fields.Float(
        string='Recognition Percentage',
        compute='_compute_financial_data',
        store=True,
        digits=(12, 2)
    )
    
    # Related Records Count
    journal_entry_count = fields.Integer(
        string='Journal Entries',
        compute='_compute_entry_counts'
    )
    
    revenue_recognition_count = fields.Integer(
        string='Revenue Recognition Entries',
        compute='_compute_entry_counts'
    )
    
    # Status and Processing
    last_processed_date = fields.Date(
        string='Last Processed Date',
        readonly=True,
        help="Date when this subscription was last processed for accounting"
    )
    
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_date',
        help="Date for next revenue recognition entry"
    )
    
    processing_notes = fields.Text(
        string='Processing Notes',
        help="Notes about accounting processing for this subscription"
    )
    
    # Constraints
    _sql_constraints = [
        ('subscription_company_uniq', 'unique (subscription_id, company_id)', 
         'Each subscription can only have one accounting configuration per company!'),
    ]
    
    # Computed Methods
    @api.depends('revenue_account_id', 'deferred_revenue_account_id', 'journal_id')
    def _compute_setup_status(self):
        """Compute accounting setup status"""
        for record in self:
            issues = []
            
            if not record.revenue_account_id:
                issues.append("Revenue account not configured")
            
            if not record.deferred_revenue_account_id:
                issues.append("Deferred revenue account not configured")
            
            if not record.journal_id:
                issues.append("Journal not configured")
            
            # Check product configuration
            if record.product_id:
                if hasattr(record.product_id, 'financial_setup_complete'):
                    if not record.product_id.financial_setup_complete:
                        issues.append("Product financial setup incomplete")
            
            # Check subscription status
            if record.subscription_id:
                if hasattr(record.subscription_id, 'state'):
                    if record.subscription_id.state not in ['active', 'pending']:
                        issues.append(f"Subscription state is {record.subscription_id.state}")
            
            record.setup_complete = len(issues) == 0
            record.setup_issues = '\n'.join(issues) if issues else ''
    
    @api.depends('subscription_id')
    def _compute_financial_data(self):
        """Compute financial data from subscription"""
        for record in self:
            # Initialize defaults
            record.total_subscription_value = 0.0
            record.total_recognized_revenue = 0.0
            record.deferred_revenue_balance = 0.0
            record.recognition_percentage = 0.0
            
            if not record.subscription_id:
                continue
            
            # Get subscription total value (safe field access)
            subscription = record.subscription_id
            total_value = 0.0
            
            if hasattr(subscription, 'total_invoiced_amount'):
                total_value = subscription.total_invoiced_amount or 0.0
            elif hasattr(subscription, 'total_amount'):
                total_value = subscription.total_amount or 0.0
            elif hasattr(subscription, 'amount'):
                total_value = subscription.amount or 0.0
            
            record.total_subscription_value = total_value
            
            # Calculate recognized revenue from recognition entries
            recognized_revenue = sum(
                self.env['ams.revenue.recognition'].search([
                    ('subscription_id', '=', subscription.id),
                    ('state', '=', 'posted')
                ]).mapped('recognition_amount')
            )
            
            record.total_recognized_revenue = recognized_revenue
            record.deferred_revenue_balance = total_value - recognized_revenue
            
            if total_value > 0:
                record.recognition_percentage = (recognized_revenue / total_value) * 100
    
    def _compute_entry_counts(self):
        """Compute related entry counts"""
        for record in self:
            record.journal_entry_count = self.env['ams.account.move'].search_count([
                ('subscription_id', '=', record.subscription_id.id)
            ])
            
            record.revenue_recognition_count = self.env['ams.revenue.recognition'].search_count([
                ('subscription_id', '=', record.subscription_id.id)
            ])
    
    @api.depends('recognition_frequency', 'last_processed_date')
    def _compute_next_recognition_date(self):
        """Compute next revenue recognition date"""
        for record in self:
            if not record.last_processed_date:
                record.next_recognition_date = fields.Date.today()
            else:
                from dateutil.relativedelta import relativedelta
                
                if record.recognition_frequency == 'monthly':
                    record.next_recognition_date = record.last_processed_date + relativedelta(months=1)
                elif record.recognition_frequency == 'quarterly':
                    record.next_recognition_date = record.last_processed_date + relativedelta(months=3)
                elif record.recognition_frequency == 'annual':
                    record.next_recognition_date = record.last_processed_date + relativedelta(years=1)
                else:
                    record.next_recognition_date = False
    
    # Validation Methods
    @api.constrains('revenue_account_id', 'deferred_revenue_account_id')
    def _check_accounts(self):
        """Validate account configurations"""
        for record in self:
            if record.revenue_account_id == record.deferred_revenue_account_id:
                raise ValidationError(
                    "Revenue account and deferred revenue account cannot be the same."
                )
            
            # Check account types
            if record.revenue_account_id:
                if record.revenue_account_id.account_type not in [
                    'income', 'income_membership', 'income_chapter', 'income_publication'
                ]:
                    raise ValidationError(
                        f"Revenue account must be an income account type, "
                        f"got '{record.revenue_account_id.account_type}'"
                    )
            
            if record.deferred_revenue_account_id:
                if record.deferred_revenue_account_id.account_type != 'liability_deferred_revenue':
                    raise ValidationError(
                        "Deferred revenue account must be a deferred revenue liability account."
                    )
    
    # Lifecycle Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default values"""
        for vals in vals_list:
            # Set default accounts from product if available
            if 'subscription_id' in vals and not vals.get('revenue_account_id'):
                subscription = self.env['ams.subscription'].browse(vals['subscription_id'])
                if subscription.product_id:
                    product = subscription.product_id
                    if hasattr(product, 'revenue_account_id') and product.revenue_account_id:
                        vals['revenue_account_id'] = product.revenue_account_id.id
                    if hasattr(product, 'deferred_revenue_account_id') and product.deferred_revenue_account_id:
                        vals['deferred_revenue_account_id'] = product.deferred_revenue_account_id.id
        
        return super().create(vals_list)
    
    # Business Methods
    def setup_subscription_accounting(self):
        """Complete setup for subscription accounting"""
        self.ensure_one()
        
        if not self.setup_complete:
            raise UserError(f"Cannot complete setup due to issues:\n{self.setup_issues}")
        
        # Update product configuration if needed
        if self.product_id and hasattr(self.product_id, 'financial_setup_complete'):
            if not self.product_id.financial_setup_complete:
                self.product_id.write({
                    'financial_setup_complete': True,
                    'revenue_account_id': self.revenue_account_id.id,
                    'deferred_revenue_account_id': self.deferred_revenue_account_id.id,
                })
        
        # Create initial revenue recognition schedule if needed
        if self.auto_revenue_recognition and self.recognition_frequency:
            self._create_revenue_recognition_schedule()
        
        # Mark as processed
        self.last_processed_date = fields.Date.today()
        
        self.message_post(
            body="Subscription accounting setup completed successfully.",
            message_type='notification'
        )
    
    def _create_revenue_recognition_schedule(self):
        """Create revenue recognition schedule for this subscription"""
        # Check if schedule already exists
        existing_schedule = self.env['ams.revenue.recognition.schedule'].search([
            ('subscription_id', '=', self.subscription_id.id)
        ], limit=1)
        
        if existing_schedule:
            return existing_schedule
        
        # Get subscription dates
        start_date = fields.Date.today()
        end_date = start_date
        
        if hasattr(self.subscription_id, 'start_date') and self.subscription_id.start_date:
            start_date = self.subscription_id.start_date
        
        if hasattr(self.subscription_id, 'end_date') and self.subscription_id.end_date:
            end_date = self.subscription_id.end_date
        elif hasattr(self.subscription_id, 'paid_through_date') and self.subscription_id.paid_through_date:
            end_date = self.subscription_id.paid_through_date
        
        # Create schedule
        schedule_vals = {
            'subscription_id': self.subscription_id.id,
            'start_date': start_date,
            'end_date': end_date,
            'total_amount': self.total_subscription_value,
            'recognition_method': self.recognition_frequency,
            'frequency': self.recognition_frequency,
            'revenue_account_id': self.revenue_account_id.id,
            'deferred_revenue_account_id': self.deferred_revenue_account_id.id,
            'journal_id': self.journal_id.id,
            'auto_create_entries': self.auto_create_entries,
            'auto_post_entries': self.auto_post_entries,
            'company_id': self.company_id.id,
        }
        
        schedule = self.env['ams.revenue.recognition.schedule'].create(schedule_vals)
        return schedule
    
    def process_revenue_recognition(self):
        """Process revenue recognition for this subscription"""
        self.ensure_one()
        
        if not self.setup_complete:
            raise UserError("Accounting setup is not complete.")
        
        # Create revenue recognition entry for current period
        recognition_vals = self._prepare_recognition_entry()
        
        if recognition_vals:
            entry = self.env['ams.revenue.recognition'].create(recognition_vals)
            
            if self.auto_post_entries:
                entry.action_confirm()
                entry.action_post()
            
            self.last_processed_date = fields.Date.today()
            
            return entry
        
        return False
    
    def _prepare_recognition_entry(self):
        """Prepare values for revenue recognition entry"""
        if not self.deferred_revenue_balance > 0:
            return False  # Nothing to recognize
        
        # Calculate recognition amount based on frequency
        total_amount = self.total_subscription_value
        
        if self.recognition_frequency == 'monthly':
            recognition_amount = total_amount / 12  # Assume annual subscription
        elif self.recognition_frequency == 'quarterly':
            recognition_amount = total_amount / 4
        else:  # annual
            recognition_amount = total_amount
        
        # Don't recognize more than remaining balance
        recognition_amount = min(recognition_amount, self.deferred_revenue_balance)
        
        today = fields.Date.today()
        
        return {
            'subscription_id': self.subscription_id.id,
            'recognition_date': today,
            'period_start': today.replace(day=1),
            'period_end': today,  # Simplified
            'total_subscription_amount': total_amount,
            'recognition_amount': recognition_amount,
            'recognition_method': self.recognition_frequency,
            'revenue_account_id': self.revenue_account_id.id,
            'deferred_revenue_account_id': self.deferred_revenue_account_id.id,
            'journal_id': self.revenue_recognition_journal_id.id or self.journal_id.id,
            'is_automated': True,
            'auto_post': self.auto_post_entries,
            'company_id': self.company_id.id,
        }
    
    # View Actions
    def action_view_journal_entries(self):
        """View related journal entries"""
        self.ensure_one()
        
        return {
            'name': f'Journal Entries - {self.subscription_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.subscription_id.id)],
            'context': {'create': False}
        }
    
    def action_view_revenue_recognition(self):
        """View revenue recognition entries"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognition - {self.subscription_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.subscription_id.id)],
            'context': {'default_subscription_id': self.subscription_id.id}
        }
    
    def action_setup_wizard(self):
        """Open setup wizard"""
        self.ensure_one()
        
        return {
            'name': 'Configure Subscription Accounting',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.accounting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_type': 'setup',
                'default_subscription_id': self.subscription_id.id,
                'default_revenue_account_id': self.revenue_account_id.id,
                'default_deferred_revenue_account_id': self.deferred_revenue_account_id.id,
                'default_journal_id': self.journal_id.id,
            }
        }
    
    def action_process_recognition(self):
        """Process revenue recognition"""
        self.ensure_one()
        
        entry = self.process_revenue_recognition()
        
        if entry:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success!',
                    'message': f'Revenue recognition entry created: {entry.name}',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Information',
                    'message': 'No revenue recognition needed at this time.',
                    'type': 'info',
                }
            }
    
    # Utility Methods
    @api.model
    def setup_subscription_accounting_bulk(self, subscription_ids):
        """Bulk setup for multiple subscriptions"""
        created_records = []
        
        for subscription_id in subscription_ids:
            existing = self.search([('subscription_id', '=', subscription_id)], limit=1)
            
            if not existing:
                # Create basic accounting record
                vals = {
                    'subscription_id': subscription_id,
                    # Other fields would be set via onchange or defaults
                }
                record = self.create(vals)
                created_records.append(record)
        
        return created_records
    
    @api.model
    def process_all_revenue_recognition(self):
        """Process revenue recognition for all eligible subscriptions"""
        records = self.search([
            ('setup_complete', '=', True),
            ('auto_revenue_recognition', '=', True),
            ('subscription_state', '=', 'active'),
        ])
        
        processed_count = 0
        error_count = 0
        
        for record in records:
            try:
                entry = record.process_revenue_recognition()
                if entry:
                    processed_count += 1
            except Exception as e:
                error_count += 1
                record.message_post(
                    body=f"Revenue recognition processing failed: {str(e)}",
                    message_type='notification'
                )
        
        return {
            'processed': processed_count,
            'errors': error_count,
            'total': len(records)
        }