# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    """Extend Odoo's product category with AMS-specific functionality."""
    
    _inherit = 'product.category'

    # ========================================================================
    # AMS CLASSIFICATION FIELDS
    # ========================================================================
    
    is_ams_category = fields.Boolean(
        string="AMS Category",
        default=False,
        help="Mark this category as an AMS-managed category with enhanced features"
    )
    
    ams_category_type = fields.Selection([
        ('membership', 'Membership'),
        ('event', 'Event'),
        ('education', 'Education'),
        ('publication', 'Publication'),
        ('merchandise', 'Merchandise'),
        ('certification', 'Certification'),
        ('digital', 'Digital Download')
    ], string="AMS Category Type", help="AMS-specific category classification")
    
    # ========================================================================
    # AMS PRODUCT ATTRIBUTES
    # ========================================================================
    
    requires_member_pricing = fields.Boolean(
        string="Supports Member Pricing",
        default=False,
        help="Products in this category offer different pricing for members vs non-members"
    )
    
    is_subscription_category = fields.Boolean(
        string="Subscription Category",
        default=False,
        help="Products in this category represent recurring subscriptions"
    )
    
    is_digital_category = fields.Boolean(
        string="Digital Category",
        default=False,
        help="Products in this category are delivered digitally"
    )
    
    requires_inventory = fields.Boolean(
        string="Requires Inventory Tracking",
        default=True,
        help="Products in this category require physical inventory management"
    )
    
    # ========================================================================
    # INTEGRATION FIELDS
    # ========================================================================
    
    default_uom_id = fields.Many2one(
        'uom.uom',
        string="Default Unit of Measure",
        help="Default unit of measure for products in this category"
    )
    
    default_route_ids = fields.Many2many(
        'stock.route',
        'category_route_rel',
        'category_id',
        'route_id',
        string="Default Routes",
        help="Default routes for products in this category"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    ams_product_count = fields.Integer(
        string="AMS Products",
        compute='_compute_ams_product_count',
        help="Number of AMS products in this category"
    )
    
    total_product_count = fields.Integer(
        string="Total Products",
        compute='_compute_total_product_count',
        help="Total number of products in this category and subcategories"
    )
    
    category_summary = fields.Char(
        string="Category Summary",
        compute='_compute_category_summary',
        help="Summary of AMS category attributes"
    )
    
    category_type_display = fields.Char(
        string="Category Type Display",
        compute='_compute_category_type_display',
        help="Human-readable category type name"
    )
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_ams_product_count(self):
        """Compute AMS product count for this category."""
        for category in self:
            if category.is_ams_category:
                # Count products that have is_ams_product=True in this category
                category.ams_product_count = self.env['product.template'].search_count([
                    ('categ_id', 'child_of', category.id),
                    ('is_ams_product', '=', True)
                ])
            else:
                category.ams_product_count = 0
    
    def _compute_total_product_count(self):
        """Compute total product count including subcategories."""
        for category in self:
            category.total_product_count = self.env['product.template'].search_count([
                ('categ_id', 'child_of', category.id)
            ])
    
    def _compute_category_summary(self):
        """Compute category summary for display."""
        for category in self:
            if category.is_ams_category:
                attributes = []
                
                if category.ams_category_type:
                    type_dict = dict(category._fields['ams_category_type'].selection)
                    attributes.append(type_dict.get(category.ams_category_type))
                
                if category.requires_member_pricing:
                    attributes.append("Member Pricing")
                
                if category.is_subscription_category:
                    attributes.append("Subscription")
                
                if category.is_digital_category:
                    attributes.append("Digital")
                else:
                    attributes.append("Physical")
                
                if category.requires_inventory:
                    attributes.append("Inventory Tracked")
                
                category.category_summary = " • ".join(filter(None, attributes))
            else:
                category.category_summary = ""
    
    def _compute_category_type_display(self):
        """Compute human-readable category type display."""
        type_dict = dict(self._fields['ams_category_type'].selection)
        for category in self:
            category.category_type_display = type_dict.get(category.ams_category_type, '')
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('ams_category_type')
    def _onchange_ams_category_type(self):
        """Set default attributes based on AMS category type."""
        if self.ams_category_type:
            # Set is_ams_category to True when type is selected
            self.is_ams_category = True
            
            # Set sensible defaults based on category type
            category_defaults = {
                'membership': {
                    'requires_member_pricing': False,  # Members get membership pricing anyway
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': False,
                },
                'event': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': False,
                },
                'education': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'publication': {
                    'requires_member_pricing': True,
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'merchandise': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                },
                'certification': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                },
                'digital': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                },
            }
            
            defaults = category_defaults.get(self.ams_category_type, {})
            for field, value in defaults.items():
                setattr(self, field, value)
            
            # Set default UOM based on category type
            self._set_default_uom()
    
    def _set_default_uom(self):
        """Set default unit of measure based on category type."""
        if not self.default_uom_id:
            uom_mapping = {
                'membership': 'Units',  # Each membership
                'event': 'Units',       # Each registration
                'education': 'Units',   # Each course
                'publication': 'Units', # Each publication
                'merchandise': 'Units', # Each item
                'certification': 'Units', # Each certification
                'digital': 'Units',     # Each download
            }
            
            uom_name = uom_mapping.get(self.ams_category_type)
            if uom_name:
                uom = self.env['uom.uom'].search([('name', '=', uom_name)], limit=1)
                if uom:
                    self.default_uom_id = uom.id
    
    @api.onchange('is_digital_category')
    def _onchange_is_digital_category(self):
        """Digital categories typically don't need inventory tracking."""
        if self.is_digital_category:
            self.requires_inventory = False
    
    @api.onchange('is_ams_category')
    def _onchange_is_ams_category(self):
        """Clear AMS fields when unmarking as AMS category."""
        if not self.is_ams_category:
            self.ams_category_type = False
            self.requires_member_pricing = False
            self.is_subscription_category = False
            self.is_digital_category = False
            self.requires_inventory = True  # Reset to default
            self.default_uom_id = False
            self.default_route_ids = [(5, 0, 0)]  # Clear routes
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('is_digital_category', 'requires_inventory')
    def _check_digital_inventory(self):
        """Warn about digital categories with inventory tracking."""
        for category in self:
            if category.is_digital_category and category.requires_inventory:
                # This is just a warning case, not an error
                # Some digital categories might still need limited inventory tracking
                pass
    
    @api.constrains('parent_id', 'is_ams_category')
    def _check_ams_category_hierarchy(self):
        """Validate AMS category hierarchy."""
        for category in self:
            if category.is_ams_category and category.parent_id:
                # If parent is also AMS category, ensure consistent attributes
                if category.parent_id.is_ams_category:
                    if (category.ams_category_type and 
                        category.parent_id.ams_category_type and
                        category.ams_category_type != category.parent_id.ams_category_type):
                        # Allow different types in hierarchy, but warn
                        pass
    
    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set up category defaults."""
        categories = super().create(vals_list)
        
        for category in categories:
            if category.is_ams_category:
                category._setup_category_defaults()
        
        return categories
    
    def write(self, vals):
        """Override write to maintain category consistency."""
        result = super().write(vals)
        
        # If AMS category attributes changed, update defaults
        ams_fields = ['is_ams_category', 'ams_category_type', 'is_digital_category', 
                     'requires_inventory', 'requires_member_pricing', 'is_subscription_category']
        
        if any(field in vals for field in ams_fields):
            for category in self:
                if category.is_ams_category:
                    category._setup_category_defaults()
        
        return result
    
    def _setup_category_defaults(self):
        """Set up category defaults after creation/modification."""
        self.ensure_one()
        
        # Ensure default UOM is set
        if not self.default_uom_id:
            self._set_default_uom()
        
        # Set up default routes for inventory categories
        if self.requires_inventory and not self.default_route_ids:
            self._set_default_routes()
    
    def _set_default_routes(self):
        """Set default routes for inventory categories."""
        if self.requires_inventory:
            # Get standard routes like Buy, Manufacture, etc.
            buy_route = self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
            if buy_route:
                self.default_route_ids = [(4, buy_route.id)]
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    @api.model
    def get_ams_categories_by_type(self, ams_category_type=None):
        """Get AMS categories filtered by type.
        
        Args:
            ams_category_type (str, optional): AMS category type to filter by
            
        Returns:
            recordset: AMS categories of the specified type
        """
        domain = [('is_ams_category', '=', True)]
        if ams_category_type:
            domain.append(('ams_category_type', '=', ams_category_type))
        
        return self.search(domain)
    
    @api.model
    def get_digital_categories(self):
        """Get all digital product categories."""
        return self.search([('is_digital_category', '=', True)])
    
    @api.model
    def get_subscription_categories(self):
        """Get all subscription product categories."""
        return self.search([('is_subscription_category', '=', True)])
    
    @api.model
    def get_member_pricing_categories(self):
        """Get categories that support member pricing."""
        return self.search([('requires_member_pricing', '=', True)])
    
    @api.model
    def get_inventory_categories(self):
        """Get categories that require inventory tracking."""
        return self.search([('requires_inventory', '=', True)])
    
    def get_category_defaults_for_product(self):
        """Get default values for products in this category.
        
        Returns:
            dict: Default field values for new products
        """
        self.ensure_one()
        
        defaults = {}
        
        if self.is_ams_category:
            defaults.update({
                'is_ams_product': True,
                'has_member_pricing': self.requires_member_pricing,
                'is_digital_product': self.is_digital_category,
                'stock_controlled': self.requires_inventory,
                'type': 'service' if not self.requires_inventory else 'product',
            })
            
            if self.default_uom_id:
                defaults.update({
                    'uom_id': self.default_uom_id.id,
                    'uom_po_id': self.default_uom_id.id,
                })
            
            if self.default_route_ids:
                defaults['route_ids'] = [(6, 0, self.default_route_ids.ids)]
        
        return defaults
    
    def action_view_ams_products(self):
        """Open view of AMS products in this category."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('AMS Products - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [
                ('categ_id', 'child_of', self.id),
                ('is_ams_product', '=', True)
            ],
            'context': dict(
                self.env.context,
                default_categ_id=self.id,
                **self.get_category_defaults_for_product()
            ),
        }
    
    def action_view_all_products(self):
        """Open view of all products in this category."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Products - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('categ_id', 'child_of', self.id)],
            'context': dict(
                self.env.context,
                default_categ_id=self.id,
                **self.get_category_defaults_for_product()
            ),
        }
    
    def action_create_ams_product(self):
        """Create a new AMS product in this category."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create AMS Product - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'current',
            'context': dict(
                self.env.context,
                default_categ_id=self.id,
                **self.get_category_defaults_for_product()
            ),
        }
    
    def action_configure_category(self):
        """Open category configuration wizard."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Category - %s') % self.name,
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
    
    def toggle_ams_category(self):
        """Toggle AMS category status."""
        for category in self:
            category.is_ams_category = not category.is_ams_category
    
    # ========================================================================
    # REPORTING METHODS
    # ========================================================================
    
    def get_category_statistics(self):
        """Get detailed statistics for this category.
        
        Returns:
            dict: Category statistics and metrics
        """
        self.ensure_one()
        
        stats = {
            'total_products': self.total_product_count,
            'ams_products': self.ams_product_count,
            'category_type': self.category_type_display,
            'is_ams': self.is_ams_category,
            'attributes': {
                'member_pricing': self.requires_member_pricing,
                'subscription': self.is_subscription_category,
                'digital': self.is_digital_category,
                'inventory': self.requires_inventory,
            }
        }
        
        if self.is_ams_category:
            # Get additional AMS-specific statistics
            products = self.env['product.template'].search([
                ('categ_id', 'child_of', self.id),
                ('is_ams_product', '=', True)
            ])
            
            stats.update({
                'member_pricing_products': len(products.filtered('has_member_pricing')),
                'digital_products': len(products.filtered('is_digital_product')),
                'subscription_products': len(products.filtered(
                    lambda p: p.category_is_subscription)),
            })
        
        return stats
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def name_get(self):
        """Enhanced name display for AMS categories."""
        result = []
        for category in self:
            name = category.name
            if category.is_ams_category and category.ams_category_type:
                name = f"{name} ({category.category_type_display})"
            result.append((category.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search including AMS category type."""
        args = args or []
        
        if name:
            # Search in name and category type
            domain = [
                '|',
                ('name', operator, name),
                ('ams_category_type', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)