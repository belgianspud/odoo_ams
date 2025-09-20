# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Membership-related fields
    membership_ids = fields.Many2many(
        'membership.membership',
        string='Related Memberships',
        help='Memberships related to this invoice'
    )
    
    is_membership_invoice = fields.Boolean(
        string='Membership Invoice',
        compute='_compute_is_membership_invoice',
        store=True,
        help='True if this invoice contains membership-related line items'
    )
    
    membership_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Membership Lines',
        domain=[('is_membership_line', '=', True)],
        help='Invoice lines related to membership fees'
    )
    
    @api.depends('invoice_line_ids.is_membership_line')
    def _compute_is_membership_invoice(self):
        for move in self:
            move.is_membership_invoice = any(
                line.is_membership_line for line in move.invoice_line_ids
            )
    
    def action_post(self):
        """Override to handle membership creation/renewal on invoice posting"""
        result = super().action_post()
        
        # Process membership-related invoices
        if self.is_membership_invoice and self.move_type == 'out_invoice':
            self._process_membership_payment()
        
        return result
    
    def _process_membership_payment(self):
        """Process membership creation or renewal when invoice is posted"""
        for line in self.membership_line_ids:
            if line.membership_type_id:
                # Check if this is a renewal or new membership
                existing_membership = self.env['membership.membership'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('membership_type_id', '=', line.membership_type_id.id),
                    ('state', 'in', ['active', 'grace', 'suspended'])
                ], limit=1)
                
                if existing_membership:
                    # This is a renewal
                    existing_membership.action_renew(amount_paid=line.price_subtotal)
                    self.membership_ids = [(4, existing_membership.id)]
                else:
                    # Create new membership
                    membership_vals = {
                        'partner_id': self.partner_id.id,
                        'membership_type_id': line.membership_type_id.id,
                        'amount_paid': line.price_subtotal,
                        'start_date': fields.Date.today(),
                        'state': 'draft'
                    }
                    
                    new_membership = self.env['membership.membership'].create(membership_vals)
                    new_membership.action_activate()
                    self.membership_ids = [(4, new_membership.id)]
                
                # Link invoice to membership
                line.membership_id = new_membership.id if not existing_membership else existing_membership.id
    
    def action_view_memberships(self):
        """View memberships related to this invoice"""
        self.ensure_one()
        if len(self.membership_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Membership'),
                'res_model': 'membership.membership',
                'res_id': self.membership_ids[0].id,
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Related Memberships'),
                'res_model': 'membership.membership',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.membership_ids.ids)],
                'target': 'current'
            }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # Membership-related fields
    membership_type_id = fields.Many2one(
        'membership.type',
        string='Membership Type',
        help='Membership type if this line is for membership fees'
    )
    
    membership_id = fields.Many2one(
        'membership.membership',
        string='Related Membership',
        help='Membership record created or renewed by this line'
    )
    
    is_membership_line = fields.Boolean(
        string='Membership Line',
        compute='_compute_is_membership_line',
        store=True,
        help='True if this line is related to membership fees'
    )
    
    @api.depends('membership_type_id', 'product_id.membership_type_id')
    def _compute_is_membership_line(self):
        for line in self:
            line.is_membership_line = bool(
                line.membership_type_id or 
                (line.product_id and hasattr(line.product_id, 'membership_type_id') and line.product_id.membership_type_id)
            )
    
    @api.onchange('product_id')
    def _onchange_product_id_membership(self):
        """Auto-populate membership type from product"""
        if self.product_id and hasattr(self.product_id, 'membership_type_id'):
            if self.product_id.membership_type_id:
                self.membership_type_id = self.product_id.membership_type_id.id