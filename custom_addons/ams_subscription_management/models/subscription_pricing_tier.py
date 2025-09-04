from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSSubscriptionPricingTier(models.Model):
    """Member-type specific pricing tiers for subscription products."""
    _name = 'ams.subscription.pricing.tier'
    _description = 'Subscription Pricing Tier'
    _order = 'subscription_product_id, member_type_id, valid_from desc'
    _rec_name = 'display_name'

    # ==========================================
    # CORE RELATIONSHIP FIELDS
    # ==========================================
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Product',
        required=True,
        ondelete='cascade',
        help='Parent subscription product'
    )
    
    member_type_id = fields.Many2one(
        'ams.member.type',
        string='Member Type',
        required=True,
        help='Target member type for this pricing'
    )
    
    # ==========================================
    # PRICING FIELDS
    # ==========================================
    
    price = fields.Monetary(
        string='Price',
        required=True,
        currency_field='currency_id',
        help='Subscription price for this member type'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        help='Currency for this pricing tier'
    )
    
    # ==========================================
    # VALIDITY PERIOD FIELDS
    # ==========================================
    
    valid_from = fields.Date(
        string='Valid From',
        help='Start date for this pricing (leave empty for immediate effect)'
    )
    
    valid_to = fields.Date(
        string='Valid Until',
        help='End date for this pricing (leave empty for indefinite)'
    )
    
    # ==========================================
    # VERIFICATION FIELDS
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        help='Member eligibility must be verified for this pricing'
    )
    
    verification_criteria = fields.Text(
        string='Verification Criteria',
        help='Specific requirements for eligibility verification'
    )
    
    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Formatted display name for this tier'
    )
    
    discount_percentage = fields.Float(
        string='Discount %',
        compute='_compute_discount_percentage',
        store=True,
        help='Percentage discount from default price'
    )
    
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_discount_percentage',
        store=True,
        currency_field='currency_id',
        help='Absolute discount amount from default price'
    )
    
    is_currently_active = fields.Boolean(
        string='Currently Active',
        compute='_compute_is_currently_active',
        help='Whether this pricing tier is currently in effect'
    )
    
    member_type_code = fields.Char(
        related='member_type_id.code',
        string='Member Type Code',
        readonly=True,
        help='Code of the associated member type'
    )
    
    subscription_name = fields.Char(
        related='subscription_product_id.name',
        string='Subscription Name',
        readonly=True,
        help='Name of the parent subscription'
    )
    
    default_subscription_price = fields.Monetary(
        related='subscription_product_id.default_price',
        string='Default Price',
        readonly=True,
        currency_field='currency_id',
        help='Default subscription price for comparison'
    )
    
    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('positive_price', 'CHECK(price >= 0)',
         'Price cannot be negative.'),
        ('valid_date_range', 'CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)',
         'Valid until date must be after valid from date.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('subscription_product_id.name', 'member_type_id.name', 'price')
    def _compute_display_name(self):
        """Generate display name for the pricing tier."""
        for record in self:
            if record.subscription_product_id and record.member_type_id:
                record.display_name = (
                    f"{record.subscription_product_id.name} - "
                    f"{record.member_type_id.name} "
                    f"({record.currency_id.symbol}{record.price})"
                )
            else:
                record.display_name = "Pricing Tier"

    @api.depends('price', 'subscription_product_id.default_price')
    def _compute_discount_percentage(self):
        """Calculate discount percentage and amount."""
        for record in self:
            if (record.subscription_product_id and 
                record.subscription_product_id.default_price > 0):
                
                default_price = record.subscription_product_id.default_price
                discount_amount = default_price - record.price
                discount_percentage = (discount_amount / default_price) * 100
                
                record.discount_amount = discount_amount
                record.discount_percentage = max(0.0, discount_percentage)
            else:
                record.discount_amount = 0.0
                record.discount_percentage = 0.0

    @api.depends('valid_from', 'valid_to')
    def _compute_is_currently_active(self):
        """Check if pricing tier is currently active."""
        today = fields.Date.today()
        
        for record in self:
            is_active = True
            
            if record.valid_from and today < record.valid_from:
                is_active = False
            
            if record.valid_to and today > record.valid_to:
                is_active = False
            
            record.is_currently_active = is_active

    # ==========================================
    # VALIDATION CONSTRAINTS
    # ==========================================

    @api.constrains('subscription_product_id', 'member_type_id', 'valid_from', 'valid_to')
    def _validate_unique_active_pricing(self):
        """Ensure no overlapping active pricing for same member type."""
        for record in self:
            # Build domain to find potentially conflicting records
            domain = [
                ('id', '!=', record.id),
                ('subscription_product_id', '=', record.subscription_product_id.id),
                ('member_type_id', '=', record.member_type_id.id),
            ]
            
            # Check for overlapping date ranges
            overlapping = self.search(domain)
            
            for other in overlapping:
                if self._date_ranges_overlap(
                    record.valid_from, record.valid_to,
                    other.valid_from, other.valid_to
                ):
                    raise ValidationError(
                        f"Overlapping pricing found for {record.member_type_id.name} "
                        f"in subscription {record.subscription_product_id.name}. "
                        f"Date ranges cannot overlap."
                    )

    def _date_ranges_overlap(self, start1, end1, start2, end2):
        """Check if two date ranges overlap."""
        # Convert None to appropriate date values
        start1 = start1 or fields.Date.from_string('1900-01-01')
        end1 = end1 or fields.Date.from_string('2999-12-31')
        start2 = start2 or fields.Date.from_string('1900-01-01')
        end2 = end2 or fields.Date.from_string('2999-12-31')
        
        return not (end1 < start2 or end2 < start1)

    @api.constrains('price', 'subscription_product_id')
    def _validate_price_reasonableness(self):
        """Validate price is reasonable compared to default."""
        for record in self:
            if (record.subscription_product_id and 
                record.subscription_product_id.default_price > 0):
                
                default_price = record.subscription_product_id.default_price
                
                # Check if price is more than 200% of default (likely error)
                if record.price > default_price * 2:
                    raise ValidationError(
                        f"Price {record.price} seems unusually high compared to "
                        f"default price {default_price}. Please verify this is correct."
                    )

    @api.constrains('requires_verification', 'verification_criteria')
    def _validate_verification_criteria(self):
        """Ensure verification criteria is provided when required."""
        for record in self:
            if record.requires_verification and not record.verification_criteria:
                raise ValidationError(
                    f"Verification criteria must be specified when verification "
                    f"is required for {record.member_type_id.name} pricing."
                )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def is_applicable_for_date(self, check_date=None):
        """Check if pricing tier is applicable for given date.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            bool: True if applicable
        """
        self.ensure_one()
        
        if not check_date:
            check_date = fields.Date.today()
        
        if self.valid_from and check_date < self.valid_from:
            return False
        
        if self.valid_to and check_date > self.valid_to:
            return False
        
        return True

    def get_pricing_details(self):
        """Get comprehensive pricing details.
        
        Returns:
            dict: Detailed pricing information
        """
        self.ensure_one()
        
        return {
            'tier_id': self.id,
            'member_type': {
                'id': self.member_type_id.id,
                'name': self.member_type_id.name,
                'code': self.member_type_id.code,
            },
            'pricing': {
                'price': self.price,
                'currency': self.currency_id.name,
                'currency_symbol': self.currency_id.symbol,
                'discount_percentage': self.discount_percentage,
                'discount_amount': self.discount_amount,
            },
            'validity': {
                'valid_from': self.valid_from,
                'valid_to': self.valid_to,
                'is_currently_active': self.is_currently_active,
            },
            'verification': {
                'requires_verification': self.requires_verification,
                'criteria': self.verification_criteria,
            }
        }

    def check_member_eligibility(self, member):
        """Check if member is eligible for this pricing tier.
        
        Args:
            member: res.partner record
            
        Returns:
            tuple: (eligible, reason)
        """
        self.ensure_one()
        
        # Check member type match
        if not member.member_type_id or member.member_type_id.id != self.member_type_id.id:
            return False, f"Member type must be {self.member_type_id.name}"
        
        # Check if pricing is currently active
        if not self.is_currently_active:
            return False, "This pricing is not currently available"
        
        # Check verification requirements
        if self.requires_verification:
            # This would integrate with verification systems in future modules
            return True, f"Subject to verification: {self.verification_criteria}"
        
        return True, "Eligible for this pricing"

    @api.model
    def get_applicable_pricing(self, subscription_product_id, member_type_id, check_date=None):
        """Get applicable pricing for subscription and member type.
        
        Args:
            subscription_product_id: ID of subscription product
            member_type_id: ID of member type
            check_date: Date to check (defaults to today)
            
        Returns:
            recordset: Applicable pricing tier (empty if none)
        """
        if not check_date:
            check_date = fields.Date.today()
        
        domain = [
            ('subscription_product_id', '=', subscription_product_id),
            ('member_type_id', '=', member_type_id),
            '|',
                ('valid_from', '=', False),
                ('valid_from', '<=', check_date),
            '|',
                ('valid_to', '=', False),
                ('valid_to', '>=', check_date),
        ]
        
        # Return most recent if multiple found
        return self.search(domain, order='valid_from desc', limit=1)

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults."""
        for vals in vals_list:
            # Set currency from subscription if not provided
            if not vals.get('currency_id') and vals.get('subscription_product_id'):
                subscription = self.env['ams.subscription.product'].browse(
                    vals['subscription_product_id']
                )
                vals['currency_id'] = subscription.currency_id.id
        
        return super().create(vals_list)

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_subscription(self):
        """View parent subscription product."""
        self.ensure_one()
        
        return {
            'name': f'Subscription - {self.subscription_product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': self.subscription_product_id.id,
        }

    def action_duplicate_tier(self):
        """Duplicate this pricing tier."""
        self.ensure_one()
        
        # Create copy with modified name
        copy_vals = {
            'subscription_product_id': self.subscription_product_id.id,
            'member_type_id': self.member_type_id.id,
            'price': self.price,
            'currency_id': self.currency_id.id,
            'valid_from': False,
            'valid_to': False,
            'requires_verification': self.requires_verification,
            'verification_criteria': self.verification_criteria,
        }
        
        return {
            'name': f'Duplicate Pricing Tier - {self.member_type_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'form',
            'context': {'default_' + k: v for k, v in copy_vals.items()},
            'target': 'new',
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_member_type_pricing_summary(self, member_type_id):
        """Get pricing summary across all subscriptions for a member type.
        
        Args:
            member_type_id: ID of member type
            
        Returns:
            list: Pricing summaries
        """
        tiers = self.search([
            ('member_type_id', '=', member_type_id),
            ('is_currently_active', '=', True),
        ])
        
        return [tier.get_pricing_details() for tier in tiers]

    @api.model
    def get_subscription_pricing_matrix(self, subscription_product_id):
        """Get complete pricing matrix for a subscription.
        
        Args:
            subscription_product_id: ID of subscription product
            
        Returns:
            dict: Pricing matrix by member type
        """
        tiers = self.search([
            ('subscription_product_id', '=', subscription_product_id)
        ])
        
        matrix = {}
        for tier in tiers:
            member_type_name = tier.member_type_id.name
            if member_type_name not in matrix:
                matrix[member_type_name] = []
            matrix[member_type_name].append(tier.get_pricing_details())
        
        return matrix

    def get_discount_display(self):
        """Get formatted discount display text."""
        self.ensure_one()
        
        if self.discount_percentage > 0:
            return f"Save {self.discount_percentage:.0f}% (${self.discount_amount:.2f})"
        elif self.discount_percentage < 0:
            return f"Premium +{abs(self.discount_percentage):.0f}% (+${abs(self.discount_amount):.2f})"
        else:
            return "Standard pricing"

    # ==========================================
    # DISPLAY AND SEARCH METHODS
    # ==========================================

    def name_get(self):
        """Custom display name."""
        result = []
        for record in self:
            if record.member_type_id and record.subscription_product_id:
                name = (f"{record.subscription_product_id.name} - "
                       f"{record.member_type_id.name} "
                       f"({record.currency_id.symbol}{record.price})")
            else:
                name = f"Pricing Tier {record.id}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including subscription and member type names."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|', '|',
                     ('display_name', operator, name),
                     ('subscription_product_id.name', operator, name),
                     ('member_type_id.name', operator, name),
                     ('member_type_id.code', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)