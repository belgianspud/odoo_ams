# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Extended AMS product template with comprehensive subscription management.
    Adds subscription behavior and advanced subscription lifecycle management.
    """
    _inherit = 'product.template'

    # ========================================================================
    # SUBSCRIPTION BEHAVIOR EXTENSION
    # ========================================================================

    ams_product_behavior = fields.Selection(
        selection_add=[('subscription', 'Subscription Product')],
        ondelete={'subscription': 'set default'}
    )

    # ========================================================================
    # SUBSCRIPTION-SPECIFIC FIELDS
    # ========================================================================

    is_subscription_product = fields.Boolean(
        string="Subscription Product",
        default=False,
        help="Product with recurring billing cycles and subscription management"
    )

    subscription_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Billing Period",
        help="Standard billing period for this subscription"
    )

    subscription_term = fields.Integer(
        string="Subscription Term",
        default=12,
        help="Duration of subscription in specified time units"
    )

    subscription_term_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'), 
        ('months', 'Months'),
        ('years', 'Years'),
    ], string="Term Type", 
       default='months',
       help="Time unit for subscription term duration")

    subscription_auto_renewal = fields.Boolean(
        string="Auto Renewal",
        default=True,
        help="Automatically renew subscriptions when they expire"
    )

    subscription_grace_period = fields.Integer(
        string="Grace Period (Days)",
        default=30,
        help="Days to maintain access after subscription expires"
    )

    subscription_min_term = fields.Integer(
        string="Minimum Term",
        default=1,
        help="Minimum subscription duration (prevents early cancellation)"
    )

    subscription_cancellation_notice = fields.Integer(
        string="Cancellation Notice (Days)",
        default=30,
        help="Required notice period for subscription cancellation"
    )

    subscription_prorated_billing = fields.Boolean(
        string="Prorated Billing",
        default=True,
        help="Enable prorated billing for mid-cycle starts/changes"
    )

    # ========================================================================
    # SUBSCRIPTION CONTENT & ACCESS
    # ========================================================================

    subscription_content_type = fields.Selection([
        ('digital_access', 'Digital Platform Access'),
        ('publication', 'Publication/Journal'),
        ('research', 'Research & Reports'),
        ('software', 'Software License'),
        ('course', 'Educational Content'),
        ('premium', 'Premium Member Benefits'),
        ('committee', 'Committee/Group Access'),
        ('mixed', 'Mixed Content & Services'),
    ], string="Content Type",
       help="Type of content or service provided by subscription")

    subscription_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access'),
        ('enterprise', 'Enterprise Access'),
    ], string="Access Level",
       default='standard',
       help="Level of access granted by this subscription")

    subscription_concurrent_users = fields.Integer(
        string="Concurrent Users",
        default=1,
        help="Number of simultaneous users allowed (0 = unlimited)"
    )

    subscription_download_limit = fields.Integer(
        string="Monthly Download Limit",
        default=0,
        help="Monthly download limit (0 = unlimited)"
    )

    # ========================================================================
    # SUBSCRIPTION PRICING & ACCOUNTING
    # ========================================================================

    subscription_setup_fee = fields.Monetary(
        string="Setup Fee",
        default=0.0,
        help="One-time setup fee charged at subscription start"
    )

    subscription_cancellation_fee = fields.Monetary(
        string="Cancellation Fee", 
        default=0.0,
        help="Fee charged for early subscription cancellation"
    )

    subscription_member_discount_additional = fields.Float(
        string="Additional Member Discount %",
        default=0.0,
        help="Additional discount for members beyond category discount"
    )

    subscription_deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string="Deferred Revenue Account",
        domain=[('account_type', '=', 'liability_current')],
        help="Account for deferred subscription revenue recognition"
    )

    subscription_revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('monthly', 'Monthly Recognition'),
        ('service_delivery', 'Service Delivery Based'),
    ], string="Revenue Recognition",
       default='monthly',
       help="Method for recognizing subscription revenue")

    # ========================================================================
    # SUBSCRIPTION WORKFLOW & AUTOMATION
    # ========================================================================

    subscription_renewal_reminder_days = fields.Char(
        string="Renewal Reminder Days",
        default="30,15,7",
        help="Days before expiry to send renewal reminders (comma-separated)"
    )

    subscription_welcome_template_id = fields.Many2one(
        'mail.template',
        string="Welcome Email Template",
        domain=[('model', '=', 'sale.subscription')],
        help="Email template sent when subscription is activated"
    )

    subscription_renewal_reminder_template_id = fields.Many2one(
        'mail.template',
        string="Renewal Reminder Template",
        domain=[('model', '=', 'sale.subscription')],
        help="Email template for renewal reminders"
    )

    subscription_cancellation_template_id = fields.Many2one(
        'mail.template',
        string="Cancellation Confirmation Template",
        domain=[('model', '=', 'sale.subscription')],
        help="Email template sent when subscription is cancelled"
    )

    # ========================================================================
    # COMPUTED SUBSCRIPTION FIELDS
    # ========================================================================

    subscription_summary = fields.Char(
        string="Subscription Summary",
        compute='_compute_subscription_summary',
        store=True,
        help="Human-readable subscription configuration summary"
    )

    subscription_annual_value = fields.Monetary(
        string="Annual Subscription Value",
        compute='_compute_subscription_annual_value',
        store=True,
        help="Annualized value of this subscription"
    )

    subscription_effective_member_price = fields.Monetary(
        string="Effective Member Price",
        compute='_compute_subscription_effective_member_price',
        store=True,
        help="Member price including additional subscription discount"
    )

    subscription_billing_frequency = fields.Char(
        string="Billing Frequency",
        compute='_compute_subscription_billing_frequency',
        help="Human-readable billing frequency description"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('subscription_term', 'subscription_term_type', 'subscription_billing_period_id')
    def _compute_subscription_summary(self):
        """Generate subscription configuration summary."""
        for product in self:
            if not product.is_subscription_product:
                product.subscription_summary = ""
                continue

            parts = []
            
            # Term information
            if product.subscription_term and product.subscription_term_type:
                term_display = f"{product.subscription_term} {product.subscription_term_type}"
                if product.subscription_term == 1:
                    term_display = term_display.rstrip('s')  # Remove plural
                parts.append(f"Term: {term_display}")

            # Billing period
            if product.subscription_billing_period_id:
                parts.append(f"Billed: {product.subscription_billing_period_id.name}")
            
            # Auto renewal
            if product.subscription_auto_renewal:
                parts.append("Auto-renewal")
            
            # Access level
            if product.subscription_access_level:
                access_dict = dict(product._fields['subscription_access_level'].selection)
                parts.append(f"{access_dict[product.subscription_access_level]} Access")

            product.subscription_summary = " • ".join(parts) if parts else "Subscription Product"

    @api.depends('list_price', 'subscription_term', 'subscription_term_type')
    def _compute_subscription_annual_value(self):
        """Calculate annualized subscription value."""
        for product in self:
            if not product.is_subscription_product:
                product.subscription_annual_value = 0.0
                continue

            if not product.subscription_term or not product.subscription_term_type:
                product.subscription_annual_value = 0.0
                continue

            # Calculate periods per year
            periods_per_year = 1
            if product.subscription_term_type == 'days':
                periods_per_year = 365.25 / product.subscription_term
            elif product.subscription_term_type == 'weeks':
                periods_per_year = 52.18 / product.subscription_term  # 365.25 / 7
            elif product.subscription_term_type == 'months':
                periods_per_year = 12 / product.subscription_term
            elif product.subscription_term_type == 'years':
                periods_per_year = 1 / product.subscription_term

            product.subscription_annual_value = product.list_price * periods_per_year

    @api.depends('member_price', 'subscription_member_discount_additional')
    def _compute_subscription_effective_member_price(self):
        """Calculate effective member price with additional subscription discount."""
        for product in self:
            if not product.is_subscription_product:
                product.subscription_effective_member_price = product.member_price
                continue

            base_price = product.member_price if product.member_price else product.list_price
            
            if product.subscription_member_discount_additional > 0:
                additional_discount = base_price * (product.subscription_member_discount_additional / 100)
                product.subscription_effective_member_price = base_price - additional_discount
            else:
                product.subscription_effective_member_price = base_price

    @api.depends('subscription_billing_period_id')
    def _compute_subscription_billing_frequency(self):
        """Compute human-readable billing frequency."""
        for product in self:
            if product.subscription_billing_period_id:
                period = product.subscription_billing_period_id
                product.subscription_billing_frequency = f"Every {period.period_summary}"
            else:
                product.subscription_billing_frequency = ""

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior_subscription(self):
        """Apply subscription-specific defaults when behavior is selected."""
        result = super()._onchange_ams_product_behavior()
        
        if self.ams_product_behavior == 'subscription':
            # Set subscription defaults
            self.is_subscription_product = True
            self.subscription_term = 12
            self.subscription_term_type = 'months'
            self.subscription_auto_renewal = True
            self.subscription_prorated_billing = True
            self.type = 'service'
            
            # Set default billing period if available
            default_period = self.env['ams.billing.period'].get_default_period()
            if default_period:
                self.subscription_billing_period_id = default_period.id
                # Sync term with billing period
                self.subscription_term = default_period.duration_value
                self.subscription_term_type = default_period.duration_unit
            
            # Set content type based on category
            if self.categ_id:
                content_type_mapping = {
                    'publication': 'publication',
                    'digital': 'digital_access',
                    'certification': 'course',
                    'membership': 'premium',
                }
                ams_category = getattr(self.categ_id, 'ams_category_type', None)
                if ams_category in content_type_mapping:
                    self.subscription_content_type = content_type_mapping[ams_category]
        
        elif self.ams_product_behavior and self.ams_product_behavior != 'subscription':
            # Clear subscription fields if changing away from subscription
            if self._origin and self._origin.ams_product_behavior == 'subscription':
                self.is_subscription_product = False
                self.subscription_billing_period_id = False
        
        return result

    @api.onchange('subscription_billing_period_id')
    def _onchange_subscription_billing_period(self):
        """Sync subscription term with selected billing period."""
        if self.subscription_billing_period_id:
            period = self.subscription_billing_period_id
            self.subscription_term = period.duration_value
            self.subscription_term_type = period.duration_unit

    @api.onchange('categ_id')
    def _onchange_categ_id_subscription(self):
        """Enhanced category onchange with subscription suggestions."""
        result = super()._onchange_categ_id()
        
        # Suggest subscription behavior for subscription categories
        if (self.categ_id and 
            hasattr(self.categ_id, 'is_subscription_category') and 
            self.categ_id.is_subscription_category and
            not self._origin.id):  # Only for new products
            
            if not self.ams_product_behavior:
                self.ams_product_behavior = 'subscription'
        
        return result

    # ========================================================================
    # BUSINESS METHODS - SUBSCRIPTION MANAGEMENT
    # ========================================================================

    def get_subscription_details(self):
        """
        Get comprehensive subscription details for this product.
        
        Returns:
            dict: Complete subscription configuration
        """
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'is_subscription': False}
            
        # Get reminder days as list
        reminder_days = []
        if self.subscription_renewal_reminder_days:
            try:
                reminder_days = [int(d.strip()) for d in self.subscription_renewal_reminder_days.split(',')]
            except (ValueError, AttributeError):
                reminder_days = [30, 15, 7]  # Default fallback
        
        return {
            'is_subscription': True,
            'term': self.subscription_term,
            'term_type': self.subscription_term_type,
            'term_display': f"{self.subscription_term} {dict(self._fields['subscription_term_type'].selection)[self.subscription_term_type]}",
            'billing_period': self.subscription_billing_period_id.name if self.subscription_billing_period_id else None,
            'billing_period_id': self.subscription_billing_period_id.id if self.subscription_billing_period_id else None,
            'billing_frequency': self.subscription_billing_frequency,
            'auto_renewal': self.subscription_auto_renewal,
            'grace_period': self.subscription_grace_period,
            'min_term': self.subscription_min_term,
            'cancellation_notice': self.subscription_cancellation_notice,
            'prorated_billing': self.subscription_prorated_billing,
            'content_type': self.subscription_content_type,
            'access_level': self.subscription_access_level,
            'concurrent_users': self.subscription_concurrent_users,
            'download_limit': self.subscription_download_limit,
            'setup_fee': self.subscription_setup_fee,
            'cancellation_fee': self.subscription_cancellation_fee,
            'annual_value': self.subscription_annual_value,
            'effective_member_price': self.subscription_effective_member_price,
            'renewal_reminder_days': reminder_days,
            'revenue_recognition': self.subscription_revenue_recognition_method,
            'summary': self.subscription_summary,
        }

    def calculate_subscription_pricing_for_partner(self, partner, start_date=None):
        """
        Calculate subscription pricing for a specific partner with prorating.
        
        Args:
            partner (res.partner): Partner to calculate pricing for
            start_date (date, optional): Subscription start date for prorating
            
        Returns:
            dict: Pricing breakdown
        """
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'error': 'Not a subscription product'}
            
        # Get base pricing
        is_member = self._check_partner_membership(partner)
        base_price = self.subscription_effective_member_price if is_member else self.list_price
        
        # Calculate prorated amount if start date provided
        prorated_amount = base_price
        proration_factor = 1.0
        
        if start_date and self.subscription_prorated_billing and self.subscription_billing_period_id:
            try:
                period_start = start_date
                period_end = self.subscription_billing_period_id.calculate_period_end(period_start)
                total_days = (period_end - period_start).days + 1
                period_length = self.subscription_billing_period_id.total_days
                
                if total_days > 0 and period_length > 0:
                    proration_factor = total_days / period_length
                    prorated_amount = base_price * proration_factor
            except Exception as e:
                _logger.warning(f"Proration calculation failed: {e}")
        
        return {
            'base_price': base_price,
            'prorated_amount': prorated_amount,
            'proration_factor': proration_factor,
            'setup_fee': self.subscription_setup_fee,
            'total_initial_amount': prorated_amount + self.subscription_setup_fee,
            'is_member': is_member,
            'member_savings': self.list_price - base_price if is_member else 0.0,
            'is_prorated': proration_factor < 1.0,
        }

    def get_subscription_next_billing_date(self, start_date=None):
        """
        Calculate next billing date for subscription.
        
        Args:
            start_date (date, optional): Subscription start date
            
        Returns:
            date: Next billing date
        """
        self.ensure_one()
        
        if not start_date:
            start_date = fields.Date.today()
            
        if self.subscription_billing_period_id:
            return self.subscription_billing_period_id.calculate_next_date(start_date)
        else:
            # Fallback calculation
            if self.subscription_term_type == 'days':
                return start_date + timedelta(days=self.subscription_term)
            elif self.subscription_term_type == 'weeks':
                return start_date + timedelta(weeks=self.subscription_term)
            elif self.subscription_term_type == 'months':
                return start_date + relativedelta(months=self.subscription_term)
            elif self.subscription_term_type == 'years':
                return start_date + relativedelta(years=self.subscription_term)
        
        return start_date

    def get_subscription_access_details(self):
        """
        Get subscription access and content details.
        
        Returns:
            dict: Access configuration
        """
        self.ensure_one()
        
        return {
            'content_type': self.subscription_content_type,
            'content_type_display': dict(self._fields['subscription_content_type'].selection).get(self.subscription_content_type) if self.subscription_content_type else None,
            'access_level': self.subscription_access_level,
            'access_level_display': dict(self._fields['subscription_access_level'].selection).get(self.subscription_access_level),
            'concurrent_users': self.subscription_concurrent_users,
            'unlimited_users': self.subscription_concurrent_users == 0,
            'download_limit': self.subscription_download_limit,
            'unlimited_downloads': self.subscription_download_limit == 0,
            'has_digital_content': self.has_digital_content,
            'grants_portal_access': self.grants_portal_access,
            'portal_groups': self.portal_group_ids.mapped('name') if self.grants_portal_access else [],
        }

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('subscription_term', 'subscription_min_term')
    def _check_subscription_terms(self):
        """Validate subscription term values."""
        for product in self:
            if product.is_subscription_product:
                if product.subscription_term <= 0:
                    raise ValidationError(_("Subscription term must be greater than 0."))
                
                if product.subscription_min_term < 0:
                    raise ValidationError(_("Minimum subscription term cannot be negative."))
                
                if product.subscription_min_term > product.subscription_term:
                    raise ValidationError(_("Minimum term cannot be greater than subscription term."))

    @api.constrains('subscription_grace_period', 'subscription_cancellation_notice')
    def _check_subscription_periods(self):
        """Validate subscription period values."""
        for product in self:
            if product.is_subscription_product:
                if product.subscription_grace_period < 0:
                    raise ValidationError(_("Grace period cannot be negative."))
                
                if product.subscription_cancellation_notice < 0:
                    raise ValidationError(_("Cancellation notice period cannot be negative."))

    @api.constrains('subscription_concurrent_users', 'subscription_download_limit')
    def _check_subscription_limits(self):
        """Validate subscription usage limits."""
        for product in self:
            if product.is_subscription_product:
                if product.subscription_concurrent_users < 0:
                    raise ValidationError(_("Concurrent users limit cannot be negative."))
                
                if product.subscription_download_limit < 0:
                    raise ValidationError(_("Download limit cannot be negative."))

    @api.constrains('subscription_member_discount_additional')
    def _check_subscription_additional_discount(self):
        """Validate additional member discount."""
        for product in self:
            if (product.is_subscription_product and 
                product.subscription_member_discount_additional < 0):
                raise ValidationError(_("Additional member discount cannot be negative."))

    # ========================================================================
    # QUERY METHODS FOR SUBSCRIPTIONS
    # ========================================================================

    @api.model
    def get_subscription_products(self, content_type=None, access_level=None):
        """Get subscription products with optional filtering."""
        domain = [('ams_product_behavior', '=', 'subscription')]
        
        if content_type:
            domain.append(('subscription_content_type', '=', content_type))
        
        if access_level:
            domain.append(('subscription_access_level', '=', access_level))
        
        return self.search(domain)

    @api.model
    def get_auto_renewal_subscriptions(self):
        """Get subscriptions with auto-renewal enabled."""
        return self.search([
            ('ams_product_behavior', '=', 'subscription'),
            ('subscription_auto_renewal', '=', True)
        ])

    @api.model
    def get_prorated_subscriptions(self):
        """Get subscriptions with prorated billing enabled."""
        return self.search([
            ('ams_product_behavior', '=', 'subscription'),
            ('subscription_prorated_billing', '=', True)
        ])

    @api.model
    def get_subscription_products_by_billing_period(self, billing_period_id):
        """Get subscription products using specific billing period."""
        return self.search([
            ('ams_product_behavior', '=', 'subscription'),
            ('subscription_billing_period_id', '=', billing_period_id)
        ])

    # ========================================================================
    # ENHANCED NAME DISPLAY
    # ========================================================================

    def name_get(self):
        """Enhanced name display for subscription products."""
        result = super().name_get()
        
        # Add subscription indicator for subscription products
        if self.env.context.get('show_subscription_info'):
            new_result = []
            for product_id, name in result:
                product = self.browse(product_id)
                if product.ams_product_behavior == 'subscription':
                    billing_info = ""
                    if product.subscription_billing_period_id:
                        billing_info = f" ({product.subscription_billing_period_id.name})"
                    name = f"🔄 {name}{billing_info}"
                new_result.append((product_id, name))
            return new_result
        
        return result