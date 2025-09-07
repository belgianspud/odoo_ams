# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AMSProductType(models.Model):
    """Product type classification for association products and services."""
    
    _name = 'ams.product.type'
    _inherit = ['mail.thread']
    _description = 'AMS Product Type'
    _order = 'category, name'
    
    # ========================================================================
    # FIELDS
    # ========================================================================
    
    name = fields.Char(
        string="Product Type",
        required=True,
        help="Display name for this product type"
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for this product type"
    )
    
    category = fields.Selection([
        ('membership', 'Membership'),
        ('event', 'Event'),
        ('education', 'Education'),
        ('publication', 'Publication'),
        ('merchandise', 'Merchandise'),
        ('certification', 'Certification'),
        ('digital', 'Digital Download')
    ], string="Category", required=True, help="Primary category classification")
    
    description = fields.Text(
        string="Description",
        help="Detailed description of this product type"
    )
    
    # ========================================================================
    # PRODUCT ATTRIBUTES
    # ========================================================================
    
    requires_member_pricing = fields.Boolean(
        string="Supports Member Pricing",
        default=False,
        help="This product type offers different pricing for members vs non-members"
    )
    
    is_subscription = fields.Boolean(
        string="Is Subscription Product",
        default=False,
        help="This product type represents a recurring subscription"
    )
    
    is_digital = fields.Boolean(
        string="Is Digital Product",
        default=False,
        help="This product type is delivered digitally (download, online access)"
    )
    
    requires_inventory = fields.Boolean(
        string="Requires Inventory Tracking",
        default=True,
        help="This product type requires physical inventory management"
    )
    
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Inactive product types cannot be assigned to new products"
    )
    
    # ========================================================================
    # INTEGRATION FIELDS
    # ========================================================================
    
    product_category_id = fields.Many2one(
        'product.category',
        string="Default Product Category",
        help="Default Odoo product category for products of this type"
    )
    
    default_uom_id = fields.Many2one(
        'uom.uom',
        string="Default Unit of Measure",
        help="Default unit of measure for products of this type"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    product_count = fields.Integer(
        string="Products",
        compute='_compute_product_count',
        help="Number of products using this type"
    )
    
    category_display = fields.Char(
        string="Category Display",
        compute='_compute_category_display',
        help="Human-readable category name"
    )
    
    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Product type code must be unique!'),
        ('name_unique', 'UNIQUE(name)', 'Product type name must be unique!'),
    ]
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format."""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(record.code) > 20:
                    raise ValidationError(_("Code cannot be longer than 20 characters"))
    
    @api.constrains('is_digital', 'requires_inventory')
    def _check_digital_inventory(self):
        """Digital products typically don't require inventory tracking."""
        for record in self:
            if record.is_digital and record.requires_inventory:
                # This is just a warning case, not an error
                # Some digital products might still need limited inventory tracking
                pass
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_product_count(self):
        """Compute current product count for this type."""
        for record in self:
            record.product_count = self.env['product.template'].search_count([
                ('ams_product_type_id', '=', record.id)
            ])
    
    def _compute_category_display(self):
        """Get human-readable category display."""
        category_dict = dict(self._fields['category'].selection)
        for record in self:
            record.category_display = category_dict.get(record.category, record.category)
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name: "Annual Membership" -> "ANNUAL_MEMBERSHIP"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
    
    @api.onchange('category')
    def _onchange_category(self):
        """Set default attributes based on category."""
        if self.category:
            # Set sensible defaults based on category
            category_defaults = {
                'membership': {
                    'requires_member_pricing': False,  # Members get membership pricing anyway
                    'is_subscription': True,
                    'is_digital': False,
                    'requires_inventory': False,
                },
                'event': {
                    'requires_member_pricing': True,
                    'is_subscription': False,
                    'is_digital': False,
                    'requires_inventory': False,  # Usually just registration
                },
                'education': {
                    'requires_member_pricing': True,
                    'is_subscription': False,
                    'is_digital': False,
                    'requires_inventory': True,
                },
                'publication': {
                    'requires_member_pricing': True,
                    'is_subscription': True,
                    'is_digital': False,
                    'requires_inventory': True,
                },
                'merchandise': {
                    'requires_member_pricing': True,
                    'is_subscription': False,
                    'is_digital': False,
                    'requires_inventory': True,
                },
                'certification': {
                    'requires_member_pricing': True,
                    'is_subscription': False,
                    'is_digital': True,
                    'requires_inventory': False,
                },
                'digital': {
                    'requires_member_pricing': True,
                    'is_subscription': False,
                    'is_digital': True,
                    'requires_inventory': False,
                },
            }
            
            defaults = category_defaults.get(self.category, {})
            for field, value in defaults.items():
                setattr(self, field, value)
            
            # Set default product category if available
            self._set_default_product_category()
    
    def _set_default_product_category(self):
        """Set default Odoo product category based on AMS category."""
        category_mapping = {
            'membership': 'Membership',
            'event': 'Events',
            'education': 'Education',
            'publication': 'Publications',
            'merchandise': 'Merchandise',
            'certification': 'Certifications',
            'digital': 'Digital Products',
        }
        
        if self.category:
            category_name = category_mapping.get(self.category)
            if category_name:
                product_category = self.env['product.category'].search([
                    ('name', '=', category_name)
                ], limit=1)
                if product_category:
                    self.product_category_id = product_category.id
    
    @api.onchange('is_digital')
    def _onchange_is_digital(self):
        """Digital products typically don't need inventory tracking."""
        if self.is_digital:
            self.requires_inventory = False
    
    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set up default product categories."""
        records = super().create(vals_list)
        
        # Create corresponding product categories if they don't exist
        for record in records:
            record._ensure_product_category_exists()
        
        return records
    
    def _ensure_product_category_exists(self):
        """Ensure corresponding product category exists."""
        category_mapping = {
            'membership': 'Membership',
            'event': 'Events',
            'education': 'Education',
            'publication': 'Publications',
            'merchandise': 'Merchandise',
            'certification': 'Certifications',
            'digital': 'Digital Products',
        }
        
        category_name = category_mapping.get(self.category)
        if category_name:
            product_category = self.env['product.category'].search([
                ('name', '=', category_name)
            ], limit=1)
            
            if not product_category:
                product_category = self.env['product.category'].create({
                    'name': category_name,
                })
            
            if not self.product_category_id:
                self.product_category_id = product_category.id
    
    def copy(self, default=None):
        """Override copy to ensure unique names and codes."""
        default = dict(default or {})
        default.update({
            'name': _("%s (Copy)") % self.name,
            'code': "%s_COPY" % self.code,
        })
        return super().copy(default)
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def get_type_summary(self):
        """Get summary information about this product type.
        
        Returns:
            str: Summary description
        """
        self.ensure_one()
        
        attributes = []
        
        if self.requires_member_pricing:
            attributes.append(_("Member Pricing"))
        
        if self.is_subscription:
            attributes.append(_("Subscription"))
        
        if self.is_digital:
            attributes.append(_("Digital"))
        else:
            attributes.append(_("Physical"))
        
        if self.requires_inventory:
            attributes.append(_("Inventory Tracked"))
        
        summary = _("Category: %s") % self.category_display
        if attributes:
            summary += " • " + " • ".join(attributes)
        
        return summary
    
    @api.model
    def get_types_by_category(self, category=None):
        """Get product types filtered by category.
        
        Args:
            category (str, optional): Category to filter by
            
        Returns:
            recordset: Product types in the category
        """
        domain = [('active', '=', True)]
        if category:
            domain.append(('category', '=', category))
        
        return self.search(domain)
    
    @api.model
    def get_digital_types(self):
        """Get all digital product types."""
        return self.search([('is_digital', '=', True), ('active', '=', True)])
    
    @api.model
    def get_subscription_types(self):
        """Get all subscription product types."""
        return self.search([('is_subscription', '=', True), ('active', '=', True)])
    
    @api.model
    def get_member_pricing_types(self):
        """Get product types that support member pricing."""
        return self.search([('requires_member_pricing', '=', True), ('active', '=', True)])
    
    def action_view_products(self):
        """Open view of products using this type."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('ams_product_type_id', '=', self.id)],
            'context': {
                'default_ams_product_type_id': self.id,
                'default_categ_id': self.product_category_id.id if self.product_category_id else False,
                'default_type': 'service' if not self.requires_inventory else 'product',
            },
        }
    
    def action_create_product(self):
        """Create a new product of this type."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Product - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_ams_product_type_id': self.id,
                'default_categ_id': self.product_category_id.id if self.product_category_id else False,
                'default_type': 'service' if not self.requires_inventory else 'product',
                'default_is_digital': self.is_digital,
                'default_recurring_rule_type': 'yearly' if self.is_subscription else False,
            },
        }
    
    def toggle_active(self):
        """Toggle active status."""
        for record in self:
            record.active = not record.active
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            if record.category_display:
                name = f"{name} ({record.category_display})"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search to include code and category."""
        args = args or []
        
        if name:
            # Search in name, code, and category
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('category', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class ProductTemplate(models.Model):
    """Extend product template with AMS-specific functionality."""
    
    _inherit = 'product.template'
    
    # ========================================================================
    # AMS FIELDS
    # ========================================================================
    
    ams_product_type_id = fields.Many2one(
        'ams.product.type',
        string="AMS Product Type",
        help="AMS-specific product type classification"
    )
    
    is_digital = fields.Boolean(
        string="Digital Product",
        related='ams_product_type_id.is_digital',
        store=True,
        help="Product is delivered digitally"
    )
    
    requires_member_pricing = fields.Boolean(
        string="Member Pricing",
        related='ams_product_type_id.requires_member_pricing',
        store=True,
        help="Product supports member vs non-member pricing"
    )
    
    is_subscription = fields.Boolean(
        string="Subscription Product",
        related='ams_product_type_id.is_subscription',
        store=True,
        help="Product is a recurring subscription"
    )
    
    ams_category = fields.Selection(
        related='ams_product_type_id.category',
        string="AMS Category",
        store=True,
        help="AMS product category"
    )
    
    # ========================================================================
    # MEMBER PRICING FIELDS
    # ========================================================================
    
    member_list_price = fields.Float(
        string="Member Price",
        help="List price for association members"
    )
    
    member_standard_price = fields.Float(
        string="Member Cost",
        help="Cost price for member pricing calculations"
    )
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('ams_product_type_id')
    def _onchange_ams_product_type(self):
        """Set product attributes based on AMS product type."""
        if self.ams_product_type_id:
            # Set product category
            if self.ams_product_type_id.product_category_id:
                self.categ_id = self.ams_product_type_id.product_category_id
            
            # Set product type (service vs storable)
            if not self.ams_product_type_id.requires_inventory:
                self.type = 'service'
            else:
                self.type = 'product'
            
            # Set default UoM if specified
            if self.ams_product_type_id.default_uom_id:
                self.uom_id = self.ams_product_type_id.default_uom_id
                self.uom_po_id = self.ams_product_type_id.default_uom_id
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    def get_member_price(self):
        """Get the member price for this product.
        
        Returns:
            float: Member price or regular price if no member pricing
        """
        self.ensure_one()
        if self.requires_member_pricing and self.member_list_price:
            return self.member_list_price
        return self.list_price
    
    def get_price_for_member_type(self, is_member=False):
        """Get price based on member status.
        
        Args:
            is_member (bool): Whether the customer is a member
            
        Returns:
            float: Appropriate price for member status
        """
        self.ensure_one()
        if is_member and self.requires_member_pricing and self.member_list_price:
            return self.member_list_price
        return self.list_price
    
    @api.model
    def get_products_by_ams_category(self, category):
        """Get products by AMS category.
        
        Args:
            category (str): AMS category
            
        Returns:
            recordset: Products in the category
        """
        return self.search([('ams_category', '=', category)])
    
    def action_view_ams_product_type(self):
        """Open the AMS product type form."""
        self.ensure_one()
        if not self.ams_product_type_id:
            return False
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('AMS Product Type'),
            'res_model': 'ams.product.type',
            'view_mode': 'form',
            'res_id': self.ams_product_type_id.id,
            'target': 'current',
        }