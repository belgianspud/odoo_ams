# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    """Enhanced Account Move with Revenue Recognition Integration"""
    _inherit = 'account.move'

    # Revenue Recognition Fields
    creates_deferred_revenue = fields.Boolean(
        string='Creates Deferred Revenue',
        compute='_compute_revenue_recognition_info',
        store=True,
        help='This invoice creates deferred revenue that needs recognition'
    )
    
    has_ams_revenue_products = fields.Boolean(
        string='Has AMS Revenue Products',
        compute='_compute_revenue_recognition_info',
        store=True,
        help='This invoice contains AMS products with revenue recognition'
    )
    
    revenue_schedule_ids = fields.One2many(
        'ams.revenue.schedule',
        'invoice_id',
        string='Revenue Schedules',
        help='Revenue recognition schedules created from this invoice'
    )
    
    total_deferred_amount = fields.Float(
        string='Total Deferred Amount',
        compute='_compute_revenue_amounts',
        store=True,
        help='Total amount deferred for future revenue recognition'
    )
    
    total_immediate_revenue = fields.Float(
        string='Total Immediate Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Total amount recognized immediately'
    )
    
    revenue_recognition_method = fields.Selection([
        ('mixed', 'Mixed Methods'),
        ('immediate', 'All Immediate'),
        ('deferred', 'All Deferred'),
        ('not_applicable', 'Not Applicable'),
    ], string='Revenue Recognition Method',
       compute='_compute_revenue_recognition_info',
       store=True,
       help='Revenue recognition method for this invoice')
    
    revenue_recognition_status = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending_setup', 'Pending Setup'),
        ('schedules_created', 'Schedules Created'),
        ('recognition_active', 'Recognition Active'),
        ('fully_recognized', 'Fully Recognized'),
        ('error', 'Error'),
    ], string='Revenue Recognition Status',
       compute='_compute_revenue_recognition_status',
       store=True,
       help='Current status of revenue recognition for this invoice')
    
    # ASC 606 Performance Obligation Tracking
    performance_obligations_count = fields.Integer(
        string='Performance Obligations',
        compute='_compute_performance_obligations',
        store=True,
        help='Number of distinct performance obligations in this invoice'
    )
    
    requires_allocation = fields.Boolean(
        string='Requires Price Allocation',
        compute='_compute_performance_obligations',
        store=True,
        help='This invoice requires price allocation across performance obligations'
    )
    
    # Revenue Recognition Processing
    revenue_recognition_processed = fields.Boolean(
        string='Revenue Recognition Processed',
        default=False,
        help='Revenue recognition has been processed for this invoice'
    )
    
    revenue_recognition_processed_date = fields.Datetime(
        string='Processing Date',
        help='Date when revenue recognition was processed'
    )
    
    revenue_recognition_error = fields.Text(
        string='Revenue Recognition Error',
        help='Error message if revenue recognition processing failed'
    )
    
    # Computed Fields
    @api.depends('invoice_line_ids.product_id.is_subscription_product',
                 'invoice_line_ids.product_id.use_ams_accounting',
                 'invoice_line_ids.product_id.revenue_recognition_method')
    def _compute_revenue_recognition_info(self):
        """Compute revenue recognition information"""
        for move in self:
            if move.move_type != 'out_invoice':
                move.creates_deferred_revenue = False
                move.has_ams_revenue_products = False
                move.revenue_recognition_method = 'not_applicable'
                continue
            
            ams_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.use_ams_accounting
            )
            
            move.has_ams_revenue_products = bool(ams_lines)
            
            if not ams_lines:
                move.creates_deferred_revenue = False
                move.revenue_recognition_method = 'not_applicable'
                continue
            
            # Check recognition methods
            recognition_methods = ams_lines.mapped('product_id.product_tmpl_id.revenue_recognition_method')
            
            has_deferred = any(method != 'immediate' for method in recognition_methods)
            has_immediate = any(method == 'immediate' for method in recognition_methods)
            
            move.creates_deferred_revenue = has_deferred
            
            if has_deferred and has_immediate:
                move.revenue_recognition_method = 'mixed'
            elif has_immediate:
                move.revenue_recognition_method = 'immediate'
            elif has_deferred:
                move.revenue_recognition_method = 'deferred'
            else:
                move.revenue_recognition_method = 'not_applicable'
    
    @api.depends('revenue_schedule_ids', 'revenue_schedule_ids.state', 'revenue_recognition_processed')
    def _compute_revenue_recognition_status(self):
        """Compute revenue recognition status"""
        for move in self:
            if not move.has_ams_revenue_products:
                move.revenue_recognition_status = 'not_applicable'
                continue
            
            if not move.revenue_recognition_processed:
                move.revenue_recognition_status = 'pending_setup'
                continue
            
            if move.revenue_recognition_error:
                move.revenue_recognition_status = 'error'
                continue
            
            schedules = move.revenue_schedule_ids
            if not schedules:
                if move.revenue_recognition_method == 'immediate':
                    move.revenue_recognition_status = 'fully_recognized'
                else:
                    move.revenue_recognition_status = 'pending_setup'
                continue
            
            active_schedules = schedules.filtered(lambda s: s.state == 'active')
            completed_schedules = schedules.filtered(lambda s: s.state == 'completed')
            
            if active_schedules:
                move.revenue_recognition_status = 'recognition_active'
            elif completed_schedules and len(completed_schedules) == len(schedules):
                move.revenue_recognition_status = 'fully_recognized'
            else:
                move.revenue_recognition_status = 'schedules_created'
    
    @api.depends('invoice_line_ids.product_id.product_tmpl_id.is_distinct_service')
    def _compute_performance_obligations(self):
        """Compute performance obligations information"""
        for move in self:
            if not move.has_ams_revenue_products:
                move.performance_obligations_count = 0
                move.requires_allocation = False
                continue
            
            # Count distinct performance obligations
            distinct_services = move.invoice_line_ids.filtered(
                lambda l: l.product_id.product_tmpl_id.is_subscription_product and
                         l.product_id.product_tmpl_id.is_distinct_service
            )
            
            move.performance_obligations_count = len(distinct_services)
            
            # Multiple performance obligations require price allocation
            move.requires_allocation = move.performance_obligations_count > 1
    
    @api.depends('revenue_schedule_ids.total_contract_value',
                 'invoice_line_ids.price_subtotal',
                 'revenue_recognition_method')
    def _compute_revenue_amounts(self):
        """Compute revenue amounts"""
        for move in self:
            if not move.has_ams_revenue_products:
                move.total_deferred_amount = 0.0
                move.total_immediate_revenue = 0.0
                continue
            
            # Calculate deferred amount from schedules
            move.total_deferred_amount = sum(move.revenue_schedule_ids.mapped('total_contract_value'))
            
            # Calculate immediate revenue
            ams_lines = move.invoice_line_ids.filtered(
                lambda l: l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.use_ams_accounting
            )
            
            immediate_lines = ams_lines.filtered(
                lambda l: l.product_id.product_tmpl_id.revenue_recognition_method == 'immediate'
            )
            
            move.total_immediate_revenue = sum(immediate_lines.mapped('price_subtotal'))
    
    # Enhanced Methods
    def _post(self, soft=True):
        """Enhanced posting to trigger revenue recognition processing"""
        result = super()._post(soft=soft)
        
        # Process revenue recognition for posted invoices
        for move in self.filtered(lambda m: m.move_type == 'out_invoice' and m.has_ams_revenue_products):
            if not move.revenue_recognition_processed:
                try:
                    move._process_revenue_recognition()
                except Exception as e:
                    _logger.error(f"Revenue recognition processing failed for invoice {move.name}: {str(e)}")
                    move.revenue_recognition_error = str(e)
        
        return result
    
    def _process_revenue_recognition(self):
        """Process revenue recognition for this invoice"""
        self.ensure_one()
        
        if self.move_type != 'out_invoice':
            return
        
        if not self.has_ams_revenue_products:
            return
        
        if self.revenue_recognition_processed:
            return
        
        _logger.info(f"Processing revenue recognition for invoice {self.name}")
        
        # Process each AMS line
        ams_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id.product_tmpl_id.is_subscription_product and 
                     l.product_id.product_tmpl_id.use_ams_accounting
        )
        
        for line in ams_lines:
            self._process_line_revenue_recognition(line)
        
        # Mark as processed
        self.write({
            'revenue_recognition_processed': True,
            'revenue_recognition_processed_date': fields.Datetime.now(),
            'revenue_recognition_error': False,
        })
        
        self.message_post(body="Revenue recognition processing completed.")
    
    def _process_line_revenue_recognition(self, invoice_line):
        """Process revenue recognition for a single invoice line"""
        self.ensure_one()
        
        product = invoice_line.product_id.product_tmpl_id
        
        if not product.auto_create_recognition_schedule:
            return
        
        # Find related subscription
        subscription = self._find_related_subscription(invoice_line)
        
        if not subscription:
            _logger.warning(f"No subscription found for invoice line {invoice_line.id}")
            return
        
        # Create revenue recognition schedule
        if product.revenue_recognition_method == 'immediate':
            self._create_immediate_recognition(invoice_line, subscription)
        else:
            self._create_deferred_recognition_schedule(invoice_line, subscription)
    
    def _find_related_subscription(self, invoice_line):
        """Find the subscription related to this invoice line"""
        # Try to find by invoice line reference
        subscription = self.env['ams.subscription'].search([
            ('invoice_line_id', '=', invoice_line.id)
        ], limit=1)
        
        if subscription:
            return subscription
        
        # Try to find by invoice reference
        subscription = self.env['ams.subscription'].search([
            ('invoice_id', '=', self.id),
            ('product_id', '=', invoice_line.product_id.id)
        ], limit=1)
        
        if subscription:
            return subscription
        
        # Try to find by partner and product
        subscription = self.env['ams.subscription'].search([
            ('partner_id', '=', self.partner_id.id),
            ('product_id', '=', invoice_line.product_id.id),
            ('state', '=', 'active')
        ], limit=1)
        
        return subscription
    
    def _create_immediate_recognition(self, invoice_line, subscription):
        """Create immediate revenue recognition"""
        # For immediate recognition, we just need to ensure proper accounting
        # The revenue is recognized immediately when the invoice is posted
        
        # Create a minimal schedule for tracking
        schedule_vals = {
            'subscription_id': subscription.id,
            'total_contract_value': invoice_line.price_subtotal,
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today(),
            'recognition_method': 'immediate',
            'recognition_frequency': 'daily',
            'state': 'completed',
            'invoice_id': self.id,
            'invoice_line_id': invoice_line.id,
        }
        
        schedule = self.env['ams.revenue.schedule'].create(schedule_vals)
        
        # Create immediate recognition entry
        recognition_vals = {
            'schedule_id': schedule.id,
            'recognition_date': fields.Date.today(),
            'planned_amount': invoice_line.price_subtotal,
            'recognized_amount': invoice_line.price_subtotal,
            'state': 'posted',
            'processed_date': fields.Datetime.now(),
            'processed_by': self.env.user.id,
        }
        
        self.env['ams.revenue.recognition'].create(recognition_vals)
        
        _logger.info(f"Created immediate recognition for invoice line {invoice_line.id}")
    
    def _create_deferred_recognition_schedule(self, invoice_line, subscription):
        """Create deferred revenue recognition schedule"""
        product = invoice_line.product_id.product_tmpl_id
        
        # Use product method to create schedule
        schedule = product.create_recognition_schedule_from_subscription(subscription)
        
        if not schedule:
            raise UserError(f"Failed to create revenue schedule for product {product.name}")
        
        # Link schedule to this invoice
        schedule.write({
            'invoice_id': self.id,
            'invoice_line_id': invoice_line.id,
        })
        
        _logger.info(f"Created deferred recognition schedule {schedule.id} for invoice line {invoice_line.id}")
        
        return schedule
    
    # Action Methods
    def action_view_revenue_schedules(self):
        """Action to view revenue recognition schedules"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Schedules - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
            }
        }
    
    def action_reprocess_revenue_recognition(self):
        """Reprocess revenue recognition for this invoice"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError("Can only reprocess revenue recognition for posted invoices.")
        
        # Cancel existing schedules
        self.revenue_schedule_ids.action_cancel()
        
        # Reset processing flags
        self.write({
            'revenue_recognition_processed': False,
            'revenue_recognition_processed_date': False,
            'revenue_recognition_error': False,
        })
        
        # Reprocess
        self._process_revenue_recognition()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Revenue recognition reprocessed successfully!',
                'type': 'success',
            }
        }
    
    def action_create_missing_schedules(self):
        """Create missing revenue recognition schedules"""
        self.ensure_one()
        
        if not self.has_ams_revenue_products:
            raise UserError("This invoice does not contain AMS revenue products.")
        
        # Find lines without schedules
        ams_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id.product_tmpl_id.is_subscription_product and 
                     l.product_id.product_tmpl_id.use_ams_accounting and
                     l.product_id.product_tmpl_id.revenue_recognition_method != 'immediate'
        )
        
        lines_without_schedules = ams_lines.filtered(
            lambda l: not self.revenue_schedule_ids.filtered(lambda s: s.invoice_line_id == l)
        )
        
        created_count = 0
        for line in lines_without_schedules:
            subscription = self._find_related_subscription(line)
            if subscription:
                self._create_deferred_recognition_schedule(line, subscription)
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Created {created_count} revenue recognition schedules.',
                'type': 'success',
            }
        }
    
    def action_validate_revenue_recognition(self):
        """Validate revenue recognition setup for this invoice"""
        self.ensure_one()
        
        issues = []
        
        if not self.has_ams_revenue_products:
            issues.append("Invoice does not contain AMS revenue products")
        
        if not self.revenue_recognition_processed:
            issues.append("Revenue recognition not yet processed")
        
        if self.revenue_recognition_error:
            issues.append(f"Processing error: {self.revenue_recognition_error}")
        
        # Check for missing schedules
        ams_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id.product_tmpl_id.is_subscription_product and 
                     l.product_id.product_tmpl_id.use_ams_accounting and
                     l.product_id.product_tmpl_id.revenue_recognition_method != 'immediate'
        )
        
        for line in ams_lines:
            schedule = self.revenue_schedule_ids.filtered(lambda s: s.invoice_line_id == line)
            if not schedule:
                issues.append(f"Missing schedule for line: {line.product_id.name}")
        
        if issues:
            message = "Revenue Recognition Issues:\n" + "\n".join(f"• {issue}" for issue in issues)
            message_type = 'warning'
        else:
            message = "Revenue recognition validation passed! All schedules are properly configured."
            message_type = 'success'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Revenue Recognition Validation',
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }
    
    # Reporting Methods
    def get_revenue_recognition_summary(self):
        """Get revenue recognition summary for this invoice"""
        self.ensure_one()
        
        return {
            'invoice_id': self.id,
            'invoice_name': self.name,
            'customer_name': self.partner_id.name,
            'invoice_date': self.invoice_date,
            'invoice_amount': self.amount_total,
            'has_ams_products': self.has_ams_revenue_products,
            'recognition_method': self.revenue_recognition_method,
            'recognition_status': self.revenue_recognition_status,
            'deferred_amount': self.total_deferred_amount,
            'immediate_amount': self.total_immediate_revenue,
            'schedules_count': len(self.revenue_schedule_ids),
            'performance_obligations': self.performance_obligations_count,
            'processed': self.revenue_recognition_processed,
            'error': self.revenue_recognition_error,
        }
    
    @api.model
    def get_revenue_recognition_dashboard_data(self):
        """Get dashboard data for revenue recognition on invoices"""
        # Get invoices with revenue recognition
        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('has_ams_revenue_products', '=', True)
        ])
        
        # Status breakdown
        status_counts = {}
        recognition_statuses = ['pending_setup', 'schedules_created', 'recognition_active', 'fully_recognized', 'error']
        for status in recognition_statuses:
            status_counts[status] = len(invoices.filtered(lambda i: i.revenue_recognition_status == status))
        
        # Method breakdown
        method_counts = {}
        recognition_methods = ['immediate', 'deferred', 'mixed']
        for method in recognition_methods:
            method_counts[method] = len(invoices.filtered(lambda i: i.revenue_recognition_method == method))
        
        return {
            'total_invoices': len(invoices),
            'total_deferred': sum(invoices.mapped('total_deferred_amount')),
            'total_immediate': sum(invoices.mapped('total_immediate_revenue')),
            'processed_count': len(invoices.filtered('revenue_recognition_processed')),
            'error_count': len(invoices.filtered('revenue_recognition_error')),
            'status_breakdown': status_counts,
            'method_breakdown': method_counts,
        }


class AccountMoveLine(models.Model):
    """Enhanced Account Move Line with Revenue Recognition Integration"""
    _inherit = 'account.move.line'

    # Revenue Recognition Fields
    creates_revenue_schedule = fields.Boolean(
        string='Creates Revenue Schedule',
        compute='_compute_revenue_recognition_info',
        store=True,
        help='This line creates a revenue recognition schedule'
    )
    
    revenue_schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        help='Revenue recognition schedule for this line'
    )
    
    revenue_recognition_method = fields.Selection(
        related='product_id.product_tmpl_id.revenue_recognition_method',
        string='Recognition Method',
        store=True,
        help='Revenue recognition method for this product'
    )
    
    deferred_revenue_amount = fields.Float(
        string='Deferred Revenue Amount',
        compute='_compute_revenue_amounts',
        store=True,
        help='Amount deferred for future recognition'
    )
    
    immediate_revenue_amount = fields.Float(
        string='Immediate Revenue Amount', 
        compute='_compute_revenue_amounts',
        store=True,
        help='Amount recognized immediately'
    )
    
    @api.depends('product_id.product_tmpl_id.is_subscription_product',
                 'product_id.product_tmpl_id.use_ams_accounting',
                 'product_id.product_tmpl_id.revenue_recognition_method')
    def _compute_revenue_recognition_info(self):
        """Compute revenue recognition information"""
        for line in self:
            product = line.product_id.product_tmpl_id
            line.creates_revenue_schedule = (
                product.is_subscription_product and 
                product.use_ams_accounting and
                product.auto_create_recognition_schedule and
                product.revenue_recognition_method != 'immediate'
            )
    
    @api.depends('price_subtotal', 'revenue_recognition_method')
    def _compute_revenue_amounts(self):
        """Compute revenue amounts"""
        for line in self:
            if line.revenue_recognition_method == 'immediate':
                line.immediate_revenue_amount = line.price_subtotal
                line.deferred_revenue_amount = 0.0
            elif line.creates_revenue_schedule:
                line.immediate_revenue_amount = 0.0
                line.deferred_revenue_amount = line.price_subtotal
            else:
                line.immediate_revenue_amount = line.price_subtotal
                line.deferred_revenue_amount = 0.0