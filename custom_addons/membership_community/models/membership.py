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
    
    # Member Information - Now uses ams.member.type instead of membership.type
    partner_id = fields.Many2one('res.partner', string='Member', required=True, 
                                 tracking=True, domain=[('is_company', '=', False)])
    membership_type_id = fields.Many2one('ams.member.type', string='Membership Type', 
                                         required=True, tracking=True)
    
    # Dates
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today,
                             tracking=True)
    end_date = fields.Date(string='End Date', compute='_compute_end_date', store=True,
                           tracking=True)
    renewal_date = fields.Date(string='Renewal Date', compute='_compute_renewal_date', store=True)
    
    # Get membership period type from AMS settings or member type
    membership_period_type = fields.Selection(
        related='membership_type_id.membership_period_type',
        string='Period Type',
        store=True
    )
    
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
        
        membership = super().create(vals)
        
        # Update partner membership info from ams_foundation
        if membership.partner_id and membership.state == 'active':
            membership._sync_to_partner()
        
        return membership
    
    def write(self, vals):
        result = super().write(vals)
        
        # Sync to partner when state changes to active
        if 'state' in vals and vals['state'] == 'active':
            for membership in self:
                membership._sync_to_partner()
        
        return result
    
    def _sync_to_partner(self):
        """Sync membership data to partner's ams_foundation fields"""
        self.ensure_one()
        if self.partner_id:
            self.partner_id.write({
                'is_member': True,
                'member_type_id': self.membership_type_id.id,
                'member_status': 'active' if self.state == 'active' else 'prospective',
                'membership_start_date': self.start_date,
                'membership_end_date': self.end_date,
            })
    
    @api.depends('membership_type_id', 'start_date')
    def _compute_end_date(self):
        """Calculate end date based on AMS settings and member type configuration"""
        for record in self:
            if not record.membership_type_id or not record.start_date:
                record.end_date = False
                continue
            
            # Get the effective membership period type
            period_type = record.membership_type_id.get_effective_membership_period_type()
            
            if period_type == 'calendar':
                # Calendar year - ends December 31 of the current year
                record.end_date = record.start_date.replace(month=12, day=31)
                
            elif period_type == 'anniversary':
                # Anniversary - based on membership duration
                duration_days = record.membership_type_id.membership_duration or 365
                record.end_date = record.start_date + relativedelta(days=duration_days - 1)
                
            elif period_type == 'rolling':
                # Rolling period - same as anniversary for now
                duration_days = record.membership_type_id.membership_duration or 365
                record.end_date = record.start_date + relativedelta(days=duration_days - 1)
                
            else:
                # Default to anniversary
                duration_days = record.membership_type_id.membership_duration or 365
                record.end_date = record.start_date + relativedelta(days=duration_days - 1)
    
    @api.depends('end_date', 'membership_type_id')
    def _compute_renewal_date(self):
        """Calculate renewal date based on grace period from member type"""
        for record in self:
            if record.end_date and record.membership_type_id:
                # Get grace period from member type (or AMS settings default)
                grace_period_days = record.membership_type_id.get_effective_grace_period()
                record.renewal_date = record.end_date - relativedelta(days=grace_period_days)
            else:
                record.renewal_date = record.end_date
    
    @api.depends('membership_type_id')
    def _compute_amount_total(self):
        """Get amount from AMS member type"""
        for record in self:
            record.amount_total = record.membership_type_id.base_annual_fee or 0.0
    
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
        """Activate membership and sync to partner"""
        self.write({'state': 'active'})
        for membership in self:
            membership._sync_to_partner()
        return True
    
    def action_cancel(self):
        """Cancel membership and update partner status"""
        self.write({'state': 'cancelled'})
        for membership in self:
            if membership.partner_id:
                membership.partner_id.write({'member_status': 'terminated'})
        return True
    
    def action_suspend(self):
        """Suspend membership and update partner status"""
        self.write({'state': 'suspended'})
        for membership in self:
            if membership.partner_id:
                membership.partner_id.write({'member_status': 'suspended'})
        return True
    
    def action_renew(self):
        """Create a new membership for renewal"""
        for record in self:
            # Calculate new start date based on period type
            period_type = record.membership_type_id.get_effective_membership_period_type()
            
            if period_type == 'calendar':
                # For calendar year, next membership starts Jan 1 of next year
                new_start_date = date(record.end_date.year + 1, 1, 1)
            else:
                # For anniversary/rolling, start the day after current end date
                new_start_date = record.end_date + relativedelta(days=1)
            
            renewal_vals = {
                'partner_id': record.partner_id.id,
                'membership_type_id': record.membership_type_id.id,
                'start_date': new_start_date,
                'state': 'draft',
            }
            new_membership = self.create(renewal_vals)
            
            # Update partner's last renewal date
            if record.partner_id:
                record.partner_id.write({
                    'last_renewal_date': fields.Date.today()
                })
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renewed Membership'),
                'res_model': 'membership.membership',
                'res_id': new_membership.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_create_invoice(self):
        """Create invoice for membership using member type product"""
        if not self.partner_id:
            raise UserError(_('Please set a member for this membership.'))
        
        if not self.membership_type_id.default_product_id:
            raise UserError(_('No product configured for this membership type. Please configure a product in the member type settings.'))
        
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'membership_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.membership_type_id.default_product_id.product_variant_id.id,
                'name': f"Membership: {self.membership_type_id.name}",
                'quantity': 1,
                'price_unit': self.membership_type_id.base_annual_fee,
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
        
        for membership in expired_memberships:
            membership.write({'state': 'expired'})
            # Update partner to grace period
            if membership.partner_id:
                membership.partner_id.write({'member_status': 'grace'})
        
        return True
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate membership dates"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('membership_type_id', 'partner_id')
    def _check_membership_type_eligibility(self):
        """Check if partner is eligible for the selected membership type"""
        for record in self:
            if record.membership_type_id and record.partner_id:
                errors = record.membership_type_id.check_eligibility(record.partner_id)
                if errors:
                    raise ValidationError('\n'.join(errors))