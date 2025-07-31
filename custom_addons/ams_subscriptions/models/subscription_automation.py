from odoo import models, fields, api, _
from datetime import date
import logging


class AMSSubscriptionAutomation(models.Model):
    """Automated subscription workflows"""
    _name = 'ams.subscription.automation'
    _description = 'Subscription Automation'
    _order = 'sequence, name'

    name = fields.Char(string='Automation Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Trigger Conditions
    trigger_type = fields.Selection([
        ('subscription_created', 'Subscription Created'),
        ('subscription_activated', 'Subscription Activated'),
        ('subscription_renewed', 'Subscription Renewed'),
        ('subscription_expired', 'Subscription Expired'),
        ('payment_failed', 'Payment Failed'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('scheduled', 'Scheduled/Cron')
    ], string='Trigger Type', required=True)
    
    # Conditions
    membership_type_ids = fields.Many2many(
        'ams.membership.type',
        string='Apply to Membership Types',
        help="Leave empty to apply to all types"
    )
    
    chapter_ids = fields.Many2many(
        'ams.chapter',
        string='Apply to Chapters',
        help="Leave empty to apply to all chapters"
    )
    
    # Actions
    action_type = fields.Selection([
        ('send_email', 'Send Email'),
        ('create_task', 'Create Task'),
        ('update_subscription', 'Update Subscription'),
        ('create_invoice', 'Create Invoice'),
        ('webhook', 'Webhook Call'),
        ('python_code', 'Execute Python Code')
    ], string='Action Type', required=True)
    
    # Email Action
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'ams.member.subscription')]
    )
    
    # Task Action
    task_summary = fields.Char(string='Task Summary')
    task_description = fields.Text(string='Task Description')
    task_user_id = fields.Many2one('res.users', string='Assign To')
    
    # Update Action
    update_field = fields.Char(string='Field to Update')
    update_value = fields.Char(string='New Value')
    
    # Webhook Action
    webhook_url = fields.Char(string='Webhook URL')
    webhook_method = fields.Selection([
        ('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT')
    ], default='POST')
    
    # Python Code Action
    python_code = fields.Text(string='Python Code')
    
    # Scheduling (for cron triggers)
    schedule_interval = fields.Integer(string='Interval (minutes)', default=60)
    
    # Statistics
    execution_count = fields.Integer(string='Execution Count', default=0)
    last_execution = fields.Datetime(string='Last Execution')

    def execute_automation(self, subscription):
        """Execute this automation for a subscription"""
        self.ensure_one()
        
        # Check conditions
        if not self._check_conditions(subscription):
            return False
        
        try:
            if self.action_type == 'send_email' and self.email_template_id:
                self.email_template_id.send_mail(subscription.id, force_send=True)
            
            elif self.action_type == 'create_task':
                self.env['project.task'].create({
                    'name': self.task_summary or f"Task for {subscription.display_name}",
                    'description': self.task_description,
                    'user_ids': [(6, 0, [self.task_user_id.id])] if self.task_user_id else [],
                    'partner_id': subscription.partner_id.id,
                })
            
            elif self.action_type == 'update_subscription' and self.update_field:
                if hasattr(subscription, self.update_field):
                    setattr(subscription, self.update_field, self.update_value)
            
            elif self.action_type == 'create_invoice':
                subscription.action_generate_recurring_invoice()
            
            elif self.action_type == 'python_code' and self.python_code:
                # Execute Python code with subscription in context
                exec_globals = {
                    'subscription': subscription,
                    'env': self.env,
                    'datetime': datetime,
                    'fields': fields,
                }
                exec(self.python_code, exec_globals)
            
            # Update execution statistics
            self.sudo().write({
                'execution_count': self.execution_count + 1,
                'last_execution': fields.Datetime.now()
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Automation {self.name} failed for subscription {subscription.id}: {e}")
            return False

    def _check_conditions(self, subscription):
        """Check if conditions are met for execution"""
        # Check membership type filter
        if self.membership_type_ids and subscription.membership_type_id not in self.membership_type_ids:
            return False
        
        # Check chapter filter
        if self.chapter_ids and subscription.chapter_id not in self.chapter_ids:
            return False
        
        return True

    @api.model
    def trigger_automation(self, trigger_type, subscription):
        """Trigger automations based on subscription events"""
        automations = self.search([
            ('trigger_type', '=', trigger_type),
            ('active', '=', True)
        ])
        
        for automation in automations:
            automation.execute_automation(subscription)
