from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionAccounting(models.Model):
    """
    Enhanced subscription model with advanced accounting integration
    """
    _inherit = 'ams.subscription'
    
    # Accounting Integration Fields
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account',
        help="Analytic account for tracking this subscription's financial performance")
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('proportional', 'Proportional Over Period')
    ], string='Revenue Recognition', default='proportional')
    
    deferred_revenue_account_id = fields.Many2one('account.account', 'Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current')]")
    
    # Financial Tracking
    total_invoiced = fields.Float('Total Invoiced', compute='_compute_financial_totals', store=True)
    total_paid = fields.Float('Total Paid', compute='_compute_financial_totals', store=True)
    outstanding_balance = fields.Float('Outstanding Balance', compute='_compute_financial_totals', store=True)
    
    # Revenue Analytics
    monthly_recurring_revenue = fields.Float('MRR', compute='_compute_revenue_metrics', store=True,
        help="Monthly Recurring Revenue contribution")
    annual_recurring_revenue = fields.Float('ARR', compute='_compute_revenue_metrics', store=True,
        help="Annual Recurring Revenue contribution")
    lifetime_value = fields.Float('Customer Lifetime Value', compute='_compute_revenue_metrics', store=True)
    
    # Payment Terms
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms')
    
    # Tax Configuration
    tax_ids = fields.Many2many('account.tax', string='Taxes',
        help="Taxes applied to this subscription")
    
    # Subscription Modifications
    modification_ids = fields.One2many('ams.subscription.modification', 'subscription_id', 'Modifications')
    has_modifications = fields.Boolean('Has Modifications', compute='_compute_has_modifications')
    
    # Credit Management
    credit_hold = fields.Boolean('Credit Hold', default=False,
        help="Subscription is on credit hold")
    credit_limit = fields.Float('Credit Limit',
        help="Credit limit for this subscription")
    
    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.payment_state')
    def _compute_financial_totals(self):
        for subscription in self:
            invoices = subscription.invoice_ids.filtered(lambda i: i.state == 'posted')
            
            subscription.total_invoiced = sum(invoices.mapped('amount_total'))
            subscription.outstanding_balance = sum(invoices.mapped('amount_residual'))
            subscription.total_paid = subscription.total_invoiced - subscription.outstanding_balance
    
    @api.depends('amount', 'recurring_period', 'is_recurring', 'start_date', 'end_date')
    def _compute_revenue_metrics(self):
        for subscription in self:
            if not subscription.is_recurring:
                subscription.monthly_recurring_revenue = 0.0
                subscription.annual_recurring_revenue = 0.0
                subscription.lifetime_value = subscription.amount
                continue
            
            # Calculate MRR based on recurring period
            if subscription.recurring_period == 'monthly':
                subscription.monthly_recurring_revenue = subscription.amount
                subscription.annual_recurring_revenue = subscription.amount * 12
            elif subscription.recurring_period == 'quarterly':
                subscription.monthly_recurring_revenue = subscription.amount / 3
                subscription.annual_recurring_revenue = subscription.amount * 4
            elif subscription.recurring_period == 'yearly':
                subscription.monthly_recurring_revenue = subscription.amount / 12
                subscription.annual_recurring_revenue = subscription.amount
            else:
                subscription.monthly_recurring_revenue = 0.0
                subscription.annual_recurring_revenue = 0.0
            
            # Calculate lifetime value (simplified)
            if subscription.start_date and subscription.end_date:
                months = (subscription.end_date.year - subscription.start_date.year) * 12 + \
                        (subscription.end_date.month - subscription.start_date.month)
                subscription.lifetime_value = subscription.monthly_recurring_revenue * months
            else:
                # Assume 12 months for active subscriptions without end date
                subscription.lifetime_value = subscription.annual_recurring_revenue
    
    @api.depends('modification_ids')
    def _compute_has_modifications(self):
        for subscription in self:
            subscription.has_modifications = bool(subscription.modification_ids)
    
    def create_deferred_revenue_entries(self):
        """Create deferred revenue entries for subscription"""
        if not self.deferred_revenue_account_id:
            raise UserError(_('Deferred revenue account must be configured for this subscription.'))
        
        if self.revenue_recognition_method != 'deferred':
            return
        
        if not self.start_date or not self.end_date:
            raise UserError(_('Start and end dates are required for deferred revenue calculation.'))
        
        # Calculate monthly revenue recognition
        total_months = (self.end_date.year - self.start_date.year) * 12 + \
                      (self.end_date.month - self.start_date.month) + 1
        
        monthly_amount = self.amount / total_months if total_months > 0 else 0
        
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            raise UserError(_('No general journal found for deferred revenue entries.'))
        
        # Create monthly recognition entries
        current_date = self.start_date.replace(day=1)
        while current_date <= self.end_date:
            move_vals = {
                'journal_id': journal.id,
                'date': current_date,
                'ref': f'Deferred Revenue Recognition - {self.name}',
                'line_ids': [
                    (0, 0, {
                        'name': f'Revenue Recognition - {self.name}',
                        'account_id': self.deferred_revenue_account_id.id,
                        'debit': monthly_amount,
                        'credit': 0.0,
                        'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                    }),
                    (0, 0, {
                        'name': f'Revenue Recognition - {self.name}',
                        'account_id': self.subscription_type_id.revenue_account_id.id if hasattr(self.subscription_type_id, 'revenue_account_id') else self.env.company.income_currency_exchange_account_id.id,
                        'debit': 0.0,
                        'credit': monthly_amount,
                        'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                    })
                ]
            }
            
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            
            current_date = current_date + relativedelta(months=1)
    
    def create_subscription_modification(self, modification_type, amount_change=0.0, description=''):
        """Create a subscription modification record"""
        modification_vals = {
            'subscription_id': self.id,
            'modification_type': modification_type,
            'original_amount': self.amount,
            'new_amount': self.amount + amount_change,
            'amount_change': amount_change,
            'description': description,
            'effective_date': fields.Date.today(),
            'processed': False,
        }
        
        modification = self.env['ams.subscription.modification'].create(modification_vals)
        return modification
    
    def apply_modification(self, modification_id):
        """Apply a subscription modification"""
        modification = self.env['ams.subscription.modification'].browse(modification_id)
        
        if modification.processed:
            raise UserError(_('This modification has already been processed.'))
        
        # Update subscription amount
        self.amount = modification.new_amount
        
        # Create accounting entry for the modification
        if modification.amount_change != 0:
            self._create_modification_accounting_entry(modification)
        
        # Mark modification as processed
        modification.processed = True
        modification.processed_date = fields.Date.today()
        
        return True
    
    def _create_modification_accounting_entry(self, modification):
        """Create accounting entry for subscription modification"""
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not journal:
            return
        
        revenue_account = self.subscription_type_id.revenue_account_id if hasattr(self.subscription_type_id, 'revenue_account_id') else self.env.company.income_currency_exchange_account_id
        
        move_vals = {
            'journal_id': journal.id,
            'date': modification.effective_date,
            'ref': f'Subscription Modification - {self.name}',
            'line_ids': []
        }
        
        if modification.amount_change > 0:
            # Increase in subscription amount
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Subscription Increase - {self.name}',
                    'account_id': self.partner_id.property_account_receivable_id.id,
                    'debit': modification.amount_change,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id,
                    'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                }),
                (0, 0, {
                    'name': f'Subscription Increase - {self.name}',
                    'account_id': revenue_account.id,
                    'debit': 0.0,
                    'credit': modification.amount_change,
                    'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                })
            ]
        else:
            # Decrease in subscription amount (credit note)
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Subscription Decrease - {self.name}',
                    'account_id': revenue_account.id,
                    'debit': abs(modification.amount_change),
                    'credit': 0.0,
                    'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                }),
                (0, 0, {
                    'name': f'Subscription Decrease - {self.name}',
                    'account_id': self.partner_id.property_account_receivable_id.id,
                    'debit': 0.0,
                    'credit': abs(modification.amount_change),
                    'partner_id': self.partner_id.id,
                    'analytic_account_id': self.account_analytic_id.id if self.account_analytic_id else False,
                })
            ]
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
    
    def action_view_financial_analysis(self):
        """View financial analysis for this subscription"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Analysis - {self.name}',
            'res_model': 'ams.subscription.financial.analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
            }
        }
    
    def action_create_credit_note(self):
        """Create credit note for subscription"""
        if not self.invoice_ids:
            raise UserError(_('No invoices found for this subscription.'))
        
        last_invoice = self.invoice_ids.filtered(lambda i: i.state == 'posted').sorted('date', reverse=True)
        if not last_invoice:
            raise UserError(_('No posted invoices found for this subscription.'))
        
        # Create credit note
        credit_note = last_invoice[0]._reverse_moves()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Note',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': credit_note.id,
        }
    
    def action_put_on_credit_hold(self):
        """Put subscription on credit hold"""
        self.credit_hold = True
        self.message_post(body=_("Subscription placed on credit hold."))
    
    def action_remove_credit_hold(self):
        """Remove subscription from credit hold"""
        self.credit_hold = False
        self.message_post(body=_("Subscription removed from credit hold."))
    
    @api.model
    def _cron_process_deferred_revenue(self):
        """Cron job to process deferred revenue recognition"""
        subscriptions = self.search([
            ('revenue_recognition_method', '=', 'deferred'),
            ('state', '=', 'active')
        ])
        
        for subscription in subscriptions:
            try:
                subscription.create_deferred_revenue_entries()
            except Exception as e:
                _logger.error(f"Failed to process deferred revenue for subscription {subscription.name}: {str(e)}")
    
    @api.model
    def get_subscription_revenue_analytics(self, period='current_month'):
        """Get subscription revenue analytics for dashboard"""
        today = fields.Date.today()
        
        if period == 'current_month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'last_month':
            start_date = (today.replace(day=1) - relativedelta(months=1))
            end_date = today.replace(day=1) - relativedelta(days=1)
        elif period == 'current_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = today.replace(day=1)
            end_date = today
        
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('start_date', '<=', end_date),
            '|', ('end_date', '>=', start_date), ('end_date', '=', False)
        ])
        
        total_mrr = sum(subscriptions.mapped('monthly_recurring_revenue'))
        total_arr = sum(subscriptions.mapped('annual_recurring_revenue'))
        total_ltv = sum(subscriptions.mapped('lifetime_value'))
        
        # Revenue by subscription type
        revenue_by_type = {}
        for subscription in subscriptions:
            type_name = subscription.subscription_type_id.name
            if type_name not in revenue_by_type:
                revenue_by_type[type_name] = 0
            revenue_by_type[type_name] += subscription.monthly_recurring_revenue
        
        return {
            'total_mrr': total_mrr,
            'total_arr': total_arr,
            'total_ltv': total_ltv,
            'subscription_count': len(subscriptions),
            'revenue_by_type': revenue_by_type,
            'period': period,
        }


class AMSSubscriptionModification(models.Model):
    """
    Model to track subscription modifications and their accounting impact
    """
    _name = 'ams.subscription.modification'
    _description = 'AMS Subscription Modification'
    _order = 'create_date desc'
    
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='subscription_id.partner_id', store=True)
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('addon', 'Add-on Service'),
        ('discount', 'Discount Applied'),
        ('penalty', 'Penalty/Fee'),
        ('proration', 'Proration Adjustment')
    ], string='Modification Type', required=True)
    
    original_amount = fields.Float('Original Amount', required=True)
    new_amount = fields.Float('New Amount', required=True)
    amount_change = fields.Float('Amount Change', compute='_compute_amount_change', store=True)
    
    effective_date = fields.Date('Effective Date', required=True, default=fields.Date.today)
    description = fields.Text('Description')
    
    processed = fields.Boolean('Processed', default=False)
    processed_date = fields.Date('Processed Date')
    
    # Accounting
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
    
    @api.depends('original_amount', 'new_amount')
    def _compute_amount_change(self):
        for modification in self:
            modification.amount_change = modification.new_amount - modification.original_amount
    
    def action_process_modification(self):
        """Process the modification"""
        self.subscription_id.apply_modification(self.id)
        return True


class AMSSubscriptionFinancialAnalysis(models.TransientModel):
    """
    Wizard for detailed subscription financial analysis
    """
    _name = 'ams.subscription.financial.analysis'
    _description = 'AMS Subscription Financial Analysis'
    
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', required=True)
    
    # Analysis Results
    total_revenue = fields.Float('Total Revenue', compute='_compute_analysis')
    total_costs = fields.Float('Total Costs', compute='_compute_analysis')
    profit_margin = fields.Float('Profit Margin %', compute='_compute_analysis')
    
    payment_performance = fields.Selection([
        ('excellent', 'Excellent (0 days avg)'),
        ('good', 'Good (1-15 days avg)'),
        ('fair', 'Fair (16-30 days avg)'),
        ('poor', 'Poor (30+ days avg)')
    ], string='Payment Performance', compute='_compute_analysis')
    
    @api.depends('subscription_id')
    def _compute_analysis(self):
        for analysis in self:
            subscription = analysis.subscription_id
            
            # Calculate revenue and costs
            analysis.total_revenue = subscription.total_paid
            
            # Simplified cost calculation (could be enhanced)
            analysis.total_costs = subscription.total_revenue * 0.3  # Assume 30% cost ratio
            
            # Profit margin
            if analysis.total_revenue > 0:
                analysis.profit_margin = ((analysis.total_revenue - analysis.total_costs) / analysis.total_revenue) * 100
            else:
                analysis.profit_margin = 0.0
            
            # Payment performance analysis
            invoices = subscription.invoice_ids.filtered(lambda i: i.state == 'posted' and i.payment_state == 'paid')
            if invoices:
                avg_days_to_pay = sum([(inv.payment_date - inv.invoice_date).days for inv in invoices if inv.payment_date]) / len(invoices)
                
                if avg_days_to_pay <= 0:
                    analysis.payment_performance = 'excellent'
                elif avg_days_to_pay <= 15:
                    analysis.payment_performance = 'good'
                elif avg_days_to_pay <= 30:
                    analysis.payment_performance = 'fair'
                else:
                    analysis.payment_performance = 'poor'
            else:
                analysis.payment_performance = 'fair'
