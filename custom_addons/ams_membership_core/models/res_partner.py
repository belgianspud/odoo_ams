# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Membership Records
    membership_ids = fields.One2many(
        'ams.membership',
        'partner_id',
        string='Memberships',
        help='All membership records for this member'
    )
    
    subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id', 
        string='Subscriptions',
        help='All subscription records for this member'
    )
    
    # Current Active Records
    current_membership_id = fields.Many2one(
        'ams.membership',
        string='Current Membership',
        compute='_compute_current_records',
        store=True,
        help='Current active membership (only one allowed)'
    )
    
    active_subscription_ids = fields.Many2many(
        'ams.subscription',
        string='Active Subscriptions',
        compute='_compute_current_records',
        store=True,
        help='All currently active subscriptions'
    )
    
    # Membership Status (enhanced from ams_foundation)
    has_active_membership = fields.Boolean(
        string='Has Active Membership',
        compute='_compute_membership_status',
        store=True,
        help='Has at least one active membership'
    )
    
    has_active_subscriptions = fields.Boolean(
        string='Has Active Subscriptions',
        compute='_compute_membership_status',
        store=True,
        help='Has at least one active subscription'
    )
    
    # Benefits
    active_benefit_ids = fields.Many2many(
        'ams.benefit',
        string='Active Benefits',
        compute='_compute_active_benefits',
        help='All benefits currently available to this member'
    )
    
    # Renewal Information
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_renewal_info',
        store=True,
        help='Next upcoming renewal date'
    )
    
    renewal_reminders_count = fields.Integer(
        string='Pending Renewals',
        compute='_compute_renewal_info',
        store=True,
        help='Number of pending renewal reminders'
    )
    
    # Statistics
    total_membership_years = fields.Float(
        string='Total Membership Years',
        compute='_compute_membership_stats',
        help='Total years of membership history'
    )
    
    membership_renewal_count = fields.Integer(
        string='Membership Renewals',
        compute='_compute_membership_stats',
        help='Total number of membership renewals'
    )
    
    subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_subscription_stats',
        help='Total number of subscriptions (all time)'
    )
    
    @api.depends('membership_ids.state', 'subscription_ids.state')
    def _compute_current_records(self):
        """Compute current active membership and subscriptions"""
        for partner in self:
            # Find current active membership (should only be one)
            active_membership = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            partner.current_membership_id = active_membership[0] if active_membership else False
            
            # Find all active subscriptions
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.state == 'active'
            )
            partner.active_subscription_ids = [(6, 0, active_subscriptions.ids)]
    
    @api.depends('current_membership_id', 'active_subscription_ids')
    def _compute_membership_status(self):
        """Compute membership status flags"""
        for partner in self:
            partner.has_active_membership = bool(partner.current_membership_id)
            partner.has_active_subscriptions = bool(partner.active_subscription_ids)
            
            # Update the base member_status from ams_foundation if needed
            if partner.is_member:
                if partner.has_active_membership:
                    if partner.member_status != 'active':
                        partner.member_status = 'active'
                elif partner.member_status == 'active':
                    # Check if in grace period or should be lapsed
                    grace_memberships = partner.membership_ids.filtered(
                        lambda m: m.state == 'grace'
                    )
                    if grace_memberships:
                        partner.member_status = 'grace'
                    else:
                        partner.member_status = 'lapsed'
    
    def _compute_active_benefits(self):
        """Compute all active benefits for this member"""
        for partner in self:
            benefit_ids = set()
            
            # Benefits from active membership
            if partner.current_membership_id:
                benefit_ids.update(partner.current_membership_id.benefit_ids.ids)
            
            # Benefits from active subscriptions
            for subscription in partner.active_subscription_ids:
                benefit_ids.update(subscription.benefit_ids.ids)
            
            partner.active_benefit_ids = [(6, 0, list(benefit_ids))]
    
    @api.depends('membership_ids.next_renewal_date', 'subscription_ids.next_renewal_date')
    def _compute_renewal_info(self):
        """Compute renewal information"""
        for partner in self:
            renewal_dates = []
            
            # Collect renewal dates from memberships and subscriptions
            if partner.current_membership_id and partner.current_membership_id.next_renewal_date:
                renewal_dates.append(partner.current_membership_id.next_renewal_date)
            
            for subscription in partner.active_subscription_ids:
                if subscription.next_renewal_date:
                    renewal_dates.append(subscription.next_renewal_date)
            
            # Find the next upcoming renewal
            if renewal_dates:
                partner.next_renewal_date = min(renewal_dates)
            else:
                partner.next_renewal_date = False
            
            # Count pending renewals
            pending_renewals = self.env['ams.renewal'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['draft', 'pending'])
            ])
            partner.renewal_reminders_count = pending_renewals
    
    def _compute_membership_stats(self):
        """Compute membership statistics"""
        for partner in self:
            # Calculate total membership years
            total_days = 0
            for membership in partner.membership_ids:
                if membership.start_date and membership.end_date:
                    days = (membership.end_date - membership.start_date).days
                    total_days += days
            
            partner.total_membership_years = total_days / 365.25 if total_days > 0 else 0.0
            
            # Count renewals
            partner.membership_renewal_count = len(partner.membership_ids.mapped('renewal_ids'))
    
    def _compute_subscription_stats(self):
        """Compute subscription statistics"""
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)
    
    # Action Methods
    def action_create_membership(self):
        """Create new membership for this partner"""
        self.ensure_one()
        
        if not self.is_member:
            raise UserError(_("This contact is not marked as a member."))
        
        return {
            'name': _('Create Membership'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_create_subscription(self):
        """Create new subscription for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Create Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_view_memberships(self):
        """View all memberships for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Memberships: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_subscriptions(self):
        """View all subscriptions for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Subscriptions: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_renewals(self):
        """View renewal history for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Renewals: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.renewal',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_benefits(self):
        """View active benefits for this partner"""
        self.ensure_one()
        
        return {
            'name': _('Active Benefits: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.benefit',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.active_benefit_ids.ids)],
        }
    
    def action_renew_membership(self):
        """Quick action to renew current membership"""
        self.ensure_one()
        
        if not self.current_membership_id:
            raise UserError(_("No active membership to renew."))
        
        return self.current_membership_id.action_renew()
    
    def action_upgrade_membership(self):
        """Open membership upgrade wizard"""
        self.ensure_one()
        
        if not self.current_membership_id:
            raise UserError(_("No active membership to upgrade."))
        
        return {
            'name': _('Upgrade Membership'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.current_membership_id.id,
                'default_partner_id': self.id,
            }
        }
    
    # Benefit Management
    def has_benefit(self, benefit_code):
        """Check if member has a specific benefit"""
        self.ensure_one()
        return any(benefit.code == benefit_code for benefit in self.active_benefit_ids)
    
    def get_discount_amount(self, original_amount, benefit_codes=None):
        """Calculate total discount amount from active benefits"""
        self.ensure_one()
        
        total_discount = 0.0
        
        for benefit in self.active_benefit_ids:
            if benefit.benefit_type != 'discount':
                continue
            
            # Filter by benefit codes if specified
            if benefit_codes and benefit.code not in benefit_codes:
                continue
            
            discount = benefit.get_discount_amount(original_amount)
            total_discount += discount
        
        return min(total_discount, original_amount)  # Don't exceed original amount
    
    def record_benefit_usage(self, benefit_code, quantity=1, notes=None):
        """Record usage of a specific benefit"""
        self.ensure_one()
        
        benefit = self.active_benefit_ids.filtered(lambda b: b.code == benefit_code)
        if not benefit:
            raise UserError(_("Benefit '%s' not available for this member.") % benefit_code)
        
        return benefit[0].record_usage(self.id, quantity, notes)
    
    # Portal Integration
    def _compute_portal_access(self):
        """Override from ams_foundation to include subscription-based access"""
        super()._compute_portal_access()
        
        for partner in self:
            if not partner.has_portal_access:
                # Check if should have portal access based on subscriptions
                if (partner.has_active_membership or partner.has_active_subscriptions):
                    # Check if any active products grant portal access
                    products_with_portal = set()
                    
                    if partner.current_membership_id:
                        if partner.current_membership_id.product_id.grant_portal_access:
                            products_with_portal.add(partner.current_membership_id.product_id.id)
                    
                    for subscription in partner.active_subscription_ids:
                        if subscription.product_id.grant_portal_access:
                            products_with_portal.add(subscription.product_id.id)
                    
                    if products_with_portal:
                        # Should have portal access - try to create it
                        try:
                            partner.action_create_portal_user()
                        except Exception as e:
                            _logger.warning(f"Failed to auto-create portal user for {partner.name}: {str(e)}")
    
    # Override member status transitions to handle membership/subscription integration
    def write(self, vals):
        """Override write to sync membership status changes"""
        result = super().write(vals)
        
        # Handle member status changes
        if 'member_status' in vals:
            for partner in self:
                partner._sync_membership_status_change(vals['member_status'])
        
        return result
    
    def _sync_membership_status_change(self, new_status):
        """Sync member status changes with membership records"""
        self.ensure_one()
        
        if new_status == 'terminated' and self.current_membership_id:
            # Terminate active membership
            self.current_membership_id.action_terminate()
        
        elif new_status == 'suspended':
            # Suspend active membership and subscriptions
            if self.current_membership_id:
                self.current_membership_id.action_suspend()
            
            for subscription in self.active_subscription_ids:
                subscription.action_suspend()
        
        elif new_status == 'active':
            # Reactivate if was suspended
            grace_membership = self.membership_ids.filtered(
                lambda m: m.state in ['grace', 'suspended']
            )
            if grace_membership:
                grace_membership[0].write({'state': 'active'})
    
    # Constraints
    @api.constrains('membership_ids')
    def _check_single_active_membership(self):
        """Ensure only one active membership per member"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            if len(active_memberships) > 1:
                raise ValidationError(
                    _("Member %s has multiple active memberships. Only one active membership is allowed per member.") % partner.name
                )