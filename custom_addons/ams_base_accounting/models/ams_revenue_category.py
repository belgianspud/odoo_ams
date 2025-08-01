# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSRevenueCategory(models.Model):
    _name = 'ams.revenue.category'
    _description = 'AMS Revenue Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Financial Settings
    account_id = fields.Many2one(
        'account.account',
        string='Default Account',
        help='Default account for this revenue category'
    )
    
    # Revenue Type
    revenue_type = fields.Selection([
        ('membership', 'Membership Dues'),
        ('chapter', 'Chapter Fees'),
        ('publication', 'Publication Sales'),
        ('event', 'Event Revenue'),
        ('training', 'Training & Education'),
        ('donation', 'Donations'),
        ('sponsorship', 'Sponsorships'),
        ('other', 'Other Revenue'),
    ], string='Revenue Type', required=True)
    
    # Statistics
    ytd_amount = fields.Float(
        string='YTD Amount',
        compute='_compute_ytd_amount',
        help='Year-to-date revenue for this category'
    )
    
    @api.depends('revenue_type')
    def _compute_ytd_amount(self):
        # This would calculate actual YTD amounts from account moves
        # For now, setting to 0 - will be implemented with full accounting integration
        for category in self:
            category.ytd_amount = 0.0