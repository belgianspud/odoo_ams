# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCategory(models.Model):
    """
    Base Membership Category - Simplified for extension by specialized modules
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
    # CATEGORY TYPE - Base types only
    # Specialized modules extend this selection
    # ==========================================
    
    category_type = fields.Selection(
        selection='_get_category_types',
        string='Category Type',
        required=True,
        default='individual',
        tracking=True,
        help='Primary classification of this member category'
    )
    
    @api.model
    def _get_category_types(self):
        """Base category types - extended by other modules"""
        return [
            ('individual', 'Individual'),
            ('organizational', 'Organizational'),
            ('chapter', 'Chapter'),
        ]

    # ==========================================
    # BASIC CLASSIFICATION
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
    
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum')
    ], string='Member Tier',
       default='standard',
       help='Tier level for benefits and access')

    # ==========================================
    # BASIC ACCESS
    # ==========================================
    
    default_portal_access = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium')
    ], string='Default Portal Access',
       default='standard',
       help='Default portal access level for this category')

    # ==========================================
    # VERIFICATION - Core only
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Membership in this category requires staff verification'
    )

    # ==========================================
    # PRODUCT MAPPING
    # ==========================================
    
    default_product_id = fields.Many2one(
        'product.template',
        string='Default Product',
        domain=[('is_membership_product', '=', True)],
        help='Default membership product for this category'
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

    def check_eligibility(self, partner_id):
        """
        Basic eligibility check - extended by specialized modules
        
        Args:
            partner_id: res.partner record or ID
        
        Returns:
            tuple: (bool: is_eligible, list: reasons if not eligible)
        """
        self.ensure_one()
        
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        reasons = []
        
        # Basic checks only - specialized modules add their own
        # Check organizational compatibility
        if self.category_type == 'organizational' and not partner.is_company:
            reasons.append(_("This category is for organizations only."))
        
        if self.category_type != 'organizational' and partner.is_company:
            reasons.append(_("This category is for individuals only."))
        
        is_eligible = len(reasons) == 0
        return (is_eligible, reasons)

    def get_available_products(self):
        """
        Get products available to this category
        
        Returns:
            recordset: product.template records
        """
        self.ensure_one()
        
        # Return all active membership products
        # Specialized modules can add filtering
        return self.env['product.template'].search([
            ('is_membership_product', '=', True),
            ('active', '=', True)
        ])

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
    # CONSTRAINTS - Basic only
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