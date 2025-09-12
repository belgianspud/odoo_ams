# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    """Extend Odoo's product category with AMS-specific functionality."""
    
    _inherit = 'product.category'

    # ========================================================================
    # AMS CLASSIFICATION FIELDS
    # ========================================================================
    
    is_ams_category = fields.Boolean(
        string="AMS Category",
        default=False,
        help="Mark this category as an AMS-managed category with enhanced features"
    )
    
    ams_category_type = fields.Selection([
        ('membership', 'Membership'),
        ('event', 'Event'),
        ('education', 'Education'),
        ('publication', 'Publication'),
        ('merchandise', 'Merchandise'),
        ('certification', 'Certification'),
        ('digital', 'Digital Download')
    ], string="AMS Category Type", help="AMS-specific category classification")
    
    # ========================================================================
    # AMS PRODUCT ATTRIBUTES
    # ========================================================================
    
    requires_member_pricing = fields.Boolean(
        string="Supports Member Pricing",
        default=False,
        help="Products in this category offer different pricing for members vs non-members"
    )
    
    is_subscription_category = fields.Boolean(
        string="Subscription Category",
        default=False,
        help="Products in this category represent recurring subscriptions"
    )
    
    is_digital_category = fields.Boolean(
        string="Digital Category",
        default=False,
        help="Products in this category are delivered digitally"
    )
    
    requires_inventory = fields.Boolean(
        string="Requires Inventory Tracking",
        default=True,
        help="Products in this category require physical inventory management"
    )
    
    # ========================================================================
    # INTEGRATION FIELDS
    # ========================================================================
    
    default_uom_id = fields.Many2one(
        'uom.uom',
        string="Default Unit of Measure",
        help="Default unit of measure for products in this category"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    ams_product_count = fields.Integer(
        string="AMS Products",
        compute='_compute_ams_product_count',
        help="Number of AMS products in this category"
    )
    
    category_summary = fields.Char(
        string="Category Summary",
        compute='_compute_category_summary',
        help="Summary of AMS category attributes"
    )
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_ams_product_count(self):
        """Compute AMS product count for this category."""
        for category in self:
            if category.is_ams_category:
                # Count products that have is_ams_product=True in this category
                category.ams_product_count = self.env['product.template'].search_count([
                    ('categ_id', 'child_of', category.id),
                    ('is_ams_product', '=', True)
                ])
            else:
                category.ams_product_count = 0
    
    def _compute_category_summary(self):
        """Compute category summary for display."""
        for category in self:
            if category.is_ams_category:
                attributes = []
                
                if category.ams_category_type:
                    type_dict = dict(category._fields['ams_category_type'].selection)
                    attributes.append(type_dict.get(category.ams_category_type))
                
                if category.requires_member_pricing:
                    attributes.append("Member Pricing")
                
                if category.is_subscription_category:
                    attributes.append("Subscription")
                
                if category.is_digital_category:
                    attributes.append("Digital")
                else:
                    attributes.append("Physical")
                
                if category.requires_inventory:
                    attributes.append("Inventory Tracked")
                
                category.category_summary = " • ".join(filter(None, attributes))
            else:
                category.category_summary = ""
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('ams_category_type')
    def _onchange_ams_category_type(self):
        """Set default attributes based on AMS category type."""
        if self.ams_category_type:
            # Set is_ams_category to True when type is selected
            self.is_ams_category = True
            
            # Set sensible defaults based on category type
            category_defaults = {
                'membership': {
                    'requires_member_pricing': False,  # Members get membership pricing anyway
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': False,
                },
                'event': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': False,
                },
                'education': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'publication': {
                    'requires_member_pricing': True,
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'merchandise': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'certification': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                },
                'digital': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                },
            }
            
            defaults = category_defaults.get(self.ams_category_type, {})
            for field, value in defaults.items():
                setattr(self, field, value)
    
    @api.onchange('is_digital_category')
    def _onchange_is_digital_category(self):
        """Digital categories typically don't need inventory tracking."""
        if self.is_digital_category:
            self.requires_inventory = False
    
    @api.onchange('is_ams_category')
    def _onchange_is_ams_category(self):
        """Clear AMS fields when unmarking as AMS category."""
        if not self.is_ams_category:
            self.ams_category_type = False
            self.requires_member_pricing = False
            self.is_subscription_category = False
            self.is_digital_category = False
            self.requires_inventory = True  # Reset to default
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('is_digital_category', 'requires_inventory')
    def _check_digital_inventory(self):
        """Warn about digital categories with inventory tracking."""
        for category in self:
            if category.is_digital_category and category.requires_inventory:
                # This is just a warning case, not an error
                # Some digital categories might still need limited inventory tracking
                pass
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    @api.model
    def get_ams_categories_by_type(self, ams_category_type=None):
        """Get AMS categories filtered by type.
        
        Args:
            ams_category_type (str, optional): AMS category type to filter by
            
        Returns:
            recordset: AMS categories of the specified type
        """
        domain = [('is_ams_category', '=', True)]
        if ams_category_type:
            domain.append(('ams_category_type', '=', ams_category_type))
        
        return self.search(domain)
    
    @api.model
    def get_digital_categories(self):
        """Get all digital product categories."""
        return self.search([('is_digital_category', '=', True)])
    
    @api.model
    def get_subscription_categories(self):
        """Get all subscription product categories."""
        return self.search([('is_subscription_category', '=', True)])
    
    @api.model
    def get_member_pricing_categories(self):
        """Get categories that support member pricing."""
        return self.search([('requires_member_pricing', '=', True)])
    
    def action_view_ams_products(self):
        """Open view of AMS products in this category."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('AMS Products - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [
                ('categ_id', 'child_of', self.id),
                ('is_ams_product', '=', True)
            ],
            'context': {
                'default_categ_id': self.id,
                'default_is_ams_product': True,
                'default_type': 'service' if not self.requires_inventory else 'product',
            },
        }
    
    def action_create_ams_product(self):
        """Create a new AMS product in this category."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create AMS Product - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_categ_id': self.id,
                'default_is_ams_product': True,
                'default_has_member_pricing': self.requires_member_pricing,
                'default_is_digital_product': self.is_digital_category,
                'default_stock_controlled': self.requires_inventory,
                'default_type': 'service' if not self.requires_inventory else 'product',
            },
        }
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def name_get(self):
        """Enhanced name display for AMS categories."""
        result = []
        for category in self:
            name = category.name
            if category.is_ams_category and category.ams_category_type:
                type_dict = dict(category._fields['ams_category_type'].selection)
                type_name = type_dict.get(category.ams_category_type, '')
                name = f"{name} ({type_name})"
            result.append((category.id, name))
        return result