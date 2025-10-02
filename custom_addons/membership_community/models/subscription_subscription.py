# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class SubscriptionSubscription(models.Model):
    """
    Simplified Subscription Extensions for Membership Module
    
    Lifecycle management is handled by subscription_management module.
    This just adds membership-specific fields and email notifications.
    """
    _inherit = 'subscription.subscription'

    # ==========================================
    # MEMBERSHIP-SPECIFIC FIELDS
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned to this membership',
        tracking=True
    )
    
    # ==========================================
    # PRODUCT HELPER FIELDS
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
    # ELIGIBILITY - Basic only
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
        """Base source types - can be extended"""
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
    # CRUD OVERRIDES
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

    def write(self, vals):
        """Override to handle membership activation"""
        result = super().write(vals)
        
        # Auto-activate membership subscriptions when they move to active state
        for subscription in self:
            if subscription.is_membership and subscription.state == 'active':
                # Assign member number if not already assigned
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                
                # Set join date if not set
                if not subscription.join_date and 'join_date' not in vals:
                    subscription.join_date = subscription.date_start or fields.Date.today()
        
        return result

    # ==========================================
    # BUSINESS METHODS
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

    def action_confirm(self):
        """Confirm subscription and activate if membership"""
        result = super().action_confirm()
        
        for subscription in self:
            if subscription.is_membership:
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
        
        return result

    # ==========================================
    # MEMBERSHIP-SPECIFIC EMAIL OVERRIDES
    # Override parent methods to use membership templates
    # ==========================================
    
    def _send_grace_period_email(self):
        """Send membership-specific grace period notification"""
        template = self.env.ref(
            'membership_community.email_template_grace_period',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
            self.last_grace_email_date = fields.Date.today()
    
    def _send_suspension_email(self):
        """Send membership-specific suspension notification"""
        template = self.env.ref(
            'membership_community.email_template_suspended_from_grace',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)
    
    def _send_termination_email(self):
        """Send membership-specific termination notification"""
        template = self.env.ref(
            'membership_community.email_template_terminated',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=False)

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_product_compatibility(self):
        """Basic check that category is compatible with product"""
        for subscription in self:
            if not subscription.is_membership:
                continue
                
            if not subscription.membership_category_id:
                continue
            
            # Basic validation - check category type matches product type
            product = subscription.plan_id.product_template_id
            
            if product.default_member_category_id:
                if subscription.membership_category_id.category_type != product.default_member_category_id.category_type:
                    # Just a warning in chatter, don't block
                    subscription.message_post(
                        body=_("Warning: Category type doesn't match product's default category type"),
                        message_type='notification'
                    )