# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSSubscription(models.Model):
    """
    Basic subscription model for revenue recognition
    This is a simplified version that works with the revenue recognition module
    """
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Subscription Reference', required=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Member', required=True)
    product_id = fields.Many2one('product.template', string='Product', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Basic subscription info
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    price = fields.Monetary(string='Price', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Revenue recognition fields
    recognition_status = fields.Selection([
        ('none', 'No Recognition'),
        ('pending', 'Recognition Pending'),
        ('active', 'Recognition Active'),
        ('completed', 'Recognition Completed'),
    ], string='Revenue Recognition Status', default='none', compute='_compute_recognition_status')
    
    revenue_schedule_ids = fields.One2many('ams.revenue.schedule', 'subscription_id', string='Revenue Schedules')
    
    @api.depends('revenue_schedule_ids', 'revenue_schedule_ids.state')
    def _compute_recognition_status(self):
        for subscription in self:
            if not subscription.revenue_schedule_ids:
                subscription.recognition_status = 'none'
            elif any(schedule.state == 'active' for schedule in subscription.revenue_schedule_ids):
                subscription.recognition_status = 'active'
            elif all(schedule.state == 'completed' for schedule in subscription.revenue_schedule_ids):
                subscription.recognition_status = 'completed'
            else:
                subscription.recognition_status = 'pending'
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.subscription') or 'New'
        return super().create(vals)