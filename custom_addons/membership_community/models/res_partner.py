# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    """
    Simplified Partner Extensions for Base Membership Module
    """
    _inherit = 'res.partner'

    # ==========================================
    # CORE MEMBERSHIP STATUS
    # ==========================================
    
    member_number = fields.Char(
        string='Member Number',
        copy=False,
        readonly=True,
        help='Unique member identification number'
    )
    
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_is_member',
        store=True,
        help='Partner has at least one active membership'
    )
    
    member_since = fields.Date(
        string='Member Since',
        compute='_compute_member_since',
        store=True,
        help='Date of first membership'
    )
    
    membership_state = fields.Selection([
        ('none', 'Not a Member'),
        ('active', 'Active Member'),
        ('trial', 'Trial'),
        ('expired', 'Expired'),
    ], string='Membership Status',
       compute='_compute_membership_state',
       store=True,
       help='Current membership status')

    # ==========================================
    # MEMBERSHIP CATEGORY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        compute='_compute_membership_category',
        store=True,
        help='Current member category'
    )
    
    member_category_type = fields.Selection(
        related='membership_category_id.category_type',
        string='Member Type',
        store=True,
        readonly=True
    )

    # ==========================================
    # GEOGRAPHIC INFORMATION (NEW - for chapters)
    # ==========================================
    
    # Note: country_id, state_id, zip already exist in base res.partner
    # We just ensure they're accessible and add computed fields
    
    eligible_chapters = fields.Many2many(
        'membership.category',
        compute='_compute_eligible_chapters',
        string='Eligible Chapters',
        help='Chapters this member is eligible to join based on location'
    )
    
    chapter_memberships = fields.Many2many(
        'membership.category',
        'partner_chapter_membership_rel',
        'partner_id',
        'category_id',
        string='Chapter Memberships',
        domain=[('category_type', '=', 'chapter')],
        help='Chapters this member belongs to'
    )
    
    chapter_count = fields.Integer(
        string='Number of Chapters',
        compute='_compute_chapter_count',
        help='Number of chapters member belongs to'
    )

    # ==========================================
    # SUBSCRIPTIONS LINK
    # ==========================================
    
    membership_subscription_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Membership Subscriptions',
        domain=[('plan_id.product_template_id.is_membership_product', '=', True)],
        help='All membership subscriptions for this partner'
    )
    
    primary_membership_id = fields.Many2one(
        'subscription.subscription',
        string='Primary Membership',
        compute='_compute_primary_membership',
        store=True,
        help='Current active primary membership'
    )
    
    membership_count = fields.Integer(
        string='Membership Count',
        compute='_compute_membership_counts',
        help='Total number of membership subscriptions'
    )
    
    active_membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_membership_counts',
        help='Number of currently active memberships'
    )

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP - SEAT SUPPORT
    # ==========================================
    
    parent_organization_id = fields.Many2one(
        'res.partner',
        string='Parent Organization',
        help='Organization this person is affiliated with (for seat memberships)',
        index=True
    )
    
    child_member_ids = fields.One2many(
        'res.partner',
        'parent_organization_id',
        string='Organization Members',
        help='Individuals with seats under this organizational membership'
    )
    
    is_seat_member = fields.Boolean(
        string='Is Seat Member',
        compute='_compute_is_seat_member',
        store=True,
        help='This member has a seat through an organizational subscription'
    )
    
    seat_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Seat Subscription',
        help='The seat subscription this member uses',
        index=True
    )
    
    organizational_role = fields.Selection([
        ('primary_contact', 'Primary Contact'),
        ('billing_contact', 'Billing Contact'),
        ('seat_user', 'Seat User'),
        ('admin', 'Administrator'),
    ], string='Organizational Role',
       help='Role within the parent organization')

    # ==========================================
    # BASIC DATES
    # ==========================================
    
    membership_start_date = fields.Date(
        string='Membership Start',
        compute='_compute_membership_dates',
        store=True,
        help='Start date of current active membership'
    )
    
    membership_end_date = fields.Date(
        string='Membership End',
        compute='_compute_membership_dates',
        store=True,
        help='End date of current active membership'
    )
    
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
        help='Days until current membership expires'
    )

    # ==========================================
    # PORTAL ACCESS - Basic
    # ==========================================
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], string='Portal Access',
       compute='_compute_portal_access',
       store=True,
       help='Current portal access level')
    
    has_portal_access = fields.Boolean(
        string='Has Portal Access',
        compute='_compute_portal_access',
        store=True
    )

    # ==========================================
    # FEATURES & BENEFITS - Available to member
    # ==========================================
    
    available_features = fields.Many2many(
        'membership.feature',
        compute='_compute_available_features',
        string='Available Features',
        help='Features available through current memberships'
    )
    
    available_benefits = fields.Many2many(
        'membership.benefit',
        compute='_compute_available_benefits',
        string='Available Benefits',
        help='Benefits available through current memberships'
    )

    # ==========================================
    # GRACE PERIOD & LIFECYCLE FIELDS (from primary membership)
    # ==========================================
    
    paid_through_date = fields.Date(
        string='Paid Through',
        compute='_compute_membership_lifecycle',
        store=True,
        help='Date member is paid through'
    )
    
    grace_period_end_date = fields.Date(
        string='Grace Period Ends',
        compute='_compute_membership_lifecycle',
        store=True,
        help='Date when grace period ends'
    )
    
    suspend_end_date = fields.Date(
        string='Suspension Ends',
        compute='_compute_membership_lifecycle',
        store=True,
        help='Date when suspension period ends'
    )
    
    terminate_date = fields.Date(
        string='Termination Date',
        compute='_compute_membership_lifecycle',
        store=True,
        help='Final termination date'
    )
    
    is_in_grace_period = fields.Boolean(
        string='In Grace Period',
        compute='_compute_membership_lifecycle',
        store=True,
        help='Member is in grace period'
    )
    
    lifecycle_stage = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Lifecycle Stage',
       compute='_compute_membership_lifecycle',
       store=True)
    
    days_until_suspension = fields.Integer(
        string='Days Until Suspension',
        compute='_compute_membership_lifecycle'
    )
    
    days_until_termination = fields.Integer(
        string='Days Until Termination',
        compute='_compute_membership_lifecycle'
    )

    # ==========================================
    # COMPUTE METHODS - Core only
    # ==========================================

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state',
                 'seat_subscription_id', 'seat_subscription_id.state')
    def _compute_is_member(self):
        """Compute if partner is a member - includes seat memberships"""
        for partner in self:
            # Check direct memberships
            has_direct = bool(
                partner.membership_subscription_ids.filtered(
                    lambda s: s.state in ['trial', 'active']
                )
            )
            
            # Check seat membership
            has_seat = bool(
                partner.seat_subscription_id and 
                partner.seat_subscription_id.state in ['trial', 'active']
            )
            
            partner.is_member = has_direct or has_seat

    @api.depends('seat_subscription_id')
    def _compute_is_seat_member(self):
        """Determine if this is a seat member"""
        for partner in self:
            partner.is_seat_member = bool(partner.seat_subscription_id)

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.date_start',
                 'seat_subscription_id', 'seat_subscription_id.date_start')
    def _compute_member_since(self):
        """Find earliest membership start date - includes seat memberships"""
        for partner in self:
            dates = []
            
            # Direct memberships
            if partner.membership_subscription_ids:
                direct_dates = partner.membership_subscription_ids.filtered(
                    lambda s: s.date_start
                ).mapped('date_start')
                dates.extend(direct_dates)
            
            # Seat membership
            if partner.seat_subscription_id and partner.seat_subscription_id.date_start:
                dates.append(partner.seat_subscription_id.date_start)
            
            partner.member_since = min(dates) if dates else False

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state',
                 'seat_subscription_id', 'seat_subscription_id.state')
    def _compute_membership_state(self):
        """Compute overall membership state - includes seat memberships"""
        for partner in self:
            # Check direct subscriptions
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active']
            )
            
            # Check seat subscription
            if partner.seat_subscription_id and partner.seat_subscription_id.state in ['trial', 'active']:
                active_subs |= partner.seat_subscription_id
            
            if active_subs:
                if any(s.state == 'trial' for s in active_subs):
                    partner.membership_state = 'trial'
                else:
                    partner.membership_state = 'active'
            else:
                # Check for expired
                all_subs = partner.membership_subscription_ids
                if partner.seat_subscription_id:
                    all_subs |= partner.seat_subscription_id
                
                expired = all_subs.filtered(lambda s: s.state == 'expired')
                partner.membership_state = 'expired' if expired else 'none'

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state',
                 'seat_subscription_id', 'seat_subscription_id.state')
    def _compute_primary_membership(self):
        """Find current active primary membership - prioritizes direct over seat"""
        for partner in self:
            # First, try direct memberships
            primary = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active']
            ).sorted(lambda s: s.date_start, reverse=True)
            
            if primary:
                partner.primary_membership_id = primary[:1]
            elif partner.seat_subscription_id and partner.seat_subscription_id.state in ['trial', 'active']:
                # Fall back to seat subscription if no direct membership
                partner.primary_membership_id = partner.seat_subscription_id
            else:
                partner.primary_membership_id = False

    @api.depends('membership_subscription_ids', 'seat_subscription_id')
    def _compute_membership_counts(self):
        """Count total and active memberships - includes seat"""
        for partner in self:
            all_subs = partner.membership_subscription_ids
            if partner.seat_subscription_id:
                all_subs |= partner.seat_subscription_id
            
            partner.membership_count = len(all_subs)
            partner.active_membership_count = len(
                all_subs.filtered(lambda s: s.state in ['trial', 'active'])
            )

    @api.depends('primary_membership_id', 'primary_membership_id.membership_category_id',
                 'seat_subscription_id', 'seat_subscription_id.membership_category_id')
    def _compute_membership_category(self):
        """Get current member category - handles seat memberships"""
        for partner in self:
            if partner.primary_membership_id:
                partner.membership_category_id = (
                    partner.primary_membership_id.membership_category_id or
                    partner.primary_membership_id.plan_id.product_template_id.default_member_category_id
                )
            elif partner.seat_subscription_id:
                # Get category from seat subscription
                partner.membership_category_id = (
                    partner.seat_subscription_id.membership_category_id or
                    partner.seat_subscription_id.plan_id.product_template_id.default_member_category_id
                )
            else:
                partner.membership_category_id = False

    @api.depends('primary_membership_id', 'primary_membership_id.date_start',
                 'primary_membership_id.date_end')
    def _compute_membership_dates(self):
        """Get current membership dates"""
        for partner in self:
            if partner.primary_membership_id:
                partner.membership_start_date = partner.primary_membership_id.date_start
                partner.membership_end_date = partner.primary_membership_id.date_end
            else:
                partner.membership_start_date = False
                partner.membership_end_date = False

    @api.depends('membership_end_date')
    def _compute_days_until_expiry(self):
        """Calculate days until membership expires"""
        today = fields.Date.today()
        for partner in self:
            if partner.membership_end_date:
                delta = partner.membership_end_date - today
                partner.days_until_expiry = delta.days
            else:
                partner.days_until_expiry = 0

    @api.depends('membership_subscription_ids', 
                 'membership_subscription_ids.plan_id.product_template_id.portal_access_level',
                 'seat_subscription_id',
                 'seat_subscription_id.plan_id.product_template_id.portal_access_level')
    def _compute_portal_access(self):
        """Compute portal access level - includes seat subscriptions"""
        levels = ['none', 'basic', 'standard', 'premium']
        
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active']
            )
            
            # Add seat subscription if active
            if partner.seat_subscription_id and partner.seat_subscription_id.state in ['trial', 'active']:
                active_subs |= partner.seat_subscription_id
            
            if not active_subs:
                partner.portal_access_level = 'none'
                partner.has_portal_access = False
            else:
                access_levels = active_subs.mapped(
                    'plan_id.product_template_id.portal_access_level'
                )
                max_level = max(
                    access_levels, 
                    key=lambda x: levels.index(x) if x in levels else 0
                )
                partner.portal_access_level = max_level
                partner.has_portal_access = max_level != 'none'

    @api.depends('membership_subscription_ids', 
                 'membership_subscription_ids.plan_id.product_template_id.feature_ids',
                 'seat_subscription_id',
                 'seat_subscription_id.plan_id.product_template_id.feature_ids')
    def _compute_available_features(self):
        """Get all features from active subscriptions - includes seat subscriptions"""
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active']
            )
            
            # Add seat subscription if active
            if partner.seat_subscription_id and partner.seat_subscription_id.state in ['trial', 'active']:
                active_subs |= partner.seat_subscription_id
            
            features = active_subs.mapped('plan_id.product_template_id.feature_ids')
            partner.available_features = features

    @api.depends('membership_subscription_ids', 
                 'membership_subscription_ids.plan_id.product_template_id.benefit_ids',
                 'seat_subscription_id',
                 'seat_subscription_id.plan_id.product_template_id.benefit_ids',
                 'parent_organization_id',
                 'parent_organization_id.membership_subscription_ids',
                 'parent_organization_id.membership_subscription_ids.plan_id.product_template_id.benefit_ids')
    def _compute_available_benefits(self):
        """Get all benefits from active subscriptions - includes seat subscriptions and parent org"""
        for partner in self:
            benefits = self.env['membership.benefit']
            
            # Direct subscriptions
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active']
            )
            benefits |= active_subs.mapped('plan_id.product_template_id.benefit_ids')
            
            # Seat subscription
            if partner.seat_subscription_id and partner.seat_subscription_id.state in ['trial', 'active']:
                benefits |= partner.seat_subscription_id.plan_id.product_template_id.benefit_ids
            
            # Inherit from parent organization if seat member
            if partner.parent_organization_id and partner.is_seat_member:
                parent_subs = partner.parent_organization_id.membership_subscription_ids.filtered(
                    lambda s: s.state in ['trial', 'active']
                )
                benefits |= parent_subs.mapped('plan_id.product_template_id.benefit_ids')
            
            partner.available_benefits = benefits

    @api.depends('primary_membership_id', 'primary_membership_id.paid_through_date',
                 'primary_membership_id.grace_period_end_date',
                 'primary_membership_id.suspend_end_date',
                 'primary_membership_id.terminate_date',
                 'primary_membership_id.is_in_grace_period',
                 'primary_membership_id.lifecycle_stage',
                 'primary_membership_id.days_until_suspension',
                 'primary_membership_id.days_until_termination')
    def _compute_membership_lifecycle(self):
        """Get lifecycle information from primary membership"""
        for partner in self:
            if partner.primary_membership_id:
                partner.paid_through_date = partner.primary_membership_id.paid_through_date
                partner.grace_period_end_date = partner.primary_membership_id.grace_period_end_date
                partner.suspend_end_date = partner.primary_membership_id.suspend_end_date
                partner.terminate_date = partner.primary_membership_id.terminate_date
                partner.is_in_grace_period = partner.primary_membership_id.is_in_grace_period
                partner.lifecycle_stage = partner.primary_membership_id.lifecycle_stage
                partner.days_until_suspension = partner.primary_membership_id.days_until_suspension
                partner.days_until_termination = partner.primary_membership_id.days_until_termination
            else:
                partner.paid_through_date = False
                partner.grace_period_end_date = False
                partner.suspend_end_date = False
                partner.terminate_date = False
                partner.is_in_grace_period = False
                partner.lifecycle_stage = False
                partner.days_until_suspension = 0
                partner.days_until_termination = 0

    # ==========================================
    # COMPUTE METHODS - GEOGRAPHIC/CHAPTERS (NEW)
    # ==========================================
    
    @api.depends('country_id', 'state_id', 'zip')
    def _compute_eligible_chapters(self):
        """
        Compute which chapters this member is eligible for based on location
        Override in membership_chapter for actual geographic matching logic
        """
        for partner in self:
            # Base implementation: no geographic matching
            # membership_chapter module will override this
            partner.eligible_chapters = self.env['membership.category']
    
    @api.depends('membership_subscription_ids', 
                 'membership_subscription_ids.membership_category_id',
                 'membership_subscription_ids.membership_category_id.category_type')
    def _compute_chapter_count(self):
        """Count number of chapter memberships"""
        for partner in self:
            chapter_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.membership_category_id.category_type == 'chapter' and
                         s.state in ['trial', 'active']
            )
            partner.chapter_count = len(chapter_subs)

    # ==========================================
    # ACTIONS - Basic
    # ==========================================

    def action_view_memberships(self):
        """View all membership subscriptions"""
        self.ensure_one()
        
        all_subs = self.membership_subscription_ids
        if self.seat_subscription_id:
            all_subs |= self.seat_subscription_id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships'),
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [('id', 'in', all_subs.ids)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_view_eligible_chapters(self):
        """View chapters this member is eligible for"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Eligible Chapters'),
            'res_model': 'membership.category',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.eligible_chapters.ids)],
            'context': {'default_category_type': 'chapter'}
        }

    def check_feature_access(self, feature_code):
        """
        Check if partner has access to a specific feature
        
        Args:
            feature_code: Feature code to check
        
        Returns:
            bool: Has access
        """
        self.ensure_one()
        
        feature = self.env['membership.feature'].search([
            ('code', '=', feature_code)
        ], limit=1)
        
        if not feature:
            return False
        
        return feature in self.available_features

    def check_benefit_access(self, benefit_code):
        """
        Check if partner has access to a specific benefit
        
        Args:
            benefit_code: Benefit code to check
        
        Returns:
            bool: Has access
        """
        self.ensure_one()
        
        benefit = self.env['membership.benefit'].search([
            ('code', '=', benefit_code)
        ], limit=1)
        
        if not benefit:
            return False
        
        return benefit in self.available_benefits