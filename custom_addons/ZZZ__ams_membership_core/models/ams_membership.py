# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSMembership(models.Model):
    _name = 'ams.membership'
    _description = 'Association Membership Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char('Membership Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'))
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Member Information (integrated with ams_foundation)
    partner_id = fields.Many2one('res.partner', 'Member', required=True, tracking=True,
                                domain=[('is_member', '=', True)])
    member_type_id = fields.Many2one(related='partner_id.member_type_id', store=True, readonly=True)
    
    # Product and Sales Integration
    product_id = fields.Many2one('product.product', 'Membership Product', required=True,
                                domain=[('is_subscription_product', '=', True), 
                                       ('subscription_product_type', 'in', ['membership', 'chapter'])])
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order Line', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True)
    
    # Membership Timeline
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True)
    end_date = fields.Date('End Date', required=True, tracking=True)
    last_renewal_date = fields.Date('Last Renewal Date', tracking=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)
    
    # Enhanced Chapter Membership Identification
    is_chapter_membership = fields.Boolean(
        string='Chapter Membership', 
        compute='_compute_is_chapter_membership', 
        store=True,
        help='This membership is for a chapter'
    )
    
    membership_type = fields.Selection([
        ('regular', 'Regular Membership'),
        ('chapter', 'Chapter Membership'),
    ], string='Membership Type', compute='_compute_membership_type', store=True)
    
    # Enhanced Chapter-Specific Fields
    chapter_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('leadership', 'Leadership Access'),
        ('officer', 'Officer Access'),
        ('board', 'Board Member'),
    ], string='Chapter Access Level', 
       compute='_compute_chapter_info', store=True)
    
    chapter_type = fields.Selection([
        ('local', 'Local Chapter'),
        ('regional', 'Regional Chapter'),
        ('state', 'State Chapter'),
        ('national', 'National Chapter'),
        ('international', 'International Chapter'),
        ('special', 'Special Interest Chapter'),
        ('student', 'Student Chapter'),
        ('professional', 'Professional Chapter'),
    ], string='Chapter Type',
       compute='_compute_chapter_info', store=True)
    
    chapter_location = fields.Char('Chapter Location',
                                  compute='_compute_chapter_info', store=True)
    chapter_city = fields.Char('Chapter City', compute='_compute_chapter_info', store=True)
    chapter_state = fields.Char('Chapter State', compute='_compute_chapter_info', store=True)
    chapter_country_id = fields.Many2one('res.country', 'Chapter Country',
                                        compute='_compute_chapter_info', store=True)
    
    # Chapter Role and Responsibilities
    chapter_role = fields.Selection([
        ('member', 'Member'),
        ('volunteer', 'Volunteer'),
        ('committee_member', 'Committee Member'),
        ('officer', 'Officer'),
        ('board_member', 'Board Member'),
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
    ], string='Chapter Role', default='member', tracking=True)
    
    chapter_committee_ids = fields.Many2many('chapter.committee', string='Committees',
                                           help='Committees this member participates in')
    chapter_position_start_date = fields.Date('Position Start Date')
    chapter_position_end_date = fields.Date('Position End Date')
    
    # Enhanced Chapter Access and Benefits Tracking
    has_local_events_access = fields.Boolean('Local Events Access', 
                                            compute='_compute_chapter_access', store=True)
    has_chapter_documents_access = fields.Boolean('Chapter Documents Access',
                                                 compute='_compute_chapter_access', store=True)
    has_chapter_training_access = fields.Boolean('Chapter Training Access',
                                                compute='_compute_chapter_access', store=True)
    has_networking_access = fields.Boolean('Networking Access',
                                          compute='_compute_chapter_access', store=True)
    has_mentorship_access = fields.Boolean('Mentorship Access',
                                          compute='_compute_chapter_access', store=True)
    has_certification_access = fields.Boolean('Certification Access',
                                             compute='_compute_chapter_access', store=True)
    has_job_board_access = fields.Boolean('Job Board Access',
                                         compute='_compute_chapter_access', store=True)
    has_newsletter_access = fields.Boolean('Newsletter Access',
                                          compute='_compute_chapter_access', store=True)
    
    # Chapter Participation and Engagement
    chapter_events_attended = fields.Integer('Events Attended', default=0)
    chapter_volunteer_hours = fields.Float('Volunteer Hours', default=0.0)
    chapter_last_activity_date = fields.Date('Last Chapter Activity')
    chapter_engagement_score = fields.Float('Chapter Engagement Score', 
                                           compute='_compute_chapter_engagement', store=True)
    
    # Chapter Transfer and Migration Support
    previous_chapter_id = fields.Many2one('product.product', 'Previous Chapter',
                                         domain=[('subscription_product_type', '=', 'chapter')])
    transfer_reason = fields.Text('Transfer Reason')
    transfer_date = fields.Date('Transfer Date')
    
    # Chapter Geographic Preferences and Restrictions
    chapter_geographic_restriction = fields.Boolean('Geographic Restriction',
                                                   help='Member must be in chapter geographic area')
    member_zip_code = fields.Char('Member ZIP Code', related='partner_id.zip', store=True)
    member_state = fields.Char('Member State', related='partner_id.state_id.name', store=True)
    member_country_id = fields.Many2one('res.country', 'Member Country', 
                                       related='partner_id.country_id', store=True)
    geographic_distance_km = fields.Float('Distance from Chapter (km)',
                                         compute='_compute_geographic_distance')
    
    # Regular Membership Fields (existing)
    auto_renew = fields.Boolean('Auto Renew', default=True, tracking=True)
    renewal_interval = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Renewal Interval', default='annual', required=True)
    
    # Pricing and Payment
    membership_fee = fields.Monetary('Membership Fee', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    payment_status = fields.Selection([
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('failed', 'Failed'),
    ], string='Payment Status', default='pending', tracking=True)
    
    # Benefits and Features
    benefit_ids = fields.Many2many('ams.benefit', 'membership_benefit_rel', 
                                  'membership_id', 'benefit_id', string='Active Benefits')
    has_portal_access = fields.Boolean('Has Portal Access', compute='_compute_portal_access', store=True)
    
    # Lifecycle Dates (computed using foundation settings)
    grace_end_date = fields.Date('Grace Period End', compute='_compute_lifecycle_dates', store=True)
    suspension_end_date = fields.Date('Suspension End Date', compute='_compute_lifecycle_dates', store=True)
    termination_date = fields.Date('Termination Date', compute='_compute_lifecycle_dates', store=True)
    
    # Renewal Management
    renewal_ids = fields.One2many('ams.renewal', 'membership_id', 'Renewals')
    next_renewal_date = fields.Date('Next Renewal Date', compute='_compute_next_renewal_date', store=True)
    renewal_reminder_sent = fields.Boolean('Renewal Reminder Sent', default=False)
    
    # Enhanced Chapter Activity Tracking
    chapter_activity_ids = fields.One2many('chapter.activity', 'membership_id', 'Chapter Activities')
    chapter_meeting_attendance = fields.Float('Meeting Attendance %',
                                             compute='_compute_chapter_participation')
    chapter_committee_participation = fields.Boolean('Committee Participation',
                                                    compute='_compute_chapter_participation')
    
    # Additional Information
    notes = fields.Text('Internal Notes')
    tags = fields.Many2many('ams.membership.tag', string='Tags')
    
    # Computed Fields
    is_expired = fields.Boolean('Is Expired', compute='_compute_status_flags')
    days_until_expiry = fields.Integer('Days Until Expiry', compute='_compute_status_flags')
    membership_duration = fields.Integer('Duration (Days)', compute='_compute_membership_duration')

    # Enhanced display name computation
    @api.depends('partner_id', 'product_id', 'start_date', 'is_chapter_membership')
    def _compute_display_name(self):
        for membership in self:
            if membership.partner_id and membership.product_id:
                prefix = "Chapter: " if membership.is_chapter_membership else ""
                membership.display_name = f"{prefix}{membership.partner_id.name} - {membership.product_id.name}"
            else:
                membership.display_name = membership.name or _('New Membership')
    
    @api.depends('product_id.subscription_product_type')
    def _compute_is_chapter_membership(self):
        """Determine if this is a chapter membership"""
        for membership in self:
            membership.is_chapter_membership = (
                membership.product_id.subscription_product_type == 'chapter'
            )

    @api.depends('product_id.subscription_product_type')
    def _compute_membership_type(self):
        """Compute membership type based on product"""
        for membership in self:
            if membership.product_id.subscription_product_type == 'chapter':
                membership.membership_type = 'chapter'
            else:
                membership.membership_type = 'regular'

    @api.depends('product_id.chapter_access_level', 'product_id.chapter_type', 'product_id.chapter_location',
                 'product_id.chapter_city', 'product_id.chapter_state', 'product_id.chapter_country_id')
    def _compute_chapter_info(self):
        """Get enhanced chapter information from product"""
        for membership in self:
            if membership.is_chapter_membership:
                membership.chapter_access_level = membership.product_id.chapter_access_level
                membership.chapter_type = membership.product_id.chapter_type
                membership.chapter_location = membership.product_id.chapter_location
                membership.chapter_city = membership.product_id.chapter_city
                membership.chapter_state = membership.product_id.chapter_state
                membership.chapter_country_id = membership.product_id.chapter_country_id
            else:
                membership.chapter_access_level = False
                membership.chapter_type = False
                membership.chapter_location = False
                membership.chapter_city = False
                membership.chapter_state = False
                membership.chapter_country_id = False

    @api.depends('product_id.provides_local_events', 'product_id.provides_chapter_documents',
                 'product_id.provides_chapter_training', 'product_id.provides_networking_access',
                 'product_id.provides_mentorship', 'product_id.provides_certification',
                 'product_id.provides_job_board', 'product_id.provides_newsletter')
    def _compute_chapter_access(self):
        """Compute enhanced chapter access permissions"""
        for membership in self:
            if membership.is_chapter_membership:
                membership.has_local_events_access = membership.product_id.provides_local_events
                membership.has_chapter_documents_access = membership.product_id.provides_chapter_documents
                membership.has_chapter_training_access = membership.product_id.provides_chapter_training
                membership.has_networking_access = membership.product_id.provides_networking_access
                membership.has_mentorship_access = membership.product_id.provides_mentorship
                membership.has_certification_access = membership.product_id.provides_certification
                membership.has_job_board_access = membership.product_id.provides_job_board
                membership.has_newsletter_access = membership.product_id.provides_newsletter
            else:
                membership.has_local_events_access = False
                membership.has_chapter_documents_access = False
                membership.has_chapter_training_access = False
                membership.has_networking_access = False
                membership.has_mentorship_access = False
                membership.has_certification_access = False
                membership.has_job_board_access = False
                membership.has_newsletter_access = False

    @api.depends('chapter_events_attended', 'chapter_volunteer_hours', 'chapter_last_activity_date',
                 'chapter_meeting_attendance', 'chapter_committee_participation')
    def _compute_chapter_engagement(self):
        """Compute chapter engagement score"""
        for membership in self:
            if membership.is_chapter_membership:
                score = 0.0
                
                # Event attendance component (0-30 points)
                if membership.chapter_events_attended > 0:
                    score += min(membership.chapter_events_attended * 5, 30)
                
                # Volunteer hours component (0-25 points)
                if membership.chapter_volunteer_hours > 0:
                    score += min(membership.chapter_volunteer_hours * 2, 25)
                
                # Meeting attendance component (0-25 points)
                score += (membership.chapter_meeting_attendance / 100) * 25
                
                # Committee participation (0-20 points)
                if membership.chapter_committee_participation:
                    score += 20
                
                # Recent activity bonus (0-10 points)
                if membership.chapter_last_activity_date:
                    days_since = (fields.Date.today() - membership.chapter_last_activity_date).days
                    if days_since <= 30:
                        score += 10 - (days_since / 3)  # Decay over 30 days
                
                membership.chapter_engagement_score = min(score, 100)
            else:
                membership.chapter_engagement_score = 0.0

    @api.depends('chapter_activity_ids')
    def _compute_chapter_participation(self):
        """Compute chapter participation metrics"""
        for membership in self:
            if membership.is_chapter_membership:
                activities = membership.chapter_activity_ids
                
                # Calculate meeting attendance
                meeting_activities = activities.filtered(lambda a: a.activity_type == 'meeting')
                if meeting_activities:
                    attended = meeting_activities.filtered(lambda a: a.attended)
                    membership.chapter_meeting_attendance = (len(attended) / len(meeting_activities)) * 100
                else:
                    membership.chapter_meeting_attendance = 0.0
                
                # Check committee participation
                membership.chapter_committee_participation = bool(membership.chapter_committee_ids)
            else:
                membership.chapter_meeting_attendance = 0.0
                membership.chapter_committee_participation = False

    def _compute_geographic_distance(self):
        """Compute distance from chapter location (placeholder for geo calculation)"""
        for membership in self:
            if membership.is_chapter_membership:
                # This would integrate with a geocoding service
                # For now, set to 0 for members in same state/country
                if (membership.member_state == membership.chapter_state and 
                    membership.member_country_id == membership.chapter_country_id):
                    membership.geographic_distance_km = 0.0
                else:
                    membership.geographic_distance_km = 999999.0  # Placeholder for different state/country
            else:
                membership.geographic_distance_km = 0.0
    
    @api.depends('partner_id.portal_user_id')
    def _compute_portal_access(self):
        for membership in self:
            membership.has_portal_access = bool(membership.partner_id.portal_user_id)
    
    @api.depends('end_date', 'member_type_id')
    def _compute_lifecycle_dates(self):
        """Compute lifecycle dates using ams_foundation settings"""
        for membership in self:
            if not membership.end_date:
                membership.grace_end_date = False
                membership.suspension_end_date = False
                membership.termination_date = False
                continue
            
            # Get grace period from member type or foundation settings
            grace_days = membership._get_effective_grace_period()
            
            membership.grace_end_date = membership.end_date + timedelta(days=grace_days)
            membership.suspension_end_date = membership.grace_end_date + timedelta(days=60)
            membership.termination_date = membership.suspension_end_date + timedelta(days=30)
    
    def _get_effective_grace_period(self):
        """Get effective grace period using foundation settings"""
        self.ensure_one()
        
        # First check member type override
        if self.member_type_id and hasattr(self.member_type_id, 'grace_period_override') and self.member_type_id.grace_period_override:
            return getattr(self.member_type_id, 'grace_period_days', 30)
        
        # Then check foundation settings
        settings = self._get_ams_settings()
        if settings and hasattr(settings, 'grace_period_days'):
            return settings.grace_period_days
        
        # Default fallback
        return 30
    
    def _get_ams_settings(self):
        """Get active AMS settings from foundation"""
        return self.env['ams.settings'].search([('active', '=', True)], limit=1)
    
    @api.depends('end_date', 'auto_renew', 'renewal_interval')
    def _compute_next_renewal_date(self):
        for membership in self:
            if not membership.auto_renew or not membership.end_date:
                membership.next_renewal_date = False
                continue
            
            # Calculate next renewal based on interval
            if membership.renewal_interval == 'monthly':
                membership.next_renewal_date = membership.end_date + relativedelta(months=1)
            elif membership.renewal_interval == 'quarterly':
                membership.next_renewal_date = membership.end_date + relativedelta(months=3)
            elif membership.renewal_interval == 'semi_annual':
                membership.next_renewal_date = membership.end_date + relativedelta(months=6)
            else:  # annual
                membership.next_renewal_date = membership.end_date + relativedelta(years=1)
    
    @api.depends('end_date')
    def _compute_status_flags(self):
        today = fields.Date.today()
        for membership in self:
            if membership.end_date:
                membership.is_expired = membership.end_date < today
                membership.days_until_expiry = (membership.end_date - today).days
            else:
                membership.is_expired = False
                membership.days_until_expiry = 0
    
    @api.depends('start_date', 'end_date')
    def _compute_membership_duration(self):
        for membership in self:
            if membership.start_date and membership.end_date:
                membership.membership_duration = (membership.end_date - membership.start_date).days
            else:
                membership.membership_duration = 0

    @api.model
    def create(self, vals):
        """Override create to handle sequence and integrations"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.membership') or _('New')
        
        membership = super().create(vals)
        
        # Set benefits based on product configuration
        if membership.product_id and membership.product_id.benefit_ids:
            membership.benefit_ids = [(6, 0, membership.product_id.benefit_ids.ids)]
        
        # Enhanced single active membership handling (for regular memberships only)
        if membership.state == 'active':
            membership._ensure_single_active_membership()
        
        # Chapter-specific setup
        if membership.is_chapter_membership:
            membership._setup_chapter_membership()
        
        return membership
    
    def write(self, vals):
        """Override write to handle state changes and foundation integration"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for membership in self:
                membership._handle_state_change(vals['state'])
        
        # Handle chapter role changes
        if 'chapter_role' in vals:
            for membership in self:
                if membership.is_chapter_membership:
                    membership._handle_chapter_role_change(vals['chapter_role'])
        
        return result
    
    def _setup_chapter_membership(self):
        """Setup chapter-specific configuration"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            return
        
        # Set default chapter role if not set
        if not self.chapter_role:
            self.chapter_role = 'member'
        
        # Check geographic restrictions
        if self.product_id.chapter_geographic_restriction:
            self._check_geographic_eligibility()
        
        # Log chapter membership creation
        self.message_post(
            body=f"Chapter membership created for {self.product_id.name}",
            subject="Chapter Membership Created"
        )
    
    def _check_geographic_eligibility(self):
        """Check if member meets geographic requirements"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            return
        
        # Simple check - same state/country
        if (self.member_state != self.chapter_state or 
            self.member_country_id != self.chapter_country_id):
            _logger.warning(f"Geographic restriction warning for {self.partner_id.name} - "
                           f"Member in {self.member_state}, {self.member_country_id.name or 'Unknown'} "
                           f"joining chapter in {self.chapter_state}, {self.chapter_country_id.name or 'Unknown'}")
    
    def _handle_chapter_role_change(self, new_role):
        """Handle chapter role changes"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            return
        
        # Update position dates
        if new_role != 'member' and self.chapter_role == 'member':
            self.chapter_position_start_date = fields.Date.today()
        elif new_role == 'member' and self.chapter_role != 'member':
            self.chapter_position_end_date = fields.Date.today()
        
        # Log role change
        self.message_post(
            body=f"Chapter role changed from {self.chapter_role or 'None'} to {new_role}",
            subject="Chapter Role Changed"
        )
    
    def _ensure_single_active_membership(self):
        """Enhanced: Ensure only one active REGULAR membership per member - chapters are unlimited"""
        self.ensure_one()
        
        if self.state != 'active':
            _logger.debug(f"Membership {self.name} is not active, skipping single membership check")
            return
        
        # CRITICAL: Only enforce single membership rule for REGULAR memberships, not chapters
        if self.is_chapter_membership:
            _logger.debug(f"Membership {self.name} is a chapter membership - multiple chapters allowed")
            return
        
        # Find other active REGULAR memberships for same member (excluding current one and chapters)
        other_memberships = self.search([
            ('partner_id', '=', self.partner_id.id),
            ('product_id.subscription_product_type', '=', 'membership'),  # Only regular memberships
            ('state', '=', 'active'),
            ('id', '!=', self.id)
        ])
        
        if other_memberships:
            _logger.info(f"Found {len(other_memberships)} other active REGULAR memberships for {self.partner_id.name} - terminating them")
            
            for other_membership in other_memberships:
                other_membership.write({
                    'state': 'terminated',
                    'notes': (other_membership.notes or '') + f"\n\nTerminated on {fields.Date.today()} due to new active membership: {self.name}"
                })
                
                # Log the termination
                other_membership.message_post(
                    body=f"Membership terminated due to new active membership: {self.display_name}",
                    subject="Membership Terminated - Single Active Rule"
                )
                
                _logger.info(f"Terminated membership {other_membership.name} for {self.partner_id.name}")
            
            # Update notes on current membership
            current_notes = self.notes or ''
            if other_memberships:
                terminated_names = ', '.join(other_memberships.mapped('name'))
                self.notes = current_notes + f"\n\nActivated on {fields.Date.today()} - Terminated other memberships: {terminated_names}"
        else:
            _logger.debug(f"No other active regular memberships found for {self.partner_id.name}")
    
    def _handle_state_change(self, new_state):
        """Enhanced state change handling with chapter support"""
        self.ensure_one()
        
        if new_state == 'active':
            # Update foundation partner membership status (for regular memberships)
            if not self.is_chapter_membership:
                partner_vals = {
                    'member_status': 'active',
                    'membership_start_date': self.start_date,
                    'membership_end_date': self.end_date,
                }
                # Use context to prevent recursion
                self.partner_id.with_context(skip_portal_creation=True).write(partner_vals)
            
            # Enhanced single active membership handling
            self._ensure_single_active_membership()
            
            # Grant portal access if product allows and foundation settings enable it
            self._handle_portal_access_on_activation()
            
            # Apply engagement points for membership activation
            self._apply_engagement_points('membership_activation')
            
            # Chapter-specific activation
            if self.is_chapter_membership:
                self._handle_chapter_activation()
            
            # Log the activation
            membership_type_label = "Chapter membership" if self.is_chapter_membership else "Membership"
            self.message_post(
                body=f"{membership_type_label} activated - Active until {self.end_date}",
                subject=f"{membership_type_label} Activated"
            )
        
        elif new_state == 'terminated':
            # Only update partner status for regular memberships
            if not self.is_chapter_membership:
                # Check if this was the active membership
                if (self.partner_id.member_status == 'active' and 
                    hasattr(self.partner_id, 'current_membership_id') and
                    self.partner_id.current_membership_id == self):
                    
                    # Look for other active regular memberships
                    other_active = self.search([
                        ('partner_id', '=', self.partner_id.id),
                        ('product_id.subscription_product_type', '=', 'membership'),
                        ('state', '=', 'active'),
                        ('id', '!=', self.id)
                    ])
                    
                    if not other_active:
                        # No other active regular memberships, update partner status
                        self.partner_id.with_context(skip_portal_creation=True).write({
                            'member_status': 'terminated'
                        })
                        _logger.info(f"Set partner {self.partner_id.name} status to terminated - no other active memberships")
                    else:
                        _logger.info(f"Partner {self.partner_id.name} has {len(other_active)} other active memberships - maintaining active status")
            
            # Chapter-specific termination
            if self.is_chapter_membership:
                self._handle_chapter_termination()
            
            # Log the termination
            membership_type_label = "Chapter membership" if self.is_chapter_membership else "Membership"
            self.message_post(
                body=f"{membership_type_label} terminated",
                subject=f"{membership_type_label} Terminated"
            )
        
        elif new_state == 'grace':
            # Only update partner status for regular memberships
            if not self.is_chapter_membership:
                self.partner_id.with_context(skip_portal_creation=True).write({
                    'member_status': 'grace'
                })
            
            # Log grace period start
            membership_type_label = "Chapter membership" if self.is_chapter_membership else "Membership"
            self.message_post(
                body=f"{membership_type_label} entered grace period - expires {self.grace_end_date}",
                subject="Grace Period Started"
            )
        
        elif new_state == 'suspended':
            # Only update partner status for regular memberships
            if not self.is_chapter_membership:
                self.partner_id.with_context(skip_portal_creation=True).write({
                    'member_status': 'suspended'
                })
            
            # Chapter-specific suspension
            if self.is_chapter_membership:
                self._handle_chapter_suspension()
            
            # Log suspension
            membership_type_label = "Chapter membership" if self.is_chapter_membership else "Membership"
            self.message_post(
                body=f"{membership_type_label} suspended",
                subject=f"{membership_type_label} Suspended"
            )
    
    def _handle_chapter_activation(self):
        """Handle chapter membership activation"""
        self.ensure_one()
        
        # Check member limits
        if (self.product_id.chapter_member_limit > 0 and 
            self.product_id.chapter_member_count >= self.product_id.chapter_member_limit):
            _logger.warning(f"Chapter {self.product_id.name} is at member limit")
        
        # Create welcome activity
        self.env['chapter.activity'].create({
            'membership_id': self.id,
            'activity_type': 'membership',
            'activity_date': fields.Date.today(),
            'description': 'Chapter membership activated',
            'attended': True,
        })
    
    def _handle_chapter_termination(self):
        """Handle chapter membership termination"""
        self.ensure_one()
        
        # End any officer positions
        if self.chapter_role != 'member':
            self.chapter_position_end_date = fields.Date.today()
            self.chapter_role = 'member'
        
        # Clear committee memberships
        self.chapter_committee_ids = [(5, 0, 0)]
    
    def _handle_chapter_suspension(self):
        """Handle chapter membership suspension"""
        self.ensure_one()
        
        # Temporarily end officer positions but don't clear them
        if self.chapter_role != 'member':
            self.chapter_position_end_date = fields.Date.today()

    def _handle_portal_access_on_activation(self):
        """Handle portal access when membership becomes active"""
        self.ensure_one()
        
        # Check if product grants portal access
        if not self.product_id.grant_portal_access:
            return
        
        # Check if foundation settings allow auto portal user creation
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'auto_create_portal_users') or not settings.auto_create_portal_users:
            return
        
        # Use foundation's portal user creation method
        if not self.partner_id.portal_user_id and self.partner_id.email:
            try:
                self.partner_id.action_create_portal_user()
            except Exception as e:
                _logger.warning(f"Failed to create portal user for {self.partner_id.name}: {str(e)}")
    
    def _apply_engagement_points(self, rule_type, context_data=None):
        """Apply engagement points using foundation's engagement system"""
        self.ensure_one()
        
        # Check if engagement scoring is enabled in foundation settings
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'engagement_scoring_enabled') or not settings.engagement_scoring_enabled:
            return
        
        # Find applicable engagement rules
        engagement_rules = self.env['ams.engagement.rule'].search([
            ('rule_type', '=', rule_type),
            ('active', '=', True)
        ])
        
        for rule in engagement_rules:
            try:
                if hasattr(rule, 'apply_rule'):
                    success, message = rule.apply_rule(self.partner_id, context_data)
                    if success:
                        _logger.info(f"Applied engagement rule {rule.name} to {self.partner_id.name}")
                    else:
                        _logger.debug(f"Engagement rule {rule.name} not applied: {message}")
            except Exception as e:
                _logger.warning(f"Failed to apply engagement rule {rule.name}: {str(e)}")
    
    # Chapter-specific action methods
    def action_record_chapter_activity(self):
        """Record chapter activity"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            raise UserError(_("This is not a chapter membership."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Chapter Activity'),
            'res_model': 'chapter.activity',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
                'default_activity_date': fields.Date.today(),
            }
        }
    
    def action_transfer_chapter(self):
        """Transfer to another chapter"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            raise UserError(_("This is not a chapter membership."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Chapter Membership'),
            'res_model': 'chapter.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
            }
        }
    
    def action_chapter_dashboard(self):
        """Open chapter dashboard"""
        self.ensure_one()
        
        if not self.is_chapter_membership:
            raise UserError(_("This is not a chapter membership."))
        
        return {
            'name': f'Chapter Dashboard: {self.product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'chapter.dashboard.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
                'default_chapter_product_id': self.product_id.id,
            }
        }
    
    # Regular action methods (existing)
    def action_activate(self):
        """Activate membership"""
        for membership in self:
            if membership.state != 'draft':
                raise UserError(_("Only draft memberships can be activated."))
            
            membership.write({
                'state': 'active',
                'start_date': fields.Date.today(),
            })
    
    def action_suspend(self):
        """Suspend membership"""
        for membership in self:
            if membership.state not in ['active', 'grace']:
                raise UserError(_("Only active or grace period memberships can be suspended."))
            
            membership.write({'state': 'suspended'})
    
    def action_terminate(self):
        """Terminate membership"""
        for membership in self:
            membership.write({'state': 'terminated'})
    
    def action_renew(self):
        """Create renewal for this membership"""
        self.ensure_one()
        
        renewal = self.env['ams.renewal'].create({
            'membership_id': self.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': self._calculate_renewal_end_date(),
            'amount': self.membership_fee,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Renewal'),
            'res_model': 'ams.renewal',
            'res_id': renewal.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _calculate_renewal_end_date(self):
        """Calculate the new end date for renewal"""
        self.ensure_one()
        
        base_date = max(self.end_date, fields.Date.today())
        
        if self.renewal_interval == 'monthly':
            return base_date + relativedelta(months=1)
        elif self.renewal_interval == 'quarterly':
            return base_date + relativedelta(months=3)
        elif self.renewal_interval == 'semi_annual':
            return base_date + relativedelta(months=6)
        else:  # annual
            return base_date + relativedelta(years=1)
    
    def get_chapter_access_summary(self):
        """Get enhanced summary of chapter access for this membership"""
        self.ensure_one()
        if not self.is_chapter_membership:
            return "Not a chapter membership"
        
        access_items = []
        if self.has_local_events_access:
            access_items.append("Local Events")
        if self.has_chapter_documents_access:
            access_items.append("Chapter Documents")
        if self.has_chapter_training_access:
            access_items.append("Chapter Training")
        if self.has_networking_access:
            access_items.append("Networking")
        if self.has_mentorship_access:
            access_items.append("Mentorship")
        if self.has_certification_access:
            access_items.append("Certification")
        if self.has_job_board_access:
            access_items.append("Job Board")
        if self.has_newsletter_access:
            access_items.append("Newsletter")
        
        access_level = self.chapter_access_level.title() if self.chapter_access_level else 'Basic'
        role = self.chapter_role.replace('_', ' ').title() if self.chapter_role else 'Member'
        
        summary = f"{access_level} Access ({role})"
        if access_items:
            summary += f": {', '.join(access_items)}"
        
        return summary
    
    def get_chapter_participation_summary(self):
        """Get chapter participation summary"""
        self.ensure_one()
        if not self.is_chapter_membership:
            return "Not a chapter membership"
        
        summary_parts = []
        
        if self.chapter_events_attended:
            summary_parts.append(f"{self.chapter_events_attended} events attended")
        
        if self.chapter_volunteer_hours:
            summary_parts.append(f"{self.chapter_volunteer_hours:.1f} volunteer hours")
        
        if self.chapter_meeting_attendance:
            summary_parts.append(f"{self.chapter_meeting_attendance:.0f}% meeting attendance")
        
        if self.chapter_committee_ids:
            summary_parts.append(f"{len(self.chapter_committee_ids)} committee(s)")
        
        return "; ".join(summary_parts) if summary_parts else "No recorded participation"
    
    @api.model
    def create_from_invoice_payment(self, invoice_line):
        """Enhanced: Create membership from paid invoice line with better chapter support"""
        product = invoice_line.product_id.product_tmpl_id
        
        if not product.is_subscription_product or product.subscription_product_type not in ['membership', 'chapter']:
            return False
        
        # Check if membership already exists for this invoice line
        existing = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing:
            return existing
        
        partner = invoice_line.move_id.partner_id
        
        _logger.info(f"Creating {product.subscription_product_type} membership from invoice payment for {partner.name}")
        
        # Enhanced handling for chapter vs regular memberships
        if product.subscription_product_type == 'chapter':
            _logger.info(f"Creating chapter membership - multiple chapters allowed per member")
        else:
            # For regular memberships, terminate other active memberships BEFORE creating new one
            other_active_memberships = self.search([
                ('partner_id', '=', partner.id),
                ('product_id.subscription_product_type', '=', 'membership'),
                ('state', '=', 'active')
            ])
            
            if other_active_memberships:
                _logger.info(f"Found {len(other_active_memberships)} active memberships to terminate for {partner.name}")
                for old_membership in other_active_memberships:
                    old_membership.write({
                        'state': 'terminated',
                        'notes': (old_membership.notes or '') + f"\n\nTerminated on {fields.Date.today()} due to new membership purchase via invoice {invoice_line.move_id.name}"
                    })
                    _logger.info(f"Terminated existing membership {old_membership.name}")
        
        # Enhanced partner setup
        partner_vals = {}
        if not partner.is_member:
            partner_vals['is_member'] = True
            _logger.info(f"Setting is_member=True for {partner.name}")
        
        # Enhanced member type handling for chapters
        if not partner.member_type_id:
            if product.subscription_product_type == 'chapter':
                # Try to find chapter-specific member type first
                default_member_type = self.env['ams.member.type'].search([
                    '|', ('name', 'ilike', 'chapter'), ('name', 'ilike', 'local')
                ], limit=1)
            else:
                default_member_type = None
                
            if not default_member_type:
                default_member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', 'regular')
                ], limit=1)
            
            if not default_member_type:
                default_member_type = self.env['ams.member.type'].search([
                    ('name', 'ilike', 'individual')
                ], limit=1)
            
            if not default_member_type:
                default_member_type = self.env['ams.member.type'].search([], limit=1)
            
            if default_member_type:
                partner_vals['member_type_id'] = default_member_type.id
                _logger.info(f"Setting member type to: {default_member_type.name}")
        
        # Enhanced member number generation
        if not getattr(partner, 'member_number', None):
            if hasattr(partner, '_generate_member_number'):
                partner._generate_member_number()
            else:
                # Enhanced fallback member number generation
                try:
                    settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
                    if settings:
                        prefix = getattr(settings, 'member_number_prefix', 'M')
                        if product.subscription_product_type == 'chapter':
                            prefix = getattr(settings, 'chapter_member_prefix', prefix + 'C')
                        padding = getattr(settings, 'member_number_padding', 6)
                        sequence = self.env['ir.sequence'].next_by_code('ams.member.number')
                        if not sequence:
                            # Create a simple incremental number
                            last_member = self.env['res.partner'].search([
                                ('is_member', '=', True),
                                ('member_number', '!=', False)
                            ], order='id desc', limit=1)
                            next_num = 1
                            if last_member and last_member.member_number:
                                try:
                                    import re
                                    numbers = re.findall(r'\d+', last_member.member_number)
                                    if numbers:
                                        next_num = int(numbers[-1]) + 1
                                except:
                                    next_num = 1
                            sequence = str(next_num).zfill(padding)
                        member_number = f"{prefix}{sequence}"
                        partner_vals['member_number'] = member_number
                        _logger.info(f"Generated member number {member_number} for {partner.name}")
                except Exception as e:
                    _logger.warning(f"Could not generate member number for {partner.name}: {str(e)}")
        
        # Only set member status to active for regular memberships
        if product.subscription_product_type == 'membership':
            partner_vals['member_status'] = 'active'
        
        # Apply all partner updates at once
        if partner_vals:
            partner.with_context(skip_portal_creation=True).write(partner_vals)
        
        # Enhanced date calculation
        start_date = fields.Date.today()
        
        if product.subscription_period == 'annual':
            # Always set to December 31st of the current year
            current_year = start_date.year
            end_date = date(current_year, 12, 31)
            
            if start_date > end_date:
                end_date = date(current_year + 1, 12, 31)
                
        elif product.subscription_period == 'monthly':
            end_date = start_date + relativedelta(months=1) - timedelta(days=1)
        elif product.subscription_period == 'quarterly':
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        elif product.subscription_period == 'semi_annual':
            end_date = start_date + relativedelta(months=6) - timedelta(days=1)
        else:  # default to annual
            current_year = start_date.year
            end_date = date(current_year, 12, 31)
            if start_date > end_date:
                end_date = date(current_year + 1, 12, 31)
        
        # Update foundation partner dates (for regular memberships only)
        if product.subscription_product_type == 'membership':
            partner.with_context(skip_portal_creation=True).write({
                'membership_start_date': start_date,
                'membership_end_date': end_date,
            })
        
        # Enhanced membership record creation
        membership_vals = {
            'partner_id': partner.id,
            'product_id': invoice_line.product_id.id,
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'start_date': start_date,
            'end_date': end_date,
            'last_renewal_date': start_date,
            'membership_fee': invoice_line.price_subtotal,
            'payment_status': 'paid',
            'state': 'active',
            'auto_renew': product.auto_renew_default or True,
            'renewal_interval': product.subscription_period or 'annual',
        }
        
        # Enhanced chapter-specific setup
        if product.subscription_product_type == 'chapter':
            chapter_info = f"{product.chapter_type.title() if product.chapter_type else 'Local'} Chapter"
            if product.chapter_location:
                chapter_info += f" - {product.chapter_location}"
            if product.chapter_city:
                chapter_info += f", {product.chapter_city}"
            if product.chapter_state:
                chapter_info += f", {product.chapter_state}"
            
            notes = f"Chapter Membership: {chapter_info}"
            if product.chapter_contact_email:
                notes += f"\nChapter Contact: {product.chapter_contact_email}"
            if product.chapter_meeting_schedule:
                notes += f"\nMeetings: {product.chapter_meeting_schedule}"
            
            membership_vals['notes'] = notes
            membership_vals['chapter_role'] = 'member'
        
        membership = self.create(membership_vals)
        
        membership_type_label = "chapter membership" if product.subscription_product_type == 'chapter' else "membership"
        _logger.info(f"Created {membership_type_label} {membership.name} for {partner.name} "
                     f"from {start_date} to {end_date}")
        
        return membership

    @api.model
    def process_membership_lifecycle(self):
        """Enhanced membership lifecycle processing with chapter support"""
        _logger.info("Processing membership lifecycle transitions...")
        
        # Let foundation handle the main lifecycle transitions
        # Enhanced sync for both regular and chapter memberships
        today = fields.Date.today()
        
        # Sync active memberships with expired foundation member status
        expired_partners = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_status', '=', 'grace'),
            ('membership_end_date', '<', today)
        ])
        
        for partner in expired_partners:
            active_memberships = self.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'active')
            ])
            
            for membership in active_memberships:
                # Only sync regular memberships with partner status
                if not membership.is_chapter_membership:
                    membership.write({'state': 'grace'})
                    _logger.info(f"Synced regular membership {membership.name} to grace period")
        
        # Enhanced chapter-specific lifecycle processing
        self._process_chapter_lifecycle()
        
        # Sync lapsed members (regular memberships only)
        lapsed_partners = self.env['res.partner'].search([
            ('is_member', '=', True),
            ('member_status', '=', 'lapsed')
        ])
        
        for partner in lapsed_partners:
            grace_memberships = self.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'grace'),
                ('is_chapter_membership', '=', False)  # Only regular memberships
            ])
            
            for membership in grace_memberships:
                membership.write({'state': 'suspended'})
                _logger.info(f"Synced regular membership {membership.name} to suspended")
    
    def _process_chapter_lifecycle(self):
        """Process chapter-specific lifecycle transitions"""
        today = fields.Date.today()
        
        # Check chapter member limits and status
        chapter_products = self.env['product.template'].search([
            ('is_chapter_product', '=', True),
            ('chapter_status', '=', 'active')
        ])
        
        for chapter_product in chapter_products:
            active_members = self.search([
                ('product_id.product_tmpl_id', '=', chapter_product.id),
                ('state', '=', 'active')
            ])
            
            member_count = len(active_members)
            
            # Check minimum members requirement
            if (chapter_product.chapter_minimum_members > 0 and 
                member_count < chapter_product.chapter_minimum_members):
                _logger.warning(f"Chapter {chapter_product.name} below minimum members: "
                               f"{member_count}/{chapter_product.chapter_minimum_members}")
            
            # Update chapter member count
            if chapter_product.chapter_member_count != member_count:
                chapter_product.write({'chapter_member_count': member_count})
    
    @api.model
    def send_renewal_reminders(self):
        """Enhanced renewal reminders with chapter support"""
        settings = self._get_ams_settings()
        if not settings or not hasattr(settings, 'renewal_reminder_enabled') or not settings.renewal_reminder_enabled:
            return
        
        reminder_days = getattr(settings, 'renewal_reminder_days', 30)
        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        
        # Enhanced expiring memberships query (both regular and chapter)
        expiring_memberships = self.search([
            ('state', '=', 'active'),
            ('auto_renew', '=', False),
            ('end_date', '<=', reminder_date),
            ('renewal_reminder_sent', '=', False),
        ])
        
        for membership in expiring_memberships:
            # Different reminder templates for chapters vs regular memberships
            template_ref = 'ams_membership_core.email_chapter_renewal_reminder' if membership.is_chapter_membership else 'ams_membership_core.email_membership_renewal_reminder'
            
            try:
                template = self.env.ref(template_ref, raise_if_not_found=False)
                if template:
                    template.send_mail(membership.id, force_send=True)
                membership.renewal_reminder_sent = True
                _logger.info(f"Sent renewal reminder for {membership.display_name}")
            except Exception as e:
                _logger.error(f"Failed to send renewal reminder for {membership.display_name}: {str(e)}")
    
    # Enhanced constraints
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for membership in self:
            if membership.start_date and membership.end_date:
                if membership.end_date <= membership.start_date:
                    raise ValidationError(_("End date must be after start date."))
    
    @api.constrains('partner_id', 'product_id', 'state')
    def _check_single_active_membership(self):
        """Enhanced: Ensure only one active REGULAR membership per member - chapters are unlimited"""
        for membership in self:
            if (membership.state == 'active' and 
                membership.product_id.subscription_product_type == 'membership'):  # Only regular memberships
                
                active_count = self.search_count([
                    ('partner_id', '=', membership.partner_id.id),
                    ('product_id.subscription_product_type', '=', 'membership'),  # Only regular memberships
                    ('state', '=', 'active'),
                    ('id', '!=', membership.id)
                ])
                
                if active_count > 0:
                    raise ValidationError(
                        _("Member %s already has an active regular membership. "
                          "Only one active regular membership is allowed per member. "
                          "Chapter memberships are unlimited.") % membership.partner_id.name
                    )
    
    @api.constrains('chapter_role', 'is_chapter_membership')
    def _check_chapter_role(self):
        """Validate chapter role constraints"""
        for membership in self:
            if membership.chapter_role and membership.chapter_role != 'member':
                if not membership.is_chapter_membership:
                    raise ValidationError(_("Chapter roles can only be assigned to chapter memberships."))
                
                # Check for duplicate leadership roles within same chapter
                if membership.chapter_role in ['president', 'vice_president', 'secretary', 'treasurer']:
                    existing = self.search([
                        ('product_id', '=', membership.product_id.id),
                        ('chapter_role', '=', membership.chapter_role),
                        ('state', '=', 'active'),
                        ('id', '!=', membership.id)
                    ])
                    if existing:
                        raise ValidationError(
                            _("Chapter already has an active %s: %s") % 
                            (membership.chapter_role.replace('_', ' ').title(), existing[0].partner_id.name)
                        )
    
    @api.constrains('chapter_committee_ids', 'is_chapter_membership')
    def _check_chapter_committees(self):
        """Validate chapter committee assignments"""
        for membership in self:
            if membership.chapter_committee_ids and not membership.is_chapter_membership:
                raise ValidationError(_("Committee assignments can only be made for chapter memberships."))

    # Enhanced action methods
    def action_view_invoice(self):
        """View membership invoice"""
        self.ensure_one()
    
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this membership."))
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_view_sale_order(self):
        """View membership sale order"""
        self.ensure_one()

        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this membership."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }


class AMSMembershipTag(models.Model):
    _name = 'ams.membership.tag'
    _description = 'Membership Tag'
    
    name = fields.Char('Tag Name', required=True)
    color = fields.Integer('Color')
    active = fields.Boolean('Active', default=True)
    applies_to = fields.Selection([
        ('all', 'All Memberships'),
        ('regular', 'Regular Memberships Only'),
        ('chapter', 'Chapter Memberships Only'),
    ], string='Applies To', default='all')


# New models for enhanced chapter support
class ChapterCommittee(models.Model):
    _name = 'chapter.committee'
    _description = 'Chapter Committee'
    
    name = fields.Char('Committee Name', required=True)
    chapter_product_id = fields.Many2one('product.template', 'Chapter',
                                        domain=[('is_chapter_product', '=', True)],
                                        required=True)
    description = fields.Text('Description')
    chair_id = fields.Many2one('res.partner', 'Committee Chair')
    member_ids = fields.Many2many('ams.membership', 'chapter_committee_membership_rel',
                                 'committee_id', 'membership_id', 'Committee Members',
                                 domain=[('is_chapter_membership', '=', True)])
    meeting_schedule = fields.Text('Meeting Schedule')
    active = fields.Boolean('Active', default=True)


class ChapterActivity(models.Model):
    _name = 'chapter.activity'
    _description = 'Chapter Activity Record'
    
    name = fields.Char('Activity Name', compute='_compute_name', store=True)
    membership_id = fields.Many2one('ams.membership', 'Membership', required=True)
    partner_id = fields.Many2one(related='membership_id.partner_id', store=True)
    
    activity_type = fields.Selection([
        ('meeting', 'Chapter Meeting'),
        ('event', 'Chapter Event'),
        ('volunteer', 'Volunteer Activity'),
        ('training', 'Training Session'),
        ('networking', 'Networking Event'),
        ('committee', 'Committee Meeting'),
        ('membership', 'Membership Activity'),
        ('other', 'Other'),
    ], string='Activity Type', required=True)
    
    activity_date = fields.Date('Activity Date', required=True)
    description = fields.Text('Description')
    attended = fields.Boolean('Attended', default=False)
    hours = fields.Float('Hours', default=1.0)
    notes = fields.Text('Notes')
    
    @api.depends('activity_type', 'activity_date', 'membership_id')
    def _compute_name(self):
        for activity in self:
            activity.name = f"{activity.activity_type.replace('_', ' ').title()} - {activity.activity_date}"