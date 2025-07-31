from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionTemplate(models.Model):
    """Templates for quick subscription creation"""
    _name = 'ams.subscription.template'
    _description = 'Subscription Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    description = fields.Html(string='Description')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Template Configuration
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Default Membership Type',
        required=True
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Default Chapter'
    )
    
    # Pricing Template
    use_custom_pricing = fields.Boolean(string='Use Custom Pricing')
    template_price = fields.Float(string='Template Price', digits='Product Price')
    default_discount = fields.Float(string='Default Discount %', digits='Discount')
    
    # Recurring Settings
    recurring_rule_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'), 
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Default Recurrence', default='yearly')
    
    recurring_interval = fields.Integer(string='Default Interval', default=1)
    auto_renew_default = fields.Boolean(string='Auto-Renew by Default')
    
    # Bundle Components
    is_bundle = fields.Boolean(string='Is Bundle Template')
    bundle_component_ids = fields.One2many(
        'ams.subscription.bundle.component',
        'template_id',
        string='Bundle Components'
    )
    
    # Trial Settings
    trial_period_days = fields.Integer(string='Trial Period (Days)', default=0)
    trial_requires_payment = fields.Boolean(string='Trial Requires Payment Method')
    
    # Approval Workflow
    requires_approval = fields.Boolean(string='Requires Approval')
    auto_approve_renewals = fields.Boolean(string='Auto-Approve Renewals', default=True)
    
    # Usage Statistics
    usage_count = fields.Integer(string='Usage Count', compute='_compute_usage_count')
    
    def _compute_usage_count(self):
        """Count how many times this template has been used"""
        for template in self:
            count = self.env['ams.member.subscription'].search_count([
                ('template_id', '=', template.id)
            ])
            template.usage_count = count

    def create_subscription_from_template(self, partner_id, **kwargs):
        """Create a subscription from this template"""
        self.ensure_one()
        
        # Base subscription values from template
        subscription_vals = {
            'partner_id': partner_id,
            'membership_type_id': self.membership_type_id.id,
            'chapter_id': self.chapter_id.id if self.chapter_id else False,
            'template_id': self.id,
            'recurring_rule_type': self.recurring_rule_type,
            'recurring_interval': self.recurring_interval,
            'auto_renew': self.auto_renew_default,
            'unit_price': self.template_price if self.use_custom_pricing else self.membership_type_id.price,
            'discount_percent': self.default_discount,
        }
        
        # Apply any overrides from kwargs
        subscription_vals.update(kwargs)
        
        # Create the subscription
        subscription = self.env['ams.member.subscription'].create(subscription_vals)
        
        # Handle bundle components
        if self.is_bundle:
            self._create_bundle_subscriptions(subscription, partner_id)
        
        # Handle trial period
        if self.trial_period_days > 0:
            subscription._setup_trial_period(self.trial_period_days)
        
        return subscription

    def _create_bundle_subscriptions(self, main_subscription, partner_id):
        """Create additional subscriptions for bundle components"""
        for component in self.bundle_component_ids:
            component_vals = {
                'partner_id': partner_id,
                'membership_type_id': component.membership_type_id.id,
                'parent_subscription_id': main_subscription.id,
                'unit_price': component.price_override or component.membership_type_id.price,
                'discount_percent': component.discount_percent,
                'bundle_component': True,
            }
            
            self.env['ams.member.subscription'].create(component_vals)


class AMSSubscriptionBundleComponent(models.Model):
    """Components of subscription bundles"""
    _name = 'ams.subscription.bundle.component'
    _description = 'Subscription Bundle Component'

    template_id = fields.Many2one(
        'ams.subscription.template',
        string='Template',
        required=True,
        ondelete='cascade'
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        required=True
    )
    
    sequence = fields.Integer(default=10)
    
    # Pricing
    price_override = fields.Float(string='Price Override', digits='Product Price')
    discount_percent = fields.Float(string='Discount %', digits='Discount')
    
    # Options
    is_optional = fields.Boolean(string='Optional Component')
    is_default_selected = fields.Boolean(string='Selected by Default', default=True)

