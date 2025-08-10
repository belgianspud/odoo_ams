# models/business_automation.py
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class BusinessAutomation(models.Model):
    _name = 'business.automation'
    _description = 'Business Automation Rules'
    _order = 'sequence, name'

    name = fields.Char('Rule Name', required=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)
    
    # Target Model
    model_id = fields.Many2one('ir.model', 'Apply to', required=True,
                              help="Records of this model will be processed by this rule")
    model_name = fields.Char(related='model_id.model', store=True)
    
    # TRIGGER CONFIGURATION
    trigger_type = fields.Selection([
        ('on_create', 'Record Creation'),
        ('on_write', 'Record Update'),
        ('on_write_fields', 'Specific Field Update'),
        ('time_based', 'Time-based'),
    ], 'Trigger', required=True, default='on_write',
       help="When should this automation run?")
    
    # For field-specific triggers
    trigger_field_ids = fields.Many2many(
        'ir.model.fields', 'automation_trigger_fields_rel',
        domain="[('model_id', '=', model_id)]",
        string='Watch Fields',
        help="Only trigger when these fields are updated"
    )
    
    # For time-based triggers
    time_delay_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'), 
        ('days', 'Days'),
        ('weeks', 'Weeks'),
    ], 'Delay Unit', default='days')
    time_delay_number = fields.Integer('Delay', default=7)
    time_field_id = fields.Many2one('ir.model.fields', 'Date Field',
                                   domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]",
                                   help="Date field to calculate delay from")
    
    # DOMAIN FILTER (CONDITIONS)
    domain_filter = fields.Text('Domain Filter', default='[]',
                               help="Python domain to filter records")
    domain_force_apply = fields.Boolean('Apply on All Records', 
                                       help="Apply to all records, not just the triggering one")
    
    # Simple condition builder (alternative to domain)
    use_simple_conditions = fields.Boolean('Use Simple Conditions', default=True)
    condition_ids = fields.One2many('business.automation.condition', 'automation_id', 'Conditions')
    condition_type = fields.Selection([
        ('all', 'All conditions must be true (AND)'),
        ('any', 'Any condition can be true (OR)'),
    ], 'Condition Logic', default='all')
    
    # ACTIONS
    action_ids = fields.One2many('business.automation.action', 'automation_id', 'Actions')
    
    # EXECUTION TRACKING
    execution_count = fields.Integer('Executions', readonly=True)
    last_execution = fields.Datetime('Last Run', readonly=True)
    
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.trigger_field_ids = [(5,)]
        self.time_field_id = False
        self.condition_ids = [(5,)]
        self.action_ids = [(5,)]
    
    @api.onchange('use_simple_conditions')
    def _onchange_use_simple_conditions(self):
        if self.use_simple_conditions:
            self.domain_filter = '[]'
        else:
            self.condition_ids = [(5,)]
    
    def execute_automation(self, records=None):
        """Execute this automation rule"""
        if not self.active:
            return
        
        if records is None:
            # For time-based or manual execution
            records = self._get_target_records()
        
        processed_count = 0
        for record in records:
            if self._check_conditions(record):
                self._execute_actions(record)
                processed_count += 1
        
        # Update execution stats
        self.sudo().write({
            'execution_count': self.execution_count + processed_count,
            'last_execution': fields.Datetime.now()
        })
        
        _logger.info(f"Automation '{self.name}' processed {processed_count} records")
    
    def _get_target_records(self):
        """Get records that should be processed (for time-based rules)"""
        if self.use_simple_conditions and self.condition_ids:
            domain = self._build_domain_from_conditions()
        else:
            domain = safe_eval(self.domain_filter or '[]')
        
        if self.trigger_type == 'time_based' and self.time_field_id:
            # Add time-based condition
            time_field = self.time_field_id.name
            delay_dict = {self.time_delay_type: self.time_delay_number}
            cutoff_date = datetime.now() - timedelta(**delay_dict)
            domain.append((time_field, '<=', cutoff_date.strftime('%Y-%m-%d %H:%M:%S')))
        
        return self.env[self.model_name].search(domain)
    
    def _check_conditions(self, record):
        """Check if conditions are met for this record"""
        if self.use_simple_conditions:
            if not self.condition_ids:
                return True
            
            results = []
            for condition in self.condition_ids:
                results.append(condition.evaluate(record))
            
            if self.condition_type == 'all':
                return all(results)
            else:
                return any(results)
        else:
            # Use domain filter
            if not self.domain_filter or self.domain_filter == '[]':
                return True
            
            domain = safe_eval(self.domain_filter)
            domain.append(('id', '=', record.id))
            return bool(self.env[self.model_name].search_count(domain))
    
    def _build_domain_from_conditions(self):
        """Convert simple conditions to domain"""
        domain = []
        for condition in self.condition_ids:
            domain.append(condition.to_domain())
        return domain
    
    def _execute_actions(self, record):
        """Execute all actions for this record"""
        for action in self.action_ids:
            try:
                action.execute(record)
            except Exception as e:
                _logger.error(f"Error executing action in automation '{self.name}': {str(e)}")


class BusinessAutomationCondition(models.Model):
    _name = 'business.automation.condition'
    _description = 'Automation Condition'
    _order = 'sequence'

    automation_id = fields.Many2one('business.automation', 'Automation', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    field_id = fields.Many2one('ir.model.fields', 'Field', required=True,
                              domain="[('model_id', '=', parent.model_id)]")
    field_type = fields.Selection(related='field_id.ttype', store=True)
    
    operator = fields.Selection([
        ('=', 'equals'),
        ('!=', 'not equal'),
        ('>', 'greater than'),
        ('>=', 'greater or equal'),
        ('<', 'less than'),
        ('<=', 'less or equal'),
        ('in', 'is in'),
        ('not in', 'not in'),
        ('ilike', 'contains'),
        ('not ilike', 'does not contain'),
        ('=?', 'is set'),
        ('!=', 'is not set'),
    ], 'Operator', required=True, default='=')
    
    value_type = fields.Selection([
        ('fixed', 'Fixed Value'),
        ('field', 'Another Field'),
        ('today', 'Today'),
        ('current_user', 'Current User'),
    ], 'Value Type', default='fixed')
    
    value_char = fields.Char('Text Value')
    value_integer = fields.Integer('Number Value')
    value_float = fields.Float('Decimal Value')
    value_boolean = fields.Boolean('True/False')
    value_date = fields.Date('Date Value')
    value_datetime = fields.Datetime('Date Time Value')
    value_selection = fields.Char('Selection Value')
    value_field_id = fields.Many2one('ir.model.fields', 'Field Value',
                                    domain="[('model_id', '=', parent.model_id)]")
    
    def evaluate(self, record):
        """Evaluate this condition against a record"""
        field_value = getattr(record, self.field_id.name, None)
        compare_value = self._get_compare_value(record)
        
        if self.operator == '=':
            return field_value == compare_value
        elif self.operator == '!=':
            return field_value != compare_value
        elif self.operator == '>':
            return (field_value or 0) > (compare_value or 0)
        elif self.operator == '>=':
            return (field_value or 0) >= (compare_value or 0)
        elif self.operator == '<':
            return (field_value or 0) < (compare_value or 0)
        elif self.operator == '<=':
            return (field_value or 0) <= (compare_value or 0)
        elif self.operator == 'in':
            return field_value in (compare_value or [])
        elif self.operator == 'not in':
            return field_value not in (compare_value or [])
        elif self.operator == 'ilike':
            return str(compare_value or '') in str(field_value or '')
        elif self.operator == 'not ilike':
            return str(compare_value or '') not in str(field_value or '')
        elif self.operator == '=?':
            return bool(field_value)
        
        return False
    
    def _get_compare_value(self, record):
        """Get the value to compare against"""
        if self.value_type == 'fixed':
            if self.field_type in ['integer']:
                return self.value_integer
            elif self.field_type in ['float', 'monetary']:
                return self.value_float
            elif self.field_type == 'boolean':
                return self.value_boolean
            elif self.field_type == 'date':
                return self.value_date
            elif self.field_type == 'datetime':
                return self.value_datetime
            elif self.field_type == 'selection':
                return self.value_selection
            else:
                return self.value_char
        elif self.value_type == 'field':
            return getattr(record, self.value_field_id.name, None)
        elif self.value_type == 'today':
            return fields.Date.today()
        elif self.value_type == 'current_user':
            return record.env.user.id
        
        return None
    
    def to_domain(self):
        """Convert to domain tuple"""
        field_name = self.field_id.name
        
        if self.value_type == 'fixed':
            value = self._get_compare_value(None)
        elif self.value_type == 'today':
            value = fields.Date.today()
        else:
            # For complex value types, we'll need to evaluate at runtime
            value = self._get_compare_value(None)
        
        return (field_name, self.operator, value)


class BusinessAutomationAction(models.Model):
    _name = 'business.automation.action'
    _description = 'Automation Action'
    _order = 'sequence'

    automation_id = fields.Many2one('business.automation', 'Automation', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    action_type = fields.Selection([
        ('set_field', 'Update Field'),
        ('create_activity', 'Create Activity'),
        ('send_email', 'Send Email'),
        ('archive', 'Archive Record'),
        ('unarchive', 'Unarchive Record'),
        ('create_record', 'Create Related Record'),
        ('execute_method', 'Execute Method'),
    ], 'Action', required=True, default='set_field')
    
    # Update Field Action
    update_field_id = fields.Many2one('ir.model.fields', 'Field to Update',
                                     domain="[('model_id', '=', parent.model_id)]")
    update_value_type = fields.Selection([
        ('fixed', 'Fixed Value'),
        ('field', 'Copy from Field'),
        ('formula', 'Formula'),
        ('current_user', 'Current User'),
        ('today', 'Today'),
    ], 'Update Value', default='fixed')
    
    update_value_char = fields.Char('Text Value')
    update_value_integer = fields.Integer('Number Value')
    update_value_float = fields.Float('Decimal Value')
    update_value_boolean = fields.Boolean('True/False')
    update_value_date = fields.Date('Date Value')
    update_value_field_id = fields.Many2one('ir.model.fields', 'Copy from Field',
                                           domain="[('model_id', '=', parent.model_id)]")
    update_formula = fields.Text('Formula', help="Python expression")
    
    # Activity Action
    activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type')
    activity_summary = fields.Char('Activity Summary')
    activity_note = fields.Text('Activity Note')
    activity_user_type = fields.Selection([
        ('current', 'Current User'),
        ('responsible', 'Record Responsible'),
        ('specific', 'Specific User'),
    ], 'Assign to', default='current')
    activity_user_id = fields.Many2one('res.users', 'Specific User')
    activity_date_deadline = fields.Integer('Days from now', default=0)
    
    # Email Action
    email_template_id = fields.Many2one('mail.template', 'Email Template')
    
    # Create Record Action
    create_model_id = fields.Many2one('ir.model', 'Create Record Type')
    create_field_mappings = fields.Text('Field Mappings', help="JSON field mapping")
    
    # Method Execution
    method_name = fields.Char('Method Name')
    
    def execute(self, record):
        """Execute this action on a record"""
        if self.action_type == 'set_field':
            self._execute_set_field(record)
        elif self.action_type == 'create_activity':
            self._execute_create_activity(record)
        elif self.action_type == 'send_email':
            self._execute_send_email(record)
        elif self.action_type == 'archive':
            record.active = False
        elif self.action_type == 'unarchive':
            record.active = True
        elif self.action_type == 'create_record':
            self._execute_create_record(record)
        elif self.action_type == 'execute_method':
            self._execute_method(record)
    
    def _execute_set_field(self, record):
        """Update field value"""
        if not self.update_field_id:
            return
        
        field_name = self.update_field_id.name
        value = self._get_update_value(record)
        setattr(record, field_name, value)
    
    def _get_update_value(self, record):
        """Get the value to update with"""
        if self.update_value_type == 'fixed':
            field_type = self.update_field_id.ttype
            if field_type in ['integer']:
                return self.update_value_integer
            elif field_type in ['float', 'monetary']:
                return self.update_value_float
            elif field_type == 'boolean':
                return self.update_value_boolean
            elif field_type == 'date':
                return self.update_value_date
            else:
                return self.update_value_char
        elif self.update_value_type == 'field':
            return getattr(record, self.update_value_field_id.name, None)
        elif self.update_value_type == 'current_user':
            return record.env.user.id
        elif self.update_value_type == 'today':
            return fields.Date.today()
        elif self.update_value_type == 'formula':
            return safe_eval(self.update_formula, {'record': record, 'env': record.env})
        
        return None
    
    def _execute_create_activity(self, record):
        """Create activity"""
        if not self.activity_type_id:
            return
        
        user_id = record.env.user.id
        if self.activity_user_type == 'responsible':
            user_id = getattr(record, 'user_id', record.env.user).id
        elif self.activity_user_type == 'specific':
            user_id = self.activity_user_id.id
        
        due_date = fields.Date.today() + timedelta(days=self.activity_date_deadline)
        
        record.activity_schedule(
            act_type_xmlid=self.activity_type_id.xml_id,
            summary=self.activity_summary or f'Automated: {self.automation_id.name}',
            note=self.activity_note,
            user_id=user_id,
            date_deadline=due_date
        )
    
    def _execute_send_email(self, record):
        """Send email"""
        if self.email_template_id:
            self.email_template_id.send_mail(record.id, force_send=True)
    
    def _execute_create_record(self, record):
        """Create related record"""
        if not self.create_model_id or not self.create_field_mappings:
            return
        
        try:
            import json
            mappings = json.loads(self.create_field_mappings)
            values = {}
            
            for target_field, source_field in mappings.items():
                if hasattr(record, source_field):
                    values[target_field] = getattr(record, source_field)
            
            self.env[self.create_model_id.model].create(values)
        except Exception as e:
            _logger.error(f"Error creating record: {str(e)}")
    
    def _execute_method(self, record):
        """Execute method"""
        if self.method_name and hasattr(record, self.method_name):
            method = getattr(record, self.method_name)
            method()


# Hook into base model to trigger automations
class BaseModelAutomation(models.AbstractModel):
    _inherit = 'base'
    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        self._trigger_automations('on_create', record)
        return record
    
    def write(self, vals):
        result = super().write(vals)
        for record in self:
            self._trigger_automations('on_write', record, list(vals.keys()))
        return result
    
    def _trigger_automations(self, trigger_type, record, changed_fields=None):
        """Trigger automation rules"""
        domain = [
            ('model_name', '=', record._name),
            ('active', '=', True),
            ('trigger_type', '=', trigger_type)
        ]
        
        automations = self.env['business.automation'].search(domain)
        
        for automation in automations:
            # Check field-specific triggers
            if (automation.trigger_type == 'on_write_fields' and 
                automation.trigger_field_ids and changed_fields):
                
                watched_fields = automation.trigger_field_ids.mapped('name')
                if not any(field in watched_fields for field in changed_fields):
                    continue
            
            automation.execute_automation(record)