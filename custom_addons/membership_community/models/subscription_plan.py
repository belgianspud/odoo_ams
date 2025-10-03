# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionPlan(models.Model):
    """
    Subscription Plan - Membership Community Extensions
    ENHANCED: Now supports lifetime memberships and seat management
    """
    _inherit = 'subscription.plan'

    # ==========================================
    # MEMBERSHIP-SPECIFIC ADDITIONS ONLY
    # ==========================================
    
    # NEW: Computed lifetime flag based on billing period
    is_lifetime = fields.Boolean(
        string='Lifetime Membership',
        compute='_compute_is_lifetime',
        store=True,
        help='One-time payment, never expires'
    )
    
    @api.depends('billing_period')
    def _compute_is_lifetime(self):
        """Determine if this is a lifetime plan"""
        for plan in self:
            plan.is_lifetime = (plan.billing_period == 'lifetime')

    # NEW: Seat product for purchasing additional seats
    seat_product_id = fields.Many2one(
        'product.template',
        string='Seat Add-on Product',
        domain=[('is_membership_product', '=', True), ('provides_seats', '=', True)],
        help='Optional product for purchasing additional seats (seat packs)'
    )
    
    # NEW: Seat Statistics (computed from subscriptions)
    total_allocated_seats = fields.Integer(
        string='Total Allocated Seats',
        compute='_compute_seat_statistics',
        help='Total seats allocated across all subscriptions'
    )
    
    active_seat_subscriptions = fields.Integer(
        string='Active Seat Subscriptions',
        compute='_compute_seat_statistics',
        help='Number of active seat subscriptions'
    )
    
    @api.depends('subscription_ids', 'subscription_ids.allocated_seat_count',
                 'subscription_ids.child_subscription_ids')
    def _compute_seat_statistics(self):
        """Calculate seat allocation statistics"""
        for plan in self:
            if plan.supports_seats:
                active_subs = plan.subscription_ids.filtered(
                    lambda s: s.state in ('active', 'trial')
                )
                plan.total_allocated_seats = sum(active_subs.mapped('allocated_seat_count'))
                
                # Count all child subscriptions (seat subscriptions)
                plan.active_seat_subscriptions = len(
                    active_subs.mapped('child_subscription_ids')
                )
            else:
                plan.total_allocated_seats = 0
                plan.active_seat_subscriptions = 0

    # ==========================================
    # BUSINESS METHODS - ENHANCED
    # ==========================================

    def get_billing_frequency_display(self):
        """Get human-readable billing frequency"""
        self.ensure_one()
        
        if self.is_lifetime:
            return _('One-time payment')
        
        if self.billing_interval == 1:
            return dict(self._fields['billing_period'].selection)[self.billing_period]
        else:
            return _('Every %s %s') % (
                self.billing_interval,
                dict(self._fields['billing_period'].selection)[self.billing_period]
            )

    def calculate_next_billing_date(self, start_date):
        """
        Calculate next billing date based on plan configuration
        
        Args:
            start_date: Starting date for calculation
            
        Returns:
            date: Next billing date, or False for lifetime plans
        """
        self.ensure_one()
        
        # Lifetime plans never have a next billing date
        if self.is_lifetime:
            return False
        
        # Use parent method for regular billing
        return super().get_next_billing_date(start_date)

    def action_view_seat_subscriptions(self):
        """Action to view seat subscriptions for this plan"""
        self.ensure_one()
        
        # Get all parent subscriptions for this plan
        parent_subs = self.subscription_ids.filtered(
            lambda s: s.state in ('active', 'trial') and s.supports_seats
        )
        
        # Get all child (seat) subscriptions
        seat_subs = parent_subs.mapped('child_subscription_ids')
        
        return {
            'name': _('Seat Subscriptions - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', seat_subs.ids)],
            'context': {
                'default_plan_id': self.id,
                'search_default_active': 1,
            },
        }

    def name_get(self):
        """Custom display name"""
        result = []
        for plan in self:
            name = plan.name
            if plan.code:
                name = f"[{plan.code}] {name}"
            if plan.is_lifetime:
                name = f"{name} (Lifetime)"
            result.append((plan.id, name))
        return result

    # ==========================================
    # CONSTRAINTS - MEMBERSHIP-SPECIFIC
    # ==========================================
    
    @api.constrains('billing_period', 'auto_renew')
    def _check_lifetime_auto_renew(self):
        """Lifetime plans cannot auto-renew"""
        for plan in self:
            if plan.is_lifetime and plan.auto_renew:
                raise ValidationError(_(
                    'Lifetime plans cannot have auto-renewal enabled. '
                    'Lifetime memberships are one-time payments that never expire.'
                ))
    
    @api.constrains('billing_period', 'billing_interval')
    def _check_lifetime_interval(self):
        """Lifetime plans must have interval of 1"""
        for plan in self:
            if plan.is_lifetime and plan.billing_interval != 1:
                raise ValidationError(_(
                    'Lifetime plans must have a billing interval of 1.'
                ))

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================
    
    @api.onchange('billing_period')
    def _onchange_billing_period(self):
        """Handle lifetime selection"""
        if self.billing_period == 'lifetime':
            # Disable auto-renew for lifetime plans
            self.auto_renew = False
            self.billing_interval = 1
            
            # Clear trial period (doesn't make sense for lifetime)
            self.trial_period = 0
            self.trial_price = 0.0