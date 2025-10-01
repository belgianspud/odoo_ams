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
    # SUBSCRIPTION PRODUCT TYPE
    # Categorizes the type of subscription/membership
    # ==========================================
    
    subscription_product_type = fields.Selection([
        ('membership', 'Individual Membership'),
        ('organizational_membership', 'Organizational Membership'),
        ('chapter', 'Chapter Membership'),
        ('seat', 'Organizational Seat'),
        ('publication', 'Publication Subscription'),
        ('other', 'Other Subscription')
    ], string='Subscription Type',
       help='Type of subscription or membership this product represents')

    # ==========================================
    # MEMBERSHIP YEAR CONFIGURATION
    # ==========================================
    
    membership_year_type = fields.Selection([
        ('rolling', 'Rolling (Anniversary-based)'),
        ('calendar', 'Calendar Year'),
        ('fiscal', 'Fiscal Year')
    ], string='Membership Year Type',
       default='rolling',
       help='How membership periods are calculated')
    
    calendar_year_start = fields.Date(
        string='Calendar Year Start',
        help='Start date for calendar year memberships (e.g., January 1)'
    )
    
    prorate_partial_periods = fields.Boolean(
        string='Prorate Partial Periods',
        default=False,
        help='Prorate membership fees for partial calendar periods'
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
    # CHAPTER MEMBERSHIP
    # For chapter/section memberships
    # ==========================================
    
    is_chapter_membership = fields.Boolean(
        string='Is Chapter Membership',
        compute='_compute_is_chapter_membership',
        store=True,
        help="This is a chapter membership product"
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
        domain=[('is_membership_product', '=', True), ('subscription_product_type', '=', 'membership')],
        help="Which primary memberships qualify for this chapter"
    )
    
    chapter_ids = fields.Many2many(
        'membership.chapter',
        'product_chapter_rel',
        'product_id',
        'chapter_id',
        string='Chapters',
        help="Chapters associated with this membership product"
    )

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP
    # ==========================================
    
    is_organizational_only = fields.Boolean(
        string='Organizational Members Only',
        default=False,
        help="Only organizations can purchase this membership"
    )
    
    supports_seats = fields.Boolean(
        string='Supports Seats',
        default=False,
        help="This organizational membership includes individual seats"
    )
    
    min_seats_required = fields.Integer(
        string='Minimum Seats',
        default=1,
        help="Minimum number of seats required for organizational membership"
    )
    
    seat_product_id = fields.Many2one(
        'product.template',
        string='Seat Product',
        domain=[('subscription_product_type', '=', 'seat')],
        help="Product used for additional seats in organizational membership"
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
        help='JSON configuration of portal features enabled for this membership'
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
    
    eligibility_criteria = fields.Html(
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
                # Count active subscriptions for this product
                count = self.env['subscription.subscription'].search_count([
                    ('plan_id.product_template_id', '=', product.id),
                    ('state', 'in', ['trial', 'active'])
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
            
            # Set default subscription type if not set
            if not self.subscription_product_type:
                self.subscription_product_type = 'membership'
            
            # Set as service product
            if not self.type:
                self.type = 'service'
            
            # Enable invoicing policy
            if not self.invoice_policy:
                self.invoice_policy = 'order'
            
            # Set default portal access
            if not self.portal_access_level:
                self.portal_access_level = 'standard'

    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_product_type in ['membership', 'chapter', 'organizational_membership']:
            self.is_membership_product = True
            
            if self.subscription_product_type == 'chapter':
                self.requires_primary_membership = True
            elif self.subscription_product_type == 'organizational_membership':
                self.is_organizational_only = True

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

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

        # Check organizational requirement
        if self.is_organizational_only and not partner.is_company:
            return (False, _("This membership is only available to organizations."))
        
        if not self.is_organizational_only and partner.is_company:
            return (False, _("This membership is only available to individuals."))

        # Check member category restrictions
        if self.allowed_member_categories and hasattr(partner, 'membership_category_id'):
            if partner.membership_category_id:
                if partner.membership_category_id not in self.allowed_member_categories:
                    return (False, _("Your member category is not eligible for this product."))

        # Check primary membership requirement (for chapters)
        if self.requires_primary_membership and self.primary_membership_product_ids:
            has_required_primary = False
            
            # Check if partner has active subscription with any primary product
            for primary_product in self.primary_membership_product_ids:
                active_primary = self.env['subscription.subscription'].search([
                    ('partner_id', '=', partner.id),
                    ('plan_id.product_template_id', '=', primary_product.id),
                    ('state', 'in', ['trial', 'active'])
                ], limit=1)
                
                if active_primary:
                    has_required_primary = True
                    break
            
            if not has_required_primary:
                return (False, _("This membership requires an active primary membership."))

        return (True, '')

    def action_view_members(self):
        """View all members with this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [
                ('subscription_ids.plan_id.product_template_id', '=', self.id),
                ('subscription_ids.state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_id': self.id}
        }

    def action_view_active_subscriptions(self):
        """View active subscriptions for this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [
                ('plan_id.product_template_id', '=', self.id),
                ('state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_template_id': self.id}
        }

    def get_available_categories(self):
        """
        Get available categories for this product
        
        Returns:
            recordset: membership.category records
        """
        self.ensure_one()
        
        if self.allowed_member_categories:
            return self.allowed_member_categories
        else:
            # Return all active categories
            return self.env['membership.category'].search([('active', '=', True)])

    # ==========================================
    # CONSTRAINTS
    # ==========================================

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

    @api.constrains('max_members')
    def _check_max_members(self):
        """Validate max members"""
        for product in self:
            if product.max_members < 0:
                raise ValidationError(_("Maximum members cannot be negative. Use 0 for unlimited."))
    
    @api.constrains('min_seats_required')
    def _check_min_seats(self):
        """Validate minimum seats"""
        for product in self:
            if product.supports_seats and product.min_seats_required < 1:
                raise ValidationError(_("Minimum seats must be at least 1 when seats are supported."))