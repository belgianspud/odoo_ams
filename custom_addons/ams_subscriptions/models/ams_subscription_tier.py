# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionTier(models.Model):
    """
    Enhanced AMS Subscription Tier Model - Layer 2 Architecture
    
    Defines subscription tiers with benefits, lifecycle rules, and integration
    with ams_products_base and ams_billing_periods.
    
    Layer 2 Responsibilities:
    - Tier configuration for different subscription types
    - Lifecycle rule definitions (grace, suspension, termination periods)
    - Benefit management and included products
    - Integration with billing periods for flexible billing
    - Statistics and performance tracking
    """
    _name = 'ams.subscription.tier'
    _description = 'AMS Subscription Tier - Enhanced'
    _inherit = ['mail.thread']
    _order = 'subscription_type, sequence, name'

    # ========================================================================
    # CORE TIER IDENTIFICATION
    # ========================================================================
    
    name = fields.Char(
        string='Tier Name',
        required=True,
        tracking=True,
        help='Display name for this subscription tier'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this tier and its benefits'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order for this tier (lower numbers first)'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Whether this tier is available for new subscriptions'
    )

    # ========================================================================
    # SUBSCRIPTION TYPE CONFIGURATION
    # ========================================================================
    
    subscription_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('enterprise', 'Enterprise Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication Subscription'),
    ], string='Subscription Type',
       required=True,
       tracking=True,
       help='Type of subscriptions this tier applies to')

    # ========================================================================
    # BILLING INTEGRATION (Layer 2 - integrates with ams_billing_periods)
    # ========================================================================
    
    # Enhanced billing period integration
    default_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string='Default Billing Period',
        help='Default billing period for subscriptions using this tier'
    )
    
    # Legacy support for migration from V1.0
    period_length = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Period (Deprecated)',
       default='annual',
       help='DEPRECATED: Use default_billing_period_id instead')
    
    # Billing period display (computed from ams_billing_periods)
    billing_period_display = fields.Char(
        string='Billing Period',
        compute='_compute_billing_period_display',
        store=True,
        help='Human-readable billing period description'
    )

    # ========================================================================
    # LIFECYCLE RULES (Layer 2 - subscription management)
    # ========================================================================
    
    grace_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        required=True,
        help='Days after expiration before subscription is suspended'
    )
    
    suspend_days = fields.Integer(
        string='Suspension Period (Days)', 
        default=60,
        required=True,
        help='Days in suspension before subscription is terminated'
    )
    
    terminate_days = fields.Integer(
        string='Termination Period (Days)',
        default=30,
        required=True, 
        help='Days to keep terminated subscription data before final cleanup'
    )
    
    # Lifecycle automation settings
    auto_renew = fields.Boolean(
        string='Auto-Renew by Default',
        default=True,
        help='New subscriptions using this tier will auto-renew by default'
    )
    
    send_lifecycle_emails = fields.Boolean(
        string='Send Lifecycle Emails',
        default=True,
        help='Send automated emails for lifecycle transitions (expiration, suspension, etc.)'
    )
    
    # Notification timing
    renewal_notice_days = fields.Integer(
        string='Renewal Notice (Days Before)',
        default=14,
        help='Days before expiration to send renewal notices'
    )
    
    grace_notice_days = fields.Integer(
        string='Grace Period Notice (Days Before)',
        default=7,
        help='Days before grace period ends to send final notices'
    )

    # ========================================================================
    # TIER CLASSIFICATION AND PRICING
    # ========================================================================
    
    is_free = fields.Boolean(
        string='Free Tier',
        default=False,
        tracking=True,
        help='This tier requires no payment'
    )
    
    is_trial = fields.Boolean(
        string='Trial Tier',
        default=False,
        help='This is a trial/evaluation tier with limited duration'
    )
    
    trial_duration_days = fields.Integer(
        string='Trial Duration (Days)',
        default=30,
        help='Duration of trial period for trial tiers'
    )
    
    tier_level = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ], string='Tier Level',
       default='standard',
       help='Classification level of this tier')

    # ========================================================================
    # ENTERPRISE FEATURES (Layer 2)
    # ========================================================================
    
    default_seats = fields.Integer(
        string='Default Seats',
        default=0,
        help='Number of seats included with this tier (for enterprise subscriptions)'
    )
    
    max_additional_seats = fields.Integer(
        string='Max Additional Seats',
        default=0,
        help='Maximum additional seats that can be purchased (0 = unlimited)'
    )
    
    seat_management_enabled = fields.Boolean(
        string='Enable Seat Management',
        compute='_compute_seat_management_enabled',
        store=True,
        help='Whether this tier supports seat assignment and management'
    )

    # ========================================================================
    # BENEFIT MANAGEMENT (Layer 2 - integrates with ams_products_base)
    # ========================================================================
    
    benefit_product_ids = fields.Many2many(
        'product.template',
        'ams_tier_benefit_rel',
        'tier_id',
        'product_id',
        string='Included Benefits',
        domain=[('is_ams_product', '=', True)],
        help='Products/services automatically included with this tier'
    )
    
    included_benefits_text = fields.Html(
        string='Benefits Description',
        help='Rich text description of benefits included with this tier'
    )
    
    feature_list = fields.Text(
        string='Feature List',
        help='Bullet-point list of features (one per line)'
    )
    
    # Portal and access controls (integrates with ams_products_base portal features)
    grants_portal_access = fields.Boolean(
        string='Grants Portal Access',
        default=True,
        help='Subscriptions with this tier get portal access'
    )
    
    portal_group_ids = fields.Many2many(
        'res.groups',
        'ams_tier_portal_group_rel',
        'tier_id',
        'group_id',
        string='Portal Access Groups',
        help='Portal groups granted to subscribers of this tier'
    )

    # ========================================================================
    # RESTRICTIONS AND PERMISSIONS (Layer 2)
    # ========================================================================
    
    allow_modifications = fields.Boolean(
        string='Allow Customer Modifications',
        default=True,
        help='Allow customers to upgrade/downgrade from this tier'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Customer Pausing',
        default=True,
        help='Allow customers to pause subscriptions with this tier'
    )
    
    allow_cancellation = fields.Boolean(
        string='Allow Customer Cancellation',
        default=True,
        help='Allow customers to cancel subscriptions with this tier'
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='New subscriptions with this tier require staff approval'
    )

    # ========================================================================
    # STATISTICS AND REPORTING (Layer 2)
    # ========================================================================
    
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_tier_statistics',
        store=True,
        help='Current number of active subscriptions using this tier'
    )
    
    total_subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_tier_statistics', 
        store=True,
        help='Total subscriptions ever created with this tier'
    )
    
    revenue_ytd = fields.Monetary(
        string='Revenue YTD',
        compute='_compute_tier_statistics',
        store=True,
        currency_field='currency_id',
        help='Year-to-date revenue from subscriptions using this tier'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for financial calculations'
    )
    
    average_subscription_duration = fields.Float(
        string='Avg Duration (Months)',
        compute='_compute_tier_statistics',
        store=True,
        help='Average duration of subscriptions with this tier'
    )
    
    churn_rate = fields.Float(
        string='Churn Rate (%)',
        compute='_compute_tier_statistics',
        store=True,
        help='Percentage of subscriptions that have been cancelled'
    )

    # ========================================================================
    # INTERNAL MANAGEMENT
    # ========================================================================
    
    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes for staff about this tier'
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    @api.depends('default_billing_period_id', 'period_length')
    def _compute_billing_period_display(self):
        """Compute human-readable billing period display"""
        for tier in self:
            if tier.default_billing_period_id:
                tier.billing_period_display = tier.default_billing_period_id.name
            elif tier.period_length:
                # Map legacy period_length to display names
                period_names = {
                    'monthly': 'Monthly',
                    'quarterly': 'Quarterly', 
                    'semi_annual': 'Semi-Annual',
                    'annual': 'Annual',
                }
                tier.billing_period_display = period_names.get(tier.period_length, tier.period_length.title())
            else:
                tier.billing_period_display = 'Not Configured'
    
    @api.depends('subscription_type', 'default_seats')
    def _compute_seat_management_enabled(self):
        """Determine if seat management should be enabled"""
        for tier in self:
            tier.seat_management_enabled = (
                tier.subscription_type == 'enterprise' and 
                tier.default_seats > 0
            )
    
    @api.depends('name')  # Dummy dependency - real implementation would track subscription records
    def _compute_tier_statistics(self):
        """Compute tier usage statistics"""
        for tier in self:
            # Get all subscriptions using this tier
            subscriptions = self.env['ams.subscription'].search([
                ('tier_id', '=', tier.id)
            ])
            
            # Basic counts
            tier.total_subscription_count = len(subscriptions)
            tier.active_subscription_count = len(subscriptions.filtered(
                lambda s: s.state == 'active'
            ))
            
            # Revenue calculation (simplified - could integrate with accounting)
            # This would typically pull from invoice/payment data
            active_subscriptions = subscriptions.filtered(lambda s: s.state == 'active')
            if active_subscriptions and active_subscriptions[0].product_id:
                avg_price = sum(sub.product_id.lst_price for sub in active_subscriptions) / len(active_subscriptions)
                tier.revenue_ytd = tier.active_subscription_count * avg_price
            else:
                tier.revenue_ytd = 0.0
            
            # Churn rate calculation
            if tier.total_subscription_count > 0:
                terminated_count = len(subscriptions.filtered(
                    lambda s: s.state == 'terminated'
                ))
                tier.churn_rate = (terminated_count / tier.total_subscription_count) * 100
            else:
                tier.churn_rate = 0.0
            
            # Average duration calculation (simplified)
            completed_subscriptions = subscriptions.filtered(
                lambda s: s.state == 'terminated' and s.start_date and s.paid_through_date
            )
            if completed_subscriptions:
                total_days = sum([
                    (sub.paid_through_date - sub.start_date).days
                    for sub in completed_subscriptions
                ])
                tier.average_subscription_duration = (total_days / len(completed_subscriptions)) / 30.0
            else:
                tier.average_subscription_duration = 0.0

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('subscription_type')
    def _onchange_subscription_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_type == 'enterprise':
            self.default_seats = self.default_seats or 5
            self.allow_modifications = True
            self.requires_approval = True
            self.tier_level = 'enterprise'
        elif self.subscription_type == 'individual':
            self.default_seats = 0
            self.allow_modifications = True
            self.requires_approval = False
            self.tier_level = 'standard'
        elif self.subscription_type == 'chapter':
            self.default_seats = 0
            self.grace_days = 60  # Longer grace for chapters
            self.tier_level = 'basic'
        elif self.subscription_type == 'publication':
            self.default_seats = 0
            self.renewal_notice_days = 30  # Longer notice for publications
            self.tier_level = 'standard'
    
    @api.onchange('is_trial')
    def _onchange_is_trial(self):
        """Set trial defaults"""
        if self.is_trial:
            self.is_free = True
            self.auto_renew = False
            self.trial_duration_days = 30
            self.grace_days = 7  # Shorter grace for trials
    
    @api.onchange('is_free')
    def _onchange_is_free(self):
        """Set free tier defaults"""
        if self.is_free:
            self.renewal_notice_days = 0  # No renewal notices for free tiers
    
    @api.onchange('period_length')
    def _onchange_period_length_migration(self):
        """Help with migration from period_length to billing_period_id"""
        if self.period_length and not self.default_billing_period_id:
            # Try to find matching billing period
            billing_period = self.env['ams.billing.period'].search([
                ('name', 'ilike', self.period_length.replace('_', ' '))
            ], limit=1)
            
            if billing_period:
                self.default_billing_period_id = billing_period.id
                
                return {
                    'warning': {
                        'title': 'Migration Suggestion',
                        'message': f'Found matching billing period "{billing_period.name}". '
                                 f'Consider using billing periods instead of the deprecated period_length field.'
                    }
                }

    # ========================================================================
    # CONSTRAINT VALIDATION
    # ========================================================================
    
    @api.constrains('grace_days', 'suspend_days', 'terminate_days')
    def _check_lifecycle_periods(self):
        """Validate lifecycle period configuration"""
        for tier in self:
            if tier.grace_days < 0 or tier.suspend_days < 0 or tier.terminate_days < 0:
                raise ValidationError(_("All lifecycle periods must be non-negative"))
                
            if tier.grace_days > 365 or tier.suspend_days > 365 or tier.terminate_days > 365:
                raise ValidationError(_("Lifecycle periods should not exceed 365 days"))
    
    @api.constrains('default_seats', 'max_additional_seats')
    def _check_seat_configuration(self):
        """Validate seat configuration"""
        for tier in self:
            if tier.default_seats < 0:
                raise ValidationError(_("Default seats cannot be negative"))
                
            if tier.max_additional_seats < 0:
                raise ValidationError(_("Max additional seats cannot be negative"))
                
            if tier.subscription_type != 'enterprise' and tier.default_seats > 1:
                raise ValidationError(_("Only enterprise subscription types can have multiple seats"))
    
    @api.constrains('renewal_notice_days', 'grace_notice_days')
    def _check_notice_periods(self):
        """Validate notice period configuration"""
        for tier in self:
            if tier.renewal_notice_days < 0 or tier.grace_notice_days < 0:
                raise ValidationError(_("Notice periods cannot be negative"))
    
    @api.constrains('trial_duration_days')
    def _check_trial_duration(self):
        """Validate trial duration"""
        for tier in self:
            if tier.is_trial and tier.trial_duration_days <= 0:
                raise ValidationError(_("Trial tiers must have a positive trial duration"))

    # ========================================================================
    # BUSINESS METHODS (Layer 2 Integration)
    # ========================================================================
    
    def get_lifecycle_configuration(self):
        """Get complete lifecycle configuration for subscriptions"""
        self.ensure_one()
        
        return {
            'grace_days': self.grace_days,
            'suspend_days': self.suspend_days,
            'terminate_days': self.terminate_days,
            'auto_renew': self.auto_renew,
            'renewal_notice_days': self.renewal_notice_days,
            'grace_notice_days': self.grace_notice_days,
            'send_lifecycle_emails': self.send_lifecycle_emails,
        }
    
    def get_benefit_configuration(self):
        """Get complete benefit configuration integrating with ams_products_base"""
        self.ensure_one()
        
        return {
            'benefit_products': self.benefit_product_ids.ids,
            'grants_portal_access': self.grants_portal_access,
            'portal_groups': self.portal_group_ids.ids,
            'included_benefits_html': self.included_benefits_text,
            'feature_list': self.feature_list.split('\n') if self.feature_list else [],
        }
    
    def get_enterprise_configuration(self):
        """Get enterprise-specific configuration"""
        self.ensure_one()
        
        return {
            'default_seats': self.default_seats,
            'max_additional_seats': self.max_additional_seats,
            'seat_management_enabled': self.seat_management_enabled,
        }
    
    def get_customer_permissions(self):
        """Get customer permission configuration"""
        self.ensure_one()
        
        return {
            'allow_modifications': self.allow_modifications,
            'allow_pausing': self.allow_pausing,
            'allow_cancellation': self.allow_cancellation,
            'requires_approval': self.requires_approval,
        }
    
    def get_billing_period_info(self):
        """Get billing period information integrating with ams_billing_periods"""
        self.ensure_one()
        
        if self.default_billing_period_id:
            return {
                'billing_period_id': self.default_billing_period_id.id,
                'billing_period_name': self.default_billing_period_id.name,
                'period_value': getattr(self.default_billing_period_id, 'period_value', 1),
                'period_unit': getattr(self.default_billing_period_id, 'period_unit', 'year'),
                'display_name': self.billing_period_display,
            }
        else:
            # Fallback to legacy period_length
            return {
                'billing_period_id': False,
                'billing_period_name': self.period_length,
                'display_name': self.billing_period_display,
                'legacy_period': self.period_length,
            }

    # ========================================================================
    # ACTION METHODS
    # ========================================================================
    
    def action_view_subscriptions(self):
        """View subscriptions using this tier"""
        self.ensure_one()
        
        return {
            'name': f'Subscriptions: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'kanban,tree,form',
            'domain': [('tier_id', '=', self.id)],
            'context': {
                'search_default_active': 1,
                'default_tier_id': self.id,
                'default_subscription_type': self.subscription_type,
            }
        }
    
    def action_duplicate_tier(self):
        """Create a copy of this tier for modification"""
        self.ensure_one()
        
        copy_vals = {
            'name': f"{self.name} (Copy)",
            'active': False,  # Start inactive for configuration
        }
        
        new_tier = self.copy(copy_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Configure New Tier: {new_tier.name}',
            'res_model': 'ams.subscription.tier',
            'res_id': new_tier.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_migrate_to_billing_periods(self):
        """Action to help migrate from period_length to billing periods"""
        self.ensure_one()
        
        if not self.period_length or self.default_billing_period_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'This tier is already configured with billing periods.',
                    'type': 'info',
                }
            }
        
        # Find matching billing period
        billing_period = self.env['ams.billing.period'].search([
            ('name', 'ilike', self.period_length.replace('_', ' '))
        ], limit=1)
        
        if billing_period:
            self.default_billing_period_id = billing_period.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Successfully migrated to billing period: {billing_period.name}',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'No matching billing period found for "{self.period_length}". Please select one manually.',
                    'type': 'warning',
                }
            }

    # ========================================================================
    # NAME AND DISPLAY
    # ========================================================================
    
    def name_get(self):
        """Enhanced name display with type and status"""
        result = []
        for tier in self:
            name = tier.name
            
            # Add type indicator
            type_short = {
                'individual': 'IND',
                'enterprise': 'ENT', 
                'chapter': 'CHP',
                'publication': 'PUB',
            }.get(tier.subscription_type, 'UNK')
            
            name = f"[{type_short}] {name}"
            
            # Add status indicators
            if not tier.active:
                name = f"{name} (Inactive)"
            elif tier.is_trial:
                name = f"{name} (Trial)"
            elif tier.is_free:
                name = f"{name} (Free)"
            
            result.append((tier.id, name))
            
        return result

    @api.model 
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search including type and description"""
        args = args or []
        
        if name:
            domain = [
                '|', '|', 
                ('name', operator, name),
                ('description', operator, name),
                ('subscription_type', operator, name)
            ]
            args = domain + args
            
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    # ========================================================================
    # MIGRATION HELPERS (Layer 2 to Layer 1 Integration)
    # ========================================================================
    
    @api.model
    def migrate_legacy_periods(self):
        """Migrate all tiers from period_length to billing_period_id"""
        legacy_tiers = self.search([
            ('period_length', '!=', False),
            ('default_billing_period_id', '=', False)
        ])
        
        migrated_count = 0
        for tier in legacy_tiers:
            billing_period = self.env['ams.billing.period'].search([
                ('name', 'ilike', tier.period_length.replace('_', ' '))
            ], limit=1)
            
            if billing_period:
                tier.default_billing_period_id = billing_period.id
                migrated_count += 1
                
        _logger.info(f"Migrated {migrated_count} tiers to use ams_billing_periods")
        return migrated_count