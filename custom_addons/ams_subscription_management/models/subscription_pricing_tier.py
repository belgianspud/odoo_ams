from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSSubscriptionPricingTier(models.Model):
    """Member-type specific pricing tiers for subscription products."""
    _name = 'ams.subscription.pricing.tier'
    _description = 'Subscription Pricing Tier'
    _order = 'subscription_product_id, member_type_id, valid_from desc'

    # ==========================================
    # CORE RELATIONSHIP FIELDS
    # ==========================================
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Product',
        required=True,
        ondelete='cascade',
        help='Subscription product this pricing tier applies to'
    )
    
    member_type_id = fields.Many2one(
        'ams.member.type',
        string='Member Type',
        required=True,
        help='Type of member this pricing applies to'
    )

    # ==========================================
    # PRICING FIELDS
    # ==========================================
    
    price = fields.Monetary(
        string='Tier Price',
        required=True,
        currency_field='currency_id',
        help='Special price for this member type'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        related='subscription_product_id.currency_id',
        store=True,
        help='Currency for this pricing tier'
    )
    
    discount_percentage = fields.Float(
        string='Discount Percentage',
        compute='_compute_discount_percentage',
        store=True,
        help='Percentage discount from base price'
    )
    
    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_discount_percentage',
        store=True,
        currency_field='currency_id',
        help='Amount of discount from base price'
    )

    # ==========================================
    # VALIDITY PERIOD FIELDS
    # ==========================================
    
    valid_from = fields.Date(
        string='Valid From',
        help='Date when this pricing becomes effective (empty = immediately)'
    )
    
    valid_to = fields.Date(
        string='Valid To',
        help='Date when this pricing expires (empty = never expires)'
    )
    
    is_promotional = fields.Boolean(
        string='Promotional Pricing',
        compute='_compute_promotional_status',
        store=True,
        help='Whether this is time-limited promotional pricing'
    )

    # ==========================================
    # VERIFICATION & REQUIREMENTS
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Member must provide verification to qualify for this pricing'
    )
    
    verification_criteria = fields.Text(
        string='Verification Requirements',
        help='Description of what verification is needed'
    )
    
    approval_required = fields.Boolean(
        string='Requires Staff Approval',
        default=False,
        help='Staff must approve this pricing tier for member'
    )

    # ==========================================
    # METADATA FIELDS
    # ==========================================
    
    name = fields.Char(
        string='Tier Name',
        compute='_compute_tier_name',
        store=True,
        help='Display name for this pricing tier'
    )
    
    description = fields.Text(
        string='Description',
        help='Additional details about this pricing tier'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order for displaying pricing tiers'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active pricing tiers are available for use'
    )

    # ==========================================
    # STATUS AND INDICATORS
    # ==========================================
    
    is_current = fields.Boolean(
        string='Currently Valid',
        compute='_compute_current_status',
        help='Whether this pricing tier is currently valid'
    )
    
    expires_soon = fields.Boolean(
        string='Expires Soon',
        compute='_compute_current_status',
        help='Whether this pricing tier expires within 30 days'
    )

    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('positive_price', 'CHECK(price >= 0)', 'Price cannot be negative.'),
        ('valid_date_range', 'CHECK(valid_to >= valid_from OR valid_to IS NULL)', 
         'End date must be after start date.'),
        ('unique_member_type_period', 
         'UNIQUE(subscription_product_id, member_type_id, valid_from, valid_to)', 
         'Cannot have overlapping pricing tiers for the same member type.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('price', 'subscription_product_id.default_price')
    def _compute_discount_percentage(self):
        """Calculate discount percentage and amount from base price."""
        for tier in self:
            base_price = tier.subscription_product_id.default_price
            if base_price and base_price > 0:
                tier.discount_amount = base_price - tier.price
                tier.discount_percentage = (tier.discount_amount / base_price) * 100
            else:
                tier.discount_amount = 0.0
                tier.discount_percentage = 0.0

    @api.depends('member_type_id.name', 'price', 'discount_percentage')
    def _compute_tier_name(self):
        """Generate display name for pricing tier."""
        for tier in self:
            if tier.member_type_id:
                if tier.discount_percentage > 0:
                    tier.name = f"{tier.member_type_id.name} ({tier.discount_percentage:.0f}% off)"
                else:
                    tier.name = f"{tier.member_type_id.name} - {tier.price:.2f}"
            else:
                tier.name = f"Tier - {tier.price:.2f}"

    @api.depends('valid_from', 'valid_to')
    def _compute_promotional_status(self):
        """Determine if this is promotional pricing."""
        for tier in self:
            tier.is_promotional = bool(tier.valid_from or tier.valid_to)

    @api.depends('valid_from', 'valid_to')
    def _compute_current_status(self):
        """Compute current validity status."""
        today = fields.Date.today()
        for tier in self:
            # Check if currently valid
            valid_from_ok = not tier.valid_from or tier.valid_from <= today
            valid_to_ok = not tier.valid_to or tier.valid_to >= today
            tier.is_current = valid_from_ok and valid_to_ok
            
            # Check if expires within 30 days
            if tier.valid_to:
                days_until_expiry = (tier.valid_to - today).days
                tier.expires_soon = 0 <= days_until_expiry <= 30
            else:
                tier.expires_soon = False

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('price', 'subscription_product_id')
    def _check_price_logic(self):
        """Validate pricing logic."""
        for tier in self:
            if tier.price < 0:
                raise ValidationError("Pricing tier price cannot be negative")
            
            # Optional: Check that discounted price isn't higher than base price
            base_price = tier.subscription_product_id.default_price
            if base_price > 0 and tier.price > base_price:
                # This might be intentional for premium member types, so just warn
                pass

    @api.constrains('valid_from', 'valid_to', 'subscription_product_id', 'member_type_id')
    def _check_overlapping_tiers(self):
        """Prevent overlapping pricing tiers for the same member type."""
        for tier in self:
            if not tier.subscription_product_id or not tier.member_type_id:
                continue
                
            # Find other tiers for same subscription product and member type
            overlapping_tiers = self.search([
                ('subscription_product_id', '=', tier.subscription_product_id.id),
                ('member_type_id', '=', tier.member_type_id.id),
                ('id', '!=', tier.id),
                ('active', '=', True)
            ])
            
            for other_tier in overlapping_tiers:
                if self._date_ranges_overlap(
                    tier.valid_from, tier.valid_to,
                    other_tier.valid_from, other_tier.valid_to
                ):
                    raise ValidationError(
                        f"Pricing tier for {tier.member_type_id.name} overlaps with existing tier. "
                        "Each member type can only have one active pricing tier at a time."
                    )

    def _date_ranges_overlap(self, start1, end1, start2, end2):
        """Check if two date ranges overlap."""
        from datetime import date
    
        # Use proper constants instead of hardcoded dates
        MIN_DATE = date(1900, 1, 1)
        MAX_DATE = date(2099, 12, 31)
    
        start1 = start1 or MIN_DATE
        end1 = end1 or MAX_DATE  
        start2 = start2 or MIN_DATE
        end2 = end2 or MAX_DATE
    
        return start1 <= end2 and end1 >= start2

    @api.constrains('requires_verification', 'verification_criteria')
    def _check_verification_requirements(self):
        """Validate verification settings."""
        for tier in self:
            if tier.requires_verification and not tier.verification_criteria:
                raise ValidationError(
                    "Verification criteria must be specified when verification is required"
                )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def is_valid_for_date(self, check_date=None):
        """Check if pricing tier is valid for a specific date."""
        self.ensure_one()
        if not check_date:
            check_date = fields.Date.today()
        
        valid_from_ok = not self.valid_from or self.valid_from <= check_date
        valid_to_ok = not self.valid_to or self.valid_to >= check_date
        
        return valid_from_ok and valid_to_ok and self.active

    def get_pricing_summary(self):
        """Get comprehensive pricing tier summary."""
        self.ensure_one()
        
        return {
            'tier_id': self.id,
            'member_type': self.member_type_id.name,
            'price': self.price,
            'currency': self.currency_id.name,
            'discount_percentage': self.discount_percentage,
            'discount_amount': self.discount_amount,
            'is_promotional': self.is_promotional,
            'valid_from': self.valid_from,
            'valid_to': self.valid_to,
            'is_current': self.is_current,
            'expires_soon': self.expires_soon,
            'requires_verification': self.requires_verification,
            'verification_criteria': self.verification_criteria,
            'approval_required': self.approval_required,
        }

    def check_member_eligibility(self, partner_id):
        """Check if member is eligible for this pricing tier."""
        self.ensure_one()
        
        if not partner_id:
            return {'eligible': False, 'reason': 'No member specified'}
        
        partner = self.env['res.partner'].browse(partner_id)
        
        # Check member type match
        if not partner.member_type_id or partner.member_type_id != self.member_type_id:
            return {
                'eligible': False, 
                'reason': f'Member type mismatch. Required: {self.member_type_id.name}'
            }
        
        # Check validity period
        if not self.is_valid_for_date():
            return {
                'eligible': False,
                'reason': 'Pricing tier not currently valid'
            }
        
        # Check verification requirements
        if self.requires_verification:
            # This would integrate with member verification system
            return {
                'eligible': True,
                'requires_verification': True,
                'verification_criteria': self.verification_criteria
            }
        
        # Check approval requirements
        if self.approval_required:
            return {
                'eligible': True,
                'requires_approval': True,
                'reason': 'Staff approval required for this pricing tier'
            }
        
        return {'eligible': True, 'reason': None}

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_activate_tier(self):
        """Activate this pricing tier."""
        self.ensure_one()
        self.active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Pricing Tier Activated',
                'message': f'Pricing tier {self.name} has been activated.',
                'type': 'success',
            }
        }

    def action_deactivate_tier(self):
        """Deactivate this pricing tier."""
        self.ensure_one()
        self.active = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Pricing Tier Deactivated',
                'message': f'Pricing tier {self.name} has been deactivated.',
                'type': 'info',
            }
        }

    def action_duplicate_tier(self):
        """Create a duplicate of this pricing tier."""
        self.ensure_one()
        
        copy_vals = {
            'subscription_product_id': self.subscription_product_id.id,
            'member_type_id': self.member_type_id.id,
            'price': self.price,
            'valid_from': None,  # Clear validity dates for manual setting
            'valid_to': None,
            'description': f"Copy of: {self.description or self.name}",
        }
        
        new_tier = self.copy(copy_vals)
        
        return {
            'name': 'New Pricing Tier',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'form',
            'res_id': new_tier.id,
            'target': 'new',
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_current_pricing_for_product(self, subscription_product_id):
        """Get all current pricing tiers for a subscription product."""
        today = fields.Date.today()
        return self.search([
            ('subscription_product_id', '=', subscription_product_id),
            ('active', '=', True),
            '|', ('valid_from', '<=', today), ('valid_from', '=', False),
            '|', ('valid_to', '>=', today), ('valid_to', '=', False),
        ])

    @api.model
    def get_member_type_pricing(self, subscription_product_id, member_type_id, check_date=None):
        """Get pricing tier for specific member type and date."""
        if not check_date:
            check_date = fields.Date.today()
        
        tier = self.search([
            ('subscription_product_id', '=', subscription_product_id),
            ('member_type_id', '=', member_type_id),
            ('active', '=', True),
            '|', ('valid_from', '<=', check_date), ('valid_from', '=', False),
            '|', ('valid_to', '>=', check_date), ('valid_to', '=', False),
        ], limit=1)
        
        return tier

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    def name_get(self):
        """Custom display name."""
        result = []
        for tier in self:
            if tier.is_promotional:
                promo_indicator = " (PROMO)"
            else:
                promo_indicator = ""
            
            name = f"{tier.member_type_id.name}: {tier.price:.2f}{promo_indicator}"
            result.append((tier.id, name))
        
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including member type name and pricing."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|',
                     ('member_type_id.name', operator, name),
                     ('description', operator, name),
                     ('verification_criteria', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)