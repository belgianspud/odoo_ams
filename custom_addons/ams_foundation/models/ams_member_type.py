# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMemberType(models.Model):
    _name = 'ams.member.type'
    _description = 'Association Member Types'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char('Member Type', required=True, tracking=True)
    code = fields.Char('Code', required=True, tracking=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)

    # Pricing and Duration
    base_annual_fee = fields.Float('Base Annual Fee', default=0.0, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency')
    membership_duration = fields.Integer('Membership Duration (Days)', default=365,
                                       help="Number of days the membership is valid")

    # Grace Period Override
    grace_period_override = fields.Boolean('Override Grace Period',
                                         help="Use custom grace period instead of system default")
    grace_period_days = fields.Integer('Grace Period (Days)', default=30,
                                     help="Days after expiration before moving to lapsed status")

    # Membership Features
    requires_approval = fields.Boolean('Requires Approval', default=False, tracking=True,
                                     help="Membership applications require manual approval")
    auto_renewal = fields.Boolean('Auto Renewal Eligible', default=True, tracking=True,
                                help="Members can set up automatic renewal")
    voting_rights = fields.Boolean('Voting Rights', default=True, tracking=True)
    directory_access = fields.Boolean('Directory Access', default=True,
                                    help="Can access member directory")
    event_discounts = fields.Boolean('Event Discounts', default=True,
                                    help="Eligible for member event pricing")

    # Eligibility Requirements
    requires_license = fields.Boolean('Requires Professional License', default=False)
    min_experience_years = fields.Integer('Minimum Experience (Years)', default=0)
    education_requirements = fields.Text('Education Requirements')
    age_restrictions = fields.Char('Age Restrictions')

    # Application Process (when requires_approval is True)
    application_fee = fields.Float('Application Fee', default=0.0)
    application_form_required = fields.Boolean('Application Form Required', default=True)
    reference_letters_required = fields.Integer('Reference Letters Required', default=0)
    interview_required = fields.Boolean('Interview Required', default=False)

    # Approval Workflow - Changed to Char field to avoid missing model reference
    approval_committee_id = fields.Char('Approval Committee', 
                                       help="Committee responsible for approvals (free text for now)")
    approval_voting_required = fields.Boolean('Approval Voting Required', default=False)
    approval_threshold = fields.Float('Approval Threshold (%)', default=50.0,
                                    help="Percentage of votes required for approval")

    # Geographic and Quantity Restrictions
    geographic_restrictions = fields.Boolean('Geographic Restrictions', default=False)
    allowed_countries = fields.Many2many('res.country', string='Allowed Countries')
    allowed_states = fields.Many2many('res.country.state', string='Allowed States/Provinces')
    max_members = fields.Integer('Maximum Members', default=0,
                               help="0 = unlimited")
    waiting_list_enabled = fields.Boolean('Waiting List Enabled', default=False)
    renewal_restrictions = fields.Text('Renewal Restrictions')

    # Rich Text Fields
    eligibility_criteria = fields.Html('Eligibility Criteria',
                                      help="Detailed eligibility requirements")
    benefits_description = fields.Html('Benefits Description',
                                      help="List of benefits and privileges")

    # Computed Fields
    member_count = fields.Integer('Active Members', compute='_compute_member_count', store=True)
    application_count = fields.Integer('Pending Applications', compute='_compute_application_count')
    waiting_list_count = fields.Integer('Waiting List Count', compute='_compute_waiting_list_count')

    # Related Fields for Convenience
    current_members = fields.One2many('res.partner', 'member_type_id', 'Current Members',
                                    domain=[('is_member', '=', True), ('member_status', 'in', ['active', 'grace'])])

    @api.model
    def default_get(self, fields_list):
        """Override default_get to set currency safely"""
        res = super().default_get(fields_list)
        if 'currency_id' in fields_list and not res.get('currency_id'):
            res['currency_id'] = self._get_default_currency_id()
        return res

    def _get_default_currency_id(self):
        """Get default currency ID safely"""
        try:
            # Try to get company currency first
            if self.env.company and self.env.company.currency_id:
                return self.env.company.currency_id.id
        except:
            pass
        
        try:
            # Fallback to USD
            usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            if usd_currency:
                return usd_currency.id
        except:
            pass
        
        try:
            # Last resort - get any currency
            any_currency = self.env['res.currency'].search([], limit=1)
            if any_currency:
                return any_currency.id
        except:
            pass
        
        return False

    @api.depends('current_members')
    def _compute_member_count(self):
        """Compute active member count"""
        for member_type in self:
            member_type.member_count = len(member_type.current_members)

    def _compute_application_count(self):
        """Compute pending application count"""
        # Placeholder - will be implemented when application module is added
        for member_type in self:
            member_type.application_count = 0

    def _compute_waiting_list_count(self):
        """Compute waiting list count"""
        # Placeholder - will be implemented when waiting list functionality is added
        for member_type in self:
            member_type.waiting_list_count = 0

    @api.model
    def create(self, vals):
        """Override create to handle validations"""
        # Ensure code is uppercase
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].upper()
        
        # Set currency if not provided
        if 'currency_id' not in vals or not vals['currency_id']:
            vals['currency_id'] = self._get_default_currency_id()
        
        return super().create(vals)

    def write(self, vals):
        """Override write to handle validations"""
        # Ensure code is uppercase
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].upper()
        
        return super().write(vals)

    def name_get(self):
        """Custom name_get to show code in parentheses"""
        result = []
        for record in self:
            if record.code:
                name = f"{record.name} ({record.code})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search to include code"""
        if args is None:
            args = []
        
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def action_view_members(self):
        """View members of this type"""
        self.ensure_one()
        return {
            'name': _('Members: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('member_type_id', '=', self.id), ('is_member', '=', True)],
            'context': {
                'default_is_member': True,
                'default_member_type_id': self.id,
                'search_default_active_members': 1
            },
        }

    def action_view_applications(self):
        """View applications for this member type"""
        self.ensure_one()
        # Placeholder - will be implemented when application module is added
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Applications'),
                'message': _('Application management will be available in the membership module.'),
                'type': 'info'
            }
        }

    def check_eligibility(self, partner):
        """Check if a partner is eligible for this member type"""
        self.ensure_one()
        errors = []

        # Check license requirement
        if self.requires_license and not partner.license_number:
            errors.append(_("Professional license is required for this member type."))

        # Check experience requirement
        if self.min_experience_years > 0:
            if not partner.years_experience or partner.years_experience < self.min_experience_years:
                errors.append(_("Minimum %d years of experience required.") % self.min_experience_years)

        # Check age restrictions
        if self.age_restrictions and partner.birthdate:
            # This would need more complex logic based on age_restrictions format
            pass

        # Check geographic restrictions
        if self.geographic_restrictions:
            if self.allowed_countries and partner.country_id not in self.allowed_countries:
                errors.append(_("Member must be located in an allowed country."))
            if self.allowed_states and partner.state_id not in self.allowed_states:
                errors.append(_("Member must be located in an allowed state/province."))

        # Check member limit
        if self.max_members > 0 and self.member_count >= self.max_members:
            if not self.waiting_list_enabled:
                errors.append(_("Maximum number of members reached for this type."))
            else:
                # Could add to waiting list
                pass

        return errors

    def get_effective_grace_period(self):
        """Get effective grace period days (override or system default)"""
        self.ensure_one()
        if self.grace_period_override:
            return self.grace_period_days
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.grace_period_days if settings else 30

    def calculate_membership_end_date(self, start_date=None):
        """Calculate membership end date based on duration"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        from datetime import timedelta
        return start_date + timedelta(days=self.membership_duration)

    def get_pricing_info(self):
        """Get formatted pricing information"""
        self.ensure_one()
        if self.base_annual_fee == 0:
            return _("Free")
        else:
            currency_symbol = self.currency_id.symbol if self.currency_id else "$"
            return f"{currency_symbol}{self.base_annual_fee:,.2f}"

    def toggle_active(self):
        """Toggle active status with validation"""
        for record in self:
            if record.active and record.member_count > 0:
                raise UserError(_("Cannot archive member type that has active members."))
            record.active = not record.active

    # Constraints and Validations
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure member type codes are unique"""
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Member type code must be unique. '%s' already exists.") % record.code)

    @api.constrains('base_annual_fee')
    def _check_annual_fee(self):
        """Validate annual fee"""
        for record in self:
            if record.base_annual_fee < 0:
                raise ValidationError(_("Annual fee cannot be negative."))

    @api.constrains('membership_duration')
    def _check_membership_duration(self):
        """Validate membership duration"""
        for record in self:
            if record.membership_duration <= 0:
                raise ValidationError(_("Membership duration must be greater than 0 days."))
            if record.membership_duration > 3650:  # 10 years
                raise ValidationError(_("Membership duration cannot exceed 10 years."))

    @api.constrains('grace_period_days')
    def _check_grace_period(self):
        """Validate grace period"""
        for record in self:
            if record.grace_period_override and record.grace_period_days < 0:
                raise ValidationError(_("Grace period cannot be negative."))
            if record.grace_period_override and record.grace_period_days > 365:
                raise ValidationError(_("Grace period cannot exceed 365 days."))

    @api.constrains('min_experience_years')
    def _check_experience_years(self):
        """Validate minimum experience years"""
        for record in self:
            if record.min_experience_years < 0:
                raise ValidationError(_("Minimum experience years cannot be negative."))
            if record.min_experience_years > 70:
                raise ValidationError(_("Minimum experience years seems unrealistic (>70 years)."))

    @api.constrains('application_fee')
    def _check_application_fee(self):
        """Validate application fee"""
        for record in self:
            if record.application_fee < 0:
                raise ValidationError(_("Application fee cannot be negative."))

    @api.constrains('approval_threshold')
    def _check_approval_threshold(self):
        """Validate approval threshold"""
        for record in self:
            if record.approval_voting_required:
                if record.approval_threshold <= 0 or record.approval_threshold > 100:
                    raise ValidationError(_("Approval threshold must be between 0 and 100 percent."))

    @api.constrains('max_members')
    def _check_max_members(self):
        """Validate maximum members"""
        for record in self:
            if record.max_members < 0:
                raise ValidationError(_("Maximum members cannot be negative. Use 0 for unlimited."))

    @api.constrains('reference_letters_required')
    def _check_reference_letters(self):
        """Validate reference letters required"""
        for record in self:
            if record.reference_letters_required < 0:
                raise ValidationError(_("Reference letters required cannot be negative."))
            if record.reference_letters_required > 10:
                raise ValidationError(_("Reference letters required seems excessive (>10)."))

    def copy(self, default=None):
        """Override copy to handle unique code"""
        if default is None:
            default = {}
        if 'code' not in default:
            default['code'] = _("%s (copy)") % self.code
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super().copy(default)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_members(self):
        """Prevent deletion if members exist"""
        for record in self:
            if record.member_count > 0:
                raise UserError(_("Cannot delete member type '%s' because it has active members.") % record.name)