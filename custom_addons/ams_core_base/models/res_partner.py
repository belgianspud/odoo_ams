# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    """Extend res.partner to add AMS-specific functionality for contacts and accounts."""
    
    _inherit = 'res.partner'
    
    # === AMS Core Fields ===
    member_id = fields.Char(
        string='Member ID',
        copy=False,
        index=True,
        help='Unique member identifier'
    )
    
    is_ams_member = fields.Boolean(
        string='AMS Member',
        default=False,
        help='Indicates if this contact is an AMS member'
    )
    
    member_type_id = fields.Many2one(
        'ams.lookup',
        string='Member Type',
        domain="[('category', '=', 'member_type'), ('active', '=', True)]",
        help='Type/category of member'
    )
    
    member_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('deceased', 'Deceased'),
        ('merged', 'Merged')
    ], string='Member Status', default='active', index=True)
    
    contact_source_id = fields.Many2one(
        'ams.lookup',
        string='Contact Source',
        domain="[('category', '=', 'contact_source'), ('active', '=', True)]",
        help='How this contact was acquired'
    )
    
    # === Professional Fields (Industry Dependent) ===
    professional_category_id = fields.Many2one(
        'ams.lookup',
        string='Professional Category',
        domain="[('category', '=', 'professional_category'), ('active', '=', True)]",
        help='Professional role or category'
    )
    
    job_title = fields.Char(
        string='Job Title',
        size=100,
        help='Professional job title (limited for label compatibility)'
    )
    
    designation_ids = fields.Many2many(
        'ams.lookup',
        'partner_designation_rel',
        'partner_id',
        'designation_id',
        string='Designations/Credentials',
        domain="[('category', '=', 'designation'), ('active', '=', True)]",
        help='Professional designations and credentials'
    )
    
    designation_other = fields.Char(
        string='Other Designation',
        help='Free text field for designations not in the lookup'
    )
    
    primary_license_number = fields.Char(
        string='Primary License Number',
        size=50,
        help='Primary professional license number'
    )
    
    secondary_license_number = fields.Char(
        string='Secondary License Number', 
        size=50,
        help='Secondary professional license number'
    )
    
    # === Personal/Demographic Fields ===
    pronouns_id = fields.Many2one(
        'ams.lookup',
        string='Pronouns',
        domain="[('category', '=', 'pronouns'), ('active', '=', True)]"
    )
    
    primary_language_id = fields.Many2one(
        'ams.lookup',
        string='Primary Language',
        domain="[('category', '=', 'language'), ('active', '=', True)]"
    )
    
    secondary_language_id = fields.Many2one(
        'ams.lookup',
        string='Secondary Language',
        domain="[('category', '=', 'language'), ('active', '=', True)]"
    )
    
    gender_identity_id = fields.Many2one(
        'ams.lookup',
        string='Gender Identity',
        domain="[('category', '=', 'gender_identity'), ('active', '=', True)]"
    )
    
    gender_identity_other = fields.Char(
        string='Other Gender Identity',
        help='Free text if "Other" selected for gender identity'
    )
    
    sexual_orientation_id = fields.Many2one(
        'ams.lookup',
        string='Sexual Orientation',
        domain="[('category', '=', 'sexual_orientation'), ('active', '=', True)]"
    )
    
    ethnic_culture_id = fields.Many2one(
        'ams.lookup',
        string='Ethnic/Culture Group',
        domain="[('category', '=', 'ethnic_culture'), ('active', '=', True)]"
    )
    
    ethnic_culture_other = fields.Char(
        string='Other Ethnic/Culture',
        help='Free text if "Other" selected for ethnic/culture group'
    )
    
    # === Industry Specific Fields ===
    employment_setting_id = fields.Many2one(
        'ams.lookup',
        string='Employment Setting',
        domain="[('category', '=', 'employment_setting'), ('active', '=', True)]"
    )
    
    employment_setting_other = fields.Char(
        string='Other Employment Setting'
    )
    
    practice_area_ids = fields.Many2many(
        'ams.lookup',
        'partner_practice_area_rel',
        'partner_id', 
        'practice_area_id',
        string='Practice Areas',
        domain="[('category', '=', 'practice_area'), ('active', '=', True)]"
    )
    
    practice_area_other = fields.Char(
        string='Other Practice Area'
    )
    
    patient_type_ids = fields.Many2many(
        'ams.lookup',
        'partner_patient_type_rel',
        'partner_id',
        'patient_type_id', 
        string='Patient Types',
        domain="[('category', '=', 'patient_type'), ('active', '=', True)]"
    )
    
    # === Communication Preferences ===
    preferred_communication_id = fields.Many2one(
        'ams.lookup',
        string='Preferred Communication',
        domain="[('category', '=', 'communication_preference'), ('active', '=', True)]"
    )
    
    # === Engagement Fields ===
    engagement_score = fields.Float(
        string='Engagement Score',
        default=0.0,
        help='Calculated engagement score based on activities and participation'
    )
    
    engagement_level = fields.Selection([
        ('copper', 'Copper'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'), 
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond')
    ], string='Engagement Level', 
       help='Engagement tier based on score')
    
    last_engagement_update = fields.Datetime(
        string='Last Engagement Update',
        help='When engagement score was last calculated'
    )
    
    # === Membership Information (View-only, populated by membership modules) ===
    membership_join_date = fields.Date(
        string='Join Date',
        help='Date when member first joined (updated if reinstated)'
    )
    
    membership_original_join_date = fields.Date(
        string='Original Join Date', 
        help='Original join date, never changes'
    )
    
    membership_paid_through_date = fields.Date(
        string='Paid Through Date',
        help='Date membership is paid through'
    )
    
    membership_renewal_date = fields.Date(
        string='Renewal Date',
        help='Date membership renews'
    )
    
    # === Address Enhancement ===
    address_type_ids = fields.One2many(
        'res.partner.address',
        'partner_id',
        string='Additional Addresses',
        help='Multiple addresses with different types'
    )
    
    # === Relationship Fields ===
    relationship_ids = fields.One2many(
        'res.partner.relationship',
        'partner_id',
        string='Relationships'
    )
    
    reverse_relationship_ids = fields.One2many(
        'res.partner.relationship',
        'related_partner_id', 
        string='Reverse Relationships'
    )
    
    # === Emergency Contact ===
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name'
    )
    
    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone'
    )
    
    emergency_contact_relationship = fields.Char(
        string='Emergency Contact Relationship'
    )
    
    # === Computed Fields ===
    display_name_with_credentials = fields.Char(
        string='Name with Credentials',
        compute='_compute_display_name_with_credentials',
        store=True,
        help='Full name with professional credentials'
    )
    
    industry_fields_visible = fields.Boolean(
        string='Show Industry Fields',
        compute='_compute_industry_fields_visible',
        help='Whether to show industry-specific fields based on AMS config'
    )
    
    # === Constraints and Validations ===
    @api.constrains('member_id')
    def _check_member_id_unique(self):
        """Ensure member ID is unique."""
        for record in self:
            if record.member_id:
                duplicate = self.search([
                    ('member_id', '=', record.member_id),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(_(
                        'Member ID %s already exists for %s'
                    ) % (record.member_id, duplicate.name))
    
    @api.depends('name', 'designation_ids', 'designation_other')
    def _compute_display_name_with_credentials(self):
        """Compute display name with credentials in preferred order."""
        for record in self:
            name = record.name or ''
            credentials = []
            
            # Add formal designations
            if record.designation_ids:
                credentials.extend(record.designation_ids.mapped('name'))
            
            # Add other designation
            if record.designation_other:
                credentials.append(record.designation_other)
            
            if credentials:
                record.display_name_with_credentials = f"{name}, {', '.join(credentials)}"
            else:
                record.display_name_with_credentials = name
    
    @api.depends()
    def _compute_industry_fields_visible(self):
        """Determine if industry-specific fields should be visible."""
        config = self.env['ams.config'].get_active_config()
        for record in self:
            record.industry_fields_visible = (
                config.enable_professional_category or 
                config.enable_credentials or
                config.enable_license_numbers
            )
    
    # === Auto-generation Methods ===
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate member ID if needed."""
        config = self.env['ams.config'].get_active_config()
        
        for vals in vals_list:
            # Auto-generate member ID if not provided and is_ams_member is True
            if vals.get('is_ams_member', False) and not vals.get('member_id'):
                vals['member_id'] = config.generate_member_id()
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to handle member ID generation."""
        # Generate member ID when setting is_ams_member to True
        if vals.get('is_ams_member') and not any(rec.member_id for rec in self):
            config = self.env['ams.config'].get_active_config()
            for record in self:
                if not record.member_id:
                    record.member_id = config.generate_member_id()
        
        return super().write(vals)
    
    # === Helper Methods ===
    def generate_member_id(self):
        """Manually generate member ID for this contact."""
        self.ensure_one()
        if self.member_id:
            raise UserError(_('Member ID already exists: %s') % self.member_id)
        
        config = self.env['ams.config'].get_active_config()
        self.member_id = config.generate_member_id()
        return self.member_id
    
    def get_primary_address_by_type(self, address_type):
        """Get primary address of specific type."""
        address = self.address_type_ids.filtered(
            lambda a: a.address_type_id.code == address_type and a.is_primary
        )
        return address[0] if address else False
    
    def get_all_relationships(self):
        """Get all relationships (both directions)."""
        return self.relationship_ids + self.reverse_relationship_ids
    
    @api.model
    def search_by_member_id(self, member_id):
        """Search for partner by member ID."""
        return self.search([('member_id', '=', member_id)], limit=1)


class ResPartnerAddress(models.Model):
    """Additional addresses for partners with type classification."""
    
    _name = 'res.partner.address'
    _description = 'Partner Additional Address'
    _order = 'sequence, address_type_id'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        ondelete='cascade'
    )
    
    address_type_id = fields.Many2one(
        'ams.lookup',
        string='Address Type',
        domain="[('category', '=', 'address_type'), ('active', '=', True)]",
        required=True
    )
    
    name = fields.Char(
        string='Address Name',
        help='Optional name for this address'
    )
    
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP/Postal Code')
    country_id = fields.Many2one('res.country', string='Country')
    
    is_primary = fields.Boolean(
        string='Primary',
        default=False,
        help='Primary address of this type'
    )
    
    is_billing = fields.Boolean(
        string='Billing Address',
        default=False
    )
    
    is_shipping = fields.Boolean(
        string='Shipping Address', 
        default=False
    )
    
    is_residential = fields.Boolean(
        string='Residential Address',
        default=False
    )
    
    is_corporate = fields.Boolean(
        string='Corporate Address',
        default=False
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.constrains('is_primary', 'address_type_id', 'partner_id')
    def _check_single_primary_per_type(self):
        """Ensure only one primary address per type per partner."""
        for record in self:
            if record.is_primary:
                other_primary = self.search([
                    ('partner_id', '=', record.partner_id.id),
                    ('address_type_id', '=', record.address_type_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_primary:
                    raise ValidationError(_(
                        'Only one primary address per type is allowed. '
                        'Partner %s already has a primary %s address.'
                    ) % (record.partner_id.name, record.address_type_id.name))