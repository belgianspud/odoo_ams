# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateSubscription(models.Model):
    """
    Subscription extensions for product templates.
    Provides comprehensive subscription management capabilities for association products.
    """
    _inherit = 'product.template'

    # ========================================================================
    # SUBSCRIPTION TOGGLE & IDENTIFICATION
    # ========================================================================

    is_subscription = fields.Boolean(
        string="Is Subscription Product",
        default=False,
        help="Mark this product as offering subscription-based billing and services"
    )

    # ========================================================================
    # BASIC SUBSCRIPTION CONFIGURATION
    # ========================================================================

    default_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="Default Billing Period",
        help="Default billing cycle for new subscriptions of this product"
    )

    subscription_scope = fields.Selection([
        ('individual', 'Individual'),
        ('enterprise', 'Enterprise')
    ], string="Subscription Scope", 
       default='individual',
       help="Target scope for this subscription product")

    # ========================================================================
    # RENEWAL CONFIGURATION
    # ========================================================================

    is_renewable = fields.Boolean(
        string="Supports Renewal",
        default=True,
        help="Whether subscriptions for this product can be renewed"
    )

    auto_renewal_enabled = fields.Boolean(
        string="Auto-renewal Available",
        default=False,
        help="Whether customers can enable automatic renewal for this subscription"
    )

    renewal_window_days = fields.Integer(
        string="Renewal Notice Period (Days)",
        default=90,
        help="Number of days before expiration to begin renewal notifications"
    )

    # ========================================================================
    # APPROVAL REQUIREMENTS
    # ========================================================================

    requires_approval = fields.Boolean(
        string="Requires Staff Approval",
        default=False,
        help="Whether new subscriptions require staff approval before activation"
    )

    approval_workflow_id = fields.Many2one(
        'workflow.template',
        string="Approval Workflow",
        help="Workflow template for subscription approval process"
    )

    # ========================================================================
    # BASIC ENTERPRISE FEATURES
    # ========================================================================

    supports_seats = fields.Boolean(
        string="Supports Seat Allocation",
        default=False,
        help="Whether this subscription supports multiple user seats"
    )

    default_seat_count = fields.Integer(
        string="Default Seats",
        default=1,
        help="Default number of seats for new subscriptions"
    )

    # ========================================================================
    # COMPUTED SUBSCRIPTION INFORMATION
    # ========================================================================

    subscription_summary = fields.Char(
        string="Subscription Summary",
        compute='_compute_subscription_summary',
        help="Summary of subscription configuration"
    )

    has_subscription_issues = fields.Boolean(
        string="Has Configuration Issues",
        compute='_compute_subscription_issues',
        help="Whether this subscription product has configuration issues"
    )

    subscription_issue_message = fields.Text(
        string="Configuration Issues",
        compute='_compute_subscription_issues',
        help="Details about subscription configuration issues"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('is_subscription', 'default_billing_period_id', 'subscription_scope', 
                 'is_renewable', 'auto_renewal_enabled', 'supports_seats', 'default_seat_count')
    def _compute_subscription_summary(self):
        """Generate subscription configuration summary"""
        for product in self:
            if not product.is_subscription:
                product.subscription_summary = "Not a subscription product"
                continue
                
            parts = []
            
            # Billing period
            if product.default_billing_period_id:
                parts.append(f"Billing: {product.default_billing_period_id.name}")
            
            # Scope
            parts.append(f"Scope: {dict(product._fields['subscription_scope'].selection)[product.subscription_scope]}")
            
            # Seats
            if product.supports_seats:
                parts.append(f"Seats: {product.default_seat_count} default")
            
            # Renewal
            if product.is_renewable:
                if product.auto_renewal_enabled:
                    parts.append("Auto-renewable")
                else:
                    parts.append("Manual renewal")
            else:
                parts.append("Non-renewable")
            
            # Approval
            if product.requires_approval:
                parts.append("Approval required")
            
            product.subscription_summary = " • ".join(parts)

    @api.depends('is_subscription', 'default_billing_period_id', 'renewal_window_days', 
                 'default_seat_count', 'requires_approval', 'approval_workflow_id')
    def _compute_subscription_issues(self):
        """Identify subscription configuration issues"""
        for product in self:
            issues = []
            
            if not product.is_subscription:
                product.has_subscription_issues = False
                product.subscription_issue_message = ""
                continue
            
            # Check for missing billing period
            if not product.default_billing_period_id:
                issues.append("Missing default billing period")
            
            # Check renewal window validity
            if product.is_renewable and product.renewal_window_days <= 0:
                issues.append("Invalid renewal window period (must be positive)")
            
            # Check seat count for multi-seat subscriptions
            if product.supports_seats and product.default_seat_count <= 0:
                issues.append("Invalid default seat count (must be positive)")
            
            # Check approval workflow configuration
            if product.requires_approval and not product.approval_workflow_id:
                issues.append("Missing approval workflow template")
            
            product.has_subscription_issues = bool(issues)
            product.subscription_issue_message = "\n".join(issues) if issues else ""

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('is_subscription')
    def _onchange_is_subscription(self):
        """Apply subscription defaults when toggled on"""
        if self.is_subscription:
            # Set default billing period if none selected
            if not self.default_billing_period_id:
                default_period = self.env['ams.billing.period'].get_default_period()
                if default_period:
                    self.default_billing_period_id = default_period
            
            # Enable renewals by default
            if not self.is_renewable:
                self.is_renewable = True
            
            # Set reasonable renewal window
            if not self.renewal_window_days or self.renewal_window_days <= 0:
                self.renewal_window_days = 90

    @api.onchange('subscription_scope')
    def _onchange_subscription_scope(self):
        """Apply scope-specific defaults"""
        if self.subscription_scope == 'enterprise':
            # Enterprise subscriptions often require approval
            if not self.requires_approval:
                self.requires_approval = True
            
            # Enterprise subscriptions often support seats
            if not self.supports_seats:
                self.supports_seats = True
                if self.default_seat_count <= 1:
                    self.default_seat_count = 5
        
        elif self.subscription_scope == 'individual':
            # Individual subscriptions typically don't need seats
            if self.supports_seats and self.default_seat_count <= 1:
                self.supports_seats = False
                self.default_seat_count = 1

    @api.onchange('supports_seats')
    def _onchange_supports_seats(self):
        """Set default seat count when seats are enabled"""
        if self.supports_seats and self.default_seat_count <= 0:
            self.default_seat_count = 5 if self.subscription_scope == 'enterprise' else 1

    @api.onchange('requires_approval')
    def _onchange_requires_approval(self):
        """Clear approval workflow if approval not required"""
        if not self.requires_approval:
            self.approval_workflow_id = False

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def get_subscription_details(self):
        """
        Get comprehensive subscription configuration details.
        
        Returns:
            dict: Complete subscription configuration information
        """
        self.ensure_one()
        
        if not self.is_subscription:
            return {'is_subscription': False}
        
        # Get billing period details
        billing_details = {}
        if self.default_billing_period_id:
            billing_details = {
                'billing_period_id': self.default_billing_period_id.id,
                'billing_period_name': self.default_billing_period_id.name,
                'billing_period_duration': self.default_billing_period_id.duration_value,
                'billing_period_unit': self.default_billing_period_id.duration_unit,
                'billing_period_days': self.default_billing_period_id.total_days,
                'billing_period_summary': self.default_billing_period_id.period_summary,
            }
        
        return {
            'is_subscription': True,
            'subscription_scope': self.subscription_scope,
            'subscription_scope_display': dict(self._fields['subscription_scope'].selection)[self.subscription_scope],
            
            # Billing configuration
            **billing_details,
            
            # Renewal configuration
            'is_renewable': self.is_renewable,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'renewal_window_days': self.renewal_window_days,
            
            # Approval configuration
            'requires_approval': self.requires_approval,
            'approval_workflow_id': self.approval_workflow_id.id if self.approval_workflow_id else None,
            'approval_workflow_name': self.approval_workflow_id.name if self.approval_workflow_id else None,
            
            # Seat configuration
            'supports_seats': self.supports_seats,
            'default_seat_count': self.default_seat_count,
            
            # Summary information
            'subscription_summary': self.subscription_summary,
            'has_issues': self.has_subscription_issues,
            'issue_message': self.subscription_issue_message,
        }

    def get_billing_period_options(self):
        """
        Get available billing period options for this subscription product.
        
        Returns:
            recordset: Available billing periods
        """
        self.ensure_one()
        
        # Return all active billing periods
        # Future modules can extend this to provide product-specific filtering
        return self.env['ams.billing.period'].search([('active', '=', True)])

    def calculate_next_billing_date(self, start_date=None):
        """
        Calculate next billing date based on default billing period.
        
        Args:
            start_date (date, optional): Start date for calculation
            
        Returns:
            date: Next billing date or None if no billing period configured
        """
        self.ensure_one()
        
        if not self.is_subscription or not self.default_billing_period_id:
            return None
            
        return self.default_billing_period_id.calculate_next_date(start_date)

    def calculate_renewal_notice_date(self, end_date):
        """
        Calculate when renewal notice should be sent.
        
        Args:
            end_date (date): Subscription end date
            
        Returns:
            date: Date to send renewal notice
        """
        self.ensure_one()
        
        if not self.is_renewable or not end_date:
            return None
        
        from datetime import timedelta
        return end_date - timedelta(days=self.renewal_window_days)

    def can_auto_renew(self):
        """
        Check if this subscription product supports auto-renewal.
        
        Returns:
            bool: True if auto-renewal is supported
        """
        self.ensure_one()
        return self.is_subscription and self.is_renewable and self.auto_renewal_enabled

    def requires_staff_approval(self):
        """
        Check if new subscriptions require staff approval.
        
        Returns:
            bool: True if approval is required
        """
        self.ensure_one()
        return self.is_subscription and self.requires_approval

    # ========================================================================
    # VALIDATION CONSTRAINTS
    # ========================================================================

    @api.constrains('renewal_window_days')
    def _check_renewal_window_days(self):
        """Validate renewal window period"""
        for product in self:
            if product.is_subscription and product.is_renewable:
                if product.renewal_window_days < 0:
                    raise ValidationError(_("Renewal window period cannot be negative"))
                if product.renewal_window_days > 365:
                    raise ValidationError(_("Renewal window period cannot exceed 365 days"))

    @api.constrains('default_seat_count')
    def _check_default_seat_count(self):
        """Validate seat count configuration"""
        for product in self:
            if product.is_subscription and product.supports_seats:
                if product.default_seat_count <= 0:
                    raise ValidationError(_("Default seat count must be greater than 0"))
                if product.default_seat_count > 10000:
                    raise ValidationError(_("Default seat count cannot exceed 10,000"))

    @api.constrains('is_subscription', 'default_billing_period_id')
    def _check_subscription_billing_period(self):
        """Ensure subscription products have billing periods"""
        for product in self:
            if product.is_subscription and not product.default_billing_period_id:
                # Only warn, don't prevent saving - allow configuration in progress
                _logger.warning(
                    f"Subscription product '{product.name}' is missing default billing period"
                )

    # ========================================================================
    # QUERY METHODS
    # ========================================================================

    @api.model
    def get_subscription_products(self):
        """Get all subscription products"""
        return self.search([('is_subscription', '=', True)])

    @api.model
    def get_auto_renewable_products(self):
        """Get subscription products that support auto-renewal"""
        return self.search([
            ('is_subscription', '=', True),
            ('is_renewable', '=', True),
            ('auto_renewal_enabled', '=', True)
        ])

    @api.model
    def get_enterprise_subscription_products(self):
        """Get enterprise scope subscription products"""
        return self.search([
            ('is_subscription', '=', True),
            ('subscription_scope', '=', 'enterprise')
        ])

    @api.model
    def get_individual_subscription_products(self):
        """Get individual scope subscription products"""
        return self.search([
            ('is_subscription', '=', True),
            ('subscription_scope', '=', 'individual')
        ])

    @api.model
    def get_subscription_products_by_billing_period(self, billing_period_id):
        """Get subscription products using specific billing period"""
        return self.search([
            ('is_subscription', '=', True),
            ('default_billing_period_id', '=', billing_period_id)
        ])

    @api.model
    def get_subscription_products_with_issues(self):
        """Get subscription products with configuration issues"""
        return self.search([('has_subscription_issues', '=', True)])

    # ========================================================================
    # UI ACTIONS
    # ========================================================================

    def action_test_subscription_config(self):
        """Test subscription configuration and display results"""
        self.ensure_one()
        
        if not self.is_subscription:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Not a Subscription Product',
                    'message': 'This product is not configured as a subscription product.',
                    'type': 'warning',
                }
            }
        
        details = self.get_subscription_details()
        
        config_info = []
        config_info.append(f"Subscription Scope: {details['subscription_scope_display']}")
        
        if details.get('billing_period_name'):
            config_info.append(f"Billing Period: {details['billing_period_name']}")
        else:
            config_info.append("⚠️ Missing billing period")
        
        config_info.append(f"Renewable: {'Yes' if details['is_renewable'] else 'No'}")
        
        if details['is_renewable']:
            config_info.append(f"Auto-renewal: {'Enabled' if details['auto_renewal_enabled'] else 'Disabled'}")
            config_info.append(f"Renewal Window: {details['renewal_window_days']} days")
        
        if details['supports_seats']:
            config_info.append(f"Seats: {details['default_seat_count']} default")
        
        if details['requires_approval']:
            workflow_name = details.get('approval_workflow_name', 'Not configured')
            config_info.append(f"Approval Required: {workflow_name}")
        
        if details['has_issues']:
            config_info.append(f"\n⚠️ Issues: {details['issue_message']}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'Subscription Configuration: {self.name}',
                'message': '\n'.join(config_info),
                'type': 'success' if not details['has_issues'] else 'warning',
                'sticky': True,
            }
        }

    def action_view_billing_periods(self):
        """Open billing periods for selection"""
        return {
            'name': _('Billing Periods'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.period',
            'view_mode': 'tree,form',
            'domain': [('active', '=', True)],
            'target': 'current',
            'context': {'from_subscription_product': True}
        }