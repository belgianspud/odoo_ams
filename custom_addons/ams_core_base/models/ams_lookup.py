# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AmsLookup(models.Model):
    """Generic lookup framework for configurable dropdown values across AMS modules."""
    
    _name = 'ams.lookup'
    _description = 'AMS Lookup Values'
    _order = 'category, sequence, name'
    
    name = fields.Char(
        string='Value',
        required=True,
        help='Display value for this lookup item'
    )
    
    code = fields.Char(
        string='Code',
        size=50,
        help='Optional code for this lookup value'
    )
    
    category = fields.Selection([
        ('professional_category', 'Professional Category'),
        ('member_type', 'Member Type'),
        ('designation', 'Designation/Credentials'),
        ('language', 'Language'),
        ('employment_setting', 'Employment Setting'),
        ('practice_area', 'Practice Area'),
        ('patient_type', 'Patient Type'),
        ('ethnic_culture', 'Ethnic/Culture Group'),
        ('gender_identity', 'Gender Identity'),
        ('sexual_orientation', 'Sexual Orientation'),
        ('pronouns', 'Pronouns'),
        ('relationship_type', 'Relationship Type'),
        ('address_type', 'Address Type'),
        ('phone_type', 'Phone Type'),
        ('email_type', 'Email Type'),
        ('communication_preference', 'Communication Preference'),
        ('account_status', 'Account Status'),
        ('contact_source', 'Contact Source'),
        ('other', 'Other'),
    ], string='Category', required=True, index=True,
       help='Category this lookup value belongs to')
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive values are hidden from selection but preserved for existing data'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of appearance in lists'
    )
    
    description = fields.Text(
        string='Description',
        help='Additional description or notes for this value'
    )
    
    # Industry Configuration
    industry_types = fields.Selection([
        ('all', 'All Industries'),
        ('healthcare', 'Healthcare/Medical Only'),
        ('aviation', 'Aviation Only'),
        ('legal', 'Legal Only'),
        ('engineering', 'Engineering Only'),
        ('finance', 'Finance Only'),
        ('education', 'Education Only'),
        ('technology', 'Technology Only'),
        ('other', 'Other Only'),
    ], string='Available for Industries', default='all',
       help='Which industries can use this lookup value')
    
    # System flags
    is_system = fields.Boolean(
        string='System Value',
        default=False,
        help='System values cannot be deleted'
    )
    
    is_default = fields.Boolean(
        string='Default Value',
        default=False,
        help='This value is selected by default for new records'
    )
    
    # Usage tracking
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        store=False,
        help='Number of records using this lookup value'
    )
    
    @api.depends('category', 'name')
    def _compute_usage_count(self):
        """Compute how many records are using this lookup value."""
        for record in self:
            # This is a placeholder - actual usage counting would depend on 
            # which models use this lookup and would be implemented in those models
            record.usage_count = 0
    
    @api.constrains('category', 'is_default')
    def _check_single_default_per_category(self):
        """Ensure only one default value per category."""
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('category', '=', record.category),
                    ('is_default', '=', True),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if other_defaults:
                    raise ValidationError(_(
                        'Only one default value is allowed per category. '
                        'Category "%s" already has a default value: %s'
                    ) % (dict(self._fields['category'].selection)[record.category], 
                         ', '.join(other_defaults.mapped('name'))))
    
    @api.constrains('is_system')
    def _check_system_deletion(self):
        """Prevent deletion of system values."""
        if any(record.is_system for record in self):
            raise ValidationError(_('System lookup values cannot be deleted.'))
    
    def unlink(self):
        """Override unlink to prevent deletion of system values and values in use."""
        for record in self:
            if record.is_system:
                raise ValidationError(_(
                    'Cannot delete system lookup value: %s'
                ) % record.name)
            
            # Check if value is in use (placeholder for actual usage check)
            if record.usage_count > 0:
                raise ValidationError(_(
                    'Cannot delete lookup value "%s" because it is currently in use by %d record(s). '
                    'Consider making it inactive instead.'
                ) % (record.name, record.usage_count))
        
        return super().unlink()
    
    @api.model
    def get_values_for_category(self, category, industry_type=None):
        """Get active lookup values for a specific category and industry."""
        domain = [
            ('category', '=', category),
            ('active', '=', True)
        ]
        
        # Filter by industry if specified
        if industry_type:
            domain.append('|')
            domain.append(('industry_types', '=', 'all'))
            domain.append(('industry_types', '=', industry_type))
        
        return self.search(domain)
    
    @api.model
    def get_selection_list(self, category, industry_type=None):
        """Get selection list format for a category."""
        values = self.get_values_for_category(category, industry_type)
        return [(val.id, val.name) for val in values]
    
    @api.model
    def get_default_value(self, category, industry_type=None):
        """Get the default value for a category."""
        domain = [
            ('category', '=', category),
            ('is_default', '=', True),
            ('active', '=', True)
        ]
        
        if industry_type:
            domain.append('|')
            domain.append(('industry_types', '=', 'all'))
            domain.append(('industry_types', '=', industry_type))
        
        default = self.search(domain, limit=1)
        return default.id if default else False
    
    @api.model
    def create_category_values(self, category, values_list, industry_type='all'):
        """Helper method to create multiple lookup values for a category."""
        created_values = []
        for seq, value_data in enumerate(values_list, 1):
            if isinstance(value_data, str):
                value_data = {'name': value_data}
            
            vals = {
                'category': category,
                'sequence': seq * 10,
                'industry_types': industry_type,
                **value_data
            }
            created_values.append(self.create(vals))
        
        return created_values
    
    def toggle_active(self):
        """Toggle active status of lookup value."""
        for record in self:
            record.active = not record.active


class AmsLookupCategory(models.Model):
    """Helper model to manage lookup categories and their configuration."""
    
    _name = 'ams.lookup.category'
    _description = 'AMS Lookup Categories'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Category Name',
        required=True
    )
    
    code = fields.Char(
        string='Category Code',
        required=True,
        size=50,
        help='Technical code used in selection fields'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of what this category is used for'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    industry_specific = fields.Boolean(
        string='Industry Specific',
        default=False,
        help='Whether this category is specific to certain industries'
    )
    
    applicable_industries = fields.Selection([
        ('all', 'All Industries'),
        ('healthcare', 'Healthcare/Medical'),
        ('aviation', 'Aviation'),
        ('legal', 'Legal'),
        ('engineering', 'Engineering'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('technology', 'Technology'),
        ('other', 'Other'),
    ], string='Applicable Industries', default='all')
    
    lookup_count = fields.Integer(
        string='Lookup Values Count',
        compute='_compute_lookup_count'
    )
    
    @api.depends('code')
    def _compute_lookup_count(self):
        """Count lookup values in this category."""
        for record in self:
            record.lookup_count = self.env['ams.lookup'].search_count([
                ('category', '=', record.code)
            ])
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique.'),
    ]

    def action_view_lookup_values(self):
        """View lookup values for this category."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Lookup Values - {self.name}',
            'res_model': 'ams.lookup',
            'view_mode': 'tree,form',
            'domain': [('category', '=', self.code)],
            'context': {
                'default_category': self.code,
                'search_default_active': 1
            }
        }