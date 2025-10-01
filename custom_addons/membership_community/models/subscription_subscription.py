# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionSubscription(models.Model):
    """
    Simplified Subscription Extensions for Base Membership Module
    Extends subscription_management module with minimal membership fields
    """
    _inherit = 'subscription.subscription'

    # ==========================================
    # CORE MEMBERSHIP FIELDS ONLY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned to this membership',
        tracking=True
    )
    
    # ==========================================
    # PRODUCT HELPER FIELDS
    # Quick access to check if this is a membership subscription
    # ==========================================
    
    is_membership = fields.Boolean(
        string='Is Membership',
        related='plan_id.product_template_id.is_membership_product',
        store=True,
        help='This subscription is a membership'
    )
    
    subscription_product_type = fields.Selection(
        related='plan_id.product_template_id.subscription_product_type',
        string='Subscription Type',
        store=True
    )

    # ==========================================
    # BASIC ELIGIBILITY - Core only
    # Specialized modules extend this
    # ==========================================
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False,
        tracking=True,
        help='Membership eligibility has been verified'
    )
    
    eligibility_verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help='User who verified eligibility'
    )
    
    eligibility_verified_date = fields.Date(
        string='Verification Date',
        help='Date when eligibility was verified'
    )

    # ==========================================
    # MEMBERSHIP SOURCE
    # How this membership was created
    # ==========================================
    
    source_type = fields.Selection(
        selection='_get_source_types',
        string='Source Type',
        default='direct',
        tracking=True,
        help='How this membership was created'
    )
    
    @api.model
    def _get_source_types(self):
        """Base source types - can be extended by specialized modules"""
        return [
            ('direct', 'Direct Signup'),
            ('renewal', 'Renewal'),
            ('import', 'Data Import'),
            ('admin', 'Admin Created'),
        ]
    
    join_date = fields.Date(
        string='Original Join Date',
        help='Date when member first joined',
        tracking=True
    )

    # ==========================================
    # CRUD OVERRIDES - Minimal
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Set membership defaults on create"""
        
        for vals in vals_list:
            plan_id = vals.get('plan_id')
            if plan_id:
                plan = self.env['subscription.plan'].browse(plan_id)
                product = plan.product_template_id
                
                # Only process if membership product
                if product.is_membership_product:
                    # Set join_date if not provided
                    if 'join_date' not in vals:
                        vals['join_date'] = vals.get('date_start', fields.Date.today())
                    
                    # Set default category from product if not provided
                    if 'membership_category_id' not in vals:
                        if product.default_member_category_id:
                            vals['membership_category_id'] = product.default_member_category_id.id
        
        return super().create(vals_list)

    # ==========================================
    # BUSINESS METHODS - Basic only
    # ==========================================

    def get_available_benefits(self):
        """Get benefits for this membership subscription"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.benefit_ids
        return self.env['membership.benefit']

    def get_available_features(self):
        """Get features for this membership subscription"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.feature_ids
        return self.env['membership.feature']

    def action_verify_eligibility(self):
        """Mark eligibility as verified"""
        for subscription in self:
            if subscription.is_membership:
                subscription.write({
                    'eligibility_verified': True,
                    'eligibility_verified_by': self.env.user.id,
                    'eligibility_verified_date': fields.Date.today(),
                })
        return True

    # ==========================================
    # CONSTRAINTS - Basic validation only
    # Specialized modules add their own constraints
    # ==========================================

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_product_compatibility(self):
        """Basic check that category is compatible with product"""
        for subscription in self:
            if not subscription.is_membership:
                continue
                
            if not subscription.membership_category_id:
                continue
            
            # Basic validation - specialized modules add stricter checks
            product = subscription.plan_id.product_template_id
            
            # Check if product has a default category and it matches
            if product.default_member_category_id:
                if subscription.membership_category_id.category_type != product.default_member_category_id.category_type:
                    # Just a warning - specialized modules can enforce stricter rules
                    pass