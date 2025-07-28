from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class AmsFinancialTransaction(models.Model):
    """Financial transaction tracking for associations"""
    _name = 'ams.financial.transaction'
    _description = 'AMS Financial Transaction'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic transaction information
    name = fields.Char(string='Description', required=True, tracking=True)
    date = fields.Date(
        string='Transaction Date', 
        required=True, 
        default=fields.Date.today,
        tracking=True
    )
    amount = fields.Monetary(
        string='Amount', 
        required=True, 
        currency_field='currency_id',
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        default=lambda self: self.env.company.currency_id
    )
    
    # Transaction categorization
    transaction_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
    ], string='Transaction Type', required=True, tracking=True)
    
    revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='Revenue Category',
        help="Revenue category for income transactions"
    )
    
    # Related records and relationships
    partner_id = fields.Many2one('res.partner', string='Contact')
    invoice_id = fields.Many2one('account.move', string='Related Invoice')
    subscription_id = fields.Many2one('ams.subscription', string='Related Subscription')
    
    # Chapter/regional tracking
    chapter_id = fields.Many2one(
        'res.partner', 
        string='Chapter',
        domain=[('is_company', '=', True)]
    )
    
    # Status and workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Additional information
    notes = fields.Text(string='Notes')
    reference = fields.Char(string='Reference')
    
    # Computed fields
    display_name = fields.Char(compute='_compute_display_name', store=True)
    partner_name = fields.Char(related='partner_id.name', store=True)
    # commented this out due to error: 
    # revenue_category_name = fields.Char(related='revenue_category_id.name', store=True)
    chapter_name = fields.Char(related='chapter_id.name', store=True)
    
    @api.depends('name', 'date', 'amount', 'partner_id.name')
    def _compute_display_name(self):
        """Compute display name for transaction"""
        for transaction in self:
            partner_name = transaction.partner_id.name if transaction.partner_id else 'N/A'
            transaction.display_name = f"{transaction.date} - {transaction.name} - {partner_name} - {transaction.amount}"
    
    @api.constrains('amount')
    def _check_amount(self):
        """Validate transaction amount"""
        for record in self:
            if record.amount == 0:
                raise ValidationError(_("Transaction amount cannot be zero"))
    
    @api.constrains('revenue_category_id', 'transaction_type')
    def _check_revenue_category(self):
        """Validate revenue category is only for income transactions"""
        for record in self:
            if record.revenue_category_id and record.transaction_type != 'income':
                raise ValidationError(_("Revenue category can only be set for income transactions"))
    
    def action_confirm(self):
        """Confirm the transaction"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'confirmed'
            self.message_post(body=_("Transaction confirmed"))
    
    def action_reconcile(self):
        """Mark transaction as reconciled"""
        self.ensure_one()
        if self.state == 'confirmed':
            self.state = 'reconciled'
            self.message_post(body=_("Transaction reconciled"))
    
    def action_cancel(self):
        """Cancel the transaction"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            self.state = 'cancelled'
            self.message_post(body=_("Transaction cancelled"))
    
    def action_reset_to_draft(self):
        """Reset transaction to draft"""
        self.ensure_one()
        if self.state == 'cancelled':
            self.state = 'draft'
            self.message_post(body=_("Transaction reset to draft"))
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add logging and validation"""
        transactions = super().create(vals_list)
        
        for transaction in transactions:
            _logger.info(f"Created financial transaction: {transaction.display_name}")
            
            # Auto-confirm transactions created from invoices
            if transaction.invoice_id and transaction.state == 'draft':
                transaction.action_confirm()
        
        return transactions