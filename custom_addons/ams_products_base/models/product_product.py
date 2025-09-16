# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    """
    Simplified AMS product variant extensions.
    Inherits most functionality from template, adds only variant-specific essentials.
    """
    _inherit = 'product.product'

    # ========================================================================
    # TEMPLATE FIELD REFERENCES (for easier access) - FIXED
    # ========================================================================

    template_is_ams_product = fields.Boolean(
        related='product_tmpl_id.is_ams_product',
        string="Template AMS Product",
        readonly=True,
        store=True
    )

    template_member_price = fields.Monetary(
        related='product_tmpl_id.member_price',
        string="Template Member Price",
        readonly=True
    )

    template_requires_membership = fields.Boolean(
        related='product_tmpl_id.requires_membership',
        string="Template Requires Membership",
        readonly=True,
        store=True
    )

    template_has_digital_content = fields.Boolean(
        related='product_tmpl_id.has_digital_content',
        string="Template Has Digital Content",
        readonly=True,
        store=True
    )

    template_ams_category_display = fields.Selection([
        ('membership', 'Membership'),
        ('event', 'Event'),
        ('education', 'Education'),
        ('publication', 'Publication'),
        ('merchandise', 'Merchandise'),
        ('certification', 'Certification'),
        ('digital', 'Digital Download'),
        ('donation', 'Donation')
    ], string="Template AMS Category",
       related='product_tmpl_id.ams_category_display',
       readonly=True,
       store=True)

    # ========================================================================
    # LEGACY SYSTEM INTEGRATION
    # ========================================================================

    variant_legacy_id = fields.Char(
        string="Variant Legacy ID",
        help="Variant ID from legacy/external systems"
    )

    # ========================================================================
    # SIMPLIFIED VARIANT SKU (uses default_code)
    # ========================================================================

    @api.depends('default_code', 'product_tmpl_id.default_code')
    def _compute_effective_sku(self):
        """Calculate effective SKU (variant or template default_code)"""
        for variant in self:
            if variant.default_code:
                variant.effective_sku = variant.default_code
            elif variant.product_tmpl_id.default_code and len(variant.product_tmpl_id.product_variant_ids) > 1:
                # Multi-variant template - add variant suffix
                base_sku = variant.product_tmpl_id.default_code
                variant.effective_sku = f"{base_sku}-V{variant.id % 1000:03d}"
            else:
                variant.effective_sku = variant.product_tmpl_id.default_code or ""

    effective_sku = fields.Char(
        string="Effective SKU",
        compute='_compute_effective_sku',
        store=True,
        help="The actual SKU being used (variant default_code or template-based)"
    )

    # ========================================================================
    # VARIANT STATUS AND AVAILABILITY
    # ========================================================================

    @api.depends('template_is_ams_product', 'template_has_digital_content', 'qty_available')
    def _compute_availability_status(self):
        """Calculate availability status for this variant"""
        for variant in self:
            if not variant.template_is_ams_product:
                variant.availability_status = 'standard'
            elif variant.template_has_digital_content:
                variant.availability_status = 'digital_available' if variant.template_has_digital_content else 'digital_missing'
            elif variant.type == 'product':  # Stockable product
                if variant.qty_available > 0:
                    variant.availability_status = 'in_stock'
                else:
                    variant.availability_status = 'out_of_stock'
            else:
                variant.availability_status = 'service_available'

    availability_status = fields.Selection([
        ('standard', 'Standard Product'),
        ('digital_available', 'Digital Available'),
        ('digital_missing', 'Digital Missing'),
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('service_available', 'Service Available'),
    ], string="Availability Status", compute='_compute_availability_status', store=True)

    # ========================================================================
    # BUSINESS METHODS - DELEGATE TO TEMPLATE
    # ========================================================================

    def get_price_for_partner(self, partner):
        """
        Get appropriate price for partner - delegates to template.
        
        Args:
            partner (res.partner): Partner to check membership status
            
        Returns:
            float: Appropriate price for the partner
        """
        self.ensure_one()
        return self.product_tmpl_id.get_price_for_partner(partner)

    def can_be_purchased_by_partner(self, partner):
        """
        Check if variant can be purchased by partner - delegates to template.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner can purchase this variant
        """
        self.ensure_one()
        
        # Check template-level permissions
        if not self.product_tmpl_id.can_be_purchased_by_partner(partner):
            return False
            
        # Variant-specific availability
        if self.availability_status in ['out_of_stock', 'digital_missing']:
            return False
            
        return True

    def get_digital_content_access(self, partner=None):
        """
        Get digital content access - delegates to template.
        
        Args:
            partner (res.partner, optional): Partner requesting access
            
        Returns:
            dict: Digital content access information
        """
        self.ensure_one()
        return self.product_tmpl_id.get_digital_content_access(partner)

    def get_member_savings_amount(self, partner):
        """
        Calculate member savings for this variant.
        
        Args:
            partner (res.partner): Partner to calculate savings for
            
        Returns:
            float: Amount saved with member pricing
        """
        self.ensure_one()
        
        member_price = self.get_price_for_partner(partner) if self._check_partner_membership(partner) else self.lst_price
        regular_price = self.lst_price
        
        return max(0, regular_price - member_price)

    def _check_partner_membership(self, partner):
        """Check if partner is member - delegates to template"""
        return self.product_tmpl_id._check_partner_membership(partner)

    # ========================================================================
    # VARIANT CREATION AND SYNCHRONIZATION
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Handle variant creation with AMS features"""
        for vals in vals_list:
            # Generate variant SKU if needed
            if not vals.get('default_code'):
                template_id = vals.get('product_tmpl_id')
                if template_id:
                    template = self.env['product.template'].browse(template_id)
                    if template.is_ams_product and template.default_code:
                        # Don't auto-generate variant SKU - let compute method handle it
                        pass

        variants = super().create(vals_list)
        
        # Log creation of AMS variants
        for variant in variants:
            if variant.template_is_ams_product:
                _logger.info(f"Created AMS product variant: {variant.display_name} (SKU: {variant.effective_sku})")
        
        return variants

    # ========================================================================
    # ENHANCED NAME AND DISPLAY
    # ========================================================================

    def name_get(self):
        """Enhanced name display for AMS variants"""
        result = []
        for variant in self:
            name = super(ProductProduct, variant).name_get()[0][1]
            
            # Add SKU to AMS products
            if variant.template_is_ams_product and variant.effective_sku:
                name = f"[{variant.effective_sku}] {name}"
                
            # Add membership indicator if required
            if variant.template_requires_membership:
                name = f"{name} (Members Only)"
                
            result.append((variant.id, name))
            
        return result

    # ========================================================================
    # SEARCH AND QUERY METHODS
    # ========================================================================

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search including effective SKU"""
        args = args or []
        
        if name:
            # Search in name, default_code, and effective_sku
            domain = [
                '|', '|',
                ('name', operator, name),
                ('default_code', operator, name), 
                ('effective_sku', operator, name)
            ]
            args = domain + args
            
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def get_ams_variants_by_category_type(self, category_type=None):
        """
        Get AMS variants filtered by template category type.
        
        Args:
            category_type (str, optional): AMS category type to filter by
            
        Returns:
            recordset: AMS variants of the specified type
        """
        domain = [('template_is_ams_product', '=', True)]
        if category_type:
            domain.append(('product_tmpl_id.categ_id.ams_category_type', '=', category_type))
            
        return self.search(domain)

    @api.model
    def get_low_stock_ams_variants(self, threshold=0):
        """
        Get AMS variants with low stock levels.
        
        Args:
            threshold (float): Stock threshold (default: 0)
            
        Returns:
            recordset: Low stock AMS variants
        """
        return self.search([
            ('template_is_ams_product', '=', True),
            ('type', '=', 'product'),  # Only stockable products
            ('qty_available', '<=', threshold)
        ])

    @api.model
    def get_digital_content_missing_variants(self):
        """Get digital product variants missing content"""
        return self.search([
            ('template_is_ams_product', '=', True),
            ('product_tmpl_id.categ_id.is_digital_category', '=', True),
            ('template_has_digital_content', '=', False)
        ])

    @api.model
    def get_membership_required_variants(self):
        """Get variants that require membership to purchase"""
        return self.search([('template_requires_membership', '=', True)])

    # ========================================================================
    # ACTIONS FOR UI
    # ========================================================================

    def action_view_template(self):
        """Open the product template form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Template'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.id,
            'target': 'current',
        }

    def action_view_category(self):
        """Open the product category form"""
        self.ensure_one()
        return self.product_tmpl_id.action_view_category()
    
    def action_view_ams_category(self):
        """Alias for action_view_category for backward compatibility"""
        return self.action_view_category()

    def action_test_variant_access(self):
        """Test variant access with sample members (for debugging)"""
        self.ensure_one()
        
        # Find sample partners for testing
        test_partners = self.env['res.partner'].search([], limit=5)
        
        results = []
        for partner in test_partners:
            can_purchase = self.can_be_purchased_by_partner(partner)
            price = self.get_price_for_partner(partner)
            is_member = self._check_partner_membership(partner)
            
            results.append(
                f"{partner.name} ({'Member' if is_member else 'Non-member'}): "
                f"Can purchase: {can_purchase}, Price: ${price:.2f}"
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(results),
                'title': f'Access Test for {self.display_name}',
                'type': 'info',
                'sticky': True,
            }
        }

    # ========================================================================
    # REPORTING HELPER METHODS
    # ========================================================================

    def get_variant_summary(self):
        """
        Get summary information for this variant.
        
        Returns:
            dict: Variant summary data
        """
        self.ensure_one()
        
        return {
            'name': self.display_name,
            'sku': self.effective_sku,
            'is_ams': self.template_is_ams_product,
            'category_type': self.template_ams_category_display,
            'requires_membership': self.template_requires_membership,
            'has_digital_content': self.template_has_digital_content,
            'availability_status': self.availability_status,
            'regular_price': self.lst_price,
            'member_price': self.template_member_price,
            'template_id': self.product_tmpl_id.id,
            'category_id': self.product_tmpl_id.categ_id.id if self.product_tmpl_id.categ_id else None,
        }