# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSRenewal(models.Model):
    _name = 'ams.renewal'
    _description = 'Membership/Subscription Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date desc, id desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char('Renewal Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'))
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Related Records
    membership_id = fields.Many2one('ams.membership', 'Membership', ondelete='cascade')
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Member/Subscriber', 
                                compute='_compute_partner_id', store=True)
    
    # Renewal Details
    renewal_date = fields.Date('Renewal Date', required=True, default=fields.Date.today, tracking=True)
    previous_end_date = fields.Date('Previous End Date', compute='_compute_previous_dates', store=True)
    new_end_date = fields.Date('New End Date', required=True, tracking=True)
    
    # Renewal Configuration
    renewal_type = fields.Selection([
        ('manual', 'Manual Renewal'),
        ('automatic', 'Automatic Renewal'),
        ('early', 'Early Renewal'),
        ('late', 'Late Renewal'),
        ('grace', 'Grace Period Renewal'),
    ], string='Renewal Type', default='manual', required=True, tracking=True)
    
    renewal_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Renewal Period', default='annual', required=True)
    
    # Financial Information
    amount = fields.Monetary('Renewal Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    original_amount = fields.Monetary('Original Amount', currency_field='currency_id',
                                     help='Amount before any discounts or prorations')
    discount_amount = fields.Monetary('Discount Amount', currency_field='currency_id', default=0.0)
    proration_amount = fields.Monetary('Proration Amount', currency_field='currency_id', default=0.0,
                                      help='Positive for additional charge, negative for credit')
    
    # Payment Integration
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string='Payment Status', compute='_compute_payment_state', store=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Renewal Analysis
    is_early_renewal = fields.Boolean('Early Renewal', compute='_compute_renewal_analysis', store=True)
    is_late_renewal = fields.Boolean('Late Renewal', compute='_compute_renewal_analysis', store=True)
    days_early = fields.Integer('Days Early', compute='_compute_renewal_analysis', store=True)
    days_late = fields.Integer('Days Late', compute='_compute_renewal_analysis', store=True)
    
    # Revenue Recognition (placeholder for future billing integration)
    revenue_recognition_date = fields.Date('Revenue Recognition Date')
    deferred_revenue_amount = fields.Monetary('Deferred Revenue', currency_field='currency_id')
    
    # Additional Information
    notes = fields.Text('Notes')
    renewal_reason = fields.Text('Renewal Reason/Comments')
    
    @api.depends('membership_id', 'subscription_id')
    def _compute_display_name(self):
        for renewal in self:
            if renewal.membership_id:
                renewal.display_name = f"Membership Renewal - {renewal.membership_id.display_name}"
            elif renewal.subscription_id:
                renewal.display_name = f"Subscription Renewal - {renewal.subscription_id.display_name}"
            else:
                renewal.display_name = renewal.name or _('New Renewal')
    
    @api.depends('membership_id.partner_id', 'subscription_id.partner_id')
    def _compute_partner_id(self):
        for renewal in self:
            if renewal.membership_id:
                renewal.partner_id = renewal.membership_id.partner_id
            elif renewal.subscription_id:
                renewal.partner_id = renewal.subscription_id.partner_id
            else:
                renewal.partner_id = False
    
    @api.depends('membership_id.end_date', 'subscription_id.end_date')
    def _compute_previous_dates(self):
        for renewal in self:
            if renewal.membership_id:
                renewal.previous_end_date = renewal.membership_id.end_date
            elif renewal.subscription_id:
                renewal.previous_end_date = renewal.subscription_id.end_date
            else:
                renewal.previous_end_date = False
    
    @api.depends('invoice_id.payment_state')
    def _compute_payment_state(self):
        for renewal in self:
            if renewal.invoice_id:
                renewal.payment_state = renewal.invoice_id.payment_state
            else:
                renewal.payment_state = 'not_paid'
    
    @api.depends('renewal_date', 'previous_end_date')
    def _compute_renewal_analysis(self):
        for renewal in self:
            if not renewal.previous_end_date or not renewal.renewal_date:
                renewal.is_early_renewal = False
                renewal.is_late_renewal = False
                renewal.days_early = 0
                renewal.days_late = 0
                continue
            
            days_diff = (renewal.renewal_date - renewal.previous_end_date).days
            
            if days_diff < 0:  # Renewed before expiration
                renewal.is_early_renewal = True
                renewal.is_late_renewal = False
                renewal.days_early = abs(days_diff)
                renewal.days_late = 0
            elif days_diff > 0:  # Renewed after expiration
                renewal.is_early_renewal = False
                renewal.is_late_renewal = True
                renewal.days_early = 0
                renewal.days_late = days_diff
            else:  # Renewed exactly on expiration date
                renewal.is_early_renewal = False
                renewal.is_late_renewal = False
                renewal.days_early = 0
                renewal.days_late = 0

    @api.model
    def create(self, vals):
        """Override create to handle sequence and setup"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.renewal') or _('New')
        
        renewal = super().create(vals)
        
        # Auto-calculate amounts if not provided
        if not vals.get('original_amount'):
            renewal._calculate_renewal_amounts()
        
        return renewal
    
    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for renewal in self:
                renewal._handle_state_change(vals['state'])
        
        return result
    
    def _handle_state_change(self, new_state):
        """Handle renewal state changes"""
        self.ensure_one()
        
        if new_state == 'confirmed':
            # Apply the renewal to the membership/subscription
            self._apply_renewal()
        elif new_state == 'cancelled':
            # Handle cancellation logic
            self._handle_renewal_cancellation()
    
    def _apply_renewal(self):
        """Apply the renewal to the membership/subscription"""
        self.ensure_one()
        
        if self.membership_id:
            self.membership_id.write({
                'end_date': self.new_end_date,
                'last_renewal_date': self.renewal_date,
                'state': 'active',  # Reactivate if was in grace/suspended
            })
            _logger.info(f"Applied renewal to membership {self.membership_id.name}")
        
        elif self.subscription_id:
            self.subscription_id.write({
                'end_date': self.new_end_date,
                'last_renewal_date': self.renewal_date,
                'state': 'active',  # Reactivate if was in grace/suspended
            })
            _logger.info(f"Applied renewal to subscription {self.subscription_id.name}")
    
    def _handle_renewal_cancellation(self):
        """Handle renewal cancellation"""
        self.ensure_one()
        
        # Cancel related sale order if exists
        if self.sale_order_id and self.sale_order_id.state not in ['sale', 'done']:
            try:
                self.sale_order_id.action_cancel()
            except Exception as e:
                _logger.warning(f"Could not cancel sale order {self.sale_order_id.name}: {str(e)}")
        
        # Cancel related invoice if exists and not paid
        if self.invoice_id and self.invoice_id.payment_state == 'not_paid':
            try:
                self.invoice_id.button_cancel()
            except Exception as e:
                _logger.warning(f"Could not cancel invoice {self.invoice_id.name}: {str(e)}")
    
    def _calculate_renewal_amounts(self):
        """Calculate renewal amounts including discounts and prorations"""
        self.ensure_one()
        
        base_amount = 0.0
        
        if self.membership_id:
            base_amount = self.membership_id.membership_fee
        elif self.subscription_id:
            base_amount = self.subscription_id.subscription_fee
        
        # Apply early renewal discounts
        if self.is_early_renewal:
            discount = self._calculate_early_renewal_discount(base_amount)
            self.discount_amount = discount
        
        # Calculate proration if applicable
        proration = self._calculate_proration_amount(base_amount)
        self.proration_amount = proration
        
        # Set amounts
        self.original_amount = base_amount
        self.amount = base_amount - self.discount_amount + self.proration_amount
    
    def _calculate_early_renewal_discount(self, base_amount):
        """Calculate early renewal discount"""
        self.ensure_one()
        
        if not self.is_early_renewal:
            return 0.0
        
        # TODO: Make discount rates configurable
        if self.days_early >= 60:  # 2+ months early
            return base_amount * 0.05  # 5% discount
        elif self.days_early >= 30:  # 1+ month early
            return base_amount * 0.025  # 2.5% discount
        
        return 0.0
    
    def _calculate_proration_amount(self, base_amount):
        """Calculate proration amount (placeholder for future implementation)"""
        self.ensure_one()
        
        # TODO: Implement proration logic based on:
        # - Mid-cycle changes
        # - Partial period renewals
        # - Upgrade/downgrade scenarios
        
        return 0.0
    
    # Action Methods
    def action_create_invoice(self):
        """Create invoice for this renewal"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_("Invoice already exists for this renewal."))
        
        # Create sale order first if it doesn't exist
        if not self.sale_order_id:
            self._create_sale_order()
        
        # Create and post invoice
        invoices = self.sale_order_id._create_invoices()
        if invoices:
            self.invoice_id = invoices[0].id
            self.state = 'pending'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
    
    def _create_sale_order(self):
        """Create sale order for this renewal"""
        self.ensure_one()
        
        product = None
        if self.membership_id:
            product = self.membership_id.product_id
        elif self.subscription_id:
            product = self.subscription_id.product_id
        
        if not product:
            raise UserError(_("No product found for renewal."))
        
        # Create sale order
        sale_vals = {
            'partner_id': self.partner_id.id,
            'date_order': self.renewal_date,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': self.amount,
                'name': f"Renewal: {product.name}",
            })],
        }
        
        sale_order = self.env['sale.order'].create(sale_vals)
        self.sale_order_id = sale_order.id
        
        # Confirm the sale order
        sale_order.action_confirm()
        
        return sale_order
    
    def action_confirm(self):
        """Confirm the renewal"""
        for renewal in self:
            if renewal.state != 'draft':
                raise UserError(_("Only draft renewals can be confirmed."))
            
            renewal.write({'state': 'confirmed'})
    
    def action_cancel(self):
        """Cancel the renewal"""
        for renewal in self:
            renewal.write({'state': 'cancelled'})
    
    def action_view_invoice(self):
        """View renewal invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this renewal."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
    
    @api.model
    def generate_renewal_reminders(self):
        """Generate renewal reminders for expiring memberships/subscriptions"""
        reminder_days = 30  # TODO: Make configurable
        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        
        # Find expiring memberships
        expiring_memberships = self.env['ams.membership'].search([
            ('state', '=', 'active'),
            ('end_date', '<=', reminder_date),
            ('auto_renew', '=', False),
            ('renewal_reminder_sent', '=', False),
        ])
        
        # Find expiring subscriptions
        expiring_subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('end_date', '<=', reminder_date),
            ('auto_renew', '=', False),
            ('renewal_reminder_sent', '=', False),
        ])
        
        # Create renewal records and send reminders
        for membership in expiring_memberships:
            self._create_renewal_reminder(membership=membership)
        
        for subscription in expiring_subscriptions:
            self._create_renewal_reminder(subscription=subscription)
        
        _logger.info(f"Generated {len(expiring_memberships + expiring_subscriptions)} renewal reminders")
    
    def _create_renewal_reminder(self, membership=None, subscription=None):
        """Create renewal reminder record"""
        vals = {
            'membership_id': membership.id if membership else False,
            'subscription_id': subscription.id if subscription else False,
            'renewal_type': 'manual',
            'state': 'draft',
        }
        
        if membership:
            vals.update({
                'new_end_date': membership._calculate_renewal_end_date(),
                'amount': membership.membership_fee,
            })
            membership.renewal_reminder_sent = True
        
        if subscription:
            vals.update({
                'new_end_date': subscription._calculate_renewal_end_date(),
                'amount': subscription.subscription_fee,
            })
            subscription.renewal_reminder_sent = True
        
        renewal = self.create(vals)
        
        # TODO: Send renewal reminder email
        
        return renewal
    
    @api.model
    def process_automatic_renewals(self):
        """Process automatic renewals for eligible memberships/subscriptions"""
        today = fields.Date.today()
        
        # Find auto-renewable memberships that have expired
        auto_memberships = self.env['ams.membership'].search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', True),
        ])
        
        # Find auto-renewable subscriptions that have expired
        auto_subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', True),
        ])
        
        # Process renewals
        for membership in auto_memberships:
            try:
                self._process_automatic_renewal(membership=membership)
            except Exception as e:
                _logger.error(f"Failed to auto-renew membership {membership.name}: {str(e)}")
        
        for subscription in auto_subscriptions:
            try:
                self._process_automatic_renewal(subscription=subscription)
            except Exception as e:
                _logger.error(f"Failed to auto-renew subscription {subscription.name}: {str(e)}")
        
        _logger.info(f"Processed {len(auto_memberships + auto_subscriptions)} automatic renewals")
    
    def _process_automatic_renewal(self, membership=None, subscription=None):
        """Process automatic renewal for a membership or subscription"""
        vals = {
            'membership_id': membership.id if membership else False,
            'subscription_id': subscription.id if subscription else False,
            'renewal_type': 'automatic',
            'state': 'confirmed',
        }
        
        if membership:
            vals.update({
                'new_end_date': membership._calculate_renewal_end_date(),
                'amount': membership.membership_fee,
                'renewal_period': membership.renewal_interval,
            })
        
        if subscription:
            vals.update({
                'new_end_date': subscription._calculate_renewal_end_date(),
                'amount': subscription.subscription_fee,
                'renewal_period': subscription.renewal_interval,
            })
        
        renewal = self.create(vals)
        
        # Create invoice for automatic renewal
        try:
            renewal.action_create_invoice()
        except Exception as e:
            _logger.warning(f"Failed to create invoice for automatic renewal {renewal.name}: {str(e)}")
        
        return renewal
    
    # Constraints
    @api.constrains('membership_id', 'subscription_id')
    def _check_related_record(self):
        for renewal in self:
            if not renewal.membership_id and not renewal.subscription_id:
                raise ValidationError(_("Renewal must be linked to either a membership or subscription."))
            if renewal.membership_id and renewal.subscription_id:
                raise ValidationError(_("Renewal cannot be linked to both membership and subscription."))
    
    @api.constrains('renewal_date', 'new_end_date')
    def _check_dates(self):
        for renewal in self:
            if renewal.new_end_date <= renewal.renewal_date:
                raise ValidationError(_("New end date must be after renewal date."))
    
    @api.constrains('amount')
    def _check_amount(self):
        for renewal in self:
            if renewal.amount < 0:
                raise ValidationError(_("Renewal amount cannot be negative."))

    def action_view_invoice(self):
        """View renewal invoice"""
        self.ensure_one()
    
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this renewal."))
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_view_sale_order(self):
        """View renewal sale order"""
        self.ensure_one()
    
        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this renewal."))
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }