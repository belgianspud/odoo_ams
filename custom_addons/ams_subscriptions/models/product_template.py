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

    is_digital = fields.Boolean(
        string='Digital Publication',
        help='If checked, this is a digital publication; otherwise, it is a physical product.'
    )

    grace_days = fields.Integer(string='Grace Days', default=30)
    suspend_days = fields.Integer(string='Suspend Days', default=60)
    terminate_days = fields.Integer(string='Terminate Days', default=30)

    # 🔹 NEW: Link to default subscription tier
    subscription_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Default Subscription Tier',
        help='When this product is purchased, the subscription will be created using this tier.'
    )

    # 🔹 NEW: Special flag for enterprise seat add-on
    is_seat_addon = fields.Boolean(
        string='Enterprise Seat Add-On',
        help='If checked, purchasing this product adds seats to an existing Enterprise subscription.'
    )

    # 🔹 NEW: Reverse link to created subscriptions
    subscription_ids = fields.One2many(
        'ams.subscription',
        'product_id',
        string='Generated Subscriptions'
    )

    # Auto-configure AMS products for sales and website
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
            elif self.ams_product_type == 'publication' and self.is_digital:
                self.detailed_type = 'service'  # Digital publications are services
            elif self.ams_product_type == 'publication':
                self.detailed_type = 'product'  # Physical publications are products
            else:
                self.detailed_type = 'service'  # Chapters are services
            
            # Set default subscription period for recurring items
            if self.ams_product_type in ['individual', 'enterprise'] and self.subscription_period == 'none':
                self.subscription_period = 'annual'
            
            # Auto-set categories for website organization
            self._set_ams_category()

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
        
        if self.ams_product_type == 'individual':
            category = category_obj.search([('name', '=', 'Individual Memberships')], limit=1)
            if not category:
                category = category_obj.create({'name': 'Individual Memberships'})
            self.categ_id = category.id
            
        elif self.ams_product_type == 'enterprise':
            category = category_obj.search([('name', '=', 'Enterprise Memberships')], limit=1)
            if not category:
                category = category_obj.create({'name': 'Enterprise Memberships'})
            self.categ_id = category.id
            
        elif self.ams_product_type == 'chapter':
            category = category_obj.search([('name', '=', 'Chapters')], limit=1)
            if not category:
                category = category_obj.create({'name': 'Chapters'})
            self.categ_id = category.id
            
        elif self.ams_product_type == 'publication':
            category_name = 'Digital Publications' if self.is_digital else 'Print Publications'
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
