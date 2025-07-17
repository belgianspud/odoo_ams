from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Subscription Configuration
    is_subscription = fields.Boolean('Is Subscription Product', default=False,
                                    help="Check if this product is used for subscriptions")
    subscription_plan_ids = fields.One2many('ams.subscription.plan', 'product_id', 
                                           'Subscription Plans')
    subscription_plan_count = fields.Integer('Subscription Plans Count', 
                                           compute='_compute_subscription_plan_count')
    
    # Default subscription settings
    default_billing_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Default Billing Period', default='annual')
    
    default_auto_renew = fields.Boolean('Default Auto Renew', default=True)
    default_trial_period = fields.Integer('Default Trial Period (Days)', default=0)
    
    @api.depends('subscription_plan_ids')
    def _compute_subscription_plan_count(self):
        for product in self:
            product.subscription_plan_count = len(product.subscription_plan_ids)
    
    def action_view_subscription_plans(self):
        """Action to view subscription plans for this product"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Plans'),
            'res_model': 'ams.subscription.plan',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }
    
    @api.onchange('is_subscription')
    def _onchange_is_subscription(self):
        """Set default values when enabling subscription"""
        if self.is_subscription:
            self.type = 'service'
            self.invoice_policy = 'order'
            self.purchase_ok = False
        
    @api.model
    def create(self, vals):
        """Override create to set subscription defaults"""
        if vals.get('is_subscription'):
            vals.update({
                'type': 'service',
                'invoice_policy': 'order',
                'purchase_ok': False,
            })
        return super().create(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def action_create_subscription_plan(self):
        """Create a subscription plan for this product"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Subscription Plan'),
            'res_model': 'ams.subscription.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_name': f"{self.name} Plan",
                'default_price': self.list_price,
                'default_billing_period': self.default_billing_period or 'annual',
                'default_auto_renew': self.default_auto_renew,
                'default_trial_period_days': self.default_trial_period,
            },
        }