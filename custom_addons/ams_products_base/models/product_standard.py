from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class AMSProductStandard(models.Model):
    """AMS-specific product extensions with association features."""
    _name = 'ams.product.standard'
    _description = 'AMS Product Standard'
    _order = 'name, ams_product_type'

    # ==========================================
    # CORE PRODUCT RELATIONSHIP
    # ==========================================
    
    product_id = fields.Many2one(
        'product.product',
        string='Base Product Record',
        required=True,
        ondelete='cascade',
        help='Link to core Odoo product record'
    )
    
    name = fields.Char(
        string='Product Name',
        related='product_id.name',
        store=True,
        help='Product name from base product'
    )
    
    # ==========================================
    # AMS PRODUCT CLASSIFICATION
    # ==========================================
    
    ams_product_type = fields.Selection([
        ('merchandise', 'Merchandise'),
        ('publication', 'Publication'),
        ('certification_package', 'Certification Package'),
        ('digital_download', 'Digital Download'),
        ('event_material', 'Event Material'),
    ], string='AMS Product Type', required=True,
       help='Association-specific product categorization')
    
    sku = fields.Char(
        string='Stock Keeping Unit',
        help='Internal SKU for inventory and ordering'
    )
    
    product_code = fields.Char(
        string='Product Code',
        help='External product code for catalogs and marketing'
    )
    
    # ==========================================
    # PRICING STRUCTURE
    # ==========================================
    
    member_price = fields.Monetary(
        string='Member Price',
        currency_field='currency_id',
        help='Special price for association members'
    )
    
    non_member_price = fields.Monetary(
        string='Non-Member Price',
        currency_field='currency_id',
        help='Standard price for non-members'
    )
    
    member_discount_percentage = fields.Float(
        string='Member Discount %',
        compute='_compute_member_discount',
        store=True,
        help='Percentage discount for members'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id or self.env['res.currency'].search([('name', '=', 'USD')], limit=1),
        help='Currency for pricing'
    )
    
    # ==========================================
    # INVENTORY MANAGEMENT
    # ==========================================
    
    stock_controlled = fields.Boolean(
        string='Track Inventory',
        default=True,
        help='Whether to track inventory levels for this product'
    )
    
    minimum_stock_level = fields.Integer(
        string='Minimum Stock',
        help='Alert threshold for low inventory'
    )
    
    maximum_stock_level = fields.Integer(
        string='Maximum Stock',
        help='Maximum recommended inventory level'
    )
    
    # ==========================================
    # DIGITAL PRODUCT FEATURES
    # ==========================================
    
    digital_delivery_enabled = fields.Boolean(
        string='Digital Product',
        help='Product delivered digitally rather than physically'
    )
    
    digital_download_url = fields.Char(
        string='Download URL',
        help='Direct download link for digital products'
    )
    
    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Digital File',
        help='File attachment for automatic delivery'
    )
    
    download_limit = fields.Integer(
        string='Download Limit',
        help='Maximum number of downloads per purchase (0 = unlimited)'
    )
    
    access_expiry_days = fields.Integer(
        string='Access Expires (Days)',
        help='Days until digital access expires (0 = permanent)'
    )
    
    # ==========================================
    # ACCESS CONTROL
    # ==========================================
    
    requires_membership = fields.Boolean(
        string='Members Only',
        help='Product only available to current members'
    )
    
    member_types_allowed = fields.Many2many(
        'ams.member.type',
        string='Allowed Member Types',
        help='Specific member types eligible for purchase'
    )
    
    # ==========================================
    # GEOGRAPHIC RESTRICTIONS (PLACEHOLDER)
    # ==========================================
    
    chapter_specific = fields.Boolean(
        string='Chapter Restricted',
        help='Product restricted to specific chapters'
    )
    
    # Placeholder for future ams_chapters_core integration
    # allowed_chapter_ids = fields.Many2many(
    #     'ams.chapter',
    #     string='Allowed Chapters',
    #     help='Chapters that can access this product'
    # )
    
    # ==========================================
    # PRODUCT ATTRIBUTES
    # ==========================================
    
    featured_product = fields.Boolean(
        string='Featured Product',
        help='Highlight in catalogs and website'
    )
    
    new_product = fields.Boolean(
        string='New Product',
        help='Mark as new for promotional purposes'
    )
    
    seasonal_product = fields.Boolean(
        string='Seasonal Product',
        help='Product with seasonal availability'
    )
    
    season_start_date = fields.Date(
        string='Season Start'
    )
    
    season_end_date = fields.Date(
        string='Season End'
    )
    
    # ==========================================
    # CONTENT AND MARKETING
    # ==========================================
    
    detailed_description = fields.Html(
        string='Detailed Description',
        help='Full product description for catalogs and website'
    )
    
    specifications = fields.Text(
        string='Product Specifications',
        help='Technical specifications or detailed attributes'
    )
    
    benefits_description = fields.Html(
        string='Member Benefits',
        help='Description of special member benefits for this product'
    )
    
    # ==========================================
    # INTEGRATION FIELDS
    # ==========================================
    
    external_product_id = fields.Char(
        string='External Product ID',
        help='Product ID in external systems (e-commerce, fulfillment)'
    )
    
    supplier_product_code = fields.Char(
        string='Supplier Product Code',
        help='Vendor or supplier product identifier'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active products are available for sale'
    )

    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('product_unique', 'UNIQUE(product_id)', 
         'Each Odoo product can only have one AMS extension.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('member_price', 'non_member_price')
    def _compute_member_discount(self):
        """Calculate member discount percentage."""
        for record in self:
            if (record.member_price and record.non_member_price and 
                record.non_member_price > 0):
                discount_amount = record.non_member_price - record.member_price
                record.member_discount_percentage = (
                    discount_amount / record.non_member_price * 100
                )
            else:
                record.member_discount_percentage = 0.0

    # ==========================================
    # VALIDATION AND CONSTRAINTS
    # ==========================================

    @api.constrains('member_price', 'non_member_price')
    def _check_pricing_logic(self):
        """Validate member pricing is appropriate."""
        for record in self:
            if record.member_price and record.non_member_price:
                if record.member_price > record.non_member_price:
                    raise ValidationError(
                        "Member price cannot be higher than non-member price"
                    )
                
                # Warn if discount is unusually high (>75%)
                discount_pct = ((record.non_member_price - record.member_price)
                               / record.non_member_price * 100)
                if discount_pct > 75:
                    # Log warning but don't block
                    self.env['res.partner']  # Just to trigger logging
                    # Could implement logging here if needed

    @api.constrains('season_start_date', 'season_end_date')
    def _check_seasonal_dates(self):
        """Validate seasonal date logic."""
        for record in self:
            if record.seasonal_product:
                if record.season_start_date and record.season_end_date:
                    if record.season_start_date >= record.season_end_date:
                        raise ValidationError(
                            "Season start date must be before season end date"
                        )

    @api.constrains('download_limit', 'access_expiry_days')
    def _check_digital_settings(self):
        """Validate digital product settings."""
        for record in self:
            if record.digital_delivery_enabled:
                if not record.digital_download_url and not record.digital_attachment_id:
                    raise ValidationError(
                        "Digital products must have either a download URL or file attachment"
                    )
                    
                if record.download_limit < 0:
                    raise ValidationError(
                        "Download limit cannot be negative (use 0 for unlimited)"
                    )
                    
                if record.access_expiry_days < 0:
                    raise ValidationError(
                        "Access expiry days cannot be negative (use 0 for permanent)"
                    )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def check_product_eligibility(self, partner_id):
        """Check if partner is eligible to purchase this product."""
        partner = self.env['res.partner'].browse(partner_id)
        
        # Check membership requirement
        if self.requires_membership and not partner.is_member:
            return {
                'eligible': False,
                'reason': 'Product requires current membership',
                'action': 'join_or_renew'
            }

        # Check member type restrictions
        if self.member_types_allowed and partner.member_type_id:
            if partner.member_type_id not in self.member_types_allowed:
                return {
                    'eligible': False,
                    'reason': f'Product not available for {partner.member_type_id.name} members',
                    'action': 'contact_support'
                }

        # Check seasonal availability
        if self.seasonal_product:
            today = fields.Date.today()
            if self.season_start_date and today < self.season_start_date:
                return {
                    'eligible': False,
                    'reason': f'Product available starting {self.season_start_date}',
                    'action': 'wait'
                }
            if self.season_end_date and today > self.season_end_date:
                return {
                    'eligible': False,
                    'reason': 'Product no longer available this season',
                    'action': 'contact_support'
                }

        return {'eligible': True, 'reason': None, 'action': None}

    def get_customer_price(self, partner_id, quantity=1):
        """Get appropriate price for customer."""
        partner = self.env['res.partner'].browse(partner_id)

        # Check product eligibility first
        eligibility = self.check_product_eligibility(partner_id)
        if not eligibility['eligible']:
            raise ValidationError(eligibility['reason'])

        # Determine base price
        if partner.is_member and self.member_price:
            unit_price = self.member_price
            price_type = 'member'
        else:
            unit_price = self.non_member_price or self.product_id.list_price
            price_type = 'non_member'

        # Apply volume discounts if configured (placeholder for future enhancement)
        final_price = unit_price

        return {
            'unit_price': unit_price,
            'final_price': final_price,
            'total_price': final_price * quantity,
            'price_type': price_type,
            'discount_applied': final_price != unit_price,
            'currency': self.currency_id.name
        }

    def check_stock_availability(self, quantity_needed):
        """Check product stock availability."""
        if not self.stock_controlled:
            return {'available': True, 'quantity': quantity_needed}

        # Integration with Odoo stock - get current stock
        stock_quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', '=', 'internal')
        ])
        
        available_qty = sum(stock_quant.mapped('quantity'))
        
        if available_qty < quantity_needed:
            return {
                'available': False,
                'quantity': available_qty,
                'message': f'Only {available_qty} units available'
            }

        return {'available': True, 'quantity': quantity_needed}

    # ==========================================
    # DIGITAL PRODUCT METHODS
    # ==========================================

    def generate_digital_access_token(self):
        """Generate secure access token for digital downloads."""
        import secrets
        return secrets.token_urlsafe(32)

    def get_digital_download_info(self, partner_id):
        """Get digital download information for a customer."""
        if not self.digital_delivery_enabled:
            return None
            
        # Check eligibility
        eligibility = self.check_product_eligibility(partner_id)
        if not eligibility['eligible']:
            return None
            
        download_info = {
            'download_url': self.digital_download_url,
            'attachment_id': self.digital_attachment_id.id if self.digital_attachment_id else None,
            'download_limit': self.download_limit,
            'access_expires': self._calculate_expiry_date(),
            'access_token': self.generate_digital_access_token()
        }
        
        return download_info

    def _calculate_expiry_date(self):
        """Calculate digital product access expiry."""
        if self.access_expiry_days:
            return fields.Date.today() + fields.timedelta(days=self.access_expiry_days)
        return None

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and validate."""
        for vals in vals_list:
            # Auto-generate SKU if not provided
            if not vals.get('sku') and vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['sku'] = f"AMS-{product.default_code or product.id}"
                
        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle updates."""
        # Clear digital settings if digital delivery is disabled
        if 'digital_delivery_enabled' in vals and not vals['digital_delivery_enabled']:
            vals.update({
                'digital_download_url': False,
                'digital_attachment_id': False,
                'download_limit': 0,
                'access_expiry_days': 0,
            })
            
        return super().write(vals)

    # ==========================================
    # DISPLAY METHODS
    # ==========================================

    def name_get(self):
        """Custom display name."""
        result = []
        for record in self:
            name = record.name or 'AMS Product'
            if record.ams_product_type:
                name = f"[{dict(record._fields['ams_product_type'].selection)[record.ams_product_type]}] {name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including SKU and product code."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|', '|',
                     ('name', operator, name),
                     ('sku', operator, name),
                     ('product_code', operator, name),
                     ('product_id.default_code', operator, name)]
                     
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)