# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionCreateWizard(models.TransientModel):
    """
    Wizard for creating new AMS subscriptions with comprehensive configuration.
    Handles product selection, pricing, billing setup, and subscription preferences.
    """
    _name = 'ams.subscription.create.wizard'
    _description = 'Create AMS Subscription Wizard'

    # ========================================================================
    # CUSTOMER SELECTION
    # ========================================================================

    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        required=True,
        help="Customer for the new subscription"
    )

    partner_is_member = fields.Boolean(
        related='partner_id.is_member',
        string="Is Member",
        readonly=True
    )

    partner_membership_status = fields.Selection(
        related='partner_id.membership_status',
        string="Membership Status",
        readonly=True
    )

    partner_existing_subscriptions = fields.Integer(
        string="Existing Subscriptions",
        compute='_compute_partner_info',
        help="Number of existing active subscriptions"
    )

    # ========================================================================
    # PRODUCT SELECTION AND CONFIGURATION
    # ========================================================================

    product_id = fields.Many2one(
        'product.template',
        string="Subscription Product",
        required=True,
        domain=[('ams_product_behavior', '=', 'subscription')],
        help="Product to create subscription for"
    )

    product_variant_id = fields.Many2one(
        'product.product',
        string="Product Variant",
        compute='_compute_product_variant',
        store=True,
        help="Selected product variant"
    )

    product_content_type = fields.Selection(
        related='product_id.subscription_content_type',
        string="Content Type",
        readonly=True
    )

    product_access_level = fields.Selection(
        related='product_id.subscription_access_level',
        string="Access Level",
        readonly=True
    )

    product_auto_renewal = fields.Boolean(
        related='product_id.subscription_auto_renewal',
        string="Auto Renewal Available",
        readonly=True
    )

    # ========================================================================
    # BILLING AND PRICING CONFIGURATION
    # ========================================================================

    billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Billing Period",
        required=True,
        help="Billing cycle for this subscription"
    )

    subscription_start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.today,
        help="Subscription start date"
    )

    subscription_end_date = fields.Date(
        string="End Date",
        compute='_compute_subscription_dates',
        store=True,
        help="Calculated subscription end date"
    )

    billing_frequency_display = fields.Char(
        string="Billing Frequency",
        compute='_compute_billing_display',
        help="Human-readable billing frequency"
    )

    # ========================================================================
    # PRICING CALCULATION
    # ========================================================================

    base_price = fields.Monetary(
        string="Base Price",
        compute='_compute_pricing',
        store=True,
        help="Base subscription price"
    )

    member_discount_amount = fields.Monetary(
        string="Member Discount",
        compute='_compute_pricing',
        store=True,
        help="Member discount amount"
    )

    additional_discount_amount = fields.Monetary(
        string="Additional Discount",
        compute='_compute_pricing',
        store=True,
        help="Additional subscription discount"
    )

    setup_fee = fields.Monetary(
        string="Setup Fee",
        compute='_compute_pricing',
        store=True,
        help="One-time setup fee"
    )

    proration_adjustment = fields.Monetary(
        string="Proration Adjustment",
        compute='_compute_pricing',
        store=True,
        help="Adjustment for partial period"
    )

    subscription_price = fields.Monetary(
        string="Subscription Price",
        compute='_compute_pricing',
        store=True,
        help="Final subscription price per period"
    )

    initial_payment_amount = fields.Monetary(
        string="Initial Payment",
        compute='_compute_pricing',
        store=True,
        help="Total amount for initial payment"
    )

    annual_value = fields.Monetary(
        string="Annual Value",
        compute='_compute_pricing',
        store=True,
        help="Annualized subscription value"
    )

    is_prorated = fields.Boolean(
        string="Is Prorated",
        compute='_compute_pricing',
        store=True,
        help="Whether first billing is prorated"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ========================================================================
    # SUBSCRIPTION PREFERENCES
    # ========================================================================

    enable_auto_renewal = fields.Boolean(
        string="Enable Auto Renewal",
        default=True,
        help="Automatically renew subscription when it expires"
    )

    send_welcome_email = fields.Boolean(
        string="Send Welcome Email",
        default=True,
        help="Send subscription welcome email to customer"
    )

    grant_portal_access = fields.Boolean(
        string="Grant Portal Access",
        compute='_compute_portal_access',
        store=True,
        help="Whether this subscription grants portal access"
    )

    portal_groups_display = fields.Char(
        string="Portal Groups",
        compute='_compute_portal_access',
        help="Portal groups that will be granted"
    )

    # ========================================================================
    # SUBSCRIPTION TERMS AND CONDITIONS
    # ========================================================================

    subscription_terms = fields.Text(
        string="Terms and Conditions",
        compute='_compute_subscription_terms',
        help="Subscription terms and conditions"
    )

    customer_accepts_terms = fields.Boolean(
        string="Customer Accepts Terms",
        default=False,
        help="Customer has accepted subscription terms"
    )

    grace_period_days = fields.Integer(
        related='product_id.subscription_grace_period',
        string="Grace Period (Days)",
        readonly=True
    )

    cancellation_notice_days = fields.Integer(
        related='product_id.subscription_cancellation_notice',
        string="Cancellation Notice (Days)",
        readonly=True
    )

    # ========================================================================
    # VALIDATION AND STATUS
    # ========================================================================

    can_create_subscription = fields.Boolean(
        string="Can Create Subscription",
        compute='_compute_validation_status',
        help="Whether subscription can be created with current settings"
    )

    validation_messages = fields.Text(
        string="Validation Messages",
        compute='_compute_validation_status',
        help="Validation issues or warnings"
    )

    existing_subscription_warning = fields.Char(
        string="Existing Subscription Warning",
        compute='_compute_validation_status',
        help="Warning about existing subscriptions"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('partner_id')
    def _compute_partner_info(self):
        """Compute partner information."""
        for wizard in self:
            if wizard.partner_id:
                wizard.partner_existing_subscriptions = wizard.partner_id.active_subscription_count
            else:
                wizard.partner_existing_subscriptions = 0

    @api.depends('product_id')
    def _compute_product_variant(self):
        """Get product variant for selected product."""
        for wizard in self:
            if wizard.product_id:
                variants = wizard.product_id.product_variant_ids
                wizard.product_variant_id = variants[0] if variants else False
            else:
                wizard.product_variant_id = False

    @api.depends('billing_period_id', 'subscription_start_date')
    def _compute_subscription_dates(self):
        """Calculate subscription dates."""
        for wizard in self:
            if wizard.billing_period_id and wizard.subscription_start_date:
                wizard.subscription_end_date = wizard.billing_period_id.calculate_next_date(
                    wizard.subscription_start_date
                )
            else:
                wizard.subscription_end_date = False

    @api.depends('billing_period_id')
    def _compute_billing_display(self):
        """Generate billing frequency display."""
        for wizard in self:
            if wizard.billing_period_id:
                wizard.billing_frequency_display = f"Billed {wizard.billing_period_id.name}"
            else:
                wizard.billing_frequency_display = ""

    @api.depends('product_id', 'partner_id', 'subscription_start_date', 'billing_period_id')
    def _compute_pricing(self):
        """Calculate subscription pricing."""
        for wizard in self:
            if not wizard.product_id or not wizard.partner_id:
                wizard._reset_pricing_fields()
                continue

            try:
                # Get product pricing
                pricing = wizard.product_id.calculate_subscription_pricing_for_partner(
                    wizard.partner_id,
                    wizard.subscription_start_date
                )

                wizard.base_price = pricing.get('base_price', 0.0)
                wizard.member_discount_amount = pricing.get('member_savings', 0.0)
                wizard.setup_fee = pricing.get('setup_fee', 0.0)
                wizard.proration_adjustment = pricing.get('prorated_amount', 0.0) - pricing.get('base_price', 0.0)
                wizard.is_prorated = pricing.get('is_prorated', False)

                # Calculate additional subscription discount
                if wizard.product_id.subscription_member_discount_additional > 0 and wizard.partner_is_member:
                    additional_rate = wizard.product_id.subscription_member_discount_additional / 100
                    wizard.additional_discount_amount = wizard.base_price * additional_rate
                else:
                    wizard.additional_discount_amount = 0.0

                # Calculate final prices
                wizard.subscription_price = (
                    wizard.base_price - 
                    wizard.member_discount_amount - 
                    wizard.additional_discount_amount +
                    wizard.proration_adjustment
                )

                wizard.initial_payment_amount = wizard.subscription_price + wizard.setup_fee

                # Calculate annual value
                if wizard.billing_period_id:
                    periods_per_year = 365.25 / wizard.billing_period_id.total_days
                    wizard.annual_value = wizard.subscription_price * periods_per_year
                else:
                    wizard.annual_value = 0.0

            except Exception as e:
                _logger.error(f"Pricing calculation failed: {e}")
                wizard._reset_pricing_fields()

    def _reset_pricing_fields(self):
        """Reset all pricing fields to zero."""
        self.base_price = 0.0
        self.member_discount_amount = 0.0
        self.additional_discount_amount = 0.0
        self.setup_fee = 0.0
        self.proration_adjustment = 0.0
        self.subscription_price = 0.0
        self.initial_payment_amount = 0.0
        self.annual_value = 0.0
        self.is_prorated = False

    @api.depends('product_id')
    def _compute_portal_access(self):
        """Check portal access grants."""
        for wizard in self:
            if wizard.product_id:
                wizard.grant_portal_access = wizard.product_id.grants_portal_access
                
                if wizard.product_id.portal_group_ids:
                    wizard.portal_groups_display = ", ".join(
                        wizard.product_id.portal_group_ids.mapped('name')
                    )
                else:
                    wizard.portal_groups_display = "Default Portal Access"
            else:
                wizard.grant_portal_access = False
                wizard.portal_groups_display = ""

    @api.depends('product_id')
    def _compute_subscription_terms(self):
        """Generate subscription terms and conditions."""
        for wizard in self:
            if wizard.product_id:
                terms = []
                
                # Basic subscription terms
                terms.append("SUBSCRIPTION TERMS & CONDITIONS")
                terms.append("")
                terms.append(f"Product: {wizard.product_id.name}")
                
                if wizard.billing_period_id:
                    terms.append(f"Billing Cycle: {wizard.billing_period_id.name}")
                
                if wizard.product_id.subscription_auto_renewal:
                    terms.append(f"Auto Renewal: Available")
                
                if wizard.grace_period_days:
                    terms.append(f"Grace Period: {wizard.grace_period_days} days")
                
                if wizard.cancellation_notice_days:
                    terms.append(f"Cancellation Notice: {wizard.cancellation_notice_days} days required")
                
                # Access terms
                if wizard.product_id.subscription_access_level:
                    access_dict = dict(wizard.product_id._fields['subscription_access_level'].selection)
                    terms.append(f"Access Level: {access_dict.get(wizard.product_id.subscription_access_level)}")
                
                if wizard.product_id.subscription_concurrent_users:
                    if wizard.product_id.subscription_concurrent_users == 0:
                        terms.append("Users: Unlimited concurrent users")
                    else:
                        terms.append(f"Users: {wizard.product_id.subscription_concurrent_users} concurrent users maximum")
                
                # Content terms
                if wizard.product_id.subscription_download_limit:
                    if wizard.product_id.subscription_download_limit == 0:
                        terms.append("Downloads: Unlimited monthly downloads")
                    else:
                        terms.append(f"Downloads: {wizard.product_id.subscription_download_limit} per month maximum")
                
                wizard.subscription_terms = "\n".join(terms)
            else:
                wizard.subscription_terms = ""

    @api.depends('partner_id', 'product_id', 'product_variant_id', 'customer_accepts_terms', 'billing_period_id')
    def _compute_validation_status(self):
        """Validate subscription creation requirements."""
        for wizard in self:
            messages = []
            can_create = True
            existing_warning = ""

            # Check basic requirements
            if not wizard.partner_id:
                messages.append("Customer selection is required")
                can_create = False

            if not wizard.product_id:
                messages.append("Product selection is required")
                can_create = False

            if not wizard.billing_period_id:
                messages.append("Billing period selection is required")
                can_create = False

            if not wizard.customer_accepts_terms:
                messages.append("Customer must accept terms and conditions")
                can_create = False

            # Check product variant eligibility
            if wizard.partner_id and wizard.product_variant_id:
                eligibility = wizard.product_variant_id.can_create_subscription_for_partner(wizard.partner_id)
                
                if not eligibility.get('can_create'):
                    messages.append(f"Cannot create subscription: {eligibility.get('reason')}")
                    can_create = False

            # Check for existing subscriptions
            if wizard.partner_id and wizard.product_id:
                existing_subs = wizard.env['sale.subscription'].search([
                    ('partner_id', '=', wizard.partner_id.id),
                    ('template_id.product_id', '=', wizard.product_variant_id.id if wizard.product_variant_id else False),
                    ('stage_category', '=', 'progress')
                ])
                
                if existing_subs:
                    existing_warning = f"Customer already has {len(existing_subs)} active subscription(s) for this product"
                    messages.append("Warning: Duplicate subscription detected")

            # Member-specific validations
            if wizard.partner_id and wizard.product_id:
                if (wizard.product_id.requires_membership and 
                    not wizard.partner_is_member):
                    messages.append("This product requires active membership")
                    can_create = False

            wizard.can_create_subscription = can_create
            wizard.validation_messages = "\n".join(messages) if messages else "Ready to create subscription"
            wizard.existing_subscription_warning = existing_warning

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update fields when product changes."""
        if self.product_id:
            # Set default billing period from product
            if self.product_id.subscription_billing_period_id:
                self.billing_period_id = self.product_id.subscription_billing_period_id
            
            # Set auto renewal preference
            self.enable_auto_renewal = self.product_id.subscription_auto_renewal
            
            # Reset terms acceptance
            self.customer_accepts_terms = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update fields when customer changes."""
        if self.partner_id:
            # Set currency from customer
            if self.partner_id.property_product_pricelist:
                self.currency_id = self.partner_id.property_product_pricelist.currency_id
            
            # Reset terms acceptance
            self.customer_accepts_terms = False

    @api.onchange('billing_period_id', 'subscription_start_date')
    def _onchange_billing_configuration(self):
        """Recalculate when billing configuration changes."""
        # This will trigger _compute_pricing and _compute_subscription_dates
        pass

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @api.constrains('subscription_start_date')
    def _check_start_date(self):
        """Validate start date."""
        for wizard in self:
            if wizard.subscription_start_date:
                if wizard.subscription_start_date < fields.Date.today():
                    raise ValidationError(_("Subscription start date cannot be in the past"))

    @api.constrains('partner_id', 'product_id')
    def _check_subscription_eligibility(self):
        """Validate subscription eligibility."""
        for wizard in self:
            if wizard.partner_id and wizard.product_variant_id:
                eligibility = wizard.product_variant_id.can_create_subscription_for_partner(wizard.partner_id)
                if not eligibility.get('can_create'):
                    raise ValidationError(eligibility.get('reason', 'Cannot create subscription'))

    # ========================================================================
    # ACTION METHODS
    # ========================================================================

    def action_create_subscription(self):
        """Create the subscription with configured settings."""
        self.ensure_one()
        
        if not self.can_create_subscription:
            raise UserError(_("Cannot create subscription. Please resolve validation issues."))
        
        try:
            # Create subscription using partner method
            subscription = self.partner_id.create_subscription_from_product(
                product=self.product_id,
                start_date=self.subscription_start_date,
                billing_period_id=self.billing_period_id.id
            )
            
            # Update subscription preferences
            if not self.enable_auto_renewal:
                # Update product auto-renewal setting for this subscription
                # This might require custom logic depending on how auto-renewal is tracked
                pass
            
            # Grant portal access if configured
            if self.grant_portal_access and self.product_id.portal_group_ids:
                partner_users = self.partner_id.user_ids
                for user in partner_users:
                    user.write({
                        'groups_id': [(4, group.id) for group in self.product_id.portal_group_ids]
                    })
            
            # Send welcome email if requested
            if self.send_welcome_email:
                self.partner_id.send_subscription_welcome()
            
            # Log subscription creation
            self.partner_id.message_post(
                body=_("Subscription created: %s (Start: %s, Billing: %s)") % (
                    self.product_id.name,
                    self.subscription_start_date,
                    self.billing_period_id.name
                ),
                subject=_("New Subscription Created")
            )
            
            _logger.info(
                f"Created subscription {subscription.name} for {self.partner_id.name} "
                f"via wizard (Product: {self.product_id.name})"
            )
            
            # Return action to view created subscription
            return {
                'type': 'ir.actions.act_window',
                'name': _('Created Subscription'),
                'res_model': 'sale.subscription',
                'view_mode': 'form',
                'res_id': subscription.id,
                'target': 'current',
                'context': {'show_subscription_info': True},
            }
            
        except Exception as e:
            _logger.error(f"Failed to create subscription via wizard: {e}")
            raise UserError(_("Failed to create subscription: %s") % str(e))

    def action_preview_pricing(self):
        """Show pricing preview with detailed breakdown."""
        self.ensure_one()
        
        pricing_details = []
        
        if self.base_price:
            pricing_details.append(f"Base Price: ${self.base_price:.2f}")
        
        if self.member_discount_amount:
            pricing_details.append(f"Member Discount: -${self.member_discount_amount:.2f}")
        
        if self.additional_discount_amount:
            pricing_details.append(f"Subscription Discount: -${self.additional_discount_amount:.2f}")
        
        if self.setup_fee:
            pricing_details.append(f"Setup Fee: ${self.setup_fee:.2f}")
        
        if self.is_prorated:
            pricing_details.append(f"Proration Adjustment: ${self.proration_adjustment:.2f}")
        
        pricing_details.append("")
        pricing_details.append(f"Recurring Price: ${self.subscription_price:.2f} {self.billing_period_id.name if self.billing_period_id else ''}")
        pricing_details.append(f"Initial Payment: ${self.initial_payment_amount:.2f}")
        pricing_details.append(f"Annual Value: ${self.annual_value:.2f}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': '\n'.join(pricing_details),
                'title': f'Pricing Preview - {self.product_id.name}',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_validate_configuration(self):
        """Validate current configuration and show results."""
        self.ensure_one()
        
        # Force recomputation
        self._compute_validation_status()
        
        if self.can_create_subscription:
            message = "✅ Configuration Valid\n\nSubscription is ready to be created."
        else:
            message = f"❌ Configuration Issues\n\n{self.validation_messages}"
        
        if self.existing_subscription_warning:
            message += f"\n\n⚠️ {self.existing_subscription_warning}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'title': 'Configuration Validation',
                'type': 'success' if self.can_create_subscription else 'warning',
                'sticky': True,
            }
        }

    def action_accept_terms(self):
        """Mark terms as accepted by customer."""
        self.ensure_one()
        self.customer_accepts_terms = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Terms and conditions accepted.',
                'title': 'Terms Accepted',
                'type': 'success',
            }
        }

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_subscription_summary(self):
        """Get summary of subscription configuration."""
        self.ensure_one()
        
        return {
            'customer': self.partner_id.name,
            'product': self.product_id.name,
            'content_type': dict(self.product_id._fields['subscription_content_type'].selection).get(
                self.product_content_type) if self.product_content_type else None,
            'access_level': dict(self.product_id._fields['subscription_access_level'].selection).get(
                self.product_access_level) if self.product_access_level else None,
            'billing_period': self.billing_period_id.name,
            'start_date': self.subscription_start_date,
            'end_date': self.subscription_end_date,
            'pricing': {
                'base_price': self.base_price,
                'member_discount': self.member_discount_amount,
                'additional_discount': self.additional_discount_amount,
                'setup_fee': self.setup_fee,
                'subscription_price': self.subscription_price,
                'initial_payment': self.initial_payment_amount,
                'annual_value': self.annual_value,
                'is_prorated': self.is_prorated,
            },
            'preferences': {
                'auto_renewal': self.enable_auto_renewal,
                'welcome_email': self.send_welcome_email,
                'portal_access': self.grant_portal_access,
            },
            'validation': {
                'can_create': self.can_create_subscription,
                'terms_accepted': self.customer_accepts_terms,
                'messages': self.validation_messages,
                'warnings': self.existing_subscription_warning,
            }
        }

    @api.model
    def default_get(self, fields):
        """Set default values based on context."""
        result = super().default_get(fields)
        
        # Set partner from context
        if 'partner_id' not in result and self.env.context.get('default_partner_id'):
            result['partner_id'] = self.env.context['default_partner_id']
        
        # Set product from context
        if 'product_id' not in result and self.env.context.get('default_product_id'):
            result['product_id'] = self.env.context['default_product_id']
        
        return result

    # ========================================================================
    # QUICK ACTION METHODS
    # ========================================================================

    def action_quick_create_annual(self):
        """Quick create with annual billing."""
        self.ensure_one()
        
        annual_period = self.env['ams.billing.period'].search([
            ('name', 'ilike', 'annual')
        ], limit=1)
        
        if annual_period:
            self.billing_period_id = annual_period
            return self.action_create_subscription()
        else:
            raise UserError(_("No annual billing period found"))

    def action_quick_create_monthly(self):
        """Quick create with monthly billing."""
        self.ensure_one()
        
        monthly_period = self.env['ams.billing.period'].search([
            ('name', 'ilike', 'monthly')
        ], limit=1)
        
        if monthly_period:
            self.billing_period_id = monthly_period
            return self.action_create_subscription()
        else:
            raise UserError(_("No monthly billing period found"))