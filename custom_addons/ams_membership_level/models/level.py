from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MembershipLevel(models.Model):
    _name = 'membership.level'
    _description = 'Membership Level'
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Level Name',
        required=True,
        help="Name of the membership level (e.g., Individual, Student, Organization)"
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Short code for the membership level"
    )
    description = fields.Text(
        string='Description',
        help="Description of the membership level and its benefits"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this membership level"
    )
    
    # Duration and Pricing
    duration_months = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=12,
        help="Duration of membership in months"
    )
    price = fields.Monetary(
        string='Price',
        required=True,
        currency_field='currency_id',
        help="Price for this membership level"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Product Integration
    product_id = fields.Many2one(
        'product.product',
        string='Related Product',
        help="Product used for billing this membership level"
    )
    auto_create_product = fields.Boolean(
        string='Auto Create Product',
        default=True,
        help="Automatically create/update related product when saving"
    )
    
    # Level Configuration
    is_individual = fields.Boolean(
        string='Individual Membership',
        default=True,
        help="Check if this is for individual members"
    )
    is_organization = fields.Boolean(
        string='Organization Membership',
        default=False,
        help="Check if this is for organization members"
    )
    max_members = fields.Integer(
        string='Max Members',
        help="Maximum number of members for organization levels (0 = unlimited)"
    )
    
    # Benefits and Features
    benefits = fields.Text(
        string='Benefits',
        help="List of benefits included with this membership level"
    )
    event_discount_percent = fields.Float(
        string='Event Discount (%)',
        default=0.0,
        help="Discount percentage for events (0-100)"
    )
    can_vote = fields.Boolean(
        string='Voting Rights',
        default=True,
        help="Members of this level can vote"
    )
    
    # Statistics
    member_count = fields.Integer(
        string='Active Members',
        compute='_compute_member_count',
        help="Number of active members at this level"
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_total_revenue',
        currency_field='currency_id',
        help="Total revenue from this membership level"
    )

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            if record.code:
                record.display_name = f"[{record.code}] {record.name}"
            else:
                record.display_name = record.name

    def _compute_member_count(self):
        for level in self:
            level.member_count = self.env['membership.membership'].search_count([
                ('level_id', '=', level.id),
                ('state', 'in', ['active', 'grace'])
            ])

    def _compute_total_revenue(self):
        for level in self:
            memberships = self.env['membership.membership'].search([
                ('level_id', '=', level.id)
            ])
            invoices = memberships.mapped('invoice_ids').filtered(
                lambda inv: inv.state == 'posted'
            )
            level.total_revenue = sum(invoices.mapped('amount_total'))

    @api.constrains('duration_months')
    def _check_duration(self):
        for record in self:
            if record.duration_months <= 0:
                raise ValidationError(_("Duration must be greater than 0 months."))

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(_("Price cannot be negative."))

    @api.constrains('event_discount_percent')
    def _check_discount(self):
        for record in self:
            if not (0 <= record.event_discount_percent <= 100):
                raise ValidationError(_("Event discount must be between 0 and 100 percent."))

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Code must be unique. Another level already uses this code."))

    @api.model_create_multi
    def create(self, vals_list):
        levels = super().create(vals_list)
        for level in levels:
            if level.auto_create_product:
                level._create_or_update_product()
        return levels

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in ['name', 'price', 'duration_months']) and self.auto_create_product:
            for level in self:
                level._create_or_update_product()
        return result

    def _create_or_update_product(self):
        """Create or update the related product for billing"""
        self.ensure_one()
        
        product_vals = {
            'name': f"Membership - {self.name}",
            'type': 'service',
            'categ_id': self._get_membership_category().id,
            'list_price': self.price,
            'standard_price': 0,
            'description': self.description or f"{self.name} membership for {self.duration_months} months",
            'invoice_policy': 'order',
            'is_membership_product': True,
            'membership_level_id': self.id,
        }
        
        if self.product_id:
            self.product_id.write(product_vals)
        else:
            product = self.env['product.product'].create(product_vals)
            self.product_id = product

    def _get_membership_category(self):
        """Get or create membership product category"""
        category = self.env['product.category'].search([('name', '=', 'Membership')], limit=1)
        if not category:
            category = self.env['product.category'].create({
                'name': 'Membership',
                'parent_id': False,
            })
        return category

    def action_view_members(self):
        """View members with this level"""
        self.ensure_one()
        return {
            'name': f"Members - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'tree,form',
            'domain': [('level_id', '=', self.id)],
            'context': {'default_level_id': self.id},
        }

    def action_create_membership(self):
        """Create new membership with this level"""
        self.ensure_one()
        return {
            'name': f"New {self.name} Membership",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'form',
            'context': {'default_level_id': self.id},
            'target': 'new',
        }


class Membership(models.Model):
    _inherit = 'membership.membership'

    level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        required=True,
        help="The level/tier of this membership"
    )
    
    @api.onchange('level_id')
    def _onchange_level_id(self):
        if self.level_id:
            # Auto-set end date based on level duration
            if self.start_date:
                from dateutil.relativedelta import relativedelta
                self.end_date = self.start_date + relativedelta(months=self.level_id.duration_months)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_membership_product = fields.Boolean(
        string='Is Membership Product',
        default=False,
        help="Check if this product is used for membership billing"
    )
    membership_level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        help="Related membership level for this product"
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_membership_product = fields.Boolean(
        string='Is Membership Product',
        related='product_variant_ids.is_membership_product',
        readonly=False
    )
    membership_level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        related='product_variant_ids.membership_level_id',
        readonly=False
    )