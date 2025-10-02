# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionSubscription(models.Model):
    """
    Simplified Subscription Extensions for Membership
    
    Key Philosophy:
    - Lifecycle management (grace, suspend, terminate) = subscription_management
    - Membership-specific fields and classification = membership_community
    - Email notifications = membership_community overrides
    
    This keeps the model lean by inheriting all lifecycle compute methods
    from subscription_management rather than duplicating them.
    """
    _inherit = 'subscription.subscription'

    # ==========================================
    # MEMBERSHIP-SPECIFIC FIELDS ONLY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned to this membership',
        tracking=True
    )
    
    # ==========================================
    # HELPER FLAGS (Computed from product)
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
    # ELIGIBILITY VERIFICATION - Basic
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
    # MEMBERSHIP SOURCE TRACKING
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
        """
        Base source types - extensible by other modules
        
        Extension pattern for specialized modules:
            @api.model
            def _get_source_types(self):
                types = super()._get_source_types()
                types.extend([
                    ('referral', 'Member Referral'),
                    ('event', 'Event Signup'),
                ])
                return types
        """
        return [
            ('direct', 'Direct Signup'),
            ('renewal', 'Renewal'),
            ('import', 'Data Import'),
            ('admin', 'Admin Created'),
        ]
    
    join_date = fields.Date(
        string='Original Join Date',
        help='Date when member first joined (not renewal date)',
        tracking=True
    )

    # ==========================================
    # NOTE: Lifecycle fields are inherited from subscription_management
    # We do NOT redefine them here:
    # - grace_period_days, suspend_period_days, terminate_period_days
    # - paid_through_date, grace_period_end_date, suspend_end_date, terminate_date
    # - is_in_grace_period, lifecycle_stage
    # - days_until_suspension, days_until_termination
    # - _compute_lifecycle_periods(), _compute_lifecycle_dates(), _compute_lifecycle_status()
    #
    # All of these are handled by subscription_management!
    # ==========================================

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
                
                # Only process membership products
                if product.is_membership_product:
                    # Set join_date if not provided
                    if 'join_date' not in vals:
                        vals['join_date'] = vals.get('date_start', fields.Date.today())
                    
                    # Set default category from product if not provided
                    if 'membership_category_id' not in vals and product.default_member_category_id:
                        vals['membership_category_id'] = product.default_member_category_id.id
        
        return super().create(vals_list)

    def write(self, vals):
        """Handle membership-specific updates"""
        result = super().write(vals)
        
        # Auto-assign member numbers and join dates when activating
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
    # BUSINESS METHODS - Membership Specific
    # ==========================================

    def get_available_benefits(self):
        """Get benefits for this membership"""
        self.ensure_one()
        if self.is_membership:
            return self.plan_id.product_template_id.benefit_ids
        return self.env['membership.benefit']

    def get_available_features(self):
        """Get features for this membership"""
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
                
                subscription.message_post(
                    body=_('Eligibility verified by %s') % self.env.user.name,
                    message_type='notification'
                )
        return True

    def action_confirm(self):
        """Override to handle membership activation"""
        result = super().action_confirm()
        
        for subscription in self:
            if subscription.is_membership:
                # Assign member number
                if not subscription.partner_id.member_number:
                    subscription.partner_id.member_number = self.env['ir.sequence'].next_by_code('member.number')
                    _logger.info(f"Assigned member number {subscription.partner_id.member_number} to {subscription.partner_id.name}")
                
                # Set join date
                if not subscription.join_date:
                    subscription.join_date = subscription.date_start or fields.Date.today()
                
                # Send welcome email if configured
                if subscription.state in ['trial', 'active']:
                    self._send_membership_welcome_email()
        
        return result

    def _send_membership_welcome_email(self):
        """Send membership welcome email"""
        send_welcome = self.env['ir.config_parameter'].sudo().get_param(
            'subscription.send_welcome_email', 'True'
        )
        if send_welcome == 'True':
            template = self.env.ref(
                'subscription_management.email_template_subscription_welcome',
                raise_if_not_found=False
            )
            if template:
                try:
                    template.send_mail(self.id, force_send=False)
                    _logger.info(f"Sent welcome email for membership {self.name}")
                except Exception as e:
                    _logger.error(f"Failed to send welcome email for {self.name}: {e}")

    # ==========================================
    # EMAIL TEMPLATE OVERRIDES
    # Override parent methods to use membership-specific templates
    # These methods are called by subscription_management cron jobs
    # ==========================================
    
    def _send_grace_period_email(self):
        """Send membership-specific grace period notification"""
        template = self.env.ref(
            'membership_community.email_template_grace_period',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                self.last_grace_email_date = fields.Date.today()
                _logger.info(f"Sent grace period email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send grace period email for {self.name}: {e}")
    
    def _send_suspension_email(self):
        """Send membership-specific suspension notification"""
        template = self.env.ref(
            'membership_community.email_template_suspended_from_grace',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                _logger.info(f"Sent suspension email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send suspension email for {self.name}: {e}")
    
    def _send_termination_email(self):
        """Send membership-specific termination notification"""
        template = self.env.ref(
            'membership_community.email_template_terminated',
            raise_if_not_found=False
        )
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                _logger.info(f"Sent termination email for membership {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send termination email for {self.name}: {e}")

    # ==========================================
    # CONSTRAINTS - Basic validation
    # ==========================================

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_product_compatibility(self):
        """
        Basic validation - check category type matches product type
        
        This is a soft validation - just logs a warning rather than blocking.
        Specialized modules can add stricter validations.
        """
        for subscription in self:
            if not subscription.is_membership:
                continue
                
            if not subscription.membership_category_id:
                continue
            
            product = subscription.plan_id.product_template_id
            
            # Check type compatibility
            if product.default_member_category_id:
                if subscription.membership_category_id.category_type != product.default_member_category_id.category_type:
                    # Just a warning in chatter, don't block
                    subscription.message_post(
                        body=_("⚠️ Warning: Category type '%s' doesn't match product's default category type '%s'") % (
                            subscription.membership_category_id.category_type,
                            product.default_member_category_id.category_type
                        ),
                        message_type='notification'
                    )