from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_subscription = fields.Boolean(string="Is a Subscription Product")
    subscription_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string="Subscription Type")
    recurrence_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string="Recurrence Period")
    auto_invoice = fields.Boolean(string="Auto-Invoice on Add to Cart")
    enable_proration = fields.Boolean(string="Enable Proration?")
    fixed_start_date = fields.Boolean(string="Fixed Start Date (e.g., Jan 1)?")
