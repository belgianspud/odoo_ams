# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ==========================================
    # MEMBERSHIP PRODUCT FLAG
    # Extends subscription products with membership features
    # ==========================================
    
    is_membership_product = fields.Boolean(
        string='Is Membership Product',
        default=False,
        help="Check this if this product represents a membership. "
             "Works with subscription features for billing and renewal."
    )

    # ==========================================
    # MEMBERSHIP YEAR CONFIGURATION
    # Calendar vs Anniversary - key membership concept
    # ==========================================
    
    membership_year_type = fields.Selection([
        ('calendar', 'Calendar Year'),
        ('anniversary', 'Anniversary Year')
    ], string='Membership Year Type',
       default='anniversary',
       help="Calendar: Membership runs Jan 1 - Dec 31 regardless of join date\n"
            "Anniversary: Membership runs 12 months from member's start date")
    
    calendar_year_start = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Calendar Year Start',
       default='1',
       help='For calendar year memberships, which month starts the year')
    
    prorate_partial_periods = fields.Boolean(
        string='Prorate Partial Periods',
        default=True,
        help='For calendar year: Prorate price if joining mid-year'
    )

    # ==========================================
    # MEMBER CATEGORY RESTRICTIONS
    # Who can purchase this membership
    # ==========================================
    
    allowed_member_categories = fields.Many2many(
        'membership.category',
        'product_membership_category_rel',
        'product_id',
        'category_id',
        string='Allowed Member Categories',
        help="Which member categories can purchase this membership. "
             "Leave empty to allow all categories."
    )
    
    default_member_category_id = fields.Many2one(
        'membership.category',
        string='Default Member Category',
        help='Default category when creating membership with this product'
    )

    # ==========================================
    # MEMBERSHIP BENEFITS & FEATURES
    # What members get with this membership
    # ==========================================
    
    benefit_ids = fields.Many2many(
        'membership.benefit',
        'product_benefit_rel',
        'product_id',
        'benefit_id',
        string='Benefits',
        help="Benefits included with this membership"
    )
    
    feature_ids = fields.Many2many(
        'membership.feature',
        'product_feature_rel',
        'product_id',
        'feature_id',
        string='Features',
        help="Features included with this membership"
    )
    
    membership_description_html = fields.Html(
        string='Membership Description',
        help="Rich text description for member portal and website"
    )

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP
    # Settings for corporate/organizational memberships
    # ==========================================
    
    is_organizational_only = fields.Boolean(
        string='Organizational Only',
        default=False,
        help="Only available to organizational/corporate members"
    )
    
    supports_seats = fields.Boolean(
        string='Supports Seat Allocation',
        default=False,
        help="This membership can have seats assigned to employees. "
             "Uses subscription_management seat features."
    )
    
    min_seats_required = fields.Integer(
        string='Minimum Seats Required',
        default=1,
        help="Minimum number of seats for organizational memberships"
    )
    
    seat_product_id = fields.Many2one(
        'product.template',
        string='Seat Product',
        domain=[('subscription_product_type', '=', 'seat')],
        help="Product used for individual seats in this org membership"
    )

    # ==========================================
    # CHAPTER MEMBERSHIP
    # For chapter/section memberships
    # ==========================================
    
    is_chapter_membership = fields.Boolean(
        string='Is Chapter Membership',
        compute='_compute_is_chapter_membership',
        store=True,
        help="This is a chapter membership product"
    )
    
    chapter_ids = fields.Many2many(
        'membership.chapter',
        'product_chapter_rel',
        'product_id',
        'chapter_id',
        string='Associated Chapters',
        help="Chapters this membership provides access to"
    )
    
    requires_primary_membership = fields.Boolean(
        string='Requires Primary Membership',
        default=False,
        help="Member must have active primary membership to join chapter"
    )
    
    primary_membership_product_ids = fields.Many2many(
        'product.template',
        'chapter_primary_membership_rel',
        'chapter_product_id',
        'primary_product_id',
        string='Required Primary Memberships',
        domain=[('is_membership_product', '=', True)],
        help="Which primary memberships qualify for this chapter"
    )

    # ==========================================
    # PROFESSIONAL FEATURES
    # Enable professional module features
    # ==========================================
    
    enables_credentials = fields.Boolean(
        string='Enables Credential Tracking',
        default=False,
        help="Members can track professional credentials (licenses, certifications)"
    )
    
    enables_ce_tracking = fields.Boolean(
        string='Enables CE Tracking',
        default=False,
        help="Members can track continuing education credits"
    )
    
    enables_designations = fields.Boolean(
        string='Enables Professional Designations',
        default=False,
        help="Members can apply for professional designations (Fellow, etc.)"
    )

    # ==========================================
    # PORTAL CONFIGURATION
    # Member portal access settings
    # ==========================================
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access')
    ], string='Portal Access Level',
       default='standard',
       help="Default portal access level for members with this product")
    
    portal_features = fields.Json(
        string='Portal Features',
        help="JSON defining which portal features are enabled"
    )

    # ==========================================
    # ELIGIBILITY & APPROVAL
    # Member eligibility requirements
    # ==========================================
    
    requires_eligibility_verification = fields.Boolean(
        string='Requires Eligibility Verification',
        default=False,
        help="Membership requires staff verification of eligibility"
    )
    
    eligibility_criteria = fields.Text(
        string='Eligibility Criteria',
        help="Description of who is eligible for this membership"
    )
    
    requires_approval = fields.Boolean(
        string='Requires Staff Approval',
        default=False,
        help="Membership requires staff approval before activation"
    )

    # ==========================================
    # CAPACITY LIMITS
    # Maximum members allowed
    # ==========================================
    
    max_members = fields.Integer(
        string='Maximum Members',
        default=0,
        help="Maximum number of active members allowed (0 = unlimited)"
    )
    
    current_member_count = fields.Integer(
        string='Current Members',
        compute='_compute_current_member_count',
        help="Number of current active members"
    )
    
    is_at_capacity = fields.Boolean(
        string='At Capacity',
        compute='_compute_is_at_capacity',
        help="Whether this membership type has reached capacity"
    )

    # ==========================================
    # UPGRADE/DOWNGRADE PATHS
    # Member progression options
    # ==========================================
    
    upgrade_product_ids = fields.Many2many(
        'product.template',
        'membership_upgrade_rel',
        'product_id',
        'upgrade_product_id',
        string='Upgrade Options',
        domain=[('is_membership_product', '=', True)],
        help="Membership products this can be upgraded to"
    )
    
    downgrade_product_ids = fields.Many2many(
        'product.template',
        'membership_downgrade_rel',
        'product_id',
        'downgrade_product_id',
        string='Downgrade Options',
        domain=[('is_membership_product', '=', True)],
        help="Membership products this can be downgraded to"
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('subscription_product_type')
    def _compute_is_chapter_membership(self):
        """Check if this is a chapter membership"""
        for product in self:
            product.is_chapter_membership = (
                product.subscription_product_type == 'chapter'
            )

    @api.depends('is_membership_product')
    def _compute_current_member_count(self):
        """Calculate current active members for this product"""
        for product in self:
            if product.is_membership_product:
                count = self.env['membership.record'].search_count([
                    ('product_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                product.current_member_count = count
            else:
                product.current_member_count = 0

    @api.depends('max_members', 'current_member_count')
    def _compute_is_at_capacity(self):
        """Check if membership has reached capacity"""
        for product in self:
            if product.max_members > 0:
                product.is_at_capacity = product.current_member_count >= product.max_members
            else:
                product.is_at_capacity = False

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('is_membership_product')
    def _onchange_is_membership_product(self):
        """Set defaults when membership product is checked"""
        if self.is_membership_product:
            # Set as subscription product
            if hasattr(self, 'is_subscription'):
                self.is_subscription = True
            
            # Set subscription type
            if hasattr(self, 'subscription_product_type') and not self.subscription_product_type:
                self.subscription_product_type = 'membership'
            
            # Set as service product
            self.type = 'service'
            
            # Enable invoicing policy
            self.invoice_policy = 'order'
            
            # Set default portal access
            if not self.portal_access_level:
                self.portal_access_level = 'standard'

    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_product_type in ['membership', 'chapter']:
            self.is_membership_product = True
            
            if self.subscription_product_type == 'chapter':
                self.requires_primary_membership = True
        elif self.subscription_product_type == 'organizational_membership':
            self.is_membership_product = True
            self.is_organizational_only = True
            self.supports_seats = True

    @api.onchange('supports_seats')
    def _onchange_supports_seats(self):
        """Set defaults when seat support is enabled"""
        if self.supports_seats and not self.min_seats_required:
            self.min_seats_required = 1

    @api.onchange('membership_year_type')
    def _onchange_membership_year_type(self):
        """Update subscription duration based on year type"""
        if self.membership_year_type == 'calendar':
            # Calendar memberships typically use yearly billing
            if hasattr(self, 'recurring_rule_type'):
                self.recurring_rule_type = 'yearly'
        else:  # anniversary
            # Anniversary can use various periods
            if hasattr(self, 'recurring_rule_type') and not self.recurring_rule_type:
                self.recurring_rule_type = 'yearly'

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_membership_price_for_category(self, category_id):
        """
        Get membership price for a specific member category
        Integrates with subscription_management pricing tiers
        
        Args:
            category_id: membership.category record or ID
        
        Returns:
            float: Price for this category
        """
        self.ensure_one()
        
        # If subscription module has pricing tiers, use those
        if hasattr(self, 'subscription_pricing_tier_ids'):
            category = self.env['membership.category'].browse(category_id) if isinstance(category_id, int) else category_id
            
            # Look for matching pricing tier
            tier = self.subscription_pricing_tier_ids.filtered(
                lambda t: t.member_category_id == category
            )
            
            if tier:
                return tier.price
        
        # Fallback to list price
        return self.list_price

    def check_membership_eligibility(self, partner_id):
        """
        Check if a partner is eligible for this membership product
        
        Args:
            partner_id: res.partner record or ID
        
        Returns:
            tuple: (bool: is_eligible, str: reason if not eligible)
        """
        self.ensure_one()
        
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id

        # Check capacity
        if self.is_at_capacity:
            return (False, _("This membership type is at capacity."))

        # Check if organizational only
        if self.is_organizational_only and not partner.is_company:
            return (False, _("This membership is only available to organizations."))

        # Check member category restrictions
        if self.allowed_member_categories:
            # Get partner's current membership category
            active_membership = self.env['membership.record'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ], limit=1)
            
            if active_membership:
                if active_membership.membership_category_id not in self.allowed_member_categories:
                    return (False, _("Your member category is not eligible for this product."))

        # Check primary membership requirement (for chapters)
        if self.requires_primary_membership and self.primary_membership_product_ids:
            has_required_primary = False
            for primary_product in self.primary_membership_product_ids:
                active_primary = self.env['membership.record'].search([
                    ('partner_id', '=', partner.id),
                    ('product_id', '=', primary_product.id),
                    ('state', '=', 'active')
                ], limit=1)
                if active_primary:
                    has_required_primary = True
                    break
            
            if not has_required_primary:
                return (False, _("This membership requires an active primary membership."))

        return (True, '')

    def calculate_prorated_price(self, start_date):
        """
        Calculate prorated price for calendar year memberships
        
        Args:
            start_date: Date when membership starts
        
        Returns:
            float: Prorated price
        """
        self.ensure_one()
        
        if self.membership_year_type != 'calendar' or not self.prorate_partial_periods:
            return self.list_price
        
        # Calculate months remaining in calendar year
        calendar_start_month = int(self.calendar_year_start)
        
        # Find next calendar year start
        if start_date.month >= calendar_start_month:
            next_year_start = fields.Date.from_string(
                f"{start_date.year + 1}-{calendar_start_month:02d}-01"
            )
        else:
            next_year_start = fields.Date.from_string(
                f"{start_date.year}-{calendar_start_month:02d}-01"
            )
        
        # Calculate months from start_date to year end
        months_remaining = (next_year_start.year - start_date.year) * 12
        months_remaining += next_year_start.month - start_date.month
        
        if months_remaining <= 0:
            months_remaining = 12
        
        # Prorate
        prorated_price = (self.list_price / 12) * months_remaining
        
        return prorated_price

    def action_view_members(self):
        """View all members with this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members'),
            'res_model': 'membership.record',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }

    def action_view_active_members(self):
        """View active members with this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Members'),
            'res_model': 'membership.record',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id', '=', self.id),
                ('state', '=', 'active')
            ],
            'context': {'default_product_id': self.id}
        }

    def action_configure_membership_features(self):
        """Open wizard to configure membership-specific features"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Membership Features'),
            'res_model': 'product.membership.config.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.id}
        }

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('min_seats_required')
    def _check_min_seats(self):
        """Validate minimum seats"""
        for product in self:
            if product.supports_seats and product.min_seats_required < 1:
                raise ValidationError(_("Minimum seats must be at least 1."))

    @api.constrains('primary_membership_product_ids')
    def _check_circular_primary_memberships(self):
        """Prevent circular primary membership requirements"""
        for product in self:
            if product.id in product.primary_membership_product_ids.ids:
                raise ValidationError(_("A membership cannot require itself as primary."))

    @api.constrains('upgrade_product_ids', 'downgrade_product_ids')
    def _check_upgrade_downgrade_paths(self):
        """Validate upgrade/downgrade paths"""
        for product in self:
            # Can't upgrade to same product
            if product.id in product.upgrade_product_ids.ids:
                raise ValidationError(_("A membership cannot upgrade to itself."))
            
            # Can't downgrade to same product
            if product.id in product.downgrade_product_ids.ids:
                raise ValidationError(_("A membership cannot downgrade to itself."))
            
            # Can't be both upgrade and downgrade
            overlap = set(product.upgrade_product_ids.ids) & set(product.downgrade_product_ids.ids)
            if overlap:
                raise ValidationError(_("A product cannot be both an upgrade and downgrade option."))