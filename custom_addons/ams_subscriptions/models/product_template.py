# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Enhanced product template for subscription lifecycle management.
    Inherits from ams_products_base for product behavior and billing integration.
    """
    _inherit = 'product.template'

    # ========================================================================
    # SUBSCRIPTION LIFECYCLE FIELDS (not in base module)
    # ========================================================================
    
    # Customer self-service options
    allow_customer_pause = fields.Boolean(
        string='Allow Customer Pause',
        default=True,
        help='Allow customers to pause this subscription via portal'
    )
    
    allow_customer_modifications = fields.Boolean(
        string='Allow Customer Modifications', 
        default=True,
        help='Allow customers to upgrade/downgrade via portal'
    )
    
    allow_customer_cancellation = fields.Boolean(
        string='Allow Customer Cancellation',
        default=True,
        help='Allow customers to cancel this subscription via portal'
    )
    
    # Lifecycle automation settings
    auto_suspend_on_failure = fields.Boolean(
        string='Auto-Suspend on Payment Failure',
        default=False,
        help='Automatically suspend subscription after payment failures'
    )
    
    max_payment_retries = fields.Integer(
        string='Max Payment Retries',
        default=3,
        help='Maximum number of payment retry attempts'
    )
    
    # Approval workflows
    requires_activation_approval = fields.Boolean(
        string='Requires Activation Approval',
        default=False,
        help='New subscriptions need staff approval before activation'
    )
    
    requires_modification_approval = fields.Boolean(
        string='Requires Modification Approval', 
        default=False,
        help='Subscription changes need staff approval'
    )
    
    # Enterprise seat management (for enterprise subscriptions)
    default_seat_allocation = fields.Integer(
        string='Default Seat Allocation',
        default=1,
        help='Default number of seats for enterprise subscriptions'
    )
    
    max_additional_seats = fields.Integer(
        string='Max Additional Seats',
        default=0,
        help='Maximum additional seats that can be purchased (0 = unlimited)'
    )
    
    # Advanced subscription settings
    proration_policy = fields.Selection([
        ('none', 'No Proration'),
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('full_month', 'Full Month Billing'),
    ], string='Proration Policy', default='daily',
       help='How to handle mid-cycle billing changes')
    
    cancellation_refund_policy = fields.Selection([
        ('none', 'No Refunds'),
        ('prorated', 'Prorated Refund'),
        ('full_period', 'Full Period Refund'),
        ('admin_review', 'Admin Review Required'),
    ], string='Cancellation Refund Policy', default='admin_review',
       help='Refund policy for subscription cancellations')

    # ========================================================================
    # ENHANCED STATISTICS (computed from subscription records)
    # ========================================================================
    
    total_subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_subscription_stats',
        help='Total number of subscriptions ever created for this product'
    )
    
    active_subscription_count = fields.Integer(
        string='Active Subscriptions', 
        compute='_compute_subscription_stats',
        help='Currently active subscriptions'
    )
    
    churned_subscription_count = fields.Integer(
        string='Churned Subscriptions',
        compute='_compute_subscription_stats', 
        help='Cancelled or terminated subscriptions'
    )
    
    subscription_revenue_ytd = fields.Monetary(
        string='Subscription Revenue YTD',
        compute='_compute_subscription_stats',
        help='Year-to-date revenue from this subscription product'
    )
    
    average_subscription_lifetime = fields.Float(
        string='Avg Subscription Lifetime (Months)',
        compute='_compute_subscription_stats',
        help='Average lifetime of subscriptions for this product'
    )

    # ========================================================================
    # COMPUTED METHODS
    # ========================================================================
    
    @api.depends('name')  # Dummy dependency - real implementation would depend on subscription records
    def _compute_subscription_stats(self):
        """Compute subscription statistics from ams.subscription records"""
        for product in self:
            if not product.is_subscription_product:
                product.total_subscription_count = 0
                product.active_subscription_count = 0
                product.churned_subscription_count = 0
                product.subscription_revenue_ytd = 0.0
                product.average_subscription_lifetime = 0.0
                continue
                
            # Get all subscriptions for this product
            subscriptions = self.env['ams.subscription'].search([
                ('product_id.product_tmpl_id', '=', product.id)
            ])
            
            # Calculate statistics
            product.total_subscription_count = len(subscriptions)
            product.active_subscription_count = len(subscriptions.filtered(
                lambda s: s.state == 'active'
            ))
            product.churned_subscription_count = len(subscriptions.filtered(
                lambda s: s.state in ['terminated', 'cancelled']
            ))
            
            # Calculate revenue (simplified - could integrate with accounting)
            active_subs = subscriptions.filtered(lambda s: s.state == 'active')
            product.subscription_revenue_ytd = len(active_subs) * product.list_price
            
            # Calculate average lifetime (simplified)
            terminated_subs = subscriptions.filtered(lambda s: s.state == 'terminated')
            if terminated_subs:
                total_days = sum([
                    (sub.paid_through_date - sub.start_date).days 
                    for sub in terminated_subs 
                    if sub.start_date and sub.paid_through_date
                ])
                product.average_subscription_lifetime = (total_days / len(terminated_subs)) / 30.0
            else:
                product.average_subscription_lifetime = 0.0

    # ========================================================================
    # ONCHANGE METHODS (enhance base module behavior)
    # ========================================================================
    
    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior_subscriptions(self):
        """Extend base module onchange for subscription-specific setup"""
        result = super()._onchange_ams_product_behavior()
        
        if self.ams_product_behavior == 'subscription':
            # Set subscription lifecycle defaults
            self.allow_customer_pause = True
            self.allow_customer_modifications = True
            self.allow_customer_cancellation = True
            self.proration_policy = 'daily'
            self.cancellation_refund_policy = 'admin_review'
            
            # Ensure is_subscription_product is set
            self.is_subscription_product = True
            
        elif self.ams_product_behavior == 'membership':
            # Membership-specific defaults
            self.allow_customer_pause = False  # Memberships typically can't be paused
            self.allow_customer_modifications = True
            self.allow_customer_cancellation = True
            self.proration_policy = 'none'     # Annual membership billing
            self.cancellation_refund_policy = 'prorated'
            
            self.is_subscription_product = True
            
        elif self.ams_product_behavior in ['event', 'digital', 'publication']:
            # These can be subscription products too
            if self.is_subscription_product:
                self.allow_customer_pause = True
                self.allow_customer_modifications = True
                self.proration_policy = 'daily'
        
        return result

    @api.onchange('default_billing_period_id')
    def _onchange_billing_period_subscription(self):
        """Set lifecycle defaults based on billing period"""
        if self.default_billing_period_id:
            period = self.default_billing_period_id
            
            # Set grace period based on billing cycle
            if hasattr(period, 'duration_unit'):
                if period.duration_unit == 'days':
                    suggested_grace = min(7, period.duration_value)
                elif period.duration_unit == 'weeks': 
                    suggested_grace = period.duration_value * 2
                elif period.duration_unit == 'months':
                    suggested_grace = min(30, period.duration_value * 5)
                else:  # years
                    suggested_grace = 30
                    
                # Update grace period if using base module lifecycle settings
                if hasattr(self, 'grace_days') and not self.grace_days:
                    self.grace_days = suggested_grace

    # ========================================================================
    # SUBSCRIPTION CREATION METHODS (enhanced to use base modules)
    # ========================================================================
    
    def create_subscription_from_sale(self, sale_line, partner=None):
        """
        Enhanced subscription creation using ams_products_base and ams_billing_periods.
        
        Args:
            sale_line (sale.order.line): Sale order line
            partner (res.partner, optional): Partner override
            
        Returns:
            ams.subscription: Created subscription record
        """
        self.ensure_one()
        
        # Validate this is a subscription product using base module
        if not self.is_subscription_product:
            return False
            
        if self.ams_product_behavior not in ['subscription', 'membership']:
            _logger.warning(f"Product {self.name} has behavior {self.ams_product_behavior} but is marked as subscription")
        
        partner = partner or sale_line.order_id.partner_id
        start_date = fields.Date.today()
        
        # Use ams_billing_periods for date calculation
        if self.default_billing_period_id:
            end_date = self.default_billing_period_id.calculate_period_end(start_date)
            period_name = self.default_billing_period_id.name
        else:
            # Fallback to annual if no billing period set
            from dateutil.relativedelta import relativedelta
            end_date = start_date + relativedelta(years=1) - relativedelta(days=1)
            period_name = "Annual"
            _logger.warning(f"No billing period set for subscription product {self.name}")
        
        # Determine subscription type from product behavior
        subscription_type = self._get_subscription_type_from_behavior()
        
        # Calculate seats for enterprise subscriptions
        base_seats = self.default_seat_allocation if subscription_type == 'enterprise' else 0
        
        # Create subscription using enhanced data
        subscription_vals = {
            'name': self._generate_subscription_name(partner, period_name),
            'partner_id': partner.id,
            'account_id': partner.parent_id.id if partner.parent_id else partner.id,
            'product_id': sale_line.product_id.id,
            'subscription_type': subscription_type,
            'tier_id': False,  # Could be set from product configuration
            'start_date': start_date,
            'paid_through_date': end_date,
            'state': 'active' if not self.requires_activation_approval else 'draft',
            'sale_order_id': sale_line.order_id.id,
            'sale_order_line_id': sale_line.id,
            'base_seats': base_seats,
            'extra_seats': 0,
            'auto_renew': True,
            'is_free': self.list_price == 0,
            'allow_modifications': self.allow_customer_modifications,
            'allow_pausing': self.allow_customer_pause,
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        # Log creation with billing period info
        subscription.message_post(
            body=f"Subscription created from sale order {sale_line.order_id.name}. "
                 f"Billing period: {period_name}. "
                 f"Paid through: {end_date}"
        )
        
        # Update partner subscription tracking (from base module)
        self._update_partner_subscription_info(partner, subscription)
        
        return subscription

    def _get_subscription_type_from_behavior(self):
        """Map product behavior to subscription type"""
        behavior_mapping = {
            'membership': 'individual',
            'subscription': 'individual', 
            'event': 'individual',
            'publication': 'publication',
            'digital': 'individual',
            'certification': 'individual',
        }
        
        # Check if this should be enterprise based on other factors
        if self.default_seat_allocation > 1:
            return 'enterprise'
            
        return behavior_mapping.get(self.ams_product_behavior, 'individual')

    def _generate_subscription_name(self, partner, period_name):
        """Generate descriptive subscription name"""
        year = fields.Date.today().year
        base_name = f"{partner.name} - {self.name}"
        
        if period_name:
            base_name += f" ({period_name} {year})"
        else:
            base_name += f" ({year})"
            
        return base_name

    def _update_partner_subscription_info(self, partner, subscription):
        """Update partner with current subscription info"""
        if subscription.subscription_type == 'individual':
            partner.current_individual_subscription_id = subscription.id
        elif subscription.subscription_type == 'enterprise':
            partner.current_enterprise_subscription_id = subscription.id

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================
    
    @api.constrains('default_seat_allocation', 'max_additional_seats')
    def _check_seat_allocation(self):
        """Validate seat allocation settings"""
        for product in self:
            if product.default_seat_allocation < 0:
                raise ValidationError(_("Default seat allocation cannot be negative"))
                
            if product.max_additional_seats < 0:
                raise ValidationError(_("Max additional seats cannot be negative"))

    @api.constrains('max_payment_retries')
    def _check_payment_retries(self):
        """Validate payment retry settings"""
        for product in self:
            if product.max_payment_retries < 0:
                raise ValidationError(_("Max payment retries cannot be negative"))
                
            if product.max_payment_retries > 10:
                raise ValidationError(_("Max payment retries should not exceed 10"))

    # ========================================================================
    # ACTION METHODS (enhanced with base module integration)
    # ========================================================================
    
    def action_view_subscriptions(self):
        """Enhanced action to view subscriptions with better filtering"""
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
                'show_subscription_stats': True,
            }
        }

    def action_configure_subscription_lifecycle(self):
        """Open subscription lifecycle configuration wizard"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError(_("This product is not configured as a subscription product"))
            
        return {
            'type': 'ir.actions.act_window',
            'name': f'Configure Subscription Lifecycle: {self.name}',
            'res_model': 'product.template',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_view_mode': 'subscription_lifecycle',
            }
        }

    def action_subscription_analytics(self):
        """Open subscription analytics dashboard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Subscription Analytics: {self.name}',
            'res_model': 'ams.subscription.analytics',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            }
        }

    # ========================================================================
    # INTEGRATION HELPERS
    # ========================================================================
    
    def get_subscription_lifecycle_config(self):
        """Get complete subscription lifecycle configuration"""
        self.ensure_one()
        
        return {
            'customer_controls': {
                'allow_pause': self.allow_customer_pause,
                'allow_modifications': self.allow_customer_modifications,
                'allow_cancellation': self.allow_customer_cancellation,
            },
            'automation': {
                'auto_suspend_on_failure': self.auto_suspend_on_failure,
                'max_payment_retries': self.max_payment_retries,
            },
            'approvals': {
                'requires_activation_approval': self.requires_activation_approval,
                'requires_modification_approval': self.requires_modification_approval,
            },
            'billing': {
                'proration_policy': self.proration_policy,
                'cancellation_refund_policy': self.cancellation_refund_policy,
                'billing_period_id': self.default_billing_period_id.id if self.default_billing_period_id else None,
            },
            'enterprise': {
                'default_seats': self.default_seat_allocation,
                'max_additional_seats': self.max_additional_seats,
            }
        }

    def validate_subscription_configuration(self):
        """Validate complete subscription configuration"""
        self.ensure_one()
        
        issues = []
        
        if not self.is_subscription_product:
            return issues
            
        # Check required base module configuration
        if not self.default_billing_period_id:
            issues.append("Missing billing period configuration")
            
        if self.ams_product_behavior not in ['subscription', 'membership']:
            issues.append(f"Product behavior '{self.ams_product_behavior}' may not be suitable for subscriptions")
            
        # Check lifecycle configuration
        if self.requires_activation_approval and not self.allow_customer_modifications:
            issues.append("Products requiring activation approval should typically allow modifications")
            
        return issues