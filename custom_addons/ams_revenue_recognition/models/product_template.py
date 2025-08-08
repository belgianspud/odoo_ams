# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    """Enhanced Product Template with Revenue Recognition Features"""
    _inherit = 'product.template'

    # Revenue Recognition Configuration
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('straight_line', 'Straight Line over Period'),
        ('milestone', 'Milestone Based'),
        ('usage', 'Usage Based'),
        ('custom', 'Custom Schedule'),
    ], string='Revenue Recognition Method', default='straight_line',
       help='Method used for recognizing revenue from this product')
    
    revenue_recognition_period = fields.Selection([
        ('subscription_period', 'Match Subscription Period'),
        ('custom', 'Custom Period'),
        ('immediate', 'Immediate'),
    ], string='Recognition Period', default='subscription_period',
       help='Period over which to recognize revenue')
    
    custom_recognition_days = fields.Integer(
        string='Custom Recognition Days',
        help='Number of days over which to recognize revenue (when using custom period)'
    )
    
    # Performance Obligation Configuration (ASC 606)
    is_distinct_service = fields.Boolean(
        string='Distinct Service',
        default=True,
        help='This product represents a distinct performance obligation'
    )
    
    standalone_selling_price = fields.Float(
        string='Standalone Selling Price',
        help='Price at which this product is sold separately (for ASC 606 allocation)'
    )
    
    performance_obligation_description = fields.Text(
        string='Performance Obligation Description',
        help='Description of the performance obligation for ASC 606 compliance'
    )
    
    # Revenue Recognition Automation
    auto_create_recognition_schedule = fields.Boolean(
        string='Auto-Create Recognition Schedule',
        default=True,
        help='Automatically create revenue recognition schedule when subscription is created'
    )
    
    recognition_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], string='Recognition Frequency', default='monthly',
       help='How often revenue should be recognized')
    
    # Contract Modification Settings
    allow_contract_modifications = fields.Boolean(
        string='Allow Contract Modifications',
        default=True,
        help='Allow mid-contract modifications that affect revenue recognition'
    )
    
    modification_treatment = fields.Selection([
        ('prospective', 'Prospective Treatment'),
        ('retrospective', 'Retrospective Treatment'),
        ('cumulative', 'Cumulative Catch-up'),
    ], string='Modification Treatment', default='prospective',
       help='Default treatment for contract modifications')
    
    # Revenue Recognition Statistics
    active_recognition_schedules = fields.Integer(
        string='Active Recognition Schedules',
        compute='_compute_revenue_recognition_stats',
        help='Number of active revenue recognition schedules for this product'
    )
    
    total_deferred_revenue = fields.Float(
        string='Total Deferred Revenue',
        compute='_compute_revenue_recognition_stats',
        help='Total deferred revenue for this product across all schedules'
    )
    
    monthly_recognized_revenue = fields.Float(
        string='Monthly Recognized Revenue',
        compute='_compute_revenue_recognition_stats',
        help='Revenue recognized this month for this product'
    )
    
    # Revenue Recognition Journal Configuration
    revenue_recognition_journal_id = fields.Many2one(
        'account.journal',
        string='Revenue Recognition Journal',
        domain="[('type', '=', 'general')]",
        help='Specific journal to use for revenue recognition entries for this product'
    )
    
    # Advanced Recognition Settings
    enable_proration = fields.Boolean(
        string='Enable Proration',
        default=True,
        help='Prorate revenue recognition for partial periods'
    )
    
    minimum_recognition_amount = fields.Float(
        string='Minimum Recognition Amount',
        default=0.01,
        help='Minimum amount to recognize in each period (prevents tiny amounts)'
    )
    
    # FIXED: Computed fields with safer dependencies
    @api.depends('is_subscription_product', 'use_ams_accounting')
    def _compute_revenue_recognition_stats(self):
        """Compute revenue recognition statistics - Only if AMS accounting is enabled"""
        for product in self:
            if not (product.is_subscription_product and product.use_ams_accounting):
                product.active_recognition_schedules = 0
                product.total_deferred_revenue = 0
                product.monthly_recognized_revenue = 0
                continue
                
            # Count active schedules
            schedules = self.env['ams.revenue.schedule'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ])
            product.active_recognition_schedules = len(schedules)
            
            # Sum deferred revenue
            product.total_deferred_revenue = sum(schedules.mapped('deferred_revenue_balance'))
            
            # Calculate monthly recognized revenue
            import datetime
            current_month_start = datetime.date.today().replace(day=1)
            current_month_recognitions = self.env['ams.revenue.recognition'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('recognition_date', '>=', current_month_start),
                ('state', '=', 'posted')
            ])
            product.monthly_recognized_revenue = sum(current_month_recognitions.mapped('recognized_amount'))
    
    # FIXED: Removed conflicting onchange methods, using model method instead
    def _setup_revenue_recognition_defaults(self):
        """Setup revenue recognition defaults - called explicitly to avoid conflicts"""
        if not (self.is_subscription_product and self.use_ams_accounting):
            return
            
        # Set defaults only if not already configured
        if not self.revenue_recognition_method:
            if hasattr(self, 'ams_product_type'):
                type_defaults = {
                    'publication': 'straight_line',
                    'individual': 'straight_line', 
                    'enterprise': 'straight_line',
                    'chapter': 'straight_line',
                }
                self.revenue_recognition_method = type_defaults.get(self.ams_product_type, 'straight_line')
            else:
                self.revenue_recognition_method = 'straight_line'
        
        if not self.recognition_frequency:
            self.recognition_frequency = 'monthly'
            
        if not self.auto_create_recognition_schedule:
            self.auto_create_recognition_schedule = True
            
        # Set performance obligation description
        if not self.performance_obligation_description and hasattr(self, 'ams_product_type'):
            descriptions = {
                'individual': 'Provision of individual membership services and benefits over the subscription period',
                'enterprise': 'Provision of enterprise membership services including seat access and enterprise features',
                'chapter': 'Provision of chapter membership services and access to local chapter benefits',
                'publication': 'Delivery and access to publication content over the subscription period'
            }
            self.performance_obligation_description = descriptions.get(self.ams_product_type, '')
        
        # Set standalone selling price if not set
        if not self.standalone_selling_price and self.list_price:
            self.standalone_selling_price = self.list_price

    def get_recognition_schedule_values(self, subscription, contract_value):
        """Get values for creating recognition schedule"""
        self.ensure_one()
        
        if not self.auto_create_recognition_schedule:
            return {}
        
        # Calculate recognition period
        start_date = subscription.start_date
        
        if self.revenue_recognition_period == 'subscription_period':
            end_date = subscription.paid_through_date
        elif self.revenue_recognition_period == 'custom' and self.custom_recognition_days:
            from datetime import timedelta
            end_date = start_date + timedelta(days=self.custom_recognition_days)
        elif self.revenue_recognition_period == 'immediate':
            end_date = start_date
        else:
            # Default to subscription period
            end_date = subscription.paid_through_date or start_date
        
        return {
            'subscription_id': subscription.id,
            'total_contract_value': contract_value,
            'start_date': start_date,
            'end_date': end_date,
            'recognition_method': self.revenue_recognition_method,
            'recognition_frequency': self.recognition_frequency,
            'is_auto_recognition': True,
            'performance_obligation_id': f'PO-{subscription.id}-{self.id}',
            'state': 'active',
        }
    
    def create_recognition_schedule_from_subscription(self, subscription):
        """Create revenue recognition schedule from subscription"""
        self.ensure_one()
        
        if not self.auto_create_recognition_schedule:
            return False
        
        # Calculate contract value
        contract_value = 0.0
        if subscription.invoice_line_id:
            contract_value = subscription.invoice_line_id.price_subtotal
        elif subscription.product_id:
            contract_value = subscription.product_id.list_price
        
        if contract_value <= 0:
            return False
        
        # Get schedule values
        schedule_vals = self.get_recognition_schedule_values(subscription, contract_value)
        if not schedule_vals:
            return False
        
        # Create the schedule
        schedule = self.env['ams.revenue.schedule'].create(schedule_vals)
        
        # Activate the schedule if in immediate recognition mode
        if self.revenue_recognition_method == 'immediate':
            schedule.action_activate()
            # Create immediate recognition
            recognition = self.env['ams.revenue.recognition'].create({
                'schedule_id': schedule.id,
                'recognition_date': schedule.start_date,
                'planned_amount': contract_value,
                'recognized_amount': contract_value,
                'state': 'draft',
            })
            recognition.action_recognize()
        else:
            schedule.action_activate()
        
        return schedule
    
    # Action Methods
    def action_view_recognition_schedules(self):
        """Action to view recognition schedules for this product"""
        self.ensure_one()
        
        return {
            'name': f'Recognition Schedules - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id if self.product_variant_id else False,
                'search_default_active': 1,
            }
        }
    
    def action_view_recognized_revenue(self):
        """Action to view recognized revenue for this product"""
        self.ensure_one()
        
        return {
            'name': f'Recognized Revenue - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'search_default_posted': 1,
                'group_by': 'recognition_date:month',
            }
        }
    
    def action_setup_revenue_recognition(self):
        """Setup revenue recognition for this product"""
        self.ensure_one()
        self._setup_revenue_recognition_defaults()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Revenue recognition configured successfully!',
                'type': 'success',
            }
        }
    
    # Validation Methods
    @api.constrains('custom_recognition_days')
    def _check_custom_recognition_days(self):
        """Validate custom recognition days"""
        for product in self:
            if product.revenue_recognition_period == 'custom' and product.custom_recognition_days <= 0:
                raise UserError("Custom recognition days must be positive.")
    
    @api.constrains('minimum_recognition_amount')
    def _check_minimum_recognition_amount(self):
        """Validate minimum recognition amount"""
        for product in self:
            if product.minimum_recognition_amount < 0:
                raise UserError("Minimum recognition amount cannot be negative.")
    
    @api.constrains('standalone_selling_price')
    def _check_standalone_selling_price(self):
        """Validate standalone selling price"""
        for product in self:
            if product.standalone_selling_price and product.standalone_selling_price < 0:
                raise UserError("Standalone selling price cannot be negative.")
    
    # Reporting Methods
    def get_revenue_recognition_summary(self, date_from=None, date_to=None):
        """Get revenue recognition summary for this product"""
        self.ensure_one()
        
        domain = [('product_id.product_tmpl_id', '=', self.id)]
        
        if date_from:
            domain.append(('recognition_date', '>=', date_from))
        if date_to:
            domain.append(('recognition_date', '<=', date_to))
        
        recognitions = self.env['ams.revenue.recognition'].search(domain + [('state', '=', 'posted')])
        schedules = self.env['ams.revenue.schedule'].search([
            ('product_id.product_tmpl_id', '=', self.id),
            ('state', 'in', ['active', 'completed'])
        ])
        
        return {
            'product_name': self.name,
            'total_recognized': sum(recognitions.mapped('recognized_amount')),
            'total_deferred': sum(schedules.mapped('deferred_revenue_balance')),
            'active_schedules': len(schedules.filtered(lambda s: s.state == 'active')),
            'completed_schedules': len(schedules.filtered(lambda s: s.state == 'completed')),
            'recognition_count': len(recognitions),
            'avg_monthly_recognition': sum(recognitions.mapped('recognized_amount')) / max(1, len(recognitions)),
        }