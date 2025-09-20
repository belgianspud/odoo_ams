# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Membership relationship fields
    membership_ids = fields.One2many(
        'membership.membership',
        'partner_id',
        string='Memberships',
        help='All memberships for this partner'
    )
    
    # Computed membership status fields
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_membership_status',
        store=True,
        help='True if partner has any active membership'
    )
    
    active_membership_id = fields.Many2one(
        'membership.membership',
        string='Active Membership',
        compute='_compute_membership_status',
        store=True,
        help='Current active membership (parent membership if multiple)'
    )
    
    membership_state = fields.Selection(
        related='active_membership_id.state',
        string='Membership Status',
        store=True
    )
    
    membership_type_id = fields.Many2one(
        related='active_membership_id.membership_type_id',
        string='Membership Type',
        store=True
    )
    
    membership_expiry_date = fields.Date(
        related='active_membership_id.end_date',
        string='Membership Expires',
        store=True
    )
    
    # Statistics
    membership_count = fields.Integer(
        string='Total Memberships',
        compute='_compute_membership_statistics'
    )
    
    active_membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_membership_statistics'
    )
    
    total_membership_paid = fields.Float(
        string='Total Membership Fees Paid',
        compute='_compute_membership_statistics',
        digits='Product Price'
    )
    
    @api.depends('membership_ids.state')
    def _compute_membership_status(self):
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state in ['active', 'grace']
            )
            
            if active_memberships:
                partner.is_member = True
                # Prioritize parent memberships over chapters
                parent_membership = active_memberships.filtered(
                    lambda m: m.membership_type_id.membership_category in ['individual', 'organization']
                )
                partner.active_membership_id = parent_membership[0] if parent_membership else active_memberships[0]
            else:
                partner.is_member = False
                partner.active_membership_id = False
    
    @api.depends('membership_ids')
    def _compute_membership_statistics(self):
        for partner in self:
            memberships = partner.membership_ids
            partner.membership_count = len(memberships)
            partner.active_membership_count = len(memberships.filtered(
                lambda m: m.state in ['active', 'grace']
            ))
            partner.total_membership_paid = sum(memberships.mapped('amount_paid'))
    
    def action_view_memberships(self):
        """Open partner's memberships"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships - %s') % self.name,
            'res_model': 'membership.membership',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_membership_revenue(self):
        """View membership revenue analysis for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Revenue - %s') % self.name,
            'res_model': 'membership.membership',
            'view_mode': 'pivot,graph,tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'search_default_group_by_membership_type_id': 1,
                'search_default_group_by_state': 1,
            }
        }
    
    def get_membership_history(self):
        """Get complete membership history for partner"""
        return self.membership_ids.sorted('start_date', reverse=True)
    
    def has_active_membership_type(self, membership_type_id):
        """Check if partner has active membership of specific type"""
        return bool(self.membership_ids.filtered(
            lambda m: m.membership_type_id.id == membership_type_id and m.state in ['active', 'grace']
        ))
    
    def create_membership(self, membership_type_id, start_date=None, amount_paid=0.0):
        """Create a new membership for this partner"""
        membership_type = self.env['membership.type'].browse(membership_type_id)
        
        # Check for existing parent membership conflicts
        if membership_type.membership_category in ['individual', 'organization']:
            existing_parent = self.membership_ids.filtered(
                lambda m: m.state in ['active', 'grace'] and 
                m.membership_type_id.membership_category in ['individual', 'organization']
            )
            if existing_parent:
                raise ValidationError(
                    _("Partner %s already has an active parent membership (%s). "
                      "Cannot create another parent membership.") % 
                    (self.name, existing_parent[0].membership_type_id.name)
                )
        
        # Create membership
        membership_vals = {
            'partner_id': self.id,
            'membership_type_id': membership_type_id,
            'start_date': start_date or fields.Date.today(),
            'amount_paid': amount_paid or membership_type.price,
            'state': 'draft'
        }
        
        membership = self.env['membership.membership'].create(membership_vals)
        return membership
    
    def get_membership_benefits(self):
        """Get all benefits available to this partner through active memberships"""
        active_memberships = self.membership_ids.filtered(
            lambda m: m.state in ['active', 'grace']
        )
        
        all_benefits = self.env['membership.benefit']
        for membership in active_memberships:
            if hasattr(membership, 'available_benefit_ids'):
                all_benefits |= membership.available_benefit_ids
        
        return all_benefits
    
    def is_membership_expired(self):
        """Check if partner's primary membership is expired"""
        if not self.active_membership_id:
            return True
        
        if not self.active_membership_id.end_date:
            return False  # Lifetime membership
        
        return self.active_membership_id.end_date < fields.Date.today()
    
    def get_membership_renewal_info(self):
        """Get renewal information for partner's active membership"""
        if not self.active_membership_id:
            return None
        
        membership = self.active_membership_id
        
        return {
            'membership_id': membership.id,
            'membership_type': membership.membership_type_id.name,
            'current_expiry': membership.end_date,
            'days_until_expiry': membership.get_days_until_expiry(),
            'renewal_price': membership.membership_type_id.get_renewal_price(membership),
            'auto_renewal': membership.auto_renewal,
            'is_expiring_soon': membership.is_expiring_soon()
        }
    
    def get_membership_summary(self):
        """Get a summary of partner's membership information"""
        self.ensure_one()
        
        summary = {
            'is_member': self.is_member,
            'total_memberships': self.membership_count,
            'active_memberships': self.active_membership_count,
            'total_paid': self.total_membership_paid,
            'current_membership': None,
            'membership_history': []
        }
        
        if self.active_membership_id:
            summary['current_membership'] = {
                'name': self.active_membership_id.name,
                'type': self.active_membership_id.membership_type_id.name,
                'state': self.active_membership_id.state,
                'start_date': self.active_membership_id.start_date,
                'end_date': self.active_membership_id.end_date,
                'days_until_expiry': self.active_membership_id.get_days_until_expiry(),
            }
        
        # Get membership history
        for membership in self.membership_ids.sorted('start_date', reverse=True):
            summary['membership_history'].append({
                'name': membership.name,
                'type': membership.membership_type_id.name,
                'state': membership.state,
                'start_date': membership.start_date,
                'end_date': membership.end_date,
                'amount_paid': membership.amount_paid,
            })
        
        return summary