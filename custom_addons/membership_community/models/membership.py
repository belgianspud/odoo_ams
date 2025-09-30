# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class Membership(models.Model):
    _name = 'membership.membership'
    _description = 'Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Membership Number', required=True, copy=False, 
                       readonly=True, default=lambda self: _('New'))
    
    # Member Information
    partner_id = fields.Many2one('res.partner', string='Member', required=True, 
                                 tracking=True, domain=[('is_company', '=', False)])
    membership_type_id = fields.Many2one('membership.type', string='Membership Type', 
                                         required=True, tracking=True)
    
    # Dates
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today,
                             tracking=True)
    end_date = fields.Date(string='End Date', compute='_compute_end_date', store=True,
                           tracking=True)
    renewal_date = fields.Date(string='Renewal Date', compute='_compute_renewal_date', store=True)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ], string='Status', default='draft', tracking=True)
    
    # Payment
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overpaid', 'Overpaid'),
    ], string='Payment Status', compute='_compute_payment_state', store=True)
    
    amount_total = fields.Monetary(string='Total Amount', compute='_compute_amount_total', store=True)
    amount_paid = fields.Monetary(string='Paid Amount', compute='_compute_amount_paid', store=True)
    amount_due = fields.Monetary(string='Due Amount', compute='_compute_amount_due', store=True)
    
    currency_id = fields.Many2one('res.currency', related='membership_type_id.currency_id', store=True)
    
    # Relations
    payment_ids = fields.One2many('membership.payment', 'membership_id', string='Payments')
    invoice_ids = fields.One2many('account.move', 'membership_id', string='Invoices')
    
    # Additional Info
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', 
                                 default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('membership.membership') or _('New')
        return super().create(vals)
    
    @api.depends('membership_type_id', 'start_date')
    def _compute_end_date(self):
        for record in self:
            if record.membership_type_id and record.start_date:
                if record.membership_type_id.duration_type == 'unlimited':
                    record.end_date = False
                elif record.membership_type_id.duration_type == 'yearly':
                    record.end_date = record.start_date + relativedelta(years=1) - relativedelta(days=1)
                elif record.membership_type_id.duration_type == 'monthly':
                    record.end_date = record.start_date + relativedelta(months=1) - relativedelta(days=1)
                elif record.membership_type_id.duration_type == 'fixed':
                    months = record.membership_type_id.duration_months or 12
                    record.end_date = record.start_date + relativedelta(months=months) - relativedelta(days=1)
                else:
                    record.end_date = False
            else:
                record.end_date = False
    
    @api.depends('end_date', 'membership_type_id')
    def _compute_renewal_date(self):
        for record in self:
            if record.end_date and record.membership_type_id.grace_period_days:
                record.renewal_date = record.end_date - relativedelta(
                    days=record.membership_type_id.grace_period_days)
            else:
                record.renewal_date = record.end_date
    
    @api.depends('membership_type_id')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = record.membership_type_id.price or 0.0
    
    @api.depends('payment_ids.amount', 'payment_ids.state')
    def _compute_amount_paid(self):
        for record in self:
            paid_payments = record.payment_ids.filtered(lambda p: p.state == 'confirmed')
            record.amount_paid = sum(paid_payments.mapped('amount'))
    
    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_due(self):
        for record in self:
            record.amount_due = record.amount_total - record.amount_paid
    
    @api.depends('amount_total', 'amount_paid')
    def _compute_payment_state(self):
        for record in self:
            if record.amount_paid == 0:
                record.payment_state = 'not_paid'
            elif record.amount_paid < record.amount_total:
                record.payment_state = 'partial'
            elif record.amount_paid == record.amount_total:
                record.payment_state = 'paid'
            else:
                record.payment_state = 'overpaid'
    
    def action_activate(self):
        self.write({'state': 'active'})
        return True
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True
    
    def action_suspend(self):
        self.write({'state': 'suspended'})
        return True
    
    def action_renew(self):
        """Create a new membership for renewal"""
        for record in self:
            new_start_date = record.end_date + relativedelta(days=1) if record.end_date else fields.Date.today()
            renewal_vals = {
                'partner_id': record.partner_id.id,
                'membership_type_id': record.membership_type_id.id,
                'start_date': new_start_date,
                'state': 'draft',
            }
            new_membership = self.create(renewal_vals)
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renewed Membership'),
                'res_model': 'membership.membership',
                'res_id': new_membership.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_create_invoice(self):
        """Create invoice for membership"""
        if not self.partner_id:
            raise UserError(_('Please set a member for this membership.'))
        
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'membership_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.membership_type_id.product_id.id,
                'name': f"Membership: {self.membership_type_id.name}",
                'quantity': 1,
                'price_unit': self.membership_type_id.price,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def _cron_update_membership_states(self):
        """Cron job to update membership states based on dates"""
        today = fields.Date.today()
        
        # Expire memberships
        expired_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('end_date', '!=', False),
        ])
        expired_memberships.write({'state': 'expired'})
        
        return True