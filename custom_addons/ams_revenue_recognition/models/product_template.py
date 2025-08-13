# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Revenue Recognition Configuration
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Recognition'),
        ('manual', 'Manual Recognition'),
    ], string='Revenue Recognition Method', 
       compute='_compute_revenue_recognition_method', store=True,
       help='How revenue should be recognized for this product')
    
    recognition_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ], string='Recognition Period', default='monthly',
       help='How frequently revenue should be recognized')
    
    auto_create_recognition = fields.Boolean(
        string='Auto-Create Recognition Schedules',
        default=True,
        help='Automatically create revenue recognition schedules for this product'
    )
    
    auto_process_recognition = fields.Boolean(
        string='Auto-Process Recognition',
        default=True,
        help='Automatically process revenue recognition for this product'
    )
    
    # Statistical fields
    total_deferred_revenue = fields.Monetary(
        string='Total Deferred Revenue',
        compute='_compute_revenue_stats',
        help='Total deferred revenue for this product across all subscriptions'
    )
    
    total_recognized_revenue = fields.Monetary(
        string='Total Recognized Revenue',
        compute='_compute_revenue_stats',
        help='Total recognized revenue for this product'
    )
    
    active_recognition_schedules = fields.Integer(
        string='Active Recognition Schedules',
        compute='_compute_revenue_stats',
        help='Number of active revenue recognition schedules for this product'
    )
    
    @api.depends('subscription_period', 'is_subscription_product')
    def _compute_revenue_recognition_method(self):
        """Determine revenue recognition method based on subscription period"""
        for product in self:
            if not product.is_subscription_product:
                product.revenue_recognition_method = 'immediate'
            elif product.subscription_period == 'monthly':
                product.revenue_recognition_method = 'immediate'
            elif product.subscription_period in ['annual', 'quarterly']:
                product.revenue_recognition_method = 'deferred'
            else:
                product.revenue_recognition_method = 'immediate'
    
    @api.depends('subscription_period')
    def _compute_revenue_stats(self):
        """Compute revenue recognition statistics"""
        for product in self:
            # Get revenue schedules for this product
            schedules = self.env['ams.revenue.schedule'].search([
                ('product_id', '=', product.id),
                ('state', 'in', ['active', 'completed'])
            ])
            
            product.total_deferred_revenue = sum(schedules.mapped('deferred_amount'))
            product.total_recognized_revenue = sum(schedules.mapped('recognized_amount'))
            product.active_recognition_schedules = len(schedules.filtered(lambda s: s.state == 'active'))
    
    def action_view_recognition_schedules(self):
        """View revenue recognition schedules for this product"""
        return {
            'name': f'Revenue Recognition - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }
    
    def action_process_due_recognitions(self):
        """Process any overdue revenue recognition for this product"""
        schedules = self.env['ams.revenue.schedule'].search([
            ('product_id', '=', self.id),
            ('state', '=', 'active')
        ])
        
        processed_count = 0
        for schedule in schedules:
            due_lines = schedule.recognition_line_ids.filtered(
                lambda l: l.state == 'pending' and l.recognition_date <= fields.Date.today()
            )
            if due_lines:
                schedule.process_due_recognitions()
                processed_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Processed revenue recognition for {processed_count} schedules',
                'type': 'success' if processed_count > 0 else 'info',
            }
        }