# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class ProductTemplate(models.Model):
    """Extend Product Template with Revenue Recognition Configuration"""
    _inherit = 'product.template'
    
    # Revenue Recognition Configuration
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Recognize Immediately'),
        ('deferred', 'Defer and Recognize Over Time'),
        ('manual', 'Manual Recognition'),
    ], string='Revenue Recognition Method', 
    compute='_compute_revenue_recognition_method',
    store=True,
    help='How revenue should be recognized for this subscription product')
    
    recognition_period = fields.Selection([
        ('monthly', 'Monthly Recognition'),
        ('quarterly', 'Quarterly Recognition'),
        ('annual', 'Annual Recognition'),
    ], string='Recognition Period', default='monthly',
    help='How often revenue should be recognized for deferred products')
    
    # Revenue Recognition Statistics (kept as computed, non-stored)
    total_deferred_revenue = fields.Monetary(
        string='Total Deferred Revenue',
        compute='_compute_revenue_stats',
        currency_field='currency_id',
        help='Total amount of unrecognized revenue for this product'
    )
    
    total_recognized_revenue = fields.Monetary(
        string='Total Recognized Revenue',
        compute='_compute_revenue_stats', 
        currency_field='currency_id',
        help='Total amount of recognized revenue for this product'
    )
    
    active_recognition_schedules = fields.Integer(
        string='Active Recognition Schedules',
        compute='_compute_revenue_stats',
        help='Number of active revenue recognition schedules'
    )

    # Auto-Recognition Settings
    auto_create_recognition = fields.Boolean(
        string='Auto-Create Recognition Schedules',
        default=True,
        help='Automatically create revenue recognition schedules when invoices are posted'
    )
    
    auto_process_recognition = fields.Boolean(
        string='Auto-Process Recognition',
        default=True,
        help='Allow automated processing of revenue recognition for this product'
    )

    @api.depends('subscription_period', 'is_subscription_product')
    def _compute_revenue_recognition_method(self):
        """Determine revenue recognition method based on subscription period"""
        for product in self:
            if not product.is_subscription_product:
                product.revenue_recognition_method = 'immediate'
            elif product.subscription_period in ['monthly']:
                # Monthly subscriptions - recognize immediately when invoiced
                product.revenue_recognition_method = 'immediate'
            elif product.subscription_period in ['quarterly', 'semi_annual', 'annual']:
                # Longer periods - defer and recognize over time
                product.revenue_recognition_method = 'deferred'
            else:
                # Default for subscription products
                product.revenue_recognition_method = 'deferred'
    
    def _compute_revenue_stats(self):
        """Compute revenue recognition statistics"""
        for product in self:
            if not product.is_subscription_product:
                product.total_deferred_revenue = 0.0
                product.total_recognized_revenue = 0.0
                product.active_recognition_schedules = 0
                continue
            
            # Find all revenue schedules for this product
            schedules = self.env['ams.revenue.schedule'].search([
                ('product_id.product_tmpl_id', '=', product.id)
            ])
            
            product.total_deferred_revenue = sum(schedules.mapped('deferred_amount'))
            product.total_recognized_revenue = sum(schedules.mapped('recognized_amount'))
            product.active_recognition_schedules = len(schedules.filtered(lambda s: s.state == 'active'))
    
    @api.onchange('revenue_recognition_method')
    def _onchange_revenue_recognition_method(self):
        """Update recognition period based on method"""
        if self.revenue_recognition_method == 'immediate':
            # No need for recognition period
            pass
        elif self.revenue_recognition_method == 'deferred':
            # Set default recognition period based on subscription period
            if self.subscription_period == 'annual':
                self.recognition_period = 'monthly'  # Recognize monthly for annual subscriptions
            elif self.subscription_period == 'quarterly':
                self.recognition_period = 'monthly'  # Recognize monthly for quarterly
            elif self.subscription_period == 'semi_annual':
                self.recognition_period = 'monthly'  # Recognize monthly for semi-annual

    def get_revenue_recognition_config(self):
        """Get revenue recognition configuration for this product"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'method': 'immediate', 'create_schedule': False}
        
        config = {
            'method': self.revenue_recognition_method,
            'recognition_period': self.recognition_period,
            'create_schedule': self.auto_create_recognition,
            'auto_process': self.auto_process_recognition,
            'revenue_account_id': self.ams_revenue_account_id.id if self.ams_revenue_account_id else False,
            'deferred_account_id': self.ams_deferred_account_id.id if self.ams_deferred_account_id else False,
        }
        
        return config
    
    def calculate_recognition_period_length(self):
        """Calculate how long revenue should be recognized over"""
        self.ensure_one()
        
        if self.revenue_recognition_method == 'immediate':
            return 0  # No recognition period
        
        # Base recognition period on subscription period
        period_mapping = {
            'monthly': 1,      # 1 month
            'quarterly': 3,    # 3 months  
            'semi_annual': 6,  # 6 months
            'annual': 12,      # 12 months
        }
        
        return period_mapping.get(self.subscription_period, 12)
    
    def should_defer_revenue(self):
        """Check if revenue should be deferred for this product"""
        self.ensure_one()
        
        # Must be subscription product with AMS accounting enabled
        if not self.is_subscription_product or not self.use_ams_accounting:
            return False
        
        # Check if we have deferred account configured
        if not self.ams_deferred_account_id:
            return False
        
        # Check recognition method
        return self.revenue_recognition_method == 'deferred'
    
    def create_recognition_schedule(self, invoice_line):
        """Create revenue recognition schedule for an invoice line"""
        self.ensure_one()
        
        if not self.should_create_recognition_schedule(invoice_line):
            return False
        
        # Calculate recognition dates
        start_date = fields.Date.today()
        recognition_months = self.calculate_recognition_period_length()
        
        if recognition_months <= 0:
            # Immediate recognition
            end_date = start_date
        else:
            # Calculate end date based on recognition period
            end_date = start_date + relativedelta(months=recognition_months) - relativedelta(days=1)
        
        # Create the schedule
        schedule_vals = {
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'total_amount': invoice_line.price_subtotal,
            'recognition_method': 'immediate' if recognition_months <= 0 else 'straight_line',
            'start_date': start_date,
            'end_date': end_date,
            'period_length': self.recognition_period,
            'state': 'draft',
        }
        
        # Link to subscription if available
        subscription = self._find_subscription_for_invoice_line(invoice_line)
        if subscription:
            schedule_vals['subscription_id'] = subscription.id
        
        schedule = self.env['ams.revenue.schedule'].create(schedule_vals)
        
        # Auto-activate if configured
        if self.auto_process_recognition:
            schedule.action_activate()
        
        return schedule
    
    def should_create_recognition_schedule(self, invoice_line):
        """Check if we should create a recognition schedule for this invoice line"""
        self.ensure_one()
        
        # Must be subscription product with AMS accounting
        if not self.is_subscription_product or not self.use_ams_accounting:
            return False
        
        # Must have auto-create enabled
        if not self.auto_create_recognition:
            return False
        
        # Check if schedule already exists
        existing = self.env['ams.revenue.schedule'].search([
            ('invoice_line_id', '=', invoice_line.id)
        ], limit=1)
        
        return not bool(existing)
    
    def _find_subscription_for_invoice_line(self, invoice_line):
        """Find related subscription for invoice line"""
        # Look for subscription created from this invoice
        subscription = self.env['ams.subscription'].search([
            ('invoice_line_id', '=', invoice_line.id)
        ], limit=1)
        
        if subscription:
            return subscription
        
        # Look for subscription by partner and product
        subscription = self.env['ams.subscription'].search([
            ('partner_id', '=', invoice_line.move_id.partner_id.id),
            ('product_id.product_tmpl_id', '=', self.id),
            ('state', '=', 'active')
        ], limit=1)
        
        return subscription
    
    # Custom search methods for advanced filtering
    @api.model 
    def search_products_with_deferred_revenue(self, min_amount=0):
        """Custom search method to find products with deferred revenue above threshold"""
        
        # First get all products that could have deferred revenue
        candidate_products = self.search([
            ('is_subscription_product', '=', True),
            ('use_ams_accounting', '=', True),
            ('revenue_recognition_method', '=', 'deferred')
        ])
        
        products_with_deferred = self.env['product.template']
        
        for product in candidate_products:
            # Calculate current deferred revenue for this product
            schedules = self.env['ams.revenue.schedule'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ])
            
            total_deferred = sum(schedules.mapped('deferred_amount'))
            
            if total_deferred > min_amount:
                products_with_deferred |= product
        
        return products_with_deferred
    
    @api.model
    def search_products_needing_recognition_review(self):
        """Find products that may need revenue recognition review"""
        
        # Products with active schedules but no recent recognition processing
        from datetime import date, timedelta
        cutoff_date = date.today() - timedelta(days=30)  # 30 days ago
        
        products_to_review = self.env['product.template']
        
        # Find products with overdue recognition entries
        overdue_recognitions = self.env['ams.revenue.recognition'].search([
            ('state', '=', 'pending'),
            ('recognition_date', '<', cutoff_date)
        ])
        
        for recognition in overdue_recognitions:
            if recognition.product_id.product_tmpl_id not in products_to_review:
                products_to_review |= recognition.product_id.product_tmpl_id
        
        return products_to_review
    
    def action_view_recognition_schedules(self):
        """View revenue recognition schedules for this product"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognition - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'search_default_active': 1,
            }
        }
    
    def action_process_due_recognitions(self):
        """Process due revenue recognitions for this product"""
        self.ensure_one()
        
        schedules = self.env['ams.revenue.schedule'].search([
            ('product_id.product_tmpl_id', '=', self.id),
            ('state', '=', 'active')
        ])
        
        total_processed = 0
        for schedule in schedules:
            schedule.process_due_recognitions()
            total_processed += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Processed revenue recognition for {total_processed} schedules',
                'type': 'success',
            }
        }
    
    def action_view_deferred_revenue_products(self):
        """Action to view products with deferred revenue"""
        products = self.search_products_with_deferred_revenue(min_amount=1)
        
        return {
            'name': 'Products with Deferred Revenue',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', products.ids)],
            'context': {'search_default_filter_deferred_recognition': 1},
        }
    
    def action_view_products_needing_review(self):
        """Action to view products needing revenue recognition review"""
        products = self.search_products_needing_recognition_review()
        
        return {
            'name': 'Products Needing Revenue Recognition Review',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', products.ids)],
            'context': {'search_default_group_by_recognition_method': 1},
        }
    
    @api.constrains('revenue_recognition_method', 'ams_deferred_account_id')
    def _check_revenue_recognition_config(self):
        """Validate revenue recognition configuration"""
        for product in self:
            if (product.is_subscription_product and 
                product.use_ams_accounting and 
                product.revenue_recognition_method == 'deferred' and 
                not product.ams_deferred_account_id):
                raise UserError(_(
                    'Deferred revenue account is required for product "%s" with deferred revenue recognition'
                ) % product.name)