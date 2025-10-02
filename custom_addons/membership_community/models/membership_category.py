# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCategory(models.Model):
    """
    Simplified Membership Category - Classification Only
    
    Philosophy:
    - Category = Classification (what type of member)
    - Product = Behavior (pricing, features, benefits)
    - Plan = Billing (when and how they pay)
    
    This keeps the category model simple and delegates complexity
    to products and plans where it belongs.
    """
    _name = 'membership.category'
    _description = 'Membership Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # CORE IDENTIFICATION
    # ==========================================
    
    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        tracking=True,
        help='Display name (e.g., Individual Member, Student Member, Premium Corporate)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help='Unique identifier (e.g., IND, STU, CORP_PREM)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True,
        help='Inactive categories are hidden but not deleted'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this member category'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # TYPE CLASSIFICATION
    # ==========================================
    
    category_type = fields.Selection(
        selection='_get_category_types',
        string='Category Type',
        required=True,
        default='individual',
        tracking=True,
        help='Primary classification determining member type'
    )
    
    @api.model
    def _get_category_types(self):
        """
        Base category types - can be extended by other modules
        
        Extension pattern:
        class MembershipCategory(models.Model):
            _inherit = 'membership.category'
            
            @api.model
            def _get_category_types(self):
                types = super()._get_category_types()
                types.extend([
                    ('student', 'Student'),
                    ('retired', 'Retired'),
                ])
                return types
        """
        return [
            ('individual', 'Individual Member'),
            ('organizational', 'Organization Member'),
            ('chapter', 'Chapter Member'),
            ('seat', 'Organization Seat'),
        ]
    
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum'),
    ], string='Member Tier',
       default='standard',
       help='Tier level for this category')

    # ==========================================
    # SIMPLE CLASSIFICATION FLAGS
    # ==========================================
    
    is_voting_member = fields.Boolean(
        string='Voting Rights',
        default=True,
        tracking=True,
        help='Members in this category have voting rights'
    )
    
    is_full_member = fields.Boolean(
        string='Full Membership',
        default=True,
        help='Full membership vs affiliate/associate status'
    )
    
    # ==========================================
    # PRODUCT LINK - Core Connection
    # ==========================================
    
    default_product_id = fields.Many2one(
        'product.template',
        string='Default Product',
        domain=[('is_membership_product', '=', True)],
        help='Default product that defines pricing, billing, features, and benefits'
    )
    
    # ==========================================
    # PORTAL & VERIFICATION - Basic
    # ==========================================
    
    default_portal_access = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], string='Default Portal Access',
       default='standard',
       help='Default portal access level for this category')
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Memberships in this category require eligibility verification'
    )

    # ==========================================
    # STATISTICS
    # ==========================================
    
    member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_count',
        help='Number of active members in this category'
    )
    
    subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_count',
        help='Number of active subscriptions'
    )

    @api.depends('code')  # Dummy dependency
    def _compute_member_count(self):
        """Count active members in this category"""
        for category in self:
            category.member_count = self.env['res.partner'].search_count([
                ('membership_category_id', '=', category.id),
                ('is_member', '=', True),
            ])
    
    @api.depends('code')  # Dummy dependency
    def _compute_subscription_count(self):
        """Count active subscriptions"""
        for category in self:
            category.subscription_count = self.env['subscription.subscription'].search_count([
                ('membership_category_id', '=', category.id),
                ('state', 'in', ['trial', 'active']),
            ])

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_available_products(self):
        """
        Get products available for this category
        
        Returns:
            recordset: product.template records
        """
        self.ensure_one()
        
        if self.default_product_id:
            return self.default_product_id
        
        # Return all membership products of matching type
        domain = [
            ('is_membership_product', '=', True),
            ('active', '=', True),
        ]
        
        # Filter by subscription type
        type_map = {
            'individual': 'membership',
            'organizational': 'organizational_membership',
            'chapter': 'chapter',
            'seat': 'membership',
        }
        
        sub_type = type_map.get(self.category_type)
        if sub_type:
            domain.append(('subscription_product_type', '=', sub_type))
        
        return self.env['product.template'].search(domain)

    def action_view_members(self):
        """View members in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'kanban,list,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {'default_membership_category_id': self.id},
        }
    
    def action_view_subscriptions(self):
        """View subscriptions in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,kanban,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {'default_membership_category_id': self.id},
        }

    @api.model
    def get_category_by_code(self, code):
        """
        Get category by code (helper method)
        
        Args:
            code: Category code
            
        Returns:
            membership.category record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def name_get(self):
        """Custom name_get to show code"""
        result = []
        for record in self:
            if record.code:
                name = f"{record.name} ({record.code})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure category code is unique"""
        for category in self:
            if self.search_count([
                ('code', '=', category.code),
                ('id', '!=', category.id)
            ]) > 0:
                raise ValidationError(
                    _("Category code must be unique. '%s' is already used.") % category.code
                )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique!'),
    ]