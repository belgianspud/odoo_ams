# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # === MEMBERSHIP CORE EXTENSIONS ===
    # Add subscription-specific fields that don't conflict with foundation
    
    # Membership Records (real data - stored in membership_core)
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
    
    # Current Active Records (computed from real data)
    current_membership_id = fields.Many2one(
        'ams.membership',
        string='Current Membership',
        compute='_compute_current_membership',
        store=True,
        help='Current active membership (only one allowed)'
    )
    
    active_subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id',
        string='Active Subscriptions',
        domain=[('state', '=', 'active')],
        help='All currently active subscriptions'
    )
    
    # Benefits (computed from active memberships/subscriptions)
    active_benefit_ids = fields.Many2many(
        'ams.benefit',
        string='Active Benefits',
        compute='_compute_active_benefits',
        help='All benefits currently available to this member'
    )
    
    # Renewal Information (computed and stored for search)
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_renewal_info',
        store=True,
        help='Next upcoming renewal date'
    )
    
    pending_renewals_count = fields.Integer(
        string='Pending Renewals',
        compute='_compute_renewal_info',
        store=True,
        help='Number of pending renewal reminders'
    )
    
    # Statistics (computed and stored for search)
    total_membership_years = fields.Float(
        string='Total Membership Years',
        compute='_compute_membership_stats',
        store=True,
        help='Total years of membership history'
    )
    
    subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_subscription_stats',
        store=True,
        help='Total number of subscriptions (all time)'
    )

    # === COMPUTED METHODS ===
    
    @api.depends('membership_ids.state')
    def _compute_current_membership(self):
        """Compute current active membership"""
        for partner in self:
            active_membership = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            partner.current_membership_id = active_membership[0] if active_membership else False
            
            # Sync with foundation's member status
            if active_membership and partner.member_status != 'active':
                # Update foundation status to match membership core reality
                partner.with_context(skip_auto_sync=True).write({
                    'member_status': 'active',
                    'membership_start_date': active_membership[0].start_date,
                    'membership_end_date': active_membership[0].end_date,
                })
            elif not active_membership and partner.is_member and partner.member_status == 'active':
                # Check for grace period memberships
                grace_membership = partner.membership_ids.filtered(
                    lambda m: m.state == 'grace'
                )
                if grace_membership:
                    partner.with_context(skip_auto_sync=True).write({
                        'member_status': 'grace'
                    })
                else:
                    partner.with_context(skip_auto_sync=True).write({
                        'member_status': 'lapsed'
                    })
    
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
            
            # Convert to recordset
            partner.active_benefit_ids = [(6, 0, list(benefit_ids))]
    
    @api.depends('membership_ids.next_renewal_date', 'subscription_ids.next_renewal_date')
    def _compute_renewal_info(self):
        """Compute renewal information"""
        for partner in self:
            renewal_dates = []
            
            # Collect renewal dates
            if partner.current_membership_id and partner.current_membership_id.next_renewal_date:
                renewal_dates.append(partner.current_membership_id.next_renewal_date)
            
            for subscription in partner.active_subscription_ids:
                if subscription.next_renewal_date:
                    renewal_dates.append(subscription.next_renewal_date)
            
            # Find the next upcoming renewal
            partner.next_renewal_date = min(renewal_dates) if renewal_dates else False
            
            # Count pending renewals
            pending_renewals = self.env['ams.renewal'].search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['draft', 'pending'])
            ])
            partner.pending_renewals_count = pending_renewals
    
    @api.depends('membership_ids.start_date', 'membership_ids.end_date')
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
    
    @api.depends('subscription_ids')
    def _compute_subscription_stats(self):
        """Compute subscription statistics"""
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)

    # === ACTION METHODS ===
    
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

    # === BENEFIT MANAGEMENT ===
    
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
        
        return min(total_discount, original_amount)
    
    def record_benefit_usage(self, benefit_code, quantity=1, notes=None):
        """Record usage of a specific benefit"""
        self.ensure_one()
        
        benefit = self.active_benefit_ids.filtered(lambda b: b.code == benefit_code)
        if not benefit:
            raise UserError(_("Benefit '%s' not available for this member.") % benefit_code)
        
        return benefit[0].record_usage(self.id, quantity, notes)

    # === INTEGRATION WITH FOUNDATION ===
    
    def write(self, vals):
        """Override write to handle membership status sync"""
        # Handle foundation status changes and sync with membership core
        result = super().write(vals)
        
        # Skip auto-sync if called from membership core to avoid recursion
        if self.env.context.get('skip_auto_sync'):
            return result
        
        # Sync member status changes from foundation to membership records
        if 'member_status' in vals:
            for partner in self:
                partner._sync_member_status_to_memberships(vals['member_status'])
        
        return result
    
    def _sync_member_status_to_memberships(self, new_status):
        """Sync member status changes to membership records"""
        self.ensure_one()
        
        if new_status == 'terminated' and self.current_membership_id:
            self.current_membership_id.write({'state': 'terminated'})
        
        elif new_status == 'suspended':
            if self.current_membership_id:
                self.current_membership_id.write({'state': 'suspended'})
            
            # Also suspend active subscriptions
            for subscription in self.active_subscription_ids:
                subscription.write({'state': 'suspended'})
        
        elif new_status == 'active' and self.current_membership_id:
            if self.current_membership_id.state in ['grace', 'suspended']:
                self.current_membership_id.write({'state': 'active'})

    # === PORTAL ACCESS ENHANCEMENT ===
    
    @api.depends('current_membership_id', 'active_subscription_ids')
    def _compute_portal_access(self):
        """Enhanced portal access computation"""
        # Call foundation method first
        if hasattr(super(), '_compute_portal_access'):
            super()._compute_portal_access()
        
        for partner in self:
            # Additional check for subscription-based portal access
            if not partner.has_portal_access:
                grant_portal = False
                
                # Check if current membership grants portal access
                if (partner.current_membership_id and 
                    partner.current_membership_id.product_id.grant_portal_access):
                    grant_portal = True
                
                # Check if any active subscription grants portal access
                for subscription in partner.active_subscription_ids:
                    if subscription.product_id.grant_portal_access:
                        grant_portal = True
                        break
                
                if grant_portal and partner.email:
                    try:
                        partner.action_create_portal_user()
                    except Exception as e:
                        _logger.warning(f"Failed to create portal user for {partner.name}: {str(e)}")

    # === CONSTRAINTS ===
    
    @api.constrains('membership_ids')
    def _check_single_active_membership(self):
        """Ensure only one active membership per member (foundation rule)"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            if len(active_memberships) > 1:
                raise ValidationError(
                    _("Member %s has multiple active memberships. "
                      "Only one active membership is allowed per member.") % partner.name
                )

    def action_create_portal_user(self):
        """Create portal user for this partner"""
        self.ensure_one()
    
        if self.portal_user_id:
            raise UserError(_("Portal user already exists for this partner."))
    
        if not self.email:
            raise UserError(_("Partner must have an email address to create portal user."))
    
        # Check if foundation has the method, otherwise use basic implementation
        if hasattr(super(), 'action_create_portal_user'):
            return super().action_create_portal_user()
        else:
            # Basic portal user creation
            portal_group = self.env.ref('base.group_portal')
            user_vals = {
                'name': self.name,
                'login': self.email,
                'email': self.email,
                'partner_id': self.id,
                'groups_id': [(6, 0, [portal_group.id])],
                'active': True,
            }
        
            user = self.env['res.users'].create(user_vals)
            self.portal_user_id = user.id
        
            return {
                'type': 'ir.actions.act_window',
                'name': _('Portal User'),
                'res_model': 'res.users',
                'res_id': user.id,
                'view_mode': 'form',
            }