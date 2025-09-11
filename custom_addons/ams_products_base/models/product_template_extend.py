# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ========================================================================
    # AMS CORE FIELDS
    # ========================================================================

    is_ams_product = fields.Boolean(
        string="AMS Product",
        default=False,
        help="Mark this product as an AMS-managed product with enhanced features"
    )

    ams_product_type_id = fields.Many2one(
        'ams.product.type',
        string="AMS Product Type",
        help="AMS-specific product type that drives business rules and defaults"
    )

    sku = fields.Char(
        string="SKU",
        size=64,
        help="Stock Keeping Unit - unique product identifier. Auto-generated if left blank."
    )

    legacy_product_id = fields.Char(
        string="Legacy Product ID",
        size=32,
        help="Product ID from legacy/external systems for data migration"
    )

    # ========================================================================
    # MEMBER PRICING FIELDS
    # ========================================================================

    has_member_pricing = fields.Boolean(
        string="Member Pricing",
        default=False,
        help="Enable different pricing for members vs non-members"
    )

    member_price = fields.Float(
        string="Member Price",
        digits='Product Price',
        help="Price for association members"
    )

    non_member_price = fields.Float(
        string="Non-Member Price", 
        digits='Product Price',
        help="Price for non-members"
    )

    # ========================================================================
    # DIGITAL PRODUCT FIELDS
    # ========================================================================

    is_digital_product = fields.Boolean(
        string="Digital Product",
        default=False,
        help="Product delivered digitally (downloads, online access)"
    )

    digital_download_url = fields.Char(
        string="Download URL",
        size=255,
        help="URL for digital product download"
    )

    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Digital File",
        help="File attachment for digital product delivery"
    )

    auto_fulfill_digital = fields.Boolean(
        string="Auto-fulfill Digital",
        default=True,
        help="Automatically provide digital content upon purchase"
    )

    # ========================================================================
    # INVENTORY & FULFILLMENT FIELDS
    # ========================================================================

    stock_controlled = fields.Boolean(
        string="Stock Controlled",
        default=False,
        help="Enable inventory tracking and stock management"
    )

    ams_fulfillment_route_id = fields.Many2one(
        'stock.location.route',
        string="AMS Fulfillment Route",
        help="Specific fulfillment route for this AMS product",
        domain=lambda self: [('product_selectable', '=', True)],
    )

    # ========================================================================
    # ACCESS CONTROL FIELDS
    # ========================================================================

    requires_membership = fields.Boolean(
        string="Requires Membership",
        default=False,
        help="Only association members can purchase this product"
    )

    chapter_specific = fields.Boolean(
        string="Chapter Specific",
        default=False,
        help="Product is restricted to specific chapters"
    )

    # Note: Commented out until ams.chapter model is available
    # allowed_chapter_ids = fields.Many2many(
    #     'ams.chapter',
    #     string="Allowed Chapters",
    #     help="Chapters that can access this product"
    # )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('member_price', 'non_member_price')
    def _compute_member_discount_percentage(self):
        """Calculate member discount percentage."""
        for record in self:
            if record.non_member_price and record.member_price:
                discount = (record.non_member_price - record.member_price) / record.non_member_price * 100
                record.member_discount_percentage = max(0, discount)
            else:
                record.member_discount_percentage = 0.0

    member_discount_percentage = fields.Float(
        string="Member Discount %",
        compute='_compute_member_discount_percentage',
        store=True,
        help="Percentage discount for members"
    )

    @api.depends('has_member_pricing', 'member_price', 'non_member_price', 'list_price')
    def _compute_effective_prices(self):
        """Calculate effective pricing based on configuration."""
        for record in self:
            if record.has_member_pricing and record.member_price:
                record.effective_member_price = record.member_price
            else:
                record.effective_member_price = record.list_price

            if record.has_member_pricing and record.non_member_price:
                record.effective_non_member_price = record.non_member_price
            else:
                record.effective_non_member_price = record.list_price

    effective_member_price = fields.Monetary(
        string="Effective Member Price",
        compute='_compute_effective_prices',
        store=True
    )

    effective_non_member_price = fields.Monetary(
        string="Effective Non-Member Price", 
        compute='_compute_effective_prices',
        store=True
    )

    @api.depends('has_member_pricing', 'effective_member_price', 'effective_non_member_price')
    def _compute_pricing_summary(self):
        """Generate pricing summary text."""
        for record in self:
            if record.has_member_pricing:
                member_price = record.effective_member_price or 0
                non_member_price = record.effective_non_member_price or 0
                currency = record.currency_id.symbol or ''
                record.pricing_summary = f"Members: {currency}{member_price:.2f} | Non-members: {currency}{non_member_price:.2f}"
            else:
                record.pricing_summary = ""

    pricing_summary = fields.Char(
        string="Pricing Summary",
        compute='_compute_pricing_summary',
        store=True
    )

    @api.depends('digital_download_url', 'digital_attachment_id', 'is_digital_product')
    def _compute_is_digital_available(self):
        """Check if digital content is available."""
        for record in self:
            if record.is_digital_product:
                record.is_digital_available = bool(record.digital_download_url or record.digital_attachment_id)
            else:
                record.is_digital_available = False

    is_digital_available = fields.Boolean(
        string="Digital Content Available",
        compute='_compute_is_digital_available',
        store=True
    )

    @api.depends('is_digital_product', 'stock_controlled', 'is_digital_available')
    def _compute_inventory_status(self):
        """Calculate inventory status."""
        for record in self:
            if record.is_digital_product:
                if record.is_digital_available:
                    record.inventory_status = 'digital'
                else:
                    record.inventory_status = 'digital_missing'
            elif record.stock_controlled:
                record.inventory_status = 'tracked'
            else:
                record.inventory_status = 'service'

    inventory_status = fields.Selection([
        ('service', 'Service'),
        ('tracked', 'Inventory Tracked'),
        ('digital', 'Digital Available'),
        ('digital_missing', 'Digital Content Missing'),
    ], string="Inventory Status", compute='_compute_inventory_status', store=True)

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('ams_product_type_id')
    def _onchange_ams_product_type(self):
        """Update fields based on selected AMS product type."""
        if self.ams_product_type_id:
            # Safe access to product type fields
            product_type = self.ams_product_type_id
            
            # Set member pricing if required by product type
            if hasattr(product_type, 'requires_member_pricing'):
                self.has_member_pricing = product_type.requires_member_pricing
            
            # Set digital product if specified by product type  
            if hasattr(product_type, 'is_digital'):
                self.is_digital_product = product_type.is_digital
            
            # Set inventory tracking if required by product type
            if hasattr(product_type, 'requires_inventory'):
                self.stock_controlled = product_type.requires_inventory
                
            # Set product category if specified
            if hasattr(product_type, 'product_category_id') and product_type.product_category_id:
                self.categ_id = product_type.product_category_id
            
            # Set Odoo product type based on AMS configuration
            if self.is_digital_product or not self.stock_controlled:
                self.type = 'service'
            else:
                self.type = 'product'

    @api.onchange('is_ams_product')
    def _onchange_is_ams_product(self):
        """Clear AMS fields when unmarking as AMS product."""
        if not self.is_ams_product:
            self.ams_product_type_id = False
            self.has_member_pricing = False
            self.is_digital_product = False
            self.requires_membership = False
            self.chapter_specific = False

    @api.onchange('is_digital_product')
    def _onchange_is_digital_product(self):
        """Update product type when digital product changes."""
        if self.is_digital_product:
            self.type = 'service'
            self.stock_controlled = False
        elif self.stock_controlled:
            self.type = 'product'

    @api.onchange('stock_controlled')
    def _onchange_stock_controlled(self):
        """Update product type when stock control changes."""
        if self.stock_controlled and not self.is_digital_product:
            self.type = 'product'
        elif not self.stock_controlled:
            self.type = 'service'

    @api.onchange('has_member_pricing')
    def _onchange_has_member_pricing(self):
        """Set default member pricing when enabled."""
        if self.has_member_pricing and not self.member_price and self.list_price:
            # Default to 20% member discount
            self.member_price = self.list_price * 0.8
            self.non_member_price = self.list_price

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate SKUs and sync fields."""
        for vals in vals_list:
            # Generate SKU if not provided for AMS products
            if vals.get('is_ams_product') and not vals.get('sku'):
                vals['sku'] = self._generate_sku(vals.get('name', ''))
            
            # Sync SKU with default_code
            if vals.get('sku'):
                vals['default_code'] = vals['sku']

        products = super().create(vals_list)
        
        for product in products:
            product._sync_ams_fields()
        
        return products

    def write(self, vals):
        """Override write to maintain field synchronization."""
        # Sync SKU with default_code
        if vals.get('sku'):
            vals['default_code'] = vals['sku']
        elif vals.get('default_code') and not vals.get('sku'):
            vals['sku'] = vals['default_code']

        result = super().write(vals)
        
        # Sync AMS fields if relevant fields changed
        if any(field in vals for field in ['ams_product_type_id', 'is_ams_product', 'is_digital_product', 'stock_controlled']):
            for product in self:
                product._sync_ams_fields()
                
        return result

    def _sync_ams_fields(self):
        """Synchronize AMS fields with Odoo fields."""
        for product in self:
            vals = {}
            
            # Sync product type
            if product.is_digital_product or not product.stock_controlled:
                vals['type'] = 'service'
            elif product.stock_controlled:
                vals['type'] = 'product'
            
            # Generate SKU if missing
            if product.is_ams_product and not product.sku:
                vals['sku'] = product._generate_sku(product.name)
                vals['default_code'] = vals['sku']
            
            if vals:
                super(ProductTemplate, product).write(vals)

    def _generate_sku(self, name):
        """Generate SKU from product name."""
        if not name:
            name = "PRODUCT"
        
        # Clean name and create base SKU
        base_sku = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        base_sku = re.sub(r'\s+', '-', base_sku.strip().upper())
        base_sku = base_sku[:20]  # Limit length
        
        # Ensure uniqueness
        counter = 1
        sku = base_sku
        while self.search([('sku', '=', sku), ('id', '!=', self.id)], limit=1):
            sku = f"{base_sku}-{counter:03d}"
            counter += 1
            
        return sku

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @api.constrains('sku')
    def _check_sku_format(self):
        """Validate SKU format."""
        for record in self:
            if record.sku and record.is_ams_product:
                if not re.match(r'^[A-Z0-9\-_]+$', record.sku):
                    raise ValidationError(_("SKU must contain only uppercase letters, numbers, hyphens, and underscores."))

    @api.constrains('digital_download_url')
    def _check_digital_url(self):
        """Validate digital download URL format."""
        for record in self:
            if record.digital_download_url:
                if not record.digital_download_url.startswith(('http://', 'https://')):
                    raise ValidationError(_("Digital download URL must start with http:// or https://"))

    @api.constrains('member_price', 'non_member_price')
    def _check_member_pricing(self):
        """Validate member pricing logic."""
        for record in self:
            if record.has_member_pricing:
                if record.member_price < 0 or record.non_member_price < 0:
                    raise ValidationError(_("Prices cannot be negative."))
                if record.member_price > record.non_member_price:
                    raise ValidationError(_("Member price should not be higher than non-member price."))

    @api.constrains('is_digital_product', 'digital_download_url', 'digital_attachment_id')
    def _check_digital_content(self):
        """Validate digital product content."""
        for record in self:
            if record.is_digital_product:
                if not record.digital_download_url and not record.digital_attachment_id:
                    raise ValidationError(_("Digital products must have either a download URL or file attachment."))

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def get_price_for_member_status(self, is_member):
        """Get appropriate price based on member status."""
        self.ensure_one()
        if self.has_member_pricing:
            return self.effective_member_price if is_member else self.effective_non_member_price
        return self.list_price

    def get_member_savings(self):
        """Calculate member savings amount."""
        self.ensure_one()
        if self.has_member_pricing:
            return self.effective_non_member_price - self.effective_member_price
        return 0.0

    def can_be_purchased_by_member_status(self, is_member):
        """Check if product can be purchased by member status."""
        self.ensure_one()
        if self.requires_membership and not is_member:
            return False
        return True

    def get_digital_content_access(self):
        """Get digital content access information."""
        self.ensure_one()
        return {
            'is_digital': self.is_digital_product,
            'download_url': self.digital_download_url,
            'attachment_id': self.digital_attachment_id.id if self.digital_attachment_id else False,
            'auto_fulfill': self.auto_fulfill_digital,
            'is_available': self.is_digital_available,
        }

    def _get_pricing_context(self, partner_id=None):
        """Get pricing context for a partner."""
        self.ensure_one()
        context = {
            'product_id': self.id,
            'has_member_pricing': self.has_member_pricing,
            'requires_membership': self.requires_membership,
        }
        
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            # Safe access to partner fields
            is_member = getattr(partner, 'is_member', False)
            membership_status = getattr(partner, 'membership_status', 'prospect')
            
            context.update({
                'partner_id': partner_id,
                'is_member': is_member,
                'membership_status': membership_status,
                'can_purchase': self.can_be_purchased_by_member_status(is_member),
                'effective_price': self.get_price_for_member_status(is_member),
                'member_savings': self.get_member_savings() if is_member else 0.0,
            })
        
        return context

    # ========================================================================
    # SEARCH AND DISPLAY METHODS
    # ========================================================================

    def name_get(self):
        """Enhanced name display for AMS products."""
        result = []
        for product in self:
            name = product.name
            if product.is_ams_product:
                name_parts = [f"[{product.sku}]" if product.sku else "", product.name]
                if product.is_digital_product:
                    name_parts.append("(Digital)")
                if product.has_member_pricing:
                    name_parts.append("(Member Pricing)")
                name = " ".join(filter(None, name_parts))
            result.append((product.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Enhanced name search including SKU."""
        if args is None:
            args = []
        
        # Search by SKU if it looks like one
        if name and not operator == '=':
            sku_domain = [('sku', 'ilike', name)]
            sku_results = self.search(sku_domain + args, limit=limit)
            if sku_results:
                return sku_results.name_get()
        
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    # ========================================================================
    # BUSINESS QUERY METHODS
    # ========================================================================

    @api.model
    def get_ams_products_by_type(self, product_type_category=None):
        """Get AMS products optionally filtered by type category."""
        domain = [('is_ams_product', '=', True)]
        if product_type_category:
            domain.append(('ams_product_type_id.category', '=', product_type_category))
        return self.search(domain)

    @api.model 
    def get_digital_products(self):
        """Get all digital products."""
        return self.search([('is_digital_product', '=', True)])

    @api.model
    def get_member_pricing_products(self):
        """Get all products with member pricing."""
        return self.search([('has_member_pricing', '=', True)])

    @api.model
    def get_membership_required_products(self):
        """Get all products that require membership."""
        return self.search([('requires_membership', '=', True)])

    def action_view_variants(self):
        """Open product variants for this template."""
        self.ensure_one()
        action = self.env.ref('product.product_variant_action').read()[0]
        
        # Filter to only show variants for the current template
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        
        # If there’s only one variant, open the form view directly
        if len(self.product_variant_ids) == 1:
            form_view = [(self.env.ref('product.product_normal_form_view').id, 'form')]
            action['views'] = form_view
            action['res_id'] = self.product_variant_ids.id
        
        return action