from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSSubscriptionProduct(models.Model):
    """Core subscription product definition with member-type pricing."""
    _name = 'ams.subscription.product'
    _description = 'Subscription Product Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Added for messaging support
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
        ('publication', 'Publication')
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
        """Compute number of pricing tiers."""
        for record in self:
            record.pricing_tier_count = len(record.pricing_tier_ids)

    @api.depends('default_duration', 'duration_unit')
    def _compute_duration_display(self):
        """Generate human-readable duration display."""
        for record in self:
            if record.default_duration and record.duration_unit:
                unit_name = dict(record._fields['duration_unit'].selection)[record.duration_unit]
                if record.default_duration == 1:
                    # Singular form
                    unit_name = unit_name.rstrip('s')
                record.duration_display = f"{record.default_duration} {unit_name}"
            else:
                record.duration_display = "Not configured"

    @api.depends('pricing_tier_ids.price')
    def _compute_has_member_pricing(self):
        """Check if subscription has member-specific pricing."""
        for record in self:
            record.has_member_pricing = bool(record.pricing_tier_ids)

    @api.depends('pricing_tier_ids.price')
    def _compute_price_range(self):
        """Compute price range across member tiers."""
        for record in self:
            if record.pricing_tier_ids:
                prices = record.pricing_tier_ids.mapped('price')
                record.min_member_price = min(prices) if prices else 0.0
                record.max_member_price = max(prices) if prices else 0.0
            else:
                record.min_member_price = record.default_price
                record.max_member_price = record.default_price

    # ==========================================
    # VALIDATION CONSTRAINTS
    # ==========================================

    @api.constrains('subscription_scope', 'default_seat_count')
    def _validate_enterprise_configuration(self):
        """Validate enterprise subscription settings."""
        for record in self:
            if record.subscription_scope == 'enterprise':
                if not record.default_seat_count or record.default_seat_count < 1:
                    raise ValidationError(
                        f"Enterprise subscription '{record.name}' requires "
                        f"default seat count of at least 1."
                    )

    @api.constrains('seat_product_id')
    def _validate_seat_product(self):
        """Validate additional seat product configuration."""
        for record in self:
            if record.seat_product_id:
                if record.seat_product_id.id == record.id:
                    raise ValidationError(
                        "Subscription cannot reference itself as seat product."
                    )
                if record.seat_product_id.subscription_scope != 'individual':
                    raise ValidationError(
                        "Additional seat product must be individual scope."
                    )

    @api.constrains('renewal_window_days')
    def _validate_renewal_window(self):
        """Validate renewal window settings."""
        for record in self:
            if record.is_renewable and record.renewal_window_days:
                if record.renewal_window_days < 0:
                    raise ValidationError(
                        "Renewal window cannot be negative."
                    )
                if record.renewal_window_days > 365:
                    raise ValidationError(
                        "Renewal window cannot exceed 365 days."
                    )

    @api.constrains('pricing_tier_ids')
    def _validate_pricing_tiers(self):
        """Validate pricing tier consistency."""
        for record in self:
            if record.pricing_tier_ids:
                # Check for duplicate member types
                member_types = record.pricing_tier_ids.mapped('member_type_id.id')
                if len(member_types) != len(set(member_types)):
                    raise ValidationError(
                        f"Subscription '{record.name}' has duplicate pricing "
                        f"for the same member type."
                    )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_member_pricing(self, member_type_id=None, member=None):
        """Calculate applicable price for member type.
        
        Args:
            member_type_id: ID of member type
            member: res.partner record (alternative to member_type_id)
            
        Returns:
            dict: Pricing information
        """
        self.ensure_one()
        
        if member:
            member_type_id = member.member_type_id.id if member.member_type_id else None
        
        if not member_type_id:
            return {
                'price': self.default_price,
                'currency': self.currency_id.name,
                'discount_percentage': 0.0,
                'price_type': 'default'
            }
        
        # Find applicable pricing tier
        applicable_tier = self.pricing_tier_ids.filtered(
            lambda t: (
                t.member_type_id.id == member_type_id and
                (not t.valid_from or t.valid_from <= fields.Date.today()) and
                (not t.valid_to or t.valid_to >= fields.Date.today())
            )
        )
        
        if applicable_tier:
            tier = applicable_tier[0]  # Take first if multiple
            discount = 0.0
            if self.default_price > 0:
                discount = ((self.default_price - tier.price) / self.default_price) * 100
            
            return {
                'price': tier.price,
                'currency': self.currency_id.name,
                'discount_percentage': max(0.0, discount),
                'price_type': 'member_tier',
                'member_type': tier.member_type_id.name,
                'requires_verification': tier.requires_verification
            }
        
        return {
            'price': self.default_price,
            'currency': self.currency_id.name,
            'discount_percentage': 0.0,
            'price_type': 'default'
        }

    def check_member_eligibility(self, member):
        """Check member eligibility for subscription.
        
        Args:
            member: res.partner record
            
        Returns:
            tuple: (eligible, message)
        """
        self.ensure_one()
        
        if self.member_only:
            if not hasattr(member, 'is_member') or not member.is_member:
                return False, "Subscription restricted to current members only"
        
        if self.requires_approval:
            return True, "Subject to staff approval"
        
        return True, "Eligible for immediate purchase"

    def get_billing_configuration(self):
        """Get billing configuration for subscription lifecycle.
        
        Returns:
            dict: Billing configuration
        """
        self.ensure_one()
        
        return {
            'duration': self.default_duration,
            'duration_unit': self.duration_unit,
            'is_renewable': self.is_renewable,
            'renewal_window_days': self.renewal_window_days or 0,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'requires_approval': self.requires_approval,
            'enterprise_seats': {
                'is_enterprise': self.subscription_scope == 'enterprise',
                'default_seats': self.default_seat_count or 0,
                'allow_additional': self.allow_seat_purchase,
                'seat_product_id': self.seat_product_id.id if self.seat_product_id else None,
            }
        }

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
        
        vals = {
            'subscription_product_id': self.id,
            'member_type_id': member_type_id,
            'price': price,
            'currency_id': self.currency_id.id,
        }
        vals.update(kwargs)
        
        return self.env['ams.subscription.pricing.tier'].create(vals)

    # ==========================================
    # DISPLAY AND SEARCH METHODS
    # ==========================================

    def name_get(self):
        """Custom display name with type and scope."""
        result = []
        for record in self:
            scope_label = dict(record._fields['subscription_scope'].selection)[record.subscription_scope]
            type_label = dict(record._fields['product_type'].selection)[record.product_type]
            
            display_name = f"[{type_label} - {scope_label}] {record.name}"
            result.append((record.id, display_name))
        
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
                    product = self.env['product.template'].browse(vals['product_id'])
                    vals['code'] = self._generate_code_from_product(product)
                else:
                    vals['code'] = self._generate_sequential_code()
        
        return super().create(vals_list)

    def _generate_code_from_product(self, product):
        """Generate subscription code from product."""
        base = product.default_code or f"SUB_{product.id}"
        return self._ensure_unique_code(base)

    def _generate_sequential_code(self):
        """Generate sequential subscription code."""
        last_sub = self.search([], order='id desc', limit=1)
        next_num = (last_sub.id if last_sub else 0) + 1
        return f"SUB_{next_num:04d}"

    def _ensure_unique_code(self, base_code):
        """Ensure code uniqueness."""
        if not self.search([('code', '=', base_code)]):
            return base_code
        
        counter = 1
        while True:
            candidate = f"{base_code}_{counter}"
            if not self.search([('code', '=', candidate)]):
                return candidate
            counter += 1

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
            'view_mode': 'tree,form',
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
        return self.search([('product_type', '=', 'membership')])

    @api.model
    def get_enterprise_subscriptions(self):
        """Get all enterprise subscriptions."""
        return self.search([('subscription_scope', '=', 'enterprise')])

    def get_subscription_summary(self):
        """Get comprehensive subscription summary."""
        self.ensure_one()
        
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
            'enterprise': {
                'is_enterprise': self.subscription_scope == 'enterprise',
                'default_seats': self.default_seat_count,
                'allow_additional_seats': self.allow_seat_purchase,
            }
        }