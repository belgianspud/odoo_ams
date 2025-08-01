# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSFinancialTransaction(models.Model):
    _name = 'ams.financial.transaction'
    _description = 'AMS Financial Transaction'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Amount', required=True)
    
    # Links
    partner_id = fields.Many2one('res.partner', string='Contact')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item')
    
    # Categorization
    revenue_category_id = fields.Many2one(
        'ams.revenue.category',
        string='Revenue Category',
        required=True
    )
    
    # Transaction Type
    transaction_type = fields.Selection([
        ('membership_new', 'New Membership'),
        ('membership_renewal', 'Membership Renewal'),
        ('chapter_fee', 'Chapter Fee'),
        ('publication_sale', 'Publication Sale'),
        ('event_registration', 'Event Registration'),
        ('donation', 'Donation'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ], string='Transaction Type', required=True)
    
    # Additional Info
    subscription_id = fields.Many2one('ams.subscription', string='Related Subscription')
    notes = fields.Text(string='Notes')
    
    # Computed Fields
    is_revenue = fields.Boolean(
        string='Is Revenue',
        compute='_compute_is_revenue',
        store=True
    )
    
    @api.depends('amount')
    def _compute_is_revenue(self):
        for transaction in self:
            transaction.is_revenue = transaction.amount > 0