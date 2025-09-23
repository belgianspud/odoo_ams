# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Subscription-related fields
    has_subscription_lines = fields.Boolean(
        string='Has Subscription Lines',
        compute='_compute_has_subscription_lines',
        store=True,
        help='This invoice contains subscription product lines'
    )
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product')
    def _compute_has_subscription_lines(self):
        """Check if invoice contains subscription product lines"""
        for move in self:
            subscription_lines = move.invoice_line_ids.filtered(
                lambda line: line.product_id and line.product_id.is_subscription_product
            )
            move.has_subscription_lines = bool(subscription_lines)
    
    def _post(self, soft=True):
        """Override _post to handle subscription activation when invoice is posted"""
        result = super()._post(soft)
        
        # Process subscription activations for customer invoices that are posted
        for move in self:
            if (move.move_type == 'out_invoice' and 
                move.state == 'posted' and 
                move.has_subscription_lines):
                move._process_subscription_activations()
        
        return result
    
    def _process_subscription_activations(self):
        """Process subscription/membership activations when invoice is posted and paid"""
        self.ensure_one()
        
        # Only process if invoice is paid or in payment
        if self.payment_state not in ['paid', 'in_payment']:
            return
        
        for line in self.invoice_line_ids:
            if not line.product_id or not line.product_id.is_subscription_product:
                continue
            
            try:
                if line.product_id.subscription_product_type == 'membership':
                    self._activate_membership_from_line(line)
                else:
                    self._activate_subscription_from_line(line)
                    
            except Exception as e:
                _logger.error(f"Failed to activate subscription from invoice line {line.id}: {str(e)}")
                continue
    
    def _activate_membership_from_line(self, line):
        """Activate membership from paid invoice line"""
        # First, try to find existing membership from sale order line
        membership = self.env['ams.membership'].search([
            ('sale_order_line_id.product_id', '=', line.product_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'active'])
        ], limit=1)
        
        if membership:
            # Update existing membership with invoice information
            membership.write({
                'invoice_id': self.id,
                'invoice_line_id': line.id,
                'payment_status': 'paid',
                'state': 'active',
                'last_renewal_date': fields.Date.today(),
            })
            _logger.info(f"Activated existing membership {membership.name}")
        else:
            # Create new membership from invoice payment
            membership = self.env['ams.membership'].create_from_invoice_payment(line)
            if membership:
                _logger.info(f"Created and activated membership {membership.name} from invoice payment")
        
        return membership
    
    def _activate_subscription_from_line(self, line):
        """Activate subscription from paid invoice line"""
        # First, try to find existing subscription from sale order line
        subscription = self.env['ams.subscription'].search([
            ('sale_order_line_id.product_id', '=', line.product_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'active'])
        ], limit=1)
        
        if subscription:
            # Update existing subscription with invoice information
            subscription.write({
                'invoice_id': self.id,
                'invoice_line_id': line.id,
                'payment_status': 'paid',
                'state': 'active',
                'last_renewal_date': fields.Date.today(),
            })
            _logger.info(f"Activated existing subscription {subscription.name}")
        else:
            # Create new subscription from invoice payment
            subscription = self.env['ams.subscription'].create_from_invoice_payment(line)
            if subscription:
                _logger.info(f"Created and activated subscription {subscription.name} from invoice payment")
        
        return subscription


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_post(self):
        """Override action_post to trigger subscription processing when payment is posted"""
        result = super().action_post()
        
        # Process subscription activations for customer payments
        for payment in self:
            if payment.payment_type == 'inbound' and payment.state == 'posted':
                payment._process_subscription_payments()
        
        return result
    
    def _process_subscription_payments(self):
        """Process subscription activations from payments"""
        self.ensure_one()
        
        # Get reconciled invoices
        reconciled_moves = self._get_reconciled_invoices()
        
        for invoice in reconciled_moves:
            if invoice.has_subscription_lines and invoice.payment_state in ['paid', 'in_payment']:
                invoice._process_subscription_activations()
    
    def _get_reconciled_invoices(self):
        """Get invoices reconciled with this payment"""
        reconciled_invoices = self.env['account.move']
        
        # Get reconciled move lines
        reconciled_lines = self.line_ids.mapped('matched_debit_ids.debit_move_id') | \
                          self.line_ids.mapped('matched_credit_ids.credit_move_id')
        
        # Filter for customer invoices
        for line in reconciled_lines:
            if (line.move_id.move_type == 'out_invoice' and 
                line.move_id not in reconciled_invoices):
                reconciled_invoices |= line.move_id
        
        return reconciled_invoices


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    is_subscription_line = fields.Boolean(
        string='Subscription Line',
        compute='_compute_is_subscription_line',
        store=True,
        help='This invoice line is for a subscription product'
    )
    
    related_membership_id = fields.Many2one(
        'ams.membership',
        string='Related Membership',
        compute='_compute_related_records',
        store=True
    )
    
    related_subscription_id = fields.Many2one(
        'ams.subscription', 
        string='Related Subscription',
        compute='_compute_related_records',
        store=True
    )
    
    @api.depends('product_id.is_subscription_product')
    def _compute_is_subscription_line(self):
        """Check if this line is for a subscription product"""
        for line in self:
            line.is_subscription_line = bool(
                line.product_id and line.product_id.is_subscription_product
            )
    
    @api.depends('move_id', 'product_id')
    def _compute_related_records(self):
        """Find related membership/subscription records"""
        for line in self:
            line.related_membership_id = False
            line.related_subscription_id = False
            
            if not line.is_subscription_line:
                continue
            
            # Look for related membership
            membership = self.env['ams.membership'].search([
                ('invoice_line_id', '=', line.id)
            ], limit=1)
            if membership:
                line.related_membership_id = membership.id
                continue
            
            # Look for related subscription
            subscription = self.env['ams.subscription'].search([
                ('invoice_line_id', '=', line.id)
            ], limit=1)
            if subscription:
                line.related_subscription_id = subscription.id