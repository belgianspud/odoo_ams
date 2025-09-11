# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import re


class ProductTemplate(models.Model):
    """
    Extend product.template with AMS-specific functionality for association products.
    
    This extension adds member pricing, digital product support, chapter restrictions,
    and other association-specific features while maintaining compatibility with
    standard Odoo product functionality.
    """
    _inherit = 'product.template'

    # ========================================================================
    # AMS PRODUCT CLASSIFICATION
    # ========================================================================
    
    ams_product_type_id = fields.Many2one(
        'ams.product.type',
        string="AMS Product Type",
        help="AMS-specific product type classification"
    )
    
    is_ams_product = fields.Boolean(
        string="AMS Product",
        default=True,
        help="Is this an association-managed product?"
    )
    
    # ========================================================================
    # MEMBER PRICING
    # ========================================================================
    
    has_member_pricing = fields.Boolean(
        string="Has Member Pricing",
        help="Does this product offer different pricing for members vs non-members?"
    )
    
    member_price = fields.Monetary(
        string="Member Price",
        help="Special pricing for association members",
        currency_field='currency_id'
    )
    
    non_member_price = fields.Monetary(
        string="Non-member Price", 
        help="Standard pricing for non-members",
        currency_field='currency_id'
    )
    
    member_discount_percentage = fields.Float(
        string="Member Discount %",
        compute='_compute_member_discount',
        store=True,
        help="Percentage discount for members compared to non-member price"
    )
    
    # ========================================================================
    # PRODUCT FEATURES
    # ========================================================================
    
    requires_membership = fields.Boolean(
        string="Requires Membership",
        help="Can only be purchased by active association members"
    )
    
    is_digital_product = fields.Boolean(
        string="Digital Product",
        help="Product is delivered digitally (download, online access)"
    )
    
    digital_download_url = fields.Char(
        string="Download URL",
        help="URL for digital product download or access"
    )
    
    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Digital File",
        help="Attached file for digital product delivery"
    )
    
    # ========================================================================
    # INVENTORY & FULFILLMENT
    # ========================================================================
    
    stock_controlled = fields.Boolean(
        string="Track Inventory",
        help="Should this product's stock be tracked?"
    )
    
    auto_fulfill_digital = fields.Boolean(
        string="Auto-fulfill Digital Products",
        default=True,
        help="Automatically provide access/download upon payment"
    )
    
    # ========================================================================
    # CHAPTER RESTRICTIONS
    # ========================================================================
    # Note: ams.chapter model may not exist yet, so we'll make this optional
    
    chapter_specific = fields.Boolean(
        string="Chapter Restricted",
        help="Is this product restricted to specific chapters?"
    )
    
    # TODO: Uncomment when ams.chapter model is available
    # allowed_chapter_ids = fields.Many2many(
    #     'ams.chapter',
    #     string="Allowed Chapters",
    #     help="Chapters that can access this product"
    # )
    
    # ========================================================================
    # SKU AND LEGACY
    # ========================================================================
    
    sku = fields.Char(
        string="SKU",
        help="Stock Keeping Unit identifier"
    )
    
    legacy_product_id = fields.Char(
        string="Legacy Product ID",
        help="Product ID from previous system for migration"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    effective_member_price = fields.Monetary(
        string="Effective Member Price",
        compute='_compute_effective_prices',
        help="The actual price members will pay"
    )
    
    effective_non_member_price = fields.Monetary(
        string="Effective Non-member Price", 
        compute='_compute_effective_prices',
        help="The actual price non-members will pay"
    )
    
    is_digital_available = fields.Boolean(
        string="Digital Content Available",
        compute='_compute_digital_availability',
        help="Is digital content configured and available?"
    )
    
    pricing_summary = fields.Char(
        string="Pricing Summary",
        compute='_compute_pricing_summary',
        help="Human-readable pricing information"
    )

    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('sku_unique', 'UNIQUE(sku)', 'SKU must be unique across all products!'),
        ('member_price_positive', 'CHECK(member_price >= 0)', 'Member price must be positive!'),
        ('non_member_price_positive', 'CHECK(non_member_price >= 0)', 'Non-member price must be positive!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    @api.depends('member_price', 'non_member_price')
    def _compute_member_discount(self):
        """Calculate member discount percentage."""
        for product in self:
            if product.has_member_pricing and product.non_member_price > 0:
                discount = (product.non_member_price - product.member_price) / product.non_member_price * 100
                product.member_discount_percentage = max(0, discount)
            else:
                product.member_discount_percentage = 0.0
    
    @api.depends('has_member_pricing', 'member_price', 'non_member_price', 'list_price')
    def _compute_effective_prices(self):
        """Compute the effective prices for members and non-members."""
        for product in self:
            if product.has_member_pricing:
                product.effective_member_price = product.member_price or 0.0
                product.effective_non_member_price = product.non_member_price or product.list_price
            else:
                # No member pricing - everyone pays the same
                product.effective_member_price = product.list_price
                product.effective_non_member_price = product.list_price
    
    @api.depends('is_digital_product', 'digital_download_url', 'digital_attachment_id')
    def _compute_digital_availability(self):
        """Check if digital content is properly configured."""
        for product in self:
            if product.is_digital_product:
                product.is_digital_available = bool(
                    product.digital_download_url or product.digital_attachment_id
                )
            else:
                product.is_digital_available = False
    
    @api.depends('has_member_pricing', 'effective_member_price', 'effective_non_member_price')
    def _compute_pricing_summary(self):
        """Generate human-readable pricing summary."""
        for product in self:
            if product.has_member_pricing:
                currency = product.currency_id.symbol or ''
                member_price = product.effective_member_price
                non_member_price = product.effective_non_member_price
                
                if member_price != non_member_price:
                    product.pricing_summary = f"Members: {currency}{member_price:.2f} | Non-members: {currency}{non_member_price:.2f}"
                else:
                    product.pricing_summary = f"All: {currency}{member_price:.2f}"
            else:
                currency = product.currency_id.symbol or ''
                product.pricing_summary = f"All: {currency}{product.list_price:.2f}"

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('sku')
    def _check_sku_format(self):
        """Validate SKU format."""
        for product in self:
            if product.sku:
                # SKU should be alphanumeric with hyphens and underscores allowed
                if not re.match(r'^[A-Za-z0-9_-]+$', product.sku):
                    raise ValidationError(_("SKU can only contain letters, numbers, hyphens, and underscores"))
                if len(product.sku) > 50:
                    raise ValidationError(_("SKU cannot be longer than 50 characters"))
    
    @api.constrains('digital_download_url')
    def _check_digital_url(self):
        """Validate digital download URL format."""
        for product in self:
            if product.digital_download_url:
                # Basic URL validation
                url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
                if not re.match(url_pattern, product.digital_download_url):
                    raise ValidationError(_("Please enter a valid download URL (must start with http:// or https://)"))
    
    @api.constrains('member_price', 'non_member_price', 'has_member_pricing')
    def _check_member_pricing_logic(self):
        """Validate member pricing configuration."""
        for product in self:
            if product.has_member_pricing:
                if not product.member_price and not product.non_member_price:
                    raise ValidationError(_("Products with member pricing must have at least one price set"))
                
                if product.member_price and product.non_member_price:
                    if product.member_price > product.non_member_price:
                        raise ValidationError(_("Member price should not be higher than non-member price"))
    
    @api.constrains('is_digital_product', 'digital_download_url', 'digital_attachment_id')
    def _check_digital_product_config(self):
        """Validate digital product configuration."""
        for product in self:
            if product.is_digital_product:
                if not product.digital_download_url and not product.digital_attachment_id:
                    raise ValidationError(_("Digital products must have either a download URL or attached file"))

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('ams_product_type_id')
    def _onchange_ams_product_type(self):
        """Set product attributes based on AMS product type."""
        if self.ams_product_type_id:
            # Set digital product flag from product type
            self.is_digital_product = self.ams_product_type_id.is_digital
            
            # Set member pricing flag from product type
            self.has_member_pricing = self.ams_product_type_id.requires_member_pricing
            
            # Set inventory tracking from product type
            self.stock_controlled = self.ams_product_type_id.requires_inventory
            
            # Set product type (service vs storable) based on inventory requirements
            if not self.ams_product_type_id.requires_inventory:
                self.type = 'service'
            else:
                self.type = 'product'
    
    @api.onchange('has_member_pricing')
    def _onchange_has_member_pricing(self):
        """Handle member pricing flag changes."""
        if not self.has_member_pricing:
            # Clear member-specific prices
            self.member_price = 0.0
            self.non_member_price = 0.0
        else:
            # Set default non-member price to current list price
            if not self.non_member_price and self.list_price:
                self.non_member_price = self.list_price
    
    @api.onchange('is_digital_product')
    def _onchange_is_digital_product(self):
        """Handle digital product flag changes."""
        if self.is_digital_product:
            # Digital products typically don't need inventory tracking
            self.stock_controlled = False
            self.type = 'service'
            self.auto_fulfill_digital = True
        else:
            # Clear digital-specific fields
            self.digital_download_url = False
            self.digital_attachment_id = False
            self.auto_fulfill_digital = False
    
    @api.onchange('stock_controlled')
    def _onchange_stock_controlled(self):
        """Handle inventory tracking changes."""
        if self.stock_controlled:
            self.type = 'product'  # Storable product
        else:
            self.type = 'service'  # Service/non-storable
    
    @api.onchange('non_member_price')
    def _onchange_non_member_price(self):
        """Auto-set list price when non-member price changes."""
        if self.has_member_pricing and self.non_member_price:
            # Set list price to non-member price as default
            self.list_price = self.non_member_price

    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle AMS-specific logic."""
        for vals in vals_list:
            # Auto-generate SKU if not provided
            if not vals.get('sku') and vals.get('name'):
                vals['sku'] = self._generate_sku(vals['name'])
            
            # Set default pricing if member pricing is enabled
            if vals.get('has_member_pricing') and not vals.get('member_price') and vals.get('list_price'):
                # Default member price to 80% of list price
                vals['member_price'] = vals['list_price'] * 0.8
                vals['non_member_price'] = vals['list_price']
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to handle AMS-specific logic."""
        # Handle SKU generation if name changes and no SKU exists
        if 'name' in vals:
            for product in self:
                if not product.sku and not vals.get('sku'):
                    vals['sku'] = self._generate_sku(vals.get('name', product.name))
        
        return super().write(vals)

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def get_price_for_member_status(self, is_member=False):
        """
        Get the appropriate price based on member status.
        
        Args:
            is_member (bool): Whether the customer is a member
            
        Returns:
            float: Appropriate price for the member status
        """
        self.ensure_one()
        
        if self.has_member_pricing:
            if is_member:
                return self.effective_member_price
            else:
                return self.effective_non_member_price
        else:
            return self.list_price
    
    def get_member_savings(self):
        """
        Calculate absolute savings for members.
        
        Returns:
            float: Amount saved by being a member
        """
        self.ensure_one()
        
        if self.has_member_pricing:
            return self.effective_non_member_price - self.effective_member_price
        return 0.0
    
    def can_be_purchased_by_member_status(self, is_member=False):
        """
        Check if product can be purchased based on member status.
        
        Args:
            is_member (bool): Whether the customer is a member
            
        Returns:
            bool: Whether purchase is allowed
        """
        self.ensure_one()
        
        if self.requires_membership and not is_member:
            return False
        return True
    
    def get_digital_content_access(self):
        """
        Get digital content access information.
        
        Returns:
            dict: Digital content access details
        """
        self.ensure_one()
        
        if not self.is_digital_product:
            return {}
        
        return {
            'is_digital': True,
            'download_url': self.digital_download_url,
            'attachment_id': self.digital_attachment_id.id if self.digital_attachment_id else False,
            'auto_fulfill': self.auto_fulfill_digital,
            'is_available': self.is_digital_available,
        }
    
    @api.model
    def get_ams_products_by_type(self, product_type_code=None):
        """
        Get AMS products filtered by product type.
        
        Args:
            product_type_code (str, optional): Product type code to filter by
            
        Returns:
            recordset: Filtered AMS products
        """
        domain = [('is_ams_product', '=', True)]
        
        if product_type_code:
            domain.append(('ams_product_type_id.code', '=', product_type_code))
        
        return self.search(domain)
    
    @api.model
    def get_member_pricing_products(self):
        """Get products that have member pricing."""
        return self.search([
            ('is_ams_product', '=', True),
            ('has_member_pricing', '=', True)
        ])
    
    @api.model
    def get_digital_products(self):
        """Get digital products."""
        return self.search([
            ('is_ams_product', '=', True),
            ('is_digital_product', '=', True)
        ])
    
    @api.model
    def get_membership_required_products(self):
        """Get products that require membership."""
        return self.search([
            ('is_ams_product', '=', True),
            ('requires_membership', '=', True)
        ])

    # ========================================================================
    # ACTION METHODS (for view buttons)
    # ========================================================================
    
    def action_configure_digital_content(self):
        """Open digital content configuration wizard."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Digital Content'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_ref': 'ams_products_base.product_digital_content_form'},
        }
    
    def action_view_member_pricing(self):
        """Open member pricing details view."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Pricing Details'),
            'res_model': 'product.template', 
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_ref': 'ams_products_base.product_member_pricing_form'},
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @api.model
    def _generate_sku(self, name):
        """
        Generate SKU from product name.
        
        Args:
            name (str): Product name
            
        Returns:
            str: Generated SKU
        """
        if not name:
            return ''
        
        # Convert to uppercase, replace spaces with hyphens, remove special chars
        sku = re.sub(r'[^A-Za-z0-9\s-]', '', name)
        sku = re.sub(r'\s+', '-', sku.strip()).upper()
        
        # Ensure uniqueness by adding counter if needed
        base_sku = sku[:40]  # Limit length
        counter = 1
        final_sku = base_sku
        
        while self.search([('sku', '=', final_sku)], limit=1):
            final_sku = f"{base_sku}-{counter}"
            counter += 1
            if len(final_sku) > 50:  # Prevent infinite loop
                break
        
        return final_sku
    
    def _get_pricing_context(self, partner_id=None):
        """
        Get pricing context for this product based on partner.
        
        Args:
            partner_id (int, optional): Partner ID to check member status
            
        Returns:
            dict: Pricing context information
        """
        self.ensure_one()
        
        context = {
            'product_id': self.id,
            'has_member_pricing': self.has_member_pricing,
            'requires_membership': self.requires_membership,
            'is_digital_product': self.is_digital_product,
            'auto_fulfill_digital': self.auto_fulfill_digital,
            'sku': self.sku,
        }
        
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            is_member = getattr(partner, 'is_member', False)
            
            context.update({
                'partner_id': partner_id,
                'is_member': is_member,
                'can_purchase': self.can_be_purchased_by_member_status(is_member),
                'effective_price': self.get_price_for_member_status(is_member),
                'member_savings': self.get_member_savings() if is_member else 0.0,
                'digital_access': self.get_digital_content_access() if self.is_digital_product else {},
            })
        
        return context
    
    def validate_ams_configuration(self):
        """Validate AMS product configuration and return issues."""
        self.ensure_one()
        issues = []
        
        if self.is_ams_product:
            if not self.ams_product_type_id:
                issues.append("AMS products should have a product type assigned")
            
            if self.has_member_pricing:
                if not self.member_price and not self.non_member_price:
                    issues.append("Products with member pricing should have prices configured")
            
            if self.is_digital_product:
                if not self.is_digital_available:
                    issues.append("Digital products need either a download URL or attached file")
            
            if self.requires_membership and not self.has_member_pricing:
                issues.append("Products requiring membership typically should have member pricing")
        
        return issues
    
    def name_get(self):
        """Custom name display for AMS products."""
        result = []
        for product in self:
            name = product.name
            
            # Add SKU if available
            if product.sku:
                name = f"[{product.sku}] {name}"
            
            # Add digital indicator
            if product.is_digital_product:
                name = f"{name} (Digital)"
            
            # Add member pricing indicator
            if product.has_member_pricing:
                name = f"{name} (Member Pricing)"
            
            result.append((product.id, name))
        
        return result