# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipFeature(models.Model):
    """
    Membership Feature - Simplified Base Model
    Technical features that provide capabilities to members
    """
    _name = 'membership.feature'
    _description = 'Membership Feature'
    _order = 'category, sequence, name'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Feature Name',
        required=True,
        translate=True,
        help='Display name for this feature (e.g., "Portal Access", "CE Tracking")'
    )
    
    code = fields.Char(
        string='Feature Code',
        required=True,
        help='Unique code for this feature (e.g., PORTAL_ACCESS, CE_TRACKING)'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive features are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this feature'
    )
    
    icon = fields.Char(
        string='Icon',
        help='Font Awesome icon class (e.g., fa-star, fa-book)'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # FEATURE CLASSIFICATION
    # ==========================================
    
    category = fields.Selection([
        ('access', 'Access Rights'),
        ('portal', 'Portal Features'),
        ('directory', 'Directory'),
        ('event', 'Events'),
        ('professional', 'Professional Services'),
        ('networking', 'Networking'),
        ('education', 'Education & Training'),
        ('certification', 'Certification'),
        ('publication', 'Publications'),
        ('other', 'Other')
    ], string='Feature Category',
       required=True,
       default='other',
       help='Type of feature this provides')
    
    feature_type = fields.Selection([
        ('boolean', 'Yes/No'),
        ('quantity', 'Quantity'),
        ('percentage', 'Percentage'),
        ('text', 'Text Value'),
        ('unlimited', 'Unlimited')
    ], string='Feature Type',
       default='boolean',
       required=True,
       help='How this feature is quantified')
    
    is_premium_feature = fields.Boolean(
        string='Premium Feature',
        default=False,
        help='This is a premium feature for higher-tier memberships'
    )

    # ==========================================
    # FEATURE VALUE CONFIGURATION
    # ==========================================
    
    default_value = fields.Char(
        string='Default Value',
        help='Default value for this feature (format depends on feature_type)'
    )

    # ==========================================
    # PRODUCT ASSOCIATIONS
    # ==========================================
    
    product_ids = fields.Many2many(
        'product.template',
        'product_feature_rel',
        'feature_id',
        'product_id',
        string='Associated Products',
        help='Membership products that include this feature'
    )
    
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
        help='Number of products using this feature'
    )

    @api.depends('product_ids')
    def _compute_product_count(self):
        """Count associated products"""
        for feature in self:
            feature.product_count = len(feature.product_ids)

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def check_availability(self, partner_id, date=None):
        """
        Check if feature is available to a partner
        
        Args:
            partner_id: res.partner record or ID
            date: Date to check (defaults to today)
        
        Returns:
            tuple: (bool: is_available, str: reason if not available)
        """
        self.ensure_one()
        
        if date is None:
            date = fields.Date.today()
        
        # Check if partner has subscription with this feature
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        has_feature = bool(
            partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active'] and 
                         self in s.plan_id.product_template_id.feature_ids
            )
        )
        
        if not has_feature:
            return (False, _("Your membership does not include this feature"))
        
        return (True, '')

    def action_view_products(self):
        """View products that include this feature"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products with Feature: %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    @api.model
    def get_feature_by_code(self, code):
        """
        Get feature by code (helper method)
        
        Args:
            code: Feature code
        
        Returns:
            membership.feature record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"{name} [{record.code}]"
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure feature code is unique"""
        for feature in self:
            if self.search_count([
                ('code', '=', feature.code),
                ('id', '!=', feature.id)
            ]) > 0:
                raise ValidationError(
                    _("Feature code must be unique. '%s' is already used.") % feature.code
                )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Feature code must be unique!'),
    ]