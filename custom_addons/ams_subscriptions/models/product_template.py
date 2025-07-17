from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Subscription Configuration
    is_subscription = fields.Boolean('Is Subscription Product', default=False)
    subscription_plan_ids = fields.One2many('ams.subscription.plan', 'product_id', 
                                           'Subscription Plans')
    subscription_plan_count = fields.Integer('Subscription Plans Count', 
                                           compute='_compute_subscription_plan_count')
    
    # Default subscription settings
    default_billing_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Default Billing Period', default='annual')
    
    @api.depends('subscription_plan_ids')
    def _compute_subscription_plan_count(self):
        for product in self:
            product.subscription_plan_count = len(product.subscription_plan_ids)
    
    def action_view_subscription_plans(self):
        """View subscription plans for this product"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Plans'),
            'res_model': 'ams.subscription.plan',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def create_subscription(self, partner_id, plan_id=None):
        """Create a subscription for this product"""
        if not self.product_tmpl_id.is_subscription:
            raise UserError(_('This product is not a subscription product'))
        
        # If no plan specified, use the first available plan
        if not plan_id:
            plan = self.product_tmpl_id.subscription_plan_ids.filtered('active')[:1]
            if not plan:
                raise UserError(_('No active subscription plan found for this product'))
            plan_id = plan.id
        
        subscription_vals = {
            'partner_id': partner_id,
            'plan_id': plan_id,
            'price': self.list_price,
        }
        
        return self.env['ams.subscription'].create(subscription_vals)