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
        ('ams.membership.course', 'Course'),
        ('ams.membership.donation', 'Donation'),
    ], string='Membership Model', compute='_compute_membership_model', store=True,
       help="Model used to create membership records")

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
            'courses': 'ams.membership.course',
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

    def _compute_subscription_count(self):
        """Compute count of active subscriptions for this product"""
        for product in self:
            if product.is_subscription_product and product.membership_model:
                try:
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
                price = product.list_price
                
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

    def action_view_subscriptions(self):
        """View active subscriptions for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.membership_model:
            raise UserError(_("This is not a subscription product."))
        
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

    def create_membership_record(self, partner, invoice_line=None, start_date=None):
        """Create membership record for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.create_membership_record:
            return False
        
        if not self.membership_model:
            _logger.warning(f"No membership model defined for product {self.name}")
            return False
        
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