# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    AMS Products Base - extends the product.template features from ams_product_types
    with additional association-specific functionality.
    """
    _inherit = 'product.template'

    # ========================================================================
    # SKU MANAGEMENT
    # ========================================================================

    sku = fields.Char(
        string="SKU",
        size=64,
        help="Stock Keeping Unit - unique product identifier. Auto-generated if left blank."
    )

    sku_generation_method = fields.Selection([
        ('auto_name', 'Auto from Name'),
        ('auto_category', 'Auto from Category + Name'),
        ('manual', 'Manual Only'),
        ('sequence', 'Sequence Based'),
    ], string="SKU Generation Method", default='auto_name',
        help="How to generate SKUs for this product")

    # ========================================================================
    # LEGACY SYSTEM INTEGRATION
    # ========================================================================

    legacy_product_id = fields.Char(
        string="Legacy Product ID",
        size=32,
        help="Product ID from legacy/external systems for data migration"
    )

    legacy_sku = fields.Char(
        string="Legacy SKU",
        size=64,
        help="SKU from legacy system"
    )

    # ========================================================================
    # ENHANCED MEMBER PRICING (extends ams_product_types)
    # ========================================================================

    member_pricing_method = fields.Selection([
        ('fixed', 'Fixed Member Price'),
        ('percentage', 'Percentage Discount'),
        ('both', 'Both (Fixed Price Overrides)'),
    ], string="Member Pricing Method", default='fixed',
        help="How to calculate member pricing")

    member_discount_percentage = fields.Float(
        string="Member Discount %",
        help="Percentage discount for members (when using percentage method)"
    )

    non_member_price = fields.Float(
        string="Non-Member Price",
        digits='Product Price',
        help="Explicit non-member price (uses list_price if blank)"
    )

    # ========================================================================
    # DIGITAL PRODUCT MANAGEMENT
    # ========================================================================

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

    digital_access_duration = fields.Integer(
        string="Access Duration (Days)",
        help="Number of days customer has access to digital content (0 = unlimited)"
    )

    # ========================================================================
    # ACCESS CONTROL & RESTRICTIONS
    # ========================================================================

    requires_membership = fields.Boolean(
        string="Requires Membership",
        default=False,
        help="Only association members can purchase this product"
    )

    membership_level_required = fields.Selection([
        ('any', 'Any Membership Level'),
        ('basic', 'Basic or Higher'),
        ('premium', 'Premium or Higher'),
        ('professional', 'Professional Only'),
    ], string="Membership Level Required", default='any',
        help="Minimum membership level required to purchase")

    chapter_specific = fields.Boolean(
        string="Chapter Specific",
        default=False,
        help="Product is restricted to specific chapters"
    )

    public_visibility = fields.Boolean(
        string="Public Visibility",
        default=True,
        help="Product visible to non-members in catalog"
    )

    # ========================================================================
    # FULFILLMENT & DELIVERY
    # ========================================================================

    fulfillment_method = fields.Selection([
        ('manual', 'Manual Fulfillment'),
        ('auto_digital', 'Auto Digital Delivery'),
        ('auto_physical', 'Auto Physical Shipping'),
        ('event_based', 'Event-based Fulfillment'),
        ('subscription', 'Subscription Fulfillment'),
    ], string="Fulfillment Method", default='manual',
        help="How this product is fulfilled after purchase")

    delivery_instructions = fields.Text(
        string="Delivery Instructions",
        help="Special instructions for fulfilling this product"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('sku', 'default_code')
    def _compute_effective_sku(self):
        """Calculate the effective SKU to use."""
        for product in self:
            if product.sku:
                product.effective_sku = product.sku
            else:
                product.effective_sku = product.default_code or ''

    effective_sku = fields.Char(
        string="Effective SKU",
        compute='_compute_effective_sku',
        store=True,
        help="The actual SKU being used (sku or default_code)"
    )

    @api.depends('is_digital_product', 'digital_download_url', 'digital_attachment_id')
    def _compute_digital_content_status(self):
        """Check digital content availability."""
        for product in self:
            if product.is_digital_product:
                product.has_digital_content = bool(product.digital_download_url or product.digital_attachment_id)
                if product.digital_download_url and product.digital_attachment_id:
                    product.digital_content_status = 'both'
                elif product.digital_download_url:
                    product.digital_content_status = 'url'
                elif product.digital_attachment_id:
                    product.digital_content_status = 'file'
                else:
                    product.digital_content_status = 'missing'
            else:
                product.has_digital_content = False
                product.digital_content_status = 'not_digital'

    has_digital_content = fields.Boolean(
        string="Has Digital Content",
        compute='_compute_digital_content_status',
        store=True,
        help="Whether digital content is available"
    )

    digital_content_status = fields.Selection([
        ('not_digital', 'Not Digital Product'),
        ('missing', 'Missing Content'),
        ('url', 'URL Only'),
        ('file', 'File Only'),
        ('both', 'URL and File'),
    ], string="Digital Content Status",
        compute='_compute_digital_content_status',
        store=True,
        help="Status of digital content availability"
    )

    # ========================================================================
    # BUSINESS METHODS (extend ams_product_types)
    # ========================================================================

    def get_price_for_partner(self, partner):
        """
        Get appropriate price for a specific partner based on membership status.
        Extends the basic method from ams_product_types.
        """
        self.ensure_one()

        # Check membership status (integration with ams_member_data)
        is_member = self._check_partner_membership(partner)
        
        # Check membership level requirement
        if self.requires_membership and not is_member:
            return False  # Cannot purchase

        # Return appropriate price - delegate to existing method if available
        if hasattr(super(), 'get_price_for_member_type'):
            return super().get_price_for_member_type(is_member)
        else:
            # Fallback implementation
            if is_member and self.has_member_pricing and self.member_list_price:
                return self.member_list_price
            return self.list_price

    def _check_partner_membership(self, partner):
        """Check if partner is a member with required level."""
        if not partner:
            return False

        # Basic membership check (from ams_member_data)
        is_member = False
        if hasattr(partner, 'is_member'):
            is_member = partner.is_member
        elif hasattr(partner, 'membership_state'):
            is_member = partner.membership_state in ['invoiced', 'paid']

        return is_member

    def can_be_purchased_by_partner(self, partner):
        """Check if this product can be purchased by the given partner."""
        self.ensure_one()

        # Basic availability
        if not self.active:
            return False

        # Membership requirement
        if self.requires_membership:
            return self._check_partner_membership(partner)

        return True

    # ========================================================================
    # SKU GENERATION
    # ========================================================================

    def _generate_sku(self, name=None):
        """Generate SKU based on the configured method."""
        self.ensure_one()
        
        if not name:
            name = self.name or "PRODUCT"

        if self.sku_generation_method == 'manual':
            return ''  # Don't auto-generate for manual
        elif self.sku_generation_method == 'sequence':
            return self._generate_sequence_sku()
        elif self.sku_generation_method == 'auto_category':
            return self._generate_category_sku(name)
        else:  # auto_name
            return self._generate_name_sku(name)

    def _generate_name_sku(self, name):
        """Generate SKU from product name."""
        # Clean name and create base SKU
        base_sku = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        base_sku = re.sub(r'\s+', '-', base_sku.strip().upper())
        base_sku = base_sku[:20]  # Limit length

        return self._ensure_sku_uniqueness(base_sku)

    def _generate_category_sku(self, name):
        """Generate SKU from category + name."""
        category_prefix = ''
        if hasattr(self, 'ams_category') and self.ams_category:
            category_map = {
                'membership': 'MEM',
                'event': 'EVT',
                'education': 'EDU',
                'publication': 'PUB',
                'merchandise': 'MER',
                'certification': 'CRT',
                'digital': 'DIG',
            }
            category_prefix = category_map.get(self.ams_category, 'PRD')

        # Clean name part
        name_part = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        name_part = re.sub(r'\s+', '-', name_part.strip().upper())
        name_part = name_part[:15]  # Leave room for prefix

        base_sku = f"{category_prefix}-{name_part}" if category_prefix else name_part
        return self._ensure_sku_uniqueness(base_sku)

    def _generate_sequence_sku(self):
        """Generate sequential SKU."""
        # Get category prefix
        category_prefix = 'PRD'
        if hasattr(self, 'ams_category') and self.ams_category:
            category_map = {
                'membership': 'MEM',
                'event': 'EVT', 
                'education': 'EDU',
                'publication': 'PUB',
                'merchandise': 'MER',
                'certification': 'CRT',
                'digital': 'DIG',
            }
            category_prefix = category_map.get(self.ams_category, 'PRD')

        # Find next sequence number
        existing_skus = self.search([
            ('sku', 'like', f'{category_prefix}-%')
        ]).mapped('sku')

        sequence = 1
        for sku in existing_skus:
            try:
                num = int(sku.split('-')[-1])
                if num >= sequence:
                    sequence = num + 1
            except:
                continue

        return f"{category_prefix}-{sequence:04d}"

    def _ensure_sku_uniqueness(self, base_sku):
        """Ensure SKU is unique."""
        counter = 1
        sku = base_sku
        while self.search([('sku', '=', sku), ('id', '!=', self.id)], limit=1):
            sku = f"{base_sku}-{counter:03d}"
            counter += 1
        return sku

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate SKUs and apply defaults."""
        for vals in vals_list:
            # Generate SKU if needed for AMS products
            if vals.get('is_ams_product') and not vals.get('sku'):
                # Create temporary record to use generation methods
                temp_product = self.new(vals)
                generated_sku = temp_product._generate_sku(vals.get('name'))
                if generated_sku:
                    vals['sku'] = generated_sku
                    vals['default_code'] = generated_sku  # Sync with Odoo SKU

        products = super().create(vals_list)
        return products

    def write(self, vals):
        """Maintain SKU sync and apply updates."""
        # Sync SKU changes
        if 'sku' in vals and vals['sku']:
            vals['default_code'] = vals['sku']
        elif 'default_code' in vals and not vals.get('sku'):
            vals['sku'] = vals['default_code']

        return super().write(vals)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('digital_download_url')
    def _check_digital_url_format(self):
        """Validate digital download URL format."""
        for product in self:
            if product.digital_download_url:
                if not product.digital_download_url.startswith(('http://', 'https://')):
                    raise ValidationError(_("Digital download URL must start with http:// or https://"))

    @api.constrains('sku')
    def _check_sku_uniqueness(self):
        """Ensure SKU uniqueness."""
        for product in self:
            if product.sku:
                duplicate = self.search([
                    ('sku', '=', product.sku),
                    ('id', '!=', product.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_("SKU '%s' already exists for product '%s'") % (product.sku, duplicate.name))