from odoo import models, fields, api, _
from datetime import datetime


class SubscriptionLine(models.Model):
    _name = 'ams.subscription.line'
    _description = 'Subscription Line'
    _order = 'date desc, id desc'
    
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', required=True, 
                                     ondelete='cascade', index=True)
    date = fields.Date('Date', required=True, default=fields.Date.today)
    description = fields.Text('Description', required=True)
    price = fields.Float('Price', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 related='subscription_id.currency_id', store=True)
    
    # Line Types
    line_type = fields.Selection([
        ('activation', 'Activation'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('suspension', 'Suspension'),
        ('cancellation', 'Cancellation'),
        ('adjustment', 'Adjustment'),
    ], string='Line Type', default='activation')
    
    # Related fields for convenience
    partner_id = fields.Many2one('res.partner', related='subscription_id.partner_id', 
                                store=True, readonly=True)
    plan_id = fields.Many2one('ams.subscription.plan', related='subscription_id.plan_id',
                             store=True, readonly=True)
    
    # Invoice information
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True)
    
    # Payment status
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='pending')
    
    # Proration information
    is_prorated = fields.Boolean('Is Prorated', default=False)
    prorated_from = fields.Date('Prorated From')
    prorated_to = fields.Date('Prorated To')
    
    def name_get(self):
        result = []
        for line in self:
            name = f"{line.subscription_id.name} - {line.description}"
            result.append((line.id, name))
        return result