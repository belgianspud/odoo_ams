import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartnerOrganization(models.Model):
    """Extend res.partner with organization member specific fields."""
    _inherit = 'res.partner'

    # ==========================================
    # CORPORATE IDENTITY
    # ==========================================
    
    acronym = fields.Char(
        string='Acronym',
        help='Company abbreviation or short name'
    )
    
    website_url = fields.Char(
        string='Website',
        help='Company website URL'
    )
    
    tin_number = fields.Char(
        string='TIN',
        help='Tax Identification Number'
    )
    
    ein_number = fields.Char(
        string='EIN', 
        help='Employer Identification Number'
    )
    
    # ==========================================
    # PORTAL & ENTERPRISE MANAGEMENT
    # ==========================================
    
    portal_primary_contact_id = fields.Many2one(
        'res.partner',
        string='Portal Primary Contact',
        domain="[('parent_id', '=', id), ('is_company', '=', False)]",
        help='Employee who manages the organization portal access'
    )
    
    # ==========================================
    # ENTERPRISE SUBSCRIPTION SEATS (COMPUTED)
    # ==========================================
    
    available_seats = fields.Integer(
        string='Available Seats',
        compute='_compute_enterprise_seats',
        store=True,
        help='Enterprise subscription seats available for assignment'
    )
    
    assigned_seats = fields.Integer(
        string='Assigned Seats', 
        compute='_compute_enterprise_seats',
        store=True,
        help='Enterprise subscription seats currently assigned'
    )
    
    total_seats = fields.Integer(
        string='Total Seats',
        compute='_compute_enterprise_seats',
        store=True,
        help='Total enterprise subscription seats purchased'
    )
    
    # ==========================================
    # BUSINESS METRICS
    # ==========================================
    
    exhibitor_points = fields.Float(
        string='Exhibitor Points',
        compute='_compute_exhibitor_points',
        store=True,
        help='Points earned from event exhibition participation'
    )
    
    # ==========================================
    # RELATIONSHIPS
    # ==========================================
    
    employee_ids = fields.One2many(
        'res.partner',
        'parent_id',
        string='Employees',
        domain=[('is_company', '=', False)],
        help='Individual members who are employees of this organization'
    )
    
    # Note: These relationships will be added by dependent modules
    # corporate_benefit_ids - added by ams_benefits_engine
    # sponsorship_ids - added by ams_event_sponsorship

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('employee_ids', 'employee_ids.is_member')
    def _compute_enterprise_seats(self):
        """Compute enterprise seat statistics from subscriptions."""
        for partner in self:
            if not partner.is_company:
                partner.available_seats = 0
                partner.assigned_seats = 0
                partner.total_seats = 0
                continue
                
            # This computation will be enhanced by ams_enterprise_seats module
            # For now, we'll compute basic stats from employee relationships
            total_employees = len(partner.employee_ids)
            member_employees = len(partner.employee_ids.filtered('is_member'))
            
            # Basic computation - will be enhanced by enterprise module
            partner.total_seats = total_employees if total_employees > 0 else 0
            partner.assigned_seats = member_employees
            partner.available_seats = partner.total_seats - partner.assigned_seats

    @api.depends('employee_ids')
    def _compute_exhibitor_points(self):
        """Compute exhibitor points from event participation."""
        for partner in self:
            if not partner.is_company:
                partner.exhibitor_points = 0.0
                continue
                
            # This computation will be enhanced by ams_event_sponsorship module
            # For now, return 0 - will be enhanced by event modules
            partner.exhibitor_points = 0.0

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_employees(self):
        """Open a view showing all employees of this organization."""
        self.ensure_one()
        return {
            'name': f'Employees - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id), ('is_company', '=', False)],
            'context': {
                'default_parent_id': self.id,
                'default_is_company': False,
            },
        }

    def action_view_member_employees(self):
        """Open a view showing only member employees."""
        self.ensure_one()
        return {
            'name': f'Member Employees - {self.name}',
            'type': 'ir.actions.act_window', 
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [
                ('parent_id', '=', self.id),
                ('is_company', '=', False),
                ('is_member', '=', True)
            ],
            'context': {
                'default_parent_id': self.id,
                'default_is_company': False,
            },
        }

    def action_view_participations(self):
        """Open organization participations view."""
        self.ensure_one()
        # This will be enhanced when ams_participation module is installed
        return {
            'name': f'Participations - {self.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
            'help': '<p>No participations found. Install ams_participation module to manage organization participations.</p>'
        }

    def action_manage_enterprise_seats(self):
        """Open enterprise seat management for this organization."""
        self.ensure_one()
        if not self.is_company:
            raise ValidationError("Only organizations can manage enterprise seats.")
        
        return {
            'name': f'Enterprise Seats - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.enterprise.seat',
            'view_mode': 'tree,form',
            'domain': [('organization_id', '=', self.id)],
            'context': {
                'default_organization_id': self.id,
            },
            'help': '<p>No enterprise seats configured. Install ams_enterprise_seats module to manage seat allocations.</p>'
        }

    # ==========================================
    # VALIDATION & CONSTRAINTS  
    # ==========================================

    @api.constrains('website_url')
    def _validate_website_url(self):
        """Validate website URL format."""
        url_regex = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        for partner in self:
            if partner.website_url and not url_regex.match(partner.website_url):
                raise ValidationError(
                    "Website URL format is invalid. Use format: https://example.com"
                )

    @api.constrains('tin_number', 'ein_number')
    def _validate_tax_numbers(self):
        """Validate tax identification numbers."""
        for partner in self:
            # TIN validation (basic US format: XX-XXXXXXX or 9-10 digits)
            if partner.tin_number:
                tin_clean = partner.tin_number.replace('-', '').replace(' ', '')
                if not tin_clean.isdigit() or len(tin_clean) not in [9, 10]:
                    raise ValidationError(
                        "TIN format is invalid. Use format: XX-XXXXXXX"
                    )
            
            # EIN validation (US format: XX-XXXXXXX or 9 digits)
            if partner.ein_number:
                ein_clean = partner.ein_number.replace('-', '').replace(' ', '')
                if not ein_clean.isdigit() or len(ein_clean) != 9:
                    raise ValidationError(
                        "EIN format is invalid. Use format: XX-XXXXXXX"
                    )

    @api.constrains('portal_primary_contact_id')
    def _validate_portal_contact(self):
        """Ensure portal contact is an employee of this organization."""
        for partner in self:
            if partner.portal_primary_contact_id:
                if partner.portal_primary_contact_id.parent_id != partner:
                    raise ValidationError(
                        "Portal primary contact must be an employee of this organization."
                    )
                if partner.portal_primary_contact_id.is_company:
                    raise ValidationError(
                        "Portal primary contact must be an individual, not a company."
                    )

    @api.constrains('acronym')
    def _validate_acronym_length(self):
        """Validate acronym length and format."""
        for partner in self:
            if partner.acronym:
                if len(partner.acronym) > 20:
                    raise ValidationError("Acronym cannot be longer than 20 characters.")
                if not partner.acronym.replace(' ', '').isalnum():
                    raise ValidationError("Acronym should contain only letters and numbers.")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    @api.model
    def get_organizations_with_enterprise_seats(self):
        """Return organizations that have enterprise subscriptions."""
        # This method will be enhanced by ams_enterprise_seats module
        return self.search([
            ('is_company', '=', True),
            ('total_seats', '>', 0)
        ])

    def assign_enterprise_seat(self, employee_partner):
        """Assign an enterprise seat to an employee."""
        # This method will be enhanced by ams_enterprise_seats module
        self.ensure_one()
        if not self.is_company:
            raise ValidationError("Only organizations can assign enterprise seats.")
            
        if employee_partner.parent_id != self:
            raise ValidationError("Can only assign seats to employees of this organization.")
            
        # Basic implementation - will be enhanced by enterprise module
        if self.available_seats <= 0:
            raise ValidationError("No available enterprise seats to assign.")
            
        # Logic for actual seat assignment will be in ams_enterprise_seats module
        return True

    def release_enterprise_seat(self, employee_partner):
        """Release an enterprise seat from an employee."""
        # This method will be enhanced by ams_enterprise_seats module
        self.ensure_one()
        if not self.is_company:
            raise ValidationError("Only organizations can release enterprise seats.")
            
        if employee_partner.parent_id != self:
            raise ValidationError("Can only release seats from employees of this organization.")
            
        # Logic for actual seat release will be in ams_enterprise_seats module
        return True

    def get_employee_count_by_status(self):
        """Get count of employees by member status."""
        self.ensure_one()
        if not self.is_company:
            return {}
        
        result = {}
        for employee in self.employee_ids:
            status = employee.member_status_id.name if employee.member_status_id else 'No Status'
            result[status] = result.get(status, 0) + 1
        
        return result

    def get_enterprise_utilization_rate(self):
        """Calculate enterprise seat utilization rate."""
        self.ensure_one()
        if not self.is_company or self.total_seats == 0:
            return 0.0
        
        return (self.assigned_seats / self.total_seats) * 100.0

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('name', 'acronym')
    def _onchange_name_acronym(self):
        """Auto-generate acronym from name if not provided."""
        if self.name and not self.acronym and self.is_company:
            # Create acronym from first letter of each word
            words = self.name.split()
            acronym = ''.join([word[0].upper() for word in words if word])
            if len(acronym) <= 10:  # Keep acronyms reasonable length
                self.acronym = acronym

    @api.onchange('website')
    def _onchange_website(self):
        """Auto-populate website_url from website field."""
        if self.website and not self.website_url:
            # Ensure proper URL format
            if not self.website.startswith(('http://', 'https://')):
                self.website_url = 'https://' + self.website
            else:
                self.website_url = self.website

    @api.onchange('is_company')
    def _onchange_is_company(self):
        """Clear organization-specific fields when changing to individual."""
        if not self.is_company:
            self.acronym = False
            self.website_url = False
            self.tin_number = False
            self.ein_number = False
            self.portal_primary_contact_id = False

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_primary_contact_info(self):
        """Get primary contact information for this organization."""
        self.ensure_one()
        if not self.is_company:
            return {}
        
        primary_contact = self.portal_primary_contact_id
        if not primary_contact:
            # Try to find a primary contact from employees
            primary_contact = self.employee_ids.filtered(lambda e: e.email)[:1]
        
        if primary_contact:
            return {
                'name': primary_contact.name,
                'email': primary_contact.email,
                'phone': primary_contact.phone or primary_contact.mobile,
                'title': primary_contact.function or 'Contact'
            }
        
        return {}

    def get_organization_summary(self):
        """Get a summary of organization details."""
        self.ensure_one()
        if not self.is_company:
            return {}
        
        return {
            'name': self.name,
            'acronym': self.acronym,
            'website': self.website_url,
            'member_status': self.member_status_id.name if self.member_status_id else 'No Status',
            'is_member': self.is_member,
            'employee_count': len(self.employee_ids),
            'member_employee_count': len(self.employee_ids.filtered('is_member')),
            'enterprise_seats': {
                'total': self.total_seats,
                'assigned': self.assigned_seats,
                'available': self.available_seats,
                'utilization_rate': self.get_enterprise_utilization_rate()
            },
            'primary_contact': self.get_primary_contact_info()
        }

    def format_organization_address(self, include_secondary=False):
        """Get formatted organization address."""
        self.ensure_one()
        if not self.is_company:
            return ''
        
        # Primary address
        address_parts = []
        if self.street:
            address_parts.append(self.street)
        if self.street2:
            address_parts.append(self.street2)
        
        city_state_zip = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state_id:
            city_state_zip.append(self.state_id.code or self.state_id.name)
        if self.zip:
            city_state_zip.append(self.zip)
        
        if city_state_zip:
            address_parts.append(', '.join(city_state_zip))
        
        if self.country_id:
            address_parts.append(self.country_id.name)
        
        return '\n'.join(address_parts)

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    def write(self, vals):
        """Override write to handle organization-specific updates."""
        # Auto-update website_url when website changes
        if 'website' in vals and vals['website'] and not vals.get('website_url'):
            website = vals['website']
            if not website.startswith(('http://', 'https://')):
                vals['website_url'] = 'https://' + website
            else:
                vals['website_url'] = website
        
        return super().write(vals)