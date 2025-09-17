# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Enterprise Account Seat Management
    total_seats_available = fields.Integer(
        string='Total Seats Available',
        help='Total number of seats purchased for this enterprise account',
        compute='_compute_seat_totals',
        store=True
    )
    
    seats_used = fields.Integer(
        string='Seats Used',
        help='Number of seats currently assigned to employees',
        compute='_compute_seat_totals',
        store=True
    )
    
    seats_remaining = fields.Integer(
        string='Seats Remaining',
        help='Number of unassigned seats available',
        compute='_compute_seat_totals',
        store=True
    )

    # Membership Relationships
    individual_subscription_ids = fields.One2many(
        'ams.subscription',
        'partner_id',
        string='Individual Subscriptions',
        domain=[('subscription_type', '!=', 'enterprise')],
        help='All non-enterprise subscriptions for this contact'
    )
    
    enterprise_subscription_ids = fields.One2many(
        'ams.subscription',
        'account_id',
        string='Enterprise Subscriptions',
        domain=[('subscription_type', '=', 'enterprise')],
        help='Enterprise subscriptions where this is the account'
    )
    
    enterprise_seat_ids = fields.One2many(
        'ams.subscription.seat',
        'contact_id',
        string='Enterprise Seat Assignments',
        help='Enterprise seats assigned to this contact'
    )

    # Computed Membership Status
    is_active_member = fields.Boolean(
        string='Is Active Member',
        compute='_compute_membership_status',
        store=True,
        help='Has at least one active subscription'
    )
    
    membership_types = fields.Char(
        string='Membership Types',
        compute='_compute_membership_status',
        store=True,
        help='Summary of active membership types'
    )

    @api.depends('enterprise_subscription_ids.total_seats', 'enterprise_seat_ids.active')
    def _compute_seat_totals(self):
        for partner in self:
            if partner.is_company:
                # Sum all seats from enterprise subscriptions
                total_seats = sum(partner.enterprise_subscription_ids.mapped('total_seats'))
                
                # Count active seat assignments
                used_seats = len(partner.enterprise_seat_ids.filtered('active'))
                
                partner.total_seats_available = total_seats
                partner.seats_used = used_seats
                partner.seats_remaining = total_seats - used_seats
            else:
                partner.total_seats_available = 0
                partner.seats_used = 0
                partner.seats_remaining = 0

    @api.depends('individual_subscription_ids.state', 'enterprise_seat_ids.active')
    def _compute_membership_status(self):
        for partner in self:
            # Check individual subscriptions
            active_individual = partner.individual_subscription_ids.filtered(lambda s: s.state == 'active')
            
            # Check enterprise seat assignments
            active_enterprise_seats = partner.enterprise_seat_ids.filtered('active')
            
            # Determine if member is active
            partner.is_active_member = bool(active_individual or active_enterprise_seats)
            
            # Build membership types summary
            membership_types = []
            if active_individual:
                types = list(set(active_individual.mapped('subscription_type')))
                membership_types.extend(types)
            if active_enterprise_seats:
                membership_types.append('enterprise')
            
            partner.membership_types = ', '.join(membership_types) if membership_types else 'None'

    def action_view_subscriptions(self):
        """Action to view all subscriptions for this partner"""
        self.ensure_one()
        
        # Combine individual subscriptions and enterprise subscriptions where this partner is the account
        domain = [
            '|', 
            ('partner_id', '=', self.id),
            ('account_id', '=', self.id)
        ]
        
        return {
            'name': f'Subscriptions for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.id,
                'default_account_id': self.id if self.is_company else False
            }
        }
    
    def action_assign_enterprise_seat(self):
        """Action to assign an enterprise seat to this contact"""
        self.ensure_one()
        
        if self.is_company:
            raise UserError("Cannot assign seats to company accounts. Assign to individual contacts instead.")
        
        # Find available enterprise subscriptions for the parent company
        account = self.parent_id if self.parent_id else self
        
        available_subs = self.env['ams.subscription'].search([
            ('account_id', '=', account.id),
            ('subscription_type', '=', 'enterprise'),
            ('state', '=', 'active')
        ])
        
        if not available_subs:
            raise UserError(f"No active enterprise subscriptions found for account {account.name}")
        
        return {
            'name': 'Assign Enterprise Seat',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.seat',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contact_id': self.id,
                'default_subscription_id': available_subs[0].id if len(available_subs) == 1 else False
            }
        }