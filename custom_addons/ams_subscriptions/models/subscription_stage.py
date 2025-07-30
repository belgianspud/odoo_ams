from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Handle optional requests import for webhook functionality
try:
    import requests
    import json
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_logger = logging.getLogger(__name__)


class SubscriptionStage(models.Model):
    _name = 'ams.subscription.stage'
    _description = 'Subscription Stage'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True,
        help="Name of the subscription stage"
    )
    
    description = fields.Text(
        string='Description',
        help="Description of this stage"
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=1,
        help="Order of the stages"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this stage"
    )
    
    # Stage Properties
    is_initial_stage = fields.Boolean(
        string='Initial Stage',
        default=False,
        help="Check if this is the initial stage for new subscriptions"
    )
    
    is_final_stage = fields.Boolean(
        string='Final Stage',
        default=False,
        help="Check if this is a final stage (completed or cancelled)"
    )
    
    is_approval_stage = fields.Boolean(
        string='Approval Stage',
        default=False,
        help="Check if this stage requires approval"
    )
    
    # State Mapping
    subscription_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('pending_renewal', 'Pending Renewal'),
        ('expired', 'Expired'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Related Subscription State', 
       help="Subscription state that corresponds to this stage")
    
    # Visual Properties
    color = fields.Integer(
        string='Color',
        default=0,
        help="Color for kanban view"
    )
    
    legend_normal = fields.Char(
        string='Green Kanban Label',
        default=lambda self: _('In Progress'),
        translate=True,
        help="Label for the kanban column when the subscription is in normal state"
    )
    
    legend_blocked = fields.Char(
        string='Red Kanban Label', 
        default=lambda self: _('Blocked'),
        translate=True,
        help="Label for the kanban column when the subscription is blocked"
    )
    
    legend_done = fields.Char(
        string='Grey Kanban Label',
        default=lambda self: _('Ready for Next Stage'),
        translate=True,
        help="Label for the kanban column when the subscription is ready for next stage"
    )
    
    # Email Templates
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'ams.member.subscription')],
        help="Email template to send when subscription reaches this stage"
    )
    
    # Automation
    auto_send_email = fields.Boolean(
        string='Auto Send Email',
        default=False,
        help="Automatically send email when subscription reaches this stage"
    )
    
    # Requirements
    required_fields = fields.Text(
        string='Required Fields',
        help="Comma-separated list of fields required to move to this stage"
    )
    
    # Statistics
    subscription_count = fields.Integer(
        string='Subscription Count',
        compute='_compute_subscription_count',
        help="Number of subscriptions in this stage"
    )
    
    # Next/Previous Stages
    next_stage_ids = fields.Many2many(
        'ams.subscription.stage',
        'subscription_stage_next_rel',
        'stage_id',
        'next_stage_id',
        string='Next Stages',
        help="Allowed next stages"
    )
    
    previous_stage_ids = fields.Many2many(
        'ams.subscription.stage',
        'subscription_stage_previous_rel',
        'stage_id',
        'previous_stage_id',
        string='Previous Stages',
        help="Allowed previous stages"
    )
    
    # Permissions
    group_ids = fields.Many2many(
        'res.groups',
        string='Groups',
        help="Groups that can move subscriptions to this stage"
    )
    
    # Stage Actions
    action_ids = fields.One2many(
        'ams.subscription.stage.action',
        'stage_id',
        string='Automated Actions',
        help="Actions to perform when subscription reaches this stage"
    )

    @api.depends('subscription_state')
    def _compute_subscription_count(self):
        """Compute number of subscriptions in this stage"""
        for stage in self:
            if stage.subscription_state:
                count = self.env['ams.member.subscription'].search_count([
                    ('state', '=', stage.subscription_state)
                ])
                stage.subscription_count = count
            else:
                # Count by stage_id if no state mapping
                count = self.env['ams.member.subscription'].search_count([
                    ('stage_id', '=', stage.id)
                ])
                stage.subscription_count = count

    @api.constrains('is_initial_stage')
    def _check_single_initial_stage(self):
        """Ensure only one initial stage exists"""
        if self.is_initial_stage:
            initial_stages = self.search([
                ('is_initial_stage', '=', True),
                ('id', '!=', self.id)
            ])
            if initial_stages:
                raise ValidationError(_("Only one stage can be marked as initial stage."))

    @api.constrains('sequence')
    def _check_positive_sequence(self):
        """Ensure sequence is positive"""
        for stage in self:
            if stage.sequence <= 0:
                raise ValidationError(_("Sequence must be a positive number."))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle initial stage logic"""
        stages = super().create(vals_list)
        
        for stage in stages:
            # If this is the first stage created, make it initial
            if not self.search([('is_initial_stage', '=', True)], limit=1):
                stage.is_initial_stage = True
        
        return stages

    def write(self, vals):
        """Override write to handle stage transitions"""
        # If marking as not initial, ensure another initial stage exists
        if 'is_initial_stage' in vals and not vals['is_initial_stage']:
            for stage in self:
                if stage.is_initial_stage:
                    other_initial = self.search([
                        ('is_initial_stage', '=', True),
                        ('id', '!=', stage.id)
                    ], limit=1)
                    if not other_initial:
                        raise ValidationError(_("At least one stage must be marked as initial."))
        
        return super().write(vals)

    def unlink(self):
        """Override unlink to prevent deletion of stages with subscriptions"""
        for stage in self:
            subscription_count = self.env['ams.member.subscription'].search_count([
                ('stage_id', '=', stage.id)
            ])
            if subscription_count > 0:
                raise ValidationError(
                    _("Cannot delete stage '%s' because it has %d subscription(s). "
                      "Archive it instead.") % (stage.name, subscription_count)
                )
            
            # Prevent deletion of initial stage if it's the only one
            if stage.is_initial_stage:
                other_initial = self.search([
                    ('is_initial_stage', '=', True),
                    ('id', '!=', stage.id)
                ], limit=1)
                if not other_initial:
                    raise ValidationError(_("Cannot delete the only initial stage."))
        
        return super().unlink()

    def action_view_subscriptions(self):
        """View subscriptions in this stage"""
        self.ensure_one()
        
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ams_subscriptions.action_member_subscription"
        )
        
        if self.subscription_state:
            action['domain'] = [('state', '=', self.subscription_state)]
        else:
            action['domain'] = [('stage_id', '=', self.id)]
        
        action['context'] = {
            'default_stage_id': self.id,
            'search_default_stage_id': self.id,
        }
        
        return action

    def get_next_stages(self, subscription=None):
        """Get allowed next stages for a subscription"""
        self.ensure_one()
        
        # If specific next stages are defined, use them
        if self.next_stage_ids:
            return self.next_stage_ids
        
        # Otherwise, return next stage by sequence
        next_stage = self.search([
            ('sequence', '>', self.sequence),
            ('active', '=', True)
        ], order='sequence', limit=1)
        
        return next_stage

    def get_previous_stages(self, subscription=None):
        """Get allowed previous stages for a subscription"""
        self.ensure_one()
        
        # If specific previous stages are defined, use them
        if self.previous_stage_ids:
            return self.previous_stage_ids
        
        # Otherwise, return previous stage by sequence
        previous_stage = self.search([
            ('sequence', '<', self.sequence),
            ('active', '=', True)
        ], order='sequence desc', limit=1)
        
        return previous_stage

    def can_move_to_stage(self, subscription, user=None):
        """Check if subscription can be moved to this stage"""
        self.ensure_one()
        
        if not user:
            user = self.env.user
        
        # Check group permissions
        if self.group_ids:
            user_groups = user.groups_id
            if not any(group in user_groups for group in self.group_ids):
                return False, _("You don't have permission to move to this stage.")
        
        # Check required fields
        if self.required_fields:
            required_field_list = [f.strip() for f in self.required_fields.split(',')]
            for field_name in required_field_list:
                if hasattr(subscription, field_name):
                    field_value = getattr(subscription, field_name)
                    if not field_value:
                        return False, _("Required field '%s' is missing.") % field_name
                else:
                    return False, _("Field '%s' does not exist.") % field_name
        
        return True, _("Can move to this stage.")

    def execute_stage_actions(self, subscription):
        """Execute automated actions for this stage"""
        self.ensure_one()
        
        # Send email if configured
        if self.auto_send_email and self.mail_template_id:
            try:
                self.mail_template_id.send_mail(subscription.id, force_send=True)
            except Exception as e:
                _logger.warning(f"Failed to send email for stage {self.name}: {e}")
        
        # Execute custom actions
        for action in self.action_ids:
            action.execute(subscription)

    @api.model
    def get_default_stage(self):
        """Get the default/initial stage"""
        return self.search([('is_initial_stage', '=', True)], limit=1)

    def name_get(self):
        """Customize display name"""
        result = []
        for stage in self:
            name = stage.name
            if stage.subscription_count > 0:
                name += f" ({stage.subscription_count})"
            result.append((stage.id, name))
        return result


class SubscriptionStageAction(models.Model):
    _name = 'ams.subscription.stage.action'
    _description = 'Subscription Stage Action'
    _order = 'sequence, name'

    name = fields.Char(
        string='Action Name',
        required=True,
        help="Name of the action"
    )
    
    stage_id = fields.Many2one(
        'ams.subscription.stage',
        string='Stage',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of execution"
    )
    
    action_type = fields.Selection([
        ('email', 'Send Email'),
        ('field_update', 'Update Field'),
        ('create_activity', 'Create Activity'),
        ('server_action', 'Server Action'),
        ('webhook', 'Webhook Call')
    ], string='Action Type', required=True)
    
    # Email Action
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'ams.member.subscription')]
    )
    
    # Field Update Action
    field_name = fields.Char(
        string='Field Name',
        help="Technical name of the field to update"
    )
    
    field_value = fields.Char(
        string='Field Value',
        help="Value to set (supports Python expressions)"
    )
    
    # Activity Action
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type'
    )
    
    activity_summary = fields.Char(
        string='Activity Summary'
    )
    
    activity_note = fields.Text(
        string='Activity Note'
    )
    
    # Server Action
    server_action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action'
    )
    
    # Webhook Action
    webhook_url = fields.Char(
        string='Webhook URL'
    )
    
    webhook_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT')
    ], string='HTTP Method', default='POST')
    
    active = fields.Boolean(
        string='Active',
        default=True
    )

    def execute(self, subscription):
        """Execute this action for a subscription"""
        self.ensure_one()
        
        if not self.active:
            return
        
        try:
            if self.action_type == 'email' and self.template_id:
                self.template_id.send_mail(subscription.id, force_send=True)
            
            elif self.action_type == 'field_update' and self.field_name:
                if hasattr(subscription, self.field_name):
                    # Simple value assignment (can be extended for Python expressions)
                    setattr(subscription, self.field_name, self.field_value)
            
            elif self.action_type == 'create_activity' and self.activity_type_id:
                subscription.activity_schedule(
                    activity_type_id=self.activity_type_id.id,
                    summary=self.activity_summary or self.name,
                    note=self.activity_note
                )
            
            elif self.action_type == 'server_action' and self.server_action_id:
                self.server_action_id.with_context(
                    active_id=subscription.id,
                    active_ids=[subscription.id],
                    active_model='ams.member.subscription'
                ).run()
            
            elif self.action_type == 'webhook' and self.webhook_url:
                if not HAS_REQUESTS:
                    _logger.warning("Requests library not available for webhook functionality")
                    return
                
                # Basic webhook implementation
                data = {
                    'subscription_id': subscription.id,
                    'stage_name': self.stage_id.name,
                    'action_name': self.name,
                    'member_name': subscription.partner_id.name,
                    'membership_type': subscription.membership_type_id.name
                }
                
                if self.webhook_method == 'GET':
                    requests.get(self.webhook_url, params=data, timeout=10)
                else:
                    requests.post(
                        self.webhook_url,
                        data=json.dumps(data),
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
        
        except Exception as e:
            _logger.error(f"Failed to execute stage action {self.name}: {e}")