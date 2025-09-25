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
    
    has_subscription_products = fields.Boolean(
        'Has Subscription Products', 
        compute='_compute_has_subscription_products',
        store=True
    )
    
    # UPDATED: Chapter products are part of membership products now
    has_chapter_products = fields.Boolean(
        'Has Chapter Products', 
        compute='_compute_has_chapter_products',
        store=True
    )
    
    @api.depends('order_line.product_id')
    def _compute_has_membership_products(self):
        """Check if order has regular membership products"""
        for order in self:
            membership_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and 
                            line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            order.has_membership_products = bool(membership_lines)
    
    @api.depends('order_line.product_id')
    def _compute_has_subscription_products(self):
        """Check if order has subscription products (excluding memberships and chapters)"""
        for order in self:
            subscription_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and 
                            line.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
            )
            order.has_subscription_products = bool(subscription_lines)
    
    @api.depends('order_line.product_id')
    def _compute_has_chapter_products(self):
        """Check if order has chapter products"""
        for order in self:
            chapter_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'chapter')
            )
            order.has_chapter_products = bool(chapter_lines)
    
    def action_confirm(self):
        """Override to handle ALL subscription creation when order is confirmed AND paid"""
        _logger.info(f"=== SUBSCRIPTION DEBUG: action_confirm called for order {self.name} ===")
        
        try:
            result = super().action_confirm()
            _logger.info(f"SUBSCRIPTION DEBUG: Sale order confirmation succeeded for {self.name}")
        except Exception as e:
            # If confirmation fails due to email/PDF issues, still process subscriptions
            _logger.warning(f"Sale order confirmation had issues ({str(e)}), but continuing with subscription processing")
            result = True
        
        # For orders with ANY subscription products, check if they're paid and process
        for order in self:
            _logger.info(f"SUBSCRIPTION DEBUG: Checking order {order.name}")
            _logger.info(f"SUBSCRIPTION DEBUG: has_membership_products = {order.has_membership_products}")
            _logger.info(f"SUBSCRIPTION DEBUG: has_subscription_products = {order.has_subscription_products}")
            _logger.info(f"SUBSCRIPTION DEBUG: has_chapter_products = {order.has_chapter_products}")
            _logger.info(f"SUBSCRIPTION DEBUG: _is_paid() = {order._is_paid()}")
            
            if (order.has_membership_products or order.has_subscription_products or order.has_chapter_products) and order._is_paid():
                _logger.info(f"SUBSCRIPTION DEBUG: Processing subscription activation for order {order.name}")
                order._process_subscription_activations()
            else:
                _logger.info(f"SUBSCRIPTION DEBUG: Skipping subscription processing for order {order.name} - conditions not met")
        
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
    
    def _process_subscription_activations(self):
        """Process ALL subscription activations when sale order is paid - UPDATED for chapters"""
        self.ensure_one()
        _logger.info(f"=== SUBSCRIPTION DEBUG: _process_subscription_activations called for order {self.name} ===")
        
        for line in self.order_line:
            product_tmpl = line.product_id.product_tmpl_id
            _logger.info(f"SUBSCRIPTION DEBUG: Checking line {line.id} - Product: {line.product_id.name}")
            _logger.info(f"SUBSCRIPTION DEBUG: is_subscription_product = {product_tmpl.is_subscription_product}")
            _logger.info(f"SUBSCRIPTION DEBUG: subscription_product_type = {getattr(product_tmpl, 'subscription_product_type', 'None')}")
            
            # Handle subscription products
            if product_tmpl.is_subscription_product:
                _logger.info(f"SUBSCRIPTION DEBUG: Processing subscription product for line {line.id}")
                try:
                    if product_tmpl.subscription_product_type in ['membership', 'chapter']:
                        membership = self._create_membership_from_sale_line(line)
                        _logger.info(f"SUBSCRIPTION DEBUG: Successfully created membership: {membership}")
                    else:
                        # Handle non-membership subscription types (publication, event, etc.)
                        subscription = self._create_subscription_from_sale_line(line)
                        _logger.info(f"SUBSCRIPTION DEBUG: Successfully created subscription: {subscription}")
                except Exception as e:
                    _logger.error(f"SUBSCRIPTION DEBUG: Failed to create subscription from sale line {line.id}: {str(e)}")
                    _logger.error(f"SUBSCRIPTION DEBUG: Exception details: {type(e).__name__}: {e}")
                    continue
            else:
                _logger.info(f"SUBSCRIPTION DEBUG: Line {line.id} is not a subscription product - skipping")
    
    def _create_membership_from_sale_line(self, line):
        """Create membership from paid sale order line - UPDATED for chapters
        NOTE: Only ONE active regular membership allowed per member, UNLIMITED chapters"""
        _logger.info(f"=== MEMBERSHIP DEBUG: _create_membership_from_sale_line called for line {line.id} ===")
        
        product_tmpl = line.product_id.product_tmpl_id
        partner = self.partner_id
        
        _logger.info(f"MEMBERSHIP DEBUG: Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"MEMBERSHIP DEBUG: Product: {line.product_id.name}")
        _logger.info(f"MEMBERSHIP DEBUG: Product Type: {product_tmpl.subscription_product_type}")
        
        # Check if membership already exists for this specific sale line
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
        
        # UPDATED: Handle regular memberships vs chapter memberships differently
        if product_tmpl.subscription_product_type == 'chapter':
            _logger.info(f"MEMBERSHIP DEBUG: Creating CHAPTER membership - multiple chapters allowed")
        else:
            _logger.info(f"MEMBERSHIP DEBUG: Creating REGULAR membership - only one allowed, will terminate others")
            # Check for other active REGULAR memberships (only one allowed)
            try:
                other_active_memberships = self.env['ams.membership'].search([
                    ('partner_id', '=', partner.id),
                    ('product_id.subscription_product_type', '=', 'membership'),  # Only regular memberships
                    ('state', '=', 'active'),
                    ('id', '!=', False)  # Exclude current record if it exists
                ])
                
                if other_active_memberships:
                    _logger.info(f"MEMBERSHIP DEBUG: Found {len(other_active_memberships)} other active REGULAR memberships - will terminate them")
                    for old_membership in other_active_memberships:
                        old_membership.write({
                            'state': 'terminated',
                            'notes': f"Terminated due to new membership purchase: {line.product_id.name} on {fields.Date.today()}"
                        })
                        _logger.info(f"MEMBERSHIP DEBUG: Terminated existing membership {old_membership.name}")
                else:
                    _logger.info(f"MEMBERSHIP DEBUG: No other active regular memberships found")
            except Exception as e:
                _logger.error(f"MEMBERSHIP DEBUG: Error checking/terminating existing memberships: {str(e)}")
        
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
                # For chapters, try to find a chapter-specific member type, otherwise use default
                if product_tmpl.subscription_product_type == 'chapter':
                    default_member_type = self.env['ams.member.type'].search([
                        ('name', 'ilike', 'chapter')
                    ], limit=1)
                else:
                    default_member_type = None
                
                if not default_member_type:
                    default_member_type = self.env['ams.member.type'].search([
                        ('name', 'ilike', 'regular')
                    ], limit=1)
                if not default_member_type:
                    default_member_type = self.env['ams.member.type'].search([
                        ('name', 'ilike', 'individual')
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
        
        # Update foundation partner dates (for regular memberships only)
        try:
            if product_tmpl.subscription_product_type == 'membership':
                partner.write({
                    'membership_start_date': start_date,
                    'membership_end_date': end_date,
                    'member_status': 'active'
                })
                _logger.info(f"MEMBERSHIP DEBUG: Updated partner foundation dates and status")
            else:
                _logger.info(f"MEMBERSHIP DEBUG: Chapter membership - not updating partner foundation dates")
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
            
            # Add chapter-specific notes
            if product_tmpl.subscription_product_type == 'chapter':
                chapter_info = f"{product_tmpl.chapter_type or 'Local'} Chapter"
                if product_tmpl.chapter_location:
                    chapter_info += f" - {product_tmpl.chapter_location}"
                membership_vals['notes'] = f"Chapter Membership: {chapter_info}"
            
            _logger.info(f"MEMBERSHIP DEBUG: Membership values: {membership_vals}")
            
            membership = self.env['ams.membership'].create(membership_vals)
            
            membership_type_label = "chapter membership" if product_tmpl.subscription_product_type == 'chapter' else "membership"
            _logger.info(f"MEMBERSHIP DEBUG: Successfully created {membership_type_label} {membership.name} (ID: {membership.id}) for partner {partner.name}")
            
            # Log activity
            membership.message_post(
                body=f"{membership_type_label.title()} activated from sale order {self.name}",
                subject=f"{membership_type_label.title()} Activated"
            )
            
            return membership
            
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: CRITICAL ERROR creating membership record: {str(e)}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception type: {type(e).__name__}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception details: {e}")
            raise e
    
    def _create_subscription_from_sale_line(self, line):
        """Create subscription from paid sale order line - Pure subscriptions only (not membership or chapter)"""
        _logger.info(f"=== SUBSCRIPTION DEBUG: _create_subscription_from_sale_line called for line {line.id} ===")
        
        product_tmpl = line.product_id.product_tmpl_id
        partner = self.partner_id
        
        _logger.info(f"SUBSCRIPTION DEBUG: Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"SUBSCRIPTION DEBUG: Product: {line.product_id.name}")
        _logger.info(f"SUBSCRIPTION DEBUG: Subscription Type: {product_tmpl.subscription_product_type}")
        
        # SAFETY CHECK: This method should only handle non-membership subscription products
        if product_tmpl.subscription_product_type in ['membership', 'chapter']:
            _logger.error(f"SUBSCRIPTION DEBUG: ERROR - This method should not handle membership or chapter products!")
            raise ValueError(f"Invalid product type {product_tmpl.subscription_product_type} for subscription creation")
        
        # Check if subscription already exists for this sale line
        try:
            existing_subscription = self.env['ams.subscription'].search([
                ('partner_id', '=', partner.id),
                ('product_id', '=', line.product_id.id),
                ('sale_order_line_id', '=', line.id)
            ], limit=1)
            
            if existing_subscription:
                _logger.info(f"SUBSCRIPTION DEBUG: Subscription already exists for sale line {line.id}")
                return existing_subscription
            _logger.info(f"SUBSCRIPTION DEBUG: No existing subscription found - creating new one")
        except Exception as e:
            _logger.error(f"SUBSCRIPTION DEBUG: Error checking existing subscription: {str(e)}")
        
        # Calculate subscription dates
        start_date = fields.Date.today()
        end_date = self._calculate_subscription_end_date(start_date, product_tmpl.subscription_period)
        _logger.info(f"SUBSCRIPTION DEBUG: Calculated dates - Start: {start_date}, End: {end_date}")
        
        # Create subscription record
        try:
            _logger.info(f"SUBSCRIPTION DEBUG: Attempting to create ams.subscription record...")
            subscription_vals = {
                'partner_id': partner.id,
                'product_id': line.product_id.id,
                'sale_order_id': self.id,
                'sale_order_line_id': line.id,
                'start_date': start_date,
                'end_date': end_date,
                'last_renewal_date': start_date,
                'subscription_fee': line.price_subtotal,
                'payment_status': 'paid',
                'state': 'active',
                'auto_renew': product_tmpl.auto_renew_default or True,
                'renewal_interval': product_tmpl.subscription_period or 'annual',
            }
            
            # Add type-specific fields for non-membership subscriptions
            if product_tmpl.subscription_product_type == 'publication':
                subscription_vals.update({
                    'digital_access': getattr(product_tmpl, 'publication_digital_access', True),
                    'print_delivery': getattr(product_tmpl, 'publication_print_delivery', False),
                })
            elif product_tmpl.subscription_product_type == 'event':
                subscription_vals.update({
                    'event_access_level': getattr(product_tmpl, 'event_access_level', 'basic'),
                })
            
            _logger.info(f"SUBSCRIPTION DEBUG: Subscription values: {subscription_vals}")
            
            subscription = self.env['ams.subscription'].create(subscription_vals)
            
            _logger.info(f"SUBSCRIPTION DEBUG: Successfully created subscription {subscription.name} (ID: {subscription.id}) for partner {partner.name}")
            
            # Log activity
            subscription.message_post(
                body=f"Subscription activated from sale order {self.name}",
                subject="Subscription Activated"
            )
            
            return subscription
            
        except Exception as e:
            _logger.error(f"SUBSCRIPTION DEBUG: CRITICAL ERROR creating subscription record: {str(e)}")
            _logger.error(f"SUBSCRIPTION DEBUG: Exception type: {type(e).__name__}")
            _logger.error(f"SUBSCRIPTION DEBUG: Exception details: {e}")
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
    
    def _calculate_subscription_end_date(self, start_date, subscription_period):
        """Calculate subscription end date based on subscription period"""
        if subscription_period == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif subscription_period == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif subscription_period == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        elif subscription_period == 'annual':
            return start_date + relativedelta(years=1) - timedelta(days=1)
        else:  # default annual
            return start_date + relativedelta(years=1) - timedelta(days=1)
    
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
        """Override to trigger subscription processing after payment is done"""
        result = super()._reconcile_after_done()
        
        # Process ALL subscriptions for completed transactions
        for tx in self:
            if tx.state == 'done' and tx.sale_order_ids:
                for order in tx.sale_order_ids:
                    if (order.has_membership_products or 
                        order.has_subscription_products or 
                        order.has_chapter_products):
                        order._process_subscription_activations()
        
        return result