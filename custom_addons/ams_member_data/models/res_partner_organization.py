# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


class ResPartnerOrganization(models.Model):
    _inherit = 'res.partner'

    # Corporate Identity
    acronym = fields.Char(
        string="Acronym",
        help="Common abbreviation or acronym for the organization"
    )
    # REMOVED: website_url field - now using built-in 'website' field
    tin_number = fields.Char(
        string="TIN Number",
        help="Tax Identification Number"
    )
    ein_number = fields.Char(
        string="EIN Number", 
        help="Employer Identification Number"
    )
    
    # Organization Type
    organization_type = fields.Selection([
        ('corporation', 'Corporation'),
        ('nonprofit', 'Non-profit'),
        ('government', 'Government'),
        ('educational', 'Educational Institution'),
        ('healthcare', 'Healthcare Organization'),
        ('association', 'Professional Association'),
        ('partnership', 'Partnership'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('other', 'Other')
    ], string="Organization Type")
    
    # Industry Classification
    industry_sector = fields.Char(
        string="Industry Sector",
        help="Primary industry or sector"
    )
    naics_code = fields.Char(
        string="NAICS Code",
        help="North American Industry Classification System code"
    )
    
    # Business Details
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
    
    # Portal and Access Management
    portal_primary_contact_id = fields.Many2one(
        'res.partner', 
        string="Portal Primary Contact",
        domain="[('parent_id', '=', id), ('is_company', '=', False)]",
        help="Primary contact person for portal access and communications"
    )
    
    # REMOVED FIELDS THAT REFERENCE NON-EXISTENT MODELS
    # These will be added by higher layer modules:
    # - available_seats (computed field referencing ams.enterprise.subscription)
    # - assigned_seats (computed field referencing ams.enterprise.subscription)
    # - total_seats (computed field referencing ams.enterprise.subscription)
    # - exhibitor_points (computed field referencing ams.event models)
    
    # Computed Fields
    employee_ids = fields.One2many(
        'res.partner', 
        'parent_id', 
        string="Employees",
        domain="[('is_company', '=', False)]"
    )
    employee_count_computed = fields.Integer(
        string="Employee Count",
        compute='_compute_employee_count',
        store=True,
        help="Count of linked employee records"
    )
    
    # Legacy Integration
    legacy_contact_id = fields.Char(
        string="Legacy Contact ID",
        help="Original contact ID from legacy system for data migration"
    )
    
    # Display name computation for organizations
    display_name = fields.Char(
        string="Display Name",
        compute='_compute_display_name_org',
        store=True
    )

    @api.depends('name', 'acronym')
    def _compute_display_name_org(self):
        """Compute display name for organizations"""
        for partner in self:
            if partner.is_company:
                if partner.acronym and partner.name:
                    partner.display_name = f"{partner.name} ({partner.acronym})"
                else:
                    partner.display_name = partner.name or ''
            else:
                # For individuals, use the standard computation
                partner.display_name = partner.name or ''

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        """Compute number of linked employees"""
        for partner in self:
            if partner.is_company:
                partner.employee_count_computed = len(partner.employee_ids)
            else:
                partner.employee_count_computed = 0

    @api.model
    def create(self, vals):
        """Override create to handle organization-specific logic"""
        if vals.get('is_company') and not vals.get('member_id'):
            # Generate member ID for organizations too, if sequence exists
            try:
                vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
            except:
                # If sequence doesn't exist yet, skip for now
                pass
        return super().create(vals)

    @api.constrains('website')
    def _check_website_url(self):
        """Validate website URL format"""
        for partner in self:
            if partner.website:
                url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
                if not re.match(url_pattern, partner.website):
                    raise models.ValidationError(
                        "Please enter a valid website URL (including http:// or https://)"
                    )

    @api.constrains('ein_number')
    def _check_ein_format(self):
        """Validate EIN number format (US format: XX-XXXXXXX)"""
        for partner in self:
            if partner.ein_number:
                ein_pattern = r'^\d{2}-\d{7}$'
                if not re.match(ein_pattern, partner.ein_number):
                    raise models.ValidationError(
                        "EIN number must be in format XX-XXXXXXX (e.g., 12-3456789)"
                    )

    @api.constrains('year_established')
    def _check_year_established(self):
        """Validate year established is reasonable"""
        for partner in self:
            if partner.year_established:
                current_year = fields.Date.today().year
                if partner.year_established < 1800 or partner.year_established > current_year:
                    raise models.ValidationError(
                        f"Year established must be between 1800 and {current_year}"
                    )

    @api.onchange('website')
    def _onchange_website_url(self):
        """Auto-format website URL"""
        if self.website and not self.website.startswith(('http://', 'https://')):
            self.website = 'https://' + self.website

    def action_view_employees(self):
        """Action to view organization employees"""
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
            }
        }