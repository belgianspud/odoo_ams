import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartnerIndividual(models.Model):
    """Extend res.partner with individual member specific fields."""
    _inherit = 'res.partner'

    # ==========================================
    # IDENTITY & DEMOGRAPHICS
    # ==========================================
    
    member_id = fields.Char(
        string='Member ID',
        readonly=True,
        copy=False,
        index=True,
        help='Auto-generated unique member identifier'
    )
    
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_is_member',
        store=True,
        help='Current member status based on active participations'
    )
    
    member_type_id = fields.Many2one(
        'ams.member.type',
        string='Member Type',
        help='Member classification (Individual, Student, Retired, etc.)'
    )
    
    member_status_id = fields.Many2one(
        'ams.member.status', 
        string='Member Status',
        help='Current membership status'
    )
    
    legacy_contact_id = fields.Char(
        string='Legacy Contact ID',
        help='Reference ID from legacy system imports'
    )
    
    first_name = fields.Char(
        string='First Name',
        help='Given name'
    )
    
    middle_name = fields.Char(
        string='Middle Name',
        help='Middle name or initial'
    )
    
    last_name = fields.Char(
        string='Last Name',
        help='Family/surname'
    )
    
    suffix = fields.Char(
        string='Suffix',
        help='Name suffix (Jr, Sr, III, etc.)'
    )
    
    nickname = fields.Char(
        string='Nickname',
        help='Preferred name for communications'
    )
    
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'), 
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], string='Gender', help='Gender identification')
    
    date_of_birth = fields.Date(
        string='Date of Birth',
        help='Birth date for demographics and age calculations'
    )
    
    # ==========================================
    # MEMBERSHIP TRACKING
    # ==========================================
    
    original_join_date = fields.Date(
        string='Original Join Date',
        help='Date of first membership (set once, never changed)'
    )
    
    paid_through_date = fields.Date(
        string='Paid Through Date',
        compute='_compute_paid_through_date',
        store=True,
        help='Membership expiration based on current participation'
    )
    
    primary_membership_id = fields.Many2one(
        'ams.participation',
        string='Primary Membership',
        compute='_compute_primary_membership',
        store=True,
        help='Current active membership participation'
    )
    
    # ==========================================
    # ENHANCED CONTACT INFORMATION
    # ==========================================
    
    business_phone = fields.Char(
        string='Business Phone',
        help='Work phone number (E.164 format preferred)'
    )
    
    mobile_phone = fields.Char(
        string='Mobile Phone',
        help='Mobile phone number (E.164 format preferred)'
    )
    
    secondary_email = fields.Char(
        string='Secondary Email',
        help='Additional email address'
    )
    
    primary_address_type = fields.Selection([
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
        ('residential', 'Residential'),
        ('business', 'Business'),
        ('primary', 'Primary'),
        ('other', 'Other')
    ], string='Primary Address Type', default='primary')
    
    # Secondary Address Fields
    secondary_address_line1 = fields.Char(
        string='Secondary Address Line 1',
        help='Alternative address line 1'
    )
    
    secondary_address_line2 = fields.Char(
        string='Secondary Address Line 2', 
        help='Alternative address line 2'
    )
    
    secondary_address_city = fields.Char(
        string='Secondary City',
        help='Alternative address city'
    )
    
    secondary_address_state_id = fields.Many2one(
        'res.country.state',
        string='Secondary State',
        help='Alternative address state/province'
    )
    
    secondary_address_zip = fields.Char(
        string='Secondary ZIP',
        help='Alternative address postal code'
    )
    
    secondary_address_country_id = fields.Many2one(
        'res.country',
        string='Secondary Country',
        help='Alternative address country'
    )
    
    secondary_address_type = fields.Selection([
        ('billing', 'Billing'),
        ('shipping', 'Shipping'), 
        ('residential', 'Residential'),
        ('business', 'Business'),
        ('primary', 'Primary'),
        ('other', 'Other')
    ], string='Secondary Address Type')
    
    # ==========================================
    # PORTAL & SYSTEM INTEGRATION
    # ==========================================
    
    portal_id = fields.Char(
        string='Portal ID',
        help='Portal access identifier'
    )
    
    current_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deceased', 'Deceased'),
        ('never_member', 'Never Member')
    ], string='Current Status', compute='_compute_current_status', store=True)

    # ==========================================
    # COMPUTED FIELDS & METHODS
    # ==========================================

    @api.depends('first_name', 'middle_name', 'last_name', 'suffix', 'member_type_id')
    def _compute_display_name(self):
        """Override display name computation to use proper name components."""
        for partner in self:
            if partner.member_type_id and partner.member_type_id.is_individual:
                # Build name from components for individuals
                name_parts = []
                if partner.first_name:
                    name_parts.append(partner.first_name)
                if partner.middle_name:
                    name_parts.append(partner.middle_name)
                if partner.last_name:
                    name_parts.append(partner.last_name)
                if partner.suffix:
                    name_parts.append(partner.suffix)
                
                if name_parts:
                    partner.display_name = ' '.join(name_parts)
                else:
                    partner.display_name = partner.name or 'Unknown'
            else:
                super(ResPartnerIndividual, partner)._compute_display_name()

    @api.depends('member_status_id')
    def _compute_is_member(self):
        """Compute member status based on member status."""
        # This will be enhanced when ams_participation module is installed
        for partner in self:
            # For now, base it on member_status_id
            if partner.member_status_id and partner.member_status_id.is_active:
                partner.is_member = True
            else:
                partner.is_member = False

    @api.depends('member_status_id')
    def _compute_paid_through_date(self):
        """Compute latest paid through date from active participations."""
        # This will be enhanced when ams_participation module is installed
        for partner in self:
            # For now, set to None - will be computed by participation module
            partner.paid_through_date = False

    @api.depends('member_status_id')
    def _compute_primary_membership(self):
        """Identify the primary active membership."""
        # This will be enhanced when ams_participation module is installed
        for partner in self:
            # For now, set to None - will be computed by participation module
            partner.primary_membership_id = False

    @api.depends('member_status_id', 'is_member')
    def _compute_current_status(self):
        """Compute overall current status."""
        for partner in self:
            if partner.member_status_id and partner.member_status_id.code == 'deceased':
                partner.current_status = 'deceased'
            elif partner.is_member:
                partner.current_status = 'active'
            elif partner.member_id:  # Has member ID but not active
                partner.current_status = 'inactive'
            else:
                partner.current_status = 'never_member'

    @api.onchange('first_name', 'middle_name', 'last_name', 'suffix', 'member_type_id')
    def _onchange_name_components(self):
        """Auto-populate name field from components for individuals."""
        if self.member_type_id and self.member_type_id.is_individual:
            name_parts = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.middle_name:
                name_parts.append(self.middle_name)  
            if self.last_name:
                name_parts.append(self.last_name)
            if self.suffix:
                name_parts.append(self.suffix)
                
            if name_parts:
                self.name = ' '.join(name_parts)

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_participations(self):
        """Open member participations view."""
        self.ensure_one()
        # This will be enhanced when ams_participation module is installed
        return {
            'name': f'Participations - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'help': '<p>No participations found. Install ams_participation module to manage member participations.</p>'
        }

    # ==========================================
    # VALIDATION & CONSTRAINTS
    # ==========================================

    @api.constrains('business_phone', 'mobile_phone', 'phone')
    def _validate_phone_format(self):
        """Validate phone number formats."""
        phone_regex = re.compile(r'^\+?[1-9]\d{1,14}$')  # Basic E.164 validation
        
        for partner in self:
            phones_to_check = [
                ('business_phone', partner.business_phone),
                ('mobile_phone', partner.mobile_phone),
                ('phone', partner.phone)
            ]
            
            for field_name, phone_value in phones_to_check:
                if phone_value and not phone_regex.match(phone_value.replace(' ', '').replace('-', '')):
                    raise ValidationError(
                        f"Invalid phone format in {field_name}. Use international format: +1234567890"
                    )

    @api.constrains('email', 'secondary_email')
    def _validate_email_format(self):
        """Validate email formats."""
        email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for partner in self:
            if partner.email and not email_regex.match(partner.email):
                raise ValidationError("Primary email format is invalid.")
            if partner.secondary_email and not email_regex.match(partner.secondary_email):
                raise ValidationError("Secondary email format is invalid.")

    @api.constrains('member_type_id', 'is_company')
    def _validate_member_type_consistency(self):
        """Ensure member type matches individual/company setting."""
        for partner in self:
            if partner.member_type_id:
                if partner.member_type_id.is_individual and partner.is_company:
                    raise ValidationError(
                        "Individual member types cannot be assigned to companies."
                    )
                if partner.member_type_id.is_organization and not partner.is_company:
                    raise ValidationError(
                        "Organization member types can only be assigned to companies."
                    )

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate member IDs and set defaults."""
        for vals in vals_list:
            # Generate member ID if this is going to be a member
            if vals.get('member_type_id') and not vals.get('member_id'):
                try:
                    vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
                except Exception:
                    # Fallback if sequence doesn't exist yet
                    pass
            
            # Set original join date if not provided
            if vals.get('member_type_id') and not vals.get('original_join_date'):
                vals['original_join_date'] = fields.Date.context_today(self)
                
        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle member type changes.""" 
        # Generate member ID when member type is assigned
        if vals.get('member_type_id'):
            for record in self:
                if not record.member_id:
                    try:
                        vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
                        break  # Only set once for the batch
                    except Exception:
                        # Fallback if sequence doesn't exist yet
                        pass
            
        # Set original join date when first becoming a member
        if vals.get('member_type_id'):
            for record in self:
                if not record.original_join_date:
                    vals['original_join_date'] = fields.Date.context_today(self)
                    break  # Only set once for the batch
            
        return super().write(vals)