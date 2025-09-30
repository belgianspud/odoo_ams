# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MembershipInvoiceWizard(models.TransientModel):
    _name = 'membership.invoice.wizard'
    _description = 'Create Membership Invoices'
    
    membership_ids = fields.Many2many('membership.membership', string='Memberships')
    journal_id = fields.Many2one('account.journal', string='Journal', 
                                 domain=[('type', '=', 'sale')])
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.today)
    
    def action_create_invoices(self):
        invoices = self.env['account.move']
        errors = []
        
        for membership in self.membership_ids:
            if not membership.partner_id:
                errors.append(_('Membership %s has no partner assigned') % membership.name)
                continue
            
            if not membership.membership_type_id.default_product_id:
                errors.append(_('Membership type %s has no product configured') % membership.membership_type_id.name)
                continue
                
            invoice_vals = {
                'partner_id': membership.partner_id.id,
                'move_type': 'out_invoice',
                'membership_id': membership.id,
                'invoice_date': self.invoice_date,
                'journal_id': self.journal_id.id if self.journal_id else False,
                'invoice_line_ids': [(0, 0, {
                    'product_id': membership.membership_type_id.default_product_id.product_variant_id.id,
                    'name': f"Membership: {membership.membership_type_id.name} ({membership.membership_period_type})",
                    'quantity': 1,
                    'price_unit': membership.membership_type_id.base_annual_fee,
                })],
            }
            
            try:
                invoice = self.env['account.move'].create(invoice_vals)
                invoices |= invoice
            except Exception as e:
                errors.append(_('Error creating invoice for %s: %s') % (membership.name, str(e)))
        
        if errors:
            error_msg = '\n'.join(errors)
            if not invoices:
                raise UserError(_('No invoices were created.\n\n%s') % error_msg)
            else:
                # Some invoices were created, show warning
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Partial Success'),
                        'message': _('%d invoices created, but some errors occurred:\n%s') % (len(invoices), error_msg),
                        'type': 'warning',
                        'sticky': True,
                        'next': {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.move',
                            'view_mode': 'list,form',
                            'domain': [('id', 'in', invoices.ids)],
                        }
                    }
                }
        
        if invoices:
            return {
                'name': _('Created Invoices'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', invoices.ids)],
                'target': 'current',
            }
        else:
            raise UserError(_('No invoices were created.'))