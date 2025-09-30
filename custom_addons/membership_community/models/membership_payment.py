# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MembershipPayment(models.Model):
    _name = 'membership.payment'
    _description = 'Membership Payment'
    _inherit = ['mail.thread']
    _order = 'payment_date desc, id desc'
    
    name = fields.Char(string='Reference', required=True)
    membership_id = fields.Many2one('membership.membership', string='Membership', required=True)
    partner_id = fields.Many2one(related='membership_id.partner_id', string='Member', store=True)
    
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    payment_date = fields.Date(string='Payment Date', default=fields.Date.today, required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('check', 'Check'),
        ('online', 'Online Payment'),
        ('other', 'Other'),
    ], string='Payment Method', default='cash')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True