from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    _inherit = 'ams.subscription'
    
    # Accounting-specific fields
    account_mapping_id = fields.Many2one('product.account.mapping', 'Account Mapping',
                                        compute='_compute_account_mapping', store=True,
                                        help="Product account mapping for this subscription")
    
    # Revenue tracking
    total_invoiced = fields.Float('Total Invoiced', compute='_compute_financial_totals', store=True)
    total_paid = fields.Float('Total Paid', compute='_compute_financial_totals', store=True)
    amount_due = fields.Float('Amount Due', compute='_compute_financial_totals', store=True)
    
    # Deferred revenue tracking
    deferred_revenue_balance = fields.Float('Deferred Revenue Balance', 
                                           compute='_compute_deferred_revenue', store=True)
    monthly_recognition_amount = fields.Float('Monthly Recognition Amount',
                                             compute='_compute_deferred_revenue', store=True,
                                             help="Amount to recognize each month for deferred revenue")
    
    # Revenue recognition
    revenue_recognition_ids = fields.One2many('ams.revenue.recognition', 'subscription_id',
                                             'Revenue Recognition Entries')
    next_recognition_date = fields.Date('Next Recognition Date',
                                       compute='_compute_next_recognition', store=True)
    
    # Accounting status
    accounting_status = fields.Selection([
        ('pending', 'Pending Setup'),
        ('configured', 'Configured'),
        ('active', 'Active Accounting'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed')
    ], string='Accounting Status', compute='_compute_accounting_status', store=True)
    
    # Financial summary
    lifetime_value = fields.Float('Lifetime Value', compute='_compute_lifetime_value', store=True,
                                 help="Total expected revenue from this subscription")
    
    @api.depends('product_id')
    def _compute_account_mapping(self):
        for subscription in self:
            if subscription.product_id:
                mapping = self.env['product.account.mapping'].search([
                    ('product_id', '=', subscription.product_id.id)
                ], limit=1)
                subscription.account_mapping_id = mapping.id if mapping else False
            else:
                subscription.account_mapping_id = False
    
    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.payment_state')
    def _compute_financial_totals(self):
        for subscription in self:
            invoices = subscription.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            subscription.total_invoiced = sum(invoices.mapped('amount_total'))
            subscription.total_paid = subscription.total_invoiced - sum(invoices.mapped('amount_residual'))
            subscription.amount_due = sum(invoices.mapped('amount_residual'))
    
    @api.depends('account_mapping_id', 'amount', 'is_recurring', 'recurring_period')
    def _compute_deferred_revenue(self):
        for subscription in self:
            if (subscription.account_mapping_id and 
                subscription.account_mapping_id.use_deferred_revenue and
                subscription.is_recurring):
                
                # Calculate monthly recognition based on recurring period
                if subscription.recurring_period == 'monthly':
                    subscription.monthly_recognition_amount = subscription.amount
                elif subscription.recurring_period == 'quarterly':
                    subscription.monthly_recognition_amount = subscription.amount / 3
                elif subscription.recurring_period == 'yearly':
                    subscription.monthly_recognition_amount = subscription.amount / 12
                else:
                    subscription.monthly_recognition_amount = 0.0
                
                # Calculate current deferred balance
                total_deferred = subscription.total_paid
                total_recognized = sum(subscription.revenue_recognition_ids.mapped('amount'))
                subscription.deferred_revenue_balance = total_deferred - total_recognized
            else:
                subscription.monthly_recognition_amount = 0.0
                subscription.deferred_revenue_balance = 0.0
    
    @api.depends('revenue_recognition_ids', 'is_recurring', 'monthly_recognition_amount')
    def _compute_next_recognition(self):
        for subscription in self:
            if (subscription.is_recurring and 
                subscription.monthly_recognition_amount > 0 and
                subscription.deferred_revenue_balance > 0):
                
                # Find last recognition date
                last_recognition = subscription.revenue_recognition_ids.sorted('recognition_date', reverse=True)
                if last_recognition:
                    next_date = last_recognition[0].recognition_date + relativedelta(months=1)
                else:
                    next_date = subscription.start_date
                
                subscription.next_recognition_date = next_date
            else:
                subscription.next_recognition_date = False
    
    @api.depends('account_mapping_id', 'total_invoiced', 'amount_due')
    def _compute_accounting_status(self):
        for subscription in self:
            if not subscription.account_mapping_id:
                subscription.accounting_status = 'pending'
            elif subscription.state == 'cancelled':
                subscription.accounting_status = 'closed'
            elif subscription.amount_due > 0 and subscription.partner_id.credit_hold:
                subscription.accounting_status = 'suspended'
            elif subscription.total_invoiced > 0:
                subscription.accounting_status = 'active'
            else:
                subscription.accounting_status = 'configured'
    
    @api.depends('amount', 'is_recurring', 'recurring_period', 'state')
    def _compute_lifetime_value(self):
        for subscription in self:
            if subscription.state in ['cancelled', 'expired']:
                subscription.lifetime_value = subscription.total_invoiced
            elif subscription.is_recurring:
                # Estimate based on average subscription life (assume 3 years)
                periods_per_year = {'monthly': 12, 'quarterly': 4, 'yearly': 1}.get(subscription.recurring_period, 1)
                estimated_periods = periods_per_year * 3  # 3 years
                subscription.lifetime_value = subscription.amount * estimated_periods
            else:
                subscription.lifetime_value = subscription.amount
    
    def create_accounting_entries(self):
        """Create initial accounting entries for the subscription"""
        if not self.account_mapping_id:
            raise UserError(f"No account mapping found for product {self.product_id.name}. Please configure account mapping first.")
        
        if not self.amount or self.amount <= 0:
            raise UserError("Subscription amount must be greater than zero to create accounting entries.")
        
        # Create revenue entry
        move = self.account_mapping_id.create_revenue_entry(
            amount=self.amount,
            partner_id=self.partner_id.id,
            subscription_id=self.id
        )
        
        # Create deferred revenue recognition schedule if needed
        if (self.account_mapping_id.use_deferred_revenue and 
            self.is_recurring and 
            self.monthly_recognition_amount > 0):
            self._create_recognition_schedule()
        
        return move
    
    def _create_recognition_schedule(self):
        """Create revenue recognition schedule for deferred revenue"""
        if not self.account_mapping_id.use_deferred_revenue:
            return
        
        # Determine recognition period
        if self.recurring_period == 'monthly':
            periods = 1
        elif self.recurring_period == 'quarterly':
            periods = 3
        elif self.recurring_period == 'yearly':
            periods = 12
        else:
            periods = 12
        
        # Create recognition entries
        current_date = self.start_date
        monthly_amount = self.amount / periods
        
        for month in range(periods):
            recognition_date = current_date + relativedelta(months=month)
            
            self.env['ams.revenue.recognition'].create({
                'subscription_id': self.id,
                'recognition_date': recognition_date,
                'amount': monthly_amount,
                'state': 'scheduled',
                'description': f"Revenue recognition for {self.name} - Month {month + 1}"
            })
    
    def process_revenue_recognition(self):
        """Process due revenue recognition entries"""
        today = fields.Date.today()
        
        due_recognitions = self.revenue_recognition_ids.filtered(
            lambda r: r.state == 'scheduled' and r.recognition_date <= today
        )
        
        for recognition in due_recognitions:
            recognition.process_recognition()
    
    def action_configure_accounting(self):
        """Action to configure accounting for this subscription"""
        if not self.product_id:
            raise UserError("Product must be set before configuring accounting.")
        
        # Check if mapping exists, create if not
        mapping = self.env['product.account.mapping'].search([
            ('product_id', '=', self.product_id.id)
        ], limit=1)
        
        if not mapping:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Configure Product Account Mapping',
                'res_model': 'product.account.mapping',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_is_subscription_mapping': True,
                    'default_subscription_type_id': self.subscription_type_id.id,
                }
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Edit Product Account Mapping',
                'res_model': 'product.account.mapping',
                'view_mode': 'form',
                'res_id': mapping.id,
                'target': 'new',
            }
    
    def action_create_accounting_entries(self):
        """Action to create accounting entries"""
        try:
            move = self.create_accounting_entries()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Accounting Entry Created',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': move.id,
            }
        except Exception as e:
            raise UserError(f"Failed to create accounting entries: {str(e)}")
    
    def action_view_accounting_entries(self):
        """View all accounting entries for this subscription"""
        move_lines = self.env['account.move.line'].search([
            ('ams_subscription_id', '=', self.id)
        ])
        moves = move_lines.mapped('move_id')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Accounting Entries - {self.name}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
            'context': {'default_ams_subscription_id': self.id}
        }
    
    def action_view_revenue_recognition(self):
        """View revenue recognition schedule"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Revenue Recognition - {self.name}',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id}
        }

class AMSRevenueRecognition(models.Model):
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition'
    _order = 'recognition_date desc'
    _rec_name = 'description'
    
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='subscription_id.partner_id', store=True, readonly=True)
    product_id = fields.Many2one(related='subscription_id.product_id', store=True, readonly=True)
    
    recognition_date = fields.Date('Recognition Date', required=True)
    amount = fields.Float('Amount', required=True)
    description = fields.Char('Description', required=True)
    
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled')
    
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    company_id = fields.Many2one('res.company', related='subscription_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    def process_recognition(self):
        """Process the revenue recognition entry"""
        if self.state != 'scheduled':
            return
        
        if not self.subscription_id.account_mapping_id:
            raise UserError("No account mapping configured for subscription.")
        
        # Create journal entry to recognize revenue
        move = self.subscription_id.account_mapping_id.recognize_deferred_revenue(
            amount=self.amount,
            subscription_id=self.subscription_id.id
        )
        
        self.write({
            'state': 'processed',
            'move_id': move.id
        })
        
        _logger.info(f"Revenue recognition processed for subscription {self.subscription_id.name}: {self.amount}")
    
    def action_process(self):
        """Action to process this recognition entry"""
        self.process_recognition()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Revenue Recognized',
                'message': f'Revenue of {self.amount} has been recognized for {self.subscription_id.name}.',
                'type': 'success',
            }
        }
    
    def action_cancel(self):
        """Cancel this recognition entry"""
        if self.state == 'processed':
            raise UserError("Cannot cancel a processed revenue recognition entry.")
        
        self.state = 'cancelled'
    
    def action_view_journal_entry(self):
        """View the journal entry for this recognition"""
        if not self.move_id:
            raise UserError("No journal entry found for this recognition.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Revenue Recognition Entry',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }
    
    @api.model
    def cron_process_due_recognitions(self):
        """Cron job to process due revenue recognitions"""
        today = fields.Date.today()
        
        due_recognitions = self.search([
            ('state', '=', 'scheduled'),
            ('recognition_date', '<=', today)
        ])
        
        processed_count = 0
        for recognition in due_recognitions:
            try:
                recognition.process_recognition()
                processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to process revenue recognition {recognition.id}: {str(e)}")
        
        _logger.info(f"Processed {processed_count} revenue recognition entries")
        return processed_count