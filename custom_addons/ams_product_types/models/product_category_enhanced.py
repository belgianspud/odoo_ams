# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    """Extend Odoo's product category with AMS-specific functionality."""
    
    _inherit = 'product.category'

    # ========================================================================
    # BASIC CATEGORY DEFINITION
    # ========================================================================
    
    code = fields.Char(
        string="Category Code",
        size=20,
        help="Short code for reporting and integrations"
    )
    
    description = fields.Html(
        string="Description",
        help="Detailed description of this category and its purpose"
    )

    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        default=lambda self: self.env.company,
        help="Company this category belongs to"
    )
    
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
        ('digital', 'Digital Download'),
        ('donation', 'Donation')
    ], string="AMS Category Type", help="AMS-specific category classification")
    
    # ========================================================================
    # PRODUCT TYPE CONTROLS
    # ========================================================================
    
    default_product_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')
    ], string="Default Product Type", default='service',
        help="Default type for products created in this category")
    
    fulfillment_type = fields.Selection([
        ('shippable', 'Shippable'),
        ('downloadable', 'Downloadable'),
        ('portal_access', 'Portal Access'),
        ('event_based', 'Event-based'),
        ('donation', 'Donation (No Fulfillment)'),
        ('manual', 'Manual Fulfillment')
    ], string="Fulfillment Type", default='manual',
        help="How products in this category are fulfilled")
    
    default_income_account_id = fields.Many2one(
        'account.account',
        string="Default Income Account",
        domain="[('account_type', '=', 'income'), ('company_id', 'in', [company_id, False])]",
        help="Default income account for products in this category",
        check_company=True
    )
    
    default_expense_account_id = fields.Many2one(
        'account.account',
        string="Default Expense Account", 
        domain="[('account_type', '=', 'expense'), ('company_id', 'in', [company_id, False])]",
        help="Default expense account for products in this category",
        check_company=True
    )
    
    default_tax_ids = fields.Many2many(
        'account.tax',
        'category_tax_rel',
        'category_id',
        'tax_id',
        string="Default Taxes",
        domain="[('company_id', 'in', [company_id, False])]",
        help="Default taxes applied to products in this category",
        check_company=True
    )
    
    tax_exemption_reason = fields.Char(
        string="Tax Exemption Reason",
        help="Reason for tax exemption if applicable"
    )
    
    # ========================================================================
    # ASSOCIATION-SPECIFIC METADATA
    # ========================================================================
    
    is_membership_category = fields.Boolean(
        string="Membership Category",
        default=False,
        help="Products in this category are memberships that link to membership rules"
    )
    
    default_membership_level = fields.Char(
        string="Default Membership Level",
        help="Default membership tier for products in this category"
    )
    
    renewal_behavior = fields.Selection([
        ('one_time', 'One-time Purchase'),
        ('recurring', 'Recurring Subscription'),
        ('prorated', 'Prorated Renewal'),
        ('lifetime', 'Lifetime Access')
    ], string="Renewal Behavior", default='one_time',
        help="How products in this category handle renewals")
    
    grace_period_days = fields.Integer(
        string="Grace Period (Days)",
        default=0,
        help="Grace period for renewals and expiration logic"
    )
    
    grants_portal_access = fields.Boolean(
        string="Grants Portal Access",
        default=False,
        help="Purchasing products in this category grants portal login rights"
    )
    
    portal_group_ids = fields.Many2many(
        'res.groups',
        'category_portal_group_rel',
        'category_id',
        'group_id',
        string="Portal Groups",
        help="Groups automatically assigned when purchasing products in this category"
    )
    
    benefit_description = fields.Text(
        string="Benefit Description",
        help="Description of benefits included with products in this category"
    )
    
    # ========================================================================
    # OPERATIONAL CONTROLS
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
    
    delivery_mode = fields.Selection([
        ('ship', 'Ship to Customer'),
        ('pickup', 'Customer Pickup'),
        ('digital', 'Digital Delivery'),
        ('none', 'No Delivery Required')
    ], string="Delivery Mode", default='none',
        help="How products in this category are delivered")
    
    digital_asset_template = fields.Char(
        string="Digital Asset Template",
        help="Template or link pattern for digital assets tied to this category"
    )
    
    auto_send_welcome_email = fields.Boolean(
        string="Auto-send Welcome Email",
        default=False,
        help="Automatically send welcome email when product is purchased"
    )
    
    welcome_email_template_id = fields.Many2one(
        'mail.template',
        string="Welcome Email Template",
        help="Email template to use for welcome emails"
    )
    
    auto_create_invoice = fields.Boolean(
        string="Auto-create Invoice",
        default=True,
        help="Automatically create invoice when product is ordered"
    )
    
    # ========================================================================
    # PRICING & DISCOUNTING
    # ========================================================================
    
    default_pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Default Price List",
        help="Category-specific price list if applicable"
    )
    
    member_discount_percent = fields.Float(
        string="Member Discount %",
        default=0.0,
        help="Default discount percentage for members"
    )
    
    allows_student_pricing = fields.Boolean(
        string="Student Pricing Available",
        default=False,
        help="Products in this category offer student discounts"
    )
    
    allows_early_bird_pricing = fields.Boolean(
        string="Early Bird Pricing Available", 
        default=False,
        help="Products in this category offer early bird discounts"
    )
    
    is_tax_deductible_donation = fields.Boolean(
        string="Tax Deductible Donation",
        default=False,
        help="Purchases in this category are tax-deductible charitable contributions"
    )
    
    donation_receipt_template_id = fields.Many2one(
        'mail.template',
        string="Donation Receipt Template",
        help="Email template for donation receipts"
    )
    
    # ========================================================================
    # REPORTING & SEGMENTATION  
    # ========================================================================
    
    revenue_recognition_type = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('subscription', 'Subscription-based'),
        ('event_date', 'Recognize on Event Date')
    ], string="Revenue Recognition", default='immediate',
        help="How revenue is recognized for products in this category")
    
    analytics_tag_ids = fields.Many2many(
        'account.analytic.tag',
        'category_analytic_tag_rel',
        'category_id', 
        'tag_id',
        string="Analytics Tags",
        domain="[('company_id', 'in', [company_id, False])]",
        help="Default analytic tags for cost center or chapter tracking",
        check_company=True
    )

    visibility_control = fields.Selection([
        ('internal', 'Internal Only'),
        ('portal', 'Portal Visible'),
        ('public', 'Public'),
        ('members_only', 'Members Only')
    ], string="Visibility Control", default='internal',
        help="Who can see products in this category")
    
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
    
    fulfillment_summary = fields.Char(
        string="Fulfillment Summary",
        compute='_compute_fulfillment_summary',
        help="Summary of fulfillment and operational settings"
    )
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    def _compute_ams_product_count(self):
        """Compute AMS product count for this category."""
        for category in self:
            if category.is_ams_category:
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
    
    def _compute_fulfillment_summary(self):
        """Compute fulfillment and operational summary."""
        for category in self:
            if category.is_ams_category:
                parts = []
                
                if category.fulfillment_type:
                    fulfillment_dict = dict(category._fields['fulfillment_type'].selection)
                    parts.append(fulfillment_dict.get(category.fulfillment_type))
                
                if category.renewal_behavior and category.renewal_behavior != 'one_time':
                    renewal_dict = dict(category._fields['renewal_behavior'].selection)
                    parts.append(renewal_dict.get(category.renewal_behavior))
                
                if category.grants_portal_access:
                    parts.append("Portal Access")
                
                if category.auto_send_welcome_email:
                    parts.append("Welcome Email")
                
                category.fulfillment_summary = " • ".join(filter(None, parts))
            else:
                category.fulfillment_summary = ""

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('ams_category_type')
    def _onchange_ams_category_type(self):
        """Set default attributes based on AMS category type."""
        if self.ams_category_type:
            self.is_ams_category = True
            
            # Set comprehensive defaults based on category type
            category_defaults = {
                'membership': {
                    'requires_member_pricing': False,
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': False,
                    'fulfillment_type': 'manual',
                    'is_membership_category': True,
                    'renewal_behavior': 'recurring',
                    'grants_portal_access': True,
                    'revenue_recognition_type': 'deferred',
                    'auto_send_welcome_email': True,
                    'visibility_control': 'members_only',
                    'delivery_mode': 'none',
                },
                'event': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': False,
                    'fulfillment_type': 'event_based',
                    'revenue_recognition_type': 'event_date',
                    'auto_send_welcome_email': True,
                    'allows_early_bird_pricing': True,
                    'visibility_control': 'public',
                    'delivery_mode': 'none',
                },
                'education': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                    'fulfillment_type': 'shippable',
                    'allows_student_pricing': True,
                    'visibility_control': 'public',
                    'delivery_mode': 'ship',
                },
                'publication': {
                    'requires_member_pricing': True,
                    'is_subscription_category': True,
                    'is_digital_category': False,
                    'requires_inventory': True,
                    'fulfillment_type': 'shippable',
                    'revenue_recognition_type': 'subscription',
                    'visibility_control': 'public',
                    'delivery_mode': 'ship',
                },
                'merchandise': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': False,
                    'requires_inventory': True,
                    'fulfillment_type': 'shippable',
                    'delivery_mode': 'ship',
                    'visibility_control': 'public',
                },
                'certification': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                    'fulfillment_type': 'downloadable',
                    'grants_portal_access': True,
                    'auto_send_welcome_email': True,
                    'visibility_control': 'members_only',
                    'delivery_mode': 'digital',
                },
                'digital': {
                    'requires_member_pricing': True,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                    'fulfillment_type': 'downloadable',
                    'delivery_mode': 'digital',
                    'visibility_control': 'portal',
                },
                'donation': {
                    'requires_member_pricing': False,
                    'is_subscription_category': False,
                    'is_digital_category': True,
                    'requires_inventory': False,
                    'fulfillment_type': 'donation',
                    'is_tax_deductible_donation': True,
                    'auto_create_invoice': True,
                    'visibility_control': 'public',
                    'delivery_mode': 'none',
                },
            }
            
            defaults = category_defaults.get(self.ams_category_type, {})
            for field, value in defaults.items():
                setattr(self, field, value)
            
            self._set_default_uom()
    
    def _set_default_uom(self):
        """Set default unit of measure based on category type."""
        if not self.default_uom_id:
            uom = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
            if uom:
                self.default_uom_id = uom.id
    
    @api.onchange('is_digital_category')
    def _onchange_is_digital_category(self):
        """Digital categories typically don't need inventory tracking."""
        if self.is_digital_category:
            self.requires_inventory = False
            if not self.fulfillment_type or self.fulfillment_type == 'manual':
                self.fulfillment_type = 'downloadable'
            if not self.delivery_mode or self.delivery_mode == 'none':
                self.delivery_mode = 'digital'
    
    @api.onchange('fulfillment_type')
    def _onchange_fulfillment_type(self):
        """Update related fields based on fulfillment type."""
        fulfillment_mappings = {
            'shippable': {
                'requires_inventory': True,
                'is_digital_category': False,
                'delivery_mode': 'ship',
            },
            'downloadable': {
                'requires_inventory': False,
                'is_digital_category': True,
                'delivery_mode': 'digital',
            },
            'portal_access': {
                'requires_inventory': False,
                'grants_portal_access': True,
                'delivery_mode': 'none',
            },
            'donation': {
                'requires_inventory': False,
                'is_tax_deductible_donation': True,
                'delivery_mode': 'none',
            },
            'event_based': {
                'requires_inventory': False,
                'delivery_mode': 'none',
            },
        }
        
        if self.fulfillment_type in fulfillment_mappings:
            mapping = fulfillment_mappings[self.fulfillment_type]
            for field, value in mapping.items():
                setattr(self, field, value)
    
    @api.onchange('is_ams_category')
    def _onchange_is_ams_category(self):
        """Clear AMS fields when unmarking as AMS category."""
        if not self.is_ams_category:
            # Reset to basic defaults
            self.ams_category_type = False
            self.requires_member_pricing = False
            self.is_subscription_category = False
            self.is_digital_category = False
            self.requires_inventory = True
            self.fulfillment_type = 'manual'
            self.renewal_behavior = 'one_time'
            self.grants_portal_access = False
            self.auto_send_welcome_email = False
            self.is_tax_deductible_donation = False
            self.visibility_control = 'internal'
            self.delivery_mode = 'none'

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('is_digital_category', 'requires_inventory')
    def _check_digital_inventory(self):
        """Digital categories should not require inventory tracking."""
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
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate category code format."""
        for category in self:
            if category.code:
                if not category.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Category code can only contain letters, numbers, underscores, and hyphens."))
                if len(category.code) > 20:
                    raise ValidationError(_("Category code cannot be longer than 20 characters."))

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
                'type': self.default_product_type or 'service',
            })
            
            # Add accounting defaults
            if self.default_income_account_id:
                defaults['property_account_income_id'] = self.default_income_account_id.id
            
            if self.default_expense_account_id:
                defaults['property_account_expense_id'] = self.default_expense_account_id.id
            
            if self.default_tax_ids:
                defaults['taxes_id'] = [(6, 0, self.default_tax_ids.ids)]
            
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
            if category.code:
                name = f"[{category.code}] {name}"
            result.append((category.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search including AMS category type and code."""
        args = args or []
        
        if name:
            # Search in name, code, and category type
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('ams_category_type', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)