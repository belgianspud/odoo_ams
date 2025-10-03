# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCategory(models.Model):
    """
    Simplified Membership Category - Classification Only
    
    Philosophy:
    - Category = Classification (what type of member)
    - Product = Behavior (pricing, features, benefits)
    - Plan = Billing (when and how they pay)
    
    This keeps the category model simple and delegates complexity
    to products and plans where it belongs.
    """
    _name = 'membership.category'
    _description = 'Membership Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # CORE IDENTIFICATION
    # ==========================================
    
    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        tracking=True,
        help='Display name (e.g., Individual Member, Student Member, Premium Corporate)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help='Unique identifier (e.g., IND, STU, CORP_PREM)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
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
    # TYPE CLASSIFICATION
    # ==========================================
    
    category_type = fields.Selection(
        selection='_get_category_types',
        string='Category Type',
        required=True,
        default='individual',
        tracking=True,
        help='Primary classification determining member type'
    )
    
    @api.model
    def _get_category_types(self):
        """
        Base category types - can be extended by other modules
        
        Extension pattern:
        class MembershipCategory(models.Model):
            _inherit = 'membership.category'
            
            @api.model
            def _get_category_types(self):
                types = super()._get_category_types()
                types.extend([
                    ('student', 'Student'),
                    ('retired', 'Retired'),
                ])
                return types
        """
        return [
            ('individual', 'Individual Member'),
            ('organizational', 'Organization Member'),
            ('chapter', 'Chapter Member'),
            ('seat', 'Organization Seat'),
            ('emeritus', 'Emeritus/Retired Member'),  # NEW
            ('honorary', 'Honorary Member'),  # NEW
            ('lifetime', 'Lifetime Member'),  # NEW
        ]
    
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum'),
    ], string='Member Tier',
       default='standard',
       help='Tier level for this category')

    # ==========================================
    # SIMPLE CLASSIFICATION FLAGS
    # ==========================================
    
    is_voting_member = fields.Boolean(
        string='Voting Rights',
        default=True,
        tracking=True,
        help='Members in this category have voting rights'
    )
    
    is_full_member = fields.Boolean(
        string='Full Membership',
        default=True,
        help='Full membership vs affiliate/associate status'
    )

    # ==========================================
    # LIFETIME & EMERITUS CONFIGURATION (NEW)
    # ==========================================
    
    is_lifetime_category = fields.Boolean(
        string='Lifetime Membership Category',
        default=False,
        tracking=True,
        help='This category is for lifetime memberships (one-time payment, never expires)'
    )
    
    is_emeritus_category = fields.Boolean(
        string='Emeritus/Retired Category',
        default=False,
        tracking=True,
        help='This category is for emeritus/retired members'
    )
    
    is_honorary_category = fields.Boolean(
        string='Honorary Category',
        default=False,
        tracking=True,
        help='This category is for honorary members'
    )
    
    # Auto-qualification Rules
    auto_qualify_age = fields.Integer(
        string='Auto-Qualify Age',
        default=0,
        help='Age at which members automatically qualify for this category (e.g., 65 for emeritus). 0 = disabled'
    )
    
    auto_qualify_years = fields.Integer(
        string='Auto-Qualify Years',
        default=0,
        help='Years of continuous membership required for auto-qualification (e.g., 25 years for emeritus). 0 = disabled'
    )
    
    requires_board_approval = fields.Boolean(
        string='Requires Board Approval',
        default=False,
        tracking=True,
        help='Transitions to this category require board/committee approval'
    )
    
    # Dues Configuration
    has_reduced_dues = fields.Boolean(
        string='Reduced Dues',
        default=False,
        help='This category pays reduced dues'
    )
    
    dues_percentage = fields.Float(
        string='Dues Percentage',
        default=100.0,
        help='Percentage of standard dues (100 = full, 50 = half, 0 = free)'
    )
    
    is_complimentary = fields.Boolean(
        string='Complimentary Membership',
        default=False,
        tracking=True,
        help='This category receives complimentary (free) membership'
    )

    # ==========================================
    # CATEGORY HIERARCHY (for chapters)
    # ==========================================
    
    parent_category_id = fields.Many2one(
        'membership.category',
        string='Parent Category',
        index=True,
        ondelete='restrict',
        help='Parent membership category (e.g., National membership for chapters)'
    )
    
    child_category_ids = fields.One2many(
        'membership.category',
        'parent_category_id',
        string='Child Categories',
        help='Sub-categories (e.g., Chapters under national membership)'
    )
    
    child_count = fields.Integer(
        string='Child Categories',
        compute='_compute_child_count',
        help='Number of child categories'
    )
    
    is_parent_required = fields.Boolean(
        string='Requires Parent Membership',
        default=False,
        tracking=True,
        help='Members must have parent category membership to join this category'
    )
    
    parent_membership_note = fields.Text(
        string='Parent Membership Note',
        help='Instructions or notes about parent membership requirement'
    )
    
    @api.depends('child_category_ids')
    def _compute_child_count(self):
        """Count child categories"""
        for category in self:
            category.child_count = len(category.child_category_ids)
    
    # ==========================================
    # PRODUCT LINK - Core Connection
    # ==========================================
    
    default_product_id = fields.Many2one(
        'product.template',
        string='Default Product',
        domain=[('is_membership_product', '=', True)],
        help='Default product that defines pricing, billing, features, and benefits'
    )
    
    # ==========================================
    # PORTAL & VERIFICATION - Basic
    # ==========================================
    
    default_portal_access = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], string='Default Portal Access',
       default='standard',
       help='Default portal access level for this category')
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Memberships in this category require eligibility verification'
    )

    # ==========================================
    # STATISTICS
    # ==========================================
    
    member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_count',
        help='Number of active members in this category'
    )
    
    subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_count',
        help='Number of active subscriptions'
    )

    @api.depends('code')  # Dummy dependency
    def _compute_member_count(self):
        """Count active members in this category"""
        for category in self:
            category.member_count = self.env['res.partner'].search_count([
                ('membership_category_id', '=', category.id),
                ('is_member', '=', True),
            ])
    
    @api.depends('code')  # Dummy dependency
    def _compute_subscription_count(self):
        """Count active subscriptions"""
        for category in self:
            category.subscription_count = self.env['subscription.subscription'].search_count([
                ('membership_category_id', '=', category.id),
                ('state', 'in', ['trial', 'active']),
            ])

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_available_products(self):
        """
        Get products available for this category
        
        Returns:
            recordset: product.template records
        """
        self.ensure_one()
        
        if self.default_product_id:
            return self.default_product_id
        
        # Return all membership products of matching type
        domain = [
            ('is_membership_product', '=', True),
            ('active', '=', True),
        ]
        
        # Filter by subscription type
        type_map = {
            'individual': 'membership',
            'organizational': 'organizational_membership',
            'chapter': 'chapter',
            'seat': 'membership',
            'emeritus': 'membership',  # NEW
            'honorary': 'membership',  # NEW
            'lifetime': 'membership',  # NEW
        }
        
        sub_type = type_map.get(self.category_type)
        if sub_type:
            domain.append(('subscription_product_type', '=', sub_type))
        
        return self.env['product.template'].search(domain)
    
    def get_all_parent_categories(self):
        """
        Get all parent categories up the hierarchy
        
        Returns:
            recordset: membership.category records (parents)
        """
        self.ensure_one()
        
        parents = self.env['membership.category']
        current = self.parent_category_id
        
        while current:
            parents |= current
            current = current.parent_category_id
        
        return parents
    
    def get_all_child_categories(self, recursive=True):
        """
        Get all child categories
        
        Args:
            recursive: If True, get all descendants; if False, only direct children
        
        Returns:
            recordset: membership.category records (children)
        """
        self.ensure_one()
        
        children = self.child_category_ids
        
        if recursive:
            for child in self.child_category_ids:
                children |= child.get_all_child_categories(recursive=True)
        
        return children

    # ==========================================
    # EMERITUS/LIFETIME BUSINESS METHODS (NEW)
    # ==========================================
    
    def check_emeritus_eligibility(self, partner):
        """
        Check if a partner is eligible for emeritus status
        
        Args:
            partner: res.partner record
        
        Returns:
            tuple: (bool: is_eligible, str: reason)
        """
        self.ensure_one()
        
        if not self.is_emeritus_category:
            return (False, _('This is not an emeritus category'))
        
        # Check age requirement
        if self.auto_qualify_age > 0:
            if not partner.birthdate:
                return (False, _('Member age cannot be determined'))
            
            age = (fields.Date.today() - partner.birthdate).days / 365.25
            if age < self.auto_qualify_age:
                return (False, _(
                    'Member must be %s years old (currently %s)'
                ) % (self.auto_qualify_age, int(age)))
        
        # Check years of membership
        if self.auto_qualify_years > 0:
            if not partner.member_since:
                return (False, _('Member join date unknown'))
            
            years = (fields.Date.today() - partner.member_since).days / 365.25
            if years < self.auto_qualify_years:
                return (False, _(
                    'Member must have %s years of membership (currently %s)'
                ) % (self.auto_qualify_years, int(years)))
        
        return (True, '')
    
    def action_view_eligible_members(self):
        """View members eligible for this category (emeritus/honorary)"""
        self.ensure_one()
        
        if not (self.is_emeritus_category or self.is_honorary_category):
            raise UserError(_('This action is only for emeritus/honorary categories'))
        
        # Find eligible members
        eligible_partners = self.env['res.partner']
        
        if self.is_emeritus_category and (self.auto_qualify_age > 0 or self.auto_qualify_years > 0):
            all_members = self.env['res.partner'].search([
                ('is_member', '=', True),
                ('membership_category_id', '!=', self.id),
            ])
            
            for partner in all_members:
                is_eligible, reason = self.check_emeritus_eligibility(partner)
                if is_eligible:
                    eligible_partners |= partner
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Eligible Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', eligible_partners.ids)],
            'context': {
                'default_membership_category_id': self.id,
                'search_default_eligible': 1,
            }
        }

    def action_view_members(self):
        """View members in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'kanban,list,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {'default_membership_category_id': self.id},
        }
    
    def action_view_subscriptions(self):
        """View subscriptions in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,kanban,form',
            'domain': [('membership_category_id', '=', self.id)],
            'context': {'default_membership_category_id': self.id},
        }
    
    def action_view_child_categories(self):
        """View child categories"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Child Categories - %s') % self.name,
            'res_model': 'membership.category',
            'view_mode': 'list,form',
            'domain': [('parent_category_id', '=', self.id)],
            'context': {'default_parent_category_id': self.id},
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

    def name_get(self):
        """Custom name_get to show code"""
        result = []
        for record in self:
            if record.code:
                name = f"{record.name} ({record.code})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================
    
    @api.onchange('parent_category_id')
    def _onchange_parent_category_id(self):
        """Set defaults when parent is selected"""
        if self.parent_category_id:
            if not self.is_parent_required:
                self.is_parent_required = True
            
            # Suggest using same tier as parent
            if not self.member_tier:
                self.member_tier = self.parent_category_id.member_tier
    
    @api.onchange('category_type')
    def _onchange_category_type(self):
        """Set defaults based on category type"""
        if self.category_type == 'chapter':
            # Chapters typically require parent membership
            if not self.is_parent_required:
                self.is_parent_required = True
            
            # Chapters are typically voting members
            if not self.is_voting_member:
                self.is_voting_member = True
        
        elif self.category_type == 'seat':
            # Seats are not independent members
            self.is_voting_member = False
            self.is_full_member = False
        
        # NEW: Emeritus defaults
        elif self.category_type == 'emeritus':
            self.is_emeritus_category = True
            self.has_reduced_dues = True
            self.dues_percentage = 0.0  # Free by default
            self.is_voting_member = True
        
        # NEW: Honorary defaults
        elif self.category_type == 'honorary':
            self.is_honorary_category = True
            self.is_complimentary = True
            self.requires_board_approval = True
            self.is_voting_member = False
        
        # NEW: Lifetime defaults
        elif self.category_type == 'lifetime':
            self.is_lifetime_category = True
            self.is_voting_member = True
    
    # NEW: Complimentary onchange
    @api.onchange('is_complimentary')
    def _onchange_is_complimentary(self):
        """Free memberships have 0% dues"""
        if self.is_complimentary:
            self.has_reduced_dues = True
            self.dues_percentage = 0.0

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
                raise ValidationError(
                    _("Category code must be unique. '%s' is already used.") % category.code
                )
    
    @api.constrains('parent_category_id')
    def _check_parent_recursion(self):
        """Prevent circular parent relationships"""
        for category in self:
            if category.parent_category_id:
                # Check for direct self-reference
                if category.parent_category_id == category:
                    raise ValidationError(_(
                        "A category cannot be its own parent."
                    ))
                
                # Check for circular reference
                current = category.parent_category_id
                visited = set()
                while current:
                    if current.id in visited:
                        raise ValidationError(_(
                            "Circular parent relationship detected. "
                            "Category '%s' is in a parent loop."
                        ) % category.name)
                    
                    visited.add(current.id)
                    
                    if current == category:
                        raise ValidationError(_(
                            "Circular parent relationship detected. "
                            "Category '%s' cannot be a parent of itself through the hierarchy."
                        ) % category.name)
                    
                    current = current.parent_category_id
    
    @api.constrains('is_parent_required', 'parent_category_id')
    def _check_parent_requirement(self):
        """Validate parent requirement configuration"""
        for category in self:
            if category.is_parent_required and not category.parent_category_id:
                # This is just a warning - we allow configuration where parent is required
                # but not yet selected (will be validated when creating subscriptions)
                pass
    
    # NEW: Dues percentage constraint
    @api.constrains('dues_percentage')
    def _check_dues_percentage(self):
        """Validate dues percentage"""
        for category in self:
            if category.dues_percentage < 0 or category.dues_percentage > 100:
                raise ValidationError(_(
                    'Dues percentage must be between 0 and 100'
                ))
    
    # NEW: Auto-qualification constraints
    @api.constrains('auto_qualify_age')
    def _check_auto_qualify_age(self):
        """Validate auto-qualify age"""
        for category in self:
            if category.auto_qualify_age < 0:
                raise ValidationError(_(
                    'Auto-qualify age cannot be negative'
                ))
    
    @api.constrains('auto_qualify_years')
    def _check_auto_qualify_years(self):
        """Validate auto-qualify years"""
        for category in self:
            if category.auto_qualify_years < 0:
                raise ValidationError(_(
                    'Auto-qualify years cannot be negative'
                ))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique!'),
    ]