# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class MembershipType(models.Model):
    _name = 'membership.type'
    _description = 'Membership Type'
    _order = 'sequence, name'

    name = fields.Char(string='Membership Type', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Pricing
    price = fields.Float(string='Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Duration
    duration_type = fields.Selection([
        ('fixed', 'Fixed Period'),
        ('unlimited', 'Unlimited'),
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
    ], string='Duration Type', default='yearly', required=True)
    
    duration_months = fields.Integer(string='Duration (Months)', default=12)
    
    # Settings
    active = fields.Boolean(string='Active', default=True)
    auto_renew = fields.Boolean(string='Auto Renew', default=False)
    grace_period_days = fields.Integer(string='Grace Period (Days)', default=30)
    
    # Product integration
    product_id = fields.Many2one('product.product', string='Related Product')
    
    # Statistics
    member_count = fields.Integer(string='Active Members', compute='_compute_member_count')
    
    @api.depends('name')
    def _compute_member_count(self):
        for record in self:
            record.member_count = self.env['membership.membership'].search_count([
                ('membership_type_id', '=', record.id),
                ('state', '=', 'active')
            ])
    
    @api.model
    def create(self, vals):
        # Create related product if not specified
        if not vals.get('product_id'):
            product_vals = {
                'name': vals.get('name'),
                'type': 'service',
                'list_price': vals.get('price', 0),
                'categ_id': self.env.ref('product.product_category_all').id,
                'sale_ok': True,
                'purchase_ok': False,
            }
            product = self.env['product.product'].create(product_vals)
            vals['product_id'] = product.id
        return super().create(vals)