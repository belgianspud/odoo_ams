# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    """Enhanced AMS Subscription with Revenue Recognition Integration"""
    _inherit = 'ams.subscription'

    # Revenue Recognition Fields
    revenue_schedule_ids = fields.One2many(
        'ams.revenue.schedule',
        'subscription_id',
        string='Revenue Schedules',
        help='Revenue recognition schedules for this subscription'
    )
    
    active_revenue_schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Active Revenue Schedule',
        compute='_compute_active_revenue_schedule',
        store=True,
        help='Currently active revenue recognition schedule'
    )
    
    # Revenue Recognition Status
    revenue_recognition_status = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending', 'Pending Setup'),
        ('active', 'Active Recognition'),
        ('paused', 'Recognition Paused'),
        ('completed', 'Recognition Completed'),
        ('error', 'Recognition Error'),
    ], string='Revenue Recognition Status', 
       compute='_compute_revenue_recognition_status', 
       store=True,
       help='Current status of revenue recognition for this subscription')
    
    # Revenue Amounts
    total_contract_value = fields.Float(
        string='Total Contract Value',
        compute='_compute_revenue_amounts',
        store=True,
        help='Total value of this subscription contract'
    )
    
    recognized_revenue_amount = fields.Float(
        string='Recognized Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Total revenue recognized to date'
    )
    
    deferred_revenue_amount = fields.Float(
        string='Deferred Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Revenue deferred for future recognition'
    )
    
    unrecognized_revenue_amount = fields.Float(
        string='Unrecognized Revenue',
        compute='_compute_revenue_amounts',
        store=True,
        help='Revenue not yet recognized'
    )
    
    # Recognition Progress
    revenue_recognition_progress = fields.Float(
        string='Recognition Progress (%)',
        compute='_compute_revenue_recognition_progress',
        store=True,
        help='Percentage of revenue recognized'
    )
    
    next_recognition_date = fields.Date(
        string='Next Recognition Date',
        compute='_compute_next_recognition_info',
        store=True,
        help='Date of next scheduled revenue recognition'
    )
    
    next_recognition_amount = fields.Float(
        string='Next Recognition Amount',
        compute='_compute_next_recognition_info',
        store=True,
        help='Amount to be recognized on next recognition date'
    )
    
    # Revenue Recognition Configuration
    auto_revenue_recognition = fields.Boolean(
        string='Auto Revenue Recognition',
        default=True,
        help='Automatically process revenue recognition for this subscription'
    )
    
    revenue_recognition_notes = fields.Text(
        string='Revenue Recognition Notes',
        help='Notes about revenue recognition for this subscription'
    )
    
    # Last Recognition Information
    last_recognition_date = fields.Date(
        string='Last Recognition Date',
        compute='_compute_last_recognition_info',
        store=True,
        help='Date of most recent revenue recognition'
    )
    
    last_recognition_amount = fields.Float(
        string='Last Recognition Amount',
        compute='_compute_last_recognition_info',
        store=True,
        help='Amount of most recent revenue recognition'
    )
    
    # Contract Modification Tracking
    contract_modification_ids = fields.One2many(
        'ams.contract.modification',
        'subscription_id',
        string='Contract Modifications',
        help='Contract modifications affecting revenue recognition'
    )
    
    has_pending_modifications = fields.Boolean(
        string='Has Pending Modifications',
        compute='_compute_modification_status',
        store=True,
        help='This subscription has pending contract modifications'
    )
    
    # Computed Fields
    @api.depends('revenue_schedule_ids', 'revenue_schedule_ids.state')
    def _compute_active_revenue_schedule(self):
        """Compute the active revenue schedule"""
        for subscription in self:
            active_schedule = subscription.revenue_schedule_ids.filtered(
                lambda s: s.state == 'active'
            )
            subscription.active_revenue_schedule_id = active_schedule[0] if active_schedule else False
    
    @api.depends('active_revenue_schedule_id', 'active_revenue_schedule_id.state', 'product_id.auto_create_recognition_schedule')
    def _compute_revenue_recognition_status(self):
        """Compute revenue recognition status"""
        for subscription in self:
            product = subscription.product_id.product_tmpl_id
            
            # Check if revenue recognition is applicable
            if not product.is_subscription_product or not product.use_ams_accounting:
                subscription.revenue_recognition_status = 'not_applicable'
                continue
            
            if not product.auto_create_recognition_schedule:
                subscription.revenue_recognition_status = 'not_applicable'
                continue
            
            # Check active schedule
            if not subscription.active_revenue_schedule_id:
                subscription.revenue_recognition_status = 'pending'
            elif subscription.active_revenue_schedule_id.state == 'active':
                subscription.revenue_recognition_status = 'active'
            elif subscription.active_revenue_schedule_id.state == 'paused':
                subscription.revenue_recognition_status = 'paused'
            elif subscription.active_revenue_schedule_id.state == 'completed':
                subscription.revenue_recognition_status = 'completed'
            else:
                subscription.revenue_recognition_status = 'error'
    
    @api.depends('active_revenue_schedule_id.total_contract_value', 
                 'active_revenue_schedule_id.recognized_revenue',
                 'active_revenue_schedule_id.deferred_revenue_balance')
    def _compute_revenue_amounts(self):
        """Compute revenue amounts from active schedule"""
        for subscription in self:
            if subscription.active_revenue_schedule_id:
                schedule = subscription.active_revenue_schedule_id
                subscription.total_contract_value = schedule.total_contract_value
                subscription.recognized_revenue_amount = schedule.recognized_revenue
                subscription.deferred_revenue_amount = schedule.deferred_revenue_balance
                subscription.unrecognized_revenue_amount = schedule.remaining_revenue
            else:
                subscription.total_contract_value = 0.0
                subscription.recognized_revenue_amount = 0.0
                subscription.deferred_revenue_amount = 0.0
                subscription.unrecognized_revenue_amount = 0.0
    
    @api.depends('recognized_revenue_amount', 'total_contract_value')
    def _compute_revenue_recognition_progress(self):
        """Compute revenue recognition progress percentage"""
        for subscription in self:
            if subscription.total_contract_value > 0:
                subscription.revenue_recognition_progress = (
                    subscription.recognized_revenue_amount / subscription.total_contract_value
                ) * 100
            else:
                subscription.revenue_recognition_progress = 0.0
    
    @api.depends('active_revenue_schedule_id.next_recognition_date',
                 'active_revenue_schedule_id.recognition_ids')
    def _compute_next_recognition_info(self):
        """Compute next recognition information"""
        for subscription in self:
            if subscription.active_revenue_schedule_id:
                schedule = subscription.active_revenue_schedule_id
                subscription.next_recognition_date = schedule.next_recognition_date
                
                # Find next recognition amount
                next_recognition = schedule.recognition_ids.filtered(
                    lambda r: r.state == 'draft' and r.recognition_date == schedule.next_recognition_date
                )
                subscription.next_recognition_amount = next_recognition[0].planned_amount if next_recognition else 0.0
            else:
                subscription.next_recognition_date = False
                subscription.next_recognition_amount = 0.0
    
    @api.depends('active_revenue_schedule_id.recognition_ids')
    def _compute_last_recognition_info(self):
        """Compute last recognition information"""
        for subscription in self:
            if subscription.active_revenue_schedule_id:
                last_recognition = subscription.active_revenue_schedule_id.recognition_ids.filtered(
                    lambda r: r.state == 'posted'
                ).sorted('recognition_date', reverse=True)
                
                if last_recognition:
                    subscription.last_recognition_date = last_recognition[0].recognition_date
                    subscription.last_recognition_amount = last_recognition[0].recognized_amount
                else:
                    subscription.last_recognition_date = False
                    subscription.last_recognition_amount = 0.0
            else:
                subscription.last_recognition_date = False
                subscription.last_recognition_amount = 0.0
    
    @api.depends('contract_modification_ids.state')
    def _compute_modification_status(self):
        """Compute contract modification status"""
        for subscription in self:
            pending_mods = subscription.contract_modification_ids.filtered(
                lambda m: m.state in ['draft', 'validated']
            )
            subscription.has_pending_modifications = bool(pending_mods)
    
    # Enhanced Methods
    def write(self, vals):
        """Enhanced write method to handle revenue recognition updates"""
        result = super().write(vals)
        
        # Handle subscription state changes that affect revenue recognition
        if 'state' in vals:
            for subscription in self:
                subscription._handle_subscription_state_change(vals['state'])
        
        # Handle paid_through_date changes
        if 'paid_through_date' in vals:
            for subscription in self:
                subscription._handle_paid_through_date_change()
        
        return result
    
    def action_activate(self):
        """Override to create revenue recognition schedule when activating"""
        result = super().action_activate()
        
        for subscription in self:
            if subscription._should_create_revenue_schedule():
                try:
                    subscription._create_revenue_recognition_schedule()
                except Exception as e:
                    _logger.error(f"Failed to create revenue schedule for subscription {subscription.id}: {str(e)}")
                    # Don't fail activation, but log the error
        
        return result
    
    def _handle_subscription_state_change(self, new_state):
        """Handle revenue recognition when subscription state changes"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            return
        
        if new_state == 'paused':
            # Pause revenue recognition
            if self.active_revenue_schedule_id.state == 'active':
                self.active_revenue_schedule_id.action_pause()
                
        elif new_state == 'active':
            # Resume revenue recognition
            if self.active_revenue_schedule_id.state == 'paused':
                self.active_revenue_schedule_id.action_resume()
                
        elif new_state in ['suspended', 'terminated']:
            # Handle early termination
            self._handle_early_termination(new_state)
    
    def _handle_paid_through_date_change(self):
        """Handle revenue recognition when paid through date changes"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            return
        
        # If paid through date is extended, we may need to extend the schedule
        schedule = self.active_revenue_schedule_id
        if self.paid_through_date and self.paid_through_date > schedule.end_date:
            self._extend_revenue_schedule(self.paid_through_date)
    
    def _handle_early_termination(self, termination_type):
        """Handle revenue recognition for early termination"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            return
        
        # Create contract modification for termination
        modification_vals = {
            'schedule_id': self.active_revenue_schedule_id.id,
            'modification_type': 'termination' if termination_type == 'terminated' else 'cancellation',
            'modification_date': fields.Date.today(),
            'reason': f'Subscription {termination_type} - early termination',
            'original_contract_value': self.active_revenue_schedule_id.total_contract_value,
            'new_contract_value': 0.0,
        }
        
        modification = self.env['ams.contract.modification'].create(modification_vals)
        modification.action_validate()
        modification.action_process()
    
    def _should_create_revenue_schedule(self):
        """Check if revenue recognition schedule should be created"""
        self.ensure_one()
        
        product = self.product_id.product_tmpl_id
        
        # Check if product supports revenue recognition
        if not product.is_subscription_product or not product.use_ams_accounting:
            return False
        
        if not product.auto_create_recognition_schedule:
            return False
        
        # Check if schedule already exists
        if self.revenue_schedule_ids.filtered(lambda s: s.state != 'cancelled'):
            return False
        
        return True
    
    def _create_revenue_recognition_schedule(self):
        """Create revenue recognition schedule for this subscription"""
        self.ensure_one()
        
        product = self.product_id.product_tmpl_id
        
        if not self._should_create_revenue_schedule():
            return False
        
        # Use product method to create schedule
        schedule = product.create_recognition_schedule_from_subscription(self)
        
        if schedule:
            self.message_post(
                body=f"Revenue recognition schedule created: {schedule.name}"
            )
            _logger.info(f"Created revenue schedule {schedule.id} for subscription {self.id}")
        
        return schedule
    
    def _extend_revenue_schedule(self, new_end_date):
        """Extend revenue recognition schedule to new end date"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            return
        
        schedule = self.active_revenue_schedule_id
        
        # Create contract modification for extension
        modification_vals = {
            'schedule_id': schedule.id,
            'modification_type': 'extension',
            'modification_date': fields.Date.today(),
            'reason': 'Subscription period extended - paid through date updated',
            'original_end_date': schedule.end_date,
            'new_end_date': new_end_date,
            'original_contract_value': schedule.total_contract_value,
            'new_contract_value': schedule.total_contract_value,  # Same value, just extended
        }
        
        modification = self.env['ams.contract.modification'].create(modification_vals)
        modification.action_validate()
        modification.action_process()
    
    # Action Methods
    def action_create_revenue_schedule(self):
        """Manual action to create revenue recognition schedule"""
        for subscription in self:
            if subscription._should_create_revenue_schedule():
                subscription._create_revenue_recognition_schedule()
            else:
                raise UserError(
                    f"Cannot create revenue schedule for subscription {subscription.name}. "
                    f"Check product configuration and existing schedules."
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Revenue recognition schedule created successfully!',
                'type': 'success',
            }
        }
    
    def action_view_revenue_schedules(self):
        """Action to view revenue recognition schedules"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Schedules - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
            }
        }
    
    def action_view_revenue_recognitions(self):
        """Action to view revenue recognition entries"""
        self.ensure_one()
        
        return {
            'name': f'Revenue Recognitions - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.recognition',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
                'group_by': 'recognition_date:month',
            }
        }
    
    def action_pause_revenue_recognition(self):
        """Pause revenue recognition for this subscription"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            raise UserError("No active revenue schedule found.")
        
        if self.active_revenue_schedule_id.state != 'active':
            raise UserError("Revenue schedule is not active.")
        
        self.active_revenue_schedule_id.action_pause()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Revenue recognition paused.',
                'type': 'success',
            }
        }
    
    def action_resume_revenue_recognition(self):
        """Resume revenue recognition for this subscription"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            raise UserError("No active revenue schedule found.")
        
        if self.active_revenue_schedule_id.state != 'paused':
            raise UserError("Revenue schedule is not paused.")
        
        self.active_revenue_schedule_id.action_resume()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Revenue recognition resumed.',
                'type': 'success',
            }
        }
    
    def action_create_contract_modification(self):
        """Create contract modification wizard"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            raise UserError("No active revenue schedule found.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Contract Modification',
            'res_model': 'ams.subscription.modification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_schedule_id': self.active_revenue_schedule_id.id,
            }
        }
    
    # Override existing modification methods to handle revenue recognition
    def action_modify_subscription(self, new_tier_id, modification_type):
        """Override to handle revenue recognition in modifications"""
        # Call parent method first
        modification = super().action_modify_subscription(new_tier_id, modification_type)
        
        # Handle revenue recognition impact
        if self.active_revenue_schedule_id and modification:
            self._create_revenue_modification_from_subscription_change(modification, new_tier_id, modification_type)
        
        return modification
    
    def _create_revenue_modification_from_subscription_change(self, subscription_modification, new_tier_id, modification_type):
        """Create revenue contract modification from subscription change"""
        self.ensure_one()
        
        if not self.active_revenue_schedule_id:
            return
        
        # Get new tier
        new_tier = self.env['ams.subscription.tier'].browse(new_tier_id)
        
        # Calculate new contract value (simplified - in practice might be more complex)
        new_contract_value = self.product_id.list_price  # This could be enhanced
        
        # Create revenue contract modification
        modification_vals = {
            'schedule_id': self.active_revenue_schedule_id.id,
            'modification_type': modification_type,
            'modification_date': fields.Date.today(),
            'reason': f'Subscription tier change: {subscription_modification.reason if subscription_modification else "Tier change"}',
            'original_contract_value': self.active_revenue_schedule_id.total_contract_value,
            'new_contract_value': new_contract_value,
        }
        
        revenue_modification = self.env['ams.contract.modification'].create(modification_vals)
        revenue_modification.action_validate()
        revenue_modification.action_process()
        
        return revenue_modification
    
    # Reporting Methods
    def get_revenue_recognition_summary(self):
        """Get revenue recognition summary for this subscription"""
        self.ensure_one()
        
        return {
            'subscription_id': self.id,
            'subscription_name': self.name,
            'customer_name': self.partner_id.name,
            'total_contract_value': self.total_contract_value,
            'recognized_amount': self.recognized_revenue_amount,
            'deferred_amount': self.deferred_revenue_amount,
            'unrecognized_amount': self.unrecognized_revenue_amount,
            'recognition_progress': self.revenue_recognition_progress,
            'next_recognition_date': self.next_recognition_date,
            'next_recognition_amount': self.next_recognition_amount,
            'status': self.revenue_recognition_status,
            'schedule_count': len(self.revenue_schedule_ids),
            'modification_count': len(self.contract_modification_ids),
        }
    
    @api.model
    def get_revenue_recognition_dashboard_data(self):
        """Get dashboard data for revenue recognition"""
        # Get all subscriptions with revenue recognition
        subscriptions = self.search([
            ('revenue_recognition_status', '!=', 'not_applicable')
        ])
        
        # Calculate totals
        total_contract_value = sum(subscriptions.mapped('total_contract_value'))
        total_recognized = sum(subscriptions.mapped('recognized_revenue_amount'))
        total_deferred = sum(subscriptions.mapped('deferred_revenue_amount'))
        
        # Status breakdown
        status_counts = {}
        for status in ['pending', 'active', 'paused', 'completed', 'error']:
            status_counts[status] = len(subscriptions.filtered(lambda s: s.revenue_recognition_status == status))
        
        return {
            'total_subscriptions': len(subscriptions),
            'total_contract_value': total_contract_value,
            'total_recognized': total_recognized,
            'total_deferred': total_deferred,
            'recognition_progress': (total_recognized / total_contract_value * 100) if total_contract_value > 0 else 0,
            'status_breakdown': status_counts,
        }