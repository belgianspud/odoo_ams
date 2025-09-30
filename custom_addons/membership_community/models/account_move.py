# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    membership_id = fields.Many2one('membership.membership', string='Related Membership')
    
    def _post(self, soft=True):
        """Override to update membership when invoice is posted"""
        posted = super()._post(soft=soft)
        
        for move in posted:
            if move.membership_id and move.move_type == 'out_invoice':
                # Update membership when invoice is confirmed
                move.membership_id._check_invoice_payment()
        
        return posted
    
    def button_draft(self):
        """Override to handle membership when invoice is reset to draft"""
        res = super().button_draft()
        
        for move in self:
            if move.membership_id:
                move.membership_id._check_invoice_payment()
        
        return res
    
    def button_cancel(self):
        """Override to handle membership when invoice is cancelled"""
        res = super().button_cancel()
        
        for move in self:
            if move.membership_id:
                move.membership_id._check_invoice_payment()
        
        return res
    
    def _write(self, vals):
        """Override to detect payment state changes"""
        res = super()._write(vals)
        
        # Check if payment_state changed
        if 'payment_state' in vals:
            for move in self:
                if move.membership_id and move.move_type == 'out_invoice':
                    move.membership_id._check_invoice_payment()
        
        return res