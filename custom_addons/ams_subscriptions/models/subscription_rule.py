from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionRule(models.Model):
    _name = 'ams.subscription.rule'
    _description = 'AMS Subscription Lifecycle Rules'
    _order = 'subscription_type_id, sequence, name'
    
    name = fields.Char('Rule Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    
    # Rule Configuration
    subscription_type_id = fields.Many2one(
        'ams.subscription.type', 
        'Subscription Type', 
        required=True,
        help="Type of subscription this rule applies to"
    )
    
    rule_type = fields.Selection([
        ('grace_period', 'Grace Period'),
        ('suspend_period', 'Suspension'),
        ('terminate_period', 'Termination'),
        ('renewal_reminder', 'Renewal Reminder'),
        ('custom', 'Custom Rule')
    ], string='Rule Type', required=True)
    
    trigger_days = fields.Integer(
        'Trigger Days', 
        required=True,
        help="Number of days after/before the trigger event"
    )
    
    trigger_event = fields.Selection([
        ('expiry', 'After Expiry'),
        ('before_expiry', 'Before Expiry'),
        ('payment_due', 'Payment Due'),
        ('custom_date', 'Custom Date')
    ], string='Trigger Event', default='expiry')
    
    # Actions
    action = fields.Selection([
        ('status_change', 'Change Status'),
        ('send_email', 'Send Email'),
        ('create_activity', 'Create Activity'),
        ('webhook', 'Send Webhook'),
        ('custom_method', 'Custom Method')
    ], string='Action', required=True)
    
    target_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('terminated', 'Terminated')
    ], string='Target Status', help="Status to change to (for status_change action)")
    
    email_template_id = fields.Many2one(
        'mail.template',
        'Email Template',
        domain="[('model', '=', 'ams.subscription')]",
        help="Email template to send (for send_email action)"
    )
    
    # Execution tracking
    last_executed = fields.Datetime('Last Executed', readonly=True)
    execution_count = fields.Integer('Execution Count', readonly=True, default=0)
    
    # Conditions
    condition_field = fields.Selection([
        ('amount', 'Subscription Amount'),
        ('partner_category', 'Partner Category'),
        ('subscription_duration', 'Subscription Duration'),
        ('payment_method', 'Payment Method')
    ], string='Condition Field')
    
    condition_operator = fields.Selection([
        ('=', 'Equal to'),
        ('!=', 'Not equal to'),
        ('>', 'Greater than'),
        ('<', 'Less than'),
        ('>=', 'Greater than or equal'),
        ('<=', 'Less than or equal'),
        ('in', 'In'),
        ('not in', 'Not in')
    ], string='Condition Operator')
    
    condition_value = fields.Char('Condition Value')
    
    # Description and notes
    description = fields.Text('Description')
    notes = fields.Text('Internal Notes')
    
    @api.model
    def execute_rules(self, subscription_ids=None):
        """Execute applicable rules for given subscriptions or all active subscriptions"""
        if subscription_ids is None:
            # Get all active subscriptions that might need rule processing
            subscriptions = self.env['ams.subscription'].search([
                ('state', 'in', ['active', 'grace', 'suspended'])
            ])
        else:
            subscriptions = self.env['ams.subscription'].browse(subscription_ids)
        
        rules_executed = 0
        today = fields.Date.today()
        
        for rule in self.search([('active', '=', True)]):
            applicable_subscriptions = subscriptions.filtered(
                lambda s: s.subscription_type_id == rule.subscription_type_id
            )
            
            for subscription in applicable_subscriptions:
                if rule._should_execute_for_subscription(subscription, today):
                    try:
                        rule._execute_action(subscription)
                        rules_executed += 1
                        rule.sudo().write({
                            'last_executed': fields.Datetime.now(),
                            'execution_count': rule.execution_count + 1
                        })
                        _logger.info(f"Executed rule {rule.name} for subscription {subscription.name}")
                    except Exception as e:
                        _logger.error(f"Failed to execute rule {rule.name} for subscription {subscription.name}: {str(e)}")
        
        return rules_executed
    
    def _should_execute_for_subscription(self, subscription, today):
        """Check if this rule should be executed for the given subscription"""
        # Check basic conditions
        if not self._check_conditions(subscription):
            return False
        
        # Check trigger timing
        trigger_date = self._calculate_trigger_date(subscription, today)
        if not trigger_date or today < trigger_date:
            return False
        
        # Check if rule was already executed recently (avoid duplicate executions)
        if self.last_executed:
            days_since_last = (fields.Datetime.now() - self.last_executed).days
            if days_since_last < 1:  # Don't execute same rule twice in one day
                return False
        
        return True
    
    def _calculate_trigger_date(self, subscription, today):
        """Calculate when this rule should trigger for the subscription"""
        if self.trigger_event == 'expiry':
            base_date = subscription.end_date
            if base_date:
                return base_date + fields.Date.from_string('1970-01-01') + \
                       fields.Date.to_date(f'1970-01-{self.trigger_days + 1}') - \
                       fields.Date.from_string('1970-01-01')
        elif self.trigger_event == 'before_expiry':
            base_date = subscription.end_date
            if base_date:
                return base_date - fields.Date.from_string('1970-01-01') - \
                       fields.Date.to_date(f'1970-01-{self.trigger_days + 1}') + \
                       fields.Date.from_string('1970-01-01')
        
        return None
    
    def _check_conditions(self, subscription):
        """Check if subscription meets the rule conditions"""
        if not self.condition_field:
            return True
        
        field_value = getattr(subscription, self.condition_field, None)
        condition_value = self.condition_value
        
        # Convert condition value to appropriate type
        if self.condition_field == 'amount':
            try:
                condition_value = float(condition_value)
            except (ValueError, TypeError):
                return False
        
        # Apply operator
        if self.condition_operator == '=':
            return field_value == condition_value
        elif self.condition_operator == '!=':
            return field_value != condition_value
        elif self.condition_operator == '>':
            return field_value > condition_value
        elif self.condition_operator == '<':
            return field_value < condition_value
        elif self.condition_operator == '>=':
            return field_value >= condition_value
        elif self.condition_operator == '<=':
            return field_value <= condition_value
        
        return True
    
    def _execute_action(self, subscription):
        """Execute the rule action on the subscription"""
        if self.action == 'status_change' and self.target_status:
            subscription.state = self.target_status
            subscription.message_post(
                body=f"Status changed to {self.target_status} by rule: {self.name}"
            )
        
        elif self.action == 'send_email' and self.email_template_id:
            self.email_template_id.send_mail(subscription.id, force_send=True)
        
        elif self.action == 'create_activity':
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': f'Rule Action: {self.name}',
                'note': f'Subscription rule "{self.name}" triggered for {subscription.name}',
                'res_id': subscription.id,
                'res_model': 'ams.subscription',
                'user_id': self.env.user.id,
            })
    
    @api.constrains('trigger_days')
    def _check_trigger_days(self):
        for rule in self:
            if rule.trigger_days < 0:
                raise ValidationError(_("Trigger days must be positive"))
    
    @api.constrains('action', 'target_status', 'email_template_id')
    def _check_action_requirements(self):
        for rule in self:
            if rule.action == 'status_change' and not rule.target_status:
                raise ValidationError(_("Target status is required for status change actions"))
            if rule.action == 'send_email' and not rule.email_template_id:
                raise ValidationError(_("Email template is required for send email actions"))