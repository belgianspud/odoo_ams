from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Subscription-related fields
    subscription_id = fields.Many2one(
        'ams.subscription',
        'Related Subscription',
        help="Subscription this invoice relates to"
    )
    
    is_renewal_invoice = fields.Boolean(
        'Is Renewal Invoice',
        default=False,
        help="Whether this invoice is for a subscription renewal"
    )
    
    renewal_id = fields.Many2one(
        'ams.subscription.renewal',
        'Related Renewal',
        help="Renewal record this invoice was created for"
    )
    
    subscription_period_start = fields.Date(
        'Subscription Period Start',
        help="Start date of the subscription period this invoice covers"
    )
    
    subscription_period_end = fields.Date(
        'Subscription Period End',
        help="End date of the subscription period this invoice covers"
    )
    
    # Computed fields
    has_subscription_products = fields.Boolean(
        'Has Subscription Products',
        compute='_compute_has_subscription_products',
        store=True,
        help="Whether this invoice contains subscription products"
    )
    
    subscription_count = fields.Integer(
        'Related Subscriptions Count',
        compute='_compute_subscription_count',
        help="Number of subscriptions related to this invoice"
    )
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product')
    def _compute_has_subscription_products(self):
        for move in self:
            move.has_subscription_products = any(
                line.product_id.is_subscription_product 
                for line in move.invoice_line_ids
            )
    
    def _compute_subscription_count(self):
        for move in self:
            # Count direct subscription link plus subscriptions from sale order lines
            count = 0
            if move.subscription_id:
                count += 1
            
            # Count subscriptions from related sale order lines
            if move.invoice_line_ids.mapped('sale_line_ids'):
                sale_lines = move.invoice_line_ids.mapped('sale_line_ids')
                subscription_lines = sale_lines.filtered('subscription_id')
                count += len(subscription_lines.mapped('subscription_id'))
            
            move.subscription_count = count
    
    def action_view_subscriptions(self):
        """Action to view related subscriptions"""
        self.ensure_one()
        
        subscription_ids = []
        
        # Add direct subscription
        if self.subscription_id:
            subscription_ids.append(self.subscription_id.id)
        
        # Add subscriptions from sale order lines
        if self.invoice_line_ids.mapped('sale_line_ids'):
            sale_lines = self.invoice_line_ids.mapped('sale_line_ids')
            subscription_lines = sale_lines.filtered('subscription_id')
            subscription_ids.extend(subscription_lines.mapped('subscription_id.id'))
        
        # Remove duplicates
        subscription_ids = list(set(subscription_ids))
        
        if not subscription_ids:
            raise UserError(_("No subscriptions found for this invoice"))
        
        if len(subscription_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Related Subscription'),
                'res_model': 'ams.subscription',
                'view_mode': 'form',
                'res_id': subscription_ids[0],
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Related Subscriptions'),
                'res_model': 'ams.subscription',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', subscription_ids)],
                'context': {'default_partner_id': self.partner_id.id}
            }
    
    def action_view_renewal(self):
        """Action to view related renewal"""
        self.ensure_one()
        
        if not self.renewal_id:
            raise UserError(_("No renewal record found for this invoice"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Renewal'),
            'res_model': 'ams.subscription.renewal',
            'view_mode': 'form',
            'res_id': self.renewal_id.id,
            'target': 'current',
        }
    
    def _post(self, soft=True):
        """Override to handle subscription-related logic when invoice is posted"""
        result = super()._post(soft=soft)
        
        for move in self:
            if move.move_type == 'out_invoice' and move.has_subscription_products:
                move._handle_subscription_invoice_posted()
        
        return result
    
    def _handle_subscription_invoice_posted(self):
        """Handle subscription logic when invoice is posted"""
        # If this is a renewal invoice, update subscription status
        if self.is_renewal_invoice and self.subscription_id:
            self.subscription_id.write({
                'state': 'pending_renewal',
                'renewal_invoice_id': self.id
            })
            
            # Create status history entry
            self.env['ams.subscription.status.history'].create_status_change(
                self.subscription_id,
                'active',
                'pending_renewal',
                f"Renewal invoice {self.name} posted",
                automatic=True
            )
        
        # Handle initial subscription invoices
        elif self.subscription_id and not self.is_renewal_invoice:
            # Link as original invoice if not already set
            if not self.subscription_id.original_invoice_id:
                self.subscription_id.original_invoice_id = self.id
    
    def payment_action_capture(self):
        """Override to handle subscription activation on payment"""
        result = super().payment_action_capture()
        
        for move in self:
            if move.payment_state == 'paid':
                move._handle_subscription_payment_received()
        
        return result
    
    def _handle_subscription_payment_received(self):
        """Handle subscription logic when payment is received"""
        # For renewal invoices, confirm the renewal
        if self.is_renewal_invoice and self.renewal_id:
            try:
                self.renewal_id.action_confirm_renewal()
                _logger.info(f"Auto-confirmed renewal {self.renewal_id.id} after payment of invoice {self.name}")
            except Exception as e:
                _logger.error(f"Failed to auto-confirm renewal after payment: {str(e)}")
        
        # For initial subscription invoices, activate subscription
        elif self.subscription_id and self.subscription_id.state == 'draft':
            try:
                self.subscription_id.action_activate()
                _logger.info(f"Auto-activated subscription {self.subscription_id.name} after payment of invoice {self.name}")
            except Exception as e:
                _logger.error(f"Failed to auto-activate subscription after payment: {str(e)}")
    
    def button_cancel(self):
        """Override to handle subscription logic when invoice is cancelled"""
        result = super().button_cancel()
        
        for move in self:
            if move.is_renewal_invoice and move.renewal_id:
                # Cancel the renewal
                if move.renewal_id.state == 'pending':
                    move.renewal_id.action_cancel_renewal()
        
        return result
    
    @api.model
    def create_renewal_invoice(self, subscription, renewal_period=None, amount=None):
        """Create a renewal invoice for a subscription"""
        if not subscription.is_recurring:
            raise UserError(_("Cannot create renewal invoice for non-recurring subscription"))
        
        # Calculate period dates
        period_start = subscription.end_date
        if renewal_period == 'monthly':
            period_end = period_start + relativedelta(months=1)
        elif renewal_period == 'quarterly':
            period_end = period_start + relativedelta(months=3)
        elif renewal_period == 'semiannual':
            period_end = period_start + relativedelta(months=6)
        else:  # yearly or default
            period_end = period_start + relativedelta(years=1)
        
        renewal_amount = amount or subscription.amount
        
        # Create invoice
        invoice_vals = {
            'partner_id': subscription.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': subscription.id,
            'is_renewal_invoice': True,
            'subscription_period_start': period_start,
            'subscription_period_end': period_end,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': subscription.product_id.id if subscription.product_id else False,
                'name': f"Renewal: {subscription.name} ({period_start} to {period_end})",
                'quantity': 1,
                'price_unit': renewal_amount,
            })]
        }
        
        invoice = self.create(invoice_vals)
        
        # Update subscription
        subscription.write({
            'renewal_invoice_id': invoice.id,
            'state': 'pending_renewal'
        })
        
        return invoice
    
    @api.model
    def get_subscription_revenue_report(self, date_from=None, date_to=None):
        """Generate subscription revenue report"""
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('has_subscription_products', '=', True)
        ]
        
        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))
        
        invoices = self.search(domain)
        
        # Calculate totals
        total_revenue = sum(invoices.mapped('amount_total'))
        renewal_revenue = sum(invoices.filtered('is_renewal_invoice').mapped('amount_total'))
        new_subscription_revenue = total_revenue - renewal_revenue
        
        # Count invoices
        total_invoices = len(invoices)
        renewal_invoices = len(invoices.filtered('is_renewal_invoice'))
        new_subscription_invoices = total_invoices - renewal_invoices
        
        # Revenue by subscription type
        by_type = {}
        for invoice in invoices:
            if invoice.subscription_id and invoice.subscription_id.subscription_type_id:
                type_name = invoice.subscription_id.subscription_type_id.name
                if type_name not in by_type:
                    by_type[type_name] = {'revenue': 0, 'count': 0}
                by_type[type_name]['revenue'] += invoice.amount_total
                by_type[type_name]['count'] += 1
        
        return {
            'total_revenue': total_revenue,
            'renewal_revenue': renewal_revenue,
            'new_subscription_revenue': new_subscription_revenue,
            'total_invoices': total_invoices,
            'renewal_invoices': renewal_invoices,
            'new_subscription_invoices': new_subscription_invoices,
            'by_subscription_type': by_type,
            'period': {'from': date_from, 'to': date_to}
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    subscription_id = fields.Many2one(
        related='move_id.subscription_id',
        string='Related Subscription',
        store=True,
        readonly=True
    )
    
    is_subscription_line = fields.Boolean(
        'Is Subscription Line',
        compute='_compute_is_subscription_line',
        store=True,
        help="Whether this line is for a subscription product"
    )
    
    @api.depends('product_id.is_subscription_product')
    def _compute_is_subscription_line(self):
        for line in self:
            line.is_subscription_line = line.product_id.is_subscription_product if line.product_id else False