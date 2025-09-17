# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Enhanced product template for subscription lifecycle management.
    
    Layer 2 Architecture:
    - Inherits from ams_products_base for product behavior and billing integration
    - Focuses on subscription lifecycle management, not product configuration
    - Uses ams_billing_periods for accurate date calculations
    - Provides hooks for subscription creation and management
    """
    _inherit = 'product.template'

    # ========================================================================
    # SUBSCRIPTION LIFECYCLE FIELDS (Layer 2 - not in base module)
    # ========================================================================
    
    # Remove duplicate fields that are now in ams_products_base
    # These will come from inheritance:
    # - is_subscription_product (from base)
    # - ams_product_behavior (from base) 
    # - default_billing_period_id (from base)
    # - member_price, member_savings (from base)
    # - grants_portal_access (from base)
    
    # OLD FIELDS REMOVED/DEPRECATED (now handled by ams_products_base)
    ams_product_type = fields.Selection([
        ('none', 'Not an AMS Product'),
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
    ], string='AMS Product Type (Deprecated)', 
       default='none',
       help='DEPRECATED: Use ams_product_behavior from ams_products_base instead')
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'), 
        ('annual', 'Annual'),
    ], string='Subscription Period (Deprecated)',
       default='annual',
       help='DEPRECATED: Use default_billing_period_id from ams_products_base instead')
    
    # Subscription tier configuration
    subscription_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Default Subscription Tier',
        help='Default tier for subscriptions created from this product'
    )
    
    # Customer self-service permissions (Layer 2 - subscription management)
    allow_mid_cycle_changes = fields.Boolean(
        string='Allow Mid-Cycle Changes',
        default=True,
        help='Allow customers to modify subscription mid-billing-cycle'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Customer Pausing',
        default=True,
        help='Allow customers to pause their subscription via portal'
    )
    
    # Billing and proration policies (Layer 2 - subscription specific)
    proration_policy = fields.Selection([
        ('none', 'No Proration'),
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
    ], string='Proration Policy',
       default='daily',
       help='How to handle billing when subscription changes mid-cycle')
    
    # Enterprise seat management (Layer 2 - subscription specific)
    is_seat_addon = fields.Boolean(
        string='Enterprise Seat Add-On',
        default=False,
        help='This product adds seats to existing enterprise subscriptions'
    )
    
    default_seat_count = fields.Integer(
        string='Default Seats',
        default=1,
        help='Default number of seats for enterprise subscriptions'
    )
    
    # Publication-specific fields (Layer 2 - subscription specific)
    is_digital = fields.Boolean(
        string='Digital Publication',
        default=False,
        help='This is a digital publication (no physical shipping)'
    )
    
    publication_type = fields.Selection([
        ('magazine', 'Magazine'),
        ('journal', 'Journal'),
        ('newsletter', 'Newsletter'),
        ('report', 'Report'),
    ], string='Publication Type',
       help='Type of publication for subscription management')
    
    # Lifecycle management (Layer 2 - subscription specific)
    grace_days = fields.Integer(
        string='Grace Period (Days)', 
        default=30,
        help='Days after expiration before moving to suspended state'
    )
    
    suspend_days = fields.Integer(
        string='Suspension Period (Days)',
        default=60, 
        help='Days in suspension before permanent termination'
    )
    
    terminate_days = fields.Integer(
        string='Termination Period (Days)',
        default=30,
        help='Days until subscription is permanently deleted'
    )

    # ========================================================================
    # STATISTICS AND COMPUTED FIELDS (Layer 2)
    # ========================================================================
    
    active_subscriptions_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_statistics',
        store=True,
        help='Number of currently active subscriptions for this product'
    )
    
    total_revenue_ytd = fields.Monetary(
        string='Revenue YTD',
        compute='_compute_subscription_statistics',
        store=True,
        help='Year-to-date revenue from subscriptions for this product'
    )
    
    # Payment failure tracking (Layer 2 - subscription specific)
    nsf_flag = fields.Boolean(
        string='Has Payment Issues',
        compute='_compute_payment_statistics',
        store=True,
        help='This product has subscriptions with recent payment failures'
    )
    
    last_payment_failure_date = fields.Date(
        string='Last Payment Failure',
        compute='_compute_payment_statistics',
        store=True,
        help='Most recent payment failure for subscriptions of this product'
    )

    # ========================================================================
    # COMPUTED METHODS (Layer 2)
    # ========================================================================
    
    @api.depends('name')  # Dummy dependency - real implementation would track subscription records
    def _compute_subscription_statistics(self):
        """Compute subscription statistics from ams.subscription records"""
        for product in self:
            # Only compute for subscription products
            if not product.is_subscription_product:
                product.active_subscriptions_count = 0
                product.total_revenue_ytd = 0.0
                continue
                
            # Get subscriptions for all variants of this product template
            subscriptions = self.env['ams.subscription'].search([
                ('product_id.product_tmpl_id', '=', product.id)
            ])
            
            # Count active subscriptions
            active_subscriptions = subscriptions.filtered(lambda s: s.state == 'active')
            product.active_subscriptions_count = len(active_subscriptions)
            
            # Calculate YTD revenue (simplified - could integrate with accounting)
            current_year = date.today().year
            ytd_subscriptions = subscriptions.filtered(
                lambda s: s.start_date and s.start_date.year == current_year
            )
            product.total_revenue_ytd = len(ytd_subscriptions) * product.list_price
    
    @api.depends('name')  # Dummy dependency - real implementation would track payment history
    def _compute_payment_statistics(self):
        """Compute payment failure statistics"""
        for product in self:
            if not product.is_subscription_product:
                product.nsf_flag = False
                product.last_payment_failure_date = False
                continue
                
            # Get recent payment failures for this product's subscriptions
            thirty_days_ago = fields.Date.today() - timedelta(days=30)
            
            payment_failures = self.env['ams.payment.history'].search([
                ('subscription_id.product_id.product_tmpl_id', '=', product.id),
                ('payment_status', 'in', ['failed', 'nsf']),
                ('failure_date', '>=', thirty_days_ago)
            ])
            
            product.nsf_flag = bool(payment_failures)
            if payment_failures:
                product.last_payment_failure_date = max(payment_failures.mapped('failure_date'))
            else:
                product.last_payment_failure_date = False

    # ========================================================================
    # ONCHANGE METHODS (Layer 2 - enhance base module behavior)
    # ========================================================================
    
    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior_subscriptions(self):
        """
        Extend base module onchange for subscription-specific setup.
        This enhances the behavior from ams_products_base.
        """
        # Call parent onchange first (from ams_products_base)
        result = super()._onchange_ams_product_behavior()
        
        if not hasattr(super(), '_onchange_ams_product_behavior'):
            _logger.warning("ams_products_base not found - subscription behavior may not work correctly")
        
        # Add subscription lifecycle defaults based on behavior
        if self.ams_product_behavior == 'membership':
            # Membership-specific subscription defaults
            self.allow_mid_cycle_changes = False  # Memberships typically annual
            self.allow_pausing = False            # Memberships don't pause
            self.proration_policy = 'none'        # Annual billing
            self.grace_days = 30
            self.suspend_days = 60
            self.terminate_days = 90              # Longer for membership recovery
            
        elif self.ams_product_behavior == 'subscription':
            # General subscription defaults  
            self.allow_mid_cycle_changes = True
            self.allow_pausing = True
            self.proration_policy = 'daily'
            self.grace_days = 15
            self.suspend_days = 30
            self.terminate_days = 30
            
        elif self.ams_product_behavior == 'publication':
            # Publication-specific defaults
            self.allow_mid_cycle_changes = True
            self.allow_pausing = True  
            self.proration_policy = 'monthly'     # Publications bill monthly/quarterly
            self.is_digital = False               # Default to physical
            self.publication_type = 'magazine'
            
        return result
    
    @api.onchange('default_billing_period_id')
    def _onchange_billing_period_subscription_lifecycle(self):
        """
        Set lifecycle defaults based on billing period from ams_billing_periods.
        This integrates with the base module's billing period functionality.
        """
        if self.default_billing_period_id:
            period = self.default_billing_period_id
            
            # Set grace period based on billing frequency
            if hasattr(period, 'period_unit') and hasattr(period, 'period_value'):
                if period.period_unit == 'month':
                    if period.period_value == 1:      # Monthly
                        suggested_grace = 7
                    elif period.period_value <= 3:    # Quarterly
                        suggested_grace = 15
                    else:                             # Semi-annual+
                        suggested_grace = 30
                elif period.period_unit == 'year':
                    suggested_grace = 30
                else:
                    suggested_grace = 15
                    
                # Only update if not manually set
                if not self.grace_days or self.grace_days == 30:  # Default value
                    self.grace_days = suggested_grace
                    self.suspend_days = suggested_grace * 2
                    self.terminate_days = suggested_grace

    # ========================================================================
    # SUBSCRIPTION CREATION METHODS (Layer 2 - Enhanced with base integration)
    # ========================================================================
    
    def create_subscription_from_sale_order_line(self, sale_line):
        """
        Create subscription from sale order line using ams_products_base integration.
        
        This is the main method for subscription creation in Layer 2.
        It uses the base module for product configuration and billing periods for dates.
        
        Args:
            sale_line (sale.order.line): Sale order line containing product purchase
            
        Returns:
            ams.subscription: Created subscription or False if not applicable
        """
        self.ensure_one()
        
        # Validate this is a subscription product using base module
        if not self.is_subscription_product:
            _logger.debug(f"Product {self.name} is not a subscription product - skipping subscription creation")
            return False
        
        # Check if this is a seat add-on product
        if self.is_seat_addon:
            return self._handle_seat_addon_purchase(sale_line)
        
        # Standard subscription creation
        return self._create_standard_subscription(sale_line)
    
    def _handle_seat_addon_purchase(self, sale_line):
        """Handle purchase of seat add-on products"""
        partner = sale_line.order_id.partner_id
        quantity = int(sale_line.product_uom_qty)
        
        # Find active enterprise subscription for this partner
        enterprise_sub = self.env['ams.subscription'].search([
            '|', 
            ('partner_id', '=', partner.id),
            ('account_id', '=', partner.id), 
            ('subscription_type', '=', 'enterprise'),
            ('state', '=', 'active'),
        ], limit=1)
        
        if not enterprise_sub:
            raise UserError(f"No active enterprise subscription found for {partner.name}. "
                          f"Purchase an enterprise membership first before adding seats.")
        
        # Add seats to existing subscription
        enterprise_sub.extra_seats += quantity
        enterprise_sub.message_post(
            body=f"Added {quantity} seats via sale order {sale_line.order_id.name}. "
                 f"Total seats now: {enterprise_sub.total_seats}"
        )
        
        _logger.info(f"Added {quantity} seats to subscription {enterprise_sub.id}")
        return enterprise_sub
    
    def _create_standard_subscription(self, sale_line):
        """Create standard subscription using enhanced Layer 2 integration"""
        partner = sale_line.order_id.partner_id
        start_date = fields.Date.today()
        
        # Use ams_billing_periods for accurate date calculation
        if self.default_billing_period_id:
            try:
                end_date = self.default_billing_period_id.calculate_period_end(start_date)
                period_name = self.default_billing_period_id.name
            except AttributeError:
                _logger.warning(f"Billing period {self.default_billing_period_id.name} missing calculate_period_end method")
                # Fallback to annual
                end_date = start_date + relativedelta(years=1) - relativedelta(days=1)
                period_name = "Annual (fallback)"
        else:
            # Fallback if no billing period configured
            end_date = start_date + relativedelta(years=1) - relativedelta(days=1)
            period_name = "Annual (no billing period)"
            _logger.warning(f"No billing period set for subscription product {self.name}")
        
        # Determine subscription type from product behavior (base module)
        subscription_type = self._map_behavior_to_subscription_type()
        
        # Calculate enterprise seats
        base_seats = self.default_seat_count if subscription_type == 'enterprise' else 0
        
        # Create subscription with enhanced configuration
        subscription_vals = {
            'name': self._generate_subscription_name(partner, period_name),
            'partner_id': partner.id,
            'account_id': partner.parent_id.id if partner.parent_id else partner.id,
            'product_id': sale_line.product_id.id,
            'subscription_type': subscription_type,
            'tier_id': self.subscription_tier_id.id if self.subscription_tier_id else False,
            'start_date': start_date,
            'paid_through_date': end_date,
            'state': 'active',
            'sale_order_id': sale_line.order_id.id,
            'sale_order_line_id': sale_line.id,
            'base_seats': base_seats,
            'extra_seats': 0,
            'auto_renew': True,
            'is_free': self.list_price == 0.0,
            'allow_modifications': self.allow_mid_cycle_changes,
            'allow_pausing': self.allow_pausing,
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        # Log creation with billing integration info
        subscription.message_post(
            body=f"Subscription created from sale order {sale_line.order_id.name}. "
                 f"Using billing period: {period_name}. "
                 f"Paid through: {end_date}. "
                 f"Product behavior: {self.ams_product_behavior}"
        )
        
        # Update partner current subscription tracking
        self._update_partner_current_subscriptions(partner, subscription)
        
        _logger.info(f"Created subscription {subscription.id} for {partner.name} using enhanced Layer 2 integration")
        return subscription
    
    def _map_behavior_to_subscription_type(self):
        """Map ams_product_behavior (from base) to subscription_type"""
        behavior_mapping = {
            'membership': 'individual',
            'subscription': 'publication',
            'publication': 'publication',
            'event': 'individual',       # Events create individual subscriptions
            'digital': 'individual',
            'certification': 'individual',
            'donation': 'individual',    # Donations can create honorary memberships
        }
        
        # Check for enterprise indicators
        if (self.default_seat_count > 1 or 
            'enterprise' in self.name.lower() or 
            'corporate' in self.name.lower()):
            return 'enterprise'
        
        return behavior_mapping.get(self.ams_product_behavior, 'individual')
    
    def _generate_subscription_name(self, partner, period_name):
        """Generate descriptive subscription name using base module info"""
        year = date.today().year
        
        # Use product behavior from base module for naming
        behavior_names = {
            'membership': 'Membership',
            'subscription': 'Subscription',
            'publication': 'Publication',
            'event': 'Event Access',
            'digital': 'Digital Access',
            'certification': 'Certification',
            'donation': 'Honorary Membership',
        }
        
        behavior_name = behavior_names.get(self.ams_product_behavior, 'Subscription')
        base_name = f"{partner.name} - {behavior_name}"
        
        # Add year and period
        if period_name and period_name != 'Annual':
            base_name += f" ({period_name} {year})"
        else:
            base_name += f" ({year})"
            
        return base_name
    
    def _update_partner_current_subscriptions(self, partner, subscription):
        """Update partner's current subscription tracking"""
        if subscription.subscription_type == 'individual':
            partner.current_individual_subscription_id = subscription.id
        elif subscription.subscription_type == 'enterprise':
            partner.current_enterprise_subscription_id = subscription.id

    # ========================================================================
    # VALIDATION METHODS (Layer 2)
    # ========================================================================
    
    @api.constrains('ams_product_type', 'ams_product_behavior')
    def _check_product_type_behavior_consistency(self):
        """Ensure consistency between old and new product type systems"""
        for product in self:
            # If using old system, warn about migration
            if (product.ams_product_type != 'none' and 
                not product.ams_product_behavior and 
                product.is_subscription_product):
                
                raise ValidationError(_(
                    "Product '%s' uses deprecated ams_product_type field. "
                    "Please set ams_product_behavior from ams_products_base module."
                ) % product.name)
    
    @api.constrains('is_seat_addon', 'ams_product_behavior')
    def _check_seat_addon_configuration(self):
        """Validate seat add-on configuration"""
        for product in self:
            if product.is_seat_addon and product.ams_product_behavior != 'membership':
                raise ValidationError(_(
                    "Seat add-on products must have 'membership' behavior type."
                ))
    
    @api.constrains('grace_days', 'suspend_days', 'terminate_days')
    def _check_lifecycle_periods(self):
        """Validate lifecycle period configuration"""
        for product in self:
            if product.grace_days < 0 or product.suspend_days < 0 or product.terminate_days < 0:
                raise ValidationError(_("Lifecycle periods must be non-negative"))
                
            if (product.grace_days > 365 or product.suspend_days > 365 or 
                product.terminate_days > 365):
                raise ValidationError(_("Lifecycle periods should not exceed 365 days"))

    # ========================================================================
    # ACTION METHODS (Layer 2 - Enhanced subscription management)
    # ========================================================================
    
    def action_view_subscriptions(self):
        """Enhanced action to view subscriptions with Layer 2 filtering"""
        self.ensure_one()
        
        return {
            'name': f'Subscriptions: {self.name}',
            'type': 'ir.actions.act_window', 
            'res_model': 'ams.subscription',
            'view_mode': 'kanban,tree,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id,
                'search_default_active': 1,
                'search_default_group_by_state': 1,
                'product_behavior': self.ams_product_behavior,
                'billing_period_id': self.default_billing_period_id.id if self.default_billing_period_id else False,
            }
        }
    
    def action_configure_subscription_tier(self):
        """Create or configure subscription tier for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError(_("This product is not configured as a subscription product"))
        
        if self.subscription_tier_id:
            # Open existing tier
            return {
                'type': 'ir.actions.act_window',
                'name': f'Subscription Tier: {self.subscription_tier_id.name}',
                'res_model': 'ams.subscription.tier',
                'res_id': self.subscription_tier_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Create new tier
            return {
                'type': 'ir.actions.act_window',
                'name': f'Create Tier for {self.name}',
                'res_model': 'ams.subscription.tier',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_name': f"{self.name} Tier",
                    'default_subscription_type': self._map_behavior_to_subscription_type(),
                    'default_period_length': self.subscription_period if hasattr(self, 'subscription_period') else 'annual',
                    'default_grace_days': self.grace_days,
                    'default_suspend_days': self.suspend_days,
                    'default_terminate_days': self.terminate_days,
                    'product_template_id': self.id,
                }
            }

    # ========================================================================
    # INTEGRATION HELPERS (Layer 2)
    # ========================================================================
    
    def get_subscription_lifecycle_configuration(self):
        """Get complete subscription lifecycle configuration for integration"""
        self.ensure_one()
        
        return {
            # Base module configuration
            'product_behavior': self.ams_product_behavior,
            'is_subscription': self.is_subscription_product,
            'billing_period_id': self.default_billing_period_id.id if self.default_billing_period_id else None,
            'member_pricing': {
                'member_price': self.member_price,
                'member_savings': self.member_savings,
                'grants_portal_access': self.grants_portal_access,
            },
            
            # Layer 2 subscription lifecycle configuration
            'lifecycle': {
                'allow_mid_cycle_changes': self.allow_mid_cycle_changes,
                'allow_pausing': self.allow_pausing,
                'proration_policy': self.proration_policy,
                'grace_days': self.grace_days,
                'suspend_days': self.suspend_days, 
                'terminate_days': self.terminate_days,
            },
            
            # Enterprise configuration
            'enterprise': {
                'is_seat_addon': self.is_seat_addon,
                'default_seats': self.default_seat_count,
            },
            
            # Publication configuration
            'publication': {
                'is_digital': self.is_digital,
                'publication_type': self.publication_type,
            },
            
            # Statistics
            'statistics': {
                'active_subscriptions': self.active_subscriptions_count,
                'revenue_ytd': self.total_revenue_ytd,
                'has_payment_issues': self.nsf_flag,
            }
        }