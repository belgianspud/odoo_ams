# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    """Enhanced Account Move for AMS integration"""
    _inherit = 'account.move'
    
    # AMS-specific fields
    ams_subscription_id = fields.Many2one(
        'ams.subscription',
        string='Related AMS Subscription',
        help='AMS subscription this invoice relates to'
    )
    
    ams_transaction_type = fields.Selection([
        ('membership_payment', 'Membership Payment'),
        ('publication_payment', 'Publication Payment'), 
        ('chapter_payment', 'Chapter Payment'),
        ('seat_addon', 'Enterprise Seat Add-on'),
        ('modification', 'Subscription Modification'),
        ('refund', 'Subscription Refund'),
    ], string='AMS Transaction Type', help='Type of AMS transaction')
    
    has_ams_products = fields.Boolean(
        string='Has AMS Products',
        compute='_compute_has_ams_products',
        store=True,
        help='This invoice contains AMS subscription products'
    )
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product')
    def _compute_has_ams_products(self):
        """Check if invoice contains AMS products"""
        for move in self:
            move.has_ams_products = any(
                line.product_id.is_subscription_product 
                for line in move.invoice_line_ids
            )
    
    def _post(self, soft=True):
        """Override to handle AMS-specific posting logic"""
        result = super()._post(soft=soft)
        
        # Process AMS-related transactions
        for move in self.filtered(lambda m: m.has_ams_products and m.move_type == 'out_invoice'):
            move._process_ams_transaction()
        
        return result
    
    def _process_ams_transaction(self):
        """Process AMS-specific accounting entries"""
        self.ensure_one()
        
        for line in self.invoice_line_ids:
            if line.product_id.is_subscription_product and line.product_id.use_ams_accounting:
                self._create_ams_journal_entries(line)
    
    def _create_ams_journal_entries(self, invoice_line):
        """Create AMS-specific journal entries"""
        product = invoice_line.product_id.product_tmpl_id
        
        # Get journal entry data from product
        entry_data = product.get_ams_journal_entry_data(
            amount=invoice_line.price_subtotal,
            invoice=self
        )
        
        if not entry_data or not entry_data.get('accounts'):
            return
        
        # For now, this is a hook for future enhancement
        # The actual GL posting is handled by Odoo's standard accounting
        # But we can add AMS-specific logic here
        
        self._log_ams_transaction(invoice_line, entry_data)
    
    def _log_ams_transaction(self, invoice_line, entry_data):
        """Log AMS transaction details"""
        message = f"AMS Transaction processed:\n"
        message += f"Product: {entry_data['product_name']}\n"
        message += f"Type: {entry_data['subscription_type']}\n" 
        message += f"Amount: ${entry_data['amount']:.2f}\n"
        
        accounts_used = []
        for account_type, account_id in entry_data['accounts'].items():
            if account_id:
                account = self.env['account.account'].browse(account_id)
                accounts_used.append(f"{account_type.title()}: {account.name}")
        
        if accounts_used:
            message += f"Accounts: {', '.join(accounts_used)}"
        
        self.message_post(body=message)


class AccountMoveLine(models.Model):
    """Enhanced Account Move Line for AMS tracking"""
    _inherit = 'account.move.line'
    
    # AMS tracking fields
    ams_subscription_id = fields.Many2one(
        'ams.subscription',
        string='AMS Subscription',
        help='AMS subscription this line relates to'
    )
    
    ams_product_type = fields.Selection(
        related='product_id.ams_product_type',
        string='AMS Product Type',
        store=True
    )
    
    is_ams_line = fields.Boolean(
        string='AMS Line',
        compute='_compute_is_ams_line',
        store=True,
        help='This line is from an AMS subscription product'
    )
    
    @api.depends('product_id.is_subscription_product')
    def _compute_is_ams_line(self):
        """Check if this is an AMS-related line"""
        for line in self:
            line.is_ams_line = line.product_id.is_subscription_product if line.product_id else False