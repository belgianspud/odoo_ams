from odoo import models, fields, api

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _order = 'create_date desc'
    
    name = fields.Char(string='Subscription Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Member', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=True)
    
    subscription_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime')
    ], string='Subscription Type', default='yearly')
    
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    notes = fields.Text(string='Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        # Auto-generate subscription name if not provided
        for vals in vals_list:
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                vals['name'] = f"Subscription - {partner.name}"
        return super().create(vals_list)
    
    def action_activate(self):
        self.state = 'active'
    
    def action_cancel(self):
        self.state = 'cancelled'
    
    def action_renew(self):
        self.state = 'active'
        # Extend end date based on subscription type
        if self.subscription_type == 'monthly':
            self.end_date = fields.Date.add(self.end_date, months=1)
        elif self.subscription_type == 'yearly':
            self.end_date = fields.Date.add(self.end_date, years=1)
