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
    
    # Computed Fields - RENAMED to avoid conflicts
    @api.depends('ams_product_type')
    def _compute_revenue_recognition_stats(self):
        """Compute revenue recognition statistics"""
        for product in self:
            if product.ams_product_type == 'none':
                product.active_recognition_schedules = 0
                product.total_deferred_revenue = 0
                product.monthly_recognized_revenue = 0
            else:
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
    
    # FIXED: Use unique method names and call super() to avoid conflicts
    @api.onchange('subscription_period')
    def _onchange_subscription_period_for_revenue_recognition(self):
        """Update recognition settings when subscription period changes"""
        # Call super to ensure other modules' logic runs
        super()._onchange_subscription_period_for_revenue_recognition() if hasattr(super(), '_onchange_subscription_period_for_revenue_recognition') else None
        
        if self.subscription_period and self.revenue_recognition_period == 'subscription_period':
            # Match recognition frequency to subscription period for logical defaults
            if self.subscription_period == 'monthly':
                self.recognition_frequency = 'monthly'
            elif self.subscription_period == 'quarterly':
                self.recognition_frequency = 'monthly'  # Still recognize monthly even for quarterly billing
            elif self.subscription_period == 'annual':
                self.recognition_frequency = 'monthly'  # Monthly recognition for annual subscriptions
    
    # ALTERNATIVE: Use computed fields with @api.depends instead of onchange
    revenue_recognition_defaults_set = fields.Boolean(
        string='Revenue Recognition Defaults Set',
        compute='_compute_revenue_recognition_defaults',
        store=False,
        help='Technical field to trigger revenue recognition defaults'
    )
    
    @api.depends('ams_product_type', 'is_subscription_product')
    def _compute_revenue_recognition_defaults(self):
        """Set revenue recognition defaults based on product type"""
        for product in self:
            if product.is_subscription_product and product.ams_product_type != 'none':
                # Set defaults only if not already set
                if not product.revenue_recognition_method:
                    if product.ams_product_type == 'publication':
                        product.revenue_recognition_method = 'straight_line'
                        product.recognition_frequency = 'monthly'
                    elif product.ams_product_type in ['individual', 'enterprise']:
                        product.revenue_recognition_method = 'straight_line'
                        product.recognition_frequency = 'monthly'
                    elif product.ams_product_type == 'chapter':
                        product.revenue_recognition_method = 'straight_line'
                        product.recognition_frequency = 'monthly'
                
                # Enable auto-creation of schedules
                if not hasattr(product, '_revenue_recognition_setup_done'):
                    product.auto_create_recognition_schedule = True
                
                # Set performance obligation description
                if not product.performance_obligation_description:
                    obligation_map = {
                        'individual': 'Provision of individual membership services and benefits',
                        'enterprise': 'Provision of enterprise membership services and seat access',
                        'chapter': 'Provision of chapter membership services and local benefits',
                        'publication': 'Delivery of publication content over subscription period'
                    }
                    product.performance_obligation_description = obligation_map.get(product.ams_product_type, '')
            
            product.revenue_recognition_defaults_set = True
    
    def setup_revenue_recognition_configuration(self):
        """Setup revenue recognition configuration for this product (called explicitly)"""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.use_ams_accounting:
            return
        
        # Set default recognition method if not set
        if not self.revenue_recognition_method:
            self.revenue_recognition_method = 'straight_line'
        
        # Set default recognition frequency if not set
        if not self.recognition_frequency:
            self.recognition_frequency = 'monthly'
        
        # Set performance obligation description if not set
        if not self.performance_obligation_description and self.ams_product_type != 'none':
            obligation_map = {
                'individual': 'Provision of individual membership services and benefits over the subscription period',
                'enterprise': 'Provision of enterprise membership services including seat access and enterprise features',
                'chapter': 'Provision of chapter membership services and access to local chapter benefits',
                'publication': 'Delivery and access to publication content over the subscription period'
            }
            self.performance_obligation_description = obligation_map.get(self.ams_product_type, '')
        
        # Set standalone selling price if not set
        if not self.standalone_selling_price and self.list_price:
            self.standalone_selling_price = self.list_price
        
        # Enable auto-creation of recognition schedules
        self.auto_create_recognition_schedule = True
    
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
    
    def action_configure_revenue_recognition(self):
        """Open wizard to configure revenue recognition"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Revenue Recognition',
            'res_model': 'ams.revenue.recognition.config.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_revenue_recognition_method': self.revenue_recognition_method,
                'default_recognition_frequency': self.recognition_frequency,
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