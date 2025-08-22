# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    _name = 'ams.subscription'  # ✅ CREATES the base model
    _description = 'AMS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # For chatter and tracking

    name = fields.Char(string='Subscription Name', required=True, tracking=True)
    
    # Link to Customer / Account
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    account_id = fields.Many2one('res.partner', string='Account', help='Used for enterprise memberships')

    # Product and Sale Info
    product_id = fields.Many2one('product.product', string='Product', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')

    # Subscription Type and Tier
    subscription_type = fields.Selection([
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('seat', 'Enterprise Seat Add-On'),
    ], string='Subscription Type', required=True)

    tier_id = fields.Many2one('ams.subscription.tier', string='Tier / Level')

    # Enhanced state management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('grace', 'Grace'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    paid_through_date = fields.Date(string='Paid Through Date')
    
    # Add field to track invoice payment status
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='Invoice Payment Status',
        store=True
    )
    
    # Add computed field for membership year
    membership_year = fields.Char(
        string='Membership Year',
        compute='_compute_membership_year',
        store=True,
        help='The calendar year this membership covers'
    )

    # Enterprise Seat Management
    base_seats = fields.Integer(string='Base Seats', default=0)
    extra_seats = fields.Integer(string='Extra Seats', default=0)
    total_seats = fields.Integer(string='Total Seats', compute='_compute_total_seats', store=True)

    # Enhanced flags
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    is_free = fields.Boolean(string='Free Subscription', default=False)
    
    # Modification tracking
    allow_modifications = fields.Boolean(
        string='Allow Modifications',
        default=True,
        help='Allow customer to upgrade/downgrade this subscription'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Pausing',
        default=True,
        help='Allow customer to pause this subscription'
    )

    @api.depends('paid_through_date')
    def _compute_membership_year(self):
        for sub in self:
            if sub.paid_through_date:
                sub.membership_year = str(sub.paid_through_date.year)
            else:
                sub.membership_year = str(date.today().year)

    @api.depends('base_seats', 'extra_seats')
    def _compute_total_seats(self):
        for sub in self:
            sub.total_seats = (sub.base_seats or 0) + (sub.extra_seats or 0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-populate fields when product is selected"""
        if self.product_id:
            product_tmpl = self.product_id.product_tmpl_id
            if hasattr(product_tmpl, 'ams_product_type'):
                self.subscription_type = product_tmpl.ams_product_type
            if hasattr(product_tmpl, 'subscription_tier_id'):
                self.tier_id = product_tmpl.subscription_tier_id.id

    def _calculate_calendar_year_end(self, payment_date):
        """Calculate end date as December 31st of the payment year"""
        return date(payment_date.year, 12, 31)

    def action_activate(self):
        for sub in self:
            sub.state = 'active'
            if not sub.paid_through_date:
                # Default to end of current year
                sub.paid_through_date = self._calculate_calendar_year_end(fields.Date.today())

    def action_set_grace(self):
        self.write({'state': 'grace'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_terminate(self):
        self.write({'state': 'terminated'})

    # Enhanced payment integration methods
    @api.model
    def create_from_invoice_payment(self, invoice_line, payment_date=None):
        """Enhanced subscription creation from invoice payment"""
        if not payment_date:
            payment_date = fields.Date.today()
            
        product = invoice_line.product_id.product_tmpl_id
        
        # Only create subscriptions for AMS products
        if not hasattr(product, 'is_subscription_product') or not product.is_subscription_product:
            return False
            
        # Check if subscription already exists for this invoice line
        existing_sub = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing_sub:
            # Update existing subscription with payment details
            existing_sub._process_payment_received(payment_date)
            return existing_sub
        
        # Create new subscription
        partner = invoice_line.move_id.partner_id
        
        subscription_vals = {
            'name': f"{partner.name} - {product.name} ({payment_date.year})",
            'partner_id': partner.id,
            'account_id': partner.parent_id.id if partner.parent_id else partner.id,
            'product_id': invoice_line.product_id.id,
            'subscription_type': getattr(product, 'ams_product_type', 'individual'),
            'tier_id': product.subscription_tier_id.id if hasattr(product, 'subscription_tier_id') and product.subscription_tier_id else False,
            'start_date': payment_date,
            'paid_through_date': self._calculate_calendar_year_end(payment_date),
            'state': 'active',
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'base_seats': 0,
            'auto_renew': True,
            'is_free': False,
            'allow_modifications': True,
            'allow_pausing': True,
        }
        
        subscription = self.create(subscription_vals)
        
        subscription.message_post(
            body=f"Subscription activated from invoice payment: {invoice_line.move_id.name}. "
                 f"Paid through: {subscription.paid_through_date}"
        )
        
        _logger.info(f"Created subscription {subscription.id} for partner {partner.name}")
        
        return subscription

    def _process_payment_received(self, payment_date):
        """Process payment for existing subscription"""
        self.ensure_one()
        
        # Update subscription dates and status
        if self.state != 'active':
            self.state = 'active'
        
        # Update paid through date to end of calendar year
        new_paid_through = self._calculate_calendar_year_end(payment_date)
        if not self.paid_through_date or new_paid_through > self.paid_through_date:
            self.paid_through_date = new_paid_through
        
        # Update start date if this is the first payment
        if not self.start_date or self.state == 'draft':
            self.start_date = payment_date
        
        self.message_post(body=f"Payment received on {payment_date}. Subscription extended through {self.paid_through_date}")


# Enhanced Account Payment for subscription creation
class AccountPayment(models.Model):
    """Enhanced payment model for subscription creation"""
    _inherit = 'account.payment'

    def action_post(self):
        """Override to trigger subscription creation when payment is posted"""
        result = super().action_post()
        
        for payment in self:
            if payment.state == 'posted' and payment.partner_type == 'customer':
                payment._process_ams_subscriptions()
        
        return result

    def _process_ams_subscriptions(self):
        """Process AMS subscriptions for this payment"""
        self.ensure_one()
        
        # Get reconciled invoice lines
        reconciled_lines = self.line_ids.mapped('matched_debit_ids.debit_move_id') | \
                          self.line_ids.mapped('matched_credit_ids.credit_move_id')
        
        invoices = reconciled_lines.mapped('move_id').filtered(
            lambda m: m.move_type == 'out_invoice' and m.payment_state in ['paid', 'in_payment']
        )
        
        payment_date = self.date
        
        for invoice in invoices:
            self._create_subscriptions_for_invoice(invoice, payment_date)

    def _create_subscriptions_for_invoice(self, invoice, payment_date):
        """Create subscriptions for AMS products in this invoice"""
        for line in invoice.invoice_line_ids:
            product = line.product_id.product_tmpl_id
            if hasattr(product, 'is_subscription_product') and product.is_subscription_product:
                try:
                    subscription = self.env['ams.subscription'].create_from_invoice_payment(line, payment_date)
                    if subscription:
                        _logger.info(f"Created subscription {subscription.id} from payment {self.name}")
                except Exception as e:
                    _logger.error(f"Error creating subscription from payment {self.name}: {str(e)}")
                    # Don't block payment processing, but log the error