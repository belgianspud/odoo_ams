# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    """
    Simplified Product Extensions for Base Membership Module
    """
    _inherit = 'product.template'

    # ==========================================
    # CORE MEMBERSHIP FLAG
    # ==========================================
    
    is_membership_product = fields.Boolean(
        string='Membership',
        default=False,
        help="Check this if this product represents a membership. "
             "Works with subscription features for billing and renewal."
    )
    
    # ==========================================
    # BASIC TYPE - Extended by specialized modules
    # ==========================================
    
    subscription_product_type = fields.Selection(
        selection='_get_subscription_product_types',
        string='Subscription Type',
        help='Type of subscription this product represents'
    )
    
    @api.model
    def _get_subscription_product_types(self):
        """Base types - extended by specialized modules"""
        return [
            ('membership', 'Individual Membership'),
            ('organizational_membership', 'Organizational Membership'),
            ('chapter', 'Chapter Membership'),
        ]

    # ==========================================
    # CATEGORY MAPPING
    # ==========================================
    
    default_member_category_id = fields.Many2one(
        'membership.category',
        string='Default Member Category',
        help='Default category when creating membership with this product'
    )

    # ==========================================
    # FEATURES & BENEFITS - Core only
    # ==========================================
    
    benefit_ids = fields.Many2many(
        'membership.benefit',
        'product_benefit_rel',
        'product_id',
        'benefit_id',
        string='Benefits',
        help="Benefits included with this membership"
    )
    
    feature_ids = fields.Many2many(
        'membership.feature',
        'product_feature_rel',
        'product_id',
        'feature_id',
        string='Features',
        help="Features included with this membership"
    )

    # ==========================================
    # PORTAL ACCESS - Basic
    # ==========================================
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access')
    ], string='Portal Access Level',
       default='standard',
       help="Default portal access level for members with this product")

    # ==========================================
    # MEMBER COUNT
    # ==========================================
    
    current_member_count = fields.Integer(
        string='Current Members',
        compute='_compute_current_member_count',
        help="Number of current active members"
    )

    @api.depends('is_membership_product')
    def _compute_current_member_count(self):
        """Calculate current active members"""
        for product in self:
            if product.is_membership_product:
                count = self.env['subscription.subscription'].search_count([
                    ('plan_id.product_template_id', '=', product.id),
                    ('state', 'in', ['trial', 'active'])
                ])
                product.current_member_count = count
            else:
                product.current_member_count = 0

    # ==========================================
    # ONCHANGE - Basic
    # ==========================================

    @api.onchange('is_membership_product')
    def _onchange_is_membership_product(self):
        """Set defaults for membership products"""
        if self.is_membership_product:
            # Set as subscription product
            if hasattr(self, 'is_subscription'):
                self.is_subscription = True
            
            # Set default subscription type if not set
            if not self.subscription_product_type:
                self.subscription_product_type = 'membership'
            
            # Set as service product
            if not self.type:
                self.type = 'service'
            
            # Set default portal access
            if not self.portal_access_level:
                self.portal_access_level = 'standard'

    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_product_type in ['membership', 'chapter', 'organizational_membership']:
            self.is_membership_product = True

    # ==========================================
    # ACTIONS
    # ==========================================

    def action_view_members(self):
        """View all members with this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [
                ('membership_subscription_ids.plan_id.product_template_id', '=', self.id),
                ('membership_subscription_ids.state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_id': self.id}
        }

    def action_view_active_subscriptions(self):
        """View active subscriptions for this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [
                ('plan_id.product_template_id', '=', self.id),
                ('state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_template_id': self.id}
        }