# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re
from datetime import date


class ResPartnerOrganization(models.Model):
    """
    Organization-specific AMS extensions to res.partner.
    Universal AMS fields (is_member, membership_status, etc.) are defined in 
    res_partner_individual.py to avoid duplication since both inherit res.partner.
    
    Leverages existing Odoo fields: name, website, vat, industry_id, parent_id, 
    child_ids, category_id, email, phone, address fields, etc.
    """
    _inherit = 'res.partner'

    # === ORGANIZATION IDENTITY ===
    
    acronym = fields.Char(
        string="Acronym",
        help="Common abbreviation for the organization"
    )
    
    organization_type = fields.Selection([
        ('corporation', 'Corporation'),
        ('nonprofit', 'Non-profit'),
        ('government', 'Government Agency'),
        ('educational', 'Educational Institution'),
        ('healthcare', 'Healthcare Organization'),
        ('association', 'Professional Association'),
        ('partnership', 'Partnership'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('other', 'Other')
    ], string="Organization Type", help="Legal/operational structure")
    
    # === BUSINESS DETAILS ===
    
    year_established = fields.Integer(
        string="Year Established",
        help="Year the organization was founded"
    )
    
    employee_count = fields.Integer(
        string="Number of Employees",
        help="Total number of employees"
    )
    
    annual_revenue = fields.Monetary(
        string="Annual Revenue",
        help="Approximate annual revenue"
    )
    
    # === TAX IDENTIFICATION ===
    # Note: Use existing 'vat' field for primary tax ID
    
    ein_number = fields.Char(
        string="EIN Number", 
        help="US Employer Identification Number (XX-XXXXXXX format)"
    )
    
    # === PORTAL & ACCESS MANAGEMENT ===
    
    portal_primary_contact_id = fields.Many2one(
        'res.partner', 
        string="Portal Primary Contact",
        domain="[('parent_id', '=', id), ('is_company', '=', False)]",
        help="Primary contact for portal access and communications"
    )
    
    # === COMPUTED FIELDS ===
    
    employee_count_computed = fields.Integer(
        string="Linked Employees",
        compute='_compute_employee_count_computed',
        store=True,
        help="Count of employee records linked to this organization"
    )
    
    display_name_org = fields.Char(
        string="Display Name with Acronym",
        compute='_compute_display_name_org',
        help="Organization name with acronym if available"
    )

    # === COMPUTE METHODS ===

    @api.depends('child_ids')
    def _compute_employee_count_computed(self):
        """Count linked employee contacts using existing child_ids"""
        for partner in self:
            if partner.is_company:
                # Count child contacts that are individuals (not companies)
                partner.employee_count_computed = len(
                    partner.child_ids.filtered(lambda c: not c.is_company)
                )
            else:
                partner.employee_count_computed = 0

    @api.depends('name', 'acronym')
    def _compute_display_name_org(self):
        """Compute display name with acronym for organizations"""
        for partner in self:
            if partner.is_company and partner.acronym and partner.name:
                partner.display_name_org = f"{partner.name} ({partner.acronym})"
            else:
                partner.display_name_org = partner.name or ''

    # === VALIDATION ===

    @api.constrains('website')
    def _check_website_url(self):
        """Validate website URL format"""
        for partner in self:
            if partner.website and partner.is_company:
                # Basic URL validation
                url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
                if not re.match(url_pattern, partner.website):
                    raise models.ValidationError(
                        "Please enter a valid website URL (including http:// or https://)"
                    )

    @api.constrains('ein_number')
    def _check_ein_format(self):
        """Validate EIN number format (US format: XX-XXXXXXX)"""
        for partner in self:
            if partner.ein_number and partner.is_company:
                ein_pattern = r'^\d{2}-\d{7}$'
                if not re.match(ein_pattern, partner.ein_number):
                    raise models.ValidationError(
                        "EIN number must be in format XX-XXXXXXX (e.g., 12-3456789)"
                    )

    @api.constrains('year_established')
    def _check_year_established(self):
        """Validate year established is reasonable"""
        for partner in self:
            if partner.year_established and partner.is_company:
                current_year = date.today().year
                if partner.year_established < 1800 or partner.year_established > current_year:
                    raise models.ValidationError(
                        f"Year established must be between 1800 and {current_year}"
                    )

    @api.constrains('employee_count')
    def _check_employee_count(self):
        """Validate employee count is reasonable"""
        for partner in self:
            if partner.employee_count and partner.is_company:
                if partner.employee_count < 0:
                    raise models.ValidationError("Employee count cannot be negative")
                if partner.employee_count > 10000000:  # 10 million seems reasonable max
                    raise models.ValidationError("Employee count seems unreasonably large")

    # === ONCHANGE METHODS ===

    @api.onchange('website')
    def _onchange_website_url(self):
        """Auto-format website URL"""
        if self.website and not self.website.startswith(('http://', 'https://')):
            self.website = 'https://' + self.website

    @api.onchange('ein_number')
    def _onchange_ein_number(self):
        """Auto-format EIN number"""
        if self.ein_number:
            # Remove all non-digits
            digits = re.sub(r'\D', '', self.ein_number)
            # Format as XX-XXXXXXX if we have 9 digits
            if len(digits) == 9:
                self.ein_number = f"{digits[:2]}-{digits[2:]}"

    # === ACTIONS ===

    def action_view_employees(self):
        """Action to view organization employees using existing child_ids"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f"Employees - {self.name}",
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id), ('is_company', '=', False)],
            'context': {
                'default_parent_id': self.id,
                'default_is_company': False,
                'default_is_member': False,  # Employees aren't automatically members
            }
        }

    def action_set_as_portal_contact(self):
        """Set selected employee as portal primary contact"""
        # This would be called from employee list view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Portal Contact',
            'res_model': 'res.partner',
            'view_mode': 'list',
            'domain': [('parent_id', '=', self.id), ('is_company', '=', False)],
            'context': {
                'portal_contact_selection': True,
                'organization_id': self.id,
            }
        }

    # === ORGANIZATION-SPECIFIC BUSINESS LOGIC ===

    def get_organization_summary(self):
        """Return organization summary for reports/dashboards"""
        self.ensure_one()
        return {
            'name': self.name,
            'acronym': self.acronym,
            'type': self.organization_type,
            'industry': self.industry_id.name if self.industry_id else '',
            'employees': self.employee_count or self.employee_count_computed,
            'revenue': self.annual_revenue,
            'established': self.year_established,
            'member_since': self.member_since,
            'membership_status': self.membership_status,
        }

    def update_employee_count_from_linked(self):
        """Sync employee_count field with actual linked employees"""
        for partner in self:
            if partner.is_company:
                linked_count = partner.employee_count_computed
                if linked_count > 0:
                    partner.employee_count = linked_count