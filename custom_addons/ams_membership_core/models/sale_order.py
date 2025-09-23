# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Subscription-related fields
    has_subscription_products = fields.Boolean(
        string='Has Subscription Products',
        compute='_compute_has_subscription_products',
        store=True,
        help='This order contains subscription products'
    )
    
    created_memberships_count = fields.Integer(
        string='Created Memberships',
        compute='_compute_created_records'
    )
    
    created_subscriptions_count = fields.Integer(
        string='Created Subscriptions',
        compute='_compute_created_records'
    )
    
    @api.depends('order_line.product_id.is_subscription_product')
    def _compute_has_subscription_products(self):
        """Check if order contains subscription products"""
        for order in self:
            subscription_lines = order.order_line.filtered(
                lambda line: line.product_id.is_subscription_product
            )
            order.has_subscription_products = bool(subscription_lines)
    
    def _compute_created_records(self):
        """Compute count of created memberships and subscriptions"""
        for order in self:
            # Count memberships created from this order
            memberships = self.env['ams.membership'].search([
                ('sale_order_id', '=', order.id)
            ])
            order.created_memberships_count = len(memberships)
            
            # Count subscriptions created from this order
            subscriptions = self.env['ams.subscription'].search([
                ('sale_order_id', '=', order.id)
            ])
            order.created_subscriptions_count = len(subscriptions)
    
    def action_confirm(self):
        """Override to create subscription records when order is confirmed"""
        result = super().action_confirm()
        
        # Create subscription/membership records for confirmed orders
        for order in self:
            if order.has_subscription_products:
                order._create_subscription_records()
        
        return result
    
    def _create_subscription_records(self):
        """Create subscription/membership records from subscription products in order"""
        self.ensure_one()
        
        for line in self.order_line:
            product = line.product_id.product_tmpl_id
            
            if not product.is_subscription_product:
                continue
            
            try:
                if product.subscription_product_type == 'membership':
                    self._create_membership_from_line(line)
                else:
                    self._create_subscription_from_line(line)
                    
            except Exception as e:
                _logger.error(f"Failed to create subscription record for line {line.id}: {str(e)}")
                # Don't block the sale, just log the error
                continue
    
    def _create_membership_from_line(self, line):
        """Create membership record from sale order line"""
        # Check if membership already exists for this line
        existing = self.env['ams.membership'].search([
            ('sale_order_line_id', '=', line.id)
        ], limit=1)
        
        if existing:
            return existing
        
        # Calculate membership period based on product configuration
        start_date = fields.Date.today()
        end_date = self._calculate_subscription_end_date(
            start_date, 
            line.product_id.subscription_period
        )
        
        membership_vals = {
            'partner_id': self.partner_id.id,
            'product_id': line.product_id.id,
            'sale_order_id': self.id,
            'sale_order_line_id': line.id,
            'start_date': start_date,
            'end_date': end_date,
            'membership_fee': line.price_subtotal,
            'auto_renew': line.product_id.auto_renew_default,
            'renewal_interval': line.product_id.subscription_period,
            'state': 'draft',  # Will be activated when invoice is paid
        }
        
        membership = self.env['ams.membership'].create(membership_vals)
        
        _logger.info(f"Created membership {membership.name} from sale order line {line.id}")
        
        return membership
    
    def _create_subscription_from_line(self, line):
        """Create subscription record from sale order line"""
        # Check if subscription already exists for this line
        existing = self.env['ams.subscription'].search([
            ('sale_order_line_id', '=', line.id)
        ], limit=1)
        
        if existing:
            return existing
        
        # Calculate subscription period
        start_date = fields.Date.today()
        end_date = self._calculate_subscription_end_date(
            start_date,
            line.product_id.subscription_period
        )
        
        subscription_vals = {
            'partner_id': self.partner_id.id,
            'product_id': line.product_id.id,
            'sale_order_id': self.id,
            'sale_order_line_id': line.id,
            'start_date': start_date,
            'end_date': end_date,
            'subscription_fee': line.price_subtotal,
            'auto_renew': line.product_id.auto_renew_default,
            'renewal_interval': line.product_id.subscription_period,
            'state': 'draft',  # Will be activated when invoice is paid
        }
        
        # Add type-specific fields
        if line.product_id.subscription_product_type == 'publication':
            subscription_vals.update({
                'digital_access': line.product_id.publication_digital_access,
                'print_delivery': line.product_id.publication_print_delivery,
            })
        elif line.product_id.subscription_product_type == 'chapter':
            subscription_vals.update({
                'chapter_role': line.product_id.chapter_access_level or 'member',
            })
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        _logger.info(f"Created subscription {subscription.name} from sale order line {line.id}")
        
        return subscription
    
    def _calculate_subscription_end_date(self, start_date, period):
        """Calculate subscription end date based on period"""
        from dateutil.relativedelta import relativedelta
        from datetime import timedelta
        
        if period == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif period == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif period == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        else:  # annual or default
            return start_date + relativedelta(years=1) - timedelta(days=1)
    
    def action_view_memberships(self):
        """View memberships created from this order"""
        self.ensure_one()
        
        memberships = self.env['ams.membership'].search([
            ('sale_order_id', '=', self.id)
        ])
        
        return {
            'name': _('Memberships from Order: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('id', 'in', memberships.ids)],
        }
    
    def action_view_subscriptions(self):
        """View subscriptions created from this order"""
        self.ensure_one()
        
        subscriptions = self.env['ams.subscription'].search([
            ('sale_order_id', '=', self.id)
        ])
        
        return {
            'name': _('Subscriptions from Order: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', subscriptions.ids)],
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    is_subscription_line = fields.Boolean(
        string='Subscription Line',
        compute='_compute_is_subscription_line',
        store=True,
        help='This line creates a subscription/membership'
    )
    
    @api.depends('product_id.is_subscription_product')
    def _compute_is_subscription_line(self):
        """Check if this line is for a subscription product"""
        for line in self:
            line.is_subscription_line = bool(
                line.product_id and line.product_id.is_subscription_product
            )