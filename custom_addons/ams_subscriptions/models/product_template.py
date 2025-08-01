# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # AMS Product Types
    ams_product_type = fields.Selection([
        ('none', 'None'),
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
    ], string='AMS Product Type', default='none')

    subscription_period = fields.Selection([
        ('none', 'No Subscription'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Subscription Period', default='none')

    # Publication specific fields
    is_digital = fields.Boolean(
        string='Digital Publication',
        help='If checked, this is a digital publication; otherwise, it is a physical product.'
    )
    
    publication_type = fields.Selection([
        ('journal', 'Journal'),
        ('magazine', 'Magazine'),
        ('newsletter', 'Newsletter'),
        ('book', 'Book'),
        ('report', 'Report'),
        ('other', 'Other'),
    ], string='Publication Type')

    # Lifecycle settings
    grace_days = fields.Integer(string='Grace Days', default=30)
    suspend_days = fields.Integer(string='Suspend Days', default=60)
    terminate_days = fields.Integer(string='Terminate Days', default=30)

    # Relationships
    subscription_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Default Subscription Tier',
        help='When this product is purchased, the subscription will be created using this tier.'
    )

    # Special flags
    is_seat_addon = fields.Boolean(
        string='Enterprise Seat Add-On',
        help='If checked, purchasing this product adds seats to an existing Enterprise subscription.'
    )
    
    is_subscription_product = fields.Boolean(
        string='Is Subscription Product',
        compute='_compute_is_subscription_product',
        store=True
    )

    # Related products for bundling
    child_product_ids = fields.Many2many(
        'product.template',
        'product_template_child_rel',
        'parent_id',
        'child_id',
        string='Included Products',
        help='Products automatically included with this subscription (e.g., chapters, publications)'
    )
    
    parent_product_ids = fields.Many2many(
        'product.template',
        'product_template_child_rel',
        'child_id',
        'parent_id',
        string='Included In',
        help='Subscriptions that include this product automatically'
    )

    # Statistics
    subscription_ids = fields.One2many(
        'ams.subscription',
        'product_id',
        string='Generated Subscriptions'
    )
    
    active_subscriptions_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_stats'
    )
    
    total_revenue_ytd = fields.Float(
        string='Revenue YTD',
        compute='_compute_subscription_stats'
    )

    @api.depends('ams_product_type')
    def _compute_is_subscription_product(self):
        for product in self:
            product.is_subscription_product = product.ams_product_type != 'none'

    @api.depends('subscription_ids')
    def _compute_subscription_stats(self):
        for product in self:
            active_subs = product.subscription_ids.filtered(lambda s: s.state == 'active')
            product.active_subscriptions_count = len(active_subs)
            
            # Calculate YTD revenue (simplified - you may want to integrate with accounting)
            product.total_revenue_ytd = 0.0
            # TODO: Calculate actual revenue from accounting records

    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Auto-configure product settings when AMS type is selected"""
        if self.ams_product_type != 'none':
            # Make it sellable and publishable
            self.sale_ok = True
            self.website_published = True
            
            # Set appropriate product type
            if self.ams_product_type in ['individual', 'enterprise']:
                self.detailed_type = 'service'  # Memberships are services
                if self.subscription_period == 'none':
                    self.subscription_period = 'annual'
            elif self.ams_product_type == 'publication':
                if self.is_digital:
                    self.detailed_type = 'service'  # Digital publications are services
                else:
                    self.detailed_type = 'product'  # Physical publications are products
            elif self.ams_product_type == 'chapter':
                self.detailed_type = 'service'  # Chapters are services
            
            # Auto-set categories for website organization
            self._set_ams_category()
        else:
            # Reset subscription-related fields
            self.subscription_period = 'none'
            self.subscription_tier_id = False
            self.is_seat_addon = False

    @api.onchange('is_digital')
    def _onchange_is_digital(self):
        """Update product type when digital flag changes"""
        if self.ams_product_type == 'publication':
            if self.is_digital:
                self.detailed_type = 'service'
            else:
                self.detailed_type = 'product'

    def _set_ams_category(self):
        """Set appropriate product category for AMS products"""
        category_obj = self.env['product.category']
        
        category_mapping = {
            'individual': 'Individual Memberships',
            'enterprise': 'Enterprise Memberships', 
            'chapter': 'Chapters',
            'publication': 'Digital Publications' if self.is_digital else 'Print Publications'
        }
        
        if self.ams_product_type in category_mapping:
            category_name = category_mapping[self.ams_product_type]
            category = category_obj.search([('name', '=', category_name)], limit=1)
            if not category:
                category = category_obj.create({'name': category_name})
            self.categ_id = category.id

    @api.model
    def create(self, vals):
        """Auto-configure AMS products on creation"""
        product = super().create(vals)
        if product.ams_product_type != 'none':
            product._onchange_ams_product_type()
        return product

    def action_publish_ams_product(self):
        """Quick action to publish AMS product on website"""
        self.ensure_one()
        self.website_published = True
        self.sale_ok = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{self.name} is now published on the website!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_subscriptions(self):
        """Action to view subscriptions for this product"""
        self.ensure_one()
        return {
            'name': f'Subscriptions for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {'default_product_id': self.product_variant_ids[0].id if self.product_variant_ids else False}
        }