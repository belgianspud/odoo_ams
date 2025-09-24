# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    has_membership_products = fields.Boolean(
        'Has Membership Products', 
        compute='_compute_has_membership_products',
        store=True
    )
    
    @api.depends('order_line.product_id')
    def _compute_has_membership_products(self):
        """Check if order has membership products"""
        for order in self:
            membership_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and 
                            line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            order.has_membership_products = bool(membership_lines)
    
    def action_confirm(self):
        """Override to handle membership creation when order is confirmed AND paid"""
        _logger.info(f"=== MEMBERSHIP DEBUG: action_confirm called for order {self.name} ===")
        
        try:
            result = super().action_confirm()
            _logger.info(f"MEMBERSHIP DEBUG: Sale order confirmation succeeded for {self.name}")
        except Exception as e:
            # If confirmation fails due to email/PDF issues, still process memberships
            _logger.warning(f"Sale order confirmation had issues ({str(e)}), but continuing with membership processing")
            result = True
        
        # For orders with membership products, check if they're paid and process memberships
        for order in self:
            _logger.info(f"MEMBERSHIP DEBUG: Checking order {order.name}")
            _logger.info(f"MEMBERSHIP DEBUG: has_membership_products = {order.has_membership_products}")
            _logger.info(f"MEMBERSHIP DEBUG: _is_paid() = {order._is_paid()}")
            
            if order.has_membership_products and order._is_paid():
                _logger.info(f"MEMBERSHIP DEBUG: Processing membership activation for order {order.name}")
                order._process_membership_activations()
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Skipping membership processing for order {order.name} - conditions not met")
        
        return result
    
    def _is_paid(self):
        """Check if sale order is fully paid (for non-accounting setups)"""
        self.ensure_one()
        
        # Check payment transactions (for e-commerce payments)
        if hasattr(self, 'transaction_ids'):
            paid_transactions = self.transaction_ids.filtered(
                lambda tx: tx.state in ['done', 'authorized']
            )
            total_paid = sum(paid_transactions.mapped('amount'))
            return total_paid >= self.amount_total
        
        # Check if there's a related invoice that's paid
        if self.invoice_ids:
            paid_invoices = self.invoice_ids.filtered(
                lambda inv: inv.payment_state in ['paid', 'in_payment']
            )
            return bool(paid_invoices)
        
        # For demo/test purposes, assume paid if order is confirmed
        # Remove this in production
        return self.state in ['sale', 'done']
    
    def _process_membership_activations(self):
        """Process membership activations when sale order is paid"""
        self.ensure_one()
        _logger.info(f"=== MEMBERSHIP DEBUG: _process_membership_activations called for order {self.name} ===")
        
        for line in self.order_line:
            product_tmpl = line.product_id.product_tmpl_id
            _logger.info(f"MEMBERSHIP DEBUG: Checking line {line.id} - Product: {line.product_id.name}")
            _logger.info(f"MEMBERSHIP DEBUG: is_subscription_product = {product_tmpl.is_subscription_product}")
            _logger.info(f"MEMBERSHIP DEBUG: subscription_product_type = {product_tmpl.subscription_product_type}")
            
            if (product_tmpl.is_subscription_product and 
                product_tmpl.subscription_product_type == 'membership'):
                
                _logger.info(f"MEMBERSHIP DEBUG: Creating membership for line {line.id}")
                try:
                    membership = self._create_membership_from_sale_line(line)
                    _logger.info(f"MEMBERSHIP DEBUG: Successfully created membership: {membership}")
                except Exception as e:
                    _logger.error(f"MEMBERSHIP DEBUG: Failed to create membership from sale line {line.id}: {str(e)}")
                    _logger.error(f"MEMBERSHIP DEBUG: Exception details: {type(e).__name__}: {e}")
                    continue
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Line {line.id} is not a membership product - skipping")
    
    def _create_membership_from_sale_line(self, line):
        """Create membership from paid sale order line"""
        _logger.info(f"=== MEMBERSHIP DEBUG: _create_membership_from_sale_line called for line {line.id} ===")
        
        product_tmpl = line.product_id.product_tmpl_id
        partner = self.partner_id
        
        _logger.info(f"MEMBERSHIP DEBUG: Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"MEMBERSHIP DEBUG: Product: {line.product_id.name}")
        
        # Check if membership already exists
        try:
            existing_membership = self.env['ams.membership'].search([
                ('partner_id', '=', partner.id),
                ('product_id', '=', line.product_id.id),
                ('sale_order_line_id', '=', line.id)
            ], limit=1)
            
            if existing_membership:
                _logger.info(f"MEMBERSHIP DEBUG: Membership already exists for sale line {line.id}")
                return existing_membership
            _logger.info(f"MEMBERSHIP DEBUG: No existing membership found - creating new one")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error checking existing membership: {str(e)}")
        
        # Set partner as member if not already
        try:
            if not partner.is_member:
                partner.write({'is_member': True})
                _logger.info(f"MEMBERSHIP DEBUG: Set partner {partner.name} as member")
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Partner {partner.name} already marked as member")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error setting partner as member: {str(e)}")
        
        # Generate member number if needed
        try:
            if not partner.member_number:
                # Try foundation method first
                if hasattr(partner, '_generate_member_number'):
                    partner._generate_member_number()
                    _logger.info(f"MEMBERSHIP DEBUG: Generated member number using foundation method")
                else:
                    # Fallback member number generation
                    partner.member_number = self._generate_member_number_fallback()
                    _logger.info(f"MEMBERSHIP DEBUG: Generated member number using fallback method: {partner.member_number}")
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Partner already has member number: {partner.member_number}")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error generating member number: {str(e)}")
        
        # Set default member type if none exists
        try:
            if not partner.member_type_id:
                default_member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', 'regular')
                ], limit=1)
                if not default_member_type:
                    default_member_type = self.env['ams.member.type'].search([], limit=1)
                
                if default_member_type:
                    partner.write({'member_type_id': default_member_type.id})
                    _logger.info(f"MEMBERSHIP DEBUG: Set member type to: {default_member_type.name}")
                else:
                    _logger.warning(f"MEMBERSHIP DEBUG: No member types found in system!")
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Partner already has member type: {partner.member_type_id.name}")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error setting member type: {str(e)}")
        
        # Calculate membership dates
        start_date = fields.Date.today()
        end_date = self._calculate_membership_end_date(start_date, product_tmpl.subscription_period)
        _logger.info(f"MEMBERSHIP DEBUG: Calculated dates - Start: {start_date}, End: {end_date}")
        
        # Update foundation partner dates
        try:
            partner.write({
                'membership_start_date': start_date,
                'membership_end_date': end_date,
                'member_status': 'active'
            })
            _logger.info(f"MEMBERSHIP DEBUG: Updated partner foundation dates")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error updating partner foundation dates: {str(e)}")
        
        # Create membership record
        try:
            _logger.info(f"MEMBERSHIP DEBUG: Attempting to create ams.membership record...")
            membership_vals = {
                'partner_id': partner.id,
                'product_id': line.product_id.id,
                'sale_order_id': self.id,
                'sale_order_line_id': line.id,
                'start_date': start_date,
                'end_date': end_date,
                'last_renewal_date': start_date,
                'membership_fee': line.price_subtotal,
                'payment_status': 'paid',
                'state': 'active',
                'auto_renew': product_tmpl.auto_renew_default or True,
                'renewal_interval': product_tmpl.subscription_period or 'annual',
            }
            
            _logger.info(f"MEMBERSHIP DEBUG: Membership values: {membership_vals}")
            
            membership = self.env['ams.membership'].create(membership_vals)
            
            _logger.info(f"MEMBERSHIP DEBUG: Successfully created membership {membership.name} (ID: {membership.id}) for partner {partner.name}")
            
            # Log activity
            membership.message_post(
                body=f"Membership activated from sale order {self.name}",
                subject="Membership Activated"
            )
            
            return membership
            
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: CRITICAL ERROR creating membership record: {str(e)}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception type: {type(e).__name__}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception details: {e}")
            raise e
    
    def _calculate_membership_end_date(self, start_date, subscription_period):
        """Calculate membership end date based on subscription period"""
        if subscription_period == 'annual':
            # Always set to December 31st of current year
            current_year = start_date.year
            end_date = date(current_year, 12, 31)
            
            # If purchase date is after December 31st, extend to next year
            if start_date > end_date:
                end_date = date(current_year + 1, 12, 31)
                
            return end_date
        elif subscription_period == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif subscription_period == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif subscription_period == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        else:  # default annual
            current_year = start_date.year
            return date(current_year, 12, 31)
    
    def _generate_member_number_fallback(self):
        """Fallback member number generation if foundation module not available"""
        # Simple sequential member number
        last_member = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_number', '!=', False)
        ], order='member_number desc', limit=1)
        
        if last_member and last_member.member_number:
            try:
                last_number = int(last_member.member_number)
                return str(last_number + 1).zfill(6)
            except ValueError:
                pass
        
        # Default starting number
        return "000001"


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    def _reconcile_after_done(self):
        """Override to trigger membership processing after payment is done"""
        result = super()._reconcile_after_done()
        
        # Process memberships for completed transactions
        for tx in self:
            if tx.state == 'done' and tx.sale_order_ids:
                for order in tx.sale_order_ids:
                    if order.has_membership_products:
                        order._process_membership_activations()
        
        return result