# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Simplified AMS product extensions focusing on integration with 
    ams_product_types and ams_member_data rather than duplicating functionality.
    """
    _inherit = 'product.template'

    # ========================================================================
    # AMS PRODUCT IDENTIFICATION
    # ========================================================================

    is_ams_product = fields.Boolean(
        string="AMS Product",
        compute='_compute_is_ams_product',
        store=True,
        help="Auto-detected from AMS category (ams_product_types)"
    )

    @api.depends('categ_id.is_ams_category')
    def _compute_is_ams_product(self):
        """Auto-detect AMS products from enhanced categories"""
        for product in self:
            product.is_ams_product = bool(
                product.categ_id and product.categ_id.is_ams_category
            )

    # ========================================================================
    # MEMBER PRICING INTEGRATION
    # ========================================================================

    member_price = fields.Monetary(
        string="Member Price",
        compute='_compute_member_price',
        store=True,
        help="Calculated from category member discount percentage"
    )

    @api.depends('categ_id.member_discount_percent', 'list_price', 'categ_id.requires_member_pricing')
    def _compute_member_price(self):
        """Calculate member price using category discount from ams_product_types"""
        for product in self:
            if (product.categ_id and 
                product.categ_id.requires_member_pricing and 
                product.categ_id.member_discount_percent):
                
                discount = product.categ_id.member_discount_percent / 100
                product.member_price = product.list_price * (1 - discount)
            else:
                product.member_price = product.list_price

    member_savings = fields.Monetary(
        string="Member Savings",
        compute='_compute_member_savings',
        help="Amount saved with member pricing"
    )

    @api.depends('list_price', 'member_price')
    def _compute_member_savings(self):
        """Calculate member savings amount"""
        for product in self:
            product.member_savings = product.list_price - product.member_price

    # ========================================================================
    # DIGITAL CONTENT (SIMPLIFIED)
    # ========================================================================

    digital_url = fields.Char(
        string="Download URL",
        help="URL for digital product download"
    )

    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Digital File",
        help="File attachment for digital product delivery"
    )

    has_digital_content = fields.Boolean(
        string="Has Digital Content",
        compute='_compute_has_digital_content',
        store=True,
        help="Whether digital content is available for this product"
    )

    @api.depends('digital_url', 'digital_attachment_id', 'categ_id.is_digital_category')
    def _compute_has_digital_content(self):
        """Check if digital content is available"""
        for product in self:
            if product.categ_id and product.categ_id.is_digital_category:
                product.has_digital_content = bool(
                    product.digital_url or product.digital_attachment_id
                )
            else:
                product.has_digital_content = False

    # ========================================================================
    # MEMBERSHIP REQUIREMENTS
    # ========================================================================

    requires_membership = fields.Boolean(
        string="Requires Membership",
        compute='_compute_requires_membership',
        store=True,
        help="Whether membership is required to purchase this product"
    )

    @api.depends('categ_id.is_membership_category', 'categ_id.grants_portal_access')
    def _compute_requires_membership(self):
        """Determine if membership is required based on category"""
        for product in self:
            if product.categ_id:
                # Membership products or portal access products require membership
                product.requires_membership = (
                    product.categ_id.is_membership_category or
                    product.categ_id.grants_portal_access
                )
            else:
                product.requires_membership = False

    # ========================================================================
    # LEGACY SYSTEM INTEGRATION
    # ========================================================================

    legacy_product_id = fields.Char(
        string="Legacy Product ID",
        help="Product ID from legacy/external systems for data migration"
    )

    # ========================================================================
    # COMPUTED DISPLAY FIELDS
    # ========================================================================

    ams_category_display = fields.Char(
        string="AMS Category",
        related='categ_id.ams_category_type',
        readonly=True,
        help="AMS category type from enhanced category"
    )

    pricing_summary = fields.Char(
        string="Pricing Summary",
        compute='_compute_pricing_summary',
        help="Summary of pricing for this product"
    )

    @api.depends('list_price', 'member_price', 'categ_id.requires_member_pricing')
    def _compute_pricing_summary(self):
        """Create pricing summary for display"""
        for product in self:
            if product.categ_id and product.categ_id.requires_member_pricing:
                if product.member_savings > 0:
                    product.pricing_summary = f"Members: ${product.member_price:.2f} (Save ${product.member_savings:.2f}) • Non-members: ${product.list_price:.2f}"
                else:
                    product.pricing_summary = f"Members & Non-members: ${product.list_price:.2f}"
            else:
                product.pricing_summary = f"${product.list_price:.2f}"

    # ========================================================================
    # BUSINESS METHODS - INTEGRATION WITH AMS_MEMBER_DATA
    # ========================================================================

    def get_price_for_partner(self, partner):
        """
        Get appropriate price based on partner's membership status from ams_member_data.
        
        Args:
            partner (res.partner): Partner to check membership status
            
        Returns:
            float: Appropriate price for the partner
        """
        self.ensure_one()
        
        if not partner:
            return self.list_price
            
        # Check membership status using ams_member_data fields
        is_member = self._check_partner_membership(partner)
        
        # Return member price if applicable
        if is_member and self.categ_id and self.categ_id.requires_member_pricing:
            return self.member_price
            
        return self.list_price

    def _check_partner_membership(self, partner):
        """
        Check if partner is an active member using ams_member_data fields.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner is an active member
        """
        if not partner:
            return False

        # Check ams_member_data fields
        if hasattr(partner, 'is_member') and hasattr(partner, 'membership_status'):
            return partner.is_member and partner.membership_status == 'active'
        
        # Fallback for standard Odoo membership module
        if hasattr(partner, 'membership_state'):
            return partner.membership_state in ['invoiced', 'paid']
            
        return False

    def can_be_purchased_by_partner(self, partner):
        """
        Check if this product can be purchased by the given partner.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner can purchase this product
        """
        self.ensure_one()
        
        # Basic availability check
        if not self.active or not self.sale_ok:
            return False
            
        # Check membership requirement
        if self.requires_membership:
            return self._check_partner_membership(partner)
            
        return True

    def get_digital_content_access(self, partner=None):
        """
        Get digital content access information.
        
        Args:
            partner (res.partner, optional): Partner requesting access
            
        Returns:
            dict: Digital content access information
        """
        self.ensure_one()
        
        # Check if partner can access (for future access control)
        can_access = True
        if partner and self.requires_membership:
            can_access = self._check_partner_membership(partner)
            
        return {
            'is_digital': bool(self.categ_id and self.categ_id.is_digital_category),
            'has_content': self.has_digital_content,
            'download_url': self.digital_url if can_access else None,
            'attachment_id': self.digital_attachment_id.id if (can_access and self.digital_attachment_id) else None,
            'can_access': can_access,
        }

    # ========================================================================
    # SKU MANAGEMENT (SIMPLIFIED)
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate SKU if needed for AMS products"""
        for vals in vals_list:
            # Generate simple SKU if AMS product and no default_code
            if not vals.get('default_code') and vals.get('name'):
                # Check if this will be an AMS product
                categ_id = vals.get('categ_id')
                if categ_id:
                    category = self.env['product.category'].browse(categ_id)
                    if category.is_ams_category:
                        vals['default_code'] = self._generate_simple_sku(vals['name'])
                        
        return super().create(vals_list)

    def _generate_simple_sku(self, name):
        """
        Generate a simple SKU from product name.
        
        Args:
            name (str): Product name
            
        Returns:
            str: Generated SKU
        """
        if not name:
            return 'PRODUCT'
            
        # Clean name and create base SKU
        base_sku = re.sub(r'[^A-Z0-9\s]', '', name.upper())
        base_sku = re.sub(r'\s+', '', base_sku)[:10]  # Remove spaces, limit length
        
        if not base_sku:
            base_sku = 'PRODUCT'
            
        # Ensure uniqueness
        return self._ensure_sku_uniqueness(base_sku)

    def _ensure_sku_uniqueness(self, base_sku):
        """
        Ensure SKU is unique by adding counter if needed.
        
        Args:
            base_sku (str): Base SKU to make unique
            
        Returns:
            str: Unique SKU
        """
        counter = 1
        sku = base_sku
        
        while self.search([('default_code', '=', sku)], limit=1):
            sku = f"{base_sku}{counter:02d}"
            counter += 1
            
        return sku

    # ========================================================================
    # ODOO INTEGRATION HOOKS
    # ========================================================================

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        """Apply category defaults when category changes"""
        if self.categ_id and self.categ_id.is_ams_category:
            # Let category defaults be applied by ams_product_types
            super()._onchange_categ_id()
            
            # Additional AMS-specific logic if needed
            if not self._origin.id:  # New record
                # Auto-generate SKU if needed
                if not self.default_code and self.name:
                    self.default_code = self._generate_simple_sku(self.name)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('digital_url')
    def _check_digital_url_format(self):
        """Validate digital download URL format"""
        for product in self:
            if product.digital_url:
                if not product.digital_url.startswith(('http://', 'https://')):
                    raise ValidationError(
                        _("Digital download URL must start with http:// or https://")
                    )

    @api.constrains('categ_id', 'digital_url', 'digital_attachment_id')
    def _check_digital_content_requirements(self):
        """Validate digital products have content"""
        for product in self:
            if (product.categ_id and 
                product.categ_id.is_digital_category and
                not product.digital_url and 
                not product.digital_attachment_id):
                
                raise ValidationError(
                    _("Digital products must have either a download URL or file attachment.")
                )

    # ========================================================================
    # QUERY METHODS FOR OTHER MODULES
    # ========================================================================

    @api.model
    def get_ams_products_by_category_type(self, category_type=None):
        """
        Get AMS products filtered by category type.
        
        Args:
            category_type (str, optional): AMS category type to filter by
            
        Returns:
            recordset: AMS products of the specified type
        """
        domain = [('is_ams_product', '=', True)]
        if category_type:
            domain.append(('categ_id.ams_category_type', '=', category_type))
            
        return self.search(domain)

    @api.model  
    def get_member_pricing_products(self):
        """Get all products that offer member pricing"""
        return self.search([
            ('is_ams_product', '=', True),
            ('categ_id.requires_member_pricing', '=', True)
        ])

    @api.model
    def get_digital_products(self):
        """Get all digital products"""
        return self.search([
            ('is_ams_product', '=', True),
            ('categ_id.is_digital_category', '=', True)
        ])

    @api.model
    def get_membership_required_products(self):
        """Get all products that require membership"""
        return self.search([('requires_membership', '=', True)])

    # ========================================================================
    # ACTIONS FOR UI
    # ========================================================================

    def action_view_category(self):
        """Open the product category form"""
        self.ensure_one()
        if not self.categ_id:
            return False
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Category'),
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.categ_id.id,
            'target': 'current',
        }

    def action_test_member_pricing(self):
        """Test member pricing with sample members (for debugging)"""
        self.ensure_one()
        
        # Find sample members for testing
        members = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('membership_status', '=', 'active')
        ], limit=3)
        
        non_members = self.env['res.partner'].search([
            ('is_member', '=', False)
        ], limit=2)
        
        results = []
        for partner in members:
            price = self.get_price_for_partner(partner)
            results.append(f"Member {partner.name}: ${price:.2f}")
            
        for partner in non_members:
            price = self.get_price_for_partner(partner)
            results.append(f"Non-member {partner.name}: ${price:.2f}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(results),
                'title': f'Pricing Test for {self.name}',
                'type': 'info',
                'sticky': True,
            }
        }