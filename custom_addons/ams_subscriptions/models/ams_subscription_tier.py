# -*- coding: utf-8 -*-
from odoo import models, fields

class AMSSubscriptionTier(models.Model):
    _name = 'ams.subscription.tier'
    _description = 'AMS Subscription Tier'
    _order = 'sequence, name'

    name = fields.Char(string='Tier Name', required=True)
    description = fields.Text(string='Description')

    sequence = fields.Integer(string='Sequence', default=10)

    # Applicable Subscription Type
    subscription_type = fields.Selection([
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
    ], string='Subscription Type', required=True)

    # Lifecycle Rules
    period_length = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Period', default='annual')

    grace_days = fields.Integer(string='Grace Period (Days)', default=30)
    suspend_days = fields.Integer(string='Suspension Period (Days)', default=60)
    terminate_days = fields.Integer(string='Termination Period (Days)', default=30)

    auto_renew = fields.Boolean(string='Auto Renew By Default', default=True)
    is_free = fields.Boolean(string='Free Tier', default=False)

    # Benefits (chapters, publications, etc.)
    benefit_product_ids = fields.Many2many(
        'product.product',
        'ams_tier_product_rel',
        'tier_id',
        'product_id',
        string='Included Benefits',
        help='These products are automatically granted with this tier.'
    )

    # Default Seat Count for Enterprise Memberships
    default_seats = fields.Integer(string='Default Seats', default=0)

    # Notes for staff
    notes = fields.Text(string='Internal Notes')
