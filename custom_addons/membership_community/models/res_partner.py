# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ==========================================
    # MEMBERSHIP STATUS
    # Core membership flags
    # ==========================================
    
    is_member = fields.Boolean(
        string='Is Member',
        default=False,
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
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled')
    ], string='Membership Status',
       compute='_compute_membership_state',
       store=True,
       help='Current membership status')

    # ==========================================
    # MEMBERSHIP RECORDS
    # Links to membership records
    # ==========================================
    
    membership_ids = fields.One2many(
        'membership.record',
        'partner_id',
        string='Memberships',
        help='All membership records for this partner'
    )
    
    current_membership_id = fields.Many2one(
        'membership.record',
        string='Current Membership',
        compute='_compute_current_membership',
        store=True,
        help='Currently active primary membership'
    )
    
    membership_count = fields.Integer(
        string='Membership Count',
        compute='_compute_membership_counts',
        help='Total number of membership records'
    )
    
    active_membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_membership_counts',
        help='Number of currently active memberships'
    )

    # ==========================================
    # MEMBER CATEGORY & TYPE
    # Current member classification
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        compute='_compute_member_category',
        store=True,
        help='Current member category (Individual, Student, Corporate, etc.)'
    )
    
    member_category_type = fields.Selection(
        related='membership_category_id.category_type',
        string='Member Type',
        store=True,
        readonly=True
    )
    
    is_organizational_member = fields.Boolean(
        string='Organizational Member',
        compute='_compute_organizational_member',
        store=True,
        help='Partner is an organizational/corporate member'
    )
    
    is_student_member = fields.Boolean(
        string='Student Member',
        compute='_compute_member_flags',
        store=True,
        help='Partner is a student member'
    )
    
    is_honorary_member = fields.Boolean(
        string='Honorary Member',
        compute='_compute_member_flags',
        store=True,
        help='Partner is an honorary member'
    )
    
    is_retired_member = fields.Boolean(
        string='Retired Member',
        compute='_compute_member_flags',
        store=True,
        help='Partner is a retired member'
    )

    # ==========================================
    # SUBSCRIPTION INTEGRATION
    # Links to subscription module
    # ==========================================
    
    subscription_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Subscriptions',
        help='All subscriptions for this partner'
    )
    
    subscription_count = fields.Integer(
        string='Subscription Count',
        compute='_compute_subscription_count',
        help='Total number of subscriptions'
    )
    
    has_active_subscription = fields.Boolean(
        string='Has Active Subscription',
        compute='_compute_subscription_flags',
        help='Partner has at least one active subscription'
    )

    # ==========================================
    # MEMBERSHIP DATES & EXPIRY
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
    
    membership_expiry_date = fields.Date(
        string='Expiry Date',
        related='membership_end_date',
        store=True
    )
    
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
        help='Days until current membership expires'
    )
    
    membership_renewal_due = fields.Boolean(
        string='Renewal Due',
        compute='_compute_renewal_status',
        help='Membership is due for renewal (within 90 days)'
    )

    # ==========================================
    # PORTAL ACCESS
    # Member portal configuration
    # ==========================================
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('admin', 'Organization Admin')
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
    # ORGANIZATIONAL HIERARCHY
    # For organizational memberships
    # ==========================================
    
    parent_organization_id = fields.Many2one(
        'res.partner',
        string='Parent Organization',
        compute='_compute_organizational_structure',
        store=True,
        help='Organization this member belongs to (if seat member)'
    )
    
    is_seat_member = fields.Boolean(
        string='Seat Member',
        compute='_compute_organizational_structure',
        store=True,
        help='Member through organizational seat allocation'
    )
    
    organizational_role = fields.Char(
        string='Role in Organization',
        help='Job title or role within the organization'
    )
    
    employee_number = fields.Char(
        string='Employee Number',
        help='Employee ID within organization'
    )

    # ==========================================
    # MODULE INTEGRATION FLAGS
    # Check what extended modules are available
    # ==========================================
    
    has_professional_features = fields.Boolean(
        string='Professional Features',
        compute='_compute_feature_flags',
        help='Professional module features are available'
    )
    
    has_organizational_features = fields.Boolean(
        string='Organizational Features',
        compute='_compute_feature_flags',
        help='Organizational module features are available'
    )
    
    has_professional_profile = fields.Boolean(
        string='Has Professional Profile',
        compute='_compute_feature_flags',
        help='Partner has a professional profile'
    )
    
    has_credentials = fields.Boolean(
        string='Has Credentials',
        compute='_compute_feature_flags',
        help='Partner has professional credentials tracked'
    )
    
    has_ce_records = fields.Boolean(
        string='Has CE Records',
        compute='_compute_feature_flags',
        help='Partner has continuing education records'
    )

    # ==========================================
    # MEMBERSHIP BENEFITS ACCESS
    # What features/benefits member has access to
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
    # CHAPTERS & COMMITTEES
    # ==========================================
    
    chapter_membership_ids = fields.One2many(
        'membership.record',
        'partner_id',
        string='Chapter Memberships',
        domain=[('product_id.subscription_product_type', '=', 'chapter')],
        help='Chapter memberships'
    )
    
    chapter_count = fields.Integer(
        string='Chapters',
        compute='_compute_chapter_count',
        help='Number of chapters member belongs to'
    )

    # ==========================================
    # FINANCIAL SUMMARY
    # ==========================================
    
    total_membership_fees = fields.Monetary(
        string='Total Membership Fees',
        compute='_compute_financial_summary',
        help='Total membership fees paid all-time'
    )
    
    current_membership_value = fields.Monetary(
        string='Current Membership Value',
        compute='_compute_financial_summary',
        help='Value of current active memberships'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    # ==========================================
    # MEMBER ENGAGEMENT
    # ==========================================
    
    last_membership_activity = fields.Date(
        string='Last Activity',
        compute='_compute_engagement_metrics',
        help='Last membership-related activity'
    )
    
    engagement_score = fields.Float(
        string='Engagement Score',
        compute='_compute_engagement_metrics',
        help='Member engagement score (0-100)'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('membership_ids', 'membership_ids.state')
    def _compute_membership_state(self):
        """Compute overall membership state"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            
            if active_memberships:
                partner.membership_state = 'active'
                partner.is_member = True
            else:
                expired = partner.membership_ids.filtered(lambda m: m.state == 'expired')
                suspended = partner.membership_ids.filtered(lambda m: m.state == 'suspended')
                cancelled = partner.membership_ids.filtered(lambda m: m.state == 'cancelled')
                
                if suspended:
                    partner.membership_state = 'suspended'
                    partner.is_member = False
                elif expired:
                    partner.membership_state = 'expired'
                    partner.is_member = False
                elif cancelled:
                    partner.membership_state = 'cancelled'
                    partner.is_member = False
                else:
                    partner.membership_state = 'none'
                    partner.is_member = False

    @api.depends('membership_ids', 'membership_ids.join_date')
    def _compute_member_since(self):
        """Find earliest join date"""
        for partner in self:
            if partner.membership_ids:
                earliest = min(partner.membership_ids.mapped('join_date'), 
                             default=False)
                partner.member_since = earliest
            else:
                partner.member_since = False

    @api.depends('membership_ids', 'membership_ids.state')
    def _compute_current_membership(self):
        """Find current active primary membership"""
        for partner in self:
            active = partner.membership_ids.filtered(
                lambda m: m.state == 'active' and 
                         m.product_id.subscription_product_type == 'membership'
            ).sorted(key=lambda m: m.start_date, reverse=True)
            
            partner.current_membership_id = active[:1] if active else False

    @api.depends('membership_ids')
    def _compute_membership_counts(self):
        """Count total and active memberships"""
        for partner in self:
            partner.membership_count = len(partner.membership_ids)
            partner.active_membership_count = len(
                partner.membership_ids.filtered(lambda m: m.state == 'active')
            )

    @api.depends('current_membership_id', 'current_membership_id.membership_category_id')
    def _compute_member_category(self):
        """Get current member category"""
        for partner in self:
            if partner.current_membership_id:
                partner.membership_category_id = partner.current_membership_id.membership_category_id
            else:
                partner.membership_category_id = False

    @api.depends('membership_category_id', 'membership_category_id.category_type')
    def _compute_organizational_member(self):
        """Check if organizational member"""
        for partner in self:
            partner.is_organizational_member = (
                partner.membership_category_id.category_type == 'organizational'
            )

    @api.depends('membership_category_id', 'membership_category_id.category_type')
    def _compute_member_flags(self):
        """Compute member type flags"""
        for partner in self:
            cat_type = partner.membership_category_id.category_type
            partner.is_student_member = (cat_type == 'student')
            partner.is_honorary_member = (cat_type == 'honorary')
            partner.is_retired_member = (cat_type == 'retired')

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        """Count subscriptions"""
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)

    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_subscription_flags(self):
        """Check subscription status"""
        for partner in self:
            partner.has_active_subscription = bool(
                partner.subscription_ids.filtered(
                    lambda s: s.state in ['open', 'active']
                )
            )

    @api.depends('current_membership_id', 'current_membership_id.start_date',
                 'current_membership_id.end_date')
    def _compute_membership_dates(self):
        """Get current membership dates"""
        for partner in self:
            if partner.current_membership_id:
                partner.membership_start_date = partner.current_membership_id.start_date
                partner.membership_end_date = partner.current_membership_id.end_date
            else:
                partner.membership_start_date = False
                partner.membership_end_date = False

    @api.depends('membership_end_date')
    def _compute_days_until_expiry(self):
        """Calculate days until expiry"""
        today = fields.Date.today()
        for partner in self:
            if partner.membership_end_date:
                delta = partner.membership_end_date - today
                partner.days_until_expiry = delta.days
            else:
                partner.days_until_expiry = 0

    @api.depends('membership_end_date', 'membership_state')
    def _compute_renewal_status(self):
        """Check if renewal is due"""
        today = fields.Date.today()
        for partner in self:
            if partner.membership_state == 'active' and partner.membership_end_date:
                days_until = (partner.membership_end_date - today).days
                partner.membership_renewal_due = days_until <= 90
            else:
                partner.membership_renewal_due = False

    @api.depends('membership_ids', 'membership_ids.portal_access_level')
    def _compute_portal_access(self):
        """Compute portal access level (highest among active memberships)"""
        levels = ['none', 'basic', 'standard', 'premium', 'admin']
        
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            
            if not active_memberships:
                partner.portal_access_level = 'none'
                partner.has_portal_access = False
            else:
                access_levels = active_memberships.mapped('portal_access_level')
                # Get highest level
                max_level = max(access_levels, key=lambda x: levels.index(x) if x in levels else 0)
                partner.portal_access_level = max_level
                partner.has_portal_access = max_level != 'none'

    @api.depends('membership_ids', 'membership_ids.parent_membership_id')
    def _compute_organizational_structure(self):
        """Compute organizational structure"""
        for partner in self:
            # Check if any membership is a child (seat member)
            child_membership = partner.membership_ids.filtered(
                lambda m: m.parent_membership_id and m.state == 'active'
            )
            
            if child_membership:
                partner.is_seat_member = True
                # Get parent organization from parent membership
                parent_org = child_membership[0].parent_membership_id.partner_id
                partner.parent_organization_id = parent_org if parent_org.is_company else False
            else:
                partner.is_seat_member = False
                partner.parent_organization_id = False

    def _compute_feature_flags(self):
        """Check which extended modules are available"""
        for partner in self:
            # Check professional module
            prof_module = self.env['ir.module.module'].search([
                ('name', '=', 'membership_professional'),
                ('state', '=', 'installed')
            ], limit=1)
            partner.has_professional_features = bool(prof_module)
            
            # Check organizational module
            org_module = self.env['ir.module.module'].search([
                ('name', '=', 'membership_organizational'),
                ('state', '=', 'installed')
            ], limit=1)
            partner.has_organizational_features = bool(org_module)
            
            # Check for professional profile
            if partner.has_professional_features:
                if self.env['ir.model'].search([('model', '=', 'professional.profile')], limit=1):
                    partner.has_professional_profile = bool(
                        self.env['professional.profile'].search([
                            ('partner_id', '=', partner.id)
                        ], limit=1)
                    )
                    
                    # Check credentials
                    if self.env['ir.model'].search([('model', '=', 'professional.credential')], limit=1):
                        partner.has_credentials = bool(
                            self.env['professional.credential'].search([
                                ('partner_id', '=', partner.id)
                            ], limit=1)
                        )
                    else:
                        partner.has_credentials = False
                    
                    # Check CE records
                    if self.env['ir.model'].search([('model', '=', 'professional.continuing.education')], limit=1):
                        partner.has_ce_records = bool(
                            self.env['professional.continuing.education'].search([
                                ('partner_id', '=', partner.id)
                            ], limit=1)
                        )
                    else:
                        partner.has_ce_records = False
                else:
                    partner.has_professional_profile = False
                    partner.has_credentials = False
                    partner.has_ce_records = False
            else:
                partner.has_professional_profile = False
                partner.has_credentials = False
                partner.has_ce_records = False

    @api.depends('membership_ids', 'membership_ids.product_id.feature_ids')
    def _compute_available_features(self):
        """Get all features from active memberships"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            features = active_memberships.mapped('product_id.feature_ids')
            partner.available_features = features

    @api.depends('membership_ids', 'membership_ids.product_id.benefit_ids')
    def _compute_available_benefits(self):
        """Get all benefits from active memberships"""
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            benefits = active_memberships.mapped('product_id.benefit_ids')
            partner.available_benefits = benefits

    @api.depends('chapter_membership_ids')
    def _compute_chapter_count(self):
        """Count chapter memberships"""
        for partner in self:
            partner.chapter_count = len(partner.chapter_membership_ids.filtered(
                lambda m: m.state == 'active'
            ))

    def _compute_financial_summary(self):
        """Calculate financial metrics"""
        for partner in self:
            # Total fees all time
            partner.total_membership_fees = sum(
                partner.membership_ids.mapped('amount')
            )
            
            # Current active membership value
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            )
            partner.current_membership_value = sum(
                active_memberships.mapped('amount')
            )

    def _compute_engagement_metrics(self):
        """Calculate engagement metrics"""
        for partner in self:
            # Last activity
            if partner.membership_ids:
                latest = max(partner.membership_ids.mapped('write_date'), default=False)
                partner.last_membership_activity = latest.date() if latest else False
            else:
                partner.last_membership_activity = False
            
            # Engagement score (simplified - could be more sophisticated)
            score = 0
            if partner.is_member:
                score += 40
            if partner.chapter_count > 0:
                score += 20
            if partner.has_portal_access:
                score += 20
            if partner.has_professional_profile:
                score += 20
            
            partner.engagement_score = min(score, 100)

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_view_memberships(self):
        """View all membership records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships'),
            'res_model': 'membership.record',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }

    def action_view_subscriptions(self):
        """View all subscriptions"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }

    def action_create_membership(self):
        """Open wizard to create new membership"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'membership.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }

    def action_renew_membership(self):
        """Renew current membership"""
        self.ensure_one()
        
        if not self.current_membership_id:
            raise ValidationError(_("No active membership to renew."))
        
        return self.current_membership_id.action_renew()

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

    def get_membership_summary(self):
        """
        Get comprehensive membership summary
        
        Returns:
            dict: Membership data
        """
        self.ensure_one()
        
        return {
            'is_member': self.is_member,
            'member_since': self.member_since,
            'membership_state': self.membership_state,
            'category': self.membership_category_id.name if self.membership_category_id else None,
            'expiry_date': self.membership_end_date,
            'days_until_expiry': self.days_until_expiry,
            'renewal_due': self.membership_renewal_due,
            'portal_access': self.portal_access_level,
            'chapters': self.chapter_count,
            'features': len(self.available_features),
            'benefits': len(self.available_benefits),
        }

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('employee_number')
    def _check_employee_number_unique(self):
        """Ensure employee number is unique within organization"""
        for partner in self:
            if partner.employee_number and partner.parent_organization_id:
                duplicate = self.search([
                    ('parent_organization_id', '=', partner.parent_organization_id.id),
                    ('employee_number', '=', partner.employee_number),
                    ('id', '!=', partner.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        _("Employee number '%s' is already used in organization '%s'.") % 
                        (partner.employee_number, partner.parent_organization_id.name)
                    )