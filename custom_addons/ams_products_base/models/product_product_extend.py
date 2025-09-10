# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ProductProduct(models.Model):
    """
    Extend product.product (product variants) with AMS-specific functionality.
    
    This extension adds variant-specific features for association products,
    including individual SKU management, variant-specific pricing, and
    digital content delivery per variant.
    """
    _inherit = 'product.product'

    # ========================================================================
    # VARIANT-SPECIFIC FIELDS
    # ========================================================================
    
    variant_sku = fields.Char(
        string="Variant SKU",
        help="SKU specific to this product variant"
    )
    
    variant_legacy_id = fields.Char(
        string="Variant Legacy ID",
        help="Legacy system ID for this specific variant"
    )
    
    # ========================================================================
    # VARIANT MEMBER PRICING
    # ========================================================================
    
    variant_member_price = fields.Monetary(
        string="Variant Member Price",
        help="Member price override for this specific variant",
        currency_field='currency_id'
    )
    
    variant_non_member_price = fields.Monetary(
        string="Variant Non-member Price",
        help="Non-member price override for this specific variant", 
        currency_field='currency_id'
    )
    
    has_variant_pricing = fields.Boolean(
        string="Has Variant-Specific Pricing",
        help="Does this variant have different pricing from the template?"
    )
    
    # ========================================================================
    # VARIANT DIGITAL CONTENT
    # ========================================================================
    
    variant_digital_url = fields.Char(
        string="Variant Download URL",
        help="Download URL specific to this variant"
    )
    
    variant_digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Variant Digital File",
        help="Digital file specific to this variant"
    )
    
    has_variant_digital_content = fields.Boolean(
        string="Has Variant Digital Content",
        help="Does this variant have specific digital content?"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    effective_sku = fields.Char(
        string="Effective SKU",
        compute='_compute_effective_sku',
        store=True,
        help="The SKU to use (variant SKU or template SKU)"
    )
    
    final_member_price = fields.Monetary(
        string="Final Member Price",
        compute='_compute_final_pricing',
        help="Final member price considering variant overrides"
    )
    
    final_non_member_price = fields.Monetary(
        string="Final Non-member Price",
        compute='_compute_final_pricing',
        help="Final non-member price considering variant overrides"
    )
    
    variant_member_discount = fields.Float(
        string="Variant Member Discount %",
        compute='_compute_variant_discount',
        help="Member discount percentage for this variant"
    )
    
    final_digital_url = fields.Char(
        string="Final Download URL",
        compute='_compute_final_digital_content',
        help="Effective download URL (variant or template)"
    )
    
    final_digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Final Digital File",
        compute='_compute_final_digital_content',
        help="Effective digital file (variant or template)"
    )
    
    is_digital_content_available = fields.Boolean(
        string="Digital Content Available",
        compute='_compute_final_digital_content',
        help="Is digital content available for this variant?"
    )

    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('variant_sku_unique', 'UNIQUE(variant_sku)', 'Variant SKU must be unique!'),
        ('variant_member_price_positive', 'CHECK(variant_member_price >= 0)', 'Variant member price must be positive!'),
        ('variant_non_member_price_positive', 'CHECK(variant_non_member_price >= 0)', 'Variant non-member price must be positive!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    @api.depends('variant_sku', 'product_tmpl_id.sku', 'default_code')
    def _compute_effective_sku(self):
        """Compute the effective SKU to use for this variant."""
        for variant in self:
            if variant.variant_sku:
                variant.effective_sku = variant.variant_sku
            elif variant.product_tmpl_id.sku:
                # If template has SKU but variant doesn't, create variant-specific SKU
                if variant.product_template_attribute_value_ids:
                    # Add attribute values to template SKU
                    attribute_suffix = '-'.join([
                        pav.product_attribute_value_id.name.upper()[:3] 
                        for pav in variant.product_template_attribute_value_ids
                    ])
                    variant.effective_sku = f"{variant.product_tmpl_id.sku}-{attribute_suffix}"
                else:
                    variant.effective_sku = variant.product_tmpl_id.sku
            else:
                variant.effective_sku = variant.default_code or ''
    
    @api.depends('has_variant_pricing', 'variant_member_price', 'variant_non_member_price', 
                 'product_tmpl_id.member_price', 'product_tmpl_id.non_member_price', 'lst_price')
    def _compute_final_pricing(self):
        """Compute final pricing considering variant overrides."""
        for variant in self:
            if variant.has_variant_pricing:
                # Use variant-specific pricing
                variant.final_member_price = variant.variant_member_price or 0.0
                variant.final_non_member_price = variant.variant_non_member_price or variant.lst_price
            else:
                # Use template pricing
                variant.final_member_price = variant.product_tmpl_id.effective_member_price
                variant.final_non_member_price = variant.product_tmpl_id.effective_non_member_price
    
    @api.depends('final_member_price', 'final_non_member_price')
    def _compute_variant_discount(self):
        """Calculate member discount percentage for this variant."""
        for variant in self:
            if variant.final_non_member_price > 0:
                discount = (variant.final_non_member_price - variant.final_member_price) / variant.final_non_member_price * 100
                variant.variant_member_discount = max(0, discount)
            else:
                variant.variant_member_discount = 0.0
    
    @api.depends('has_variant_digital_content', 'variant_digital_url', 'variant_digital_attachment_id',
                 'product_tmpl_id.digital_download_url', 'product_tmpl_id.digital_attachment_id')
    def _compute_final_digital_content(self):
        """Compute final digital content considering variant overrides."""
        for variant in self:
            if variant.has_variant_digital_content:
                # Use variant-specific digital content
                variant.final_digital_url = variant.variant_digital_url
                variant.final_digital_attachment_id = variant.variant_digital_attachment_id
            else:
                # Use template digital content
                variant.final_digital_url = variant.product_tmpl_id.digital_download_url
                variant.final_digital_attachment_id = variant.product_tmpl_id.digital_attachment_id
            
            # Check if digital content is available
            variant.is_digital_content_available = bool(
                variant.final_digital_url or variant.final_digital_attachment_id
            )

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('variant_sku')
    def _check_variant_sku_format(self):
        """Validate variant SKU format."""
        for variant in self:
            if variant.variant_sku:
                import re
                if not re.match(r'^[A-Za-z0-9_-]+$', variant.variant_sku):
                    raise ValidationError(_("Variant SKU can only contain letters, numbers, hyphens, and underscores"))
                if len(variant.variant_sku) > 50:
                    raise ValidationError(_("Variant SKU cannot be longer than 50 characters"))
    
    @api.constrains('variant_digital_url')
    def _check_variant_digital_url(self):
        """Validate variant digital download URL format."""
        for variant in self:
            if variant.variant_digital_url:
                import re
                url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
                if not re.match(url_pattern, variant.variant_digital_url):
                    raise ValidationError(_("Please enter a valid download URL (must start with http:// or https://)"))
    
    @api.constrains('variant_member_price', 'variant_non_member_price', 'has_variant_pricing')
    def _check_variant_pricing_logic(self):
        """Validate variant pricing configuration."""
        for variant in self:
            if variant.has_variant_pricing:
                if not variant.variant_member_price and not variant.variant_non_member_price:
                    raise ValidationError(_("Variants with specific pricing must have at least one price set"))
                
                if variant.variant_member_price and variant.variant_non_member_price:
                    if variant.variant_member_price > variant.variant_non_member_price:
                        raise ValidationError(_("Variant member price should not be higher than non-member price"))

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('has_variant_pricing')
    def _onchange_has_variant_pricing(self):
        """Handle variant pricing flag changes."""
        if not self.has_variant_pricing:
            # Clear variant-specific prices
            self.variant_member_price = 0.0
            self.variant_non_member_price = 0.0
        else:
            # Set defaults from template if available
            if not self.variant_member_price and self.product_tmpl_id.member_price:
                self.variant_member_price = self.product_tmpl_id.member_price
            if not self.variant_non_member_price and self.product_tmpl_id.non_member_price:
                self.variant_non_member_price = self.product_tmpl_id.non_member_price
    
    @api.onchange('has_variant_digital_content')
    def _onchange_has_variant_digital_content(self):
        """Handle variant digital content flag changes."""
        if not self.has_variant_digital_content:
            # Clear variant-specific digital content
            self.variant_digital_url = False
            self.variant_digital_attachment_id = False
    
    @api.onchange('variant_non_member_price')
    def _onchange_variant_non_member_price(self):
        """Auto-set list price when variant non-member price changes."""
        if self.has_variant_pricing and self.variant_non_member_price:
            self.lst_price = self.variant_non_member_price

    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle AMS variant-specific logic."""
        for vals in vals_list:
            # Auto-generate variant SKU if not provided
            if not vals.get('variant_sku') and not vals.get('default_code'):
                template_id = vals.get('product_tmpl_id')
                if template_id:
                    template = self.env['product.template'].browse(template_id)
                    if template.sku:
                        vals['variant_sku'] = self._generate_variant_sku(template, vals)
        
        return super().create(vals_list)

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def get_variant_price_for_member_status(self, is_member=False):
        """
        Get the appropriate variant price based on member status.
        
        Args:
            is_member (bool): Whether the customer is a member
            
        Returns:
            float: Appropriate price for the member status
        """
        self.ensure_one()
        
        if self.product_tmpl_id.has_member_pricing:
            if is_member:
                return self.final_member_price
            else:
                return self.final_non_member_price
        else:
            return self.lst_price
    
    def get_variant_member_savings(self):
        """
        Calculate absolute savings for members on this variant.
        
        Returns:
            float: Amount saved by being a member
        """
        self.ensure_one()
        
        if self.product_tmpl_id.has_member_pricing:
            return self.final_non_member_price - self.final_member_price
        return 0.0
    
    def get_variant_digital_content_access(self):
        """
        Get digital content access information for this variant.
        
        Returns:
            dict: Digital content access details
        """
        self.ensure_one()
        
        if not self.product_tmpl_id.is_digital_product:
            return {}
        
        return {
            'is_digital': True,
            'download_url': self.final_digital_url,
            'attachment_id': self.final_digital_attachment_id.id if self.final_digital_attachment_id else False,
            'auto_fulfill': self.product_tmpl_id.auto_fulfill_digital,
            'is_available': self.is_digital_content_available,
            'has_variant_content': self.has_variant_digital_content,
        }
    
    def get_variant_display_name(self):
        """
        Get display name including variant attributes and AMS info.
        
        Returns:
            str: Enhanced display name
        """
        self.ensure_one()
        
        name = self.display_name
        
        # Add effective SKU
        if self.effective_sku:
            name = f"[{self.effective_sku}] {name}"
        
        # Add digital indicator
        if self.product_tmpl_id.is_digital_product:
            name = f"{name} (Digital)"
        
        # Add member pricing indicator
        if self.product_tmpl_id.has_member_pricing:
            if self.has_variant_pricing:
                name = f"{name} (Variant Pricing)"
            else:
                name = f"{name} (Member Pricing)"
        
        return name
    
    @api.model
    def get_variants_by_ams_criteria(self, is_digital=None, has_member_pricing=None, 
                                   requires_membership=None, product_type_code=None):
        """
        Get product variants filtered by AMS criteria.
        
        Args:
            is_digital (bool, optional): Filter by digital products
            has_member_pricing (bool, optional): Filter by member pricing
            requires_membership (bool, optional): Filter by membership requirement
            product_type_code (str, optional): Filter by product type code
            
        Returns:
            recordset: Filtered product variants
        """
        domain = []
        
        if is_digital is not None:
            domain.append(('product_tmpl_id.is_digital_product', '=', is_digital))
        
        if has_member_pricing is not None:
            domain.append(('product_tmpl_id.has_member_pricing', '=', has_member_pricing))
        
        if requires_membership is not None:
            domain.append(('product_tmpl_id.requires_membership', '=', requires_membership))
        
        if product_type_code:
            domain.append(('product_tmpl_id.ams_product_type_id.code', '=', product_type_code))
        
        return self.search(domain)
    
    def action_configure_variant_pricing(self):
        """Open variant pricing configuration."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Variant Pricing'),
            'res_model': 'product.product',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_ref': 'ams_products_base.product_variant_pricing_form'},
        }
    
    def action_configure_variant_digital_content(self):
        """Open variant digital content configuration."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Variant Digital Content'),
            'res_model': 'product.product', 
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_ref': 'ams_products_base.product_variant_digital_form'},
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @api.model
    def _generate_variant_sku(self, template, vals):
        """
        Generate SKU for a product variant.
        
        Args:
            template (product.template): Product template
            vals (dict): Values being created
            
        Returns:
            str: Generated variant SKU
        """
        if not template.sku:
            return ''
        
        base_sku = template.sku
        
        # Add attribute values if this is a variant with attributes
        # Note: This is simplified - in practice you'd need to look up the actual attributes
        # based on product_template_attribute_value_ids in vals
        
        counter = 1
        variant_sku = f"{base_sku}-V{counter:02d}"
        
        # Ensure uniqueness
        while self.search([('variant_sku', '=', variant_sku)], limit=1):
            counter += 1
            variant_sku = f"{base_sku}-V{counter:02d}"
            if counter > 999:  # Prevent infinite loop
                break
        
        return variant_sku
    
    def _get_variant_pricing_context(self, partner_id=None):
        """
        Get pricing context for this variant based on partner.
        
        Args:
            partner_id (int, optional): Partner ID to check member status
            
        Returns:
            dict: Variant pricing context information
        """
        self.ensure_one()
        
        context = {
            'product_id': self.id,
            'template_id': self.product_tmpl_id.id,
            'has_member_pricing': self.product_tmpl_id.has_member_pricing,
            'has_variant_pricing': self.has_variant_pricing,
            'requires_membership': self.product_tmpl_id.requires_membership,
            'effective_sku': self.effective_sku,
        }
        
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            is_member = getattr(partner, 'is_member', False)
            
            context.update({
                'partner_id': partner_id,
                'is_member': is_member,
                'can_purchase': self.product_tmpl_id.can_be_purchased_by_member_status(is_member),
                'effective_price': self.get_variant_price_for_member_status(is_member),
                'member_savings': self.get_variant_member_savings() if is_member else 0.0,
                'digital_access': self.get_variant_digital_content_access() if self.product_tmpl_id.is_digital_product else {},
            })
        
        return context
    
    def sync_with_template_pricing(self):
        """Sync variant pricing with template pricing."""
        for variant in self:
            if not variant.has_variant_pricing:
                # Reset to use template pricing
                variant.write({
                    'variant_member_price': 0.0,
                    'variant_non_member_price': 0.0,
                })
    
    def copy_template_pricing_to_variant(self):
        """Copy template pricing to variant-specific pricing."""
        for variant in self:
            variant.write({
                'has_variant_pricing': True,
                'variant_member_price': variant.product_tmpl_id.member_price,
                'variant_non_member_price': variant.product_tmpl_id.non_member_price,
            })
    
    def name_get(self):
        """Custom name display for AMS product variants."""
        result = []
        for variant in self:
            name = super(ProductProduct, variant).name_get()[0][1]
            
            # Add effective SKU if different from what's already shown
            if variant.effective_sku and f"[{variant.effective_sku}]" not in name:
                name = f"[{variant.effective_sku}] {name}"
            
            # Add variant-specific indicators
            indicators = []
            if variant.has_variant_pricing:
                indicators.append("Variant Pricing")
            if variant.has_variant_digital_content:
                indicators.append("Variant Digital")
            
            if indicators:
                name = f"{name} ({', '.join(indicators)})"
            
            result.append((variant.id, name))
        
        return result