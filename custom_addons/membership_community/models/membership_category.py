# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCategory(models.Model):
    _name = 'membership.category'
    _description = 'Membership Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        tracking=True,
        help='Display name for this member category (e.g., Individual Member, Student Member)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help='Unique code for this category (e.g., IND, STU, CORP)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists and forms'
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True,
        help='Inactive categories are hidden but not deleted'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this member category'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # CATEGORY CLASSIFICATION
    # ==========================================
    
    category_type = fields.Selection([
        ('individual', 'Individual'),
        ('organizational', 'Organizational'),
        ('student', 'Student'),
        ('honorary', 'Honorary'),
        ('retired', 'Retired'),
        ('emeritus', 'Emeritus'),
        ('affiliate', 'Affiliate'),
        ('associate', 'Associate'),
        ('special', 'Special')
    ], string='Category Type',
       required=True,
       default='individual',
       tracking=True,
       help='Primary classification of this member category')
    
    is_voting_member = fields.Boolean(
        string='Voting Rights',
        default=True,
        tracking=True,
        help='Members in this category have voting rights'
    )
    
    is_full_member = fields.Boolean(
        string='Full Membership',
        default=True,
        help='This is a full membership category (vs affiliate/associate)'
    )
    
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum')
    ], string='Member Tier',
       default='standard',
       help='Tier level for benefits and access')

    # ==========================================
    # ACCESS & FEATURES
    # ==========================================
    
    default_portal_access = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium')
    ], string='Default Portal Access',
       default='standard',
       help='Default portal access level for this category')
    
    allows_chapter_membership = fields.Boolean(
        string='Allows Chapter Membership',
        default=True,
        help='Members in this category can join chapters'
    )
    
    allows_committee_participation = fields.Boolean(
        string='Allows Committee Participation',
        default=True,
        help='Members in this category can join committees'
    )
    
    allows_event_registration = fields.Boolean(
        string='Allows Event Registration',
        default=True,
        help='Members in this category can register for events'
    )

    # ==========================================
    # ELIGIBILITY REQUIREMENTS
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Membership in this category requires staff verification'
    )
    
    eligibility_requirements = fields.Html(
        string='Eligibility Requirements',
        translate=True,
        help='Description of eligibility criteria for this category'
    )
    
    verification_documents = fields.Text(
        string='Required Documents',
        help='List of documents required for verification'
    )
    
    min_age = fields.Integer(
        string='Minimum Age',
        default=0,
        help='Minimum age requirement (0 = no requirement)'
    )
    
    max_age = fields.Integer(
        string='Maximum Age',
        default=0,
        help='Maximum age requirement (0 = no requirement)'
    )
    
    requires_sponsorship = fields.Boolean(
        string='Requires Sponsorship',
        default=False,
        help='Membership requires sponsorship from existing members'
    )
    
    min_sponsors_required = fields.Integer(
        string='Minimum Sponsors',
        default=2,
        help='Minimum number of sponsors required'
    )

    # ==========================================
    # PROFESSIONAL REQUIREMENTS
    # ==========================================
    
    requires_degree = fields.Boolean(
        string='Requires Degree',
        default=False,
        help='Membership requires specific educational degree'
    )
    
    required_degree_level = fields.Selection([
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('doctorate', 'Doctorate'),
        ('professional', 'Professional Degree')
    ], string='Required Degree Level',
       help='Minimum degree level required')
    
    requires_license = fields.Boolean(
        string='Requires Professional License',
        default=False,
        help='Membership requires active professional license'
    )
    
    required_license_types = fields.Text(
        string='Required License Types',
        help='Types of licenses that qualify'
    )
    
    requires_experience = fields.Boolean(
        string='Requires Professional Experience',
        default=False,
        help='Membership requires minimum professional experience'
    )
    
    min_years_experience = fields.Integer(
        string='Minimum Years Experience',
        default=0,
        help='Minimum years of professional experience required'
    )

    # ==========================================
    # PROGRESSION & TRANSITIONS
    # ==========================================
    
    allows_upgrade_to = fields.Many2many(
        'membership.category',
        'category_upgrade_rel',
        'from_category_id',
        'to_category_id',
        string='Can Upgrade To',
        help='Categories this can be upgraded to'
    )
    
    allows_downgrade_to = fields.Many2many(
        'membership.category',
        'category_downgrade_rel',
        'from_category_id',
        'to_category_id',
        string='Can Downgrade To',
        help='Categories this can be downgraded to'
    )
    
    auto_transition_age = fields.Integer(
        string='Auto-Transition Age',
        default=0,
        help='Age at which to automatically transition to another category (0 = no auto-transition)'
    )
    
    auto_transition_category_id = fields.Many2one(
        'membership.category',
        string='Auto-Transition To',
        help='Category to transition to at specified age (e.g., Student → Regular at 26)'
    )

    # ==========================================
    # TERM LIMITS
    # ==========================================
    
    has_term_limit = fields.Boolean(
        string='Has Term Limit',
        default=False,
        help='Membership in this category has maximum duration'
    )
    
    max_term_years = fields.Integer(
        string='Maximum Term (Years)',
        default=0,
        help='Maximum years allowed in this category'
    )
    
    max_consecutive_terms = fields.Integer(
        string='Maximum Consecutive Terms',
        default=0,
        help='Maximum consecutive terms in this category (0 = unlimited)'
    )

    # ==========================================
    # PRICING INFORMATION (for reference)
    # ==========================================
    
    typical_discount_percent = fields.Float(
        string='Typical Discount %',
        default=0.0,
        help='Typical discount percentage for this category (informational only - actual pricing via subscription tiers)'
    )
    
    has_discounted_pricing = fields.Boolean(
        string='Has Discounted Pricing',
        compute='_compute_pricing_flags',
        help='This category typically has discounted pricing'
    )

    # ==========================================
    # PRODUCT MAPPING
    # ==========================================
    
    allowed_product_ids = fields.Many2many(
        'product.template',
        'category_allowed_product_rel',
        'category_id',
        'product_id',
        string='Allowed Products',
        domain=[('is_membership_product', '=', True)],
        help='Membership products available to this category (empty = all products)'
    )
    
    default_product_id = fields.Many2one(
        'product.template',
        string='Default Product',
        domain=[('is_membership_product', '=', True)],
        help='Default membership product for this category'
    )

    # ==========================================
    # STATISTICS
    # ==========================================
    
    member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_count',
        help='Number of active members in this category'
    )
    
    total_members_all_time = fields.Integer(
        string='Total Members (All Time)',
        compute='_compute_member_count',
        help='Total members ever in this category'
    )

    # ==========================================
    # ORGANIZATIONAL SETTINGS
    # ==========================================
    
    is_organizational = fields.Boolean(
        string='Is Organizational Category',
        compute='_compute_is_organizational',
        store=True,
        help='This category is for organizations/corporations'
    )
    
    requires_ein = fields.Boolean(
        string='Requires EIN/Tax ID',
        default=False,
        help='Organization must provide EIN/Tax ID number'
    )
    
    min_employee_count = fields.Integer(
        string='Minimum Employee Count',
        default=0,
        help='Minimum number of employees for organizational membership'
    )

    # ==========================================
    # STUDENT SETTINGS
    # ==========================================
    
    is_student_category = fields.Boolean(
        string='Is Student Category',
        compute='_compute_is_student',
        store=True,
        help='This category is for students'
    )
    
    requires_enrollment_verification = fields.Boolean(
        string='Requires Enrollment Verification',
        default=False,
        help='Must verify current enrollment status'
    )
    
    enrollment_verification_frequency = fields.Selection([
        ('annual', 'Annual'),
        ('semester', 'Each Semester'),
        ('once', 'One Time')
    ], string='Verification Frequency',
       default='annual',
       help='How often enrollment must be verified')

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('category_type')
    def _compute_is_organizational(self):
        """Determine if this is an organizational category"""
        for category in self:
            category.is_organizational = category.category_type == 'organizational'

    @api.depends('category_type')
    def _compute_is_student(self):
        """Determine if this is a student category"""
        for category in self:
            category.is_student_category = category.category_type == 'student'

    @api.depends('typical_discount_percent')
    def _compute_pricing_flags(self):
        """Compute pricing-related flags"""
        for category in self:
            category.has_discounted_pricing = category.typical_discount_percent > 0

    def _compute_member_count(self):
        """Calculate member statistics"""
        for category in self:
            # Count partners with active subscriptions in this category
            active_members = self.env['res.partner'].search_count([
                ('membership_category_id', '=', category.id),
                ('is_member', '=', True)
            ])
            category.member_count = active_members
            
            # All-time count
            all_members = self.env['subscription.subscription'].search_count([
                ('membership_category_id', '=', category.id)
            ])
            category.total_members_all_time = all_members

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def check_eligibility(self, partner_id):
        """
        Check if a partner is eligible for this membership category
        
        Args:
            partner_id: res.partner record or ID
        
        Returns:
            tuple: (bool: is_eligible, list: reasons if not eligible)
        """
        self.ensure_one()
        
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        reasons = []
        
        # Check organizational requirements
        if self.is_organizational and not partner.is_company:
            reasons.append(_("This category is for organizations only."))
        
        if not self.is_organizational and partner.is_company:
            reasons.append(_("This category is for individuals only."))
        
        # Check age requirements
        if self.min_age > 0 or self.max_age > 0:
            if hasattr(partner, 'birthdate') and partner.birthdate:
                age = (fields.Date.today() - partner.birthdate).days // 365
                
                if self.min_age > 0 and age < self.min_age:
                    reasons.append(_("Minimum age requirement: %s years") % self.min_age)
                
                if self.max_age > 0 and age > self.max_age:
                    reasons.append(_("Maximum age requirement: %s years") % self.max_age)
        
        # Check organizational requirements
        if self.is_organizational:
            if self.requires_ein:
                if not hasattr(partner, 'vat') or not partner.vat:
                    reasons.append(_("EIN/Tax ID is required."))
        
        is_eligible = len(reasons) == 0
        return (is_eligible, reasons)

    def get_available_products(self):
        """
        Get products available to this category
        
        Returns:
            recordset: product.template records
        """
        self.ensure_one()
        
        if self.allowed_product_ids:
            return self.allowed_product_ids
        else:
            # Return all membership products if no restrictions
            return self.env['product.template'].search([
                ('is_membership_product', '=', True),
                ('active', '=', True)
            ])

    def action_view_members(self):
        """View members in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {
                'default_membership_category_id': self.id,
                'search_default_active_members': 1
            }
        }

    @api.model
    def get_category_by_code(self, code):
        """
        Get category by code (helper method)
        
        Args:
            code: Category code
        
        Returns:
            membership.category record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def get_transition_categories(self, transition_type='upgrade'):
        """
        Get categories this can transition to
        
        Args:
            transition_type: 'upgrade' or 'downgrade'
        
        Returns:
            recordset: Available transition categories
        """
        self.ensure_one()
        
        if transition_type == 'upgrade':
            return self.allows_upgrade_to
        else:
            return self.allows_downgrade_to

    def name_get(self):
        """Custom name_get to show code in parentheses"""
        result = []
        for record in self:
            if record.code:
                name = f"{record.name} ({record.code})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure category code is unique"""
        for category in self:
            if self.search_count([
                ('code', '=', category.code),
                ('id', '!=', category.id)
            ]) > 0:
                raise ValidationError(_("Category code must be unique. '%s' is already used.") % category.code)

    @api.constrains('min_age', 'max_age')
    def _check_age_requirements(self):
        """Validate age requirements"""
        for category in self:
            if category.min_age < 0:
                raise ValidationError(_("Minimum age cannot be negative."))
            
            if category.max_age < 0:
                raise ValidationError(_("Maximum age cannot be negative."))
            
            if category.max_age > 0 and category.min_age > 0:
                if category.max_age < category.min_age:
                    raise ValidationError(_("Maximum age must be greater than minimum age."))

    @api.constrains('min_sponsors_required')
    def _check_sponsors(self):
        """Validate sponsor requirements"""
        for category in self:
            if category.requires_sponsorship and category.min_sponsors_required < 1:
                raise ValidationError(_("Minimum sponsors must be at least 1 if sponsorship is required."))

    @api.constrains('typical_discount_percent')
    def _check_discount_percent(self):
        """Validate discount percentage"""
        for category in self:
            if category.typical_discount_percent < 0 or category.typical_discount_percent > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    @api.constrains('allows_upgrade_to', 'allows_downgrade_to')
    def _check_transition_paths(self):
        """Validate transition paths"""
        for category in self:
            # Can't upgrade/downgrade to self
            if category.id in category.allows_upgrade_to.ids:
                raise ValidationError(_("Category cannot upgrade to itself."))
            
            if category.id in category.allows_downgrade_to.ids:
                raise ValidationError(_("Category cannot downgrade to itself."))

    @api.constrains('auto_transition_category_id', 'auto_transition_age')
    def _check_auto_transition(self):
        """Validate auto-transition settings"""
        for category in self:
            if category.auto_transition_category_id:
                if category.auto_transition_age <= 0:
                    raise ValidationError(_("Auto-transition age must be greater than 0."))
                
                if category.auto_transition_category_id == category:
                    raise ValidationError(_("Category cannot auto-transition to itself."))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique!'),
    ]