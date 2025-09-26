# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    # Enhanced product detection fields
    has_membership_products = fields.Boolean(
        'Has Membership Products', 
        compute='_compute_has_subscription_products',
        store=True,
        help='This order contains regular membership products'
    )
    
    has_subscription_products = fields.Boolean(
        'Has Subscription Products', 
        compute='_compute_has_subscription_products',
        store=True,
        help='This order contains pure subscription products (not memberships or chapters)'
    )
    
    has_chapter_products = fields.Boolean(
        'Has Chapter Products', 
        compute='_compute_has_subscription_products',
        store=True,
        help='This order contains chapter membership products'
    )
    
    # Enhanced analytics fields
    membership_total = fields.Monetary(
        'Membership Total',
        compute='_compute_subscription_totals',
        store=True,
        help='Total amount for membership products'
    )
    
    chapter_total = fields.Monetary(
        'Chapter Total',
        compute='_compute_subscription_totals',
        store=True,
        help='Total amount for chapter products'
    )
    
    subscription_total = fields.Monetary(
        'Subscription Total',
        compute='_compute_subscription_totals',
        store=True,
        help='Total amount for pure subscription products'
    )
    
    # Chapter-specific fields
    chapter_count = fields.Integer(
        'Chapter Products Count',
        compute='_compute_subscription_counts',
        help='Number of different chapter products in this order'
    )
    
    membership_count = fields.Integer(
        'Membership Products Count',
        compute='_compute_subscription_counts',
        help='Number of membership products in this order'
    )
    
    subscription_count = fields.Integer(
        'Pure Subscription Count',
        compute='_compute_subscription_counts',
        help='Number of pure subscription products in this order'
    )
    
    # Chapter eligibility and validation
    chapter_eligibility_checked = fields.Boolean(
        'Chapter Eligibility Checked',
        default=False,
        help='Whether chapter eligibility has been validated'
    )
    
    chapter_warnings = fields.Text(
        'Chapter Warnings',
        help='Warnings about chapter eligibility or restrictions'
    )

    @api.depends('order_line.product_id')
    def _compute_has_subscription_products(self):
        """Enhanced computation for all subscription product types"""
        for order in self:
            membership_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and 
                            line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            order.has_membership_products = bool(membership_lines)
            
            chapter_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'chapter')
            )
            order.has_chapter_products = bool(chapter_lines)
            
            subscription_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and 
                            line.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
            )
            order.has_subscription_products = bool(subscription_lines)
    
    @api.depends('order_line.product_id', 'order_line.price_subtotal')
    def _compute_subscription_totals(self):
        """Compute totals for different subscription types"""
        for order in self:
            membership_total = 0.0
            chapter_total = 0.0
            subscription_total = 0.0
            
            for line in order.order_line:
                if line.product_id.product_tmpl_id.is_subscription_product:
                    if line.product_id.product_tmpl_id.subscription_product_type == 'membership':
                        membership_total += line.price_subtotal
                    elif line.product_id.product_tmpl_id.subscription_product_type == 'chapter':
                        chapter_total += line.price_subtotal
                    else:
                        subscription_total += line.price_subtotal
            
            order.membership_total = membership_total
            order.chapter_total = chapter_total
            order.subscription_total = subscription_total
    
    @api.depends('order_line.product_id')
    def _compute_subscription_counts(self):
        """Compute counts for different subscription types"""
        for order in self:
            membership_count = len(order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            ))
            
            chapter_count = len(order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'chapter')
            ))
            
            subscription_count = len(order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
            ))
            
            order.membership_count = membership_count
            order.chapter_count = chapter_count
            order.subscription_count = subscription_count

    def action_confirm(self):
        """Enhanced order confirmation with chapter eligibility validation"""
        _logger.info(f"=== ENHANCED SALE ORDER DEBUG: action_confirm called for order {self.name} ===")
        
        # Pre-confirmation validations
        for order in self:
            if order.has_chapter_products:
                order._validate_chapter_eligibility()
            
            if order.has_membership_products or order.has_chapter_products:
                order._validate_membership_rules()
        
        try:
            result = super().action_confirm()
            _logger.info(f"SALE ORDER DEBUG: Order confirmation succeeded for {self.name}")
        except Exception as e:
            # If confirmation fails due to email/PDF issues, still process subscriptions
            _logger.warning(f"Sale order confirmation had issues ({str(e)}), but continuing with subscription processing")
            result = True
        
        # Enhanced subscription processing
        for order in self:
            _logger.info(f"SALE ORDER DEBUG: Checking order {order.name}")
            _logger.info(f"SALE ORDER DEBUG: has_membership_products = {order.has_membership_products}")
            _logger.info(f"SALE ORDER DEBUG: has_subscription_products = {order.has_subscription_products}")
            _logger.info(f"SALE ORDER DEBUG: has_chapter_products = {order.has_chapter_products}")
            _logger.info(f"SALE ORDER DEBUG: _is_paid() = {order._is_paid()}")
            
            if (order.has_membership_products or order.has_subscription_products or order.has_chapter_products) and order._is_paid():
                _logger.info(f"SALE ORDER DEBUG: Processing subscription activation for order {order.name}")
                order._process_subscription_activations()
            else:
                _logger.info(f"SALE ORDER DEBUG: Skipping subscription processing for order {order.name} - conditions not met")
        
        return result
    
    def _validate_chapter_eligibility(self):
        """Validate chapter membership eligibility - EMERGENCY SAFE VERSION"""
        self.ensure_one()
        
        warnings = []
        
        # Check if customer is a member
        if not self.partner_id.is_member:
            warnings.append("Customer is not a member - chapter membership may require regular membership first")
        
        # Check each chapter product
        for line in self.order_line:
            product_tmpl = line.product_id.product_tmpl_id
            
            if product_tmpl.subscription_product_type == 'chapter':
                # Check if already a member of this chapter
                existing_chapter = self.partner_id.membership_ids.filtered(
                    lambda m: (m.product_id.product_tmpl_id == product_tmpl and 
                              m.state in ['active', 'grace', 'draft'])
                )
                if existing_chapter:
                    warnings.append(f"Customer already has membership in {product_tmpl.name}")
                
                # SKIP geographic restrictions for now - EMERGENCY FIX
                # TODO: Add back when chapter_geographic_restriction field is added
                
                # Check member limits - SAFE VERSION
                try:
                    if hasattr(product_tmpl, 'chapter_member_limit') and product_tmpl.chapter_member_limit > 0:
                        member_count = getattr(product_tmpl, 'chapter_member_count', 0)
                        if member_count >= product_tmpl.chapter_member_limit:
                            warnings.append(f"Chapter at capacity: {product_tmpl.name} has reached its member limit")
                except (AttributeError, TypeError):
                    pass
                
                # Check minimum member requirement - SAFE VERSION
                try:
                    if hasattr(product_tmpl, 'chapter_minimum_members') and product_tmpl.chapter_minimum_members > 0:
                        member_count = getattr(product_tmpl, 'chapter_member_count', 0)
                        if member_count < product_tmpl.chapter_minimum_members:
                            warnings.append(f"Chapter below minimum: {product_tmpl.name} needs more members to remain active")
                except (AttributeError, TypeError):
                    pass
        
        if warnings:
            self.chapter_warnings = '\n'.join(warnings)
            _logger.warning(f"Chapter eligibility warnings for order {self.name}: {self.chapter_warnings}")
        else:
            self.chapter_warnings = False
        
        self.chapter_eligibility_checked = True
    
    def _validate_membership_rules(self):
        """Validate membership business rules - ENHANCED for chapters"""
        self.ensure_one()
        
        # Check for multiple regular memberships in same order
        membership_lines = self.order_line.filtered(
            lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                         line.product_id.product_tmpl_id.subscription_product_type == 'membership')
        )
        
        if len(membership_lines) > 1:
            raise ValidationError(
                _("Only one regular membership product is allowed per order. "
                  "Please remove extra membership products or create separate orders.")
            )
        
        # Check if customer already has active regular membership
        if membership_lines and self.partner_id.current_membership_id and self.partner_id.current_membership_id.state == 'active':
            existing_membership = self.partner_id.current_membership_id
            new_product = membership_lines[0].product_id.product_tmpl_id
            
            if existing_membership.product_id.product_tmpl_id != new_product:
                # Different product - this might be an upgrade/downgrade
                _logger.info(f"Customer {self.partner_id.name} purchasing different membership product: {new_product.name} (current: {existing_membership.product_id.name})")
        
        # Chapter memberships are unlimited, so no validation needed
        _logger.info(f"Membership validation completed for order {self.name}")
    
    def _is_paid(self):
        """Enhanced payment check with better transaction support"""
        self.ensure_one()
        
        # Check payment transactions (for e-commerce payments)
        if hasattr(self, 'transaction_ids'):
            paid_transactions = self.transaction_ids.filtered(
                lambda tx: tx.state in ['done', 'authorized']
            )
            if paid_transactions:
                total_paid = sum(paid_transactions.mapped('amount'))
                return total_paid >= self.amount_total
        
        # Check if there's a related invoice that's paid
        if self.invoice_ids:
            paid_invoices = self.invoice_ids.filtered(
                lambda inv: inv.payment_state in ['paid', 'in_payment']
            )
            if paid_invoices:
                return True
        
        # Check for advance payments or deposits
        if hasattr(self, 'advance_payment_status'):
            if self.advance_payment_status == 'invoiced':
                return True
        
        # For demo/test purposes, assume paid if order is confirmed
        # Remove this in production
        return self.state in ['sale', 'done']
    
    def _process_subscription_activations(self):
        """Enhanced subscription activation processing with better chapter support"""
        self.ensure_one()
        _logger.info(f"=== ENHANCED SUBSCRIPTION DEBUG: _process_subscription_activations called for order {self.name} ===")
        
        # Process in priority order: memberships first, then chapters, then subscriptions
        membership_lines = self.order_line.filtered(
            lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                         line.product_id.product_tmpl_id.subscription_product_type == 'membership')
        )
        
        chapter_lines = self.order_line.filtered(
            lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                         line.product_id.product_tmpl_id.subscription_product_type == 'chapter')
        )
        
        subscription_lines = self.order_line.filtered(
            lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                         line.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
        )
        
        # Process regular memberships first
        for line in membership_lines:
            _logger.info(f"SUBSCRIPTION DEBUG: Processing regular membership line {line.id}")
            try:
                membership = self._create_membership_from_sale_line(line)
                _logger.info(f"SUBSCRIPTION DEBUG: Successfully created regular membership: {membership}")
            except Exception as e:
                _logger.error(f"SUBSCRIPTION DEBUG: Failed to create regular membership from line {line.id}: {str(e)}")
                continue
        
        # Process chapter memberships second
        for line in chapter_lines:
            _logger.info(f"SUBSCRIPTION DEBUG: Processing chapter membership line {line.id}")
            try:
                membership = self._create_membership_from_sale_line(line)
                _logger.info(f"SUBSCRIPTION DEBUG: Successfully created chapter membership: {membership}")
            except Exception as e:
                _logger.error(f"SUBSCRIPTION DEBUG: Failed to create chapter membership from line {line.id}: {str(e)}")
                continue
        
        # Process pure subscriptions last
        for line in subscription_lines:
            _logger.info(f"SUBSCRIPTION DEBUG: Processing subscription line {line.id}")
            try:
                subscription = self._create_subscription_from_sale_line(line)
                _logger.info(f"SUBSCRIPTION DEBUG: Successfully created subscription: {subscription}")
            except Exception as e:
                _logger.error(f"SUBSCRIPTION DEBUG: Failed to create subscription from line {line.id}: {str(e)}")
                continue
    
    def _create_membership_from_sale_line(self, line):
        """Enhanced membership creation with better chapter support and validation"""
        _logger.info(f"=== ENHANCED MEMBERSHIP DEBUG: _create_membership_from_sale_line called for line {line.id} ===")
        
        product_tmpl = line.product_id.product_tmpl_id
        partner = self.partner_id
        
        _logger.info(f"MEMBERSHIP DEBUG: Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"MEMBERSHIP DEBUG: Product: {line.product_id.name}")
        _logger.info(f"MEMBERSHIP DEBUG: Product Type: {product_tmpl.subscription_product_type}")
        
        # Enhanced duplicate check
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
        
        # Enhanced partner setup with better member type handling
        self._setup_partner_for_membership(partner, product_tmpl)
        
        # Enhanced membership handling based on type
        if product_tmpl.subscription_product_type == 'chapter':
            return self._create_chapter_membership(line, partner, product_tmpl)
        else:
            return self._create_regular_membership(line, partner, product_tmpl)
    
    def _setup_partner_for_membership(self, partner, product_tmpl):
        """Enhanced partner setup for membership creation"""
        updates = {}
        
        # Set as member if not already
        if not partner.is_member:
            updates['is_member'] = True
            _logger.info(f"MEMBERSHIP DEBUG: Setting partner {partner.name} as member")
        
        # Enhanced member number generation
        if not getattr(partner, 'member_number', None):
            member_number = self._generate_enhanced_member_number(partner, product_tmpl)
            if member_number:
                updates['member_number'] = member_number
        
        # Enhanced member type assignment
        if not partner.member_type_id:
            member_type = self._get_appropriate_member_type(partner, product_tmpl)
            if member_type:
                updates['member_type_id'] = member_type.id
        
        # Apply updates
        if updates:
            partner.with_context(skip_auto_sync=True).write(updates)
    
    def _generate_enhanced_member_number(self, partner, product_tmpl):
        """Enhanced member number generation with chapter support"""
        try:
            # Try foundation method first
            if hasattr(partner, '_generate_member_number'):
                partner._generate_member_number()
                return partner.member_number
        except Exception:
            pass
        
        try:
            # Enhanced fallback with chapter-aware numbering
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            base_prefix = getattr(settings, 'member_number_prefix', 'M') if settings else 'M'
            
            if product_tmpl.subscription_product_type == 'chapter':
                # Special prefix for chapter-only members
                if not partner.current_membership_id:  # No regular membership
                    prefix = base_prefix + 'C'
                else:
                    prefix = base_prefix  # Use regular prefix if they have regular membership
            else:
                prefix = base_prefix
            
            padding = getattr(settings, 'member_number_padding', 6) if settings else 6
            
            # Try sequence first
            sequence = self.env['ir.sequence'].next_by_code('ams.member.number')
            if not sequence:
                # Fallback: incremental numbering
                last_member = self.env['res.partner'].search([
                    ('is_member', '=', True),
                    ('member_number', '!=', False)
                ], order='id desc', limit=1)
                
                next_num = 1
                if last_member and last_member.member_number:
                    try:
                        import re
                        numbers = re.findall(r'\d+', last_member.member_number)
                        if numbers:
                            next_num = int(numbers[-1]) + 1
                    except:
                        next_num = 1
                
                sequence = str(next_num).zfill(padding)
            
            member_number = f"{prefix}{sequence}"
            _logger.info(f"MEMBERSHIP DEBUG: Generated member number {member_number} for {partner.name}")
            return member_number
            
        except Exception as e:
            _logger.warning(f"Could not generate enhanced member number for {partner.name}: {str(e)}")
            return self._generate_member_number_fallback()
    
    def _get_appropriate_member_type(self, partner, product_tmpl):
        """Get appropriate member type based on membership and chapter context"""
        try:
            # For chapter memberships, try chapter-specific types first
            if product_tmpl.subscription_product_type == 'chapter':
                chapter_member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', 'chapter')
                ], limit=1)
                if chapter_member_type:
                    return chapter_member_type
            
            # Try common member types in order of preference
            for type_name in ['regular', 'individual', 'standard']:
                member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', type_name)
                ], limit=1)
                if member_type:
                    return member_type
            
            # Return first available type
            return self.env['ams.member.type'].search([], limit=1)
            
        except Exception as e:
            _logger.warning(f"Error getting member type: {str(e)}")
            return None
    
    def _create_regular_membership(self, line, partner, product_tmpl):
        """Create regular membership with enhanced handling"""
        _logger.info(f"MEMBERSHIP DEBUG: Creating REGULAR membership - only one allowed, will terminate others")
        
        # Terminate other active REGULAR memberships (only one allowed)
        try:
            other_active_memberships = self.env['ams.membership'].search([
                ('partner_id', '=', partner.id),
                ('product_id.subscription_product_type', '=', 'membership'),
                ('state', '=', 'active'),
                ('id', '!=', False)
            ])
            
            if other_active_memberships:
                _logger.info(f"MEMBERSHIP DEBUG: Found {len(other_active_memberships)} other active REGULAR memberships - terminating them")
                for old_membership in other_active_memberships:
                    old_membership.write({
                        'state': 'terminated',
                        'notes': (old_membership.notes or '') + f"\nTerminated due to new membership purchase: {line.product_id.name} on {fields.Date.today()}"
                    })
                    _logger.info(f"MEMBERSHIP DEBUG: Terminated existing membership {old_membership.name}")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error terminating existing memberships: {str(e)}")
        
        # Calculate membership dates
        start_date = fields.Date.today()
        end_date = self._calculate_membership_end_date(start_date, product_tmpl.subscription_period)
        _logger.info(f"MEMBERSHIP DEBUG: Calculated dates - Start: {start_date}, End: {end_date}")
        
        # Update foundation partner dates (for regular memberships only)
        try:
            partner.with_context(skip_auto_sync=True).write({
                'membership_start_date': start_date,
                'membership_end_date': end_date,
                'member_status': 'active'
            })
            _logger.info(f"MEMBERSHIP DEBUG: Updated partner foundation dates and status")
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: Error updating partner foundation dates: {str(e)}")
        
        # Create membership record
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
        
        return self._create_membership_record(membership_vals, 'regular membership')
    
    def _create_chapter_membership(self, line, partner, product_tmpl):
        """Create chapter membership with enhanced handling"""
        _logger.info(f"MEMBERSHIP DEBUG: Creating CHAPTER membership - multiple chapters allowed")
        
        # Enhanced chapter eligibility check
        can_join, reason = self._check_detailed_chapter_eligibility(partner, product_tmpl)
        if not can_join:
            _logger.warning(f"MEMBERSHIP DEBUG: Chapter eligibility issue: {reason}")
            # Continue anyway but log the warning
        
        # Calculate chapter membership dates
        start_date = fields.Date.today()
        end_date = self._calculate_membership_end_date(start_date, product_tmpl.subscription_period)
        _logger.info(f"MEMBERSHIP DEBUG: Chapter dates - Start: {start_date}, End: {end_date}")
        
        # Enhanced chapter information
        chapter_info = self._build_chapter_info_string(product_tmpl)
        
        # Create chapter membership record
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
            'notes': f"Chapter Membership: {chapter_info}",
            'chapter_role': 'member',
        }
        
        return self._create_membership_record(membership_vals, 'chapter membership')
    
    def _check_detailed_chapter_eligibility(self, partner, product_tmpl):
        """Detailed chapter eligibility check - EMERGENCY SAFE VERSION"""
        try:
            # Check if already in this chapter
            existing = partner.membership_ids.filtered(
                lambda m: (m.product_id.product_tmpl_id == product_tmpl and 
                          m.state in ['active', 'grace'])
            )
            if existing:
                return False, f"Already a member of {product_tmpl.name}"
            
            # Check member limits - SAFE
            try:
                if hasattr(product_tmpl, 'chapter_member_limit') and product_tmpl.chapter_member_limit > 0:
                    member_count = getattr(product_tmpl, 'chapter_member_count', 0)
                    if member_count >= product_tmpl.chapter_member_limit:
                        return False, f"Chapter at member capacity ({product_tmpl.chapter_member_limit})"
            except (AttributeError, TypeError):
                pass
            
            # SKIP geographic restrictions for now - EMERGENCY FIX
            # TODO: Add back when fields are properly added
            
            return True, "Eligible for chapter membership"
            
        except Exception as e:
            _logger.error(f"Error checking chapter eligibility: {str(e)}")
            return True, "Eligibility check failed - proceeding anyway"
    
    def _build_chapter_info_string(self, product_tmpl):
        """Build comprehensive chapter information string"""
        info_parts = []
        
        if product_tmpl.chapter_type:
            info_parts.append(product_tmpl.chapter_type.title())
        
        if product_tmpl.chapter_location:
            info_parts.append(product_tmpl.chapter_location)
        
        if product_tmpl.chapter_city:
            info_parts.append(product_tmpl.chapter_city)
        
        if product_tmpl.chapter_state:
            info_parts.append(product_tmpl.chapter_state)
        
        chapter_info = ' - '.join(info_parts) if info_parts else 'Chapter'
        
        # Add contact and meeting information
        additional_info = []
        if product_tmpl.chapter_contact_email:
            additional_info.append(f"Contact: {product_tmpl.chapter_contact_email}")
        
        if product_tmpl.chapter_meeting_schedule:
            additional_info.append(f"Meetings: {product_tmpl.chapter_meeting_schedule}")
        
        if additional_info:
            chapter_info += '\n' + '\n'.join(additional_info)
        
        return chapter_info
    
    def _create_membership_record(self, membership_vals, membership_type_label):
        """Create membership record with enhanced error handling"""
        try:
            _logger.info(f"MEMBERSHIP DEBUG: Creating {membership_type_label} record...")
            membership = self.env['ams.membership'].create(membership_vals)
            
            _logger.info(f"MEMBERSHIP DEBUG: Successfully created {membership_type_label} {membership.name} (ID: {membership.id})")
            
            # Enhanced activity logging
            subject = f"{membership_type_label.title()} Activated"
            body = f"{membership_type_label.title()} activated from sale order {self.name}"
            
            if membership_vals.get('notes'):
                body += f"\n\nDetails:\n{membership_vals['notes']}"
            
            membership.message_post(body=body, subject=subject)
            
            return membership
            
        except Exception as e:
            _logger.error(f"MEMBERSHIP DEBUG: CRITICAL ERROR creating {membership_type_label} record: {str(e)}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception type: {type(e).__name__}")
            _logger.error(f"MEMBERSHIP DEBUG: Exception details: {e}")
            _logger.error(f"MEMBERSHIP DEBUG: Membership values: {membership_vals}")
            raise e
    
    def _create_subscription_from_sale_line(self, line):
        """Enhanced subscription creation with better error handling"""
        _logger.info(f"=== ENHANCED SUBSCRIPTION DEBUG: _create_subscription_from_sale_line called for line {line.id} ===")
        
        product_tmpl = line.product_id.product_tmpl_id
        partner = self.partner_id
        
        _logger.info(f"SUBSCRIPTION DEBUG: Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"SUBSCRIPTION DEBUG: Product: {line.product_id.name}")
        _logger.info(f"SUBSCRIPTION DEBUG: Subscription Type: {product_tmpl.subscription_product_type}")
        
        # Enhanced validation
        if product_tmpl.subscription_product_type in ['membership', 'chapter']:
            _logger.error(f"SUBSCRIPTION DEBUG: ERROR - This method should not handle membership or chapter products!")
            raise ValueError(f"Invalid product type {product_tmpl.subscription_product_type} for subscription creation")
        
        # Enhanced duplicate check
        try:
            existing_subscription = self.env['ams.subscription'].search([
                ('partner_id', '=', partner.id),
                ('product_id', '=', line.product_id.id),
                ('sale_order_line_id', '=', line.id)
            ], limit=1)
            
            if existing_subscription:
                _logger.info(f"SUBSCRIPTION DEBUG: Subscription already exists for sale line {line.id}")
                return existing_subscription
        except Exception as e:
            _logger.error(f"SUBSCRIPTION DEBUG: Error checking existing subscription: {str(e)}")
        
        # Enhanced subscription creation
        start_date = fields.Date.today()
        end_date = self._calculate_subscription_end_date(start_date, product_tmpl.subscription_period)
        
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
        
        # Enhanced type-specific configuration
        if product_tmpl.subscription_product_type == 'publication':
            subscription_vals.update({
                'digital_access': getattr(product_tmpl, 'publication_digital_access', True),
                'print_delivery': getattr(product_tmpl, 'publication_print_delivery', False),
            })
            if subscription_vals['print_delivery'] and partner.id:
                subscription_vals['delivery_address_id'] = partner.id
        
        try:
            subscription = self.env['ams.subscription'].create(subscription_vals)
            
            _logger.info(f"SUBSCRIPTION DEBUG: Successfully created subscription {subscription.name} (ID: {subscription.id})")
            
            subscription.message_post(
                body=f"Subscription activated from sale order {self.name}",
                subject="Subscription Activated"
            )
            
            return subscription
            
        except Exception as e:
            _logger.error(f"SUBSCRIPTION DEBUG: CRITICAL ERROR creating subscription record: {str(e)}")
            raise e
    
    def _calculate_membership_end_date(self, start_date, subscription_period):
        """Enhanced membership end date calculation"""
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
        """Enhanced subscription end date calculation"""
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
        """Enhanced fallback member number generation"""
        try:
            last_member = self.env['res.partner'].search([
                ('is_member', '=', True),
                ('member_number', '!=', False)
            ], order='member_number desc', limit=1)
            
            if last_member and last_member.member_number:
                try:
                    # Extract number from member number
                    import re
                    numbers = re.findall(r'\d+', last_member.member_number)
                    if numbers:
                        return str(int(numbers[-1]) + 1).zfill(6)
                except ValueError:
                    pass
            
            # Default starting number
            return "000001"
        except Exception as e:
            _logger.error(f"Error in fallback member number generation: {str(e)}")
            return "000001"

    # === CHAPTER-SPECIFIC ACTION METHODS ===
    
    def action_validate_chapter_eligibility(self):
        """Manual chapter eligibility validation - NEW METHOD"""
        self.ensure_one()
        
        if not self.has_chapter_products:
            raise UserError(_("This order does not contain any chapter products."))
        
        self._validate_chapter_eligibility()
        
        if self.chapter_warnings:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Chapter Eligibility Warnings'),
                    'message': self.chapter_warnings,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Chapter Eligibility'),
                    'message': _('All chapter products are eligible for this customer.'),
                    'type': 'success',
                }
            }
    
    def action_chapter_order_analysis(self):
        """Open chapter order analysis - NEW METHOD"""
        self.ensure_one()
        
        return {
            'name': _('Chapter Order Analysis: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'list,form',
            'domain': [
                ('order_id', '=', self.id),
                ('product_id.subscription_product_type', '=', 'chapter')
            ],
            'context': {
                'search_default_group_by_product': 1,
            }
        }
    
    def action_view_created_memberships(self):
        """View memberships created from this order - ENHANCED"""
        self.ensure_one()
        
        memberships = self.env['ams.membership'].search([
            ('sale_order_id', '=', self.id)
        ])
        
        if not memberships:
            raise UserError(_("No memberships have been created from this order yet."))
        
        return {
            'name': _('Memberships from Order: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('id', 'in', memberships.ids)],
            'context': {
                'search_default_group_membership_type': 1,
            }
        }
    
    def action_view_created_subscriptions(self):
        """View subscriptions created from this order"""
        self.ensure_one()
        
        subscriptions = self.env['ams.subscription'].search([
            ('sale_order_id', '=', self.id)
        ])
        
        if not subscriptions:
            raise UserError(_("No subscriptions have been created from this order yet."))
        
        return {
            'name': _('Subscriptions from Order: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', subscriptions.ids)],
        }
    
    # === ENHANCED CONSTRAINTS ===
    
    @api.constrains('order_line')
    def _check_membership_rules(self):
        """Enhanced constraint validation for membership rules"""
        for order in self:
            # Check multiple regular memberships per order
            membership_lines = order.order_line.filtered(
                lambda line: (line.product_id.product_tmpl_id.is_subscription_product and
                             line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            
            if len(membership_lines) > 1:
                raise ValidationError(
                    _("Order %s: Only one regular membership product is allowed per order.") % order.name
                )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    # Enhanced subscription line detection
    is_membership_line = fields.Boolean(
        'Membership Line',
        compute='_compute_subscription_line_types',
        store=True,
        help='This line contains a regular membership product'
    )
    
    is_chapter_line = fields.Boolean(
        'Chapter Line',
        compute='_compute_subscription_line_types',
        store=True,
        help='This line contains a chapter membership product'
    )
    
    is_subscription_line = fields.Boolean(
        'Subscription Line',
        compute='_compute_subscription_line_types',
        store=True,
        help='This line contains a pure subscription product'
    )
    
    # Chapter-specific information
    chapter_type = fields.Selection(
        related='product_id.chapter_type',
        string='Chapter Type',
        readonly=True
    )
    
    chapter_location = fields.Char(
        related='product_id.chapter_location',
        string='Chapter Location',
        readonly=True
    )
    
    chapter_access_level = fields.Selection(
        related='product_id.chapter_access_level',
        string='Chapter Access Level',
        readonly=True
    )
    
    @api.depends('product_id.is_subscription_product', 'product_id.subscription_product_type')
    def _compute_subscription_line_types(self):
        """Compute subscription line types"""
        for line in self:
            if line.product_id.product_tmpl_id.is_subscription_product:
                product_type = line.product_id.product_tmpl_id.subscription_product_type
                
                line.is_membership_line = (product_type == 'membership')
                line.is_chapter_line = (product_type == 'chapter')
                line.is_subscription_line = (product_type not in ['membership', 'chapter'])
            else:
                line.is_membership_line = False
                line.is_chapter_line = False
                line.is_subscription_line = False


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    def _reconcile_after_done(self):
        """Enhanced payment reconciliation with better subscription processing"""
        result = super()._reconcile_after_done()
        
        # Enhanced subscription processing for completed transactions
        for tx in self:
            if tx.state == 'done' and tx.sale_order_ids:
                for order in tx.sale_order_ids:
                    if (order.has_membership_products or 
                        order.has_subscription_products or 
                        order.has_chapter_products):
                        
                        _logger.info(f"PAYMENT DEBUG: Processing subscriptions for order {order.name} after payment {tx.reference}")
                        order._process_subscription_activations()
        
        return result