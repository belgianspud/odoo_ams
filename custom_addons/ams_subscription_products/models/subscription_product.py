# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionProduct(models.Model):
    """
    Subscription Product Definitions for Association Management.
    
    This model provides a catalog of subscription products available within the association,
    allowing for centralized management of subscription offerings and their characteristics.
    """
    _name = 'ams.subscription.product'
    _inherit = ['mail.thread']
    _description = 'AMS Subscription Product'
    _order = 'sequence, name'
    _rec_name = 'name'

    # ========================================================================
    # CORE DEFINITION FIELDS
    # ========================================================================

    name = fields.Char(
        string="Subscription Name",
        required=True,
        tracking=True,
        help="Display name for this subscription product offering"
    )

    code = fields.Char(
        string="Code",
        required=True,
        tracking=True,
        help="Unique code for this subscription product (e.g., INDIV_ANNUAL, CORP_MONTHLY)"
    )

    product_template_id = fields.Many2one(
        'product.template',
        string="Product Template",
        required=True,
        domain=[('is_subscription', '=', True)],
        tracking=True,
        help="Underlying product template that provides subscription functionality"
    )

    sequence = fields.Integer(
        string="Display Order",
        default=10,
        help="Order for displaying subscription products in lists"
    )

    # ========================================================================
    # SUBSCRIPTION CLASSIFICATION
    # ========================================================================

    subscription_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('committee', 'Committee Access'),
        ('publication', 'Publication Subscription'),
        ('service', 'Service Subscription'),
        ('certification', 'Certification Program'),
        ('training', 'Training & Education'),
        ('premium', 'Premium Access'),
    ], string="Subscription Type",
       required=True,
       tracking=True,
       help="Classification of subscription product for organizational purposes")

    subscription_category = fields.Selection([
        ('core', 'Core Membership'),
        ('add_on', 'Add-on Service'),
        ('premium', 'Premium Upgrade'),
        ('specialty', 'Specialty Access'),
    ], string="Subscription Category",
       default='core',
       help="Category classification for subscription hierarchy")

    # ========================================================================
    # DURATION CONFIGURATION
    # ========================================================================

    default_duration = fields.Integer(
        string="Default Duration",
        required=True,
        default=12,
        help="Default subscription duration in the specified unit"
    )

    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string="Duration Unit",
       required=True,
       default='months',
       help="Unit of time for the subscription duration")

    # ========================================================================
    # BILLING INTEGRATION
    # ========================================================================

    billing_period_ids = fields.Many2many(
        'ams.billing.period',
        'subscription_product_billing_period_rel',
        'subscription_product_id',
        'billing_period_id',
        string="Supported Billing Periods",
        help="Billing periods available for this subscription product"
    )

    default_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Default Billing Period",
        help="Default billing cycle for new subscriptions"
    )

    # ========================================================================
    # BASIC PRICING (Foundation for Advanced Pricing)
    # ========================================================================

    base_price = fields.Monetary(
        string="Base Price",
        required=True,
        tracking=True,
        help="Base price for this subscription (before discounts, add-ons, etc.)"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency for subscription pricing"
    )

    # ========================================================================
    # FEATURE FLAGS & ACCESS CONTROL
    # ========================================================================

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Whether this subscription product is available for new subscriptions"
    )

    member_only = fields.Boolean(
        string="Members Only",
        default=False,
        help="Whether this subscription is restricted to existing association members"
    )

    requires_approval = fields.Boolean(
        string="Requires Approval",
        default=False,
        help="Whether new subscriptions require staff approval"
    )

    auto_assign = fields.Boolean(
        string="Auto-assign to Members",
        default=False,
        help="Automatically assign this subscription to qualifying members"
    )

    # ========================================================================
    # DESCRIPTIVE INFORMATION
    # ========================================================================

    description = fields.Html(
        string="Description",
        help="Detailed description of subscription benefits and features"
    )

    short_description = fields.Text(
        string="Short Description",
        help="Brief summary for listings and selection interfaces"
    )

    benefits_included = fields.Text(
        string="Benefits Included",
        help="List of benefits and services included with this subscription"
    )

    terms_conditions = fields.Html(
        string="Terms & Conditions",
        help="Specific terms and conditions for this subscription product"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    subscription_summary = fields.Char(
        string="Subscription Summary",
        compute='_compute_subscription_summary',
        help="Summary of key subscription characteristics"
    )

    duration_display = fields.Char(
        string="Duration Display",
        compute='_compute_duration_display',
        help="Human-readable duration display"
    )

    billing_options_count = fields.Integer(
        string="Billing Options Count",
        compute='_compute_billing_options_count',
        help="Number of supported billing periods"
    )

    template_behavior = fields.Selection(
        string="Product Behavior",
        related='product_template_id.ams_product_behavior',
        readonly=True,
        help="Product behavior from underlying template"
    )

    template_grants_portal_access = fields.Boolean(
        string="Grants Portal Access",
        related='product_template_id.grants_portal_access',
        readonly=True,
        help="Whether subscription grants portal access"
    )

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Subscription product code must be unique!'),
        ('name_unique', 'UNIQUE(name)', 'Subscription product name must be unique!'),
        ('base_price_positive', 'CHECK(base_price >= 0)', 'Base price must be non-negative!'),
        ('default_duration_positive', 'CHECK(default_duration > 0)', 'Default duration must be positive!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('subscription_type', 'subscription_category', 'duration_display', 
                 'base_price', 'currency_id')
    def _compute_subscription_summary(self):
        """Generate subscription summary for display"""
        for subscription in self:
            parts = []
            
            # Type and category
            if subscription.subscription_type:
                type_display = dict(subscription._fields['subscription_type'].selection)[subscription.subscription_type]
                parts.append(type_display)
            
            if subscription.subscription_category != 'core':
                category_display = dict(subscription._fields['subscription_category'].selection)[subscription.subscription_category]
                parts.append(f"({category_display})")
            
            # Duration
            if subscription.duration_display:
                parts.append(subscription.duration_display)
            
            # Price
            if subscription.base_price and subscription.currency_id:
                price_str = f"{subscription.currency_id.symbol}{subscription.base_price:,.2f}"
                parts.append(price_str)
            
            subscription.subscription_summary = " • ".join(parts)

    @api.depends('default_duration', 'duration_unit')
    def _compute_duration_display(self):
        """Generate human-readable duration display"""
        for subscription in self:
            if subscription.default_duration and subscription.duration_unit:
                unit_display = subscription.duration_unit
                if subscription.default_duration == 1:
                    # Singular form
                    unit_display = unit_display.rstrip('s')
                
                subscription.duration_display = f"{subscription.default_duration} {unit_display.title()}"
            else:
                subscription.duration_display = ""

    @api.depends('billing_period_ids')
    def _compute_billing_options_count(self):
        """Count supported billing periods"""
        for subscription in self:
            subscription.billing_options_count = len(subscription.billing_period_ids)

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty"""
        if self.name and not self.code:
            # Generate code from name: "Individual Annual Membership" -> "INDIV_ANNUAL_MEMBERSHIP"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
            # Limit length
            if len(self.code) > 25:
                self.code = self.code[:25]

    @api.onchange('subscription_type')
    def _onchange_subscription_type(self):
        """Apply type-specific defaults"""
        if not self.subscription_type:
            return
            
        type_defaults = {
            'membership': {
                'subscription_category': 'core',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': False,
            },
            'chapter': {
                'subscription_category': 'specialty',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': True,
            },
            'committee': {
                'subscription_category': 'specialty',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': True,
            },
            'publication': {
                'subscription_category': 'add_on',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': False,
            },
            'service': {
                'subscription_category': 'add_on',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': False,
            },
            'certification': {
                'subscription_category': 'specialty',
                'default_duration': 24,
                'duration_unit': 'months',
                'member_only': True,
            },
            'training': {
                'subscription_category': 'add_on',
                'default_duration': 6,
                'duration_unit': 'months',
                'member_only': False,
            },
            'premium': {
                'subscription_category': 'premium',
                'default_duration': 12,
                'duration_unit': 'months',
                'member_only': True,
            },
        }
        
        defaults = type_defaults.get(self.subscription_type, {})
        for field, value in defaults.items():
            if not getattr(self, field):
                setattr(self, field, value)

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        """Sync data with selected product template"""
        if self.product_template_id:
            # Inherit base price from product
            if not self.base_price:
                self.base_price = self.product_template_id.list_price
            
            # Inherit billing periods if template has subscription config
            if hasattr(self.product_template_id, 'default_billing_period_id') and self.product_template_id.default_billing_period_id:
                if not self.default_billing_period_id:
                    self.default_billing_period_id = self.product_template_id.default_billing_period_id
                
                # Add to supported periods if not already present
                if self.product_template_id.default_billing_period_id not in self.billing_period_ids:
                    self.billing_period_ids = [(4, self.product_template_id.default_billing_period_id.id)]

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @api.constrains('default_duration', 'duration_unit')
    def _check_duration_validity(self):
        """Validate duration configuration"""
        for subscription in self:
            if subscription.default_duration <= 0:
                raise ValidationError(_("Default duration must be greater than 0"))
            
            # Check for reasonable limits
            if subscription.duration_unit == 'days' and subscription.default_duration > 3650:  # ~10 years
                raise ValidationError(_("Duration in days cannot exceed 3650"))
            elif subscription.duration_unit == 'months' and subscription.default_duration > 120:  # 10 years
                raise ValidationError(_("Duration in months cannot exceed 120"))
            elif subscription.duration_unit == 'years' and subscription.default_duration > 10:
                raise ValidationError(_("Duration in years cannot exceed 10"))

    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format"""
        for subscription in self:
            if subscription.code:
                if not subscription.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(subscription.code) > 50:
                    raise ValidationError(_("Code cannot be longer than 50 characters"))

    @api.constrains('default_billing_period_id', 'billing_period_ids')
    def _check_default_billing_period(self):
        """Ensure default billing period is in supported periods"""
        for subscription in self:
            if subscription.default_billing_period_id and subscription.billing_period_ids:
                if subscription.default_billing_period_id not in subscription.billing_period_ids:
                    raise ValidationError(_("Default billing period must be included in supported billing periods"))

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def get_subscription_configuration(self):
        """
        Get complete subscription configuration.
        
        Returns:
            dict: Comprehensive subscription configuration
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'type': self.subscription_type,
            'category': self.subscription_category,
            'duration': self.default_duration,
            'duration_unit': self.duration_unit,
            'duration_display': self.duration_display,
            'base_price': self.base_price,
            'currency_id': self.currency_id.id,
            'currency_code': self.currency_id.name,
            'member_only': self.member_only,
            'requires_approval': self.requires_approval,
            'auto_assign': self.auto_assign,
            'active': self.active,
            'product_template_id': self.product_template_id.id,
            'billing_period_ids': self.billing_period_ids.ids,
            'default_billing_period_id': self.default_billing_period_id.id if self.default_billing_period_id else None,
            'benefits_included': self.benefits_included,
            'summary': self.subscription_summary,
        }

    def get_pricing_info(self, billing_period=None):
        """
        Get pricing information for specific billing period.
        
        Args:
            billing_period (ams.billing.period, optional): Specific billing period
            
        Returns:
            dict: Pricing information
        """
        self.ensure_one()
        
        # Use provided period or default
        period = billing_period or self.default_billing_period_id
        
        if not period:
            return {
                'base_price': self.base_price,
                'currency_id': self.currency_id.id,
                'billing_period': None,
                'period_price': self.base_price,
            }
        
        # For now, return base price
        # Future pricing modules can extend this with period-specific calculations
        return {
            'base_price': self.base_price,
            'currency_id': self.currency_id.id,
            'billing_period': period.name,
            'billing_period_id': period.id,
            'period_price': self.base_price,
            'period_summary': period.period_summary,
        }

    def is_available_for_partner(self, partner):
        """
        Check if this subscription is available for a given partner.
        
        Args:
            partner (res.partner): Partner to check availability for
            
        Returns:
            bool: True if subscription is available
        """
        self.ensure_one()
        
        # Check if subscription is active
        if not self.active:
            return False
        
        # Check member-only restriction
        if self.member_only:
            if not partner:
                return False
            
            # Use ams_member_data fields if available
            if hasattr(partner, 'is_member') and hasattr(partner, 'membership_status'):
                return partner.is_member and partner.membership_status == 'active'
            
            # Fallback to standard membership module
            if hasattr(partner, 'membership_state'):
                return partner.membership_state in ['invoiced', 'paid']
            
            return False
        
        return True

    def get_duration_in_days(self):
        """
        Get subscription duration in days for comparison purposes.
        
        Returns:
            int: Approximate duration in days
        """
        self.ensure_one()
        
        if self.duration_unit == 'days':
            return self.default_duration
        elif self.duration_unit == 'months':
            return int(self.default_duration * 30.44)  # Average month length
        elif self.duration_unit == 'years':
            return int(self.default_duration * 365.25)  # Average year length
        
        return 0

    # ========================================================================
    # QUERY METHODS
    # ========================================================================

    @api.model
    def get_active_subscriptions(self):
        """Get all active subscription products"""
        return self.search([('active', '=', True)])

    @api.model
    def get_subscriptions_by_type(self, subscription_type):
        """Get subscription products by type"""
        return self.search([
            ('active', '=', True),
            ('subscription_type', '=', subscription_type)
        ])

    @api.model
    def get_member_only_subscriptions(self):
        """Get subscription products restricted to members"""
        return self.search([
            ('active', '=', True),
            ('member_only', '=', True)
        ])

    @api.model
    def get_public_subscriptions(self):
        """Get subscription products available to non-members"""
        return self.search([
            ('active', '=', True),
            ('member_only', '=', False)
        ])

    @api.model
    def get_subscriptions_by_duration_range(self, min_days=None, max_days=None):
        """Get subscription products within duration range"""
        subscriptions = self.search([('active', '=', True)])
        
        if min_days is None and max_days is None:
            return subscriptions
        
        filtered_subs = self.browse()
        for sub in subscriptions:
            duration_days = sub.get_duration_in_days()
            
            if min_days and duration_days < min_days:
                continue
            if max_days and duration_days > max_days:
                continue
                
            filtered_subs |= sub
        
        return filtered_subs

    # ========================================================================
    # UI ACTIONS
    # ========================================================================

    def action_view_product_template(self):
        """Open the linked product template"""
        self.ensure_one()
        return {
            'name': _('Product Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_template_id.id,
            'target': 'current',
        }

    def action_test_availability(self):
        """Test subscription availability with sample partners"""
        self.ensure_one()
        
        # Find sample partners for testing
        test_partners = self.env['res.partner'].search([
            '|', ('is_member', '=', True), ('is_member', '=', False)
        ], limit=5)
        
        results = []
        for partner in test_partners:
            is_available = self.is_available_for_partner(partner)
            is_member = hasattr(partner, 'is_member') and partner.is_member
            
            status = "✓ Available" if is_available else "✗ Not Available"
            member_status = "Member" if is_member else "Non-member"
            results.append(f"{partner.name} ({member_status}): {status}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'Availability Test: {self.name}',
                'message': '\n'.join(results) if results else 'No test partners found',
                'type': 'info',
                'sticky': True,
            }
        }

    # ========================================================================
    # NAME AND DISPLAY
    # ========================================================================

    def name_get(self):
        """Custom name display with code and type"""
        result = []
        for subscription in self:
            name = subscription.name
            if subscription.code:
                name = f"[{subscription.code}] {name}"
            if subscription.subscription_type:
                type_display = dict(subscription._fields['subscription_type'].selection)[subscription.subscription_type]
                name = f"{name} ({type_display})"
            result.append((subscription.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search including code and type"""
        args = args or []
        
        if name:
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('subscription_type', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)