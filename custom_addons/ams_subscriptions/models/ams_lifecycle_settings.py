# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSLifecycleSettings(models.TransientModel):
    """Global configuration wizard for AMS lifecycle settings"""
    _name = 'ams.lifecycle.settings'
    _description = 'AMS Lifecycle Settings'

    default_grace_days = fields.Integer(
        string='Default Grace Period (Days)',
        default=30,
        help='Default grace period for new subscription tiers'
    )
    
    default_suspend_days = fields.Integer(
        string='Default Suspension Period (Days)',
        default=60,
        help='Default suspension period for new subscription tiers'
    )
    
    default_terminate_days = fields.Integer(
        string='Default Termination Period (Days)',
        default=30,
        help='Default termination period for new subscription tiers'
    )
    
    auto_create_renewal_invoices = fields.Boolean(
        string='Auto-Create Renewal Invoices',
        default=True,
        help='Automatically create renewal invoices before expiration'
    )
    
    renewal_notice_days = fields.Integer(
        string='Renewal Notice (Days Before)',
        default=14,
        help='How many days before expiration to create renewal invoices'
    )
    
    send_lifecycle_emails = fields.Boolean(
        string='Send Lifecycle Emails',
        default=True,
        help='Send automatic emails when subscriptions change state'
    )

    def apply_settings(self):
        """Apply settings to existing tiers and save as system parameters"""
        self.ensure_one()
        
        # Save as system parameters
        self.env['ir.config_parameter'].sudo().set_param('ams.default_grace_days', self.default_grace_days)
        self.env['ir.config_parameter'].sudo().set_param('ams.default_suspend_days', self.default_suspend_days)
        self.env['ir.config_parameter'].sudo().set_param('ams.default_terminate_days', self.default_terminate_days)
        self.env['ir.config_parameter'].sudo().set_param('ams.auto_create_renewal_invoices', self.auto_create_renewal_invoices)
        self.env['ir.config_parameter'].sudo().set_param('ams.renewal_notice_days', self.renewal_notice_days)
        self.env['ir.config_parameter'].sudo().set_param('ams.send_lifecycle_emails', self.send_lifecycle_emails)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Lifecycle settings have been saved successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def default_get(self, fields_list):
        """Load current settings from system parameters"""
        res = super().default_get(fields_list)
        
        get_param = self.env['ir.config_parameter'].sudo().get_param
        
        res.update({
            'default_grace_days': int(get_param('ams.default_grace_days', 30)),
            'default_suspend_days': int(get_param('ams.default_suspend_days', 60)),
            'default_terminate_days': int(get_param('ams.default_terminate_days', 30)),
            'auto_create_renewal_invoices': get_param('ams.auto_create_renewal_invoices', 'True') == 'True',
            'renewal_notice_days': int(get_param('ams.renewal_notice_days', 14)),
            'send_lifecycle_emails': get_param('ams.send_lifecycle_emails', 'True') == 'True',
        })
        
        return res


class AMSSubscriptionTier(models.Model):
    """Enhanced subscription tier model"""
    _inherit = 'ams.subscription.tier'
    
    # Add some computed fields for better reporting
    active_subscriptions_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_stats'
    )
    
    total_revenue_ytd = fields.Float(
        string='Revenue YTD',
        compute='_compute_subscription_stats'
    )
    
    @api.depends('name')  # Dummy dependency - in real implementation you'd depend on subscription records
    def _compute_subscription_stats(self):
        for tier in self:
            # Get active subscriptions for this tier
            active_subs = self.env['ams.subscription'].search([
                ('tier_id', '=', tier.id),
                ('state', '=', 'active')
            ])
            tier.active_subscriptions_count = len(active_subs)
            
            # Calculate YTD revenue (simplified)
            tier.total_revenue_ytd = 0.0
            # TODO: Integrate with accounting for actual revenue calculation


class ProductTemplate(models.Model):
    """Additional enhancements to product template"""
    _inherit = 'product.template'
    
    def action_create_subscription_tier(self):
        """Create a subscription tier based on this product"""
        self.ensure_one()
        
        if self.ams_product_type == 'none':
            raise UserError("This is not an AMS subscription product.")
        
        tier_vals = {
            'name': f"{self.name} Tier",
            'description': self.description or f"Tier for {self.name}",
            'subscription_type': self.ams_product_type,
            'period_length': self.subscription_period,
            'grace_days': self.grace_days,
            'suspend_days': self.suspend_days,
            'terminate_days': self.terminate_days,
        }
        
        tier = self.env['ams.subscription.tier'].create(tier_vals)
        self.subscription_tier_id = tier.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Subscription Tier',
            'res_model': 'ams.subscription.tier',
            'res_id': tier.id,
            'view_mode': 'form',
            'target': 'new',
        }