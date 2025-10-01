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

    # ... [Keep all the field definitions exactly as they are until _create_default_product method]
    
    # Basic Information
    name = fields.Char('Member Type', required=True, tracking=True)
    code = fields.Char('Code', required=True, tracking=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True, tracking=True)

    # Product Class Configuration
    product_class = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter Membership'),
        ('subscription', 'Subscription'),
        ('publication', 'Publication'),
        ('exhibits', 'Exhibits'),
        ('advertising', 'Advertising'),
        ('donations', 'Donations'),
        ('courses', 'Courses'),
        ('sponsorship', 'Sponsorship'),
        ('event_booth', 'Event Booth'),
        ('newsletter', 'Newsletter'),
        ('services', 'Services')
    ], string='Product Class', default='membership', required=True, tracking=True,
       help="Defines the type of product/service this member type represents")

    # Membership Period Configuration
    membership_period_type = fields.Selection([
        ('calendar', 'Calendar Year'),
        ('anniversary', 'Anniversary'),
        ('rolling', 'Rolling Period')
    ], string='Period Type', tracking=True,
       help="How membership periods are calculated. Leave blank to use system default.")
    
    recurrence_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
        ('one_time', 'One Time')
    ], string='Recurrence Period', default='annual', tracking=True,
       help="How often this membership renews")

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

    # Multiple Membership Rules
    allow_multiple_active = fields.Boolean('Allow Multiple Active', 
                                         help="Allow multiple active memberships of this type per member")
    max_active_per_member = fields.Integer('Max Active Per Member', default=1,
                                         help="Maximum active memberships of this type per member (0 = unlimited)")
    
    # Upgrade/Downgrade Rules
    allow_upgrades = fields.Boolean('Allow Upgrades', default=True,
                                  help="Allow upgrading to higher tier memberships")
    allow_downgrades = fields.Boolean('Allow Downgrades', default=True,
                                    help="Allow downgrading to lower tier memberships")
    upgrade_member_type_ids = fields.Many2many('ams.member.type', 
                                             'member_type_upgrade_rel',
                                             'from_type_id', 'to_type_id',
                                             string='Upgrade Options',
                                             help="Member types this can be upgraded to")

    # Prorating Configuration
    enable_prorating = fields.Boolean('Enable Pro-rating', default=True,
                                     help="Calculate pro-rated pricing for partial periods")
    prorate_on_upgrade = fields.Boolean('Pro-rate on Upgrade', default=True,
                                      help="Apply pro-rating when upgrading")
    prorate_on_downgrade = fields.Boolean('Pro-rate on Downgrade', default=True,
                                        help="Apply pro-rating when downgrading")

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

    # Approval Workflow
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

    # Product Integration
    default_product_id = fields.Many2one('product.template', 'Default Product',
                                       help="Default product for this member type")
    auto_create_product = fields.Boolean('Auto Create Product', default=False,
                                       help="Automatically create product when member type is created")

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
        """Override create to handle validations and auto-create product"""
        # Ensure code is uppercase
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].upper()
        
        # Set currency if not provided
        if 'currency_id' not in vals or not vals['currency_id']:
            vals['currency_id'] = self._get_default_currency_id()
        
        member_type = super().create(vals)
        
        # Auto-create product if enabled
        if member_type.auto_create_product:
            member_type._create_default_product()
        
        return member_type

    def write(self, vals):
        """Override write to handle validations"""
        # Ensure code is uppercase
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].upper()
        
        return super().write(vals)

    def _get_product_class_label(self):
        """Get the human-readable label for product_class"""
        self.ensure_one()
        # Get the selection field definition
        selection_dict = dict(self._fields['product_class'].selection)
        return selection_dict.get(self.product_class, self.product_class)

    def _create_default_product(self):
        """Create default product for this member type"""
        self.ensure_one()
        
        if self.default_product_id:
            return self.default_product_id
        
        # Get the product class label
        product_class_label = self._get_product_class_label()
        
        product_vals = {
            'name': f"{self.name} - {product_class_label}",
            'type': 'service',
            'list_price': self.base_annual_fee,
            'description_sale': self.description or f"{self.name} membership",
        }
        
        try:
            product = self.env['product.template'].create(product_vals)
            self.default_product_id = product.id
            _logger.info(f"Created product {product.name} for member type {self.name}")
            return product
        except Exception as e:
            _logger.warning(f"Failed to create default product for member type {self.name}: {str(e)}")
            return False

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
                'message': _('Application management will be available in future updates.'),
                'type': 'info'
            }
        }

    def action_create_default_product(self):
        """Manually create default product"""
        self.ensure_one()
        
        if self.default_product_id:
            raise UserError(_("Default product already exists for this member type."))
        
        product = self._create_default_product()
        if product:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Default product created successfully.'),
                    'type': 'success'
                }
            }
        else:
            raise UserError(_("Failed to create default product."))

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

    def check_multiple_membership_rules(self, partner):
        """Check if partner can have multiple memberships of this type"""
        self.ensure_one()
        
        if self.allow_multiple_active:
            if self.max_active_per_member > 0:
                # Check current count for this member type
                current_count = self.env['membership.membership'].search_count([
                    ('partner_id', '=', partner.id),
                    ('membership_type_id.member_type_id', '=', self.id),
                    ('state', '=', 'active')
                ])
                
                if current_count >= self.max_active_per_member:
                    return False, _("Maximum number of active memberships of this type reached.")
            
            return True, _("Multiple memberships allowed.")
        else:
            # Check if partner has any active membership of this type
            existing = self.env['membership.membership'].search([
                ('partner_id', '=', partner.id),
                ('membership_type_id.member_type_id', '=', self.id),
                ('state', '=', 'active')
            ], limit=1)
            
            if existing:
                return False, _("Member already has an active membership of this type.")
            
            return True, _("No conflicts found.")

    def get_effective_grace_period(self):
        """Get effective grace period days (override or system default)"""
        self.ensure_one()
        if self.grace_period_override:
            return self.grace_period_days
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.grace_period_days if settings else 30

    def get_effective_membership_period_type(self):
        """Get effective membership period type (override or system default)"""
        self.ensure_one()
        if self.membership_period_type:
            return self.membership_period_type
        else:
            settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
            return settings.default_membership_period_type if settings else 'calendar'

    def calculate_membership_end_date(self, start_date=None):
        """Calculate membership end date based on duration and period type"""
        self.ensure_one()
        if not start_date:
            start_date = fields.Date.today()
        
        settings = self.env['ams.settings'].search([('active', '=', True)], limit=1)
        if settings:
            return settings.calculate_membership_end_date(
                start_date, 
                self.get_effective_membership_period_type(),
                self.membership_duration
            )
        else:
            # Fallback calculation
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

    def get_recurrence_display(self):
        """Get user-friendly recurrence display"""
        self.ensure_one()
        recurrence_map = {
            'monthly': _('Monthly'),
            'quarterly': _('Quarterly'),
            'semi_annual': _('Semi-Annual'),
            'annual': _('Annual'),
            'biennial': _('Biennial'),
            'one_time': _('One Time')
        }
        return recurrence_map.get(self.recurrence_period, self.recurrence_period)

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

    @api.constrains('max_active_per_member')
    def _check_max_active_per_member(self):
        """Validate max active per member"""
        for record in self:
            if record.max_active_per_member < 0:
                raise ValidationError(_("Max active per member cannot be negative. Use 0 for unlimited."))

    @api.constrains('reference_letters_required')
    def _check_reference_letters(self):
        """Validate reference letters required"""
        for record in self:
            if record.reference_letters_required < 0:
                raise ValidationError(_("Reference letters required cannot be negative."))
            if record.reference_letters_required > 10:
                raise ValidationError(_("Reference letters required seems excessive (>10)."))

    @api.constrains('upgrade_member_type_ids')
    def _check_upgrade_circular_reference(self):
        """Prevent circular upgrade references"""
        for record in self:
            if record.id in record.upgrade_member_type_ids.ids:
                raise ValidationError(_("Member type cannot upgrade to itself."))

    def copy(self, default=None):
        """Override copy to handle unique code"""
        if default is None:
            default = {}
        if 'code' not in default:
            default['code'] = _("%s_COPY") % self.code
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super().copy(default)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_members(self):
        """Prevent deletion if members exist"""
        for record in self:
            if record.member_count > 0:
                raise UserError(_("Cannot delete member type '%s' because it has active members.") % record.name)