# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """Extend product template with AMS functionality."""
    
    _inherit = 'product.template'

    # ========================================================================
    # AMS PRODUCT IDENTIFICATION
    # ========================================================================
    
    is_ams_product = fields.Boolean(
        string="AMS Product",
        default=False,
        help="This product is managed by the AMS system with enhanced features"
    )
    
    # ========================================================================
    # AMS CATEGORY INTEGRATION
    # ========================================================================
    
    ams_category = fields.Selection(
        related='categ_id.ams_category_type',
        string="AMS Category",
        readonly=True,
        store=True,
        help="AMS category type inherited from product category"
    )
    
    category_is_ams = fields.Boolean(
        related='categ_id.is_ams_category',
        string="Category is AMS",
        readonly=True,
        store=True,
        help="Whether the product category is AMS-enabled"
    )
    
    category_requires_member_pricing = fields.Boolean(
        related='categ_id.requires_member_pricing',
        string="Category Requires Member Pricing",
        readonly=True,
        store=True
    )
    
    category_is_subscription = fields.Boolean(
        related='categ_id.is_subscription_category',
        string="Category is Subscription",
        readonly=True,
        store=True
    )
    
    category_is_digital = fields.Boolean(
        related='categ_id.is_digital_category',
        string="Category is Digital",
        readonly=True,
        store=True
    )
    
    category_requires_inventory = fields.Boolean(
        related='categ_id.requires_inventory',
        string="Category Requires Inventory",
        readonly=True,
        store=True
    )
    
    # ========================================================================
    # AMS PRODUCT ATTRIBUTES (can be overridden from category defaults)
    # ========================================================================
    
    has_member_pricing = fields.Boolean(
        string="Has Member Pricing",
        default=False,
        help="This product offers different pricing for members vs non-members"
    )
    
    is_digital_product = fields.Boolean(
        string="Digital Product",
        default=False,
        help="This product is delivered digitally"
    )
    
    stock_controlled = fields.Boolean(
        string="Stock Controlled",
        default=True,
        help="This product requires inventory tracking"
    )
    
    # ========================================================================
    # MEMBER PRICING FIELDS
    # ========================================================================
    
    member_list_price = fields.Float(
        string="Member Price",
        digits='Product Price',
        help="Sale price for association members"
    )
    
    member_standard_price = fields.Float(
        string="Member Cost",
        digits='Product Price',
        help="Cost price for member pricing calculations"
    )
    
    # ========================================================================
    # ONCHANGE METHODS - FIXED
    # ========================================================================
    
    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        """Apply category defaults when category changes."""
        if self.categ_id and self.categ_id.is_ams_category:
            # Set AMS product flag
            self.is_ams_product = True
            
            # Apply category defaults if not already set
            if not self._origin.id:  # New record
                defaults = self.categ_id.get_category_defaults_for_product()
                for field, value in defaults.items():
                    if hasattr(self, field):
                        setattr(self, field, value)
    
    @api.onchange('is_digital_product')
    def _onchange_is_digital_product(self):
        """Digital products don't need inventory tracking."""
        if self.is_digital_product:
            self.stock_controlled = False
            # Set to service for digital products
            self.type = 'service'
    
    @api.onchange('stock_controlled')
    def _onchange_stock_controlled(self):
        """Set product type based on stock control - FIXED VERSION."""
        try:
            if self.stock_controlled:
                # Try different valid values in order of preference
                if hasattr(self, '_fields') and 'type' in self._fields:
                    type_field = self._fields['type']
                    if hasattr(type_field, 'selection'):
                        valid_values = [item[0] for item in type_field.selection]
                        
                        # Try 'consu' first (most common for stockable in Odoo 18)
                        if 'consu' in valid_values:
                            self.type = 'consu'
                        # Try 'product' if available
                        elif 'product' in valid_values:
                            self.type = 'product'
                        # Find first non-service option
                        else:
                            for value in valid_values:
                                if value != 'service':
                                    self.type = value
                                    break
                    else:
                        # Fallback if no selection found
                        self.type = 'consu'
                else:
                    # Fallback if no field info available
                    self.type = 'consu'
            else:
                self.type = 'service'
        except Exception as e:
            # If anything fails, just use service as safe default
            self.type = 'service'
            # Log the error for debugging
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error in _onchange_stock_controlled: {e}")
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def get_member_price(self):
        """Get member price, fallback to regular price if no member pricing."""
        self.ensure_one()
        if self.has_member_pricing and self.member_list_price:
            return self.member_list_price
        return self.list_price
    
    def get_price_for_member_type(self, is_member=False):
        """Get appropriate price based on member status.
        
        Args:
            is_member (bool): Whether customer is a member
            
        Returns:
            float: Appropriate price for customer type
        """
        self.ensure_one()
        if is_member and self.has_member_pricing and self.member_list_price:
            return self.member_list_price
        return self.list_price
    
    @api.model
    def get_products_by_ams_category(self, category):
        """Get products by AMS category type.
        
        Args:
            category (str): AMS category type
            
        Returns:
            recordset: Products in the specified AMS category
        """
        return self.search([('ams_category', '=', category)])
    
    def action_view_ams_category(self):
        """Open the AMS category form for this product's category."""
        self.ensure_one()
        if not self.categ_id or not self.categ_id.is_ams_category:
            return False
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('AMS Category - %s') % self.categ_id.name,
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.categ_id.id,
            'target': 'current',
        }
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('member_list_price', 'list_price', 'has_member_pricing')
    def _check_member_pricing(self):
        """Validate member pricing configuration."""
        for product in self:
            if product.has_member_pricing:
                if product.member_list_price < 0:
                    raise ValidationError(_("Member price cannot be negative."))
                # You might want to add other validations here
    
    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set AMS defaults from category."""
        products = super().create(vals_list)
        
        for product in products:
            if product.categ_id and product.categ_id.is_ams_category:
                # Apply category defaults if not explicitly set
                defaults = product.categ_id.get_category_defaults_for_product()
                values_to_update = {}
                
                for field, value in defaults.items():
                    if hasattr(product, field) and not getattr(product, field):
                        values_to_update[field] = value
                
                if values_to_update:
                    product.write(values_to_update)
        
        return products
    
    def write(self, vals):
        """Override write to maintain AMS consistency."""
        result = super().write(vals)
        
        # If category changed to AMS category, apply defaults
        if 'categ_id' in vals:
            for product in self:
                if product.categ_id and product.categ_id.is_ams_category and not product.is_ams_product:
                    defaults = product.categ_id.get_category_defaults_for_product()
                    product.write(defaults)
        
        return result