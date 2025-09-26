# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Membership-related fields
    contains_memberships = fields.Boolean('Contains Memberships', compute='_compute_contains_memberships', store=True)
    membership_ids = fields.One2many('ams.membership.base', 'sale_order_id', 'Memberships')
    membership_count = fields.Integer('Membership Count', compute='_compute_membership_count')
    
    # Member information
    is_member_order = fields.Boolean('Member Order', compute='_compute_is_member_order', store=True)
    member_type_id = fields.Many2one('ams.member.type', 'Member Type', related='partner_id.member_type_id', readonly=True)
    member_discount_applied = fields.Boolean('Member Discount Applied', default=False)
    
    # Subscription order types
    order_type = fields.Selection([
        ('new', 'New Subscription'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('additional', 'Additional Subscription')
    ], string='Order Type', compute='_compute_order_type', store=True)
    
    # Original membership for upgrades/renewals
    original_membership_id = fields.Many2one('ams.membership.base', 'Original Membership',
                                           help="Original membership being renewed or upgraded")

    @api.depends('order_line.product_id')
    def _compute_contains_memberships(self):
        """Check if order contains subscription products"""
        for order in self:
            has_subscriptions = any(
                line.product_id.product_tmpl_id.is_subscription_product 
                for line in order.order_line
            )
            order.contains_memberships = has_subscriptions

    def _compute_membership_count(self):
        """Count related membership records"""
        for order in self:
            order.membership_count = len(order.membership_ids)

    @api.depends('partner_id')
    def _compute_is_member_order(self):
        """Check if order is from a member"""
        for order in self:
            order.is_member_order = order.partner_id.is_member if order.partner_id else False

    @api.depends('order_line.product_id', 'original_membership_id')
    def _compute_order_type(self):
        """Determine order type based on products and context"""
        for order in self:
            if not order.contains_memberships:
                order.order_type = False
                continue
            
            if order.original_membership_id:
                # Check if it's an upgrade or renewal
                original_product = order.original_membership_id.product_id.product_tmpl_id
                new_products = order.order_line.mapped('product_id.product_tmpl_id')
                
                if any(p.list_price > original_product.list_price for p in new_products):
                    order.order_type = 'upgrade'
                elif any(p.list_price < original_product.list_price for p in new_products):
                    order.order_type = 'downgrade'
                else:
                    order.order_type = 'renewal'
            else:
                # Check if customer has existing active memberships
                if order.partner_id:
                    existing_memberships = self.env['ams.membership.base'].search([
                        ('partner_id', '=', order.partner_id.id),
                        ('state', 'in', ['active', 'grace'])
                    ])
                    
                    if existing_memberships:
                        order.order_type = 'additional'
                    else:
                        order.order_type = 'new'
                else:
                    order.order_type = 'new'

    @api.onchange('partner_id')
    def _onchange_partner_id_membership(self):
        """Apply member discounts when partner changes"""
        super()._onchange_partner_id()
        
        if self.partner_id and self.partner_id.is_member:
            self._apply_member_discounts()

    def _apply_member_discounts(self):
        """Apply member discounts to subscription products"""
        if not self.partner_id or not self.partner_id.is_member:
            return
        
        for line in self.order_line:
            if line.product_id.product_tmpl_id.is_subscription_product:
                # Check if member discount should be applied
                # This is simplified - in practice would use price rules/discounts
                if self.partner_id.member_type_id:
                    member_type = self.partner_id.member_type_id
                    # Apply a sample 10% member discount
                    if not line.member_discount_applied:
                        discount_percent = 10.0  # This would be configurable
                        line.discount = discount_percent
                        line.member_discount_applied = True
        
        self.member_discount_applied = True

    def action_confirm(self):
        """Override to handle membership-specific confirmation logic"""
        result = super().action_confirm()
        
        for order in self:
            if order.contains_memberships:
                order._process_membership_order()
        
        return result

    def _process_membership_order(self):
        """Process membership-specific order logic"""
        self.ensure_one()
        
        # Handle upgrade/downgrade logic
        if self.order_type in ['upgrade', 'downgrade'] and self.original_membership_id:
            self._process_membership_change()
        
        # Set up auto-renewal if applicable
        for line in self.order_line:
            if line.product_id.product_tmpl_id.is_subscription_product:
                if line.product_id.product_tmpl_id.auto_renewal_eligible:
                    # This would set up auto-renewal logic
                    pass

    def _process_membership_change(self):
        """Process membership upgrade or downgrade"""
        self.ensure_one()
        
        if not self.original_membership_id:
            return
        
        original = self.original_membership_id
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        
        if not settings:
            return
        
        # Handle billing based on settings
        if settings.upgrade_billing_method == 'credit_invoice':
            self._create_credit_memo_for_upgrade()
        elif settings.upgrade_billing_method == 'adjustment_invoice':
            self._create_adjustment_invoice()
        # immediate_charge would be handled at payment time
        
        # Schedule original membership for cancellation
        original.write({
            'state': 'cancelled',
            'cancellation_date': fields.Date.today(),
            'cancellation_reason': f'Replaced by order {self.name}'
        })

    def _create_credit_memo_for_upgrade(self):
        """Create credit memo for unused portion of original membership"""
        # This would calculate unused portion and create credit memo
        # Simplified implementation
        original = self.original_membership_id
        
        # Calculate unused days
        today = fields.Date.today()
        if original.end_date > today:
            unused_days = (original.end_date - today).days
            total_days = (original.end_date - original.start_date).days
            
            if total_days > 0:
                refund_amount = original.paid_amount * (unused_days / total_days)
                
                # Create credit memo (simplified)
                self.message_post(
                    body=_("Credit memo needed: $%.2f for %d unused days") % (refund_amount, unused_days),
                    message_type='notification'
                )

    def _create_adjustment_invoice(self):
        """Create single adjustment invoice showing net difference"""
        # This would create an invoice line showing the net difference
        self.message_post(
            body=_("Adjustment invoice logic would be implemented here"),
            message_type='notification'
        )

    def action_view_memberships(self):
        """View related memberships"""
        self.ensure_one()
        
        if not self.membership_ids:
            raise UserError(_("No membership records found for this order."))
        
        return {
            'name': _('Memberships from Order %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.base',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_membership_preview(self):
        """Preview membership details before confirmation"""
        self.ensure_one()
        
        if not self.contains_memberships:
            raise UserError(_("This order does not contain subscription products."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Preview'),
            'res_model': 'ams.membership.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            }
        }

    def action_setup_auto_renewal(self):
        """Set up auto-renewal for subscription products"""
        self.ensure_one()
        
        auto_renewal_lines = self.order_line.filtered(
            lambda l: l.product_id.product_tmpl_id.auto_renewal_eligible
        )
        
        if not auto_renewal_lines:
            raise UserError(_("No auto-renewal eligible products in this order."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Setup Auto-Renewal'),
            'res_model': 'ams.auto.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'auto_renewal_line_ids': auto_renewal_lines.ids,
            }
        }

    # Portal methods for member self-service
    def _get_portal_return_action(self):
        """Return portal action"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/orders/{self.id}',
            'target': 'self',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Membership-related fields
    is_subscription_line = fields.Boolean('Is Subscription Line', 
                                        compute='_compute_is_subscription_line', store=True)
    membership_id = fields.Many2one('ams.membership.base', 'Related Membership', readonly=True)
    
    # Member discount tracking
    member_discount_applied = fields.Boolean('Member Discount Applied', default=False)
    original_member_price = fields.Float('Original Member Price')
    
    # Membership dates for preview
    membership_start_date = fields.Date('Membership Start Date')
    membership_end_date = fields.Date('Membership End Date')
    
    # Pro-rating information
    is_prorated = fields.Boolean('Is Pro-rated', default=False)
    proration_details = fields.Text('Pro-ration Details')

    @api.depends('product_id')
    def _compute_is_subscription_line(self):
        """Check if line contains subscription product"""
        for line in self:
            line.is_subscription_line = (
                line.product_id and 
                line.product_id.product_tmpl_id.is_subscription_product
            )

    @api.onchange('product_id')
    def _onchange_product_id_membership(self):
        """Handle subscription product selection"""
        if self.is_subscription_line and self.product_id:
            # Set membership dates
            self._calculate_membership_dates()
            
            # Apply member pricing if applicable
            if self.order_id.partner_id and self.order_id.partner_id.is_member:
                self._apply_member_pricing()
            
            # Check for pro-rating
            self._check_prorating()

    def _calculate_membership_dates(self):
        """Calculate membership start and end dates"""
        if not self.is_subscription_line:
            return
        
        product_tmpl = self.product_id.product_tmpl_id
        
        # Set default start date
        if not self.membership_start_date:
            self.membership_start_date = fields.Date.today()
        
        # Calculate end date
        self.membership_end_date = product_tmpl.calculate_membership_end_date(
            self.membership_start_date
        )

    def _apply_member_pricing(self):
        """Apply member-specific pricing"""
        if not self.order_id.partner_id.is_member:
            return
        
        # This would integrate with Odoo's pricelist system
        # For now, apply a simple discount
        if not self.member_discount_applied:
            self.original_member_price = self.price_unit
            # Apply 10% member discount (would be configurable)
            self.discount = 10.0
            self.member_discount_applied = True

    def _check_prorating(self):
        """Check if pro-rating should be applied"""
        if not self.is_subscription_line:
            return
        
        product_tmpl = self.product_id.product_tmpl_id
        
        if product_tmpl.enable_prorating and self.membership_start_date and self.membership_end_date:
            prorated_price = product_tmpl.calculate_prorated_price(
                self.membership_start_date,
                self.membership_end_date
            )
            
            if abs(prorated_price - product_tmpl.list_price) > 0.01:  # Small threshold for float comparison
                self.is_prorated = True
                self.price_unit = prorated_price
                
                # Calculate proration details
                period_days = (self.membership_end_date - self.membership_start_date).days
                total_days = product_tmpl.membership_duration
                percentage = (period_days / total_days) * 100 if total_days > 0 else 100
                
                self.proration_details = _(
                    "Pro-rated for %(period_days)d of %(total_days)d days (%(percentage).1f%%)"
                ) % {
                    'period_days': period_days,
                    'total_days': total_days,
                    'percentage': percentage
                }

    def get_membership_summary(self):
        """Get membership summary for this line"""
        self.ensure_one()
        
        if not self.is_subscription_line:
            return {}
        
        product_tmpl = self.product_id.product_tmpl_id
        
        return {
            'product_class': dict(product_tmpl._fields['product_class'].selection)[product_tmpl.product_class],
            'recurrence_period': dict(product_tmpl._fields['recurrence_period'].selection)[product_tmpl.recurrence_period],
            'start_date': self.membership_start_date,
            'end_date': self.membership_end_date,
            'is_prorated': self.is_prorated,
            'proration_details': self.proration_details,
            'auto_renewal_eligible': product_tmpl.auto_renewal_eligible,
            'member_discount_applied': self.member_discount_applied,
        }

    def action_view_membership(self):
        """View related membership record"""
        self.ensure_one()
        
        if not self.membership_id:
            raise UserError(_("No membership record linked to this line."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Record'),
            'res_model': self.membership_id._name,
            'res_id': self.membership_id.id,
            'view_mode': 'form',
        }

    # Constraints
    @api.constrains('membership_start_date', 'membership_end_date')
    def _check_membership_dates(self):
        """Validate membership dates"""
        for line in self.filtered('is_subscription_line'):
            if line.membership_start_date and line.membership_end_date:
                if line.membership_end_date <= line.membership_start_date:
                    raise ValidationError(_("Membership end date must be after start date."))

    @api.constrains('discount')
    def _check_member_discount(self):
        """Validate member discount"""
        for line in self:
            if line.member_discount_applied and line.discount > 50:
                # Prevent excessive discounts
                raise ValidationError(_("Member discount cannot exceed 50%."))

    def _prepare_invoice_line(self, **optional_values):
        """Override to pass membership information to invoice line"""
        values = super()._prepare_invoice_line(**optional_values)
        
        if self.is_subscription_line:
            values.update({
                'membership_start_date': self.membership_start_date,
                'membership_end_date': self.membership_end_date,
                'is_prorated': self.is_prorated,
                'original_price': self.original_member_price or self.price_unit,
                'proration_period': self.proration_details,
            })
        
        return values