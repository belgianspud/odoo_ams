# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Enhanced AMS product template with comprehensive product behavior management.
    Provides category-driven defaults with employee override capabilities.
    """
    _inherit = 'product.template'

    # ========================================================================
    # AMS PRODUCT IDENTIFICATION
    # ========================================================================

    is_ams_product = fields.Boolean(
        string="AMS Product",
        default=False,
        help="Mark this product as an AMS-managed product with enhanced features"
    )

    # ========================================================================
    # PRODUCT BEHAVIOR TYPE (RADIO BUTTON SELECTION)
    # ========================================================================
    
    ams_product_behavior = fields.Selection([
        ('membership', 'Membership Product'),
        ('subscription', 'Subscription Product'), 
        ('event', 'Event Product'),
        ('publication', 'Publication Product'),
        ('merchandise', 'Merchandise Product'),
        ('certification', 'Certification Product'),
        ('digital', 'Digital Download'),
        ('donation', 'Donation Product'),
    ], string="Product Behavior Type", 
       help="Select the primary behavior and business logic for this product")

    # ========================================================================
    # SUBSCRIPTION & RECURRING FIELDS
    # ========================================================================
    
    is_subscription_product = fields.Boolean(
        string="Subscription Product",
        default=False,
        help="Product with recurring billing cycles"
    )
    
    subscription_term = fields.Integer(
        string="Subscription Term (Months)",
        default=12,
        help="Default subscription duration in months"
    )
    
    subscription_term_type = fields.Selection([
        ('months', 'Months'),
        ('years', 'Years'),
    ], string="Term Type", default='months',
       help="Whether the subscription term is in months or years")

    # ========================================================================
    # PORTAL & ACCESS CONTROL
    # ========================================================================
    
    grants_portal_access = fields.Boolean(
        string="Grants Portal Access",
        default=False,
        help="Purchasing this product grants customer portal login access"
    )
    
    portal_group_ids = fields.Many2many(
        'res.groups',
        'product_portal_group_rel',
        'product_id', 
        'group_id',
        string="Portal Access Groups",
        help="Specific portal groups granted when this product is purchased"
    )

    # ========================================================================
    # BENEFIT & BUNDLE MANAGEMENT
    # ========================================================================
    
    benefit_bundle_id = fields.Many2one(
        'product.template',
        string="Benefit Bundle",
        domain=[('is_ams_product', '=', True)],
        help="Related benefit package or bundle product"
    )
    
    includes_benefits = fields.Text(
        string="Included Benefits",
        help="Description of benefits, services, or access included with this product"
    )

    # ========================================================================
    # DONATION & TAX FIELDS
    # ========================================================================
    
    donation_tax_deductible = fields.Boolean(
        string="Tax Deductible Donation",
        default=False,
        help="Purchases are tax-deductible charitable contributions"
    )
    
    donation_receipt_template_id = fields.Many2one(
        'mail.template',
        string="Donation Receipt Template",
        help="Email template for donation tax receipts"
    )

    # ========================================================================
    # EVENT INTEGRATION
    # ========================================================================
    
    default_event_template_id = fields.Many2one(
        'event.event',
        string="Default Event Template", 
        help="Default event to link when this product is purchased"
    )
    
    creates_event_registration = fields.Boolean(
        string="Creates Event Registration",
        default=False,
        help="Automatically register customers for events when purchased"
    )

    # ========================================================================
    # ACCOUNTING INTEGRATION
    # ========================================================================
    
    deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string="Deferred Revenue Account",
        domain=[('account_type', '=', 'liability_current')],
        help="Account for deferred revenue (subscriptions, prepaid services)"
    )
    
    cash_account_id = fields.Many2one(
        'account.account', 
        string="Cash Receipt Account",
        domain=[('account_type', '=', 'asset_receivable')],
        help="Account for immediate cash receipts"
    )
    
    refund_account_id = fields.Many2one(
        'account.account',
        string="Refund Account",
        domain=[('account_type', '=', 'liability_current')], 
        help="Account for processing refunds"
    )
    
    membership_revenue_account_id = fields.Many2one(
        'account.account',
        string="Membership Revenue Account", 
        domain=[('account_type', '=', 'income')],
        help="Specific revenue account for membership income"
    )

    # ========================================================================
    # EXISTING FIELDS FROM CURRENT VERSION
    # ========================================================================

    member_price = fields.Monetary(
        string="Member Price",
        compute='_compute_member_price',
        store=True,
        help="Calculated from category member discount percentage"
    )

    member_savings = fields.Monetary(
        string="Member Savings",
        compute='_compute_member_savings',
        store=True,
        help="Amount saved with member pricing"
    )

    digital_url = fields.Char(
        string="Download URL",
        help="URL for digital product download"
    )

    digital_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Digital File",
        help="File attachment for digital product delivery"
    )

    has_digital_content = fields.Boolean(
        string="Has Digital Content",
        compute='_compute_has_digital_content',
        store=True,
        help="Whether digital content is available for this product"
    )

    requires_membership = fields.Boolean(
        string="Requires Membership",
        default=False,
        help="Whether membership is required to purchase this product"
    )

    legacy_product_id = fields.Char(
        string="Legacy Product ID",
        help="Product ID from legacy/external systems for data migration"
    )

    # ========================================================================
    # COMPUTED DISPLAY FIELDS
    # ========================================================================
    
    ams_category_display = fields.Selection(
        string="AMS Category",
        related='categ_id.ams_category_type',
        readonly=True,
        store=True,
        help="AMS category type from enhanced category"
    )

    pricing_summary = fields.Char(
        string="Pricing Summary",
        compute='_compute_pricing_summary',
        help="Summary of pricing for this product"
    )
    
    product_behavior_summary = fields.Char(
        string="Product Summary",
        compute='_compute_product_behavior_summary',
        help="Summary of product behavior and key attributes"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    @api.depends('categ_id.member_discount_percent', 'list_price', 'categ_id.requires_member_pricing')
    def _compute_member_price(self):
        """Calculate member price using category discount from ams_product_types"""
        for product in self:
            if (product.categ_id and 
                product.categ_id.requires_member_pricing and 
                product.categ_id.member_discount_percent):
                
                discount = product.categ_id.member_discount_percent / 100
                product.member_price = product.list_price * (1 - discount)
            else:
                product.member_price = product.list_price

    @api.depends('list_price', 'member_price')
    def _compute_member_savings(self):
        """Calculate member savings amount"""
        for product in self:
            product.member_savings = product.list_price - product.member_price

    @api.depends('digital_url', 'digital_attachment_id', 'categ_id.is_digital_category')
    def _compute_has_digital_content(self):
        """Check if digital content is available"""
        for product in self:
            if product.categ_id and product.categ_id.is_digital_category:
                product.has_digital_content = bool(
                    product.digital_url or product.digital_attachment_id
                )
            else:
                product.has_digital_content = False

    @api.depends('list_price', 'member_price', 'categ_id.requires_member_pricing')
    def _compute_pricing_summary(self):
        """Create pricing summary for display"""
        for product in self:
            if product.categ_id and product.categ_id.requires_member_pricing:
                if product.member_savings > 0:
                    product.pricing_summary = f"Members: ${product.member_price:.2f} (Save ${product.member_savings:.2f}) • Non-members: ${product.list_price:.2f}"
                else:
                    product.pricing_summary = f"Members & Non-members: ${product.list_price:.2f}"
            else:
                product.pricing_summary = f"${product.list_price:.2f}"

    @api.depends('ams_product_behavior', 'is_subscription_product', 'grants_portal_access', 'donation_tax_deductible')
    def _compute_product_behavior_summary(self):
        """Generate a summary of product behavior"""
        for product in self:
            parts = []
            
            if product.ams_product_behavior:
                behavior_dict = dict(product._fields['ams_product_behavior'].selection)
                parts.append(behavior_dict.get(product.ams_product_behavior))
            
            if product.is_subscription_product:
                term_text = f"{product.subscription_term} {product.subscription_term_type}"
                parts.append(f"Subscription: {term_text}")
            
            if product.grants_portal_access:
                parts.append("Portal Access")
                
            if product.donation_tax_deductible:
                parts.append("Tax Deductible")
                
            product.product_behavior_summary = " • ".join(parts) if parts else "Standard Product"

    # ========================================================================
    # ONCHANGE METHODS FOR SMART DEFAULTS
    # ========================================================================
    
    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior(self):
        """Apply smart defaults based on selected behavior type"""
        if not self.ams_product_behavior:
            return
            
        behavior_defaults = {
            'membership': {
                'is_subscription_product': True,
                'grants_portal_access': True,
                'subscription_term': 12,
                'subscription_term_type': 'months',
                'type': 'service',
            },
            'subscription': {
                'is_subscription_product': True,
                'subscription_term': 12,
                'subscription_term_type': 'months',
                'type': 'service',
            },
            'event': {
                'creates_event_registration': True,
                'type': 'service',
            },
            'publication': {
                'is_subscription_product': True,
                'subscription_term': 12,
                'subscription_term_type': 'months',
            },
            'merchandise': {
                'type': 'consu',
            },
            'certification': {
                'grants_portal_access': True,
                'type': 'service',
            },
            'digital': {
                'type': 'service',
            },
            'donation': {
                'donation_tax_deductible': True,
                'type': 'service',
            },
        }
        
        defaults = behavior_defaults.get(self.ams_product_behavior, {})
        for field, value in defaults.items():
            if hasattr(self, field) and not getattr(self, field):
                setattr(self, field, value)

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        """Enhanced category onchange with behavior suggestions"""
        result = super()._onchange_categ_id()
        
        if self.categ_id and self.categ_id.is_ams_category:
            # Suggest behavior type based on category
            if not self._origin.id and self.categ_id.ams_category_type:
                self.ams_product_behavior = self.categ_id.ams_category_type
                # This will trigger _onchange_ams_product_behavior automatically
        
        return result

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Set defaults for subscription products"""
        if self.is_subscription_product and not self.subscription_term:
            self.subscription_term = 12
            self.subscription_term_type = 'months'

    # ========================================================================
    # BUSINESS METHODS - EXISTING FUNCTIONALITY ENHANCED
    # ========================================================================

    def get_price_for_partner(self, partner):
        """
        Get appropriate price based on partner's membership status from ams_member_data.
        
        Args:
            partner (res.partner): Partner to check membership status
            
        Returns:
            float: Appropriate price for the partner
        """
        self.ensure_one()
        
        if not partner:
            return self.list_price
            
        # Check membership status using ams_member_data fields
        is_member = self._check_partner_membership(partner)
        
        # Return member price if applicable
        if is_member and self.categ_id and self.categ_id.requires_member_pricing:
            return self.member_price
            
        return self.list_price

    def _check_partner_membership(self, partner):
        """
        Check if partner is an active member using ams_member_data fields.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner is an active member
        """
        if not partner:
            return False

        # Check ams_member_data fields
        if hasattr(partner, 'is_member') and hasattr(partner, 'membership_status'):
            return partner.is_member and partner.membership_status == 'active'
        
        # Fallback for standard Odoo membership module
        if hasattr(partner, 'membership_state'):
            return partner.membership_state in ['invoiced', 'paid']
            
        return False

    def can_be_purchased_by_partner(self, partner):
        """
        Check if this product can be purchased by the given partner.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner can purchase this product
        """
        self.ensure_one()
        
        # Basic availability check
        if not self.active or not self.sale_ok:
            return False
            
        # Check membership requirement
        if self.requires_membership:
            return self._check_partner_membership(partner)
            
        return True

    def get_digital_content_access(self, partner=None):
        """
        Get digital content access information.
        
        Args:
            partner (res.partner, optional): Partner requesting access
            
        Returns:
            dict: Digital content access information
        """
        self.ensure_one()
        
        # Check if partner can access (for future access control)
        can_access = True
        if partner and self.requires_membership:
            can_access = self._check_partner_membership(partner)
            
        return {
            'is_digital': bool(self.categ_id and self.categ_id.is_digital_category),
            'has_content': self.has_digital_content,
            'download_url': self.digital_url if can_access else None,
            'attachment_id': self.digital_attachment_id.id if (can_access and self.digital_attachment_id) else None,
            'can_access': can_access,
        }

    # ========================================================================
    # NEW BUSINESS METHODS FOR ENHANCED FUNCTIONALITY
    # ========================================================================

    def get_subscription_details(self):
        """
        Get subscription details for this product.
        
        Returns:
            dict: Subscription configuration
        """
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'is_subscription': False}
            
        return {
            'is_subscription': True,
            'term': self.subscription_term,
            'term_type': self.subscription_term_type,
            'term_display': f"{self.subscription_term} {dict(self._fields['subscription_term_type'].selection)[self.subscription_term_type]}",
        }

    def get_portal_access_details(self):
        """
        Get portal access configuration.
        
        Returns:
            dict: Portal access information
        """
        self.ensure_one()
        
        return {
            'grants_access': self.grants_portal_access,
            'portal_groups': self.portal_group_ids.mapped('name'),
            'portal_group_ids': self.portal_group_ids.ids,
        }

    def get_donation_details(self):
        """
        Get donation tax information.
        
        Returns:
            dict: Donation configuration
        """
        self.ensure_one()
        
        return {
            'is_tax_deductible': self.donation_tax_deductible,
            'receipt_template': self.donation_receipt_template_id.name if self.donation_receipt_template_id else None,
            'receipt_template_id': self.donation_receipt_template_id.id if self.donation_receipt_template_id else None,
        }

    def get_event_integration_details(self):
        """
        Get event integration configuration.
        
        Returns:
            dict: Event integration information
        """
        self.ensure_one()
        
        return {
            'creates_registration': self.creates_event_registration,
            'default_event': self.default_event_template_id.name if self.default_event_template_id else None,
            'default_event_id': self.default_event_template_id.id if self.default_event_template_id else None,
        }

    def get_accounting_configuration(self):
        """
        Get accounting GL account configuration.
        
        Returns:
            dict: Accounting account information
        """
        self.ensure_one()
        
        return {
            'deferred_revenue_account': self.deferred_revenue_account_id.code if self.deferred_revenue_account_id else None,
            'cash_account': self.cash_account_id.code if self.cash_account_id else None,
            'refund_account': self.refund_account_id.code if self.refund_account_id else None,
            'membership_revenue_account': self.membership_revenue_account_id.code if self.membership_revenue_account_id else None,
        }

    # ========================================================================
    # SKU MANAGEMENT (ENHANCED)
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create with behavior-based SKU generation"""
        for vals in vals_list:
            # Generate behavior-based SKU if needed
            if not vals.get('default_code') and vals.get('name'):
                behavior = vals.get('ams_product_behavior')
                if behavior:
                    vals['default_code'] = self._generate_behavior_based_sku(
                        vals['name'], behavior
                    )
                elif vals.get('categ_id'):
                    category = self.env['product.category'].browse(vals['categ_id'])
                    if category.is_ams_category:
                        vals['default_code'] = self._generate_simple_sku(vals['name'])
                        
        return super().create(vals_list)

    def _generate_behavior_based_sku(self, name, behavior):
        """
        Generate SKU with behavior type prefix.
        
        Args:
            name (str): Product name
            behavior (str): Product behavior type
            
        Returns:
            str: Generated SKU with behavior prefix
        """
        prefixes = {
            'membership': 'MEM',
            'subscription': 'SUB',
            'event': 'EVT',
            'publication': 'PUB',
            'merchandise': 'MERCH',
            'certification': 'CERT',
            'digital': 'DIG',
            'donation': 'DON',
        }
        
        prefix = prefixes.get(behavior, 'PROD')
        base_name = re.sub(r'[^A-Z0-9\s]', '', name.upper())
        base_name = re.sub(r'\s+', '', base_name)[:8]
        
        if not base_name:
            base_name = 'PRODUCT'
            
        base_sku = f"{prefix}-{base_name}"
        return self._ensure_sku_uniqueness(base_sku)

    def _generate_simple_sku(self, name):
        """
        Generate a simple SKU from product name.
        
        Args:
            name (str): Product name
            
        Returns:
            str: Generated SKU
        """
        if not name:
            return 'PRODUCT'
            
        # Clean name and create base SKU
        base_sku = re.sub(r'[^A-Z0-9\s]', '', name.upper())
        base_sku = re.sub(r'\s+', '', base_sku)[:10]  # Remove spaces, limit length
        
        if not base_sku:
            base_sku = 'PRODUCT'
            
        # Ensure uniqueness
        return self._ensure_sku_uniqueness(base_sku)

    def _ensure_sku_uniqueness(self, base_sku):
        """
        Ensure SKU is unique by adding counter if needed.
        
        Args:
            base_sku (str): Base SKU to make unique
            
        Returns:
            str: Unique SKU
        """
        counter = 1
        sku = base_sku
        
        while self.search([('default_code', '=', sku)], limit=1):
            sku = f"{base_sku}{counter:02d}"
            counter += 1
            
        return sku

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('subscription_term')
    def _check_subscription_term(self):
        """Validate subscription term values"""
        for product in self:
            if product.is_subscription_product and product.subscription_term <= 0:
                raise ValidationError(_("Subscription term must be greater than 0."))

    @api.constrains('digital_url')
    def _check_digital_url_format(self):
        """Validate digital download URL format"""
        for product in self:
            if product.digital_url:
                if not product.digital_url.startswith(('http://', 'https://')):
                    raise ValidationError(
                        _("Digital download URL must start with http:// or https://")
                    )

    @api.constrains('ams_product_behavior', 'digital_url', 'digital_attachment_id')
    def _check_digital_content_requirements(self):
        """Check that digital products have appropriate content configured"""
        for product in self:
            # Only check digital content requirements for digital and certification behaviors
            if product.ams_product_behavior in ['digital', 'certification']:
                if not product.digital_url and not product.digital_attachment_id:
                    raise ValidationError(
                        "Digital products must have either a download URL or file attachment configured. "
                        f"Product '{product.name}' is missing digital content."
                    )

    @api.constrains('ams_product_behavior', 'default_event_template_id')
    def _check_event_template_requirement(self):
        """Validate event products have event template if creates_event_registration is True"""
        for product in self:
            if (product.ams_product_behavior == 'event' and 
                product.creates_event_registration and 
                not product.default_event_template_id):
                
                raise ValidationError(
                    _("Event products that create registrations must have a default event template.")
                )

    # ========================================================================
    # QUERY METHODS FOR OTHER MODULES (ENHANCED)
    # ========================================================================

    @api.model
    def get_ams_products_by_category_type(self, category_type=None):
        """Get AMS products filtered by category type"""
        domain = [('is_ams_product', '=', True)]
        if category_type:
            domain.append(('categ_id.ams_category_type', '=', category_type))
        return self.search(domain)

    @api.model
    def get_products_by_behavior_type(self, behavior_type=None):
        """Get products filtered by behavior type"""
        domain = [('ams_product_behavior', '!=', False)]
        if behavior_type:
            domain.append(('ams_product_behavior', '=', behavior_type))
        return self.search(domain)

    @api.model  
    def get_member_pricing_products(self):
        """Get all products that offer member pricing"""
        return self.search([
            ('is_ams_product', '=', True),
            ('categ_id.requires_member_pricing', '=', True)
        ])

    @api.model
    def get_digital_products(self):
        """Get all digital products"""
        return self.search([
            ('is_ams_product', '=', True),
            ('categ_id.is_digital_category', '=', True)
        ])

    @api.model
    def get_subscription_products(self):
        """Get all subscription products"""
        return self.search([('is_subscription_product', '=', True)])

    @api.model
    def get_donation_products(self):
        """Get all donation products"""
        return self.search([('donation_tax_deductible', '=', True)])

    @api.model
    def get_portal_access_products(self):
        """Get all products that grant portal access"""
        return self.search([('grants_portal_access', '=', True)])

    @api.model
    def get_event_products(self):
        """Get all event-related products"""
        return self.search([('ams_product_behavior', '=', 'event')])

    @api.model
    def get_membership_required_products(self):
        """Get all products that require membership"""
        return self.search([('requires_membership', '=', True)])

    # ========================================================================
    # ACTIONS FOR UI (ENHANCED)
    # ========================================================================

    def action_view_category(self):
        """Open the product category form"""
        self.ensure_one()
        if not self.categ_id:
            return False
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Category'),
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.categ_id.id,
            'target': 'current',
        }

    def action_test_product_behavior(self):
        """Test product behavior configuration"""
        self.ensure_one()
        
        behavior_info = []
        
        if self.ams_product_behavior:
            behavior_info.append(f"Behavior: {dict(self._fields['ams_product_behavior'].selection)[self.ams_product_behavior]}")
        
        if self.is_subscription_product:
            subscription = self.get_subscription_details()
            behavior_info.append(f"Subscription: {subscription['term_display']}")
        
        if self.grants_portal_access:
            portal = self.get_portal_access_details()
            behavior_info.append(f"Portal Groups: {', '.join(portal['portal_groups'])}")
        
        if self.donation_tax_deductible:
            behavior_info.append("Tax Deductible Donation")
        
        if self.creates_event_registration:
            event = self.get_event_integration_details()
            behavior_info.append(f"Event Template: {event['default_event'] or 'None'}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(behavior_info) if behavior_info else 'No special behavior configured',
                'title': f'Product Behavior Test for {self.name}',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_test_member_pricing(self):
        """Test member pricing with sample members"""
        self.ensure_one()
        
        # Find sample members for testing
        members = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('membership_status', '=', 'active')
        ], limit=3)
        
        non_members = self.env['res.partner'].search([
            ('is_member', '=', False)
        ], limit=2)
        
        results = []
        for partner in members:
            price = self.get_price_for_partner(partner)
            results.append(f"Member {partner.name}: ${price:.2f}")
            
        for partner in non_members:
            price = self.get_price_for_partner(partner)
            results.append(f"Non-member {partner.name}: ${price:.2f}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(results),
                'title': f'Pricing Test for {self.name}',
                'type': 'info',
                'sticky': True,
            }
        }