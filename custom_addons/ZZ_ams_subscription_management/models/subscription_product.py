from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionProduct(models.Model):
    """Core subscription product definition with member-type pricing."""
    _name = 'ams.subscription.product'
    _description = 'Subscription Product Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'product_type, subscription_scope, name'
    _rec_name = 'name'

    # ==========================================
    # CORE IDENTITY FIELDS
    # ==========================================
    
    name = fields.Char(
        string='Product Name',
        required=True,
        tracking=True,
        help='Subscription product name'
    )
    
    code = fields.Char(
        string='Unique Code',
        required=True,
        tracking=True,
        help='Unique identifier for this subscription'
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Related Product',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Base product record'
    )
    
    # ==========================================
    # CLASSIFICATION FIELDS
    # ==========================================
    
    subscription_scope = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('enterprise', 'Enterprise Subscription')
    ], string='Subscription Scope',
       required=True,
       default='individual',
       tracking=True,
       help='Target audience for this subscription')
    
    product_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('committee', 'Committee'),
        ('publication', 'Publication'),
        ('certification', 'Certification'),
        ('continuing_education', 'Continuing Education'),
        ('conference', 'Conference Access'),
        ('professional_insurance', 'Professional Insurance'),
        ('legal_resources', 'Legal Resources'),
    ], string='Product Type',
       required=True,
       default='membership',
       tracking=True,
       help='Type of subscription offering')
    
    description = fields.Html(
        string='Description',
        help='Detailed subscription description'
    )
    
    # ==========================================
    # DURATION & PRICING FIELDS
    # ==========================================
    
    default_duration = fields.Integer(
        string='Default Duration',
        required=True,
        default=12,
        tracking=True,
        help='Standard subscription duration'
    )
    
    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Duration Unit',
       required=True,
       default='months',
       tracking=True,
       help='Unit for duration calculation')
    
    default_price = fields.Monetary(
        string='Default Price',
        required=True,
        currency_field='currency_id',
        tracking=True,
        help='Base subscription price'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Currency for pricing'
    )
    
    # ==========================================
    # PROFESSIONAL ASSOCIATION FIELDS
    # ==========================================
    
    verification_type = fields.Selection([
        ('none', 'No Verification Required'),
        ('license_check', 'Professional License Verification'),
        ('employer_verification', 'Employer Verification'),
        ('education_credentials', 'Education Credential Verification'),
        ('membership_status', 'Current Membership Status'),
        ('ce_credits', 'Continuing Education Credits'),
    ], string='Verification Type',
       default='none',
       help='Type of verification required for this subscription')
    
    license_requirements = fields.Text(
        string='License Requirements',
        help='Specific professional license requirements for this subscription'
    )
    
    continuing_education_required = fields.Boolean(
        string='CE Credits Required',
        help='Continuing education credits required for this subscription'
    )
    
    ce_credits_per_period = fields.Integer(
        string='CE Credits Required',
        help='Number of continuing education credits required per subscription period'
    )
    
    professional_insurance_included = fields.Boolean(
        string='Professional Insurance Included',
        help='Professional liability insurance included with subscription'
    )
    
    regulatory_compliance_tracking = fields.Boolean(
        string='Regulatory Compliance Tracking',
        help='Track regulatory compliance requirements for this subscription'
    )
    
    # ==========================================
    # ENTERPRISE SUBSCRIPTION FIELDS
    # ==========================================
    
    default_seat_count = fields.Integer(
        string='Default Seats',
        tracking=True,
        help='Default number of seats for enterprise subscriptions'
    )
    
    seat_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Additional Seat Product',
        help='Product for purchasing additional seats'
    )
    
    allow_seat_purchase = fields.Boolean(
        string='Allow Additional Seats',
        tracking=True,
        help='Enable purchasing extra seats beyond default allocation'
    )
    
    # ==========================================
    # RENEWAL & CONFIGURATION FIELDS
    # ==========================================
    
    is_renewable = fields.Boolean(
        string='Is Renewable',
        default=True,
        tracking=True,
        help='Subscription can be renewed'
    )
    
    renewal_window_days = fields.Integer(
        string='Renewal Window (Days)',
        help='Days before expiration to allow renewals'
    )
    
    auto_renewal_enabled = fields.Boolean(
        string='Auto-Renewal Available',
        tracking=True,
        help='Subscription supports automatic renewal'
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        tracking=True,
        help='Staff approval required before activation'
    )
    
    approval_workflow_id = fields.Many2one(
        'workflow.definition',
        string='Approval Workflow',
        help='Specific workflow for subscription approval'
    )
    
    member_only = fields.Boolean(
        string='Members Only',
        tracking=True,
        help='Restricted to current association members'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Available for new subscriptions'
    )
    
    # ==========================================
    # PRICING ENHANCEMENTS
    # ==========================================
    
    early_bird_enabled = fields.Boolean(
        string='Early Bird Pricing',
        help='Enable early bird pricing for this subscription'
    )
    
    early_bird_price = fields.Monetary(
        string='Early Bird Price',
        currency_field='currency_id',
        help='Special early bird pricing'
    )
    
    early_bird_deadline = fields.Date(
        string='Early Bird Deadline',
        help='Deadline for early bird pricing'
    )
    
    group_discount_enabled = fields.Boolean(
        string='Group Discounts',
        help='Enable group discount pricing'
    )
    
    group_discount_threshold = fields.Integer(
        string='Group Discount Threshold',
        help='Minimum number for group discount'
    )
    
    group_discount_percentage = fields.Float(
        string='Group Discount %',
        help='Percentage discount for group purchases'
    )
    
    # ==========================================
    # RELATIONSHIP FIELDS
    # ==========================================
    
    pricing_tier_ids = fields.One2many(
        'ams.subscription.pricing.tier',
        'subscription_product_id',
        string='Pricing Tiers',
        help='Member-type specific pricing'
    )
    
    benefit_assignment_ids = fields.One2many(
        'ams.subscription.product.benefit',
        'subscription_product_id',
        string='Attached Benefits',
        help='Benefits included with this subscription'
    )
    
    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    pricing_tier_count = fields.Integer(
        string='Pricing Tiers',
        compute='_compute_pricing_tier_count',
        store=True,
        help='Number of member pricing tiers defined'
    )
    
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display',
        help='Human-readable duration format'
    )
    
    has_member_pricing = fields.Boolean(
        string='Has Member Pricing',
        compute='_compute_has_member_pricing',
        store=True,
        help='Has different pricing for member types'
    )
    
    min_member_price = fields.Monetary(
        string='Lowest Member Price',
        compute='_compute_price_range',
        currency_field='currency_id',
        help='Lowest price among member tiers'
    )
    
    max_member_price = fields.Monetary(
        string='Highest Member Price',
        compute='_compute_price_range',
        currency_field='currency_id',
        help='Highest price among member tiers'
    )
    
    professional_features_summary = fields.Text(
        string='Professional Features Summary',
        compute='_compute_professional_summary',
        help='Summary of professional association features'
    )
    
    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 
         'Subscription code must be unique.'),
        ('product_unique', 'UNIQUE(product_id)', 
         'Each product can only have one subscription configuration.'),
        ('positive_duration', 'CHECK(default_duration > 0)',
         'Duration must be positive.'),
        ('positive_price', 'CHECK(default_price >= 0)',
         'Price cannot be negative.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('pricing_tier_ids')
    def _compute_pricing_tier_count(self):
        """Compute number of pricing tiers with error handling."""
        for record in self:
            try:
                record.pricing_tier_count = len(record.pricing_tier_ids)
            except Exception as e:
                _logger.warning(f"Error computing pricing tier count for {record.id}: {e}")
                record.pricing_tier_count = 0

    @api.depends('default_duration', 'duration_unit')
    def _compute_duration_display(self):
        """Generate human-readable duration display."""
        for record in self:
            try:
                if record.default_duration and record.duration_unit:
                    unit_name = dict(record._fields['duration_unit'].selection)[record.duration_unit]
                    if record.default_duration == 1:
                        # Singular form
                        unit_name = unit_name.rstrip('s')
                    record.duration_display = f"{record.default_duration} {unit_name}"
                else:
                    record.duration_display = "Not configured"
            except Exception as e:
                _logger.warning(f"Error computing duration display for {record.id}: {e}")
                record.duration_display = "Error"

    @api.depends('pricing_tier_ids.price')
    def _compute_has_member_pricing(self):
        """Check if subscription has member-specific pricing."""
        for record in self:
            try:
                record.has_member_pricing = bool(record.pricing_tier_ids)
            except Exception as e:
                _logger.warning(f"Error computing has_member_pricing for {record.id}: {e}")
                record.has_member_pricing = False

    @api.depends('pricing_tier_ids.price')
    def _compute_price_range(self):
        """Compute price range across member tiers."""
        for record in self:
            try:
                if record.pricing_tier_ids:
                    prices = record.pricing_tier_ids.mapped('price')
                    record.min_member_price = min(prices) if prices else 0.0
                    record.max_member_price = max(prices) if prices else 0.0
                else:
                    record.min_member_price = record.default_price
                    record.max_member_price = record.default_price
            except Exception as e:
                _logger.warning(f"Error computing price range for {record.id}: {e}")
                record.min_member_price = record.default_price
                record.max_member_price = record.default_price

    @api.depends('verification_type', 'continuing_education_required', 'professional_insurance_included', 'regulatory_compliance_tracking')
    def _compute_professional_summary(self):
        """Compute professional features summary."""
        for record in self:
            try:
                features = []
                if record.verification_type != 'none':
                    features.append(f"Verification: {dict(record._fields['verification_type'].selection)[record.verification_type]}")
                if record.continuing_education_required:
                    features.append(f"CE Credits: {record.ce_credits_per_period} per period")
                if record.professional_insurance_included:
                    features.append("Professional Insurance Included")
                if record.regulatory_compliance_tracking:
                    features.append("Regulatory Compliance Tracking")
                
                record.professional_features_summary = "; ".join(features) if features else "Standard subscription features"
            except Exception as e:
                _logger.warning(f"Error computing professional summary for {record.id}: {e}")
                record.professional_features_summary = "Error computing features"

    # ==========================================
    # VALIDATION CONSTRAINTS
    # ==========================================

    @api.constrains('subscription_scope', 'default_seat_count')
    def _validate_enterprise_configuration(self):
        """Validate enterprise subscription settings."""
        for record in self:
            try:
                if record.subscription_scope == 'enterprise':
                    if not record.default_seat_count or record.default_seat_count < 1:
                        raise ValidationError(
                            f"Enterprise subscription '{record.name}' requires "
                            f"default seat count of at least 1."
                        )
            except Exception as e:
                _logger.error(f"Error validating enterprise configuration for {record.id}: {e}")

    @api.constrains('seat_product_id')
    def _validate_seat_product(self):
        """Validate additional seat product configuration."""
        for record in self:
            try:
                if record.seat_product_id:
                    if record.seat_product_id.id == record.id:
                        raise ValidationError(
                            "Subscription cannot reference itself as seat product."
                        )
                    if record.seat_product_id.subscription_scope != 'individual':
                        raise ValidationError(
                            "Additional seat product must be individual scope."
                        )
            except Exception as e:
                _logger.error(f"Error validating seat product for {record.id}: {e}")

    @api.constrains('renewal_window_days')
    def _validate_renewal_window(self):
        """Validate renewal window settings."""
        for record in self:
            try:
                if record.is_renewable and record.renewal_window_days:
                    if record.renewal_window_days < 0:
                        raise ValidationError(
                            "Renewal window cannot be negative."
                        )
                    if record.renewal_window_days > 365:
                        raise ValidationError(
                            "Renewal window cannot exceed 365 days."
                        )
            except Exception as e:
                _logger.error(f"Error validating renewal window for {record.id}: {e}")

    @api.constrains('continuing_education_required', 'ce_credits_per_period')
    def _validate_ce_requirements(self):
        """Validate continuing education requirements."""
        for record in self:
            try:
                if record.continuing_education_required:
                    if not record.ce_credits_per_period or record.ce_credits_per_period <= 0:
                        raise ValidationError(
                            "CE credits per period must be specified and positive when CE is required."
                        )
            except Exception as e:
                _logger.error(f"Error validating CE requirements for {record.id}: {e}")

    @api.constrains('early_bird_enabled', 'early_bird_price', 'early_bird_deadline')
    def _validate_early_bird_pricing(self):
        """Validate early bird pricing configuration."""
        for record in self:
            try:
                if record.early_bird_enabled:
                    if not record.early_bird_price or record.early_bird_price <= 0:
                        raise ValidationError(
                            "Early bird price must be specified and positive."
                        )
                    if not record.early_bird_deadline:
                        raise ValidationError(
                            "Early bird deadline must be specified."
                        )
                    if record.early_bird_price >= record.default_price:
                        raise ValidationError(
                            "Early bird price must be less than default price."
                        )
            except Exception as e:
                _logger.error(f"Error validating early bird pricing for {record.id}: {e}")

    @api.constrains('group_discount_enabled', 'group_discount_threshold', 'group_discount_percentage')
    def _validate_group_discount(self):
        """Validate group discount configuration."""
        for record in self:
            try:
                if record.group_discount_enabled:
                    if not record.group_discount_threshold or record.group_discount_threshold <= 1:
                        raise ValidationError(
                            "Group discount threshold must be greater than 1."
                        )
                    if not record.group_discount_percentage or record.group_discount_percentage <= 0:
                        raise ValidationError(
                            "Group discount percentage must be positive."
                        )
                    if record.group_discount_percentage > 50:
                        raise ValidationError(
                            "Group discount percentage cannot exceed 50%."
                        )
            except Exception as e:
                _logger.error(f"Error validating group discount for {record.id}: {e}")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_member_pricing(self, member_type_id=None, member=None, quantity=1, purchase_date=None):
        """Calculate applicable price for member type with enhanced features.
        
        Args:
            member_type_id: ID of member type
            member: res.partner record (alternative to member_type_id)
            quantity: Number of subscriptions (for group discounts)
            purchase_date: Date of purchase (for early bird pricing)
            
        Returns:
            dict: Pricing information
        """
        self.ensure_one()
        
        try:
            if member:
                member_type_id = member.member_type_id.id if member.member_type_id else None
            
            if not purchase_date:
                purchase_date = fields.Date.today()
            
            # Start with default pricing
            base_price = self.default_price
            price_type = 'default'
            discounts_applied = []
            
            # Check for member-specific pricing
            if member_type_id:
                applicable_tier = self.pricing_tier_ids.filtered(
                    lambda t: (
                        t.member_type_id.id == member_type_id and
                        (not t.valid_from or t.valid_from <= purchase_date) and
                        (not t.valid_to or t.valid_to >= purchase_date)
                    )
                )
                
                if applicable_tier:
                    tier = applicable_tier[0]
                    base_price = tier.price
                    price_type = 'member_tier'
                    discounts_applied.append(f"Member discount: {tier.member_type_id.name}")
            
            # Check for early bird pricing
            if (self.early_bird_enabled and 
                self.early_bird_deadline and 
                purchase_date <= self.early_bird_deadline):
                if self.early_bird_price < base_price:
                    base_price = self.early_bird_price
                    price_type = 'early_bird'
                    discounts_applied.append("Early bird pricing")
            
            # Check for group discounts
            final_price = base_price
            if (self.group_discount_enabled and 
                quantity >= self.group_discount_threshold):
                discount_amount = base_price * (self.group_discount_percentage / 100)
                final_price = base_price - discount_amount
                discounts_applied.append(f"Group discount ({quantity} qty): {self.group_discount_percentage}%")
            
            return {
                'unit_price': base_price,
                'final_price': final_price,
                'total_price': final_price * quantity,
                'price_type': price_type,
                'discounts_applied': discounts_applied,
                'currency': self.currency_id.name,
                'quantity': quantity,
                'savings': (base_price - final_price) * quantity if final_price < base_price else 0,
            }
            
        except Exception as e:
            _logger.error(f"Error calculating member pricing for {self.id}: {e}")
            return {
                'unit_price': self.default_price,
                'final_price': self.default_price,
                'total_price': self.default_price * quantity,
                'price_type': 'error_fallback',
                'discounts_applied': [],
                'currency': self.currency_id.name,
                'quantity': quantity,
                'savings': 0,
            }

    def check_professional_eligibility(self, partner):
        """Check professional association specific eligibility."""
        self.ensure_one()
        
        try:
            # Check basic member eligibility first
            basic_eligibility = self.check_member_eligibility(partner)
            if not basic_eligibility[0]:
                return basic_eligibility
            
            # Professional license verification
            if self.verification_type == 'license_check':
                if not hasattr(partner, 'professional_license') or not partner.professional_license:
                    return (False, "Valid professional license required", "license_verification")
            
            # Employer verification
            if self.verification_type == 'employer_verification':
                if not hasattr(partner, 'employer_verified') or not partner.employer_verified:
                    return (False, "Employer verification required", "employer_verification")
            
            # Education credentials verification
            if self.verification_type == 'education_credentials':
                if not hasattr(partner, 'education_verified') or not partner.education_verified:
                    return (False, "Education credential verification required", "education_verification")
            
            # Continuing education verification
            if self.continuing_education_required:
                if not hasattr(partner, 'current_ce_credits'):
                    return (False, "Continuing education credits verification required", "ce_verification")
                if hasattr(partner, 'current_ce_credits') and partner.current_ce_credits < self.ce_credits_per_period:
                    return (False, f"Insufficient CE credits. Required: {self.ce_credits_per_period}, Current: {partner.current_ce_credits}", "ce_insufficient")
            
            return (True, "Eligible for professional subscription", None)
            
        except Exception as e:
            _logger.error(f"Error checking professional eligibility for {self.id}: {e}")
            return (False, "Error checking eligibility", "system_error")

    def check_member_eligibility(self, partner):
        """Check member eligibility for subscription.
        
        Args:
            partner: res.partner record
            
        Returns:
            tuple: (eligible, message, action)
        """
        self.ensure_one()
        
        try:
            if self.member_only:
                if not hasattr(partner, 'is_member') or not partner.is_member:
                    return (False, "Subscription restricted to current members only", "join_or_renew")
            
            if self.requires_approval:
                return (True, "Subject to staff approval", "approval_required")
            
            return (True, "Eligible for immediate purchase", None)
            
        except Exception as e:
            _logger.error(f"Error checking member eligibility for {self.id}: {e}")
            return (False, "Error checking eligibility", "system_error")

    def get_billing_configuration(self):
        """Get billing configuration for subscription lifecycle.
        
        Returns:
            dict: Billing configuration
        """
        self.ensure_one()
        
        try:
            return {
                'duration': self.default_duration,
                'duration_unit': self.duration_unit,
                'is_renewable': self.is_renewable,
                'renewal_window_days': self.renewal_window_days or 0,
                'auto_renewal_enabled': self.auto_renewal_enabled,
                'requires_approval': self.requires_approval,
                'professional_features': {
                    'verification_type': self.verification_type,
                    'ce_required': self.continuing_education_required,
                    'ce_credits_per_period': self.ce_credits_per_period,
                    'professional_insurance': self.professional_insurance_included,
                    'compliance_tracking': self.regulatory_compliance_tracking,
                },
                'enterprise_seats': {
                    'is_enterprise': self.subscription_scope == 'enterprise',
                    'default_seats': self.default_seat_count or 0,
                    'allow_additional': self.allow_seat_purchase,
                    'seat_product_id': self.seat_product_id.id if self.seat_product_id else None,
                }
            }
        except Exception as e:
            _logger.error(f"Error getting billing configuration for {self.id}: {e}")
            return {}

    def create_pricing_tier(self, member_type_id, price, **kwargs):
        """Create a pricing tier for this subscription.
        
        Args:
            member_type_id: ID of member type
            price: Price for this tier
            **kwargs: Additional tier parameters
            
        Returns:
            ams.subscription.pricing.tier: Created tier
        """
        self.ensure_one()
        
        try:
            vals = {
                'subscription_product_id': self.id,
                'member_type_id': member_type_id,
                'price': price,
                'currency_id': self.currency_id.id,
            }
            vals.update(kwargs)
            
            return self.env['ams.subscription.pricing.tier'].create(vals)
        except Exception as e:
            _logger.error(f"Error creating pricing tier for {self.id}: {e}")
            return self.env['ams.subscription.pricing.tier']

    # ==========================================
    # SAMPLE DATA CREATION
    # ==========================================

    @api.model
    def _create_safe_sample_data(self):
        """Safely create sample subscription data for professional associations."""
        try:
            # Check if required models exist
            if not self.env.get('ams.member.type'):
                _logger.info("ams.member.type model not found, skipping professional sample data")
                return
                
            if not self.env.get('product.template'):
                _logger.info("product.template model not found, skipping professional sample data")
                return
            
            # Create professional member types if they don't exist
            professional_member_types = [
                {'name': 'Professional Individual', 'code': 'professional', 'is_individual': True},
                {'name': 'Student Member', 'code': 'student', 'is_individual': True},
                {'name': 'Retired Professional', 'code': 'retired', 'is_individual': True},
                {'name': 'Corporate Member', 'code': 'corporate', 'is_organization': True},
                {'name': 'International Member', 'code': 'international', 'is_individual': True},
            ]
            
            for mt_data in professional_member_types:
                existing = self.env['ams.member.type'].search([('code', '=', mt_data['code'])])
                if not existing:
                    self.env['ams.member.type'].create(mt_data)
                    _logger.info(f"Created member type: {mt_data['name']}")
            
            # Create sample products if they don't exist
            sample_products = [
                {
                    'name': 'Professional Membership',
                    'detailed_type': 'service',
                    'sale_ok': True,
                    'list_price': 299.00,
                    'is_subscription_product': True,
                },
                {
                    'name': 'Student Membership',
                    'detailed_type': 'service',
                    'sale_ok': True,
                    'list_price': 99.00,
                    'is_subscription_product': True,
                },
                {
                    'name': 'Corporate Membership',
                    'detailed_type': 'service',
                    'sale_ok': True,
                    'list_price': 2499.00,
                    'is_subscription_product': True,
                }
            ]
            
            created_products = []
            for product_data in sample_products:
                existing = self.env['product.template'].search([('name', '=', product_data['name'])])
                if not existing:
                    product = self.env['product.template'].create(product_data)
                    created_products.append(product)
                    _logger.info(f"Created sample product: {product_data['name']}")
                else:
                    created_products.append(existing)
            
            # Create sample subscriptions
            subscription_configs = [
                {
                    'name': 'Professional Membership - Annual',
                    'code': 'PROF_ANNUAL_001',
                    'product_id': created_products[0].id,
                    'subscription_scope': 'individual',
                    'product_type': 'membership',
                    'default_duration': 12,
                    'duration_unit': 'months',
                    'default_price': 299.00,
                    'verification_type': 'license_check',
                    'continuing_education_required': True,
                    'ce_credits_per_period': 20,
                    'professional_insurance_included': True,
                },
                {
                    'name': 'Student Membership - Academic Year',
                    'code': 'STUDENT_ANNUAL_001',
                    'product_id': created_products[1].id,
                    'subscription_scope': 'individual',
                    'product_type': 'membership',
                    'default_duration': 9,
                    'duration_unit': 'months',
                    'default_price': 99.00,
                    'verification_type': 'education_credentials',
                    'continuing_education_required': False,
                    'requires_approval': True,
                },
                {
                    'name': 'Corporate Membership - Enterprise',
                    'code': 'CORP_ANNUAL_001',
                    'product_id': created_products[2].id,
                    'subscription_scope': 'enterprise',
                    'product_type': 'membership',
                    'default_duration': 12,
                    'duration_unit': 'months',
                    'default_price': 2499.00,
                    'default_seat_count': 10,
                    'allow_seat_purchase': True,
                    'requires_approval': True,
                }
            ]
            
            for sub_config in subscription_configs:
                existing = self.search([('code', '=', sub_config['code'])])
                if not existing:
                    sub_config['currency_id'] = self.env.company.currency_id.id
                    subscription = self.create(sub_config)
                    _logger.info(f"Created sample subscription: {sub_config['name']}")
                    
                    # Create sample pricing tiers
                    if subscription.subscription_scope == 'individual':
                        self._create_sample_pricing_tiers(subscription)
            
        except Exception as e:
            _logger.error(f"Error creating professional sample data: {e}")

    @api.model
    def _create_sample_pricing_tiers(self, subscription):
        """Create sample pricing tiers for a subscription."""
        try:
            if subscription.product_type == 'membership':
                # Create student pricing tier
                student_type = self.env['ams.member.type'].search([('code', '=', 'student')], limit=1)
                if student_type:
                    student_price = subscription.default_price * 0.33  # 67% discount
                    self.env['ams.subscription.pricing.tier'].create({
                        'subscription_product_id': subscription.id,
                        'member_type_id': student_type.id,
                        'price': student_price,
                        'currency_id': subscription.currency_id.id,
                        'requires_verification': True,
                        'verification_criteria': 'Valid student enrollment verification required.'
                    })
                
                # Create retired pricing tier
                retired_type = self.env['ams.member.type'].search([('code', '=', 'retired')], limit=1)
                if retired_type:
                    retired_price = subscription.default_price * 0.67  # 33% discount
                    self.env['ams.subscription.pricing.tier'].create({
                        'subscription_product_id': subscription.id,
                        'member_type_id': retired_type.id,
                        'price': retired_price,
                        'currency_id': subscription.currency_id.id,
                        'requires_verification': False,
                    })
                    
        except Exception as e:
            _logger.error(f"Error creating sample pricing tiers: {e}")

    # ==========================================
    # DISPLAY AND SEARCH METHODS
    # ==========================================

    def name_get(self):
        """Custom display name with type and scope."""
        result = []
        for record in self:
            try:
                scope_label = dict(record._fields['subscription_scope'].selection)[record.subscription_scope]
                type_label = dict(record._fields['product_type'].selection)[record.product_type]
                
                display_name = f"[{type_label} - {scope_label}] {record.name}"
                result.append((record.id, display_name))
            except Exception as e:
                _logger.warning(f"Error in name_get for record {record.id}: {e}")
                result.append((record.id, record.name or 'Subscription Product'))
        
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including code and product name."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|',
                     ('name', operator, name),
                     ('code', operator, name),
                     ('product_id.name', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and validate."""
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code'):
                if vals.get('product_id'):
                    try:
                        product = self.env['product.template'].browse(vals['product_id'])
                        vals['code'] = self._generate_code_from_product(product)
                    except:
                        vals['code'] = self._generate_sequential_code()
                else:
                    vals['code'] = self._generate_sequential_code()
        
        return super().create(vals_list)

    def _generate_code_from_product(self, product):
        """Generate subscription code from product."""
        try:
            base = product.default_code or f"SUB_{product.id}"
            return self._ensure_unique_code(base)
        except:
            return self._generate_sequential_code()

    def _generate_sequential_code(self):
        """Generate sequential subscription code."""
        try:
            last_sub = self.search([], order='id desc', limit=1)
            next_num = (last_sub.id if last_sub else 0) + 1
            return f"SUB_{next_num:04d}"
        except:
            import time
            return f"SUB_{int(time.time())}"

    def _ensure_unique_code(self, base_code):
        """Ensure code uniqueness."""
        try:
            if not self.search([('code', '=', base_code)]):
                return base_code
            
            counter = 1
            while True:
                candidate = f"{base_code}_{counter}"
                if not self.search([('code', '=', candidate)]):
                    return candidate
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    import time
                    return f"{base_code}_{int(time.time())}"
        except:
            import time
            return f"SUB_{int(time.time())}"

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_manage_pricing_tiers(self):
        """Open pricing tier management."""
        self.ensure_one()
        
        return {
            'name': f'Pricing Tiers - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'list,form',
            'domain': [('subscription_product_id', '=', self.id)],
            'context': {
                'default_subscription_product_id': self.id,
                'default_currency_id': self.currency_id.id,
            }
        }

    def action_view_product(self):
        """View related product."""
        self.ensure_one()
        
        return {
            'name': f'Product - {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_id.id,
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_membership_subscriptions(self):
        """Get all membership-type subscriptions."""
        try:
            return self.search([('product_type', '=', 'membership')])
        except:
            return self.browse()

    @api.model
    def get_enterprise_subscriptions(self):
        """Get all enterprise subscriptions."""
        try:
            return self.search([('subscription_scope', '=', 'enterprise')])
        except:
            return self.browse()

    @api.model
    def get_professional_subscriptions(self):
        """Get all professional association subscriptions."""
        try:
            return self.search([
                ('product_type', 'in', ['membership', 'certification', 'continuing_education']),
                ('verification_type', '!=', 'none')
            ])
        except:
            return self.browse()

    def get_subscription_summary(self):
        """Get comprehensive subscription summary."""
        self.ensure_one()
        
        try:
            return {
                'name': self.name,
                'code': self.code,
                'type': self.product_type,
                'scope': self.subscription_scope,
                'duration': self.duration_display,
                'price': {
                    'default': self.default_price,
                    'currency': self.currency_id.name,
                    'has_tiers': self.has_member_pricing,
                    'min_price': self.min_member_price,
                    'max_price': self.max_member_price,
                    'tier_count': self.pricing_tier_count,
                },
                'features': {
                    'renewable': self.is_renewable,
                    'auto_renewal': self.auto_renewal_enabled,
                    'requires_approval': self.requires_approval,
                    'member_only': self.member_only,
                },
                'professional': {
                    'verification_type': self.verification_type,
                    'ce_required': self.continuing_education_required,
                    'ce_credits': self.ce_credits_per_period,
                    'insurance_included': self.professional_insurance_included,
                    'compliance_tracking': self.regulatory_compliance_tracking,
                },
                'enterprise': {
                    'is_enterprise': self.subscription_scope == 'enterprise',
                    'default_seats': self.default_seat_count,
                    'allow_additional_seats': self.allow_seat_purchase,
                },
                'pricing_enhancements': {
                    'early_bird': self.early_bird_enabled,
                    'group_discounts': self.group_discount_enabled,
                }
            }
        except Exception as e:
            _logger.error(f"Error getting subscription summary for {self.id}: {e}")
            return {'error': str(e)}