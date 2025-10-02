# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionPlan(models.Model):
    """
    Extend Subscription Plan with Seat Management for Organizational Memberships
    """
    _inherit = 'subscription.plan'

    # ==========================================
    # SEAT CONFIGURATION - For Organizational Memberships
    # ==========================================
    
    supports_seats = fields.Boolean(
        string='Supports Multiple Seats',
        default=False,
        help='This plan allows multiple seat subscriptions (for organizational memberships)'
    )
    
    included_seats = fields.Integer(
        string='Included Seats',
        default=1,
        help='Number of seats included in base price'
    )
    
    max_seats = fields.Integer(
        string='Maximum Seats',
        default=0,
        help='Maximum seats allowed (0 = unlimited)'
    )
    
    additional_seat_price = fields.Float(
        string='Additional Seat Price',
        help='Price per additional seat beyond included seats'
    )
    
    seat_product_id = fields.Many2one(
        'product.template',
        string='Seat Add-on Product',
        domain=[('is_membership_product', '=', True)],
        help='Product used for additional seat purchases'
    )
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    total_allocated_seats = fields.Integer(
        string='Total Allocated Seats',
        compute='_compute_seat_statistics',
        help='Total number of seats allocated across all subscriptions'
    )
    
    active_seat_subscriptions = fields.Integer(
        string='Active Seat Subscriptions',
        compute='_compute_seat_statistics',
        help='Number of active seat subscriptions'
    )

    @api.depends('subscription_ids', 'subscription_ids.child_subscription_ids')
    def _compute_seat_statistics(self):
        """Calculate seat allocation statistics"""
        for plan in self:
            if plan.supports_seats:
                # Get all active parent subscriptions for this plan
                parent_subs = plan.subscription_ids.filtered(
                    lambda s: s.state in ['trial', 'active'] and not s.parent_subscription_id
                )
                
                # Count total allocated seats
                total_seats = sum(parent_subs.mapped('allocated_seat_count'))
                plan.total_allocated_seats = total_seats
                
                # Count active seat subscriptions
                seat_subs = parent_subs.mapped('child_subscription_ids').filtered(
                    lambda s: s.state in ['trial', 'active']
                )
                plan.active_seat_subscriptions = len(seat_subs)
            else:
                plan.total_allocated_seats = 0
                plan.active_seat_subscriptions = 0

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('included_seats', 'max_seats')
    def _check_seat_configuration(self):
        """Validate seat configuration"""
        for plan in self:
            if plan.supports_seats:
                if plan.included_seats <= 0:
                    raise ValidationError(_(
                        'Plans that support seats must include at least 1 seat.'
                    ))
                
                if plan.max_seats > 0 and plan.max_seats < plan.included_seats:
                    raise ValidationError(_(
                        'Maximum seats (%s) cannot be less than included seats (%s).'
                    ) % (plan.max_seats, plan.included_seats))
    
    @api.constrains('additional_seat_price')
    def _check_additional_seat_price(self):
        """Validate additional seat price"""
        for plan in self:
            if plan.supports_seats and plan.additional_seat_price < 0:
                raise ValidationError(_(
                    'Additional seat price cannot be negative.'
                ))

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_seat_price(self, quantity=1):
        """
        Calculate price for additional seats
        
        Args:
            quantity: Number of additional seats
        
        Returns:
            float: Total price for additional seats
        """
        self.ensure_one()
        
        if not self.supports_seats:
            return 0.0
        
        # Calculate seats beyond included
        additional_seats = max(0, quantity - self.included_seats)
        
        return additional_seats * self.additional_seat_price
    
    def check_seat_availability(self, subscription_id, requested_seats=1):
        """
        Check if seats are available for allocation
        
        Args:
            subscription_id: ID of parent subscription
            requested_seats: Number of seats requested
        
        Returns:
            tuple: (bool: available, str: message)
        """
        self.ensure_one()
        
        if not self.supports_seats:
            return (False, _('This plan does not support multiple seats'))
        
        subscription = self.env['subscription.subscription'].browse(subscription_id)
        
        if not subscription:
            return (False, _('Subscription not found'))
        
        if subscription.available_seat_count < requested_seats:
            return (False, _(
                'Only %s seats available. Requested: %s'
            ) % (subscription.available_seat_count, requested_seats))
        
        return (True, '')
    
    def action_view_seat_subscriptions(self):
        """View all seat subscriptions for this plan"""
        self.ensure_one()
        
        # Get all parent subscriptions
        parent_subs = self.subscription_ids.filtered(
            lambda s: not s.parent_subscription_id
        )
        
        # Get all child seat subscriptions
        seat_subs = parent_subs.mapped('child_subscription_ids')
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', seat_subs.ids)],
            'context': {
                'default_plan_id': self.id,
            }
        }

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('supports_seats')
    def _onchange_supports_seats(self):
        """Set defaults when enabling seat support"""
        if self.supports_seats:
            if not self.included_seats or self.included_seats <= 0:
                self.included_seats = 5
            if not self.max_seats:
                self.max_seats = self.included_seats
            
            # Calculate suggested seat price (20% of base price per seat)
            if not self.additional_seat_price and self.price > 0 and self.included_seats > 0:
                self.additional_seat_price = (self.price / self.included_seats) * 1.2
    
    @api.onchange('included_seats', 'price')
    def _onchange_calculate_seat_price(self):
        """Auto-calculate additional seat price based on base price"""
        if self.supports_seats and self.price > 0 and self.included_seats > 0:
            if not self.additional_seat_price:
                # Suggest 20% premium over pro-rated base price
                base_per_seat = self.price / self.included_seats
                self.additional_seat_price = base_per_seat * 1.2