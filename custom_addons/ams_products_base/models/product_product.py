# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    """
    Enhanced AMS product variant extensions with comprehensive behavior inheritance.
    Delegates most functionality to template while adding variant-specific essentials.
    """
    _inherit = 'product.product'

    # ========================================================================
    # TEMPLATE FIELD REFERENCES (for easier access and performance)
    # ========================================================================

    template_ams_product_behavior = fields.Selection([
        ('membership', 'Membership Product'),
        ('event', 'Event Product'),
        ('publication', 'Publication Product'),
        ('merchandise', 'Merchandise Product'),
        ('certification', 'Certification Product'),
        ('digital', 'Digital Download'),
        ('donation', 'Donation Product'),
        ('service', 'Service Product'),
    ], string="Template Product Behavior",
       related='product_tmpl_id.ams_product_behavior',
       readonly=True,
       store=True)

    template_member_price = fields.Monetary(
        related='product_tmpl_id.member_price',
        string="Template Member Price",
        readonly=True
    )

    template_member_savings = fields.Monetary(
        related='product_tmpl_id.member_savings',
        string="Template Member Savings",
        readonly=True
    )

    template_requires_membership = fields.Boolean(
        related='product_tmpl_id.requires_membership',
        string="Template Requires Membership",
        readonly=True,
        store=True
    )

    template_has_digital_content = fields.Boolean(
        related='product_tmpl_id.has_digital_content',
        string="Template Has Digital Content",
        readonly=True,
        store=True
    )

    template_grants_portal_access = fields.Boolean(
        related='product_tmpl_id.grants_portal_access',
        string="Template Grants Portal Access",
        readonly=True,
        store=True
    )

    template_donation_tax_deductible = fields.Boolean(
        related='product_tmpl_id.donation_tax_deductible',
        string="Template Tax Deductible",
        readonly=True,
        store=True
    )

    template_creates_event_registration = fields.Boolean(
        related='product_tmpl_id.creates_event_registration',
        string="Template Creates Event Registration",
        readonly=True,
        store=True
    )

    template_ams_category_display = fields.Selection([
        ('membership', 'Membership'),
        ('event', 'Event'),
        ('education', 'Education'),
        ('publication', 'Publication'),
        ('merchandise', 'Merchandise'),
        ('certification', 'Certification'),
        ('digital', 'Digital Download'),
        ('donation', 'Donation')
    ], string="Template AMS Category",
       related='product_tmpl_id.ams_category_display',
       readonly=True,
       store=True)

    # ========================================================================
    # VARIANT-SPECIFIC ENHANCEMENTS
    # ========================================================================

    variant_legacy_id = fields.Char(
        string="Variant Legacy ID",
        help="Variant ID from legacy/external systems"
    )

    variant_notes = fields.Text(
        string="Variant Notes",
        help="Variant-specific notes and configuration details"
    )

    # ========================================================================
    # COMPUTED VARIANT STATUS AND AVAILABILITY
    # ========================================================================

    @api.depends('template_has_digital_content', 'qty_available', 'template_ams_product_behavior')
    def _compute_availability_status(self):
        """Calculate comprehensive availability status for this variant"""
        for variant in self:
            if variant.template_ams_product_behavior == 'digital' or variant.template_has_digital_content:
                variant.availability_status = 'digital_available' if variant.template_has_digital_content else 'digital_missing'
            elif variant.template_ams_product_behavior == 'membership':
                variant.availability_status = 'membership_available'
            elif variant.template_ams_product_behavior == 'event':
                variant.availability_status = 'event_available' if variant.template_creates_event_registration else 'event_missing_template'
            elif variant.template_ams_product_behavior == 'donation':
                variant.availability_status = 'donation_available'
            elif variant.template_ams_product_behavior == 'certification':
                variant.availability_status = 'certification_available' if variant.template_has_digital_content else 'certification_missing_content'
            elif variant.type == 'product':  # Stockable product (merchandise)
                if variant.qty_available > 0:
                    variant.availability_status = 'in_stock'
                else:
                    variant.availability_status = 'out_of_stock'
            else:
                variant.availability_status = 'service_available'

    availability_status = fields.Selection([
        ('standard', 'Standard Product'),
        ('membership_available', 'Membership Available'),
        ('event_available', 'Event Registration Available'),
        ('event_missing_template', 'Event Missing Template'),
        ('digital_available', 'Digital Available'),
        ('digital_missing', 'Digital Content Missing'),
        ('certification_available', 'Certification Available'),
        ('certification_missing_content', 'Certification Missing Content'),
        ('donation_available', 'Donation Available'),
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('service_available', 'Service Available'),
    ], string="Availability Status", compute='_compute_availability_status', store=True)

    @api.depends('default_code', 'product_tmpl_id.default_code', 'template_ams_product_behavior')
    def _compute_effective_sku(self):
        """Calculate effective SKU with behavior-aware generation"""
        for variant in self:
            if variant.default_code:
                variant.effective_sku = variant.default_code
            elif variant.product_tmpl_id.default_code:
                base_sku = variant.product_tmpl_id.default_code
                if len(variant.product_tmpl_id.product_variant_ids) > 1:
                    # Multi-variant template - add variant suffix
                    if variant.template_ams_product_behavior:
                        # Use behavior-aware suffix
                        behavior_suffixes = {
                            'membership': 'MEM',
                            'event': 'EVT',
                            'publication': 'PUB',
                            'merchandise': 'MERCH',
                            'certification': 'CERT',
                            'digital': 'DIG',
                            'donation': 'DON',
                            'service': 'SVC',
                        }
                        suffix = behavior_suffixes.get(variant.template_ams_product_behavior, 'VAR')
                        variant.effective_sku = f"{base_sku}-{suffix}{variant.id % 1000:03d}"
                    else:
                        variant.effective_sku = f"{base_sku}-V{variant.id % 1000:03d}"
                else:
                    variant.effective_sku = base_sku
            else:
                variant.effective_sku = ""

    effective_sku = fields.Char(
        string="Effective SKU",
        compute='_compute_effective_sku',
        store=True,
        help="The actual SKU being used (variant default_code or template-based)"
    )

    @api.depends('template_ams_product_behavior', 'template_grants_portal_access', 'template_donation_tax_deductible')
    def _compute_variant_behavior_summary(self):
        """Generate variant-specific behavior summary"""
        for variant in self:
            parts = []
            
            if variant.template_ams_product_behavior:
                behavior_dict = dict(variant._fields['template_ams_product_behavior'].selection)
                parts.append(behavior_dict.get(variant.template_ams_product_behavior))
            
            if variant.template_grants_portal_access:
                parts.append("Portal Access")
                
            if variant.template_donation_tax_deductible:
                parts.append("Tax Deductible")
            
            if variant.template_requires_membership:
                parts.append("Members Only")
                
            variant.variant_behavior_summary = " • ".join(parts) if parts else "Product"

    variant_behavior_summary = fields.Char(
        string="Variant Behavior Summary",
        compute='_compute_variant_behavior_summary',
        help="Summary of variant behavior inherited from template"
    )

    # ========================================================================
    # BUSINESS METHODS - ENHANCED DELEGATION TO TEMPLATE
    # ========================================================================

    def get_price_for_partner(self, partner):
        """
        Get appropriate price for partner - delegates to template with variant awareness.
        
        Args:
            partner (res.partner): Partner to check membership status
            
        Returns:
            float: Appropriate price for the partner
        """
        self.ensure_one()
        return self.product_tmpl_id.get_price_for_partner(partner)

    def can_be_purchased_by_partner(self, partner):
        """
        Enhanced purchase permission check with variant-specific availability.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            bool: True if partner can purchase this variant
        """
        self.ensure_one()
        
        # Check template-level permissions first
        if not self.product_tmpl_id.can_be_purchased_by_partner(partner):
            return False
            
        # Variant-specific availability checks
        if self.availability_status in [
            'out_of_stock', 'digital_missing', 'event_missing_template', 
            'certification_missing_content'
        ]:
            return False
            
        return True

    def get_digital_content_access(self, partner=None):
        """
        Get digital content access - delegates to template.
        
        Args:
            partner (res.partner, optional): Partner requesting access
            
        Returns:
            dict: Digital content access information
        """
        self.ensure_one()
        access_info = self.product_tmpl_id.get_digital_content_access(partner)
        
        # Add variant-specific information
        access_info.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
            'availability_status': self.availability_status,
        })
        
        return access_info

    def get_member_savings_amount(self, partner):
        """
        Calculate member savings for this variant.
        
        Args:
            partner (res.partner): Partner to calculate savings for
            
        Returns:
            float: Amount saved with member pricing
        """
        self.ensure_one()
        
        if not partner:
            return 0.0
            
        is_member = self.product_tmpl_id._check_partner_membership(partner)
        if not is_member:
            return 0.0
        
        member_price = self.get_price_for_partner(partner)
        regular_price = self.lst_price
        
        return max(0.0, regular_price - member_price)

    # ========================================================================
    # ENHANCED BUSINESS METHODS FOR SPECIFIC BEHAVIORS
    # ========================================================================

    def get_portal_access_details(self):
        """Get portal access configuration for this variant."""
        self.ensure_one()
        details = self.product_tmpl_id.get_portal_access_details()
        details.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
        })
        return details

    def get_donation_details(self):
        """Get donation tax information for this variant."""
        self.ensure_one()
        details = self.product_tmpl_id.get_donation_details()
        details.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
        })
        return details

    def get_event_integration_details(self):
        """Get event integration configuration for this variant."""
        self.ensure_one()
        details = self.product_tmpl_id.get_event_integration_details()
        details.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
        })
        return details

    def get_accounting_configuration(self):
        """Get accounting GL account configuration for this variant."""
        self.ensure_one()
        config = self.product_tmpl_id.get_accounting_configuration()
        config.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
        })
        return config

    # ========================================================================
    # VARIANT LIFECYCLE AND SYNCHRONIZATION
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced variant creation with AMS behavior awareness"""
        for vals in vals_list:
            # Generate variant-specific SKU if needed
            if not vals.get('default_code'):
                template_id = vals.get('product_tmpl_id')
                if template_id:
                    template = self.env['product.template'].browse(template_id)
                    if template.ams_product_behavior:
                        # Let the compute method handle behavior-aware SKU generation
                        pass

        variants = super().create(vals_list)
        
        # Log creation of AMS variants with behavior info
        for variant in variants:
            if variant.template_ams_product_behavior:
                behavior = variant.template_ams_product_behavior or 'unspecified'
                _logger.info(
                    f"Created AMS product variant: {variant.display_name} "
                    f"(SKU: {variant.effective_sku}, Behavior: {behavior})"
                )
        
        return variants

    def write(self, vals):
        """Enhanced write with AMS synchronization"""
        result = super().write(vals)
        
        # If variant-specific fields changed, log for audit
        ams_fields = ['default_code', 'variant_legacy_id', 'variant_notes']
        if any(field in vals for field in ams_fields):
            for variant in self:
                if variant.template_ams_product_behavior:
                    _logger.info(f"Updated AMS variant: {variant.display_name}")
        
        return result

    # ========================================================================
    # ENHANCED NAME AND DISPLAY
    # ========================================================================

    def name_get(self):
        """Enhanced name display for AMS variants with behavior indicators"""
        result = []
        for variant in self:
            name = super(ProductProduct, variant).name_get()[0][1]
            
            # Add SKU to products
            if variant.effective_sku:
                name = f"[{variant.effective_sku}] {name}"
                
            # Add behavior-specific indicators
            if variant.template_ams_product_behavior:
                behavior_indicators = {
                    'membership': '👤',
                    'event': '📅',
                    'publication': '📖',
                    'merchandise': '🛍️',
                    'certification': '🏆',
                    'digital': '💾',
                    'donation': '💝',
                    'service': '🔧',
                }
                indicator = behavior_indicators.get(variant.template_ams_product_behavior, '')
                if indicator:
                    name = f"{indicator} {name}"
                
            # Add membership requirement indicator
            if variant.template_requires_membership:
                name = f"{name} (Members Only)"
                
            # Add availability status for problematic variants
            if variant.availability_status in [
                'digital_missing', 'event_missing_template', 'certification_missing_content', 'out_of_stock'
            ]:
                status_dict = dict(variant._fields['availability_status'].selection)
                name = f"{name} - {status_dict[variant.availability_status]}"
                
            result.append((variant.id, name))
            
        return result

    # ========================================================================
    # ENHANCED SEARCH AND QUERY METHODS
    # ========================================================================

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search including effective SKU and behavior-aware search"""
        args = args or []
        
        if name:
            # Search in name, default_code, effective_sku, and behavior type
            domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('default_code', operator, name), 
                ('effective_sku', operator, name),
                ('template_ams_product_behavior', operator, name)
            ]
            args = domain + args
            
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def get_ams_variants_by_behavior_type(self, behavior_type=None):
        """
        Get AMS variants filtered by template behavior type.
        
        Args:
            behavior_type (str, optional): AMS behavior type to filter by
            
        Returns:
            recordset: AMS variants of the specified behavior type
        """
        domain = [('template_ams_product_behavior', '!=', False)]
        if behavior_type:
            domain.append(('template_ams_product_behavior', '=', behavior_type))
            
        return self.search(domain)

    @api.model
    def get_ams_variants_by_category_type(self, category_type=None):
        """Get AMS variants filtered by template category type"""
        domain = [('template_ams_product_behavior', '!=', False)]
        if category_type:
            domain.append(('product_tmpl_id.categ_id.ams_category_type', '=', category_type))
        return self.search(domain)

    @api.model
    def get_portal_access_variants(self):
        """Get variants that grant portal access"""
        return self.search([('template_grants_portal_access', '=', True)])

    @api.model
    def get_donation_variants(self):
        """Get all donation product variants"""
        return self.search([('template_donation_tax_deductible', '=', True)])

    @api.model
    def get_event_registration_variants(self):
        """Get variants that create event registrations"""
        return self.search([('template_creates_event_registration', '=', True)])

    @api.model
    def get_low_stock_ams_variants(self, threshold=0):
        """Get AMS variants with low stock levels"""
        return self.search([
            ('template_ams_product_behavior', '!=', False),
            ('type', '=', 'product'),
            ('qty_available', '<=', threshold)
        ])

    @api.model
    def get_variants_with_issues(self):
        """Get variants with configuration issues"""
        return self.search([
            ('availability_status', 'in', [
                'digital_missing', 'event_missing_template', 
                'certification_missing_content'
            ])
        ])

    @api.model
    def get_membership_required_variants(self):
        """Get variants that require membership to purchase"""
        return self.search([('template_requires_membership', '=', True)])

    # ========================================================================
    # ACTIONS FOR UI (ENHANCED)
    # ========================================================================

    def action_view_template(self):
        """Open the product template form with enhanced context"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Template'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.id,
            'target': 'current',
            'context': {
                'from_variant': True,
                'variant_id': self.id,
            }
        }

    def action_view_category(self):
        """Open the product category form"""
        self.ensure_one()
    
        if not self.product_tmpl_id.categ_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No category assigned to this product.',
                    'title': 'No Category',
                    'type': 'warning',
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Category'),
            'res_model': 'product.category',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.categ_id.id,
            'target': 'current',
            'context': {
                'from_product_variant': True,
                'variant_id': self.id,
            }
        }

    def action_test_variant_behavior(self):
        """Test variant behavior configuration (enhanced version)"""
        self.ensure_one()
        
        behavior_info = []
        
        if self.template_ams_product_behavior:
            behavior_dict = dict(self._fields['template_ams_product_behavior'].selection)
            behavior_info.append(f"Behavior: {behavior_dict[self.template_ams_product_behavior]}")
        
        behavior_info.append(f"Availability: {dict(self._fields['availability_status'].selection)[self.availability_status]}")
        behavior_info.append(f"SKU: {self.effective_sku or 'Not set'}")
        
        if self.template_grants_portal_access:
            portal = self.get_portal_access_details()
            behavior_info.append(f"Portal Groups: {', '.join(portal['portal_groups']) or 'Default'}")
        
        if self.template_donation_tax_deductible:
            behavior_info.append("Tax Deductible Donation")
        
        if self.template_creates_event_registration:
            event = self.get_event_integration_details()
            behavior_info.append(f"Event Template: {event['default_event'] or 'Missing'}")
        
        if self.template_requires_membership:
            behavior_info.append("Membership Required")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(behavior_info),
                'title': f'Variant Behavior Test: {self.display_name}',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_test_variant_access(self):
        """Test variant access with sample members"""
        self.ensure_one()
        
        # Find sample partners for testing
        test_partners = self.env['res.partner'].search([
            '|', ('is_member', '=', True), ('is_member', '=', False)
        ], limit=5)
        
        results = []
        for partner in test_partners:
            can_purchase = self.can_be_purchased_by_partner(partner)
            price = self.get_price_for_partner(partner)
            is_member = self.product_tmpl_id._check_partner_membership(partner)
            savings = self.get_member_savings_amount(partner)
            
            result_line = (
                f"{partner.name} ({'Member' if is_member else 'Non-member'}): "
                f"Can purchase: {can_purchase}, Price: ${price:.2f}"
            )
            if savings > 0:
                result_line += f", Saves: ${savings:.2f}"
            results.append(result_line)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(results) if results else 'No test partners found',
                'title': f'Access Test: {self.display_name}',
                'type': 'info',
                'sticky': True,
            }
        }

    # ========================================================================
    # REPORTING AND ANALYTICS HELPER METHODS
    # ========================================================================

    def get_comprehensive_variant_summary(self):
        """
        Get comprehensive summary information for this variant.
        
        Returns:
            dict: Complete variant summary data
        """
        self.ensure_one()
        
        base_summary = {
            'name': self.display_name,
            'sku': self.effective_sku,
            'behavior_type': self.template_ams_product_behavior,
            'category_type': self.template_ams_category_display,
            'availability_status': self.availability_status,
            'behavior_summary': self.variant_behavior_summary,
            'regular_price': self.lst_price,
            'member_price': self.template_member_price,
            'member_savings': self.template_member_savings,
            'template_id': self.product_tmpl_id.id,
            'category_id': self.product_tmpl_id.categ_id.id if self.product_tmpl_id.categ_id else None,
        }
        
        # Add behavior-specific details
        if self.template_grants_portal_access:
            base_summary['portal_details'] = self.get_portal_access_details()
            
        if self.template_donation_tax_deductible:
            base_summary['donation_details'] = self.get_donation_details()
            
        if self.template_creates_event_registration:
            base_summary['event_details'] = self.get_event_integration_details()
            
        if self.template_has_digital_content:
            base_summary['digital_details'] = self.get_digital_content_access()
        
        return base_summary

    def get_variant_issues(self):
        """
        Get list of configuration issues for this variant.
        
        Returns:
            list: List of issue descriptions
        """
        self.ensure_one()
        
        issues = []
        
        if self.availability_status == 'digital_missing':
            issues.append("Missing digital content (URL or file attachment required)")
            
        if self.availability_status == 'event_missing_template':
            issues.append("Missing event template for registration creation")
            
        if self.availability_status == 'certification_missing_content':
            issues.append("Missing digital certificate content")
            
        if self.availability_status == 'out_of_stock':
            issues.append("Out of stock - inventory replenishment needed")
            
        if not self.effective_sku:
            issues.append("Missing product SKU")
            
        if not self.template_ams_product_behavior:
            issues.append("Product missing behavior type selection")
        
        return issues