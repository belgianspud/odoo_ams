# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipBenefit(models.Model):
    _name = 'membership.benefit'
    _description = 'Membership Benefit'
    _order = 'category, sequence, name'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Benefit Name',
        required=True,
        translate=True,
        help='Display name for this benefit (e.g., "20% Event Discount", "Free Journal Access")'
    )
    
    code = fields.Char(
        string='Benefit Code',
        required=True,
        help='Unique code for this benefit (e.g., EVENT_DISC_20, JOURNAL_FREE)'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive benefits are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this benefit for members'
    )
    
    short_description = fields.Char(
        string='Short Description',
        translate=True,
        help='Brief one-line description for lists and summaries'
    )
    
    icon = fields.Char(
        string='Icon',
        help='Font Awesome icon class (e.g., fa-star, fa-gift, fa-trophy)'
    )
    
    image = fields.Binary(
        string='Image',
        help='Image to represent this benefit'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # BENEFIT CLASSIFICATION
    # ==========================================
    
    category = fields.Selection([
        ('discount', 'Discounts'),
        ('access', 'Access & Resources'),
        ('publication', 'Publications'),
        ('event', 'Events & Conferences'),
        ('education', 'Education & Training'),
        ('certification', 'Certification'),
        ('networking', 'Networking'),
        ('professional', 'Professional Development'),
        ('recognition', 'Recognition & Awards'),
        ('business', 'Business Services'),
        ('other', 'Other')
    ], string='Benefit Category',
       required=True,
       default='other',
       help='Type of benefit')
    
    benefit_type = fields.Selection([
        ('monetary', 'Monetary Value'),
        ('service', 'Service Access'),
        ('resource', 'Resource Access'),
        ('privilege', 'Privilege/Priority'),
        ('recognition', 'Recognition'),
        ('tangible', 'Tangible Item')
    ], string='Benefit Type',
       default='service',
       required=True,
       help='Nature of the benefit')
    
    is_premium_benefit = fields.Boolean(
        string='Premium Benefit',
        default=False,
        help='This is a premium benefit for higher-tier memberships'
    )
    
    is_highlighted = fields.Boolean(
        string='Highlight Benefit',
        default=False,
        help='Highlight this benefit in marketing materials'
    )

    # ==========================================
    # VALUE & QUANTIFICATION
    # ==========================================
    
    has_monetary_value = fields.Boolean(
        string='Has Monetary Value',
        default=False,
        help='This benefit has a quantifiable monetary value'
    )
    
    monetary_value = fields.Monetary(
        string='Estimated Value',
        default=0.0,
        help='Estimated monetary value of this benefit'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    value_frequency = fields.Selection([
        ('one_time', 'One Time'),
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
        ('per_use', 'Per Use'),
        ('unlimited', 'Unlimited')
    ], string='Value Frequency',
       default='annual',
       help='How often this benefit provides value')
    
    quantifiable_value = fields.Char(
        string='Quantifiable Value',
        help='Quantity description (e.g., "Up to 5 events", "Unlimited downloads")'
    )

    # ==========================================
    # DISCOUNT BENEFITS
    # ==========================================
    
    is_discount = fields.Boolean(
        string='Is Discount',
        compute='_compute_is_discount',
        store=True,
        help='This benefit provides a discount'
    )
    
    discount_percentage = fields.Float(
        string='Discount %',
        default=0.0,
        help='Percentage discount provided'
    )
    
    discount_amount = fields.Monetary(
        string='Discount Amount',
        default=0.0,
        help='Fixed discount amount'
    )
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type',
       help='Type of discount')
    
    discount_applies_to = fields.Selection([
        ('events', 'Event Registrations'),
        ('products', 'Product Purchases'),
        ('certifications', 'Certifications'),
        ('publications', 'Publications'),
        ('all', 'All Purchases')
    ], string='Applies To',
       help='What this discount applies to')

    # ==========================================
    # ACCESS & ELIGIBILITY
    # ==========================================
    
    requires_activation = fields.Boolean(
        string='Requires Activation',
        default=False,
        help='Member must activate this benefit before use'
    )
    
    auto_activate = fields.Boolean(
        string='Auto-Activate',
        default=True,
        help='Automatically activate when membership starts'
    )
    
    requires_opt_in = fields.Boolean(
        string='Requires Opt-In',
        default=False,
        help='Member must opt-in to receive this benefit'
    )
    
    has_usage_limit = fields.Boolean(
        string='Has Usage Limit',
        default=False,
        help='This benefit has a maximum number of uses'
    )
    
    usage_limit = fields.Integer(
        string='Usage Limit',
        default=0,
        help='Maximum times this benefit can be used (0 = unlimited)'
    )
    
    usage_period = fields.Selection([
        ('membership', 'Per Membership Period'),
        ('calendar_year', 'Per Calendar Year'),
        ('month', 'Per Month'),
        ('lifetime', 'Lifetime')
    ], string='Usage Period',
       default='membership',
       help='Time period for usage limit')

    # ==========================================
    # TERMS & CONDITIONS
    # ==========================================
    
    has_terms = fields.Boolean(
        string='Has Terms & Conditions',
        default=False,
        help='This benefit has specific terms and conditions'
    )
    
    terms_and_conditions = fields.Html(
        string='Terms & Conditions',
        translate=True,
        help='Terms and conditions for this benefit'
    )
    
    exclusions = fields.Text(
        string='Exclusions',
        translate=True,
        help='What is excluded from this benefit'
    )
    
    eligibility_requirements = fields.Text(
        string='Eligibility Requirements',
        translate=True,
        help='Special requirements to be eligible for this benefit'
    )

    # ==========================================
    # REDEMPTION & USAGE
    # ==========================================
    
    redemption_method = fields.Selection([
        ('automatic', 'Automatic'),
        ('code', 'Redemption Code'),
        ('request', 'Request/Application'),
        ('portal', 'Portal Self-Service'),
        ('contact_staff', 'Contact Staff')
    ], string='Redemption Method',
       default='automatic',
       help='How members access this benefit')
    
    redemption_instructions = fields.Html(
        string='Redemption Instructions',
        translate=True,
        help='Instructions for redeeming/using this benefit'
    )
    
    redemption_url = fields.Char(
        string='Redemption URL',
        help='URL where members can redeem this benefit'
    )
    
    contact_email = fields.Char(
        string='Contact Email',
        help='Email to contact for this benefit'
    )
    
    contact_phone = fields.Char(
        string='Contact Phone',
        help='Phone number to contact for this benefit'
    )

    # ==========================================
    # PARTNER/VENDOR INFORMATION
    # ==========================================
    
    is_partner_benefit = fields.Boolean(
        string='Partner Benefit',
        default=False,
        help='This benefit is provided by a partner organization'
    )
    
    partner_organization = fields.Char(
        string='Partner Organization',
        help='Organization providing this benefit'
    )
    
    partner_logo = fields.Binary(
        string='Partner Logo',
        help='Logo of partner organization'
    )
    
    partner_url = fields.Char(
        string='Partner URL',
        help='Website of partner organization'
    )

    # ==========================================
    # VALIDITY PERIOD
    # ==========================================
    
    has_validity_period = fields.Boolean(
        string='Has Validity Period',
        default=False,
        help='This benefit is only available during specific dates'
    )
    
    valid_from = fields.Date(
        string='Valid From',
        help='Date when this benefit becomes available'
    )
    
    valid_until = fields.Date(
        string='Valid Until',
        help='Date when this benefit expires'
    )
    
    is_currently_valid = fields.Boolean(
        string='Currently Valid',
        compute='_compute_is_valid',
        help='Benefit is currently within validity period'
    )
    
    seasonal = fields.Boolean(
        string='Seasonal Benefit',
        default=False,
        help='Benefit is only available during certain months'
    )
    
    available_months = fields.Char(
        string='Available Months',
        help='Months when seasonal benefit is available (e.g., "6,7,8" for summer)'
    )

    # ==========================================
    # PRODUCT ASSOCIATIONS
    # ==========================================
    
    product_ids = fields.Many2many(
        'product.template',
        'product_benefit_rel',
        'benefit_id',
        'product_id',
        string='Associated Products',
        help='Membership products that include this benefit'
    )
    
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
        help='Number of products offering this benefit'
    )
    
    category_ids = fields.Many2many(
        'membership.category',
        'category_benefit_rel',
        'benefit_id',
        'category_id',
        string='Associated Categories',
        help='Member categories eligible for this benefit'
    )

    # ==========================================
    # LINKED FEATURE
    # ==========================================
    
    feature_id = fields.Many2one(
        'membership.feature',
        string='Linked Feature',
        help='Technical feature that enables this benefit'
    )

    # ==========================================
    # USAGE TRACKING
    # ==========================================
    
    track_usage = fields.Boolean(
        string='Track Usage',
        default=False,
        help='Track how often this benefit is used'
    )
    
    usage_count = fields.Integer(
        string='Total Usage',
        compute='_compute_usage_stats',
        help='Total times this benefit has been used'
    )
    
    active_users = fields.Integer(
        string='Active Users',
        compute='_compute_usage_stats',
        help='Number of members currently using this benefit'
    )

    # ==========================================
    # MARKETING & DISPLAY
    # ==========================================
    
    display_on_website = fields.Boolean(
        string='Display on Website',
        default=True,
        help='Show this benefit on public website'
    )
    
    display_order = fields.Integer(
        string='Display Order',
        default=10,
        help='Order for displaying on website/marketing materials'
    )
    
    marketing_tagline = fields.Char(
        string='Marketing Tagline',
        translate=True,
        help='Catchy tagline for marketing (e.g., "Save up to $500!")'
    )
    
    call_to_action = fields.Char(
        string='Call to Action',
        translate=True,
        help='CTA text (e.g., "Learn More", "Claim Now")'
    )

    # ==========================================
    # INTERNAL NOTES
    # ==========================================
    
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes about this benefit (not visible to members)'
    )
    
    cost_to_association = fields.Monetary(
        string='Cost to Association',
        default=0.0,
        help='What this benefit costs the association to provide'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('category')
    def _compute_is_discount(self):
        """Check if this is a discount benefit"""
        for benefit in self:
            benefit.is_discount = benefit.category == 'discount'

    @api.depends('valid_from', 'valid_until')
    def _compute_is_valid(self):
        """Check if benefit is currently valid"""
        today = fields.Date.today()
        for benefit in self:
            is_valid = True
            
            if benefit.has_validity_period:
                if benefit.valid_from and today < benefit.valid_from:
                    is_valid = False
                
                if benefit.valid_until and today > benefit.valid_until:
                    is_valid = False
            
            benefit.is_currently_valid = is_valid

    @api.depends('product_ids')
    def _compute_product_count(self):
        """Count associated products"""
        for benefit in self:
            benefit.product_count = len(benefit.product_ids)

    def _compute_usage_stats(self):
        """Calculate usage statistics"""
        for benefit in self:
            if benefit.track_usage:
                # This would integrate with a usage tracking system
                # For now, set to 0
                benefit.usage_count = 0
                benefit.active_users = 0
            else:
                benefit.usage_count = 0
                benefit.active_users = 0

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def check_eligibility(self, partner_id, date=None):
        """
        Check if a partner is eligible for this benefit
        
        Args:
            partner_id: res.partner record or ID
            date: Date to check (defaults to today)
        
        Returns:
            tuple: (bool: is_eligible, str: reason if not eligible)
        """
        self.ensure_one()
        
        if date is None:
            date = fields.Date.today()
        
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        # Check validity period
        if self.has_validity_period:
            if self.valid_from and date < self.valid_from:
                return (False, _("Benefit not available until %s") % self.valid_from)
            
            if self.valid_until and date > self.valid_until:
                return (False, _("Benefit expired on %s") % self.valid_until)
        
        # Check seasonal availability
        if self.seasonal and self.available_months:
            current_month = str(date.month)
            if current_month not in self.available_months.split(','):
                return (False, _("Benefit not available this month"))
        
        # Check if partner has subscription with this benefit
        has_benefit = bool(
            partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active'] and 
                         self in s.product_id.benefit_ids
            )
        )
        
        if not has_benefit:
            return (False, _("Your membership does not include this benefit"))
        
        # Check category restrictions
        if self.category_ids:
            if partner.membership_category_id not in self.category_ids:
                return (False, _("Your member category is not eligible for this benefit"))
        
        return (True, '')

    def action_view_products(self):
        """View products that include this benefit"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products with Benefit: %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    @api.model
    def get_benefit_by_code(self, code):
        """
        Get benefit by code (helper method)
        
        Args:
            code: Benefit code
        
        Returns:
            membership.benefit record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def get_member_value(self, partner_id):
        """
        Calculate the value of this benefit for a specific member
        
        Args:
            partner_id: res.partner record or ID
        
        Returns:
            float: Monetary value
        """
        self.ensure_one()
        
        if not self.has_monetary_value:
            return 0.0
        
        value = self.monetary_value
        
        # Adjust based on usage frequency
        if self.value_frequency == 'monthly':
            value = value * 12
        elif self.value_frequency == 'per_use' and self.usage_limit > 0:
            value = value * self.usage_limit
        
        return value

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"{name} [{record.code}]"
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure benefit code is unique"""
        for benefit in self:
            if self.search_count([
                ('code', '=', benefit.code),
                ('id', '!=', benefit.id)
            ]) > 0:
                raise ValidationError(_("Benefit code must be unique. '%s' is already used.") % benefit.code)

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for benefit in self:
            if benefit.discount_percentage < 0 or benefit.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    @api.constrains('usage_limit')
    def _check_usage_limit(self):
        """Validate usage limit"""
        for benefit in self:
            if benefit.has_usage_limit and benefit.usage_limit < 1:
                raise ValidationError(_("Usage limit must be at least 1 if limit is enabled."))

    @api.constrains('valid_from', 'valid_until')
    def _check_validity_dates(self):
        """Validate validity dates"""
        for benefit in self:
            if benefit.has_validity_period and benefit.valid_from and benefit.valid_until:
                if benefit.valid_until < benefit.valid_from:
                    raise ValidationError(_("Valid until date must be after valid from date."))

    @api.constrains('monetary_value', 'cost_to_association')
    def _check_monetary_values(self):
        """Validate monetary values"""
        for benefit in self:
            if benefit.monetary_value < 0:
                raise ValidationError(_("Monetary value cannot be negative."))
            
            if benefit.cost_to_association < 0:
                raise ValidationError(_("Cost to association cannot be negative."))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Benefit code must be unique!'),
    ]