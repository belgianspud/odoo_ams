# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """
    Simple AMS extension to product.template - just add the essential fields.
    Let Odoo handle all the standard product functionality.
    """
    _inherit = 'product.template'

    # ========================================================================
    # CORE AMS FIELDS - Keep it simple
    # ========================================================================
    
    is_ams_product = fields.Boolean(
        string="AMS Product",
        default=False,
        help="Is this an association product?"
    )
    
    ams_product_type_id = fields.Many2one(
        'ams.product.type',
        string="AMS Product Type",
        help="AMS product type classification"
    )
    
    sku = fields.Char(
        string="SKU",
        help="Stock keeping unit"
    )
    
    # ========================================================================
    # MEMBER PRICING - Simple approach
    # ========================================================================
    
    has_member_pricing = fields.Boolean(
        string="Member Pricing",
        help="Different pricing for members vs non-members"
    )
    
    member_price = fields.Monetary(
        string="Member Price",
        help="Price for association members"
    )
    
    non_member_price = fields.Monetary(
        string="Non-Member Price",
        help="Price for non-members"
    )
    
    # ========================================================================
    # BASIC FEATURES
    # ========================================================================
    
    requires_membership = fields.Boolean(
        string="Requires Membership",
        help="Only members can purchase"
    )
    
    is_digital_product = fields.Boolean(
        string="Digital Product",
        help="Delivered digitally"
    )
    
    digital_download_url = fields.Char(
        string="Download URL"
    )
    
    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Digital File"
    )
    
    auto_fulfill_digital = fields.Boolean(
        string="Auto-fulfill Digital",
        default=True
    )
    
    stock_controlled = fields.Boolean(
        string="Track Inventory",
        default=True
    )
    
    chapter_specific = fields.Boolean(
        string="Chapter Restricted"
    )
    
    legacy_product_id = fields.Char(
        string="Legacy ID",
        help="ID from old system"
    )

    # ========================================================================
    # SIMPLE BUSINESS METHODS
    # ========================================================================
    
    def get_price_for_member(self, is_member=False):
        """Get appropriate price based on member status."""
        self.ensure_one()
        if self.has_member_pricing and is_member and self.member_price:
            return self.member_price
        elif self.has_member_pricing and self.non_member_price:
            return self.non_member_price
        else:
            return self.list_price
    
    def can_purchase(self, is_member=False):
        """Check if customer can purchase this product."""
        self.ensure_one()
        if self.requires_membership and not is_member:
            return False
        return True
    
    # ========================================================================
    # ONCHANGE - Keep it simple
    # ========================================================================
    
    @api.onchange('ams_product_type_id')
    def _onchange_ams_product_type(self):
        """Set basic defaults from product type."""
        if self.ams_product_type_id:
            self.is_digital_product = self.ams_product_type_id.is_digital
            self.has_member_pricing = self.ams_product_type_id.requires_member_pricing
    
    @api.onchange('is_digital_product')
    def _onchange_is_digital_product(self):
        """Digital products don't need inventory."""
        if self.is_digital_product:
            self.type = 'service'
            self.stock_controlled = False
    
    @api.onchange('has_member_pricing')
    def _onchange_has_member_pricing(self):
        """Set non-member price to list price by default."""
        if self.has_member_pricing and not self.non_member_price:
            self.non_member_price = self.list_price