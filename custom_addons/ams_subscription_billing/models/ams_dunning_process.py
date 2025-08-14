# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSDunningSequence(models.Model):
    """Dunning Sequence Configuration"""
    _name = 'ams.dunning.sequence'
    _description = 'AMS Dunning Sequence'
    _order = 'sequence, id'
    
    name = fields.Char(
        string='Sequence Name',
        required=True,
        translate=True
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of sequences'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    is_default = fields.Boolean(
        string='Is Default',
        help='Default sequence for new subscriptions'
    )
    
    # Applicability Rules
    partner_category_ids = fields.Many2many(
        'res.partner.category',
        string='Customer Categories',
        help='Apply to customers with these categories. Leave empty for all customers.'
    )
    
    product_category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Apply to products in these categories. Leave empty for all products.'
    )
    
    subscription_type_filter = fields.Selection([
        ('all', 'All Subscriptions'),
        ('individual', 'Individual Only'),
        ('enterprise', 'Enterprise Only'),
        ('chapter', 'Chapter Only'),
        ('publication', 'Publication Only'),
    ], string='Subscription Type Filter', default='all')
    
    # Grace Period Configuration
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=7,
        help='Days to wait before starting dunning process'
    )
    
    suspension_after_final = fields.Boolean(
        string='Auto-Suspend After Final Notice',
        default=True,
        help='Automatically suspend subscription after final notice'
    )
    
    suspension_delay_days = fields.Integer(
        string='Suspension Delay (Days)',
        default=3,
        help='Days to wait after final notice before suspension'
    )
    
    # Steps
    step_ids = fields.One2many(
        'ams.dunning.step',
        'dunning_sequence_id',
        string='Dunning Steps'
    )
    
    step_count = fields.Integer(
        string='Number of Steps',
        compute='_compute_step_count'
    )
    
    @api.depends('step_ids')
    def _compute_step_count(self):
        """Compute number of steps"""
        for sequence in self:
            sequence.step_count = len(sequence.step_ids)
    
    @api.constrains('is_default')
    def _check_single_default(self):
        """Ensure only one default sequence"""
        if self.is_default:
            other_defaults = self.search([
                ('is_default', '=', True),
                ('id', '!=', self.id)
            ])
            if other_defaults:
                raise ValidationError(_('Only one dunning sequence can be set as default'))
    
    def get_applicable_sequences(self, subscription):
        """Get applicable dunning sequences for a subscription"""
        domain = [('active', '=', True)]
        
        # Apply filters
        sequences = self.search(domain)
        applicable = self.env['ams.dunning.sequence']
        
        for sequence in sequences:
            if sequence._is_applicable_to_subscription(subscription):
                applicable |= sequence
        
        # Return default if no specific sequence found
        if not applicable:
            applicable = self.search([('is_default', '=', True)], limit=1)
        
        return applicable
    
    def _is_applicable_to_subscription(self, subscription):
        """Check if sequence is applicable to subscription"""
        # Check partner categories
        if self.partner_category_ids:
            if not any(cat in subscription.partner_id.category_id.ids 
                      for cat in self.partner_category_ids.ids):
                return False
        
        # Check product categories
        if self.product_category_ids:
            product_category = subscription.product_id.categ_id
            if product_category.id not in self.product_category_ids.ids:
                return False
        
        # Check subscription type
        if self.subscription_type_filter != 'all':
            if hasattr(subscription.product_id.product_tmpl_id, 'ams_product_type'):
                product_type = subscription.product_id.product_tmpl_id.ams_product_type
                if self.subscription_type_filter != product_type:
                    return False
        
        return True


class AMSDunningStep(models.Model):
    """Individual Dunning Steps"""
    _name = 'ams.dunning.step'
    _description = 'AMS Dunning Step'
    _order = 'sequence, id'
    
    dunning_sequence_id = fields.Many2one(
        'ams.dunning.sequence',
        string='Dunning Sequence',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Step Name',
        required=True,
        translate=True
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    sequence = fields.Integer(
        string='Step Sequence',
        required=True,
        help='Order of this step in the sequence'
    )
    
    # Timing
    days_after_due = fields.Integer(
        string='Days After Due Date',
        required=True,
        help='Number of days after due date to execute this step'
    )
    
    days_after_previous_step = fields.Integer(
        string='Days After Previous Step',
        help='Alternative: days after previous step (0 = use days_after_due)'
    )
    
    # Actions
    action_type = fields.Selection([
        ('email', 'Send Email'),
        ('email_and_sms', 'Send Email and SMS'),
        ('email_and_call', 'Send Email and Schedule Call'),
        ('email_and_suspend', 'Send Email and Suspend'),
        ('suspend_only', 'Suspend Only'),
        ('terminate', 'Terminate Subscription'),
        ('collection_agency', 'Send to Collection Agency'),
        ('custom', 'Custom Action'),
    ], string='Action Type', required=True)
    
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'ams.dunning.process')]"
    )
    
    sms_template_id = fields.Many2one(
        'sms.template',
        string='SMS Template',
        domain="[('model', '=', 'ams.dunning.process')]"
    )
    
    # Escalation Options
    create_activity = fields.Boolean(
        string='Create Activity',
        help='Create a follow-up activity for staff'
    )
    
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type'
    )
    
    activity_user_id = fields.Many2one(
        'res.users',
        string='Assign Activity To'
    )
    
    # Access Control
    restrict_access = fields.Boolean(
        string='Restrict Access',
        help='Restrict customer access to services'
    )
    
    access_level = fields.Selection([
        ('full', 'Full Access'),
        ('limited', 'Limited Access'),
        ('view_only', 'View Only'),
        ('no_access', 'No Access'),
    ], string='Access Level', default='full')
    
    # Validation
    require_manual_approval = fields.Boolean(
        string='Require Manual Approval',
        help='Require manual approval before executing this step'
    )
    
    is_final_step = fields.Boolean(
        string='Is Final Step',
        help='Mark this as the final step in the sequence'
    )


class AMSDunningProcess(models.Model):
    """Active Dunning Process for a specific payment failure"""
    _name = 'ams.dunning.process'
    _description = 'AMS Dunning Process'
    _order = 'failure_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Process Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.dunning.process') or 'New'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Related Records
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    payment_failure_id = fields.Many2one(
        'ams.payment.failure',
        string='Payment Failure',
        ondelete='set null',
        help='Original payment failure that triggered this process'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Failed Invoice',
        ondelete='cascade',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    dunning_sequence_id = fields.Many2one(
        'ams.dunning.sequence',
        string='Dunning Sequence',
        required=True,
        tracking=True
    )
    
    # Failure Information
    failure_date = fields.Date(
        string='Failure Date',
        required=True,
        index=True,
        tracking=True
    )
    
    failure_reason = fields.Selection([
        ('payment_failed', 'Payment Failed'),
        ('insufficient_funds', 'Insufficient Funds'),
        ('card_declined', 'Card Declined'),
        ('payment_overdue', 'Payment Overdue'),
        ('auto_payment_failed', 'Auto Payment Failed'),
        ('manual_trigger', 'Manual Trigger'),
    ], string='Failure Reason', required=True)
    
    failed_amount = fields.Monetary(
        string='Failed Amount',
        currency_field='currency_id',
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Process Status
    state = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('escalated', 'Escalated'),
    ], string='Status', default='active', required=True, tracking=True)
    
    current_step = fields.Integer(
        string='Current Step',
        default=1,
        tracking=True
    )
    
    next_action_date = fields.Date(
        string='Next Action Date',
        index=True,
        tracking=True
    )
    
    last_action_date = fields.Date(
        string='Last Action Date',
        readonly=True
    )
    
    # Grace Period
    grace_end_date = fields.Date(
        string='Grace Period End',
        compute='_compute_grace_end_date',
        store=True
    )
    
    in_grace_period = fields.Boolean(
        string='In Grace Period',
        compute='_compute_grace_status',
        store=True
    )
    
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_days_overdue',
        store=True
    )
    
    # Suspension Information
    suspension_date = fields.Date(
        string='Planned Suspension Date',
        compute='_compute_suspension_date',
        store=True
    )
    
    is_suspended = fields.Boolean(
        string='Is Suspended',
        related='subscription_id.is_suspended',
        readonly=True
    )
    
    # Communication Tracking
    emails_sent = fields.Integer(
        string='Emails Sent',
        default=0,
        readonly=True
    )
    
    sms_sent = fields.Integer(
        string='SMS Sent',
        default=0,
        readonly=True
    )
    
    last_communication_date = fields.Datetime(
        string='Last Communication',
        readonly=True
    )
    
    # Customer Response
    customer_contacted = fields.Boolean(
        string='Customer Contacted Us',
        default=False,
        tracking=True
    )
    
    customer_response_date = fields.Datetime(
        string='Customer Response Date'
    )
    
    customer_response_notes = fields.Text(
        string='Customer Response Notes'
    )
    
    payment_plan_offered = fields.Boolean(
        string='Payment Plan Offered',
        default=False
    )
    
    # Related Records
    dunning_action_ids = fields.One2many(
        'ams.dunning.action',
        'dunning_process_id',
        string='Dunning Actions'
    )
    
    # Computed Fields
    @api.depends('subscription_id', 'partner_id', 'failure_date')
    def _compute_display_name(self):
        """Compute display name"""
        for process in self:
            if process.partner_id and process.subscription_id:
                process.display_name = f"{process.partner_id.name} - {process.subscription_id.name} ({process.failure_date})"
            else:
                process.display_name = process.name or 'New Dunning Process'
    
    @api.depends('failure_date', 'dunning_sequence_id.grace_period_days')
    def _compute_grace_end_date(self):
        """Compute grace period end date"""
        for process in self:
            if process.failure_date and process.dunning_sequence_id:
                grace_days = process.dunning_sequence_id.grace_period_days or 0
                process.grace_end_date = process.failure_date + timedelta(days=grace_days)
            else:
                process.grace_end_date = False
    
    @api.depends('grace_end_date')
    def _compute_grace_status(self):
        """Compute if still in grace period"""
        today = fields.Date.today()
        for process in self:
            process.in_grace_period = (
                process.grace_end_date and 
                today <= process.grace_end_date and
                process.state == 'active'
            )
    
    @api.depends('failure_date')
    def _compute_days_overdue(self):
        """Compute days overdue"""
        today = fields.Date.today()
        for process in self:
            if process.failure_date:
                process.days_overdue = (today - process.failure_date).days
            else:
                process.days_overdue = 0
    
    @api.depends('dunning_sequence_id', 'failure_date')
    def _compute_suspension_date(self):
        """Compute planned suspension date"""
        for process in self:
            if process.dunning_sequence_id and process.failure_date:
                sequence = process.dunning_sequence_id
                if sequence.suspension_after_final:
                    # Find final step
                    final_step = sequence.step_ids.filtered('is_final_step')
                    if not final_step:
                        final_step = sequence.step_ids.sorted('sequence', reverse=True)[:1]
                    
                    if final_step:
                        final_step_date = process.failure_date + timedelta(days=final_step.days_after_due)
                        process.suspension_date = final_step_date + timedelta(days=sequence.suspension_delay_days)
                    else:
                        process.suspension_date = False
                else:
                    process.suspension_date = False
            else:
                process.suspension_date = False
    
    # Actions
    def action_process_next_step(self):
        """Process the next dunning step"""
        for process in self:
            if process.state != 'active':
                raise UserError(_('Only active processes can be advanced'))
            
            process._execute_current_step()
    
    def action_pause(self):
        """Pause the dunning process"""
        for process in self:
            if process.state != 'active':
                raise UserError(_('Only active processes can be paused'))
            
            process.state = 'paused'
            process.message_post(body=_('Dunning process paused'))
    
    def action_resume(self):
        """Resume the dunning process"""
        for process in self:
            if process.state != 'paused':
                raise UserError(_('Only paused processes can be resumed'))
            
            process.state = 'active'
            process._schedule_next_action()
            process.message_post(body=_('Dunning process resumed'))
    
    def action_cancel(self):
        """Cancel the dunning process"""
        for process in self:
            if process.state in ['completed', 'cancelled']:
                raise UserError(_('Process is already completed or cancelled'))
            
            process.state = 'cancelled'
            process.message_post(body=_('Dunning process cancelled'))
    
    def action_complete(self):
        """Mark process as completed"""
        for process in self:
            if process.state != 'active':
                raise UserError(_('Only active processes can be completed'))
            
            process.state = 'completed'
            process.message_post(body=_('Dunning process completed'))
    
    def action_escalate(self):
        """Escalate to manual handling"""
        for process in self:
            process.state = 'escalated'
            process.message_post(body=_('Dunning process escalated for manual handling'))
    
    def action_customer_responded(self):
        """Mark that customer has responded"""
        for process in self:
            process.customer_contacted = True
            process.customer_response_date = fields.Datetime.now()
            process.message_post(body=_('Customer response recorded'))
    
    # Core Processing Logic
    def _execute_current_step(self):
        """Execute the current dunning step"""
        self.ensure_one()
        
        # Get current step configuration
        step = self._get_current_step_config()
        if not step:
            self.action_complete()
            return
        
        _logger.info(f'Executing dunning step {self.current_step} for process {self.name}')
        
        try:
            # Create action record
            action = self._create_dunning_action(step)
            
            # Execute step actions
            result = self._execute_step_actions(step, action)
            
            # Update action with results
            action.write({
                'executed': True,
                'execution_date': fields.Datetime.now(),
                'success': result.get('success', False),
                'error_message': result.get('error'),
            })
            
            # Update process status
            if result.get('success'):
                self._handle_step_success(step)
            else:
                self._handle_step_failure(step, result.get('error'))
            
        except Exception as e:
            self._handle_step_exception(str(e))
            _logger.error(f'Exception executing dunning step for process {self.name}: {str(e)}')
    
    def _get_current_step_config(self):
        """Get configuration for current step"""
        steps = self.dunning_sequence_id.step_ids.sorted('sequence')
        if self.current_step <= len(steps):
            return steps[self.current_step - 1]
        return False
    
    def _create_dunning_action(self, step):
        """Create dunning action record"""
        return self.env['ams.dunning.action'].create({
            'dunning_process_id': self.id,
            'step_sequence': self.current_step,
            'step_name': step.name,
            'action_type': step.action_type,
            'scheduled_date': self.next_action_date,
            'amount': self.failed_amount,
        })
    
    def _execute_step_actions(self, step, action):
        """Execute the actions for a dunning step"""
        result = {'success': True, 'actions': []}
        
        try:
            # Send email if required
            if step.action_type in ['email', 'email_and_sms', 'email_and_call', 'email_and_suspend']:
                email_result = self._send_dunning_email(step)
                result['actions'].append(email_result)
                if email_result.get('success'):
                    self.emails_sent += 1
                    self.last_communication_date = fields.Datetime.now()
            
            # Send SMS if required
            if step.action_type in ['email_and_sms']:
                sms_result = self._send_dunning_sms(step)
                result['actions'].append(sms_result)
                if sms_result.get('success'):
                    self.sms_sent += 1
            
            # Create activity if required
            if step.create_activity:
                activity_result = self._create_follow_up_activity(step)
                result['actions'].append(activity_result)
            
            # Handle suspension
            if step.action_type in ['email_and_suspend', 'suspend_only']:
                suspend_result = self._suspend_subscription(step)
                result['actions'].append(suspend_result)
            
            # Handle termination
            if step.action_type == 'terminate':
                terminate_result = self._terminate_subscription(step)
                result['actions'].append(terminate_result)
            
            # Handle access restriction
            if step.restrict_access:
                access_result = self._restrict_access(step)
                result['actions'].append(access_result)
            
            # Check if any action failed
            if any(not action.get('success', True) for action in result['actions']):
                result['success'] = False
                result['error'] = 'One or more actions failed'
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _send_dunning_email(self, step):
        """Send dunning email"""
        try:
            if not step.email_template_id:
                return {'success': False, 'error': 'No email template configured'}
            
            # Send email using template
            step.email_template_id.send_mail(self.id, force_send=True)
            
            return {'success': True, 'action': 'email_sent'}
            
        except Exception as e:
            _logger.error(f'Error sending dunning email for process {self.name}: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _send_dunning_sms(self, step):
        """Send dunning SMS"""
        try:
            if not step.sms_template_id:
                return {'success': False, 'error': 'No SMS template configured'}
            
            # Send SMS using template (if SMS module is available)
            if hasattr(step.sms_template_id, 'send_sms'):
                step.sms_template_id.send_sms(self.id)
                return {'success': True, 'action': 'sms_sent'}
            else:
                return {'success': False, 'error': 'SMS functionality not available'}
            
        except Exception as e:
            _logger.error(f'Error sending dunning SMS for process {self.name}: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _create_follow_up_activity(self, step):
        """Create follow-up activity"""
        try:
            activity_type = step.activity_type_id or self.env.ref('mail.mail_activity_data_call', False)
            user = step.activity_user_id or self.env.user
            
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                summary=f'Follow up on dunning: {step.name}',
                note=f'Follow up with {self.partner_id.name} regarding overdue payment of {self.failed_amount}'
            )
            
            return {'success': True, 'action': 'activity_created'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _suspend_subscription(self, step):
        """Suspend the subscription"""
        try:
            if hasattr(self.subscription_id, 'action_suspend'):
                self.subscription_id.action_suspend()
                return {'success': True, 'action': 'subscription_suspended'}
            else:
                return {'success': False, 'error': 'Suspension not supported'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _terminate_subscription(self, step):
        """Terminate the subscription"""
        try:
            if hasattr(self.subscription_id, 'action_terminate'):
                self.subscription_id.action_terminate()
                return {'success': True, 'action': 'subscription_terminated'}
            else:
                return {'success': False, 'error': 'Termination not supported'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _restrict_access(self, step):
        """Restrict customer access"""
        try:
            # This would integrate with access control systems
            # For now, just log the action
            _logger.info(f'Access restricted to {step.access_level} for subscription {self.subscription_id.name}')
            return {'success': True, 'action': 'access_restricted'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_step_success(self, step):
        """Handle successful step execution"""
        self.last_action_date = fields.Date.today()
        
        # Move to next step or complete
        if step.is_final_step or self.current_step >= len(self.dunning_sequence_id.step_ids):
            # Final step completed
            if self.dunning_sequence_id.suspension_after_final and not self.is_suspended:
                # Schedule suspension
                self._schedule_final_suspension()
            else:
                self.action_complete()
        else:
            # Move to next step
            self.current_step += 1
            self._schedule_next_action()
        
        self.message_post(body=_('Dunning step %s executed successfully') % step.name)
    
    def _handle_step_failure(self, step, error):
        """Handle failed step execution"""
        self.message_post(body=_('Dunning step %s failed: %s') % (step.name, error))
        
        # Optionally retry or escalate
        if step.require_manual_approval:
            self.action_escalate()
    
    def _handle_step_exception(self, error):
        """Handle exception during step execution"""
        self.message_post(body=_('Dunning step encountered exception: %s') % error)
        self.action_escalate()
    
    def _schedule_next_action(self):
        """Schedule the next dunning action"""
        step = self._get_current_step_config()
        if step:
            if step.days_after_previous_step > 0:
                # Schedule based on previous step
                self.next_action_date = self.last_action_date + timedelta(days=step.days_after_previous_step)
            else:
                # Schedule based on failure date
                self.next_action_date = self.failure_date + timedelta(days=step.days_after_due)
    
    def _schedule_final_suspension(self):
        """Schedule final suspension after delay"""
        delay_days = self.dunning_sequence_id.suspension_delay_days or 0
        suspension_date = fields.Date.today() + timedelta(days=delay_days)
        
        # Create scheduled action for suspension
        # This could be implemented as a scheduled activity or cron job
        self.message_post(body=_('Subscription suspension scheduled for %s') % suspension_date)
    
    # Utility Methods
    def get_payment_url(self):
        """Get URL for customer to make payment"""
        # This would generate a payment portal URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/invoices/{self.invoice_id.id}" if self.invoice_id else ""
    
    # Batch Processing
    @api.model
    def cron_process_dunning(self):
        """Cron job to process due dunning actions"""
        today = fields.Date.today()
        
        # Find processes that need action
        due_processes = self.search([
            ('state', '=', 'active'),
            ('next_action_date', '<=', today),
        ])
        
        _logger.info(f'Found {len(due_processes)} dunning processes due for action')
        
        processed_count = 0
        error_count = 0
        
        for process in due_processes:
            try:
                process.action_process_next_step()
                processed_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f'Error processing dunning for {process.name}: {str(e)}')
        
        _logger.info(f'Dunning processing completed: {processed_count} processed, {error_count} errors')
        
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'total_due': len(due_processes),
        }


class AMSDunningAction(models.Model):
    """Individual Dunning Action Execution Records"""
    _name = 'ams.dunning.action'
    _description = 'AMS Dunning Action'
    _order = 'scheduled_date desc, id desc'
    
    dunning_process_id = fields.Many2one(
        'ams.dunning.process',
        string='Dunning Process',
        required=True,
        ondelete='cascade'
    )
    
    step_sequence = fields.Integer(
        string='Step Sequence',
        required=True
    )
    
    step_name = fields.Char(
        string='Step Name',
        required=True
    )
    
    action_type = fields.Selection([
        ('email', 'Send Email'),
        ('email_and_sms', 'Send Email and SMS'),
        ('email_and_call', 'Send Email and Schedule Call'),
        ('email_and_suspend', 'Send Email and Suspend'),
        ('suspend_only', 'Suspend Only'),
        ('terminate', 'Terminate Subscription'),
        ('collection_agency', 'Send to Collection Agency'),
        ('custom', 'Custom Action'),
    ], string='Action Type', required=True)
    
    scheduled_date = fields.Date(
        string='Scheduled Date',
        required=True
    )
    
    executed = fields.Boolean(
        string='Executed',
        default=False
    )
    
    execution_date = fields.Datetime(
        string='Execution Date'
    )
    
    success = fields.Boolean(
        string='Success',
        default=False
    )
    
    error_message = fields.Text(
        string='Error Message'
    )
    
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='dunning_process_id.currency_id',
        store=True,
        readonly=True
    )
    
    notes = fields.Text(
        string='Notes'
    )