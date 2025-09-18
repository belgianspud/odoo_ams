# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    """
    Enhanced AMS product variant with subscription functionality inheritance.
    Provides variant-level subscription management and status tracking.
    """
    _inherit = 'product.product'

    # ========================================================================
    # TEMPLATE SUBSCRIPTION FIELD REFERENCES (for performance and access)
    # ========================================================================

    template_is_subscription_product = fields.Boolean(
        related='product_tmpl_id.is_subscription_product',
        string="Template Is Subscription",
        readonly=True,
        store=True
    )

    template_subscription_billing_period_id = fields.Many2one(
        related='product_tmpl_id.subscription_billing_period_id',
        string="Template Billing Period",
        readonly=True,
        store=True
    )

    template_subscription_term = fields.Integer(
        related='product_tmpl_id.subscription_term',
        string="Template Subscription Term",
        readonly=True,
        store=True
    )

    template_subscription_term_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string="Template Term Type",
       related='product_tmpl_id.subscription_term_type',
       readonly=True,
       store=True)

    template_subscription_auto_renewal = fields.Boolean(
        related='product_tmpl_id.subscription_auto_renewal',
        string="Template Auto Renewal",
        readonly=True,
        store=True
    )

    template_subscription_grace_period = fields.Integer(
        related='product_tmpl_id.subscription_grace_period',
        string="Template Grace Period",
        readonly=True,
        store=True
    )

    template_subscription_content_type = fields.Selection([
        ('digital_access', 'Digital Platform Access'),
        ('publication', 'Publication/Journal'),
        ('research', 'Research & Reports'),
        ('software', 'Software License'),
        ('course', 'Educational Content'),
        ('premium', 'Premium Member Benefits'),
        ('committee', 'Committee/Group Access'),
        ('mixed', 'Mixed Content & Services'),
    ], string="Template Content Type",
       related='product_tmpl_id.subscription_content_type',
       readonly=True,
       store=True)

    template_subscription_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access'),
        ('enterprise', 'Enterprise Access'),
    ], string="Template Access Level",
       related='product_tmpl_id.subscription_access_level',
       readonly=True,
       store=True)

    template_subscription_concurrent_users = fields.Integer(
        related='product_tmpl_id.subscription_concurrent_users',
        string="Template Concurrent Users",
        readonly=True,
        store=True
    )

    template_subscription_prorated_billing = fields.Boolean(
        related='product_tmpl_id.subscription_prorated_billing',
        string="Template Prorated Billing",
        readonly=True,
        store=True
    )

    template_subscription_setup_fee = fields.Monetary(
        related='product_tmpl_id.subscription_setup_fee',
        string="Template Setup Fee",
        readonly=True
    )

    template_subscription_annual_value = fields.Monetary(
        related='product_tmpl_id.subscription_annual_value',
        string="Template Annual Value",
        readonly=True
    )

    template_subscription_effective_member_price = fields.Monetary(
        related='product_tmpl_id.subscription_effective_member_price',
        string="Template Effective Member Price",
        readonly=True
    )

    template_subscription_summary = fields.Char(
        related='product_tmpl_id.subscription_summary',
        string="Template Subscription Summary",
        readonly=True
    )

    # ========================================================================
    # VARIANT-SPECIFIC SUBSCRIPTION FIELDS
    # ========================================================================

    variant_subscription_notes = fields.Text(
        string="Variant Subscription Notes",
        help="Variant-specific subscription configuration notes"
    )

    variant_subscription_external_id = fields.Char(
        string="External Subscription ID",
        help="ID from external subscription management system"
    )

    # ========================================================================
    # COMPUTED SUBSCRIPTION STATUS FIELDS
    # ========================================================================

    @api.depends('template_is_subscription_product', 'template_subscription_billing_period_id',
                 'template_subscription_content_type', 'active')
    def _compute_subscription_availability_status(self):
        """Calculate subscription-specific availability status."""
        for variant in self:
            if not variant.template_is_subscription_product:
                variant.subscription_availability_status = 'not_subscription'
            elif not variant.active:
                variant.subscription_availability_status = 'inactive'
            elif not variant.template_subscription_billing_period_id:
                variant.subscription_availability_status = 'missing_billing_period'
            elif (variant.template_subscription_content_type in ['digital_access', 'software'] and 
                  not variant.template_has_digital_content):
                variant.subscription_availability_status = 'missing_digital_content'
            elif variant.template_subscription_content_type == 'publication' and not variant.template_has_digital_content:
                variant.subscription_availability_status = 'missing_publication_content'
            else:
                variant.subscription_availability_status = 'subscription_ready'

    subscription_availability_status = fields.Selection([
        ('not_subscription', 'Not a Subscription'),
        ('inactive', 'Inactive Subscription'),
        ('missing_billing_period', 'Missing Billing Period'),
        ('missing_digital_content', 'Missing Digital Content'),
        ('missing_publication_content', 'Missing Publication Content'),
        ('subscription_ready', 'Ready for Subscription'),
    ], string="Subscription Status", 
       compute='_compute_subscription_availability_status', 
       store=True,
       help="Subscription readiness and configuration status")

    @api.depends('template_subscription_term', 'template_subscription_term_type',
                 'template_subscription_billing_period_id')
    def _compute_variant_subscription_display(self):
        """Generate variant subscription display information."""
        for variant in self:
            if not variant.template_is_subscription_product:
                variant.variant_subscription_display = ""
                continue

            parts = []
            
            # Billing period or term
            if variant.template_subscription_billing_period_id:
                parts.append(variant.template_subscription_billing_period_id.name)
            elif variant.template_subscription_term and variant.template_subscription_term_type:
                term_unit = variant.template_subscription_term_type
                if variant.template_subscription_term == 1:
                    term_unit = term_unit.rstrip('s')
                parts.append(f"{variant.template_subscription_term} {term_unit}")
            
            # Content type
            if variant.template_subscription_content_type:
                content_dict = dict(variant._fields['template_subscription_content_type'].selection)
                parts.append(content_dict.get(variant.template_subscription_content_type, ''))
            
            # Access level
            if variant.template_subscription_access_level:
                access_dict = dict(variant._fields['template_subscription_access_level'].selection)
                access_level = access_dict.get(variant.template_subscription_access_level, '')
                if access_level != 'Standard Access':  # Only show if not standard
                    parts.append(access_level)
            
            # Auto renewal indicator
            if variant.template_subscription_auto_renewal:
                parts.append("Auto-renew")

            variant.variant_subscription_display = " • ".join(parts) if parts else "Subscription"

    variant_subscription_display = fields.Char(
        string="Variant Subscription Display",
        compute='_compute_variant_subscription_display',
        help="Formatted subscription information for display"
    )

    @api.depends('template_subscription_concurrent_users', 'template_subscription_content_type')
    def _compute_subscription_usage_summary(self):
        """Generate usage limits summary for subscription."""
        for variant in self:
            if not variant.template_is_subscription_product:
                variant.subscription_usage_summary = ""
                continue

            parts = []
            
            # User limits
            if variant.template_subscription_concurrent_users == 0:
                parts.append("Unlimited Users")
            elif variant.template_subscription_concurrent_users == 1:
                parts.append("Single User")
            else:
                parts.append(f"{variant.template_subscription_concurrent_users} Concurrent Users")
            
            # Download limits (if applicable for content type)
            if variant.template_subscription_content_type in ['publication', 'research', 'digital_access']:
                if variant.product_tmpl_id.subscription_download_limit == 0:
                    parts.append("Unlimited Downloads")
                elif variant.product_tmpl_id.subscription_download_limit > 0:
                    parts.append(f"{variant.product_tmpl_id.subscription_download_limit}/month")

            variant.subscription_usage_summary = " • ".join(parts)

    subscription_usage_summary = fields.Char(
        string="Usage Summary",
        compute='_compute_subscription_usage_summary',
        help="Summary of subscription usage limits"
    )

    # ========================================================================
    # BUSINESS METHODS - SUBSCRIPTION VARIANT MANAGEMENT
    # ========================================================================

    def get_subscription_details(self):
        """
        Get subscription details for this variant (delegates to template).
        
        Returns:
            dict: Subscription configuration with variant-specific info
        """
        self.ensure_one()
        
        details = self.product_tmpl_id.get_subscription_details()
        
        # Add variant-specific information
        details.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
            'variant_subscription_display': self.variant_subscription_display,
            'subscription_availability_status': self.subscription_availability_status,
            'usage_summary': self.subscription_usage_summary,
            'variant_notes': self.variant_subscription_notes,
            'external_id': self.variant_subscription_external_id,
        })
        
        return details

    def calculate_subscription_pricing_for_partner(self, partner, start_date=None):
        """
        Calculate subscription pricing for partner (delegates to template).
        
        Args:
            partner (res.partner): Partner to calculate pricing for
            start_date (date, optional): Subscription start date
            
        Returns:
            dict: Pricing breakdown with variant info
        """
        self.ensure_one()
        
        pricing = self.product_tmpl_id.calculate_subscription_pricing_for_partner(partner, start_date)
        
        # Add variant-specific information
        pricing.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
            'variant_display': self.variant_subscription_display,
        })
        
        return pricing

    def get_subscription_access_details(self):
        """
        Get subscription access details (delegates to template).
        
        Returns:
            dict: Access configuration with variant info
        """
        self.ensure_one()
        
        access = self.product_tmpl_id.get_subscription_access_details()
        
        # Add variant-specific information
        access.update({
            'variant_id': self.id,
            'variant_sku': self.effective_sku,
            'usage_summary': self.subscription_usage_summary,
            'availability_status': self.subscription_availability_status,
        })
        
        return access

    def can_create_subscription_for_partner(self, partner):
        """
        Check if subscription can be created for partner with this variant.
        
        Args:
            partner (res.partner): Partner to check
            
        Returns:
            dict: Eligibility status with details
        """
        self.ensure_one()
        
        if not self.template_is_subscription_product:
            return {
                'can_create': False,
                'reason': 'Not a subscription product',
                'status': 'invalid_product'
            }
        
        if self.subscription_availability_status != 'subscription_ready':
            return {
                'can_create': False,
                'reason': dict(self._fields['subscription_availability_status'].selection)[self.subscription_availability_status],
                'status': self.subscription_availability_status
            }
        
        # Check if partner can purchase this product
        if not self.can_be_purchased_by_partner(partner):
            return {
                'can_create': False,
                'reason': 'Partner cannot purchase this product',
                'status': 'purchase_restricted'
            }
        
        # Check for existing active subscriptions
        if self.env['sale.subscription'].search_count([
            ('partner_id', '=', partner.id),
            ('template_id.product_id', '=', self.id),
            ('stage_category', '=', 'progress')
        ]):
            return {
                'can_create': False,
                'reason': 'Partner already has active subscription for this product',
                'status': 'existing_subscription'
            }
        
        return {
            'can_create': True,
            'reason': 'Ready to create subscription',
            'status': 'ready'
        }

    def get_next_billing_date(self, start_date=None):
        """Get next billing date for subscription (delegates to template)."""
        self.ensure_one()
        return self.product_tmpl_id.get_subscription_next_billing_date(start_date)

    # ========================================================================
    # SUBSCRIPTION VARIANT LIFECYCLE
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced variant creation with subscription awareness."""
        variants = super().create(vals_list)
        
        # Log creation of subscription variants
        for variant in variants:
            if variant.template_is_subscription_product:
                _logger.info(
                    f"Created subscription variant: {variant.display_name} "
                    f"(SKU: {variant.effective_sku}, "
                    f"Billing: {variant.template_subscription_billing_period_id.name if variant.template_subscription_billing_period_id else 'Custom'})"
                )
                
                # Validate subscription configuration
                if variant.subscription_availability_status != 'subscription_ready':
                    _logger.warning(
                        f"Subscription variant {variant.display_name} has configuration issues: "
                        f"{variant.subscription_availability_status}"
                    )
        
        return variants

    def write(self, vals):
        """Enhanced write with subscription synchronization."""
        result = super().write(vals)
        
        # Log subscription variant updates
        subscription_fields = [
            'variant_subscription_notes', 
            'variant_subscription_external_id'
        ]
        if any(field in vals for field in subscription_fields):
            for variant in self:
                if variant.template_is_subscription_product:
                    _logger.info(f"Updated subscription variant: {variant.display_name}")
        
        return result

    # ========================================================================
    # ENHANCED NAME AND DISPLAY FOR SUBSCRIPTIONS
    # ========================================================================

    def name_get(self):
        """Enhanced name display for subscription variants."""
        result = super().name_get()
        
        # Add subscription indicators if context requests it
        if self.env.context.get('show_subscription_info'):
            new_result = []
            for variant_id, name in result:
                variant = self.browse(variant_id)
                if variant.template_is_subscription_product:
                    # Add subscription emoji and billing info
                    billing_info = ""
                    if variant.template_subscription_billing_period_id:
                        billing_info = f" ({variant.template_subscription_billing_period_id.name})"
                    elif variant.template_subscription_term and variant.template_subscription_term_type:
                        billing_info = f" ({variant.template_subscription_term} {variant.template_subscription_term_type})"
                    
                    name = f"🔄 {name}{billing_info}"
                    
                    # Add status indicator for problematic subscriptions
                    if variant.subscription_availability_status not in ['subscription_ready', 'not_subscription']:
                        name += f" - {dict(variant._fields['subscription_availability_status'].selection)[variant.subscription_availability_status]}"
                
                new_result.append((variant_id, name))
            return new_result
        
        return result

    # ========================================================================
    # SUBSCRIPTION VARIANT QUERY METHODS
    # ========================================================================

    @api.model
    def get_subscription_variants_by_content_type(self, content_type=None):
        """Get subscription variants filtered by content type."""
        domain = [('template_is_subscription_product', '=', True)]
        if content_type:
            domain.append(('template_subscription_content_type', '=', content_type))
        return self.search(domain)

    @api.model
    def get_subscription_variants_by_access_level(self, access_level=None):
        """Get subscription variants filtered by access level."""
        domain = [('template_is_subscription_product', '=', True)]
        if access_level:
            domain.append(('template_subscription_access_level', '=', access_level))
        return self.search(domain)

    @api.model
    def get_auto_renewal_subscription_variants(self):
        """Get subscription variants with auto-renewal enabled."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            ('template_subscription_auto_renewal', '=', True)
        ])

    @api.model
    def get_prorated_subscription_variants(self):
        """Get subscription variants with prorated billing."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            ('template_subscription_prorated_billing', '=', True)
        ])

    @api.model
    def get_subscription_variants_by_billing_period(self, billing_period_id):
        """Get subscription variants using specific billing period."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            ('template_subscription_billing_period_id', '=', billing_period_id)
        ])

    @api.model
    def get_ready_subscription_variants(self):
        """Get subscription variants ready for subscription creation."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            ('subscription_availability_status', '=', 'subscription_ready')
        ])

    @api.model
    def get_subscription_variants_with_issues(self):
        """Get subscription variants with configuration issues."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            ('subscription_availability_status', 'in', [
                'missing_billing_period',
                'missing_digital_content', 
                'missing_publication_content'
            ])
        ])

    @api.model
    def get_multi_user_subscription_variants(self):
        """Get subscription variants supporting multiple concurrent users."""
        return self.search([
            ('template_is_subscription_product', '=', True),
            '|',
            ('template_subscription_concurrent_users', '=', 0),  # Unlimited
            ('template_subscription_concurrent_users', '>', 1)   # Multiple users
        ])

    @api.model
    def get_subscription_variants_by_annual_value(self, min_value=0, max_value=None):
        """Get subscription variants filtered by annual value range."""
        domain = [
            ('template_is_subscription_product', '=', True),
            ('template_subscription_annual_value', '>=', min_value)
        ]
        if max_value is not None:
            domain.append(('template_subscription_annual_value', '<=', max_value))
        return self.search(domain)

    # ========================================================================
    # ACTIONS FOR SUBSCRIPTION VARIANT MANAGEMENT
    # ========================================================================

    def action_view_subscription_template(self):
        """Open the subscription product template with subscription context."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Product Template'),
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.id,
            'target': 'current',
            'context': {
                'from_subscription_variant': True,
                'variant_id': self.id,
                'show_subscription_info': True,
            }
        }

    def action_test_subscription_configuration(self):
        """Test subscription configuration and display results."""
        self.ensure_one()
        
        if not self.template_is_subscription_product:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'This is not a subscription product variant.',
                    'title': 'Not a Subscription',
                    'type': 'warning',
                }
            }
        
        details = self.get_subscription_details()
        access = self.get_subscription_access_details()
        
        config_info = [
            f"Subscription Type: {details.get('term_display', 'Not configured')}",
            f"Billing: {details.get('billing_frequency', 'Not configured')}",
            f"Content: {access.get('content_type_display', 'Not specified')}",
            f"Access Level: {access.get('access_level_display', 'Standard')}",
            f"Users: {access.get('concurrent_users', 1)} concurrent" if access.get('concurrent_users', 1) > 0 else "Users: Unlimited",
            f"Auto Renewal: {'Yes' if details.get('auto_renewal') else 'No'}",
            f"Prorated: {'Yes' if details.get('prorated_billing') else 'No'}",
            f"Setup Fee: ${details.get('setup_fee', 0):.2f}" if details.get('setup_fee', 0) > 0 else "No Setup Fee",
            f"Annual Value: ${details.get('annual_value', 0):.2f}",
            f"Status: {dict(self._fields['subscription_availability_status'].selection)[self.subscription_availability_status]}",
        ]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(config_info),
                'title': f'Subscription Configuration: {self.display_name}',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_test_subscription_pricing(self):
        """Test subscription pricing with sample partners."""
        self.ensure_one()
        
        if not self.template_is_subscription_product:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'This is not a subscription product variant.',
                    'title': 'Not a Subscription',
                    'type': 'warning',
                }
            }
        
        # Find sample partners for testing
        test_partners = self.env['res.partner'].search([
            '|', ('is_member', '=', True), ('is_member', '=', False)
        ], limit=5)
        
        pricing_results = []
        for partner in test_partners:
            pricing = self.calculate_subscription_pricing_for_partner(partner)
            is_member = pricing.get('is_member', False)
            base_price = pricing.get('base_price', 0)
            setup_fee = pricing.get('setup_fee', 0)
            total = pricing.get('total_initial_amount', 0)
            savings = pricing.get('member_savings', 0)
            
            result_line = (
                f"{partner.name} ({'Member' if is_member else 'Non-member'}): "
                f"${base_price:.2f}"
            )
            
            if setup_fee > 0:
                result_line += f" + ${setup_fee:.2f} setup"
            
            if savings > 0:
                result_line += f" (Saves ${savings:.2f})"
                
            result_line += f" = ${total:.2f} initial"
            
            pricing_results.append(result_line)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(pricing_results) if pricing_results else 'No test partners found',
                'title': f'Subscription Pricing Test: {self.display_name}',
                'type': 'info',
                'sticky': True,
            }
        }

    # ========================================================================
    # SUBSCRIPTION VARIANT SUMMARY METHODS
    # ========================================================================

    def get_comprehensive_subscription_summary(self):
        """
        Get comprehensive subscription summary for this variant.
        
        Returns:
            dict: Complete subscription variant summary
        """
        self.ensure_one()
        
        base_summary = self.get_comprehensive_variant_summary()
        
        if not self.template_is_subscription_product:
            return base_summary
        
        # Add subscription-specific details
        subscription_summary = {
            'subscription_details': self.get_subscription_details(),
            'access_details': self.get_subscription_access_details(),
            'availability_status': self.subscription_availability_status,
            'subscription_display': self.variant_subscription_display,
            'usage_summary': self.subscription_usage_summary,
            'annual_value': self.template_subscription_annual_value,
            'effective_member_price': self.template_subscription_effective_member_price,
            'setup_fee': self.template_subscription_setup_fee,
        }
        
        base_summary.update(subscription_summary)
        return base_summary

    def get_subscription_variant_issues(self):
        """
        Get list of subscription configuration issues for this variant.
        
        Returns:
            list: List of issue descriptions
        """
        self.ensure_one()
        
        issues = self.get_variant_issues()  # Get base variant issues
        
        if not self.template_is_subscription_product:
            return issues
        
        # Add subscription-specific issue checks
        if self.subscription_availability_status == 'missing_billing_period':
            issues.append("Missing billing period configuration - required for subscription billing")
        
        if self.subscription_availability_status == 'missing_digital_content':
            issues.append("Missing digital content for digital access subscription")
        
        if self.subscription_availability_status == 'missing_publication_content':
            issues.append("Missing publication content for publication subscription")
        
        if (self.template_subscription_content_type == 'software' and 
            not self.template_has_digital_content):
            issues.append("Software subscription missing digital content or license delivery method")
        
        if (self.template_subscription_auto_renewal and 
            not self.product_tmpl_id.subscription_renewal_reminder_template_id):
            issues.append("Auto-renewal enabled but no renewal reminder email template configured")
        
        if (self.template_subscription_setup_fee > 0 and 
            not self.product_tmpl_id.subscription_deferred_revenue_account_id):
            issues.append("Setup fee configured but no deferred revenue account for proper accounting")
        
        return issues