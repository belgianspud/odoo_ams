# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipMembership(models.Model):
    _name = 'ams.membership.membership'
    _description = 'Regular Association Memberships'
    _inherit = 'ams.membership.base'
    _rec_name = 'name'

    # Membership-specific fields
    membership_level = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('lifetime', 'Lifetime')
    ], string='Membership Level', compute='_compute_membership_level', store=True)
    
    voting_rights = fields.Boolean('Voting Rights', related='member_type_id.voting_rights', readonly=True)
    directory_access = fields.Boolean('Directory Access', related='member_type_id.directory_access', readonly=True)
    event_discounts = fields.Boolean('Event Discounts', related='member_type_id.event_discounts', readonly=True)
    
    # Professional Information Enhancement
    professional_designation = fields.Char('Professional Designation', 
                                         related='partner_id.professional_designation', readonly=True)
    license_number = fields.Char('License Number', related='partner_id.license_number', readonly=True)
    specialty_area = fields.Char('Specialty Area', related='partner_id.specialty_area', readonly=True)
    years_experience = fields.Integer('Years Experience', related='partner_id.years_experience', readonly=True)
    
    # Membership Benefits
    committee_memberships = fields.Text('Committee Memberships')
    special_privileges = fields.Text('Special Privileges')
    mentorship_program = fields.Boolean('Mentorship Program Access', default=False)
    
    # Chapter Relationships
    chapter_membership_ids = fields.One2many('ams.membership.chapter', 'primary_membership_id', 
                                           'Chapter Memberships',
                                           help="Chapter memberships linked to this primary membership")
    chapter_count = fields.Integer('Chapter Count', compute='_compute_chapter_count')
    
    # Education and CE Credits
    ce_credits_required = fields.Float('CE Credits Required', related='member_type_id.min_experience_years', readonly=True)
    ce_credits_earned = fields.Float('CE Credits Earned', default=0.0)
    ce_credits_balance = fields.Float('CE Credits Balance', compute='_compute_ce_balance')
    
    # Membership Statistics
    total_renewals = fields.Integer('Total Renewals', compute='_compute_membership_stats')
    membership_tenure_years = fields.Float('Membership Tenure (Years)', compute='_compute_membership_stats')
    first_membership_date = fields.Date('First Membership Date', compute='_compute_membership_stats')
    
    # Dues and Financial
    dues_current = fields.Boolean('Dues Current', compute='_compute_dues_status')
    last_payment_date = fields.Date('Last Payment Date', compute='_compute_dues_status')
    next_dues_amount = fields.Float('Next Dues Amount', compute='_compute_next_dues')

    @api.depends('member_type_id')
    def _compute_membership_level(self):
        """Determine membership level based on member type"""
        level_mapping = {
            'HON': 'lifetime',  # Honorary
            'RET': 'standard',  # Retired
            'CORP': 'premium',  # Corporate
            'INTL': 'standard', # International
            'REG': 'premium',   # Regular
            'ASC': 'standard',  # Associate
            'STU': 'basic',     # Student
        }
        
        for membership in self:
            if membership.member_type_id and membership.member_type_id.code:
                membership.membership_level = level_mapping.get(
                    membership.member_type_id.code, 'standard'
                )
            else:
                membership.membership_level = 'standard'

    def _compute_chapter_count(self):
        """Count active chapter memberships"""
        for membership in self:
            membership.chapter_count = len(membership.chapter_membership_ids.filtered(
                lambda c: c.state in ['active', 'grace']
            ))

    def _compute_ce_balance(self):
        """Compute CE credits balance"""
        for membership in self:
            membership.ce_credits_balance = membership.ce_credits_earned - membership.ce_credits_required

    def _compute_membership_stats(self):
        """Compute membership statistics"""
        for membership in self:
            # Count all memberships for this partner (including this one)
            all_memberships = self.search([
                ('partner_id', '=', membership.partner_id.id),
                ('product_id.product_tmpl_id.product_class', '=', 'membership')
            ], order='start_date asc')
            
            membership.total_renewals = len(all_memberships) - 1  # Exclude original
            
            if all_memberships:
                first_membership = all_memberships[0]
                membership.first_membership_date = first_membership.start_date
                
                # Calculate tenure from first membership to now/end date
                if membership.state in ['active', 'grace']:
                    end_date = fields.Date.today()
                else:
                    end_date = membership.end_date
                
                years = (end_date - first_membership.start_date).days / 365.25
                membership.membership_tenure_years = round(years, 1)
            else:
                membership.first_membership_date = False
                membership.membership_tenure_years = 0

    def _compute_dues_status(self):
        """Compute dues payment status"""
        for membership in self:
            if membership.invoice_id and membership.invoice_id.payment_state == 'paid':
                membership.dues_current = True
                membership.last_payment_date = membership.invoice_id.invoice_date_due
            else:
                membership.dues_current = False
                membership.last_payment_date = False

    def _compute_next_dues(self):
        """Compute next dues amount based on current product pricing"""
        for membership in self:
            if membership.can_be_renewed:
                membership.next_dues_amount = membership.product_id.lst_price
            else:
                membership.next_dues_amount = 0

    # Override Methods
    def write(self, vals):
        """Override to handle membership-specific updates"""
        result = super().write(vals)
        
        # Update partner primary membership info when this membership changes
        if 'state' in vals or 'member_type_id' in vals:
            for membership in self:
                if membership.state == 'active':
                    membership.partner_id.write({
                        'member_type_id': membership.member_type_id.id if membership.member_type_id else membership.partner_id.member_type_id.id,
                    })
        
        return result

    # Action Methods
    def action_view_chapters(self):
        """View chapter memberships for this member"""
        self.ensure_one()
        return {
            'name': _('Chapter Memberships: %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.chapter',
            'view_mode': 'list,form',
            'domain': [('primary_membership_id', '=', self.id)],
            'context': {
                'default_primary_membership_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_create_chapter_membership(self):
        """Create a new chapter membership"""
        self.ensure_one()
        
        if self.state not in ['active', 'grace']:
            raise UserError(_("Primary membership must be active to create chapter memberships."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Chapter Membership'),
            'res_model': 'ams.membership.chapter',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_primary_membership_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_start_date': fields.Date.today(),
            }
        }

    def action_view_subscriptions(self):
        """View all subscriptions for this member"""
        self.ensure_one()
        return {
            'name': _('Subscriptions: %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.subscription',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_record_ce_credits(self):
        """Open wizard to record CE credits"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record CE Credits'),
            'res_model': 'ams.ce.credits.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_update_benefits(self):
        """Update membership benefits and privileges"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Membership Benefits'),
            'res_model': 'ams.membership.benefits.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
            }
        }

    def action_generate_membership_certificate(self):
        """Generate membership certificate"""
        self.ensure_one()
        
        if self.state not in ['active', 'grace']:
            raise UserError(_("Membership certificate can only be generated for active memberships."))
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'ams_membership_core.membership_certificate_report',
            'report_type': 'qweb-pdf',
            'data': {'membership_id': self.id},
            'context': {'active_id': self.id},
        }

    def action_membership_history(self):
        """View membership history for this partner"""
        self.ensure_one()
        return {
            'name': _('Membership History: %s') % self.partner_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.membership',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'search_default_group_by_state': 1},
        }

    # Membership-specific Methods
    def update_ce_credits(self, credits, description="Manual entry"):
        """Update CE credits for this membership"""
        self.ensure_one()
        
        if credits < 0:
            raise UserError(_("CE credits cannot be negative."))
        
        # Log CE credit entry
        self.message_post(
            body=_("CE Credits Updated: +%.1f credits - %s") % (credits, description),
            message_type='notification'
        )
        
        self.ce_credits_earned += credits

    def check_renewal_eligibility(self):
        """Check if membership is eligible for renewal with detailed reasons"""
        self.ensure_one()
        
        issues = []
        
        if self.state not in ['active', 'grace', 'lapsed']:
            issues.append(_("Membership status must be active, grace, or lapsed"))
        
        if self.next_membership_id:
            issues.append(_("Membership has already been renewed"))
        
        if not self.product_id.product_tmpl_id.auto_renewal_eligible:
            issues.append(_("Product is not eligible for renewal"))
        
        if not self.dues_current and self.state != 'lapsed':
            issues.append(_("Dues are not current"))
        
        # Check CE credits if required
        if self.ce_credits_required > 0 and self.ce_credits_balance < 0:
            issues.append(_("Insufficient CE credits (%.1f required, %.1f earned)") % 
                         (self.ce_credits_required, self.ce_credits_earned))
        
        return {
            'eligible': len(issues) == 0,
            'issues': issues
        }

    def get_membership_benefits(self):
        """Get list of membership benefits"""
        self.ensure_one()
        benefits = []
        
        if self.voting_rights:
            benefits.append(_("Voting Rights"))
        if self.directory_access:
            benefits.append(_("Member Directory Access"))
        if self.event_discounts:
            benefits.append(_("Event Discounts"))
        if self.mentorship_program:
            benefits.append(_("Mentorship Program Access"))
        
        # Add chapter access
        if self.chapter_count > 0:
            benefits.append(_("Chapter Membership Access (%d chapters)") % self.chapter_count)
        
        # Add level-specific benefits
        if self.membership_level == 'premium':
            benefits.extend([
                _("Premium Member Resources"),
                _("Priority Event Registration"),
                _("Advanced Networking Features")
            ])
        elif self.membership_level == 'lifetime':
            benefits.extend([
                _("Lifetime Membership Benefits"),
                _("No Renewal Required"),
                _("Legacy Member Recognition")
            ])
        
        return benefits

    # Constraints
    @api.constrains('ce_credits_earned')
    def _check_ce_credits(self):
        """Validate CE credits"""
        for membership in self:
            if membership.ce_credits_earned < 0:
                raise ValidationError(_("CE credits earned cannot be negative."))

    @api.constrains('product_id')
    def _check_product_class(self):
        """Ensure product is a membership product"""
        for membership in self:
            if membership.product_id.product_tmpl_id.product_class != 'membership':
                raise ValidationError(_("Product must be a membership product class."))

    @api.constrains('partner_id', 'state')
    def _check_single_active_membership(self):
        """Ensure only one active primary membership per partner (configurable)"""
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if settings and not settings.allow_multiple_active_memberships:
            for membership in self:
                if membership.state in ['active', 'grace']:
                    other_active = self.search([
                        ('partner_id', '=', membership.partner_id.id),
                        ('state', 'in', ['active', 'grace']),
                        ('id', '!=', membership.id)
                    ])
                    
                    if other_active:
                        raise ValidationError(_(
                            "Partner %s already has an active primary membership. "
                            "Multiple active memberships are not allowed."
                        ) % membership.partner_id.name)