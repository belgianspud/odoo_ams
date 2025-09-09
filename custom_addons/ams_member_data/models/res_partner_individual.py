# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta


class ResPartnerMember(models.Model):
    """
    AMS-specific extensions to res.partner for membership management.
    Focuses only on association-specific fields, leveraging Odoo's existing contact features.
    """
    _inherit = 'res.partner'

    # === CORE AMS MEMBERSHIP FIELDS (Universal for Individuals & Organizations) ===
    
    member_id = fields.Char(
        string="Member ID", 
        readonly=True,
        copy=False,
        index=True,
        help="Unique member identifier auto-generated upon first save"
    )
    
    is_member = fields.Boolean(
        string="Is Member",
        default=False,
        index=True,
        help="Quick filter: is this contact a current or past member?"
    )
    
    membership_status = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('former', 'Former Member'),
        ('honorary', 'Honorary'),
        ('suspended', 'Suspended'),
    ], string="Membership Status", default='prospect', index=True)
    
    # === MEMBERSHIP DATES ===
    
    join_date = fields.Date(
        string="Current Join Date",
        help="Start date of current membership term"
    )
    
    member_since = fields.Date(
        string="Member Since", 
        readonly=True,
        help="Original date when first became a member"
    )
    
    renewal_date = fields.Date(
        string="Renewal Date",
        help="Expected membership renewal date"
    )
    
    paid_through_date = fields.Date(
        string="Paid Through",
        help="Membership coverage end date"
    )
    
    # === MEMBER CLASSIFICATION ===
    
    # Note: member_type_id will be added by ams_member_types module
    # This shows the pattern - we only add what doesn't exist in base Odoo
    
    # === ENGAGEMENT & CONTRIBUTIONS ===
    
    engagement_score = fields.Float(
        string="Engagement Score",
        default=0.0,
        help="Calculated engagement metric based on events, committees, etc."
    )
    
    last_payment_date = fields.Date(
        string="Last Payment Date",
        help="Date of most recent dues or contribution payment"
    )
    
    last_payment_amount = fields.Monetary(
        string="Last Payment Amount",
        help="Amount of most recent payment"
    )
    
    total_contributions = fields.Monetary(
        string="Total Contributions",
        default=0.0,
        help="Lifetime total of all contributions/donations"
    )
    
    donor_level = fields.Selection([
        ('none', 'Non-Donor'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'), 
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string="Donor Level", default='none')
    
    # === ORGANIZATION-SPECIFIC FIELDS ===
    
    # Corporate identity (only relevant for organizations)
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
        ('other', 'Other')
    ], string="Organization Type")
    
    industry_sector = fields.Char(
        string="Industry Sector",
        help="Primary industry or sector"
    )
    
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
    
    # === INDIVIDUAL-SPECIFIC FIELDS ===
    
    # Professional credentials (only relevant for individuals)
    credentials = fields.Text(
        string="Professional Credentials",
        help="Professional licenses, certifications, degrees"
    )
    
    specialties = fields.Text(
        string="Areas of Specialty",
        help="Professional areas of expertise or interest"
    )
    
    # === SYSTEM & INTEGRATION FIELDS ===
    
    legacy_contact_id = fields.Char(
        string="Legacy Contact ID",
        help="Original contact ID from legacy system for data migration"
    )
    
    portal_access = fields.Boolean(
        string="Portal Access",
        default=False,
        help="Has access to member portal"
    )
    
    # === COMPUTED FIELDS ===
    
    membership_duration_days = fields.Integer(
        string="Membership Duration (Days)",
        compute='_compute_membership_duration',
        help="Days since first became a member"
    )
    
    days_until_renewal = fields.Integer(
        string="Days Until Renewal",
        compute='_compute_days_until_renewal',
        help="Days until membership renewal is due"
    )
    
    is_renewal_due = fields.Boolean(
        string="Renewal Due",
        compute='_compute_is_renewal_due',
        help="Is membership renewal currently due?"
    )

    @api.depends('member_since')
    def _compute_membership_duration(self):
        """Calculate how long someone has been a member"""
        today = date.today()
        for partner in self:
            if partner.member_since:
                delta = today - partner.member_since
                partner.membership_duration_days = delta.days
            else:
                partner.membership_duration_days = 0

    @api.depends('renewal_date')
    def _compute_days_until_renewal(self):
        """Calculate days until renewal is due"""
        today = date.today()
        for partner in self:
            if partner.renewal_date:
                delta = partner.renewal_date - today
                partner.days_until_renewal = delta.days
            else:
                partner.days_until_renewal = 0

    @api.depends('renewal_date', 'membership_status')
    def _compute_is_renewal_due(self):
        """Determine if renewal is currently due"""
        today = date.today()
        for partner in self:
            if (partner.renewal_date and 
                partner.membership_status in ['active', 'grace'] and
                partner.renewal_date <= today + timedelta(days=30)):
                partner.is_renewal_due = True
            else:
                partner.is_renewal_due = False

    @api.model
    def create(self, vals):
        """Override create to auto-generate member ID and set member_since"""
        # Auto-generate member ID if this will be a member
        if not vals.get('member_id') and vals.get('is_member'):
            try:
                vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
                # Set member_since if not provided but is_member is True
                if not vals.get('member_since'):
                    vals['member_since'] = fields.Date.today()
            except:
                # If sequence doesn't exist yet, skip for now
                pass
        return super().create(vals)

    def write(self, vals):
        """Override write to handle membership status changes"""
        # If becoming a member for the first time, set member_since and generate ID
        for partner in self:
            if (vals.get('is_member') and not partner.is_member and 
                not partner.member_since):
                vals['member_since'] = fields.Date.today()
                if not partner.member_id:
                    try:
                        vals['member_id'] = self.env['ir.sequence'].next_by_code('ams.member.id')
                    except:
                        pass
        return super().write(vals)

    @api.constrains('year_established')
    def _check_year_established(self):
        """Validate year established is reasonable"""
        current_year = date.today().year
        for partner in self:
            if (partner.year_established and 
                (partner.year_established < 1800 or partner.year_established > current_year)):
                raise models.ValidationError(
                    f"Year established must be between 1800 and {current_year}"
                )

    def action_make_member(self):
        """Action to convert a prospect to a member"""
        self.ensure_one()
        if not self.is_member:
            self.write({
                'is_member': True,
                'membership_status': 'active',
                'join_date': fields.Date.today(),
            })

    def action_renew_membership(self):
        """Action to renew membership"""
        self.ensure_one()
        if self.membership_status in ['active', 'grace', 'lapsed']:
            # Basic renewal logic - can be enhanced by other modules
            new_renewal_date = fields.Date.today() + timedelta(days=365)
            self.write({
                'membership_status': 'active',
                'join_date': fields.Date.today(),
                'renewal_date': new_renewal_date,
            })