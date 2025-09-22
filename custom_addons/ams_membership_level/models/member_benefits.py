from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipBenefit(models.Model):
    _name = 'membership.benefit'
    _description = 'Membership Benefit'
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Benefit Name',
        required=True,
        help="Name of the membership benefit"
    )
    code = fields.Char(
        string='Code',
        help="Short code for the benefit"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of the benefit"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this benefit"
    )
    
    # Benefit Configuration
    benefit_type = fields.Selection([
        ('discount', 'Discount Benefit'),
        ('access', 'Access Benefit'),
        ('service', 'Service Benefit'),
        ('product', 'Product Benefit'),
        ('event', 'Event Benefit'),
        ('other', 'Other')
    ], string='Benefit Type', required=True, default='access')
    
    # Usage Limits
    usage_limit = fields.Integer(
        string='Usage Limit per Year',
        default=0,
        help="Maximum uses per member per year (0 = unlimited)"
    )
    usage_period = fields.Selection([
        ('yearly', 'Per Year'),
        ('membership', 'Per Membership Period'),
        ('lifetime', 'Lifetime'),
        ('monthly', 'Per Month')
    ], string='Usage Period', default='yearly')
    
    # Financial Tracking
    cost_to_organization = fields.Monetary(
        string='Cost per Use',
        currency_field='currency_id',
        help="Cost to organization when member uses this benefit"
    )
    member_price = fields.Monetary(
        string='Member Price',
        currency_field='currency_id',
        help="Price member pays for this benefit (if any)"
    )
    non_member_price = fields.Monetary(
        string='Non-Member Price',
        currency_field='currency_id',
        help="Price non-members pay for equivalent service"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Availability
    level_ids = fields.Many2many(
        'membership.level',
        'benefit_level_rel',
        'benefit_id',
        'level_id',
        string='Available to Levels',
        help="Membership levels that have access to this benefit"
    )
    chapter_ids = fields.Many2many(
        'membership.chapter',
        'benefit_chapter_rel',
        'benefit_id',
        'chapter_id',
        string='Available to Chapters',
        help="Chapters that have access to this benefit (empty = all chapters)"
    )
    
    # External Integration
    external_system = fields.Char(
        string='External System',
        help="Name of external system providing this benefit"
    )
    external_url = fields.Char(
        string='External URL',
        help="URL for accessing this benefit"
    )
    api_endpoint = fields.Char(
        string='API Endpoint',
        help="API endpoint for benefit verification"
    )
    
    # Statistics
    total_usage_count = fields.Integer(
        string='Total Usage Count',
        compute='_compute_usage_statistics',
        help="Total number of times this benefit has been used"
    )
    unique_users_count = fields.Integer(
        string='Unique Users',
        compute='_compute_usage_statistics',
        help="Number of unique members who have used this benefit"
    )
    total_cost = fields.Monetary(
        string='Total Cost',
        compute='_compute_usage_statistics',
        currency_field='currency_id',
        help="Total cost of providing this benefit"
    )

    @api.depends('usage_ids.usage_count')
    def _compute_usage_statistics(self):
        for benefit in self:
            usages = benefit.usage_ids
            benefit.total_usage_count = sum(usages.mapped('usage_count'))
            benefit.unique_users_count = len(usages.mapped('partner_id'))
            benefit.total_cost = benefit.total_usage_count * benefit.cost_to_organization

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Benefit code must be unique."))

    def action_view_usage(self):
        """View usage records for this benefit"""
        self.ensure_one()
        return {
            'name': f"Usage - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.benefit.usage',
            'view_mode': 'tree,form',
            'domain': [('benefit_id', '=', self.id)],
            'context': {'default_benefit_id': self.id},
        }


class MembershipBenefitUsage(models.Model):
    _name = 'membership.benefit.usage'
    _description = 'Membership Benefit Usage'
    _order = 'usage_date desc'

    # Basic Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        help="Member who used the benefit"
    )
    benefit_id = fields.Many2one(
        'membership.benefit',
        string='Benefit',
        required=True,
        help="Benefit that was used"
    )
    usage_date = fields.Date(
        string='Usage Date',
        required=True,
        default=fields.Date.today,
        help="Date when benefit was used"
    )
    usage_count = fields.Integer(
        string='Usage Count',
        default=1,
        help="Number of times benefit was used on this date"
    )
    
    # Usage Details
    usage_description = fields.Text(
        string='Usage Description',
        help="Description of how the benefit was used"
    )
    usage_value = fields.Monetary(
        string='Usage Value',
        related='benefit_id.cost_to_organization',
        currency_field='currency_id',
        help="Value of benefit usage"
    )
    
    # Member Information (at time of usage)
    membership_id = fields.Many2one(
        'membership.membership',
        string='Membership',
        help="Active membership at time of usage"
    )
    membership_level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        help="Member's level at time of usage"
    )
    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        help="Member's chapter at time of usage"
    )
    
    # Verification
    verified = fields.Boolean(
        string='Verified',
        default=False,
        help="Usage has been verified"
    )
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help="Staff member who verified usage"
    )
    verification_date = fields.Datetime(
        string='Verification Date',
        help="When usage was verified"
    )
    
    # External System Integration
    external_reference = fields.Char(
        string='External Reference',
        help="Reference number from external system"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='benefit_id.currency_id',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._populate_member_info()
        return records

    def _populate_member_info(self):
        """Populate member information at time of usage"""
        self.ensure_one()
        
        # Get current membership
        current_membership = self.partner_id.current_membership_id
        if current_membership:
            self.membership_id = current_membership.id
            self.membership_level_id = current_membership.level_id.id
            # Note: chapter_id will remain empty in base module since chapters aren't implemented yet
            # This is acceptable for the MVP

    def action_verify_usage(self):
        """Verify benefit usage"""
        self.ensure_one()
        self.write({
            'verified': True,
            'verified_by': self.env.user.id,
            'verification_date': fields.Datetime.now()
        })

    @api.constrains('usage_count')
    def _check_usage_count(self):
        for record in self:
            if record.usage_count <= 0:
                raise ValidationError(_("Usage count must be greater than zero."))

    @api.constrains('partner_id', 'benefit_id', 'usage_date')
    def _check_usage_limits(self):
        """Check if member has exceeded usage limits"""
        for record in self:
            if record.benefit_id.usage_limit > 0:
                # Calculate usage period start date
                usage_date = record.usage_date
                
                if record.benefit_id.usage_period == 'yearly':
                    start_date = usage_date.replace(month=1, day=1)
                    end_date = usage_date.replace(month=12, day=31)
                elif record.benefit_id.usage_period == 'monthly':
                    start_date = usage_date.replace(day=1)
                    if usage_date.month == 12:
                        end_date = usage_date.replace(year=usage_date.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end_date = usage_date.replace(month=usage_date.month + 1, day=1) - timedelta(days=1)
                elif record.benefit_id.usage_period == 'membership':
                    if record.membership_id:
                        start_date = record.membership_id.start_date
                        end_date = record.membership_id.end_date
                    else:
                        continue  # Skip check if no membership
                else:  # lifetime
                    start_date = fields.Date.from_string('1900-01-01')
                    end_date = fields.Date.today()
                
                # Count existing usage in period
                existing_usage = self.search([
                    ('partner_id', '=', record.partner_id.id),
                    ('benefit_id', '=', record.benefit_id.id),
                    ('usage_date', '>=', start_date),
                    ('usage_date', '<=', end_date),
                    ('id', '!=', record.id)
                ])
                
                total_usage = sum(existing_usage.mapped('usage_count')) + record.usage_count
                
                if total_usage > record.benefit_id.usage_limit:
                    raise ValidationError(
                        _("Usage limit exceeded. Member has already used %d of %d allowed uses in this period.") % (
                            total_usage - record.usage_count,
                            record.benefit_id.usage_limit
                        )
                    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    benefit_usage_ids = fields.One2many(
        'membership.benefit.usage',
        'partner_id',
        string='Benefit Usage History'
    )
    total_benefit_usage_count = fields.Integer(
        string='Total Benefit Uses',
        compute='_compute_benefit_statistics'
    )
    benefit_value_received = fields.Monetary(
        string='Benefit Value Received',
        compute='_compute_benefit_statistics',
        currency_field='currency_id'
    )

    @api.depends('benefit_usage_ids.usage_count', 'benefit_usage_ids.usage_value')
    def _compute_benefit_statistics(self):
        for partner in self:
            usages = partner.benefit_usage_ids
            partner.total_benefit_usage_count = sum(usages.mapped('usage_count'))
            partner.benefit_value_received = sum(u.usage_count * u.usage_value for u in usages)

    def get_available_benefits(self):
        """Get benefits available to this member"""
        self.ensure_one()
        
        if not self.current_membership_id:
            return self.env['membership.benefit'].browse()
        
        # Get member's level and chapter
        level = self.current_membership_id.level_id
        # For MVP, we'll ignore chapter filtering since chapters aren't implemented yet
        
        # Find benefits available to this level
        domain = [
            ('active', '=', True),
            '|', ('level_ids', 'in', level.ids), ('level_ids', '=', False)
        ]
        
        # Note: Chapter filtering is commented out for MVP since chapters aren't implemented
        # if chapter:
        #     domain = ['&'] + domain + [
        #         '|', ('chapter_ids', 'in', chapter.ids), ('chapter_ids', '=', False)
        #     ]
        # else:
        #     domain = ['&'] + domain + [('chapter_ids', '=', False)]
        
        return self.env['membership.benefit'].search(domain)

    def action_view_benefit_usage(self):
        """View benefit usage for this member"""
        self.ensure_one()
        return {
            'name': f"Benefit Usage - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.benefit.usage',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def record_benefit_usage(self, benefit_id, usage_count=1, usage_description=''):
        """Record benefit usage for this member"""
        self.ensure_one()
        
        return self.env['membership.benefit.usage'].create({
            'partner_id': self.id,
            'benefit_id': benefit_id,
            'usage_count': usage_count,
            'usage_description': usage_description,
            'usage_date': fields.Date.today()
        })


class MembershipLevel(models.Model):
    _inherit = 'membership.level'

    benefit_ids = fields.Many2many(
        'membership.benefit',
        'benefit_level_rel',
        'level_id',
        'benefit_id',
        string='Included Benefits'
    )
    benefit_count = fields.Integer(
        string='Benefits Count',
        compute='_compute_benefit_count'
    )

    @api.depends('benefit_ids')
    def _compute_benefit_count(self):
        for level in self:
            level.benefit_count = len(level.benefit_ids)

    def action_view_benefits(self):
        """View benefits for this level"""
        self.ensure_one()
        return {
            'name': f"Benefits - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.benefit',
            'view_mode': 'tree,form',
            'domain': [('level_ids', 'in', self.id)],
            'context': {'default_level_ids': [(4, self.id)]},
        }


# Add reverse relation for usage statistics
class MembershipBenefit(models.Model):
    _inherit = 'membership.benefit'
    
    usage_ids = fields.One2many(
        'membership.benefit.usage',
        'benefit_id',
        string='Usage Records'
    )