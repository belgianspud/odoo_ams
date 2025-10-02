# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCategory(models.Model):
    """
    Simplified Membership Category - Classification only
    
    The product defines behavior (pricing, billing, features, benefits)
    The category just classifies the member type
    """
    _name = 'membership.category'
    _description = 'Membership Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # CORE FIELDS ONLY
    # ==========================================
    
    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        tracking=True,
        help='Display name for this member category (e.g., Individual Member, Student Member)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help='Unique code (e.g., IND, ORG, CHAP)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists and forms'
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
    # CATEGORY TYPE - This determines behavior
    # ==========================================
    
    category_type = fields.Selection([
        ('individual', 'Individual Member'),
        ('organizational', 'Organization Member'),
        ('chapter', 'Chapter Member'),
        ('seat', 'Organization Seat'),
    ], string='Category Type',
       required=True,
       default='individual',
       tracking=True,
       help='Primary classification - determines member type and available products')
    
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
        help='This is a full membership category (vs affiliate/associate)'
    )

    # ==========================================
    # PRODUCT LINK - THE CORE CONNECTION
    # This is what defines pricing, billing, features, benefits
    # ==========================================
    
    default_product_id = fields.Many2one(
        'product.template',
        string='Membership Product',
        domain=[('is_membership_product', '=', True)],
        help='The subscription product that defines pricing, billing, features, and benefits for this category'
    )

    # ==========================================
    # STATISTICS
    # ==========================================
    
    member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_count',
        help='Number of active members in this category'
    )

    @api.depends('name')  # Dummy dependency - recompute manually when needed
    def _compute_member_count(self):
        """Calculate member statistics"""
        for category in self:
            active_members = self.env['res.partner'].search_count([
                ('membership_category_id', '=', category.id),
                ('is_member', '=', True)
            ])
            category.member_count = active_members

    # ==========================================
    # BUSINESS METHODS - Simplified
    # ==========================================

    def get_available_products(self):
        """
        Get products available to this category
        
        Returns:
            recordset: product.template records
        """
        self.ensure_one()
        
        # If category has default product, return it
        if self.default_product_id:
            return self.default_product_id
        
        # Otherwise return all membership products of matching type
        domain = [
            ('is_membership_product', '=', True),
            ('active', '=', True)
        ]
        
        # Filter by subscription type if available
        if self.category_type in ['individual', 'organizational', 'chapter', 'seat']:
            domain.append(('subscription_product_type', '=', 
                          'membership' if self.category_type == 'individual' 
                          else 'organizational_membership' if self.category_type == 'organizational'
                          else self.category_type))
        
        return self.env['product.template'].search(domain)

    def action_view_members(self):
        """View members in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {
                'default_membership_category_id': self.id,
            }
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
        """Custom name_get to show code in parentheses"""
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