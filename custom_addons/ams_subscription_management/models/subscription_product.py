from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date


class AMSSubscriptionProduct(models.Model):
    """Core subscription product definitions with sophisticated configuration."""
    _name = 'ams.subscription.product'
    _description = 'Subscription Product Definition'
    _order = 'subscription_scope, product_type, name'

    # ==========================================
    # CORE IDENTIFICATION
    # ==========================================
    
    name = fields.Char(
        string='Product Name',
        required=True,
        help='Subscription product name'
    )
    
    code = fields.Char(
        string='Unique Code',
        required=True,
        help='Unique identifier for this subscription product'
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Base Product',
        required=True,
        ondelete='cascade',
        help='Related Odoo product template'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active subscription products are available for purchase'
    )

    # ==========================================
    # SUBSCRIPTION CLASSIFICATION
    # ==========================================
    
    subscription_scope = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('enterprise', 'Enterprise Subscription')
    ], string='Subscription Scope', required=True, default='individual',
       help='Individual for single users, Enterprise for organizations')
    
    product_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('committee', 'Committee'),
        ('publication', 'Publication')
    ], string='Product Type', required=True, default='membership',
       help='Subscription category for business logic and pricing')

    # ==========================================
    # DURATION & LIFECYCLE
    # ==========================================
    
    default_duration = fields.Integer(
        string='Default Duration',
        required=True,
        default=12,
        help='Standard subscription length'
    )
    
    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Duration Unit', required=True, default='months')
    
    is_renewable = fields.Boolean(
        string='Renewable',
        default=True,
        help='Subscription can be renewed before expiration'
    )
    
    renewal_window_days = fields.Integer(
        string='Renewal Window (Days)',
        default=90,
        help='Days before expiration when renewal is available'
    )
    
    auto_renewal_enabled = fields.Boolean(
        string='Auto-Renewal Available',
        default=False,
        help='Subscription supports automatic renewal'
    )

    # ==========================================
    # PRICING STRUCTURE
    # ==========================================
    
    default_price = fields.Monetary(
        string='Base Price',
        required=True,
        currency_field='currency_id',
        help='Standard subscription price'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Subscription currency'
    )
    
    pricing_tier_ids = fields.One2many(
        'ams.subscription.pricing.tier',
        'subscription_product_id',
        string='Member Pricing Tiers',
        help='Special pricing for different member types'
    )
    
    pricing_tier_count = fields.Integer(
        string='Pricing Tiers',
        compute='_compute_pricing_stats',
        store=True,
        help='Number of member-type pricing tiers'
    )

    # ==========================================
    # ENTERPRISE SUBSCRIPTION FEATURES
    # ==========================================
    
    default_seat_count = fields.Integer(
        string='Default Seats',
        help='Default number of seats for enterprise subscriptions'
    )
    
    allow_seat_purchase = fields.Boolean(
        string='Allow Additional Seats',
        default=False,
        help='Enterprise customers can purchase additional seats'
    )
    
    max_additional_seats = fields.Integer(
        string='Maximum Additional Seats',
        default=0,
        help='Maximum extra seats that can be purchased (0 = unlimited)'
    )
    
    seat_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Additional Seat Product',
        help='Product used for additional seat purchases'
    )

    # ==========================================
    # ACCESS CONTROL & APPROVAL
    # ==========================================
    
    requires_approval = fields.Boolean(
        string='Requires Staff Approval',
        default=False,
        help='Subscription purchases require staff approval'
    )
    
    member_only = fields.Boolean(
        string='Members Only',
        default=False,
        help='Subscription restricted to current association members'
    )
    
    eligible_member_types = fields.Many2many(
        'ams.member.type',
        string='Eligible Member Types',
        help='Specific member types allowed to purchase (empty = all types)'
    )

    # ==========================================
    # CONTENT & MARKETING
    # ==========================================
    
    description = fields.Html(
        string='Description',
        help='Detailed subscription description'
    )
    
    benefits_description = fields.Html(
        string='Member Benefits',
        help='Description of benefits included with subscription'
    )
    
    terms_and_conditions = fields.Html(
        string='Terms & Conditions',
        help='Subscription-specific terms and conditions'
    )

    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    total_pricing_tiers = fields.Integer(
        string='Total Pricing Tiers',
        compute='_compute_pricing_stats',
        store=True
    )
    
    has_member_pricing = fields.Boolean(
        string='Has Member Pricing',
        compute='_compute_pricing_stats', 
        store=True,
        help='Subscription has member-specific pricing tiers'
    )
    
    lowest_price = fields.Monetary(
        string='Lowest Price',
        compute='_compute_pricing_stats',
        store=True,
        currency_field='currency_id',
        help='Lowest available price across all tiers'
    )
    
    highest_discount_percentage = fields.Float(
        string='Max Discount %',
        compute='_compute_pricing_stats',
        store=True,
        help='Highest discount percentage available'
    )

    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Subscription product code must be unique.'),
        ('positive_price', 'CHECK(default_price >= 0)', 'Price cannot be negative.'),
        ('positive_duration', 'CHECK(default_duration > 0)', 'Duration must be positive.'),
        ('valid_renewal_window', 'CHECK(renewal_window_days >= 0)', 'Renewal window cannot be negative.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('pricing_tier_ids', 'pricing_tier_ids.price', 'default_price')
    def _compute_pricing_stats(self):
        """Compute pricing statistics and indicators."""
        for subscription in self:
            tiers = subscription.pricing_tier_ids
            
            subscription.pricing_tier_count = len(tiers)
            subscription.total_pricing_tiers = len(tiers)
            subscription.has_member_pricing = len(tiers) > 0
            
            if tiers:
                prices = [subscription.default_price] + list(tiers.mapped('price'))
                subscription.lowest_price = min(prices)
                
                # Calculate highest discount
                discounts = []
                for tier in tiers:
                    if subscription.default_price > 0:
                        discount = ((subscription.default_price - tier.price) / 
                                   subscription.default_price * 100)
                        discounts.append(discount)
                
                subscription.highest_discount_percentage = max(discounts) if discounts else 0.0
            else:
                subscription.lowest_price = subscription.default_price
                subscription.highest_discount_percentage = 0.0

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('subscription_scope', 'default_seat_count')
    def _check_enterprise_configuration(self):
        """Validate enterprise subscription settings."""
        for subscription in self:
            if subscription.subscription_scope == 'enterprise':
                if not subscription.default_seat_count or subscription.default_seat_count < 1:
                    raise ValidationError(
                        "Enterprise subscriptions must have a default seat count of at least 1."
                    )

    @api.constrains('seat_product_id')
    def _check_seat_product_recursion(self):
        """Prevent recursive seat product references."""
        for subscription in self:
            if subscription.seat_product_id:
                if subscription.seat_product_id.id == subscription.id:
                    raise ValidationError("Subscription cannot reference itself as seat product.")

    @api.constrains('renewal_window_days', 'default_duration', 'duration_unit')
    def _check_renewal_window_logic(self):
        """Validate renewal window makes sense."""
        for subscription in self:
            if subscription.renewal_window_days and subscription.is_renewable:
                # Convert duration to days for comparison
                duration_days = subscription._convert_duration_to_days()
                
                if subscription.renewal_window_days > duration_days:
                    raise ValidationError(
                        f"Renewal window ({subscription.renewal_window_days} days) cannot be longer than "
                        f"subscription duration ({duration_days} days)."
                    )

    @api.constrains('max_additional_seats')
    def _check_additional_seats_logic(self):
        """Validate additional seats configuration."""
        for subscription in self:
            if subscription.allow_seat_purchase and subscription.max_additional_seats < 0:
                raise ValidationError("Maximum additional seats cannot be negative.")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_member_pricing(self, member_type_id=None, member=None):
        """Get applicable pricing for specific member type."""
        self.ensure_one()
        
        if member and not member_type_id:
            member_type_id = member.member_type_id.id
        
        if not member_type_id:
            return {
                'price': self.default_price,
                'currency': self.currency_id.name,
                'discount_percentage': 0.0,
                'tier_name': 'Standard',
                'requires_verification': False
            }
        
        # Find applicable pricing tier
        today = fields.Date.today()
        applicable_tier = self.pricing_tier_ids.filtered(
            lambda t: (
                t.member_type_id.id == member_type_id and
                (not t.valid_from or t.valid_from <= today) and
                (not t.valid_to or t.valid_to >= today)
            )
        )
        
        if applicable_tier:
            tier = applicable_tier[0]  # Take first if multiple
            discount_pct = 0.0
            if self.default_price > 0:
                discount_pct = ((self.default_price - tier.price) / self.default_price) * 100
            
            return {
                'price': tier.price,
                'currency': self.currency_id.name,
                'discount_percentage': discount_pct,
                'tier_name': tier.member_type_id.name,
                'requires_verification': tier.requires_verification,
                'tier_id': tier.id
            }
        
        return {
            'price': self.default_price,
            'currency': self.currency_id.name,
            'discount_percentage': 0.0,
            'tier_name': 'Standard',
            'requires_verification': False
        }

    def check_member_eligibility(self, partner_id):
        """Check if member is eligible for this subscription."""
        self.ensure_one()
        
        if not partner_id:
            return {'eligible': False, 'reason': 'No member specified', 'action': None}
        
        partner = self.env['res.partner'].browse(partner_id)
        
        # Check if partner exists
        if not partner.exists():
            return {'eligible': False, 'reason': 'Member not found', 'action': None}
        
        # Check membership requirement
        if self.member_only and not partner.is_member:
            return {
                'eligible': False,
                'reason': 'Subscription restricted to current members only',
                'action': 'join_or_renew'
            }
        
        # Check specific member type restrictions
        if self.eligible_member_types:
            if not partner.member_type_id or partner.member_type_id not in self.eligible_member_types:
                allowed_types = ', '.join(self.eligible_member_types.mapped('name'))
                return {
                    'eligible': False,
                    'reason': f'Subscription only available for: {allowed_types}',
                    'action': 'contact_support'
                }
        
        # Check enterprise vs individual scope
        if self.subscription_scope == 'enterprise' and not partner.is_company:
            return {
                'eligible': False,
                'reason': 'Enterprise subscription requires organization account',
                'action': 'create_organization'
            }
        
        if self.subscription_scope == 'individual' and partner.is_company:
            return {
                'eligible': False,
                'reason': 'Individual subscription not available for organizations',
                'action': 'view_enterprise_options'
            }
        
        # All checks passed
        return {'eligible': True, 'reason': None, 'action': None}

    def calculate_enterprise_pricing(self, total_seats):
        """Calculate pricing for enterprise subscription with specific seat count."""
        self.ensure_one()
        
        if self.subscription_scope != 'enterprise':
            raise ValidationError("Not an enterprise subscription")
        
        if total_seats < 1:
            raise ValidationError("Seat count must be at least 1")
        
        base_price = self.default_price
        additional_seats = 0
        additional_seat_price = 0.0
        
        if total_seats > self.default_seat_count:
            additional_seats = total_seats - self.default_seat_count
            
            # Check maximum seat limit
            if (self.max_additional_seats > 0 and 
                additional_seats > self.max_additional_seats):
                raise ValidationError(
                    f"Maximum {self.max_additional_seats} additional seats allowed"
                )
            
            # Calculate additional seat pricing
            if self.seat_product_id:
                additional_seat_price = self.seat_product_id.default_price * additional_seats
            else:
                # Fallback calculation if no seat product defined
                seat_price = base_price / self.default_seat_count if self.default_seat_count > 0 else 0
                additional_seat_price = seat_price * additional_seats
        
        total_price = base_price + additional_seat_price
        
        return {
            'base_price': base_price,
            'base_seats': self.default_seat_count,
            'additional_seats': additional_seats,
            'additional_seat_price': additional_seat_price,
            'total_price': total_price,
            'total_seats': total_seats,
            'currency': self.currency_id.name,
            'price_per_seat': total_price / total_seats if total_seats > 0 else 0
        }

    def get_billing_configuration(self):
        """Get billing configuration for other modules."""
        self.ensure_one()
        
        return {
            'duration': self.default_duration,
            'duration_unit': self.duration_unit,
            'renewable': self.is_renewable,
            'renewal_window_days': self.renewal_window_days,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'requires_approval': self.requires_approval,
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def _convert_duration_to_days(self):
        """Convert subscription duration to days for calculations."""
        self.ensure_one()
        # FIXED: Imports moved to top of file
        start_date = date.today()
    
        if self.duration_unit == 'days':
            return self.default_duration
        elif self.duration_unit == 'months':
            end_date = start_date + relativedelta(months=self.default_duration)
            return (end_date - start_date).days
        elif self.duration_unit == 'years':
            end_date = start_date + relativedelta(years=self.default_duration)
            return (end_date - start_date).days
        else:
            return 365  # Default fallback

    def get_duration_display(self):
        """Get human-readable duration display."""
        self.ensure_one()
        
        unit_map = {
            'days': 'day' if self.default_duration == 1 else 'days',
            'months': 'month' if self.default_duration == 1 else 'months',
            'years': 'year' if self.default_duration == 1 else 'years'
        }
        
        unit_display = unit_map.get(self.duration_unit, self.duration_unit)
        return f"{self.default_duration} {unit_display}"

    def get_subscription_summary(self):
        """Get comprehensive subscription summary."""
        self.ensure_one()
        
        return {
            'name': self.name,
            'code': self.code,
            'scope': self.subscription_scope,
            'type': self.product_type,
            'duration': self.get_duration_display(),
            'base_price': self.default_price,
            'currency': self.currency_id.name,
            'renewable': self.is_renewable,
            'auto_renewal': self.auto_renewal_enabled,
            'member_only': self.member_only,
            'requires_approval': self.requires_approval,
            'has_member_pricing': self.has_member_pricing,
            'pricing_tiers': self.pricing_tier_count,
            'lowest_price': self.lowest_price,
            'max_discount': self.highest_discount_percentage,
            'enterprise_features': {
                'default_seats': self.default_seat_count,
                'allow_additional_seats': self.allow_seat_purchase,
                'max_additional_seats': self.max_additional_seats
            } if self.subscription_scope == 'enterprise' else None
        }

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and validate."""
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code'):
                product_id = vals.get('product_id')
                if product_id:
                    product = self.env['product.template'].browse(product_id)
                    vals['code'] = f"SUB_{product.default_code or product.id}"
                else:
                    vals['code'] = f"SUB_{self.env['ir.sequence'].next_by_code('ams.subscription.product') or 'NEW'}"
            
            # Set enterprise defaults
            if vals.get('subscription_scope') == 'enterprise' and not vals.get('default_seat_count'):
                vals['default_seat_count'] = 5  # Conservative default
        
        return super().create(vals_list)

    def name_get(self):
        """Custom display name with scope and type indicators."""
        result = []
        for record in self:
            scope_indicator = "🏢" if record.subscription_scope == 'enterprise' else "👤"
            type_map = {
                'membership': 'Membership',
                'chapter': 'Chapter',
                'committee': 'Committee',
                'publication': 'Publication'
            }
            type_display = type_map.get(record.product_type, record.product_type.title())
            
            name = f"{scope_indicator} {record.name} ({type_display})"
            result.append((record.id, name))
        
        return result

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_pricing_tiers(self):
        """View pricing tiers for this subscription."""
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
            },
        }

    def action_create_pricing_tier(self):
        """Create new pricing tier."""
        self.ensure_one()
        
        return {
            'name': f'New Pricing Tier - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_product_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_price': self.default_price * 0.8,  # 20% discount default
            },
        }

    def action_duplicate_subscription(self):
        """Duplicate subscription product with modifications."""
        self.ensure_one()
        
        copy_vals = {
            'name': f"{self.name} (Copy)",
            'code': f"{self.code}_COPY",
        }
        
        new_subscription = self.copy(copy_vals)
        
        return {
            'name': f'Configure Copy - {new_subscription.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': new_subscription.id,
        }