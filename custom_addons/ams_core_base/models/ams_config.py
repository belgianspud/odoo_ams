# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AmsConfig(models.Model):
    """AMS-wide configuration settings including industry type and global preferences."""
    
    _name = 'ams.config'
    _description = 'AMS Configuration'
    _order = 'name'
    
    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='Name for this configuration set'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Only one configuration can be active at a time'
    )
    
    # Industry Configuration
    industry_type = fields.Selection([
        ('healthcare', 'Healthcare/Medical'),
        ('aviation', 'Aviation'),
        ('legal', 'Legal'),
        ('engineering', 'Engineering'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('technology', 'Technology'),
        ('other', 'Other')
    ], string='Industry Type', required=True, default='healthcare',
       help='Industry type determines which fields and lookups are available')
    
    # Member ID Configuration
    member_id_prefix = fields.Char(
        string='Member ID Prefix',
        size=5,
        help='Optional prefix for member IDs (e.g., "M-" or "AMS")'
    )
    
    member_id_sequence_length = fields.Integer(
        string='Member ID Sequence Length',
        default=6,
        help='Number of digits in the member ID sequence'
    )
    
    # Address Configuration
    enable_multiple_addresses = fields.Boolean(
        string='Enable Multiple Addresses',
        default=True,
        help='Allow contacts to have multiple addresses'
    )
    
    max_addresses_per_contact = fields.Integer(
        string='Max Addresses per Contact',
        default=3,
        help='Maximum number of addresses allowed per contact'
    )
    
    # Relationship Configuration
    enable_partner_relationships = fields.Boolean(
        string='Enable Partner Relationships',
        default=True,
        help='Enable relationship tracking between partners'
    )
    
    # Security Configuration
    default_portal_access = fields.Boolean(
        string='Default Portal Access',
        default=False,
        help='Give new members portal access by default'
    )
    
    # Communication Configuration
    require_primary_email = fields.Boolean(
        string='Require Primary Email',
        default=True,
        help='Make primary email address mandatory'
    )
    
    require_primary_phone = fields.Boolean(
        string='Require Primary Phone',
        default=False,
        help='Make primary phone number mandatory'
    )
    
    # Professional Fields Configuration (Industry Dependent)
    enable_professional_category = fields.Boolean(
        string='Enable Professional Category',
        compute='_compute_industry_fields',
        store=True,
        help='Enable professional category field'
    )
    
    enable_credentials = fields.Boolean(
        string='Enable Credentials',
        compute='_compute_industry_fields', 
        store=True,
        help='Enable credentials/designations field'
    )
    
    enable_license_numbers = fields.Boolean(
        string='Enable License Numbers',
        compute='_compute_industry_fields',
        store=True,
        help='Enable professional license number fields'
    )
    
    @api.depends('industry_type')
    def _compute_industry_fields(self):
        """Compute which fields should be enabled based on industry type."""
        for record in self:
            if record.industry_type in ['healthcare', 'legal', 'aviation', 'engineering']:
                record.enable_professional_category = True
                record.enable_credentials = True
                record.enable_license_numbers = True
            else:
                record.enable_professional_category = False
                record.enable_credentials = False  
                record.enable_license_numbers = False
    
    @api.constrains('active')
    def _check_single_active_config(self):
        """Ensure only one configuration is active at a time."""
        if self.active:
            other_active = self.search([('active', '=', True), ('id', '!=', self.id)])
            if other_active:
                raise ValidationError(_('Only one AMS configuration can be active at a time.'))
    
    @api.model
    def get_active_config(self):
        """Get the currently active configuration."""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # Create default configuration if none exists
            config = self.create({
                'name': 'Default AMS Configuration',
                'active': True,
                'industry_type': 'healthcare',
            })
        return config
    
    def generate_member_id(self):
        """Generate the next member ID based on configuration."""
        self.ensure_one()
        
        # Get or create sequence
        sequence_code = f'ams.member.id.{self.id}'
        sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
        
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': f'AMS Member ID ({self.name})',
                'code': sequence_code,
                'padding': self.member_id_sequence_length,
                'number_increment': 1,
            })
        
        # Generate next number
        next_number = sequence.next_by_code(sequence_code)
        
        # Add prefix if configured
        if self.member_id_prefix:
            return f'{self.member_id_prefix}{next_number}'
        
        return next_number
    
    # Add this method to the AmsConfig class in ams_config.py

    def action_view_sequences(self):
        """View sequences related to this configuration."""
        self.ensure_one()
    
        sequence_code = f'ams.member.id.{self.id}'
        sequences = self.env['ir.sequence'].search([('code', '=', sequence_code)])
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Member ID Sequences',
            'res_model': 'ir.sequence',
            'view_mode': 'tree,form',
            'domain': [('code', '=', sequence_code)],
            'context': {
                'default_name': f'AMS Member ID ({self.name})',
                'default_code': sequence_code,
                'default_padding': self.member_id_sequence_length,
                'default_prefix': self.member_id_prefix or '',
            },
            'help': f"""
                <p class="o_view_nocontent_smiling_face">
                    No sequences found for this configuration
                </p>
                <p>
                    Member ID sequences will be created automatically when the first member ID is generated.
                </p>
            """
    }