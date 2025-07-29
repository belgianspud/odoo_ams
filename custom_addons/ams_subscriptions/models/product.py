from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Enhanced subscription fields
    is_subscription_product = fields.Boolean('Is Subscription Product', default=False)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type')
    
    # Recurring settings
    is_recurring = fields.Boolean('Is Recurring', default=False)
    recurring_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Recurring Period', default='yearly')
    
    # Auto-renewal settings
    auto_renewal = fields.Boolean('Auto Renewal', default=True)
    renewal_reminder_days = fields.Integer('Renewal Reminder (Days)', default=30,
                                          help="Days before expiry to send renewal reminder")
    
    # Chapter linking for memberships
    auto_create_chapters = fields.Boolean('Auto Create Chapters', default=False,
                                         help="Automatically create chapter subscriptions when membership is purchased")
    default_chapter_ids = fields.Many2many('ams.chapter', 'product_chapter_rel', 
                                          'product_id', 'chapter_id', 
                                          'Default Chapters',
                                          help="Chapters to automatically add with this membership")
    
    # E-commerce settings
    website_published = fields.Boolean('Published on Website', default=False)
    #available_in_pos = fields.Boolean('Available in POS', default=True)
    
    # Statistics
    subscription_count = fields.Integer('Subscription Count', compute='_compute_subscription_count')
    
    @api.depends('product_variant_ids.subscription_ids')
    def _compute_subscription_count(self):
        for template in self:
            count = 0
            for variant in template.product_variant_ids:
                count += len(variant.subscription_ids)
            template.subscription_count = count
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Set defaults when marking as subscription product"""
        if self.is_subscription_product:
            self.type = 'service'
            self.is_recurring = True
            if not self.subscription_type_id:
                # Try to find default membership type
                membership_type = self.env['ams.subscription.type'].search([('code', '=', 'membership')], limit=1)
                if membership_type:
                    self.subscription_type_id = membership_type.id
        else:
            self.is_recurring = False
            self.auto_renewal = False
            self.auto_create_chapters = False
            self.default_chapter_ids = False
    
    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        """Update fields based on subscription type"""
        if self.subscription_type_id:
            if self.subscription_type_id.code == 'membership':
                self.auto_create_chapters = True
            else:
                self.auto_create_chapters = False
                self.default_chapter_ids = False
    
    def action_create_subscription(self):
        """Action to create subscription from product"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Subscription',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'context': {
                'default_subscription_type_id': self.subscription_type_id.id,
                'default_product_id': self.product_variant_id.id,
                'default_amount': self.list_price,
                'default_is_recurring': self.is_recurring,
                'default_recurring_period': self.recurring_period,
            }
        }
    
    def action_view_subscriptions(self):
        """Action to view all subscriptions created from this product"""
        subscriptions = self.env['ams.subscription'].search([
            ('product_id', 'in', self.product_variant_ids.ids)
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', subscriptions.ids)],
            'context': {'default_product_id': self.product_variant_id.id}
        }

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    subscription_ids = fields.One2many('ams.subscription', 'product_id', 'Related Subscriptions')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    is_membership = fields.Boolean(
        'Is Membership Product',
        #compute='_compute_is_membership',
        store=True,
        help="Whether this product is specifically a membership product"
    )
    
    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """Override to create subscriptions for subscription products"""
        result = super()._action_launch_stock_rule(previous_product_uom_qty)
        
        for line in self:
            if (line.product_id.is_subscription_product and 
                line.order_id.state == 'sale' and 
                not line.subscription_id):
                line._create_subscription_from_sale()
        
        return result
    
    subscription_id = fields.Many2one('ams.subscription', 'Created Subscription', readonly=True)
    
    def _create_subscription_from_sale(self):
        """Create subscription from sale order line"""
        if not self.product_id.subscription_type_id:
            return
        
        # Calculate end date based on recurring period
        start_date = fields.Date.today()
        if self.product_id.recurring_period == 'monthly':
            end_date = start_date + relativedelta(months=1)
        elif self.product_id.recurring_period == 'quarterly':
            end_date = start_date + relativedelta(months=3)
        else:  # yearly
            end_date = start_date + relativedelta(years=1)
            
        subscription_vals = {
            'partner_id': self.order_id.partner_id.id,
            'subscription_type_id': self.product_id.subscription_type_id.id,
            'product_id': self.product_id.id,
            'name': f"{self.product_id.name} - {self.order_id.partner_id.name}",
            'sale_order_line_id': self.id,
            'amount': self.price_unit,
            'start_date': start_date,
            'end_date': end_date,
            'is_recurring': self.product_id.is_recurring,
            'recurring_period': self.product_id.recurring_period,
            'auto_renewal': self.product_id.auto_renewal,
            'next_renewal_date': end_date,
            'state': 'active',
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        self.subscription_id = subscription.id
        
        # Auto-create chapter subscriptions if enabled
        if (self.product_id.auto_create_chapters and 
            self.product_id.default_chapter_ids and
            subscription.subscription_code == 'membership'):
            subscription._create_chapter_subscriptions(self.product_id.default_chapter_ids)
        
        return subscription

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    subscription_id = fields.Many2one('ams.subscription', 'Related Subscription')
    is_renewal_invoice = fields.Boolean('Is Renewal Invoice', default=False)