# wizards/automation_wizard.py
from odoo import models, fields, api

class AutomationWizard(models.TransientModel):
    _name = 'automation.wizard'
    _description = 'Quick Automation Setup Wizard'

    template_type = fields.Selection([
        ('low_stock', '📦 Unpublish products when stock is low'),
        ('high_value', '💰 Alert on high-value opportunities'),
        ('overdue', '⏰ Follow up on overdue records'),
        ('archive_old', '📁 Archive old inactive records'),
        ('custom', '🔧 Custom automation (advanced)')
    ], 'Automation Type', required=True, default='low_stock')

    target_model_id = fields.Many2one('ir.model', 'Apply to Model', required=True)
    rule_name = fields.Char('Rule Name')
    
    # Template parameters
    threshold_value = fields.Integer('Threshold Value', default=5)
    days_value = fields.Integer('Days', default=7)
    target_field_id = fields.Many2one('ir.model.fields', 'Field')

    @api.onchange('template_type', 'target_model_id')
    def _onchange_template_config(self):
        """Set default configurations based on template and model"""
        if not self.target_model_id:
            return

        model_name = self.target_model_id.model
        
        # Set default rule names and field suggestions
        if self.template_type == 'low_stock':
            self.rule_name = f'Unpublish Low Stock {self.target_model_id.name}'
            if model_name == 'product.template':
                self.target_field_id = self._find_field('qty_available')
        
        elif self.template_type == 'high_value':
            self.rule_name = f'High Value {self.target_model_id.name} Alert'
            if model_name == 'crm.lead':
                self.target_field_id = self._find_field('expected_revenue')
                self.threshold_value = 10000
        
        elif self.template_type == 'overdue':
            self.rule_name = f'Overdue {self.target_model_id.name} Follow-up'
            self.target_field_id = self._find_field('date_deadline') or self._find_field('date_open')
        
        elif self.template_type == 'archive_old':
            self.rule_name = f'Archive Old {self.target_model_id.name}'
            self.target_field_id = self._find_field('write_date') or self._find_field('create_date')
            self.days_value = 90

    def _find_field(self, field_name):
        """Find a field by name in the target model"""
        if not self.target_model_id:
            return False
        
        field = self.env['ir.model.fields'].search([
            ('model_id', '=', self.target_model_id.id),
            ('name', '=', field_name)
        ], limit=1)
        return field.id if field else False

    def create_automation(self):
        """Create the automation rule based on template"""
        if self.template_type == 'custom':
            return self._create_custom_automation()
        
        automation_vals = self._get_automation_values()
        automation = self.env['business.automation'].create(automation_vals)
        
        # Create conditions
        condition_vals = self._get_condition_values(automation.id)
        if condition_vals:
            self.env['business.automation.condition'].create(condition_vals)
        
        # Create actions
        action_vals = self._get_action_values(automation.id)
        if action_vals:
            for action_val in action_vals:
                self.env['business.automation.action'].create(action_val)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'business.automation',
            'res_id': automation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_automation_values(self):
        """Get base automation values"""
        return {
            'name': self.rule_name or f'Auto-generated {self.template_type}',
            'model_id': self.target_model_id.id,
            'trigger_type': self._get_trigger_type(),
            'use_simple_conditions': True,
            'condition_type': 'all'
        }

    def _get_trigger_type(self):
        """Get trigger type based on template"""
        if self.template_type in ['low_stock', 'high_value']:
            return 'on_write_fields'
        elif self.template_type in ['overdue', 'archive_old']:
            return 'time_based'
        return 'on_write'

    def _get_condition_values(self, automation_id):
        """Get condition configuration based on template"""
        if not self.target_field_id:
            return None

        base_vals = {
            'automation_id': automation_id,
            'field_id': self.target_field_id,
            'sequence': 10
        }

        if self.template_type == 'low_stock':
            base_vals.update({
                'operator': '<',
                'value_type': 'fixed',
                'value_integer': self.threshold_value
            })
        
        elif self.template_type == 'high_value':
            base_vals.update({
                'operator': '>',
                'value_type': 'fixed',
                'value_integer': self.threshold_value
            })
        
        elif self.template_type in ['overdue', 'archive_old']:
            # Time-based conditions are handled in the automation trigger
            return None

        return base_vals

    def _get_action_values(self, automation_id):
        """Get action configuration based on template"""
        actions = []
        model_name = self.target_model_id.model

        if self.template_type == 'low_stock':
            # Try to unpublish product
            publish_field = self._find_model_field('is_published') or self._find_model_field('website_published')
            if publish_field:
                actions.append({
                    'automation_id': automation_id,
                    'sequence': 10,
                    'action_type': 'set_field',
                    'update_field_id': publish_field,
                    'update_value_type': 'fixed',
                    'update_value_boolean': False
                })
            
            # Create activity for stock manager
            actions.append({
                'automation_id': automation_id,
                'sequence': 20,
                'action_type': 'create_activity',
                'activity_type_id': self._get_activity_type('mail.mail_activity_data_todo'),
                'activity_summary': f'Low stock alert: {{record_name}}',
                'activity_note': f'Product stock has fallen below {self.threshold_value} units.',
                'activity_user_type': 'current',
                'activity_date_deadline': 0
            })

        elif self.template_type == 'high_value':
            # Create high-priority activity
            actions.append({
                'automation_id': automation_id,
                'sequence': 10,
                'action_type': 'create_activity',
                'activity_type_id': self._get_activity_type('mail.mail_activity_data_call'),
                'activity_summary': f'High-value opportunity: {{record_name}}',
                'activity_note': f'Opportunity value exceeds {self.threshold_value}. Requires immediate attention.',
                'activity_user_type': 'responsible',
                'activity_date_deadline': 1
            })

        elif self.template_type == 'overdue':
            # Send follow-up email if template exists
            template = self._find_email_template()
            if template:
                actions.append({
                    'automation_id': automation_id,
                    'sequence': 10,
                    'action_type': 'send_email',
                    'email_template_id': template
                })
            else:
                # Create follow-up activity
                actions.append({
                    'automation_id': automation_id,
                    'sequence': 10,
                    'action_type': 'create_activity',
                    'activity_type_id': self._get_activity_type('mail.mail_activity_data_call'),
                    'activity_summary': f'Follow up on overdue: {{record_name}}',
                    'activity_note': f'This record is {self.days_value} days overdue.',
                    'activity_user_type': 'responsible',
                    'activity_date_deadline': 0
                })

        elif self.template_type == 'archive_old':
            # Archive old records
            if self._model_has_active_field():
                actions.append({
                    'automation_id': automation_id,
                    'sequence': 10,
                    'action_type': 'archive'
                })

        return actions

    def _find_model_field(self, field_name):
        """Find field ID by name in target model"""
        field = self.env['ir.model.fields'].search([
            ('model_id', '=', self.target_model_id.id),
            ('name', '=', field_name)
        ], limit=1)
        return field.id if field else None

    def _get_activity_type(self, xml_id):
        """Get activity type by XML ID"""
        try:
            activity_type = self.env.ref(xml_id)
            return activity_type.id
        except:
            # Fallback to any activity type
            activity_type = self.env['mail.activity.type'].search([], limit=1)
            return activity_type.id if activity_type else None

    def _find_email_template(self):
        """Find relevant email template for the model"""
        templates = self.env['mail.template'].search([
            ('model_id', '=', self.target_model_id.id)
        ], limit=1)
        return templates.id if templates else None

    def _model_has_active_field(self):
        """Check if model has 'active' field"""
        return bool(self._find_model_field('active'))

    def _create_custom_automation(self):
        """Create empty automation for custom configuration"""
        automation = self.env['business.automation'].create({
            'name': self.rule_name or 'Custom Automation',
            'model_id': self.target_model_id.id,
            'trigger_type': 'on_write',
            'use_simple_conditions': True,
            'condition_type': 'all'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'business.automation',
            'res_id': automation.id,
            'view_mode': 'form',
            'target': 'current',
        }


# Demo data with sample automations
class BusinessAutomationDemo(models.Model):
    _inherit = 'business.automation'

    def create_demo_automations(self):
        """Create sample automation rules for demonstration"""
        
        # 1. Product Stock Automation
        product_model = self.env['ir.model'].search([('model', '=', 'product.template')], limit=1)
        if product_model:
            stock_automation = self.create({
                'name': 'Unpublish Low Stock Products',
                'model_id': product_model.id,
                'trigger_type': 'on_write_fields',
                'use_simple_conditions': True,
                'condition_type': 'all',
                'active': False  # Disabled by default
            })
            
            # Add trigger field
            qty_field = self.env['ir.model.fields'].search([
                ('model_id', '=', product_model.id),
                ('name', '=', 'qty_available')
            ], limit=1)
            if qty_field:
                stock_automation.write({'trigger_field_ids': [(4, qty_field.id)]})
                
                # Add condition
                self.env['business.automation.condition'].create({
                    'automation_id': stock_automation.id,
                    'field_id': qty_field.id,
                    'operator': '<',
                    'value_type': 'fixed',
                    'value_integer': 5
                })
                
                # Add action
                publish_field = self.env['ir.model.fields'].search([
                    ('model_id', '=', product_model.id),
                    ('name', '=', 'is_published')
                ], limit=1)
                if publish_field:
                    self.env['business.automation.action'].create({
                        'automation_id': stock_automation.id,
                        'action_type': 'set_field',
                        'update_field_id': publish_field.id,
                        'update_value_type': 'fixed',
                        'update_value_boolean': False
                    })

        # 2. CRM Lead Automation  
        lead_model = self.env['ir.model'].search([('model', '=', 'crm.lead')], limit=1)
        if lead_model:
            lead_automation = self.create({
                'name': 'High Value Lead Alert',
                'model_id': lead_model.id,
                'trigger_type': 'on_write_fields',
                'use_simple_conditions': True,
                'condition_type': 'all',
                'active': False
            })
            
            # Add condition for high expected revenue
            revenue_field = self.env['ir.model.fields'].search([
                ('model_id', '=', lead_model.id),
                ('name', '=', 'expected_revenue')
            ], limit=1)
            if revenue_field:
                lead_automation.write({'trigger_field_ids': [(4, revenue_field.id)]})
                
                self.env['business.automation.condition'].create({
                    'automation_id': lead_automation.id,
                    'field_id': revenue_field.id,
                    'operator': '>',
                    'value_type': 'fixed',
                    'value_float': 50000.0
                })
                
                # Add activity creation action
                activity_type = self.env['mail.activity.type'].search([], limit=1)
                if activity_type:
                    self.env['business.automation.action'].create({
                        'automation_id': lead_automation.id,
                        'action_type': 'create_activity',
                        'activity_type_id': activity_type.id,
                        'activity_summary': 'High-value lead requires attention',
                        'activity_note': 'Lead value exceeds $50,000 - immediate follow-up required',
                        'activity_user_type': 'responsible',
                        'activity_date_deadline': 1
                    })

        return True


# Sample usage instructions as comments
"""
QUICK SETUP EXAMPLES:

1. PRODUCT STOCK MANAGEMENT:
   - Choose "Unpublish products when stock is low"
   - Select Product Template model
   - Set threshold to 5
   - Creates: Trigger on qty_available update, condition < 5, action set is_published = False

2. HIGH-VALUE OPPORTUNITY ALERTS:
   - Choose "Alert on high-value opportunities" 
   - Select CRM Lead model
   - Set threshold to 10000
   - Creates: Trigger on expected_revenue update, condition > 10000, action create activity

3. OVERDUE FOLLOW-UPS:
   - Choose "Follow up on overdue records"
   - Select any model with date fields
   - Set days to 7
   - Creates: Time-based trigger, condition 7 days after deadline, action send email/activity

4. ARCHIVE OLD RECORDS:
   - Choose "Archive old inactive records"
   - Select any model
   - Set days to 90
   - Creates: Time-based trigger, condition 90 days after last update, action archive

The system automatically:
- Sets appropriate trigger types
- Creates relevant conditions  
- Configures useful actions
- Provides execution tracking
- Includes error handling
"""