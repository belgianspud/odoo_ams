from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

class PartnerAmsExtension(models.Model):
    """Extend res.partner with AMS financial fields"""
    _inherit = 'res.partner'
    
    # Financial summary fields
    total_membership_paid = fields.Monetary(
        string='Total Membership Paid',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    total_event_paid = fields.Monetary(
        string='Total Event Fees Paid',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    outstanding_balance = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_financial_summary',
        currency_field='currency_id'
    )
    last_payment_date = fields.Date(
        string='Last Payment Date',
        compute='_compute_financial_summary'
    )
    
    # Chapter financial tracking (for chapter partners)
    is_chapter = fields.Boolean(string='Is Chapter', default=False)
    chapter_revenue_ytd = fields.Monetary(
        string='Chapter Revenue YTD',
        compute='_compute_chapter_financials',
        currency_field='currency_id'
    )
    
    @api.depends('invoice_ids.payment_state', 'invoice_ids.amount_total')
    def _compute_financial_summary(self):
        for partner in self:
            # Calculate totals from invoices
            invoices = partner.invoice_ids.filtered(lambda i: i.state == 'posted')
            
            membership_total = sum(
                line.credit for invoice in invoices 
                for line in invoice.line_ids 
                if line.product_id.is_membership
            )
            
            event_total = sum(
                line.credit for invoice in invoices 
                for line in invoice.line_ids 
                if hasattr(line, 'event_id') and line.event_id
            )
            
            partner.total_membership_paid = membership_total
            partner.total_event_paid = event_total
            #partner.outstanding_balance = partner.total_due or 0.0
            
            # Last payment date
            payments = invoices.mapped('payment_id').filtered(lambda p: p.state == 'posted')
            partner.last_payment_date = max(payments.mapped('date')) if payments else False
    
    @api.depends('is_chapter')
    def _compute_chapter_financials(self):
        for partner in self:
            if partner.is_chapter:
                # Calculate chapter revenue for current year
                current_year = fields.Date.today().year
                chapter_invoices = self.env['account.move'].search([
                    ('partner_id', 'child_of', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('invoice_date', '>=', f'{current_year}-01-01'),
                    ('invoice_date', '<=', f'{current_year}-12-31'),
                ])
                partner.chapter_revenue_ytd = sum(chapter_invoices.mapped('amount_total'))
            else:
                partner.chapter_revenue_ytd = 0.0
