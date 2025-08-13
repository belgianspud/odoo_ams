# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Basic AMS member fields
    is_ams_member = fields.Boolean(
        string='Is AMS Member',
        default=False,
        help='Check if this contact is an association member'
    )
    
    ams_member_id = fields.Char(
        string='Member ID',
        help='Unique member identification number'
    )
    
    ams_member_type = fields.Selection([
        ('individual', 'Individual Member'),
        ('enterprise', 'Corporate Member'),
        ('student', 'Student Member'),
        ('honorary', 'Honorary Member'),
    ], string='Member Type', help='Type of association membership')
    
    # Financial summary fields
    total_outstanding_amount = fields.Monetary(
        string='Outstanding Balance',
        compute='_compute_financial_summary',
        help='Total amount this member currently owes'
    )
    
    total_paid_amount = fields.Monetary(
        string='Total Paid This Year',
        compute='_compute_financial_summary',
        help='Total amount paid by this member in the current year'
    )
    
    lifetime_member_value = fields.Monetary(
        string='Lifetime Member Value',
        compute='_compute_financial_summary',
        help='Total amount this member has paid since joining'
    )
    
    last_payment_date = fields.Date(
        string='Last Payment Date',
        compute='_compute_financial_summary',
        help='Date of most recent payment received'
    )
    
    # Payment preferences
    preferred_payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
    ], string='Preferred Payment Method')
    
    auto_payment_enabled = fields.Boolean(
        string='Auto-Payment Enabled',
        default=False,
        help='Whether member has automatic payment set up'
    )
    
    # Billing contact information
    billing_contact_name = fields.Char(string='Billing Contact')
    billing_email = fields.Char(string='Billing Email')
    billing_phone = fields.Char(string='Billing Phone')
    
    # Computed fields for member status
    membership_start_date = fields.Date(
        string='Member Since',
        help='Date this member first joined the association'
    )
    
    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.amount_total')
    def _compute_financial_summary(self):
        """Compute financial summary fields"""
        for partner in self:
            if not partner.is_ams_member:
                partner.total_outstanding_amount = 0
                partner.total_paid_amount = 0
                partner.lifetime_member_value = 0
                partner.last_payment_date = False
                continue
            
            # Get member invoices
            member_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )
            
            # Outstanding amount
            partner.total_outstanding_amount = sum(
                member_invoices.filtered(
                    lambda inv: inv.payment_state in ['not_paid', 'partial']
                ).mapped('amount_residual')
            )
            
            # Current year payments
            current_year = fields.Date.today().year
            current_year_invoices = member_invoices.filtered(
                lambda inv: inv.invoice_date and inv.invoice_date.year == current_year
            )
            partner.total_paid_amount = sum(
                current_year_invoices.filtered(
                    lambda inv: inv.payment_state == 'paid'
                ).mapped('amount_total')
            )
            
            # Lifetime value (all paid invoices)
            paid_invoices = member_invoices.filtered(lambda inv: inv.payment_state == 'paid')
            partner.lifetime_member_value = sum(paid_invoices.mapped('amount_total'))
            
            # Last payment date
            if paid_invoices:
                partner.last_payment_date = max(paid_invoices.mapped('invoice_date'))
            else:
                partner.last_payment_date = False
    
    def action_view_member_invoices(self):
        """View all invoices for this member"""
        self.ensure_one()
        return {
            'name': f'Invoices for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'context': {'default_partner_id': self.id, 'default_move_type': 'out_invoice'},
        }
    
    def action_view_member_payments(self):
        """View all payments from this member"""
        self.ensure_one()
        return {
            'name': f'Payments from {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('partner_type', '=', 'customer')],
            'context': {'default_partner_id': self.id, 'default_partner_type': 'customer'},
        }
    
    def action_create_payment_reminder(self):
        """Send payment reminder to this member"""
        self.ensure_one()
        # This would integrate with email templates
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Payment reminder feature will be implemented for {self.name}',
                'type': 'info',
            }
        }