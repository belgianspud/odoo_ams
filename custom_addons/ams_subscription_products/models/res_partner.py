# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """
    Enhanced partner model with comprehensive subscription management for AMS.
    Tracks customer subscription history, preferences, and analytics.
    """
    _inherit = 'res.partner'

    # ========================================================================
    # SUBSCRIPTION STATUS AND TRACKING
    # ========================================================================

    has_active_subscriptions = fields.Boolean(
        string="Has Active Subscriptions",
        compute='_compute_subscription_status',
        store=True,
        help="Whether customer has any active subscriptions"
    )

    subscription_count = fields.Integer(
        string="Total Subscriptions",
        compute='_compute_subscription_counts',
        help="Total number of subscriptions (all time)"
    )

    active_subscription_count = fields.Integer(
        string="Active Subscriptions",
        compute='_compute_subscription_counts',
        help="Number of currently active subscriptions"
    )

    expired_subscription_count = fields.Integer(
        string="Expired Subscriptions",
        compute='_compute_subscription_counts',
        help="Number of expired subscriptions"
    )

    subscription_status_summary = fields.Char(
        string="Subscription Status",
        compute='_compute_subscription_status_summary',
        help="Summary of customer's subscription status"
    )

    # ========================================================================
    # SUBSCRIPTION FINANCIAL TRACKING
    # ========================================================================

    total_subscription_value = fields.Monetary(
        string="Total Subscription Value",
        compute='_compute_subscription_financials',
        help="Total value of all subscriptions (lifetime)"
    )

    annual_subscription_value = fields.Monetary(
        string="Annual Subscription Value",
        compute='_compute_subscription_financials',
        help="Current annual subscription value"
    )

    average_subscription_price = fields.Monetary(
        string="Average Subscription Price",
        compute='_compute_subscription_financials',
        help="Average price across all subscriptions"
    )

    last_subscription_payment = fields.Monetary(
        string="Last Payment Amount",
        compute='_compute_subscription_financials',
        help="Amount of most recent subscription payment"
    )

    subscription_payment_total = fields.Monetary(
        string="Total Payments",
        compute='_compute_subscription_financials',
        help="Total amount paid for subscriptions"
    )

    outstanding_subscription_amount = fields.Monetary(
        string="Outstanding Amount",
        compute='_compute_subscription_financials',
        help="Outstanding subscription payment amount"
    )

    # ========================================================================
    # SUBSCRIPTION HISTORY AND LIFECYCLE
    # ========================================================================

    first_subscription_date = fields.Date(
        string="First Subscription Date",
        compute='_compute_subscription_history',
        store=True,
        help="Date of customer's first subscription"
    )

    last_renewal_date = fields.Date(
        string="Last Renewal Date",
        compute='_compute_subscription_history',
        store=True,
        help="Date of most recent subscription renewal"
    )

    next_renewal_date = fields.Date(
        string="Next Renewal Due",
        compute='_compute_subscription_history',
        store=True,
        help="Next subscription renewal due date"
    )

    subscription_tenure_months = fields.Integer(
        string="Subscription Tenure (Months)",
        compute='_compute_subscription_history',
        help="Total months as a subscriber"
    )

    subscription_churn_risk = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ], string="Churn Risk",
       compute='_compute_churn_risk',
       help="Calculated churn risk based on subscription behavior")

    # ========================================================================
    # SUBSCRIPTION PREFERENCES
    # ========================================================================

    subscription_auto_renewal_preference = fields.Selection([
        ('enabled', 'Auto-Renewal Enabled'),
        ('disabled', 'Auto-Renewal Disabled'),
        ('ask_each_time', 'Ask Each Time'),
    ], string="Auto-Renewal Preference",
       default='enabled',
       help="Customer's preference for automatic renewal")

    subscription_communication_preference = fields.Selection([
        ('email', 'Email Only'),
        ('phone', 'Phone Only'),
        ('both', 'Email and Phone'),
        ('none', 'No Communications'),
    ], string="Communication Preference",
       default='email',
       help="Preferred method for subscription communications")

    renewal_reminder_days = fields.Selection([
        ('7', '7 Days Before'),
        ('15', '15 Days Before'),
        ('30', '30 Days Before'),
        ('custom', 'Custom Schedule'),
    ], string="Renewal Reminder Timing",
       default='30',
       help="When to send renewal reminders")

    subscription_billing_day = fields.Integer(
        string="Preferred Billing Day",
        default=1,
        help="Preferred day of month for subscription billing (1-28)"
    )

    subscription_portal_access = fields.Boolean(
        string="Portal Access Granted",
        compute='_compute_portal_access',
        help="Whether customer has portal access from subscriptions"
    )

    # ========================================================================
    # SUBSCRIPTION CONTENT AND ACCESS
    # ========================================================================

    subscription_access_levels = fields.Char(
        string="Access Levels",
        compute='_compute_subscription_access',
        help="Comma-separated list of current access levels"
    )

    subscription_content_types = fields.Char(
        string="Content Types",
        compute='_compute_subscription_access',
        help="Types of subscription content customer has access to"
    )

    concurrent_users_allowed = fields.Integer(
        string="Concurrent Users Allowed",
        compute='_compute_subscription_access',
        help="Total concurrent users across all subscriptions"
    )

    download_limits_monthly = fields.Integer(
        string="Monthly Download Limit",
        compute='_compute_subscription_access',
        help="Combined monthly download limits"
    )

    # ========================================================================
    # SUBSCRIPTION COMMUNICATION AND NOTIFICATIONS
    # ========================================================================

    subscription_welcome_sent = fields.Boolean(
        string="Welcome Email Sent",
        default=False,
        help="Whether subscription welcome email has been sent"
    )

    renewal_reminders_sent = fields.Integer(
        string="Renewal Reminders Sent",
        default=0,
        help="Total renewal reminders sent to this customer"
    )

    last_subscription_communication_date = fields.Date(
        string="Last Communication Date",
        help="Date of last subscription-related communication"
    )

    subscription_notes = fields.Text(
        string="Subscription Notes",
        help="Internal notes about customer's subscriptions"
    )

    # ========================================================================
    # MEMBER-SPECIFIC SUBSCRIPTION DATA
    # ========================================================================

    member_subscription_discount_total = fields.Monetary(
        string="Member Discount Total",
        compute='_compute_member_subscription_benefits',
        help="Total member discounts received on subscriptions"
    )

    member_subscription_savings_annual = fields.Monetary(
        string="Annual Member Savings",
        compute='_compute_member_subscription_benefits',
        help="Annual savings from member subscription discounts"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('subscription_ids.stage_category')
    def _compute_subscription_status(self):
        """Compute subscription status."""
        for partner in self:
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.stage_category == 'progress'
            )
            partner.has_active_subscriptions = bool(active_subscriptions)

    @api.depends('subscription_ids', 'subscription_ids.stage_category')
    def _compute_subscription_counts(self):
        """Compute subscription counts."""
        for partner in self:
            subscriptions = partner.subscription_ids
            partner.subscription_count = len(subscriptions)
            partner.active_subscription_count = len(
                subscriptions.filtered(lambda s: s.stage_category == 'progress')
            )
            partner.expired_subscription_count = len(
                subscriptions.filtered(lambda s: s.stage_category == 'closed')
            )

    @api.depends('subscription_count', 'active_subscription_count', 'expired_subscription_count')
    def _compute_subscription_status_summary(self):
        """Generate subscription status summary."""
        for partner in self:
            if not partner.subscription_count:
                partner.subscription_status_summary = "No Subscriptions"
            elif partner.active_subscription_count == 0:
                partner.subscription_status_summary = f"No Active ({partner.expired_subscription_count} Expired)"
            elif partner.active_subscription_count == 1:
                expired_text = f", {partner.expired_subscription_count} Expired" if partner.expired_subscription_count else ""
                partner.subscription_status_summary = f"1 Active{expired_text}"
            else:
                expired_text = f", {partner.expired_subscription_count} Expired" if partner.expired_subscription_count else ""
                partner.subscription_status_summary = f"{partner.active_subscription_count} Active{expired_text}"

    @api.depends('subscription_ids', 'subscription_ids.recurring_total', 'subscription_ids.stage_category')
    def _compute_subscription_financials(self):
        """Compute subscription financial data."""
        for partner in self:
            subscriptions = partner.subscription_ids
            active_subscriptions = subscriptions.filtered(lambda s: s.stage_category == 'progress')
            
            # Calculate totals
            partner.annual_subscription_value = sum(
                sub.recurring_total * 12 for sub in active_subscriptions  # Assume monthly billing
            )
            
            # Get billing data
            billings = self.env['ams.subscription.billing'].search([
                ('partner_id', '=', partner.id)
            ])
            
            partner.subscription_payment_total = sum(
                billings.filtered(lambda b: b.state in ['billed', 'paid']).mapped('total_amount')
            )
            partner.total_subscription_value = partner.subscription_payment_total
            
            if subscriptions:
                partner.average_subscription_price = (
                    sum(subscriptions.mapped('recurring_total')) / len(subscriptions)
                )
            else:
                partner.average_subscription_price = 0.0
            
            # Last payment
            last_billing = billings.filtered(lambda b: b.state in ['billed', 'paid']).sorted('billing_date', reverse=True)
            partner.last_subscription_payment = last_billing[0].total_amount if last_billing else 0.0
            
            # Outstanding amount
            partner.outstanding_subscription_amount = sum(
                billings.filtered(lambda b: b.state == 'billed').mapped('total_amount')
            )

    @api.depends('subscription_ids', 'subscription_ids.date_start')
    def _compute_subscription_history(self):
        """Compute subscription history."""
        for partner in self:
            subscriptions = partner.subscription_ids
            
            if not subscriptions:
                partner.first_subscription_date = False
                partner.last_renewal_date = False
                partner.next_renewal_date = False
                partner.subscription_tenure_months = 0
                continue
            
            # First subscription
            first_subscription = subscriptions.sorted('date_start')
            partner.first_subscription_date = first_subscription[0].date_start if first_subscription else False
            
            # Renewal data
            renewals = self.env['ams.subscription.renewal'].search([
                ('partner_id', '=', partner.id)
            ])
            
            if renewals:
                last_renewal = renewals.filtered(lambda r: r.state == 'renewed').sorted('renewal_processed_date', reverse=True)
                partner.last_renewal_date = last_renewal[0].renewal_processed_date if last_renewal else False
                
                pending_renewals = renewals.filtered(lambda r: r.state in ['pending', 'reminded', 'grace_period']).sorted('renewal_due_date')
                partner.next_renewal_date = pending_renewals[0].renewal_due_date if pending_renewals else False
            else:
                partner.last_renewal_date = False
                partner.next_renewal_date = False
            
            # Calculate tenure
            if partner.first_subscription_date:
                today = fields.Date.today()
                months = (today.year - partner.first_subscription_date.year) * 12
                months += today.month - partner.first_subscription_date.month
                partner.subscription_tenure_months = max(0, months)
            else:
                partner.subscription_tenure_months = 0

    @api.depends('subscription_ids', 'last_renewal_date', 'next_renewal_date', 'outstanding_subscription_amount')
    def _compute_churn_risk(self):
        """Calculate churn risk based on subscription behavior."""
        for partner in self:
            if not partner.has_active_subscriptions:
                partner.subscription_churn_risk = 'critical'
                continue
            
            risk_score = 0
            
            # Outstanding payment risk
            if partner.outstanding_subscription_amount > 0:
                risk_score += 2
            
            # Renewal behavior risk
            if partner.next_renewal_date:
                days_until_renewal = (partner.next_renewal_date - fields.Date.today()).days
                if days_until_renewal < 0:  # Overdue
                    risk_score += 3
                elif days_until_renewal < 7:  # Due soon
                    risk_score += 1
            
            # Communication response risk
            if partner.renewal_reminders_sent > 3:
                risk_score += 1
            
            # Tenure risk (newer customers are higher risk)
            if partner.subscription_tenure_months < 3:
                risk_score += 1
            
            # Determine risk level
            if risk_score >= 5:
                partner.subscription_churn_risk = 'critical'
            elif risk_score >= 3:
                partner.subscription_churn_risk = 'high'
            elif risk_score >= 1:
                partner.subscription_churn_risk = 'medium'
            else:
                partner.subscription_churn_risk = 'low'

    @api.depends('subscription_ids')
    def _compute_portal_access(self):
        """Check if customer has portal access from subscriptions."""
        for partner in self:
            # Check if any active subscription grants portal access
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.stage_category == 'progress'
            )
            
            portal_products = active_subscriptions.mapped('template_id.product_id').filtered(
                lambda p: p.grants_portal_access
            )
            
            partner.subscription_portal_access = bool(portal_products)

    @api.depends('subscription_ids')
    def _compute_subscription_access(self):
        """Compute subscription access details."""
        for partner in self:
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.stage_category == 'progress'
            )
            
            if not active_subscriptions:
                partner.subscription_access_levels = ""
                partner.subscription_content_types = ""
                partner.concurrent_users_allowed = 0
                partner.download_limits_monthly = 0
                continue
            
            products = active_subscriptions.mapped('template_id.product_id')
            
            # Access levels
            access_levels = set()
            for product in products:
                if product.subscription_access_level:
                    level_dict = dict(product._fields['subscription_access_level'].selection)
                    access_levels.add(level_dict.get(product.subscription_access_level, ''))
            partner.subscription_access_levels = ", ".join(sorted(access_levels))
            
            # Content types
            content_types = set()
            for product in products:
                if product.subscription_content_type:
                    type_dict = dict(product._fields['subscription_content_type'].selection)
                    content_types.add(type_dict.get(product.subscription_content_type, ''))
            partner.subscription_content_types = ", ".join(sorted(content_types))
            
            # User limits (sum or max depending on product configuration)
            partner.concurrent_users_allowed = sum(products.mapped('subscription_concurrent_users'))
            
            # Download limits
            partner.download_limits_monthly = sum(products.mapped('subscription_download_limit'))

    @api.depends('subscription_ids', 'is_member')
    def _compute_member_subscription_benefits(self):
        """Compute member subscription benefits and savings."""
        for partner in self:
            if not partner.is_member:
                partner.member_subscription_discount_total = 0.0
                partner.member_subscription_savings_annual = 0.0
                continue
            
            # Get billing records with member discounts
            billings = self.env['ams.subscription.billing'].search([
                ('partner_id', '=', partner.id),
                ('is_member_billing', '=', True),
                ('state', 'in', ['billed', 'paid'])
            ])
            
            partner.member_subscription_discount_total = sum(billings.mapped('member_discount_amount'))
            
            # Calculate annual savings from active subscriptions
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.stage_category == 'progress'
            )
            
            annual_savings = 0.0
            for subscription in active_subscriptions:
                if subscription.template_id and subscription.template_id.product_id:
                    product = subscription.template_id.product_id
                    if product.member_savings > 0:
                        # Assume monthly billing, multiply by 12
                        annual_savings += product.member_savings * 12
            
            partner.member_subscription_savings_annual = annual_savings

    # ========================================================================
    # SUBSCRIPTION RELATIONSHIP FIELDS
    # ========================================================================

    subscription_ids = fields.One2many(
        'sale.subscription',
        'partner_id',
        string="Subscriptions",
        help="All subscriptions for this customer"
    )

    subscription_billing_ids = fields.One2many(
        'ams.subscription.billing',
        'partner_id',
        string="Subscription Billings",
        help="All subscription billing records"
    )

    subscription_renewal_ids = fields.One2many(
        'ams.subscription.renewal',
        'partner_id',
        string="Subscription Renewals",
        help="All subscription renewal records"
    )

    # ========================================================================
    # BUSINESS METHODS - SUBSCRIPTION MANAGEMENT
    # ========================================================================

    def create_subscription_from_product(self, product, start_date=None, billing_period_id=None):
        """
        Create a new subscription for this customer from a product.
        
        Args:
            product (product.template): Subscription product
            start_date (date, optional): Subscription start date
            billing_period_id (int, optional): Specific billing period
            
        Returns:
            sale.subscription: Created subscription
        """
        self.ensure_one()
        
        if not product.ams_product_behavior == 'subscription':
            raise UserError(_("Product must be a subscription product"))
        
        # Check if customer can create subscription
        variant = product.product_variant_ids[0] if product.product_variant_ids else None
        if not variant:
            raise UserError(_("Product has no variants"))
        
        eligibility = variant.can_create_subscription_for_partner(self)
        if not eligibility.get('can_create'):
            raise UserError(eligibility.get('reason', 'Cannot create subscription'))
        
        # Prepare subscription values
        if not start_date:
            start_date = fields.Date.today()
        
        period_id = billing_period_id or product.subscription_billing_period_id.id
        if not period_id:
            raise UserError(_("No billing period configured for subscription"))
        
        billing_period = self.env['ams.billing.period'].browse(period_id)
        end_date = billing_period.calculate_next_date(start_date)
        
        # Create subscription template
        template_vals = {
            'name': f"{product.name} - {self.name}",
            'product_id': variant.id,
            'recurring_rule_type': 'monthly',  # This should be mapped from billing period
            'recurring_interval': 1,
        }
        
        template = self.env['sale.subscription.template'].create(template_vals)
        
        # Create subscription
        subscription_vals = {
            'partner_id': self.id,
            'template_id': template.id,
            'date_start': start_date,
            'date': end_date,
            'pricelist_id': self.property_product_pricelist.id,
            'currency_id': self.currency_id.id or self.env.company.currency_id.id,
        }
        
        subscription = self.env['sale.subscription'].create(subscription_vals)
        
        # Create initial billing
        initial_billing = self.env['ams.subscription.billing'].create({
            'subscription_id': subscription.id,
            'product_id': product.id,
            'billing_period_id': period_id,
            'billing_date': start_date,
            'period_start_date': start_date,
            'period_end_date': end_date - timedelta(days=1),
            'billing_type': 'initial',
            'state': 'scheduled',
        })
        
        # Calculate billing amounts
        initial_billing.calculate_billing_amounts()
        
        # Create renewal record
        self.env['ams.subscription.renewal'].create({
            'subscription_id': subscription.id,
            'product_id': product.id,
            'billing_period_id': period_id,
            'current_period_end': end_date,
            'renewal_due_date': end_date,
            'current_price': subscription.recurring_total,
            'first_subscription_date': start_date,
        })
        
        _logger.info(f"Created subscription {subscription.name} for customer {self.name}")
        
        return subscription

    def get_subscription_summary(self):
        """
        Get comprehensive subscription summary for this customer.
        
        Returns:
            dict: Complete subscription summary
        """
        self.ensure_one()
        
        return {
            'customer_name': self.name,
            'customer_id': self.id,
            'is_member': self.is_member,
            'membership_status': self.membership_status,
            'subscription_status_summary': self.subscription_status_summary,
            'has_active_subscriptions': self.has_active_subscriptions,
            'subscription_counts': {
                'total': self.subscription_count,
                'active': self.active_subscription_count,
                'expired': self.expired_subscription_count,
            },
            'financial_summary': {
                'total_lifetime_value': self.total_subscription_value,
                'annual_value': self.annual_subscription_value,
                'average_price': self.average_subscription_price,
                'last_payment': self.last_subscription_payment,
                'total_payments': self.subscription_payment_total,
                'outstanding': self.outstanding_subscription_amount,
                'member_savings_total': self.member_subscription_discount_total,
                'member_savings_annual': self.member_subscription_savings_annual,
            },
            'subscription_history': {
                'first_subscription': self.first_subscription_date,
                'last_renewal': self.last_renewal_date,
                'next_renewal': self.next_renewal_date,
                'tenure_months': self.subscription_tenure_months,
                'churn_risk': self.subscription_churn_risk,
            },
            'access_summary': {
                'portal_access': self.subscription_portal_access,
                'access_levels': self.subscription_access_levels,
                'content_types': self.subscription_content_types,
                'concurrent_users': self.concurrent_users_allowed,
                'monthly_downloads': self.download_limits_monthly,
            },
            'communication': {
                'preference': self.subscription_communication_preference,
                'auto_renewal_pref': self.subscription_auto_renewal_preference,
                'reminder_timing': self.renewal_reminder_days,
                'reminders_sent': self.renewal_reminders_sent,
                'last_communication': self.last_subscription_communication_date,
            },
        }

    def get_subscription_recommendations(self):
        """
        Get subscription recommendations for this customer.
        
        Returns:
            dict: Subscription recommendations
        """
        self.ensure_one()
        
        recommendations = []
        
        # Recommend upgrades for active subscriptions
        active_subscriptions = self.subscription_ids.filtered(
            lambda s: s.stage_category == 'progress'
        )
        
        for subscription in active_subscriptions:
            if subscription.template_id and subscription.template_id.product_id:
                product = subscription.template_id.product_id
                
                # Recommend upgrade if customer has basic access
                if product.subscription_access_level == 'basic':
                    premium_products = self.env['product.template'].search([
                        ('ams_product_behavior', '=', 'subscription'),
                        ('subscription_content_type', '=', product.subscription_content_type),
                        ('subscription_access_level', 'in', ['premium', 'enterprise']),
                    ])
                    
                    if premium_products:
                        recommendations.append({
                            'type': 'upgrade',
                            'current_product': product.name,
                            'recommended_products': premium_products.mapped('name'),
                            'reason': 'Upgrade to premium access for enhanced features',
                        })
        
        # Recommend complementary subscriptions
        if self.is_member:
            current_content_types = set()
            for subscription in active_subscriptions:
                if subscription.template_id and subscription.template_id.product_id.subscription_content_type:
                    current_content_types.add(subscription.template_id.product_id.subscription_content_type)
            
            # Recommend missing content types
            all_content_types = {'publication', 'research', 'digital_access', 'course'}
            missing_types = all_content_types - current_content_types
            
            for content_type in missing_types:
                complementary_products = self.env['product.template'].search([
                    ('ams_product_behavior', '=', 'subscription'),
                    ('subscription_content_type', '=', content_type),
                ], limit=3)
                
                if complementary_products:
                    type_dict = dict(complementary_products[0]._fields['subscription_content_type'].selection)
                    recommendations.append({
                        'type': 'complementary',
                        'content_type': type_dict.get(content_type, ''),
                        'recommended_products': complementary_products.mapped('name'),
                        'reason': f'Enhance your professional development with {type_dict.get(content_type, "")} access',
                    })
        
        # Recommend renewal if overdue
        overdue_renewals = self.subscription_renewal_ids.filtered(
            lambda r: r.state in ['grace_period', 'expired']
        )
        
        if overdue_renewals:
            recommendations.append({
                'type': 'renewal',
                'overdue_count': len(overdue_renewals),
                'products': overdue_renewals.mapped('product_id.name'),
                'reason': 'Renew to maintain access to subscription benefits',
            })
        
        return {
            'customer': self.name,
            'recommendation_count': len(recommendations),
            'recommendations': recommendations,
            'based_on': {
                'is_member': self.is_member,
                'active_subscriptions': len(active_subscriptions),
                'tenure_months': self.subscription_tenure_months,
                'churn_risk': self.subscription_churn_risk,
            }
        }

    # ========================================================================
    # SUBSCRIPTION COMMUNICATION METHODS
    # ========================================================================

    def send_subscription_welcome(self):
        """Send subscription welcome email to customer."""
        self.ensure_one()
        
        if not self.email:
            return False
        
        if self.subscription_welcome_sent:
            return False  # Already sent
        
        # Find welcome template
        template = self.env.ref('ams_subscriptions_products.customer_welcome_template', False)
        
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.write({
                    'subscription_welcome_sent': True,
                    'last_subscription_communication_date': fields.Date.today(),
                })
                return True
            except Exception as e:
                _logger.error(f"Failed to send subscription welcome to {self.name}: {e}")
        
        return False

    def update_subscription_communication_date(self):
        """Update last communication date."""
        self.ensure_one()
        self.last_subscription_communication_date = fields.Date.today()

    # ========================================================================
    # VALIDATION
    # ========================================================================

    @api.constrains('subscription_billing_day')
    def _check_billing_day(self):
        """Validate preferred billing day."""
        for partner in self:
            if partner.subscription_billing_day < 1 or partner.subscription_billing_day > 28:
                raise ValidationError(_("Billing day must be between 1 and 28"))

    # ========================================================================
    # ACTIONS AND UI METHODS
    # ========================================================================

    def action_view_subscriptions(self):
        """View all subscriptions for this customer."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Subscriptions'),
            'res_model': 'sale.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'show_subscription_info': True,
            },
        }

    def action_view_subscription_billings(self):
        """View all subscription billings for this customer."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Billings'),
            'res_model': 'ams.subscription.billing',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_subscription_renewals(self):
        """View all subscription renewals for this customer."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Renewals'),
            'res_model': 'ams.subscription.renewal',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_create_subscription(self):
        """Launch subscription creation wizard."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Subscription'),
            'res_model': 'ams.subscription.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def action_subscription_recommendations(self):
        """Show subscription recommendations."""
        self.ensure_one()
        
        recommendations = self.get_subscription_recommendations()
        
        if not recommendations['recommendations']:
            message = "No subscription recommendations available at this time."
        else:
            message_parts = []
            for rec in recommendations['recommendations']:
                message_parts.append(f"• {rec['reason']}")
            message = "Subscription Recommendations:\n" + "\n".join(message_parts)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'title': f'Recommendations for {self.name}',
                'type': 'info',
                'sticky': True,
            }
        }

    # ========================================================================
    # QUERY METHODS FOR CUSTOMER ANALYSIS
    # ========================================================================

    @api.model
    def get_high_value_subscription_customers(self, min_annual_value=1000):
        """Get customers with high annual subscription value."""
        return self.search([
            ('annual_subscription_value', '>=', min_annual_value),
            ('has_active_subscriptions', '=', True),
        ])

    @api.model
    def get_at_risk_customers(self, risk_levels=['high', 'critical']):
        """Get customers at risk of churning."""
        return self.search([
            ('subscription_churn_risk', 'in', risk_levels),
            ('has_active_subscriptions', '=', True),
        ])

    @api.model
    def get_customers_for_renewal_campaign(self, days_ahead=30):
        """Get customers with renewals due for marketing campaign."""
        cutoff_date = fields.Date.today() + timedelta(days=days_ahead)
        
        return self.search([
            ('next_renewal_date', '<=', cutoff_date),
            ('next_renewal_date', '>=', fields.Date.today()),
        ])

    @api.model
    def get_member_subscribers(self):
        """Get members who also have subscriptions."""
        return self.search([
            ('is_member', '=', True),
            ('has_active_subscriptions', '=', True),
        ])

    @api.model
    def get_subscription_analytics(self):
        """Get customer subscription analytics."""
        all_customers = self.search([('subscription_count', '>', 0)])
        
        return {
            'total_customers': len(all_customers),
            'active_subscribers': len(all_customers.filtered('has_active_subscriptions')),
            'member_subscribers': len(all_customers.filtered(lambda c: c.is_member and c.has_active_subscriptions)),
            'total_annual_value': sum(all_customers.mapped('annual_subscription_value')),
            'average_annual_value': sum(all_customers.mapped('annual_subscription_value')) / len(all_customers) if all_customers else 0,
            'churn_risk_distribution': {
                'low': len(all_customers.filtered(lambda c: c.subscription_churn_risk == 'low')),
                'medium': len(all_customers.filtered(lambda c: c.subscription_churn_risk == 'medium')),
                'high': len(all_customers.filtered(lambda c: c.subscription_churn_risk == 'high')),
                'critical': len(all_customers.filtered(lambda c: c.subscription_churn_risk == 'critical')),
            },
            'tenure_analysis': {
                'new_subscribers': len(all_customers.filtered(lambda c: c.subscription_tenure_months < 12)),
                'mature_subscribers': len(all_customers.filtered(lambda c: c.subscription_tenure_months >= 12)),
                'average_tenure_months': sum(all_customers.mapped('subscription_tenure_months')) / len(all_customers) if all_customers else 0,
            },
        }