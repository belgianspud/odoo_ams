# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


class ResPartnerIndividual(models.Model):
    _inherit = 'res.partner'

    # Identity & Demographics
    member_id = fields.Char(
        string="Member ID", 
        readonly=True,
        copy=False,
        help="Unique member identifier auto-generated upon first save"
    )
    first_name = fields.Char(
        string="First Name",
        help="Individual's first/given name"
    )
    middle_name = fields.Char(
        string="Middle Name",
        help="Individual's middle name or initial"
    )
    last_name = fields.Char(
        string="Last Name",
        help="Individual's last/family name"
    )
    suffix = fields.Char(
        string="Suffix",
        help="Name suffix (Jr., Sr., III, etc.)"
    )
    nickname = fields.Char(
        string="Nickname",
        help="Preferred name for informal communications"
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], string="Gender")
    date_of_birth = fields.Date(
        string="Date of Birth",
        help="Individual's birth date for demographics and age verification"
    )

    # Contact Information Extensions
    business_phone = fields.Char(
        string="Business Phone",
        help="Primary business phone number"
    )
    mobile_phone = fields.Char(
        string="Mobile Phone", 
        help="Mobile/cell phone number"
    )
    secondary_email = fields.Char(
        string="Secondary Email",
        help="Backup email address"
    )

    # Address Extensions
    primary_address_type = fields.Selection([
        ('residential', 'Residential'),
        ('business', 'Business'),
        ('billing', 'Billing'),
        ('shipping', 'Shipping')
    ], string="Primary Address Type", default='residential')
    
    secondary_address_line1 = fields.Char(string="Secondary Address Line 1")
    secondary_address_line2 = fields.Char(string="Secondary Address Line 2")
    secondary_address_city = fields.Char(string="Secondary City")
    secondary_address_state_id = fields.Many2one(
        'res.country.state', 
        string="Secondary State"
    )
    secondary_address_zip = fields.Char(string="Secondary ZIP")
    secondary_address_country_id = fields.Many2one(
        'res.country', 
        string="Secondary Country"
    )
    secondary_address_type = fields.Selection([
        ('residential', 'Residential'),
        ('business', 'Business'),
        ('billing', 'Billing'),
        ('shipping', 'Shipping')
    ], string="Secondary Address Type", default='residential')

    # System Fields
    legacy_contact_id = fields.Char(
        string="Legacy Contact ID",
        help="Original contact ID from legacy system for data migration"
    )
    portal_id = fields.Char(
        string="Portal ID", 
        readonly=True,
        help="Portal user identifier"
    )
    
    # Original join date - will be set by membership modules
    original_join_date = fields.Date(
        string="Original Join Date", 
        readonly=True,
        help="Date when member first joined the association"
    )

    # REMOVED FIELDS THAT REFERENCE NON-EXISTENT MODELS
    # These will be added by higher layer modules:
    # - is_member (computed field referencing ams.participation)
    # - member_type_id (references ams.member.type)  
    # - member_status_id (references ams.member.status)
    # - paid_through_date (computed field referencing ams.participation)
    # - primary_membership_id (references ams.participation)

    # Computed Fields
    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name',
        store=True
    )
    
    formatted_address = fields.Text(
        string="Formatted Address",
        compute='_compute_formatted_address'
    )
    
    formatted_secondary_address = fields.Text(
        string="Formatted Secondary Address", 
        compute='_compute_formatted_secondary_address'
    )

    @api.depends('first_name', 'last_name', 'middle_name', 'suffix', 'name')
    def _compute_display_name(self):
        """Compute display name from name components or fall back to name field"""
        for partner in self:
            if partner.first_name or partner.last_name:
                name_parts = []
                if partner.first_name:
                    name_parts.append(partner.first_name)
                if partner.middle_name:
                    name_parts.append(partner.middle_name)
                if partner.last_name:
                    name_parts.append(partner.last_name)
                if partner.suffix:
                    name_parts.append(partner.suffix)
                partner.display_name = ' '.join(name_parts)
            else:
                partner.display_name = partner.name or ''

    @api.depends('street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _compute_formatted_address(self):
        """Format primary address for display"""
        for partner in self:
            address_parts = []
            if partner.street:
                address_parts.append(partner.street)
            if partner.street2:
                address_parts.append(partner.street2)
            
            city_line = []
            if partner.city:
                city_line.append(partner.city)
            if partner.state_id:
                city_line.append(partner.state_id.name)
            if partner.zip:
                city_line.append(partner.zip)
            if city_line:
                address_parts.append(', '.join(city_line))
                
            if partner.country_id:
                address_parts.append(partner.country_id.name)
                
            partner.formatted_address = '\n'.join(address_parts)

    @api.depends('secondary_address_line1', 'secondary_address_line2', 
                 'secondary_address_city', 'secondary_address_state_id', 
                 'secondary_address_zip', 'secondary_address_country_id')
    def _compute_formatted_secondary_address(self):
        """Format secondary address for display"""
        for partner in self:
            address_parts = []
            if partner.secondary_address_line1:
                address_parts.append(partner.secondary_address_line1)
            if partner.secondary_address_line2:
                address_parts.append(partner.secondary_address_line2)
            
            city_line = []
            if partner.secondary_address_city:
                city_line.append(partner.secondary_address_city)
            if partner.secondary_address_state_id:
                city_line.append(partner.secondary_address_state_id.name)
            if partner.secondary_address_zip:
                city_line.append(partner.secondary_address_zip)
            if city_line:
                address_parts.append(', '.join(city_line))
                
            if partner.secondary_address_country_id:
                address_parts.append(partner.secondary_address_country_id.name)
                
            partner.formatted_secondary_address = '\n'.join(address_parts)

    @api.model
    def create(self, vals):
        """Override create to auto-generate member ID"""
        if not vals.get('member_id') and not vals.get('is_company'):
            # Only generate member ID for individuals, and only if sequence exists
            try:
                vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
            except:
                # If sequence doesn't exist yet, skip for now
                pass
        return super().create(vals)

    def _format_phone_number(self, phone):
        """Basic phone number formatting - can be enhanced by other modules"""
        if not phone:
            return phone
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        # Basic US formatting
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone

    @api.onchange('business_phone')
    def _onchange_business_phone(self):
        """Format business phone on change"""
        if self.business_phone:
            self.business_phone = self._format_phone_number(self.business_phone)

    @api.onchange('mobile_phone')
    def _onchange_mobile_phone(self):
        """Format mobile phone on change"""
        if self.mobile_phone:
            self.mobile_phone = self._format_phone_number(self.mobile_phone)

    @api.onchange('first_name', 'last_name', 'middle_name', 'suffix')
    def _onchange_name_components(self):
        """Update name field when components change"""
        if self.first_name or self.last_name:
            name_parts = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.middle_name:
                name_parts.append(self.middle_name)
            if self.last_name:
                name_parts.append(self.last_name)
            if self.suffix:
                name_parts.append(self.suffix)
            self.name = ' '.join(name_parts)

    @api.constrains('secondary_email')
    def _check_secondary_email(self):
        """Validate secondary email format"""
        for partner in self:
            if partner.secondary_email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, partner.secondary_email):
                    raise models.ValidationError(
                        "Please enter a valid secondary email address."
                    )