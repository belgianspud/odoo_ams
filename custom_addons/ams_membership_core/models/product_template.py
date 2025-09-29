# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Core Subscription Fields
    is_subscription_product = fields.Boolean('Subscription Product', default=False, tracking=True,
                                            help="Check this if this product represents a membership or subscription")
    
    product_class = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('subscription', 'Subscription'),
        ('publication', 'Publication'),
        ('exhibits', 'Exhibits'),
        ('advertising', 'Advertising'),
        ('donations', 'Donations'),
        ('courses', 'Courses'),
        ('sponsorship', 'Sponsorship'),
        ('event_booth', 'Event Booth'),
        ('newsletter', 'Newsletter'),
        ('services', 'Services')
    ], string='Product Class', tracking=True,
       help="Defines the type of subscription product this represents")

    # Membership Configuration
    member_type_id = fields.Many2one('ams.member.type', 'Associated Member Type',
                                   help="Member type this product is associated with")
    
    # Recurrence and Duration
    recurrence_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
        ('one_time', 'One Time')
    ], string='Recurrence Period', default='annual', tracking=True,
       help="How often this subscription renews")

    membership_period_type = fields.Selection([
        ('calendar', 'Calendar Year'),
        ('anniversary', 'Anniversary'),
        ('rolling', 'Rolling Period')
    ], string='Period Type', tracking=True,
       help="How membership periods are calculated. Leave blank to use member type or system default.")
    
    membership_duration = fields.Integer('Membership Duration (Days)', default=365,
                                       help="Number of days the membership is valid")

    # Pro-rating Configuration
    enable_prorating = fields.Boolean('Enable Pro-rating', 
                                     help="Calculate pro-rated pricing for partial periods")
    prorate_method = fields.Selection([
        ('daily', 'Daily Pro-rating'),
        ('monthly', 'Monthly Pro-rating')
    ], string='Pro-rate Method', default='monthly',
       help="Method for calculating pro-rated amounts")

    # Grace Period Override
    grace_period_override = fields.Boolean('Override Grace Period',
                                         help="Use custom grace period instead of system/member type default")
    grace_period_days = fields.Integer('Grace Period (Days)', default=30,
                                     help="Days after expiration before moving to lapsed status")

    # Membership Features and Restrictions
    requires_approval = fields.Boolean('Requires Approval', 
                                     help="Purchase requires manual approval before activation")
    auto_renewal_eligible = fields.Boolean('Auto Renewal Eligible', default=True,
                                         help="Can be set up for automatic renewal")
    
    # Multiple Membership Rules
    allow_multiple_active = fields.Boolean('Allow Multiple Active', 
                                         help="Allow multiple active subscriptions of this product per member")
    max_active_per_member = fields.Integer('Max Active Per Member', default=1,
                                         help="Maximum active subscriptions of this product per member (0 = unlimited)")

    # Upgrade/Downgrade Configuration
    allow_upgrades = fields.Boolean('Allow Upgrades', default=True,
                                  help="Allow upgrading to higher tier products")
    allow_downgrades = fields.Boolean('Allow Downgrades', default=True,
                                    help="Allow downgrading to lower tier products")
    upgrade_product_ids = fields.Many2many('product.template', 
                                         'product_upgrade_rel',
                                         'from_product_id', 'to_product_id',
                                         string='Upgrade Options',
                                         help="Products this can be upgraded to")
    downgrade_product_ids = fields.Many2many('product.template',
                                           'product_downgrade_rel', 
                                           'from_product_id', 'to_product_id',
                                           string='Downgrade Options',
                                           help="Products this can be downgraded to")

    # Renewal Configuration
    renewal_invoice_days_advance = fields.Integer('Renewal Invoice Days in Advance', 
                                                 help="Days before expiration to generate renewal invoice (leave blank to use system default)")
    auto_create_renewal_invoices = fields.Boolean('Auto Create Renewal Invoices',
                                                 help="Automatically create renewal invoices (leave blank to use system default)")

    # Portal and Member Access
    portal_access_required = fields.Boolean('Portal Access Required', default=True,
                                          help="Members need portal access to purchase this product")
    member_only = fields.Boolean('Member Only', 
                                help="Only existing members can purchase this product")
    guest_purchase_allowed = fields.Boolean('Guest Purchase Allowed', default=True,
                                          help="Non-members can purchase this product")

    # Pricing and Billing
    setup_fee = fields.Float('Setup Fee', default=0.0,
                            help="One-time setup fee charged on first purchase")
    cancellation_fee = fields.Float('Cancellation Fee', default=0.0,
                                   help="Fee charged when subscription is cancelled")
    
    # Integration and Automation
    create_membership_record = fields.Boolean('Create Membership Record', default=True,
                                            help="Automatically create membership record when invoice is paid")
    membership_model = fields.Selection([
        ('ams.membership.membership', 'Regular Membership'),
        ('ams.membership.chapter', 'Chapter Membership'),
        ('ams.membership.subscription', 'Subscription'),
        ('slide.channel.partner', 'Course Enrollment'),
        ('ams.membership.donation', 'Donation'),
    ], string='Membership Model', compute='_compute_membership_model', store=True,
       help="Model used to create membership records")

    # ===== COURSE INTEGRATION FIELDS =====
    
    # Course Link
    course_id = fields.Many2one('slide.channel', 'Associated Course',
                               domain=[('is_ams_course', '=', True)],
                               help="Link this product to an e-learning course")
    
    # Course-specific Configuration
    course_access_duration = fields.Integer('Course Access Duration (Days)', default=365,
                                          help="Days of access to course content")
    max_attendees_per_purchase = fields.Integer('Max Attendees Per Purchase', default=1,
                                              help="For corporate enrollments")
    auto_enroll_purchaser = fields.Boolean('Auto-Enroll Purchaser', default=True,
                                         help="Automatically enroll the purchaser in the course")
    
    # Member Pricing for Courses
    member_price = fields.Float('Member Price', default=0.0,
                               help="Special pricing for association members")
    price_difference = fields.Float('Price Difference', compute='_compute_price_difference', store=True,
                                   help="Difference between member and non-member pricing")
    
    # Website/Store Integration
    website_course_preview = fields.Boolean('Show Course Preview', default=True,
                                          help="Show course preview on website")
    course_syllabus = fields.Html('Course Syllabus', help="Displayed on website product page")
    instructor_bio = fields.Html('Instructor Bio')
    course_prerequisites = fields.Html('Prerequisites')
    
    # Course Statistics
    course_enrollments = fields.Integer('Course Enrollments', compute='_compute_course_stats')
    course_completion_rate = fields.Float('Course Completion Rate (%)', compute='_compute_course_stats')
    course_rating = fields.Float('Course Rating', compute='_compute_course_stats')

    # Computed Fields
    subscription_count = fields.Integer('Active Subscriptions', compute='_compute_subscription_count')
    revenue_monthly = fields.Float('Monthly Revenue', compute='_compute_revenue_stats')
    revenue_annual = fields.Float('Annual Revenue', compute='_compute_revenue_stats')

    @api.depends('product_class')
    def _compute_membership_model(self):
        """Compute the membership model based on product class"""
        model_mapping = {
            'membership': 'ams.membership.membership',
            'chapter': 'ams.membership.chapter',
            'subscription': 'ams.membership.subscription',
            'newsletter': 'ams.membership.subscription',
            'publication': 'ams.membership.subscription',
            'courses': 'slide.channel.partner',  # Use e-learning model
            'donations': 'ams.membership.donation',
            # Default for other types
            'exhibits': 'ams.membership.subscription',
            'advertising': 'ams.membership.subscription',
            'sponsorship': 'ams.membership.subscription',
            'event_booth': 'ams.membership.subscription',
            'services': 'ams.membership.subscription',
        }
        
        for product in self:
            product.membership_model = model_mapping.get(product.product_class, 'ams.membership.subscription')

    @api.depends('list_price', 'member_price')
    def _compute_price_difference(self):
        """Compute price difference between member and non-member pricing"""
        for product in self:
            if product.member_price > 0:
                product.price_difference = product.list_price - product.member_price
            else:
                product.price_difference = 0.0

    @api.depends('course_id')
    def _compute_course_stats(self):
        """Compute course-related statistics"""
        for product in self:
            if product.course_id:
                product.course_enrollments = len(product.course_id.channel_partner_ids)
                product.course_completion_rate = product.course_id.completion_rate
                product.course_rating = product.course_id.rating_avg
            else:
                product.course_enrollments = 0
                product.course_completion_rate = 0.0
                product.course_rating = 0.0

    def _compute_subscription_count(self):
        """Compute count of active subscriptions for this product"""
        for product in self:
            if product.is_subscription_product and product.membership_model:
                try:
                    if product.membership_model == 'slide.channel.partner':
                        # For courses, count enrollments
                        if product.course_id:
                            count = len(product.course_id.channel_partner_ids)
                        else:
                            count = 0
                    else:
                        # For other membership types
                        count = self.env[product.membership_model].search_count([
                            ('product_id', 'in', product.product_variant_ids.ids),
                            ('state', '=', 'active')
                        ])
                    product.subscription_count = count
                except:
                    product.subscription_count = 0
            else:
                product.subscription_count = 0

    def _compute_revenue_stats(self):
        """Compute revenue statistics"""
        for product in self:
            if product.is_subscription_product:
                # Calculate based on active subscriptions and pricing
                active_subs = product.subscription_count
                
                # Use member price if available and significant portion are members
                price = product.member_price if product.member_price > 0 else product.list_price
                
                if product.recurrence_period == 'monthly':
                    product.revenue_monthly = active_subs * price
                    product.revenue_annual = active_subs * price * 12
                elif product.recurrence_period == 'quarterly':
                    product.revenue_monthly = active_subs * price / 3
                    product.revenue_annual = active_subs * price * 4
                elif product.recurrence_period == 'semi_annual':
                    product.revenue_monthly = active_subs * price / 6
                    product.revenue_annual = active_subs * price * 2
                elif product.recurrence_period == 'annual':
                    product.revenue_monthly = active_subs * price / 12
                    product.revenue_annual = active_subs * price
                elif product.recurrence_period == 'one_time':
                    # For courses, estimate annual revenue
                    product.revenue_monthly = 0
                    product.revenue_annual = active_subs * price
                else:
                    product.revenue_monthly = 0
                    product.revenue_annual = 0
            else:
                product.revenue_monthly = 0
                product.revenue_annual = 0

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Set defaults when subscription product is enabled"""
        if self.is_subscription_product:
            if not self.type:
                self.type = 'service'
            if not self.product_class:
                self.product_class = 'membership'
            if not self.recurrence_period:
                self.recurrence_period = 'annual'
        else:
            # Clear subscription-specific fields
            self.product_class = False
            self.member_type_id = False
            self.recurrence_period = False
            self.membership_period_type = False

    @api.onchange('product_class')
    def _onchange_product_class(self):
        """Update fields based on product class"""
        if self.product_class:
            # Find a matching member type
            member_type = self.env['ams.member.type'].search([
                ('product_class', '=', self.product_class)
            ], limit=1)
            
            if member_type:
                self.member_type_id = member_type.id
                self.recurrence_period = member_type.recurrence_period
                self.membership_period_type = member_type.membership_period_type
                self.membership_duration = member_type.membership_duration
                self.list_price = member_type.base_annual_fee
                self.enable_prorating = member_type.enable_prorating
                self.requires_approval = member_type.requires_approval
                self.allow_multiple_active = member_type.allow_multiple_active
                self.max_active_per_member = member_type.max_active_per_member

            # Course-specific defaults
            if self.product_class == 'courses':
                self.type = 'service'
                self.recurrence_period = 'one_time'
                self.membership_duration = 365
                self.website_published = True
                self.auto_enroll_purchaser = True
                self.course_access_duration = 365
                
                # Set member pricing if not already set
                if not self.member_price and self.list_price:
                    self.member_price = self.list_price * 0.8  # 20% member discount by default

    @api.onchange('member_type_id')
    def _onchange_member_type_id(self):
        """Update fields based on selected member type"""
        if self.member_type_id:
            self.product_class = self.member_type_id.product_class
            self.recurrence_period = self.member_type_id.recurrence_period
            self.membership_period_type = self.member_type_id.membership_period_type
            self.membership_duration = self.member_type_id.membership_duration
            if self.list_price == 0:  # Only update if not already set
                self.list_price = self.member_type_id.base_annual_fee

    @api.onchange('course_id')
    def _onchange_course_id(self):
        """Update fields when course is selected"""
        if self.course_id:
            course = self.course_id
            
            # Update product info from course
            if not self.name or self.name == 'New':
                self.name = course.name
            if not self.description:
                self.description = course.description
            
            # Set pricing from course
            if course.non_member_price > 0:
                self.list_price = course.non_member_price
            if course.member_price > 0:
                self.member_price = course.member_price
            
            # Set access duration
            if course.access_duration_days:
                self.course_access_duration = course.access_duration_days
            
            # Set member restrictions
            self.member_only = course.requires_membership
            self.guest_purchase_allowed = course.guest_purchase_allowed

    # Course Integration Methods
    def get_course_price(self, partner=None):
        """Get appropriate course price for partner"""
        self.ensure_one()
        
        if self.product_class != 'courses':
            return self.list_price
        
        if not partner:
            return self.list_price
        
        if partner.is_member and self.member_price > 0:
            return self.member_price
        else:
            return self.list_price

    def _get_course_info_for_website(self):
        """Get course information for website display"""
        self.ensure_one()
        if self.product_class != 'courses' or not self.course_id:
            return {}
            
        course = self.course_id
        return {
            'course_name': course.name,
            'total_slides': len(course.slide_ids),
            'estimated_duration': course.estimated_duration_hours,
            'difficulty_level': course.difficulty_level,
            'course_level': course.course_level,
            'course_category': course.course_category,
            'ce_credits': course.ce_credits,
            'instructor': course.user_id.name,
            'enrollments': len(course.channel_partner_ids),
            'completion_rate': course.completion_rate,
            'rating': course.rating_avg,
            'prerequisites': course.prerequisites,
            'learning_objectives': course.learning_objectives,
            'member_price': self.member_price,
            'non_member_price': self.list_price,
            'requires_membership': course.requires_membership,
        }

    def check_course_enrollment_eligibility(self, partner):
        """Check if partner can enroll in course"""
        self.ensure_one()
        
        if self.product_class != 'courses' or not self.course_id:
            return {'eligible': True, 'issues': []}
        
        return self.course_id.check_enrollment_eligibility(partner)

    # Existing Methods (Enhanced)
    def get_effective_membership_period_type(self):
        """Get effective membership period type (product -> member type -> system default)"""
        self.ensure_one()
        if self.membership_period_type:
            return self.membership_period_type
        elif self.member_type_id and self.member_type_id.membership_period_type:
            return self.member_type_id.membership_period_type
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.default_membership_period_type if settings else 'calendar'

    def get_effective_grace_period(self):
        """Get effective grace period days (product -> member type -> system default)"""
        self.ensure_one()
        if self.grace_period_override:
            return self.grace_period_days
        elif self.member_type_id:
            return self.member_type_id.get_effective_grace_period()
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.grace_period_days if settings else 30

    def calculate_membership_end_date(self, start_date=None):
        """Calculate membership end date based on product configuration"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        period_type = self.get_effective_membership_period_type()
        
        if period_type == 'calendar':
            # Set to December 31 of the start date year
            return start_date.replace(month=12, day=31)
        elif period_type == 'anniversary':
            # Add duration to start date
            from datetime import timedelta
            return start_date + timedelta(days=self.membership_duration)
        elif period_type == 'rolling':
            # Rolling period - same as anniversary for now
            from datetime import timedelta
            return start_date + timedelta(days=self.membership_duration)
        else:
            # Default to anniversary
            from datetime import timedelta
            return start_date + timedelta(days=self.membership_duration)

    def calculate_prorated_price(self, start_date=None, end_date=None):
        """Calculate pro-rated price for partial period"""
        self.ensure_one()
        
        if not self.enable_prorating:
            return self.list_price
        
        if not start_date:
            start_date = fields.Date.today()
        
        if not end_date:
            end_date = self.calculate_membership_end_date(start_date)
        
        # Calculate the proportion of the period
        total_days = self.membership_duration
        actual_days = (end_date - start_date).days + 1  # Include both start and end date
        
        if actual_days <= 0:
            return 0
        
        if self.prorate_method == 'daily':
            proportion = actual_days / total_days
        elif self.prorate_method == 'monthly':
            # Round to nearest month
            actual_months = round(actual_days / 30.44)  # Average days per month
            total_months = round(total_days / 30.44)
            proportion = actual_months / total_months if total_months > 0 else 1
        else:
            proportion = actual_days / total_days
        
        return max(0, self.list_price * proportion)

    # Action Methods
    def action_view_subscriptions(self):
        """View active subscriptions for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.membership_model:
            raise UserError(_("This is not a subscription product."))
        
        if self.membership_model == 'slide.channel.partner':
            # For courses, show enrollments
            return {
                'name': _('Course Enrollments: %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'slide.channel.partner',
                'view_mode': 'list,form',
                'domain': [('channel_id', '=', self.course_id.id)] if self.course_id else [],
                'context': {'search_default_enrolled': 1},
            }
        else:
            return {
                'name': _('Active Subscriptions: %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': self.membership_model,
                'view_mode': 'list,form',
                'domain': [
                    ('product_id', 'in', self.product_variant_ids.ids),
                    ('state', 'in', ['active', 'grace'])
                ],
                'context': {
                    'default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False,
                    'search_default_active': 1
                },
            }

    def action_view_course_content(self):
        """View associated course content"""
        self.ensure_one()
        if not self.course_id:
            raise UserError(_("No course associated with this product."))
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Course Content'),
            'res_model': 'slide.channel',
            'res_id': self.course_id.id,
            'view_mode': 'form',
        }

    def action_sync_course_pricing(self):
        """Sync pricing with associated course"""
        self.ensure_one()
        
        if not self.course_id:
            raise UserError(_("No course associated with this product."))
        
        course = self.course_id
        
        # Update course pricing from product
        course.write({
            'member_price': self.member_price,
            'non_member_price': self.list_price,
            'requires_membership': self.member_only,
            'guest_purchase_allowed': self.guest_purchase_allowed,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pricing Synced'),
                'message': _('Course pricing has been synchronized with product pricing.'),
                'type': 'success'
            }
        }

    def create_membership_record(self, partner, invoice_line=None, start_date=None):
        """Create membership record for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.create_membership_record:
            return False
        
        if not self.membership_model:
            _logger.warning(f"No membership model defined for product {self.name}")
            return False
        
        # Handle course enrollments differently
        if self.membership_model == 'slide.channel.partner' and self.course_id:
            return self._create_course_enrollment(partner, invoice_line, start_date)
        else:
            return self._create_standard_membership(partner, invoice_line, start_date)

    def _create_course_enrollment(self, partner, invoice_line=None, start_date=None):
        """Create course enrollment"""
        self.ensure_one()
        
        if not self.course_id:
            _logger.warning(f"No course associated with product {self.name}")
            return False
        
        # Check if already enrolled
        existing = self.env['slide.channel.partner'].search([
            ('channel_id', '=', self.course_id.id),
            ('partner_id', '=', partner.id)
        ])
        
        if existing:
            _logger.info(f"Partner {partner.name} already enrolled in course {self.course_id.name}")
            return existing
        
        try:
            # Create enrollment
            enrollment_vals = {
                'channel_id': self.course_id.id,
                'partner_id': partner.id,
                'enrollment_date': start_date or fields.Date.today(),
            }
            
            enrollment = self.env['slide.channel.partner'].create(enrollment_vals)
            
            # Send welcome email if configured
            if self.course_id.enroll_msg:
                enrollment._send_enrollment_email()
            
            return enrollment
            
        except Exception as e:
            _logger.error(f"Failed to create course enrollment: {str(e)}")
            return False

    def _create_standard_membership(self, partner, invoice_line=None, start_date=None):
        """Create standard membership record"""
        self.ensure_one()
        
        # Calculate dates
        if not start_date:
            start_date = fields.Date.today()
        end_date = self.calculate_membership_end_date(start_date)
        
        # Prepare membership values
        membership_vals = {
            'partner_id': partner.id,
            'product_id': self.product_variant_ids[0].id if self.product_variant_ids else False,
            'member_type_id': self.member_type_id.id if self.member_type_id else False,
            'start_date': start_date,
            'end_date': end_date,
            'state': 'pending' if self.requires_approval else 'active',
            'invoice_line_id': invoice_line.id if invoice_line else False,
        }
        
        try:
            membership = self.env[self.membership_model].create(membership_vals)
            
            # Update partner member status if this is a membership product
            if self.product_class == 'membership' and not self.requires_approval:
                partner.write({
                    'is_member': True,
                    'member_type_id': self.member_type_id.id if self.member_type_id else partner.member_type_id.id,
                    'member_status': 'active',
                    'membership_start_date': start_date,
                    'membership_end_date': end_date,
                })
            
            return membership
            
        except Exception as e:
            _logger.error(f"Failed to create membership record: {str(e)}")
            return False

    # Constraints and Validations
    @api.constrains('is_subscription_product', 'product_class')
    def _check_subscription_product_class(self):
        """Ensure subscription products have a product class"""
        for product in self:
            if product.is_subscription_product and not product.product_class:
                raise ValidationError(_("Subscription products must have a product class defined."))

    @api.constrains('membership_duration')
    def _check_membership_duration(self):
        """Validate membership duration"""
        for product in self:
            if product.is_subscription_product and product.membership_duration <= 0:
                raise ValidationError(_("Membership duration must be greater than 0 days."))
            if product.membership_duration > 3650:  # 10 years
                raise ValidationError(_("Membership duration cannot exceed 10 years."))

    @api.constrains('grace_period_days')
    def _check_grace_period(self):
        """Validate grace period"""
        for product in self:
            if product.grace_period_override and product.grace_period_days < 0:
                raise ValidationError(_("Grace period cannot be negative."))
            if product.grace_period_override and product.grace_period_days > 365:
                raise ValidationError(_("Grace period cannot exceed 365 days."))

    @api.constrains('max_active_per_member')
    def _check_max_active_per_member(self):
        """Validate max active per member"""
        for product in self:
            if product.max_active_per_member < 0:
                raise ValidationError(_("Max active per member cannot be negative. Use 0 for unlimited."))

    @api.constrains('setup_fee', 'cancellation_fee')
    def _check_fees(self):
        """Validate fees"""
        for product in self:
            if product.setup_fee < 0:
                raise ValidationError(_("Setup fee cannot be negative."))
            if product.cancellation_fee < 0:
                raise ValidationError(_("Cancellation fee cannot be negative."))

    @api.constrains('member_price')
    def _check_member_price(self):
        """Validate member price"""
        for product in self:
            if product.member_price < 0:
                raise ValidationError(_("Member price cannot be negative."))

    @api.constrains('course_access_duration', 'max_attendees_per_purchase')
    def _check_course_settings(self):
        """Validate course-specific settings"""
        for product in self:
            if product.product_class == 'courses':
                if product.course_access_duration < 1:
                    raise ValidationError(_("Course access duration must be at least 1 day."))
                if product.max_attendees_per_purchase < 1:
                    raise ValidationError(_("Max attendees per purchase must be at least 1."))

    @api.constrains('upgrade_product_ids')
    def _check_upgrade_circular_reference(self):
        """Prevent circular upgrade references"""
        for product in self:
            if product.id in product.upgrade_product_ids.ids:
                raise ValidationError(_("Product cannot upgrade to itself."))

    @api.constrains('downgrade_product_ids')
    def _check_downgrade_circular_reference(self):
        """Prevent circular downgrade references"""
        for product in self:
            if product.id in product.downgrade_product_ids.ids:
                raise ValidationError(_("Product cannot downgrade to itself."))

    def copy(self, default=None):
        """Override copy to handle unique constraints"""
        if default is None:
            default = {}
        default.update({
            'name': _("%s (copy)") % self.name,
        })
        return super().copy(default)