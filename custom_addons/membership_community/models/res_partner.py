# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ==========================================
    # MEMBERSHIP STATUS
    # Core membership flags computed from subscriptions
    # ==========================================
    
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_is_member',
        store=True,
        help='Partner has at least one active membership subscription'
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
        ('pending', 'Pending'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Membership Status',
       compute='_compute_membership_state',
       store=True,
       help='Current membership status')

    # ==========================================
    # MEMBERSHIP SUBSCRIPTIONS
    # Links to subscription records (from subscription_management)
    # ==========================================
    
    membership_subscription_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Membership Subscriptions',
        domain=[('product_id.is_membership_product', '=', True)],
        help='All membership subscriptions for this partner'
    )
    
    primary_membership_id = fields.Many2one(
        'subscription.subscription',
        string='Primary Membership',
        compute='_compute_primary_membership',
        store=True,
        help='Current active primary (non-chapter) membership'
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
    # MEMBER CATEGORY & TYPE
    # Current member classification
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        compute='_compute_membership_category',
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
        compute='_compute_member_flags',
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

    # ==========================================
    # MEMBERSHIP DATES & EXPIRY
    # Computed from primary subscription
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
    # MEMBERSHIP BENEFITS & FEATURES
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
    # CHAPTERS
    # ==========================================
    
    chapter_membership_ids = fields.One2many(
        'subscription.subscription',
        'partner_id',
        string='Chapter Memberships',
        domain=[('product_id.subscription_product_type', '=', 'chapter')],
        help='Chapter membership subscriptions'
    )
    
    chapter_count = fields.Integer(
        string='Chapters',
        compute='_compute_chapter_count',
        help='Number of chapters member belongs to'
    )

    # ==========================================
    # ELIGIBILITY & VERIFICATION
    # ==========================================
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False,
        help='Member eligibility has been verified by staff'
    )
    
    eligibility_verified_by = fields.Many2one(
        'res.users',
        string='Verified By'
    )
    
    eligibility_verified_date = fields.Date(
        string='Verification Date'
    )
    
    membership_notes = fields.Text(
        string='Membership Notes',
        help='Internal notes about this member'
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
    # COMPUTE METHODS
    # ==========================================

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state')
    def _compute_is_member(self):
        """Compute if partner is a member based on active subscriptions"""
        for partner in self:
            partner.is_member = bool(
                partner.membership_subscription_ids.filtered(
                    lambda s: s.state in ['open', 'active']
                )
            )

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.date_start')
    def _compute_member_since(self):
        """Find earliest membership start date"""
        for partner in self:
            if partner.membership_subscription_ids:
                dates = partner.membership_subscription_ids.filtered(
                    lambda s: s.date_start
                ).mapped('date_start')
                partner.member_since = min(dates) if dates else False
            else:
                partner.member_since = False

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state')
    def _compute_membership_state(self):
        """Compute overall membership state"""
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active']
            )
            
            if active_subs:
                partner.membership_state = 'active'
            else:
                # Check for other states
                pending = partner.membership_subscription_ids.filtered(
                    lambda s: s.state == 'pending'
                )
                if pending:
                    partner.membership_state = 'pending'
                else:
                    expired = partner.membership_subscription_ids.filtered(
                        lambda s: s.state == 'close'
                    )
                    cancelled = partner.membership_subscription_ids.filtered(
                        lambda s: s.state == 'cancel'
                    )
                    
                    if expired:
                        partner.membership_state = 'expired'
                    elif cancelled:
                        partner.membership_state = 'cancelled'
                    else:
                        partner.membership_state = 'none'

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.state')
    def _compute_primary_membership(self):
        """Find current active primary membership"""
        for partner in self:
            # Get primary (non-chapter) active memberships
            primary = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active'] and 
                         s.product_id.subscription_product_type == 'membership'
            ).sorted(lambda s: s.date_start, reverse=True)
            
            partner.primary_membership_id = primary[:1] if primary else False

    @api.depends('membership_subscription_ids')
    def _compute_membership_counts(self):
        """Count total and active memberships"""
        for partner in self:
            partner.membership_count = len(partner.membership_subscription_ids)
            partner.active_membership_count = len(
                partner.membership_subscription_ids.filtered(
                    lambda s: s.state in ['open', 'active']
                )
            )

    @api.depends('primary_membership_id', 'primary_membership_id.membership_category_id')
    def _compute_membership_category(self):
        """Get current member category from primary subscription"""
        for partner in self:
            if partner.primary_membership_id:
                # Get category from subscription or product default
                partner.membership_category_id = (
                    partner.primary_membership_id.membership_category_id or
                    partner.primary_membership_id.product_id.default_member_category_id
                )
            else:
                partner.membership_category_id = False

    @api.depends('membership_category_id', 'membership_category_id.category_type')
    def _compute_member_flags(self):
        """Compute member type flags"""
        for partner in self:
            cat_type = partner.membership_category_id.category_type if partner.membership_category_id else False
            partner.is_organizational_member = (cat_type == 'organizational')
            partner.is_student_member = (cat_type == 'student')
            partner.is_honorary_member = (cat_type == 'honorary')

    @api.depends('primary_membership_id', 'primary_membership_id.date_start',
                 'primary_membership_id.date_end')
    def _compute_membership_dates(self):
        """Get current membership dates from primary subscription"""
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

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.product_id.portal_access_level')
    def _compute_portal_access(self):
        """Compute portal access level (highest among active subscriptions)"""
        levels = ['none', 'basic', 'standard', 'premium', 'admin']
        
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active']
            )
            
            if not active_subs:
                partner.portal_access_level = 'none'
                partner.has_portal_access = False
            else:
                access_levels = active_subs.mapped('product_id.portal_access_level')
                # Get highest level
                max_level = max(access_levels, key=lambda x: levels.index(x) if x in levels else 0)
                partner.portal_access_level = max_level
                partner.has_portal_access = max_level != 'none'

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.product_id.feature_ids')
    def _compute_available_features(self):
        """Get all features from active subscriptions"""
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active']
            )
            features = active_subs.mapped('product_id.feature_ids')
            partner.available_features = features

    @api.depends('membership_subscription_ids', 'membership_subscription_ids.product_id.benefit_ids')
    def _compute_available_benefits(self):
        """Get all benefits from active subscriptions"""
        for partner in self:
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active']
            )
            benefits = active_subs.mapped('product_id.benefit_ids')
            partner.available_benefits = benefits

    @api.depends('chapter_membership_ids')
    def _compute_chapter_count(self):
        """Count chapter memberships"""
        for partner in self:
            partner.chapter_count = len(
                partner.chapter_membership_ids.filtered(
                    lambda s: s.state in ['open', 'active']
                )
            )

    def _compute_financial_summary(self):
        """Calculate financial metrics"""
        for partner in self:
            # Total fees all time (from invoices)
            invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_line_ids.subscription_id', 'in', partner.membership_subscription_ids.ids)
            ])
            partner.total_membership_fees = sum(invoices.mapped('amount_total'))
            
            # Current active membership value
            active_subs = partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['open', 'active']
            )
            partner.current_membership_value = sum(active_subs.mapped('recurring_total'))

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_view_memberships(self):
        """View all membership subscriptions"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships'),
            'res_model': 'subscription.subscription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.membership_subscription_ids.ids)],
            'context': {'default_partner_id': self.id}
        }

    def action_view_subscriptions(self):
        """View all subscriptions (includes non-membership)"""
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
        """Open wizard to create new membership subscription"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'membership.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }

    def action_renew_membership(self):
        """Renew current primary membership"""
        self.ensure_one()
        
        if not self.primary_membership_id:
            raise ValidationError(_("No active membership to renew."))
        
        # Use subscription renewal mechanism
        return self.primary_membership_id.action_renew()

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
            'category_code': self.membership_category_id.code if self.membership_category_id else None,
            'expiry_date': self.membership_end_date,
            'days_until_expiry': self.days_until_expiry,
            'renewal_due': self.membership_renewal_due,
            'portal_access': self.portal_access_level,
            'chapters': self.chapter_count,
            'features': len(self.available_features),
            'benefits': len(self.available_benefits),
            'primary_membership_id': self.primary_membership_id.id if self.primary_membership_id else False,
        }