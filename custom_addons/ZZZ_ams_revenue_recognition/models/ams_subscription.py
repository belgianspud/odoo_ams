# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AMSSubscription(models.Model):
    """Extend AMS Subscription with Revenue Recognition Integration"""
    _inherit = 'ams.subscription'
    
    # Revenue Recognition Fields
    revenue_schedule_ids = fields.One2many(
        'ams.revenue.schedule',
        'subscription_id',
        string='Revenue Recognition Schedules',
        help='Revenue recognition schedules associated with this subscription'
    )
    
    total_deferred_revenue = fields.Monetary(
        string='Total Deferred Revenue',
        compute='_compute_revenue_recognition_totals',
        currency_field='currency_id',
        store=True,
        help='Total unrecognized revenue for this subscription'
    )
    
    total_recognized_revenue = fields.Monetary(
        string='Total Recognized Revenue',
        compute='_compute_revenue_recognition_totals',
        currency_field='currency_id', 
        store=True,
        help='Total recognized revenue for this subscription'
    )
    
    active_schedules_count = fields.Integer(
        string='Active Recognition Schedules',
        compute='_compute_revenue_recognition_totals',
        store=True,
        help='Number of active revenue recognition schedules'
    )
    
    # Revenue Recognition Status
    recognition_status = fields.Selection([
        ('none', 'No Recognition Required'),
        ('pending', 'Recognition Pending'),
        ('active', 'Recognition Active'),
        ('completed', 'Recognition Completed'),
    ], string='Recognition Status', 
    compute='_compute_recognition_status',
    store=True,
    help='Current revenue recognition status')
    
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_date',
        help='Next date revenue will be recognized'
    )
    
    # Currency for monetary fields
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for revenue amounts'
    )

    @api.depends('revenue_schedule_ids.deferred_amount', 'revenue_schedule_ids.recognized_amount', 'revenue_schedule_ids.state')
    def _compute_revenue_recognition_totals(self):
        """Compute revenue recognition totals from schedules"""
        for subscription in self:
            schedules = subscription.revenue_schedule_ids
            
            subscription.total_deferred_revenue = sum(schedules.mapped('deferred_amount'))
            subscription.total_recognized_revenue = sum(schedules.mapped('recognized_amount'))
            subscription.active_schedules_count = len(schedules.filtered(lambda s: s.state == 'active'))
    
    @api.depends('revenue_schedule_ids', 'revenue_schedule_ids.state', 'product_id.revenue_recognition_method')
    def _compute_recognition_status(self):
        """Compute overall recognition status"""
        for subscription in self:
            if not subscription.product_id.is_subscription_product:
                subscription.recognition_status = 'none'
                continue
                
            if not subscription.product_id.use_ams_accounting:
                subscription.recognition_status = 'none'
                continue
            
            schedules = subscription.revenue_schedule_ids
            
            if not schedules:
                # Check if recognition is needed
                if subscription.product_id.revenue_recognition_method == 'immediate':
                    subscription.recognition_status = 'none'
                else:
                    subscription.recognition_status = 'pending'
            else:
                # Analyze schedule states
                active_schedules = schedules.filtered(lambda s: s.state == 'active')
                completed_schedules = schedules.filtered(lambda s: s.state == 'completed')
                
                if active_schedules:
                    subscription.recognition_status = 'active'
                elif completed_schedules and not active_schedules:
                    subscription.recognition_status = 'completed'
                else:
                    subscription.recognition_status = 'pending'
    
    @api.depends('revenue_schedule_ids.next_recognition_date')
    def _compute_next_recognition_date(self):
        """Compute next recognition date across all schedules"""
        for subscription in self:
            next_dates = subscription.revenue_schedule_ids.filtered(
                lambda s: s.state == 'active' and s.next_recognition_date
            ).mapped('next_recognition_date')
            
            if next_dates:
                subscription.next_recognition_date = min(next_dates)
            else:
                subscription.next_recognition_date = False
    
    def create_revenue_recognition_schedules(self):
        """Create revenue recognition schedules for this subscription"""
        self.ensure_one()
        
        # Check if product supports revenue recognition
        if not self.product_id.is_subscription_product or not self.product_id.use_ams_accounting:
            return False
        
        # Find invoices related to this subscription
        invoices = self.env['account.move'].search([
            ('ams_subscription_id', '=', self.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice')
        ])
        
        created_schedules = self.env['ams.revenue.schedule']
        
        for invoice in invoices:
            for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id.product_tmpl_id == self.product_id.product_tmpl_id):
                # Check if schedule already exists
                existing = self.env['ams.revenue.schedule'].search([
                    ('invoice_line_id', '=', line.id)
                ], limit=1)
                
                if not existing:
                    # Create schedule using product method
                    schedule = self.product_id.product_tmpl_id.create_recognition_schedule(line)
                    if schedule:
                        created_schedules |= schedule
        
        return created_schedules
    
    def process_revenue_recognition(self, cutoff_date=None):
        """Process revenue recognition for this subscription"""
        self.ensure_one()
        
        if not cutoff_date:
            cutoff_date = fields.Date.today()
        
        processed_count = 0
        for schedule in self.revenue_schedule_ids.filtered(lambda s: s.state == 'active'):
            initial_recognized = schedule.recognized_amount
            schedule.process_due_recognitions(cutoff_date)
            
            if schedule.recognized_amount > initial_recognized:
                processed_count += 1
        
        return processed_count
    
    def action_view_revenue_schedules(self):
        """View revenue recognition schedules for this subscription"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognition - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
    
    def action_create_recognition_schedules(self):
        """Action to create revenue recognition schedules"""
        self.ensure_one()
        
        schedules = self.create_revenue_recognition_schedules()
        
        if schedules:
            message = f'Created {len(schedules)} revenue recognition schedule(s)'
            message_type = 'success'
        else:
            message = 'No revenue recognition schedules needed or schedules already exist'
            message_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': message_type,
            }
        }
    
    def action_process_recognition(self):
        """Action to process revenue recognition"""
        self.ensure_one()
        
        processed = self.process_revenue_recognition()
        
        if processed > 0:
            message = f'Processed revenue recognition for {processed} schedule(s)'
            message_type = 'success'
        else:
            message = 'No revenue recognition entries were due for processing'
            message_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': message_type,
            }
        }
    
    def get_revenue_recognition_summary(self):
        """Get summary of revenue recognition for this subscription"""
        self.ensure_one()
        
        return {
            'subscription_id': self.id,
            'subscription_name': self.name,
            'partner_name': self.partner_id.name,
            'product_name': self.product_id.name,
            'recognition_status': self.recognition_status,
            'total_deferred_revenue': self.total_deferred_revenue,
            'total_recognized_revenue': self.total_recognized_revenue,
            'active_schedules_count': self.active_schedules_count,
            'next_recognition_date': self.next_recognition_date,
            'schedules': [
                {
                    'id': schedule.id,
                    'display_name': schedule.display_name,
                    'state': schedule.state,
                    'total_amount': schedule.total_amount,
                    'recognized_amount': schedule.recognized_amount,
                    'deferred_amount': schedule.deferred_amount,
                    'next_recognition_date': schedule.next_recognition_date,
                }
                for schedule in self.revenue_schedule_ids
            ]
        }
    
    # Override subscription state changes to handle revenue recognition
    def action_suspend(self):
        """Override suspend to handle revenue recognition"""
        result = super().action_suspend()
        
        # When suspending, you might want to pause revenue recognition
        # For now, just log the event
        for subscription in self:
            if subscription.revenue_schedule_ids:
                subscription.message_post(
                    body=_('Subscription suspended. Revenue recognition schedules remain active.')
                )
        
        return result
    
    def action_terminate(self):
        """Override terminate to handle revenue recognition"""
        result = super().action_terminate()
        
        # When terminating, handle remaining deferred revenue
        for subscription in self:
            active_schedules = subscription.revenue_schedule_ids.filtered(lambda s: s.state == 'active')
            if active_schedules:
                subscription.message_post(
                    body=_('Subscription terminated. Review remaining deferred revenue in active recognition schedules.')
                )
        
        return result
    
    @api.model
    def cron_process_subscription_recognition(self):
        """Cron job to process revenue recognition for all active subscriptions"""
        active_subscriptions = self.search([
            ('state', '=', 'active'),
            ('recognition_status', '=', 'active')
        ])
        
        total_processed = 0
        errors = []
        
        for subscription in active_subscriptions:
            try:
                processed = subscription.process_revenue_recognition()
                total_processed += processed
            except Exception as e:
                errors.append(f'Subscription {subscription.name}: {str(e)}')
        
        return {
            'total_processed': total_processed,
            'subscriptions_checked': len(active_subscriptions),
            'errors': errors
        }