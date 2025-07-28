from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSFinancialTransaction(models.Model):
    _name = 'ams.financial.transaction'
    _description = 'AMS Financial Transaction Tracking'
    _order = 'transaction_date desc, id desc'
    _rec_name = 'display_name'
    
    # Basic Information
    name = fields.Char('Transaction Reference', required=True)
    transaction_date = fields.Date('Transaction Date', required=True, default=fields.Date.today)
    
    # Related Records
    subscription_id = fields.Many2one(
        'ams.subscription',
        'Related Subscription',
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        'Member',
        required=True,
        index=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        'Related Invoice',
        domain="[('move_type', '=', 'out_invoice')]"
    )
    
    # Transaction Details
    transaction_type = fields.Selection([
        ('subscription_payment', 'Subscription Payment'),
        ('renewal_payment', 'Renewal Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('fee', 'Additional Fee'),
        ('discount', 'Discount Applied')
    ], string='Transaction Type', required=True)
    
    amount = fields.Monetary('Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    
    payment_method = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('paypal', 'PayPal'),
        ('other', 'Other')
    ], string='Payment Method')
    
    # Financial Details
    gross_amount = fields.Monetary('Gross Amount', currency_field='currency_id')
    fees_amount = fields.Monetary('Processing Fees', currency_field='currency_id')
    net_amount = fields.Monetary('Net Amount', currency_field='currency_id')
    
    # Processing Information
    processor_reference = fields.Char('Processor Reference')
    processor_fee = fields.Monetary('Processor Fee', currency_field='currency_id')
    
    # Dates
    processed_date = fields.Datetime('Processed Date')
    reconciled_date = fields.Date('Reconciled Date')
    
    # Computed Fields
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Related Fields for easier reporting
    subscription_type_id = fields.Many2one(
        related='subscription_id.subscription_type_id',
        string='Subscription Type',
        store=True,
        readonly=True
    )
    
    chapter_id = fields.Many2one(
        related='subscription_id.chapter_id',
        string='Chapter',
        store=True,
        readonly=True
    )
    
    # Description and Notes
    description = fields.Text('Description')
    notes = fields.Text('Internal Notes')
    
    @api.depends('name', 'partner_id', 'amount', 'transaction_type')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.amount:
                record.display_name = f"{record.name} - {record.partner_id.name} ({record.amount})"
            else:
                record.display_name = record.name or 'Financial Transaction'
    
    @api.onchange('gross_amount', 'fees_amount')
    def _onchange_amounts(self):
        """Auto-calculate net amount"""
        if self.gross_amount and self.fees_amount:
            self.net_amount = self.gross_amount - self.fees_amount
            self.amount = self.net_amount
    
    @api.model
    def create_from_subscription_payment(self, subscription, invoice, amount, payment_method='credit_card'):
        """Create a financial transaction from a subscription payment"""
        vals = {
            'name': f"SUB-{subscription.id}-{fields.Date.today()}",
            'subscription_id': subscription.id,
            'partner_id': subscription.partner_id.id,
            'invoice_id': invoice.id if invoice else False,
            'transaction_type': 'renewal_payment' if invoice and invoice.is_renewal_invoice else 'subscription_payment',
            'amount': amount,
            'gross_amount': amount,
            'net_amount': amount,
            'payment_method': payment_method,
            'state': 'completed',
            'processed_date': fields.Datetime.now(),
            'description': f"Payment for {subscription.name}"
        }
        
        return self.create(vals)
    
    def action_mark_completed(self):
        """Mark transaction as completed"""
        self.ensure_one()
        if self.state in ('draft', 'pending'):
            self.write({
                'state': 'completed',
                'processed_date': fields.Datetime.now()
            })
            self.message_post(body="Transaction marked as completed")
    
    def action_mark_failed(self):
        """Mark transaction as failed"""
        self.ensure_one()
        if self.state in ('draft', 'pending'):
            self.write({'state': 'failed'})
            self.message_post(body="Transaction marked as failed")
    
    def action_reconcile(self):
        """Mark transaction as reconciled"""
        self.ensure_one()
        if self.state == 'completed':
            self.reconciled_date = fields.Date.today()
            self.message_post(body="Transaction reconciled")
    
    @api.model
    def get_revenue_summary(self, date_from=None, date_to=None, subscription_type_id=None):
        """Get revenue summary for reporting"""
        domain = [
            ('state', '=', 'completed'),
            ('transaction_type', 'in', ['subscription_payment', 'renewal_payment'])
        ]
        
        if date_from:
            domain.append(('transaction_date', '>=', date_from))
        if date_to:
            domain.append(('transaction_date', '<=', date_to))
        if subscription_type_id:
            domain.append(('subscription_type_id', '=', subscription_type_id))
        
        transactions = self.search(domain)
        
        total_revenue = sum(transactions.mapped('amount'))
        total_fees = sum(transactions.mapped('fees_amount'))
        net_revenue = sum(transactions.mapped('net_amount'))
        
        # Revenue by type
        subscription_revenue = sum(
            transactions.filtered(lambda t: t.transaction_type == 'subscription_payment').mapped('amount')
        )
        renewal_revenue = sum(
            transactions.filtered(lambda t: t.transaction_type == 'renewal_payment').mapped('amount')
        )
        
        # Revenue by payment method
        by_payment_method = {}
        for method in transactions.mapped('payment_method'):
            if method:
                method_transactions = transactions.filtered(lambda t: t.payment_method == method)
                by_payment_method[method] = sum(method_transactions.mapped('amount'))
        
        return {
            'total_revenue': total_revenue,
            'total_fees': total_fees,
            'net_revenue': net_revenue,
            'subscription_revenue': subscription_revenue,
            'renewal_revenue': renewal_revenue,
            'by_payment_method': by_payment_method,
            'transaction_count': len(transactions),
            'period': {'from': date_from, 'to': date_to}
        }
    
    # View actions
    def action_view_subscription(self):
        """View related subscription"""
        self.ensure_one()
        if not self.subscription_id:
            raise UserError(_("No subscription linked to this transaction"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Subscription'),
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
        }
    
    def action_view_invoice(self):
        """View related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice linked to this transaction"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }
    
    # Constraints
    @api.constrains('amount', 'gross_amount', 'net_amount')
    def _check_amounts(self):
        for record in self:
            if record.amount and record.amount == 0:
                raise ValidationError(_("Transaction amount cannot be zero"))
            if record.gross_amount and record.net_amount and record.gross_amount < record.net_amount:
                raise ValidationError(_("Gross amount cannot be less than net amount"))
    
    @api.constrains('transaction_date')
    def _check_transaction_date(self):
        for record in self:
            if record.transaction_date > fields.Date.today():
                raise ValidationError(_("Transaction date cannot be in the future"))