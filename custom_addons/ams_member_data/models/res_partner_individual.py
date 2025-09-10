# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta
import re


class ResPartnerIndividual(models.Model):
    """
    AMS extensions to res.partner - ONLY adds association-specific fields.
    Leverages existing Odoo fields: name, email, phone, mobile, website, vat, 
    industry_id, category_id, parent_id, child_ids, function, title, etc.
    """
    _inherit = 'res.partner'

    # === CORE AMS MEMBERSHIP FIELDS (Universal - applies to both individuals & orgs) ===
    
    is_member = fields.Boolean(
        string="Is Member",
        default=False,
        index=True,
        help="Is this contact a current or past member?"
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
    
    # === ENGAGEMENT & CONTRIBUTIONS (Universal) ===
    
    engagement_score = fields.Float(
        string="Engagement Score",
        default=0.0,
        help="Calculated engagement metric"
    )
    
    last_payment_date = fields.Date(
        string="Last Payment Date",
        help="Most recent dues/contribution payment"
    )
    
    last_payment_amount = fields.Monetary(
        string="Last Payment Amount",
        help="Amount of most recent payment"
    )
    
    total_contributions = fields.Monetary(
        string="Total Contributions",
        default=0.0,
        help="Lifetime total contributions/donations"
    )
    
    donor_level = fields.Selection([
        ('none', 'Non-Donor'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'), 
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string="Donor Level", default='none')
    
    # === INDIVIDUAL-SPECIFIC ONLY ===
    
    date_of_birth = fields.Date(
        string="Date of Birth",
        help="Individual's birth date"
    )
    
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ], string="Gender")
    
    credentials = fields.Text(
        string="Professional Credentials",
        help="Licenses, certifications, degrees"
    )
    
    # === SYSTEM INTEGRATION ===
    
    legacy_contact_id = fields.Char(
        string="Legacy Contact ID",
        help="ID from previous system"
    )
    
    # === COMPUTED FIELDS ===
    
    member_id = fields.Char(
        string="Member ID",
        compute='_compute_member_id',
        inverse='_inverse_member_id',
        store=True,
        help="Formatted member ID using ref field"
    )
    
    membership_duration_days = fields.Integer(
        string="Membership Duration (Days)",
        compute='_compute_membership_duration'
    )
    
    days_until_renewal = fields.Integer(
        string="Days Until Renewal",
        compute='_compute_days_until_renewal'
    )
    
    is_renewal_due = fields.Boolean(
        string="Renewal Due",
        compute='_compute_is_renewal_due',
        store=True,
        help="Is membership renewal currently due?"
    )

    # === COMPUTE METHODS ===

    @api.depends('ref')
    def _compute_member_id(self):
        """Format ref field as member ID"""
        for partner in self:
            if partner.ref and partner.is_member:
                partner.member_id = f"M{partner.ref.zfill(6)}"
            else:
                partner.member_id = False
    
    def _inverse_member_id(self):
        """Store member ID back to ref field"""
        for partner in self:
            if partner.member_id and partner.member_id.startswith('M'):
                ref_value = partner.member_id[1:].lstrip('0') or '0'
                partner.ref = ref_value

    @api.depends('member_since')
    def _compute_membership_duration(self):
        """Calculate membership duration"""
        today = date.today()
        for partner in self:
            if partner.member_since:
                delta = today - partner.member_since
                partner.membership_duration_days = delta.days
            else:
                partner.membership_duration_days = 0

    @api.depends('renewal_date')
    def _compute_days_until_renewal(self):
        """Calculate days until renewal"""
        today = date.today()
        for partner in self:
            if partner.renewal_date:
                delta = partner.renewal_date - today
                partner.days_until_renewal = delta.days
            else:
                partner.days_until_renewal = 0

    @api.depends('renewal_date', 'membership_status')
    def _compute_is_renewal_due(self):
        """Determine if renewal is due"""
        today = date.today()
        for partner in self:
            if (partner.renewal_date and 
                partner.membership_status in ['active', 'grace'] and
                partner.renewal_date <= today + timedelta(days=30)):
                partner.is_renewal_due = True
            else:
                partner.is_renewal_due = False

    # === LIFECYCLE METHODS ===

    @api.model
    def create(self, vals):
        """Auto-generate member ID using sequence"""
        if vals.get('is_member') and not vals.get('ref'):
            try:
                sequence = self.env['ir.sequence'].next_by_code('ams.system.member.id')
                if sequence:
                    # Store sequence number in ref field (without M prefix)
                    vals['ref'] = sequence.replace('M', '').lstrip('0') or '1'
                if not vals.get('member_since'):
                    vals['member_since'] = fields.Date.today()
            except:
                pass
        return super().create(vals)

    def write(self, vals):
        """Handle membership status changes"""
        for partner in self:
            if (vals.get('is_member') and not partner.is_member and 
                not partner.member_since):
                vals['member_since'] = fields.Date.today()
                if not partner.ref:
                    try:
                        sequence = self.env['ir.sequence'].next_by_code('ams.system.member.id')
                        if sequence:
                            vals['ref'] = sequence.replace('M', '').lstrip('0') or '1'
                    except:
                        pass
        return super().write(vals)

    # === VALIDATION ===

    @api.constrains('email')
    def _check_email_format(self):
        """Validate email format using existing Odoo validation"""
        # Odoo already handles email validation, just ensure it's called
        super()._check_email_format() if hasattr(super(), '_check_email_format') else None

    # === ACTIONS ===

    def action_make_member(self):
        """Convert prospect to member"""
        self.ensure_one()
        if not self.is_member:
            self.write({
                'is_member': True,
                'membership_status': 'active',
                'join_date': fields.Date.today(),
            })

    def action_renew_membership(self):
        """Renew membership"""
        self.ensure_one()
        if self.membership_status in ['active', 'grace', 'lapsed']:
            new_renewal_date = fields.Date.today() + timedelta(days=365)
            self.write({
                'membership_status': 'active',
                'join_date': fields.Date.today(),
                'renewal_date': new_renewal_date,
            })