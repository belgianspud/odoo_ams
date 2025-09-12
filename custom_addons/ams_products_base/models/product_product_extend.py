# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ========================================================================
    # VARIANT-SPECIFIC AMS FIELDS
    # ========================================================================

    variant_sku = fields.Char(
        string="Variant SKU",
        size=64,
        help="Variant-specific SKU override. Leave blank to use template SKU."
    )

    variant_legacy_id = fields.Char(
        string="Variant Legacy ID",
        size=32,
        help="Variant ID from legacy/external systems"
    )

    # ========================================================================
    # VARIANT PRICING FIELDS
    # ========================================================================

    has_variant_pricing = fields.Boolean(
        string="Variant Pricing",
        default=False,
        help="Use variant-specific pricing instead of template pricing"
    )

    variant_member_price = fields.Float(
        string="Variant Member Price",
        digits='Product Price',
        help="Variant-specific member price"
    )

    variant_non_member_price = fields.Float(
        string="Variant Non-Member Price",
        digits='Product Price', 
        help="Variant-specific non-member price"
    )

    # ========================================================================
    # VARIANT DIGITAL CONTENT FIELDS
    # ========================================================================

    has_variant_digital_content = fields.Boolean(
        string="Variant Digital Content",
        default=False,
        help="Use variant-specific digital content"
    )

    variant_digital_url = fields.Char(
        string="Variant Digital URL",
        size=255,
        help="Variant-specific download URL"
    )

    variant_digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Variant Digital File",
        help="Variant-specific digital file"
    )

    # ========================================================================
    # VARIANT INVENTORY FIELDS
    # ========================================================================

    has_variant_inventory_config = fields.Boolean(
        string="Variant Inventory Config",
        default=False,
        help="Use variant-specific inventory configuration"
    )

    variant_stock_controlled = fields.Boolean(
        string="Variant Stock Controlled",
        default=False,
        help="Variant-specific stock control override"
    )

    variant_reorder_point = fields.Float(
        string="Variant Reorder Point",
        help="Minimum stock level before reordering"
    )

    variant_max_stock = fields.Float(
        string="Variant Max Stock",
        help="Maximum stock level"
    )

    variant_fulfillment_route_id = fields.Many2one(
        'stock.route',
        string="Variant Fulfillment Route",
        help="Variant-specific fulfillment route"
    )

    variant_lead_time = fields.Integer(
        string="Variant Lead Time",
        help="Lead time in days for this variant"
    )

    # ========================================================================
    # TEMPLATE FIELD REFERENCES (for easier access) - Updated for categories
    # ========================================================================

    template_is_ams_product = fields.Boolean(
        related='product_tmpl_id.is_ams_product',
        string="Template AMS Product",
        readonly=True
    )

    template_ams_category_type = fields.Selection(
        related='product_tmpl_id.ams_category_type',
        string="Template AMS Category Type",
        readonly=True
    )

    template_has_member_pricing = fields.Boolean(
        related='product_tmpl_id.has_member_pricing',
        string="Template Member Pricing",
        readonly=True
    )

    template_is_digital_product = fields.Boolean(
        related='product_tmpl_id.is_digital_product',
        string="Template Digital Product",
        readonly=True
    )

    template_requires_membership = fields.Boolean(
        related='product_tmpl_id.requires_membership',
        string="Template Requires Membership",
        readonly=True
    )

    template_stock_controlled = fields.Boolean(
        related='product_tmpl_id.stock_controlled',
        string="Template Stock Controlled",
        readonly=True
    )

    template_member_price = fields.Float(
        related='product_tmpl_id.member_price',
        string="Template Member Price",
        readonly=True
    )

    template_non_member_price = fields.Float(
        related='product_tmpl_id.non_member_price',
        string="Template Non-Member Price",
        readonly=True
    )

    template_digital_download_url = fields.Char(
        related='product_tmpl_id.digital_download_url',
        string="Template Digital URL",
        readonly=True
    )

    template_digital_attachment_id = fields.Many2one(
        related='product_tmpl_id.digital_attachment_id',
        string="Template Digital File",
        readonly=True
    )

    template_auto_fulfill_digital = fields.Boolean(
        related='product_tmpl_id.auto_fulfill_digital',
        string="Template Auto Fulfill",
        readonly=True
    )

    template_member_discount_percentage = fields.Float(
        related='product_tmpl_id.member_discount_percentage',
        string="Template Member Discount %",
        readonly=True
    )

    # Category-related fields for variants
    template_category_requires_member_pricing = fields.Boolean(
        related='product_tmpl_id.category_requires_member_pricing',
        string="Category Requires Member Pricing",
        readonly=True
    )

    template_category_is_digital = fields.Boolean(
        related='product_tmpl_id.category_is_digital',
        string="Category is Digital",
        readonly=True
    )

    template_category_requires_inventory = fields.Boolean(
        related='product_tmpl_id.category_requires_inventory',
        string="Category Requires Inventory",
        readonly=True
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('variant_sku', 'product_tmpl_id.sku', 'default_code')
    def _compute_effective_sku(self):
        """Calculate effective SKU (variant or template)."""
        for variant in self:
            if variant.variant_sku:
                variant.effective_sku = variant.variant_sku
            elif variant.product_tmpl_id.sku:
                # Generate variant SKU from template
                base_sku = variant.product_tmpl_id.sku
                if len(variant.product_tmpl_id.product_variant_ids) > 1:
                    variant.effective_sku = f"{base_sku}-V{variant.id}"
                else:
                    variant.effective_sku = base_sku
            else:
                variant.effective_sku = variant.default_code or ""

    effective_sku = fields.Char(
        string="Effective SKU",
        compute='_compute_effective_sku',
        store=True
    )

    @api.depends('has_variant_pricing', 'variant_member_price', 'template_member_price')
    def _compute_final_member_price(self):
        """Calculate final member price (variant or template)."""
        for variant in self:
            if variant.has_variant_pricing and variant.variant_member_price:
                variant.final_member_price = variant.variant_member_price
            else:
                variant.final_member_price = variant.template_member_price or variant.list_price

    final_member_price = fields.Monetary(
        string="Final Member Price",
        compute='_compute_final_member_price',
        store=True
    )

    @api.depends('has_variant_pricing', 'variant_non_member_price', 'template_non_member_price')
    def _compute_final_non_member_price(self):
        """Calculate final non-member price (variant or template)."""
        for variant in self:
            if variant.has_variant_pricing and variant.variant_non_member_price:
                variant.final_non_member_price = variant.variant_non_member_price
            else:
                variant.final_non_member_price = variant.template_non_member_price or variant.list_price

    final_non_member_price = fields.Monetary(
        string="Final Non-Member Price",
        compute='_compute_final_non_member_price',
        store=True
    )

    @api.depends('final_member_price', 'final_non_member_price')
    def _compute_variant_member_discount(self):
        """Calculate variant member discount percentage."""
        for variant in self:
            if variant.final_non_member_price and variant.final_member_price:
                discount = (variant.final_non_member_price - variant.final_member_price) / variant.final_non_member_price * 100
                variant.variant_member_discount = max(0, discount)
            else:
                variant.variant_member_discount = 0.0

    variant_member_discount = fields.Float(
        string="Variant Member Discount %",
        compute='_compute_variant_member_discount',
        store=True
    )

    @api.depends('has_variant_digital_content', 'variant_digital_url', 'variant_digital_attachment_id', 'template_digital_download_url', 'template_digital_attachment_id')
    def _compute_final_digital_content(self):
        """Calculate final digital content (variant or template)."""
        for variant in self:
            if variant.has_variant_digital_content:
                variant.final_digital_url = variant.variant_digital_url
                variant.final_digital_attachment_id = variant.variant_digital_attachment_id
            else:
                variant.final_digital_url = variant.template_digital_download_url
                variant.final_digital_attachment_id = variant.template_digital_attachment_id

    final_digital_url = fields.Char(
        string="Final Digital URL",
        compute='_compute_final_digital_content',
        store=True
    )

    final_digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Final Digital File",
        compute='_compute_final_digital_content',
        store=True
    )

    @api.depends('template_is_digital_product', 'final_digital_url', 'final_digital_attachment_id')
    def _compute_is_digital_content_available(self):
        """Check if digital content is available for this variant."""
        for variant in self:
            if variant.template_is_digital_product:
                variant.is_digital_content_available = bool(variant.final_digital_url or variant.final_digital_attachment_id)
            else:
                variant.is_digital_content_available = False

    is_digital_content_available = fields.Boolean(
        string="Digital Content Available",
        compute='_compute_is_digital_content_available',
        store=True
    )

    @api.depends('has_variant_inventory_config', 'variant_stock_controlled', 'template_stock_controlled')
    def _compute_effective_stock_controlled(self):
        """Calculate effective stock control setting."""
        for variant in self:
            if variant.has_variant_inventory_config:
                variant.effective_stock_controlled = variant.variant_stock_controlled
            else:
                variant.effective_stock_controlled = variant.template_stock_controlled

    effective_stock_controlled = fields.Boolean(
        string="Effective Stock Controlled",
        compute='_compute_effective_stock_controlled',
        store=True
    )

    @api.depends('effective_stock_controlled', 'qty_available', 'variant_reorder_point')
    def _compute_current_stock_level(self):
        """Calculate current stock level for variants."""
        for variant in self:
            if variant.effective_stock_controlled:
                variant.current_stock_level = variant.qty_available
            else:
                variant.current_stock_level = 0.0

    current_stock_level = fields.Float(
        string="Current Stock Level",
        compute='_compute_current_stock_level',
        store=True
    )

    @api.depends('current_stock_level', 'variant_reorder_point', 'effective_stock_controlled')
    def _compute_variant_needs_reorder(self):
        """Check if variant needs reordering."""
        for variant in self:
            if variant.effective_stock_controlled and variant.variant_reorder_point:
                variant.variant_needs_reorder = variant.current_stock_level <= variant.variant_reorder_point
            else:
                variant.variant_needs_reorder = False

    variant_needs_reorder = fields.Boolean(
        string="Needs Reorder",
        compute='_compute_variant_needs_reorder',
        store=True
    )

    @api.depends('template_is_digital_product', 'effective_stock_controlled', 'is_digital_content_available', 'variant_needs_reorder')
    def _compute_inventory_status_display(self):
        """Calculate inventory status display."""
        for variant in self:
            if variant.template_is_digital_product:
                if variant.is_digital_content_available:
                    variant.inventory_status_display = 'Digital Available'
                else:
                    variant.inventory_status_display = 'Digital Missing'
            elif variant.effective_stock_controlled:
                if variant.variant_needs_reorder:
                    variant.inventory_status_display = 'Low Stock'
                else:
                    variant.inventory_status_display = 'In Stock'
            else:
                variant.inventory_status_display = 'Service'

    inventory_status_display = fields.Char(
        string="Inventory Status",
        compute='_compute_inventory_status_display',
        store=True
    )

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle variant SKU generation."""
        for vals in vals_list:
            # Generate variant SKU if needed
            if vals.get('template_is_ams_product') and not vals.get('variant_sku'):
                template = self.env['product.template'].browse(vals.get('product_tmpl_id'))
                if template.sku:
                    vals['variant_sku'] = self._generate_variant_sku(template.sku)

        variants = super().create(vals_list)
        
        for variant in variants:
            variant._sync_variant_fields()
        
        return variants

    def write(self, vals):
        """Override write to maintain synchronization."""
        result = super().write(vals)
        
        # Sync variant fields if relevant fields changed
        if any(field in vals for field in ['has_variant_pricing', 'has_variant_digital_content', 'has_variant_inventory_config']):
            for variant in self:
                variant._sync_variant_fields()
                
        return result

    def _sync_variant_fields(self):
        """Synchronize variant fields."""
        for variant in self:
            # Sync effective SKU with default_code
            if variant.effective_sku and variant.default_code != variant.effective_sku:
                super(ProductProduct, variant).write({'default_code': variant.effective_sku})

    def _generate_variant_sku(self, template_sku):
        """Generate unique variant SKU."""
        base_sku = template_sku
        counter = 1
        variant_sku = f"{base_sku}-V{counter:03d}"
        
        while self.search([('variant_sku', '=', variant_sku), ('id', '!=', self.id)], limit=1):
            counter += 1
            variant_sku = f"{base_sku}-V{counter:03d}"
            
        return variant_sku

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @api.constrains('variant_sku')
    def _check_variant_sku_format(self):
        """Validate variant SKU format."""
        for variant in self:
            if variant.variant_sku and variant.template_is_ams_product:
                import re
                if not re.match(r'^[A-Z0-9\-_]+$', variant.variant_sku):
                    raise ValidationError(_("Variant SKU must contain only uppercase letters, numbers, hyphens, and underscores."))

    @api.constrains('variant_member_price', 'variant_non_member_price')
    def _check_variant_pricing(self):
        """Validate variant pricing logic."""
        for variant in self:
            if variant.has_variant_pricing:
                if variant.variant_member_price < 0 or variant.variant_non_member_price < 0:
                    raise ValidationError(_("Variant prices cannot be negative."))
                if variant.variant_member_price > variant.variant_non_member_price:
                    raise ValidationError(_("Variant member price should not be higher than non-member price."))

    @api.constrains('variant_reorder_point', 'variant_max_stock')
    def _check_variant_inventory(self):
        """Validate variant inventory logic."""
        for variant in self:
            if variant.has_variant_inventory_config:
                if variant.variant_reorder_point < 0 or variant.variant_max_stock < 0:
                    raise ValidationError(_("Inventory levels cannot be negative."))
                if variant.variant_reorder_point > variant.variant_max_stock:
                    raise ValidationError(_("Reorder point cannot be higher than maximum stock."))

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def get_variant_price_for_member_status(self, is_member):
        """Get appropriate variant price based on member status."""
        self.ensure_one()
        if self.template_has_member_pricing:
            return self.final_member_price if is_member else self.final_non_member_price
        return self.list_price

    def get_variant_member_savings(self):
        """Calculate variant member savings amount."""
        self.ensure_one()
        if self.template_has_member_pricing:
            return self.final_non_member_price - self.final_member_price
        return 0.0

    def get_variant_digital_content_access(self):
        """Get variant digital content access information."""
        self.ensure_one()
        return {
            'is_digital': self.template_is_digital_product,
            'download_url': self.final_digital_url,
            'attachment_id': self.final_digital_attachment_id.id if self.final_digital_attachment_id else False,
            'auto_fulfill': self.template_auto_fulfill_digital,
            'is_available': self.is_digital_content_available,
            'has_variant_content': self.has_variant_digital_content,
        }

    def get_variant_inventory_status(self):
        """Get variant inventory status information."""
        self.ensure_one()
        return {
            'stock_controlled': self.effective_stock_controlled,
            'current_level': self.current_stock_level,
            'reorder_point': self.variant_reorder_point,
            'max_stock': self.variant_max_stock,
            'needs_reorder': self.variant_needs_reorder,
            'has_variant_config': self.has_variant_inventory_config,
        }

    # ========================================================================
    # VARIANT MANAGEMENT METHODS
    # ========================================================================

    def copy_template_pricing_to_variant(self):
        """Copy template pricing to variant-specific pricing."""
        self.ensure_one()
        if self.template_has_member_pricing:
            self.write({
                'has_variant_pricing': True,
                'variant_member_price': self.template_member_price,
                'variant_non_member_price': self.template_non_member_price,
            })

    def sync_with_template_pricing(self):
        """Reset to template pricing (remove variant overrides)."""
        self.ensure_one()
        self.write({
            'has_variant_pricing': False,
            'variant_member_price': 0.0,
            'variant_non_member_price': 0.0,
        })

    def copy_template_inventory_to_variant(self):
        """Copy template inventory settings to variant."""
        self.ensure_one()
        self.write({
            'has_variant_inventory_config': True,
            'variant_stock_controlled': self.template_stock_controlled,
        })

    # ========================================================================
    # ACTION METHODS (for buttons)
    # ========================================================================

    def action_configure_variant_pricing(self):
        """Open variant pricing configuration form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Variant Pricing',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ams_products_base.product_variant_pricing_form').id,
            'target': 'new',
        }

    def action_configure_variant_digital_content(self):
        """Open variant digital content configuration form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Variant Digital Content',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ams_products_base.product_variant_digital_form').id,
            'target': 'new',
        }

    def action_configure_variant_inventory(self):
        """Open variant inventory configuration form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Variant Inventory',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ams_products_base.product_variant_inventory_form').id,
            'target': 'new',
        }

    def action_view_stock_moves(self):
        """View stock moves for this variant."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_update_stock(self):
        """Update stock levels for this variant."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update Stock',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_view_category(self):
        """Open the product category form."""
        self.ensure_one()
        if not self.product_tmpl_id.categ_id:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Category'),
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.categ_id.id,
            'target': 'current',
        }

    # ========================================================================
    # SEARCH AND DISPLAY METHODS
    # ========================================================================

    def name_get(self):
        """Enhanced name display for AMS variants."""
        result = []
        for variant in self:
            name = super(ProductProduct, variant).name_get()[0][1]
            if variant.template_is_ams_product and variant.effective_sku:
                name = f"[{variant.effective_sku}] {name}"
            result.append((variant.id, name))
        return result

    # ========================================================================
    # BUSINESS QUERY METHODS
    # ========================================================================

    @api.model
    def get_variants_by_ams_criteria(self, is_digital=None, stock_controlled=None, has_member_pricing=None, ams_category_type=None):
        """Get variants by AMS criteria."""
        domain = [('template_is_ams_product', '=', True)]
        
        if is_digital is not None:
            domain.append(('template_is_digital_product', '=', is_digital))
        if stock_controlled is not None:
            domain.append(('effective_stock_controlled', '=', stock_controlled))
        if has_member_pricing is not None:
            domain.append(('template_has_member_pricing', '=', has_member_pricing))
        if ams_category_type is not None:
            domain.append(('template_ams_category_type', '=', ams_category_type))
            
        return self.search(domain)

    @api.model
    def get_low_stock_variants(self):
        """Get variants that need reordering."""
        return self.search([('variant_needs_reorder', '=', True)])

    @api.model 
    def get_digital_content_issues(self):
        """Get digital variants missing content."""
        return self.search([
            ('template_is_digital_product', '=', True),
            ('is_digital_content_available', '=', False)
        ])