from odoo import models, fields, api


class ProductProduct(models.Model):
    """Extend product.product with AMS integration points."""
    _inherit = 'product.product'

    # ==========================================
    # COMPUTED AMS FIELDS
    # ==========================================
    
    is_ams_product = fields.Boolean(
        string='AMS Product',
        compute='_compute_ams_product',
        store=True,
        help='Whether this product has AMS extensions'
    )
    
    ams_product_id = fields.Many2one(
        'ams.product.standard',
        string='AMS Product Record',
        compute='_compute_ams_product',
        store=True,
        help='Related AMS product extension'
    )
    
    # ==========================================
    # MEMBER PRICING INTEGRATION
    # ==========================================
    
    member_price = fields.Monetary(
        string='Member Price',
        related='ams_product_id.member_price',
        readonly=True,
        help='Special pricing for association members'
    )
    
    non_member_price = fields.Monetary(
        string='Non-Member Price', 
        related='ams_product_id.non_member_price',
        readonly=True,
        help='Standard pricing for non-members'
    )
    
    has_member_pricing = fields.Boolean(
        string='Has Member Pricing',
        compute='_compute_has_member_pricing',
        store=True,
        help='Product has different pricing for members vs non-members'
    )
    
    member_discount_percentage = fields.Float(
        string='Member Discount %',
        related='ams_product_id.member_discount_percentage',
        readonly=True,
        help='Percentage discount for members'
    )
    
    # ==========================================
    # DIGITAL PRODUCT INDICATORS
    # ==========================================
    
    is_digital_product = fields.Boolean(
        string='Digital Product',
        related='ams_product_id.digital_delivery_enabled',
        readonly=True,
        help='Product delivered digitally'
    )
    
    # ==========================================
    # ACCESS CONTROL INDICATORS
    # ==========================================
    
    requires_membership = fields.Boolean(
        string='Members Only',
        related='ams_product_id.requires_membership',
        readonly=True,
        help='Product only available to current members'
    )
    
    is_chapter_restricted = fields.Boolean(
        string='Chapter Restricted',
        related='ams_product_id.chapter_specific',
        readonly=True,
        help='Product restricted to specific chapters'
    )
    
    # ==========================================
    # PRODUCT CATEGORIES
    # ==========================================
    
    ams_product_type = fields.Selection(
        string='AMS Product Type',
        related='ams_product_id.ams_product_type',
        readonly=True,
        help='Association-specific product categorization'
    )
    
    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('ams_product_standard_ids')
    def _compute_ams_product(self):
        """Compute AMS product relationship."""
        for product in self:
            ams_products = self.env['ams.product.standard'].search([
                ('product_id', '=', product.id)
            ], limit=1)
            
            if ams_products:
                product.is_ams_product = True
                product.ams_product_id = ams_products.id
            else:
                product.is_ams_product = False
                product.ams_product_id = False

    @api.depends('ams_product_id.member_price', 'ams_product_id.non_member_price')
    def _compute_has_member_pricing(self):
        """Compute whether product has member-specific pricing."""
        for product in self:
            if (product.ams_product_id and 
                product.ams_product_id.member_price and 
                product.ams_product_id.non_member_price):
                product.has_member_pricing = True
            else:
                product.has_member_pricing = False

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_price_for_partner(self, partner_id, quantity=1):
        """Get appropriate price for a specific partner."""
        self.ensure_one()
        
        if not self.is_ams_product:
            # Standard Odoo pricing
            return {
                'unit_price': self.list_price,
                'final_price': self.list_price,
                'total_price': self.list_price * quantity,
                'price_type': 'standard',
                'currency': self.currency_id.name or self.env.company.currency_id.name
            }
        
        # Use AMS pricing logic
        return self.ams_product_id.get_customer_price(partner_id, quantity)

    def check_availability_for_partner(self, partner_id, quantity=1):
        """Check if product is available for a specific partner."""
        self.ensure_one()
        
        if not self.is_ams_product:
            # Standard availability check
            return {'available': True, 'quantity': quantity}
        
        # Check AMS eligibility
        eligibility = self.ams_product_id.check_product_eligibility(partner_id)
        if not eligibility['eligible']:
            return {
                'available': False,
                'reason': eligibility['reason'],
                'action': eligibility['action']
            }
        
        # Check stock availability
        return self.ams_product_id.check_stock_availability(quantity)

    def create_ams_extension(self, ams_product_type='merchandise'):
        """Create AMS product extension for this product."""
        self.ensure_one()
        
        if self.is_ams_product:
            raise ValueError("Product already has AMS extension")
        
        ams_product = self.env['ams.product.standard'].create({
            'product_id': self.id,
            'ams_product_type': ams_product_type,
            'non_member_price': self.list_price,  # Default non-member price to list price
        })
        
        return ams_product

    def get_digital_download_info(self, partner_id):
        """Get digital download information for a partner."""
        self.ensure_one()
        
        if not self.is_ams_product or not self.is_digital_product:
            return None
            
        return self.ams_product_id.get_digital_download_info(partner_id)

    # ==========================================
    # E-COMMERCE INTEGRATION METHODS
    # ==========================================

    def _get_website_price(self, partner=None):
        """Override website pricing for member discounts."""
        if not partner or not self.is_ams_product:
            return super()._get_website_price(partner)

        try:
            price_info = self.get_price_for_partner(partner.id)
            return price_info['unit_price']
        except Exception:
            # Fallback to standard pricing
            return super()._get_website_price(partner)

    def _is_available_for_partner(self, partner=None):
        """Check product availability for specific partner."""
        available = super()._is_available_for_partner(partner)
        
        if not available or not partner or not self.is_ams_product:
            return available

        try:
            availability = self.check_availability_for_partner(partner.id)
            return availability.get('available', True)
        except Exception:
            # Fallback to standard availability
            return available

    # ==========================================
    # SEARCH AND FILTERING METHODS
    # ==========================================

    @api.model
    def search_ams_products(self, domain=None, filters=None):
        """Search AMS products with additional filters."""
        domain = domain or []
        domain.append(('is_ams_product', '=', True))
        
        if filters:
            # Member pricing filter
            if filters.get('has_member_pricing'):
                domain.append(('has_member_pricing', '=', True))
            
            # Product type filter
            if filters.get('ams_product_type'):
                domain.append(('ams_product_type', '=', filters['ams_product_type']))
            
            # Digital product filter
            if filters.get('digital_only'):
                domain.append(('is_digital_product', '=', True))
            
            # Member-only filter
            if filters.get('members_only'):
                domain.append(('requires_membership', '=', True))
        
        return self.search(domain)

    @api.model
    def get_ams_product_categories(self):
        """Get available AMS product categories."""
        return dict(self.env['ams.product.standard']._fields['ams_product_type'].selection)

    # ==========================================
    # REPORTING METHODS
    # ==========================================

    def get_pricing_summary(self):
        """Get pricing summary for this product."""
        self.ensure_one()
        
        if not self.is_ams_product:
            return {
                'pricing_type': 'standard',
                'price': self.list_price,
                'currency': self.currency_id.name or self.env.company.currency_id.name
            }
        
        return {
            'pricing_type': 'member_based',
            'member_price': self.member_price,
            'non_member_price': self.non_member_price,
            'discount_percentage': self.member_discount_percentage,
            'currency': self.ams_product_id.currency_id.name
        }

    def get_product_features(self):
        """Get product feature summary."""
        self.ensure_one()
        
        features = {
            'is_ams_product': self.is_ams_product,
            'digital_delivery': self.is_digital_product,
            'member_pricing': self.has_member_pricing,
            'membership_required': self.requires_membership,
            'chapter_restricted': self.is_chapter_restricted,
        }
        
        if self.is_ams_product:
            features.update({
                'product_type': self.ams_product_type,
                'stock_controlled': self.ams_product_id.stock_controlled,
                'featured': self.ams_product_id.featured_product,
                'seasonal': self.ams_product_id.seasonal_product,
            })
        
        return features

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_ams_extension(self):
        """Open AMS product extension form."""
        self.ensure_one()
        
        if not self.is_ams_product:
            # Create AMS extension
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create AMS Product Extension',
                'res_model': 'ams.product.standard',
                'view_mode': 'form',
                'context': {'default_product_id': self.id},
                'target': 'new',
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'AMS Product Extension',
            'res_model': 'ams.product.standard',
            'res_id': self.ams_product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_toggle_ams_extension(self):
        """Toggle AMS extension on/off."""
        self.ensure_one()
        
        if self.is_ams_product:
            # Remove AMS extension
            self.ams_product_id.unlink()
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            # Create AMS extension
            return self.action_view_ams_extension()