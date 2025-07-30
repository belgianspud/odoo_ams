from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionBenefit(models.Model):
    _name = 'ams.subscription.benefit'
    _description = 'Subscription Benefit'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Benefit Name',
        required=True,
        help="Name of the membership benefit"
    )
    
    description = fields.Html(
        string='Description',
        help="Detailed description of this benefit"
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for display"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this benefit"
    )
    
    # Benefit Category
    category = fields.Selection([
        ('access', 'Access & Privileges'),
        ('discount', 'Discounts & Savings'),
        ('resource', 'Resources & Materials'),
        ('event', 'Events & Networking'),
        ('education', 'Education & Training'),
        ('publication', 'Publications & Newsletters'),
        ('certification', 'Certification & Credentials'),
        ('support', 'Support & Services'),
        ('other', 'Other')
    ], string='Category', default='access', required=True)
    
    # Benefit Type
    benefit_type = fields.Selection([
        ('included', 'Included'),
        ('discount', 'Discount Available'),
        ('exclusive', 'Exclusive Access'),
        ('priority', 'Priority Access'),
        ('free', 'Free Service'),
        ('reduced_rate', 'Reduced Rate')
    ], string='Benefit Type', default='included', required=True)
    
    # Membership Type Association
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        required=True,
        ondelete='cascade',
        help="Membership type this benefit belongs to"
    )
    
    # Value and Cost Information
    monetary_value = fields.Float(
        string='Monetary Value',
        digits='Product Price',
        help="Estimated monetary value of this benefit"
    )
    
    discount_percentage = fields.Float(
        string='Discount Percentage',
        digits='Discount',
        help="Discount percentage if applicable"
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price',
        help="Fixed discount amount if applicable"
    )
    
    # Benefit Details
    is_quantifiable = fields.Boolean(
        string='Quantifiable Benefit',
        default=False,
        help="Check if this benefit has measurable quantities"
    )
    
    quantity_limit = fields.Integer(
        string='Quantity Limit',
        help="Maximum number of times this benefit can be used (0 = unlimited)"
    )
    
    usage_period = fields.Selection([
        ('per_membership', 'Per Membership Period'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('one_time', 'One Time Only')
    ], string='Usage Period', default='per_membership')
    
    # Eligibility and Requirements
    eligibility_requirements = fields.Html(
        string='Eligibility Requirements',
        help="Requirements to access this benefit"
    )
    
    requires_application = fields.Boolean(
        string='Requires Application',
        default=False,
        help="Check if member must apply to receive this benefit"
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help="Check if benefit requires approval before use"
    )
    
    # Geographic Restrictions
    geographic_restriction = fields.Boolean(
        string='Geographic Restrictions',
        default=False,
        help="Check if benefit has geographic limitations"
    )
    
    allowed_country_ids = fields.Many2many(
        'res.country',
        'benefit_country_rel',
        'benefit_id',
        'country_id',
        string='Allowed Countries',
        help="Countries where this benefit is available"
    )
    
    allowed_state_ids = fields.Many2many(
        'res.country.state',
        'benefit_state_rel',
        'benefit_id',
        'state_id',
        string='Allowed States/Provinces',
        help="States/provinces where this benefit is available"
    )
    
    # Chapter Restrictions
    chapter_restriction = fields.Boolean(
        string='Chapter Restrictions',
        default=False,
        help="Check if benefit is limited to specific chapters"
    )
    
    allowed_chapter_ids = fields.Many2many(
        'ams.chapter',
        'benefit_chapter_rel',
        'benefit_id',
        'chapter_id',
        string='Allowed Chapters',
        help="Chapters where this benefit is available"
    )
    
    # External Integration
    external_url = fields.Char(
        string='External URL',
        help="External website or portal for this benefit"
    )
    
    access_code = fields.Char(
        string='Access Code',
        help="Special code members need to access this benefit"
    )
    
    contact_email = fields.Char(
        string='Contact Email',
        help="Email for questions about this benefit"
    )
    
    contact_phone = fields.Char(
        string='Contact Phone',
        help="Phone number for questions about this benefit"
    )
    
    # Provider Information
    provider_name = fields.Char(
        string='Provider Name',
        help="Name of company/organization providing this benefit"
    )
    
    provider_contact = fields.Char(
        string='Provider Contact',
        help="Contact information for benefit provider"
    )
    
    contract_reference = fields.Char(
        string='Contract Reference',
        help="Reference to contract or agreement for this benefit"
    )
    
    # Validity Dates
    start_date = fields.Date(
        string='Start Date',
        help="Date when this benefit becomes available"
    )
    
    end_date = fields.Date(
        string='End Date',
        help="Date when this benefit expires"
    )
    
    # Usage Tracking
    usage_count = fields.Integer(
        string='Total Usage Count',
        compute='_compute_usage_statistics',
        store=True,
        help="Total number of times this benefit has been used"
    )
    
    member_usage_count = fields.Integer(
        string='Member Usage Count',
        compute='_compute_usage_statistics',
        store=True,
        help="Number of unique members who have used this benefit"
    )
    
    # Related Records
    usage_log_ids = fields.One2many(
        'ams.benefit.usage',
        'benefit_id',
        string='Usage Log',
        help="Log of benefit usage by members"
    )
    
    # Marketing and Display
    featured = fields.Boolean(
        string='Featured Benefit',
        default=False,
        help="Check to feature this benefit in marketing materials"
    )
    
    display_on_website = fields.Boolean(
        string='Display on Website',
        default=True,
        help="Show this benefit on public website"
    )
    
    marketing_text = fields.Html(
        string='Marketing Text',
        help="Marketing description for public display"
    )
    
    icon_image = fields.Binary(
        string='Icon Image',
        help="Icon or image for this benefit"
    )
    
    # Tags and Keywords
    tag_ids = fields.Many2many(
        'ams.benefit.tag',
        string='Tags',
        help="Tags for categorizing and searching benefits"
    )
    
    keywords = fields.Char(
        string='Keywords',
        help="Keywords for searching this benefit"
    )

    @api.depends('usage_log_ids')
    def _compute_usage_statistics(self):
        """Compute usage statistics"""
        for benefit in self:
            usage_logs = benefit.usage_log_ids
            benefit.usage_count = len(usage_logs)
            benefit.member_usage_count = len(usage_logs.mapped('member_id'))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate benefit dates"""
        for benefit in self:
            if benefit.start_date and benefit.end_date:
                if benefit.start_date > benefit.end_date:
                    raise ValidationError(_("Start date cannot be after end date."))

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for benefit in self:
            if benefit.discount_percentage < 0 or benefit.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    @api.constrains('quantity_limit')
    def _check_quantity_limit(self):
        """Validate quantity limit"""
        for benefit in self:
            if benefit.quantity_limit < 0:
                raise ValidationError(_("Quantity limit cannot be negative."))

    def name_get(self):
        """Customize display name"""
        result = []
        for benefit in self:
            name = benefit.name
            if benefit.benefit_type == 'discount' and benefit.discount_percentage > 0:
                name += f" ({benefit.discount_percentage:.0f}% off)"
            elif benefit.benefit_type == 'discount' and benefit.discount_amount > 0:
                name += f" (${benefit.discount_amount:.2f} off)"
            result.append((benefit.id, name))
        return result

    def is_available_for_member(self, member):
        """Check if this benefit is available for a specific member"""
        self.ensure_one()
        
        # Check if benefit is active
        if not self.active:
            return False, _("Benefit is not active.")
        
        # Check validity dates
        today = fields.Date.today()
        if self.start_date and today < self.start_date:
            return False, _("Benefit is not yet available.")
        
        if self.end_date and today > self.end_date:
            return False, _("Benefit has expired.")
        
        # Check geographic restrictions
        if self.geographic_restriction:
            if self.allowed_country_ids and member.country_id not in self.allowed_country_ids:
                return False, _("Benefit not available in your country.")
            
            if self.allowed_state_ids and member.state_id not in self.allowed_state_ids:
                return False, _("Benefit not available in your state/province.")
        
        # Check chapter restrictions
        if self.chapter_restriction:
            member_chapter = member.current_chapter_id
            if not member_chapter or member_chapter not in self.allowed_chapter_ids:
                return False, _("Benefit not available for your chapter.")
        
        # Check usage limits
        if self.quantity_limit > 0:
            member_usage = self.get_member_usage_count(member)
            if member_usage >= self.quantity_limit:
                return False, _("Usage limit reached for this benefit.")
        
        return True, _("Benefit is available.")

    def get_member_usage_count(self, member):
        """Get usage count for a specific member"""
        self.ensure_one()
        
        domain = [
            ('benefit_id', '=', self.id),
            ('member_id', '=', member.id)
        ]
        
        # Filter by usage period if needed
        if self.usage_period == 'monthly':
            from datetime import date
            today = date.today()
            start_of_month = today.replace(day=1)
            domain.append(('usage_date', '>=', start_of_month))
        elif self.usage_period == 'quarterly':
            # Add quarterly logic if needed
            pass
        elif self.usage_period == 'annually':
            from datetime import date
            today = date.today()
            start_of_year = today.replace(month=1, day=1)
            domain.append(('usage_date', '>=', start_of_year))
        
        return self.env['ams.benefit.usage'].search_count(domain)

    def record_usage(self, member, notes=None, usage_value=None):
        """Record usage of this benefit by a member"""
        self.ensure_one()
        
        # Check if benefit is available
        is_available, message = self.is_available_for_member(member)
        if not is_available:
            raise ValidationError(message)
        
        # Create usage record
        usage_vals = {
            'benefit_id': self.id,
            'member_id': member.id,
            'usage_date': fields.Date.today(),
            'notes': notes,
            'usage_value': usage_value or 0.0,
        }
        
        usage_record = self.env['ams.benefit.usage'].create(usage_vals)
        
        # Log the usage
        self.message_post(
            body=_("Benefit used by %s") % member.name
        )
        
        return usage_record

    def action_view_usage_log(self):
        """View usage log for this benefit"""
        self.ensure_one()
        
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ams_subscriptions.action_benefit_usage"
        )
        action['domain'] = [('benefit_id', '=', self.id)]
        action['context'] = {
            'default_benefit_id': self.id,
        }
        
        return action

    @api.model
    def get_benefits_for_membership_type(self, membership_type_id, member=None):
        """Get all benefits for a specific membership type"""
        benefits = self.search([
            ('membership_type_id', '=', membership_type_id),
            ('active', '=', True)
        ])
        
        if member:
            # Filter benefits available to this member
            available_benefits = []
            for benefit in benefits:
                is_available, _ = benefit.is_available_for_member(member)
                if is_available:
                    available_benefits.append(benefit)
            return self.browse([b.id for b in available_benefits])
        
        return benefits

    @api.model
    def get_featured_benefits(self):
        """Get featured benefits for marketing"""
        return self.search([
            ('featured', '=', True),
            ('active', '=', True),
            ('display_on_website', '=', True)
        ])


class BenefitUsage(models.Model):
    _name = 'ams.benefit.usage'
    _description = 'Benefit Usage Log'
    _order = 'usage_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    benefit_id = fields.Many2one(
        'ams.subscription.benefit',
        string='Benefit',
        required=True,
        ondelete='cascade'
    )
    
    member_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        domain=[('is_member', '=', True)]
    )
    
    usage_date = fields.Date(
        string='Usage Date',
        required=True,
        default=fields.Date.context_today
    )
    
    usage_value = fields.Float(
        string='Usage Value',
        digits='Product Price',
        help="Monetary value of this usage instance"
    )
    
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this usage"
    )
    
    verified = fields.Boolean(
        string='Verified',
        default=False,
        help="Check if this usage has been verified"
    )
    
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By'
    )
    
    verification_date = fields.Datetime(
        string='Verification Date'
    )

    @api.depends('benefit_id', 'member_id', 'usage_date')
    def _compute_display_name(self):
        for record in self:
            if record.benefit_id and record.member_id:
                record.display_name = f"{record.member_id.name} - {record.benefit_id.name} ({record.usage_date})"
            else:
                record.display_name = _('New Usage Record')

    def action_verify(self):
        """Verify this usage record"""
        for record in self:
            record.write({
                'verified': True,
                'verified_by': self.env.user.id,
                'verification_date': fields.Datetime.now(),
            })


class BenefitTag(models.Model):
    _name = 'ams.benefit.tag'
    _description = 'Benefit Tag'
    _order = 'name'

    name = fields.Char(
        string='Tag Name',
        required=True
    )
    
    color = fields.Integer(
        string='Color Index',
        help="Color for display"
    )
    
    description = fields.Text(
        string='Description'
    )
    
    benefit_count = fields.Integer(
        string='Benefit Count',
        compute='_compute_benefit_count'
    )

    @api.depends('benefit_ids')
    def _compute_benefit_count(self):
        for tag in self:
            tag.benefit_count = len(tag.benefit_ids)

    benefit_ids = fields.Many2many(
        'ams.subscription.benefit',
        string='Benefits'
    )

    @api.constrains('name')
    def _check_unique_name(self):
        for tag in self:
            if self.search_count([
                ('name', '=', tag.name),
                ('id', '!=', tag.id)
            ]) > 0:
                raise ValidationError(_("Tag name must be unique!"))