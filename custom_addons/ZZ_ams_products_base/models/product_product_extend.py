from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ProductProductExtend(models.Model):
    """Extend product.product with AMS-specific computed fields and methods."""
    _inherit = 'product.product'

    # ==========================================
    # AMS INTEGRATION FIELDS
    # ==========================================
    
    is_ams_product = fields.Boolean(
        string='AMS Product',
        compute='_compute_ams_product',
        store=False,  # Don't store to avoid computation issues
        help='Whether this product has AMS extensions'
    )
    
    ams_product_id = fields.Many2one(
        'ams.product.standard',
        string='AMS Product Record',
        compute='_compute_ams_product',
        store=False,  # Don't store to avoid computation issues
        help='Related AMS product extension record'
    )
    
    ams_product_standard_ids = fields.One2many(
        'ams.product.standard',
        'product_id',
        string='AMS Product Extensions'
    )

    # ==========================================
    # MEMBER PRICING INTEGRATION
    # ==========================================
    
    member_price = fields.Monetary(
        string='Member Price',
        related='ams_product_id.member_price',
        readonly=True,
        help='Special price for association members'
    )
    
    non_member_price = fields.Monetary(
        string='Non-Member Price',
        related='ams_product_id.non_member_price',
        readonly=True,
        help='Standard price for non-members'
    )
    
    has_member_pricing = fields.Boolean(
        string='Has Member Pricing',
        compute='_compute_has_member_pricing',
        store=False,
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

    def _compute_ams_product(self):
        """Compute AMS product relationship."""
        for product in self:
            # Use direct SQL query to avoid ordering issues during installation
            self.env.cr.execute("""
                SELECT id FROM ams_product_standard 
                WHERE product_id = %s 
                LIMIT 1
            """, (product.id,))
            
            result = self.env.cr.fetchone()
            if result:
                ams_product = self.env['ams.product.standard'].browse(result[0])
                product.is_ams_product = True
                product.ams_product_id = ams_product.id
            else:
                product.is_ams_product = False
                product.ams_product_id = False

    @api.depends('ams_product_id.member_price', 'ams_product_id.non_member_price')
    def _compute_has_member_pricing(self):
        """Compute whether product has member-specific pricing."""
        for product in self:
            if product.ams_product_id:
                product.has_member_pricing = bool(
                    product.ams_product_id.member_price and 
                    product.ams_product_id.non_member_price and
                    product.ams_product_id.member_price != product.ams_product_id.non_member_price
                )
            else:
                product.has_member_pricing = False

    # ==========================================
    # AMS BUSINESS METHODS
    # ==========================================

    def get_ams_price_for_partner(self, partner_id, quantity=1):
        """Get AMS-specific pricing for a partner."""
        self.ensure_one()
        
        if not self.is_ams_product:
            # Return standard Odoo pricing
            return {
                'unit_price': self.list_price,
                'final_price': self.list_price,
                'total_price': self.list_price * quantity,
                'price_type': 'standard',
                'discount_applied': False,
                'currency': self.env.company.currency_id.name
            }
        
        return self.ams_product_id.get_customer_price(partner_id, quantity)

    def check_ams_eligibility(self, partner_id):
        """Check AMS-specific eligibility for partner."""
        self.ensure_one()
        
        if not self.is_ams_product:
            return {'eligible': True, 'reason': None, 'action': None}
        
        return self.ams_product_id.check_product_eligibility(partner_id)

    def get_ams_stock_info(self, quantity=1):
        """Get AMS-specific stock availability."""
        self.ensure_one()
        
        if not self.is_ams_product:
            # Use standard Odoo stock
            return {'available': True, 'quantity': quantity}
        
        return self.ams_product_id.check_stock_availability(quantity)

    def create_ams_extension(self, ams_values=None):
        """Create AMS extension for this product."""
        self.ensure_one()
        
        if self.is_ams_product:
            raise UserError("Product already has AMS extension")
        
        values = {
            'product_id': self.id,
            'ams_product_type': 'merchandise',  # Default type
        }
        
        if ams_values:
            values.update(ams_values)
        
        ams_product = self.env['ams.product.standard'].create(values)
        
        # Trigger recomputation
        self._compute_ams_product()
        
        return ams_product

    def remove_ams_extension(self):
        """Remove AMS extension from this product."""
        self.ensure_one()
        
        if not self.is_ams_product:
            raise UserError("Product does not have AMS extension")
        
        self.ams_product_id.unlink()
        
        # Trigger recomputation
        self._compute_ams_product()

    # ==========================================
    # WEBSITE/E-COMMERCE INTEGRATION
    # ==========================================

    def _get_website_price(self, partner=None, **kwargs):
        """Override website pricing for member discounts."""
        # Check if we should use AMS pricing
        if self.is_ams_product and partner:
            try:
                price_info = self.get_ams_price_for_partner(partner.id)
                return price_info['unit_price']
            except:
                # Fallback to standard pricing if AMS pricing fails
                pass
        
        # Use standard Odoo pricing
        return super()._get_website_price(partner=partner, **kwargs)

    def _is_available_for_partner(self, partner=None, **kwargs):
        """Check product availability for specific partner."""
        available = super()._is_available_for_partner(partner=partner, **kwargs)
        
        # Add AMS-specific availability checks
        if available and self.is_ams_product and partner:
            try:
                eligibility = self.check_ams_eligibility(partner.id)
                return eligibility['eligible']
            except:
                # If AMS check fails, use standard availability
                pass
        
        return available

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_ams_extension(self):
        """Open the AMS product extension form."""
        self.ensure_one()
        
        if not self.is_ams_product:
            raise UserError("This product does not have an AMS extension")
        
        return {
            'name': f'AMS Extension - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.standard',
            'view_mode': 'form',
            'res_id': self.ams_product_id.id,
            'target': 'new',
        }

    def action_create_ams_extension(self):
        """Wizard to create AMS extension for this product."""
        self.ensure_one()
        
        if self.is_ams_product:
            raise UserError("Product already has AMS extension")
        
        return {
            'name': f'Create AMS Extension - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.product.standard',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
                'default_ams_product_type': 'merchandise',
            },
            'target': 'new',
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_ams_product_summary(self):
        """Get summary of AMS product features."""
        self.ensure_one()
        
        if not self.is_ams_product:
            return {'has_ams_extension': False}
        
        ams = self.ams_product_id
        return {
            'has_ams_extension': True,
            'ams_product_type': ams.ams_product_type,
            'has_member_pricing': self.has_member_pricing,
            'member_price': ams.member_price,
            'non_member_price': ams.non_member_price,
            'discount_percentage': ams.member_discount_percentage,
            'is_digital': ams.digital_delivery_enabled,
            'requires_membership': ams.requires_membership,
            'is_chapter_restricted': ams.chapter_specific,
            'stock_controlled': ams.stock_controlled,
        }

    @api.model
    def get_ams_products_by_type(self, product_type):
        """Get all products of specific AMS type."""
        return self.search([
            ('is_ams_product', '=', True),
            ('ams_product_type', '=', product_type)
        ])

    @api.model
    def get_member_priced_products(self):
        """Get all products with member pricing."""
        return self.search([('has_member_pricing', '=', True)])

    @api.model
    def get_digital_products(self):
        """Get all digital products."""
        return self.search([('is_digital_product', '=', True)])

    # ==========================================
    # SEARCH AND FILTERING
    # ==========================================

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """Enhanced search to support AMS-specific filtering."""
        # Add support for searching by AMS fields
        new_args = []
        for arg in args:
            if isinstance(arg, (list, tuple)) and len(arg) == 3:
                field, operator, value = arg
                
                # Map AMS-specific search fields
                if field == 'ams_product_type':
                    new_args.append(('ams_product_id.ams_product_type', operator, value))
                elif field == 'member_price':
                    new_args.append(('ams_product_id.member_price', operator, value))
                elif field == 'requires_membership':
                    new_args.append(('ams_product_id.requires_membership', operator, value))
                else:
                    new_args.append(arg)
            else:
                new_args.append(arg)
        
        return super()._search(
            new_args, offset=offset, limit=limit, order=order, 
            count=count, access_rights_uid=access_rights_uid
        )

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    def unlink(self):
        """Override unlink to clean up AMS extensions."""
        # Remove AMS extensions before deleting products
        ams_products = self.env['ams.product.standard'].search([
            ('product_id', 'in', self.ids)
        ])
        ams_products.unlink()
        
        return super().unlink()