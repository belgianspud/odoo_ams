# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipBenefit(models.Model):
    """
    Membership Benefit - Simplified Base Model
    Benefits that members receive with their membership
    """
    _name = 'membership.benefit'
    _description = 'Membership Benefit'
    _order = 'category, sequence, name'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Benefit Name',
        required=True,
        translate=True,
        help='Display name for this benefit (e.g., "20% Event Discount", "Free Journal Access")'
    )
    
    code = fields.Char(
        string='Benefit Code',
        required=True,
        help='Unique code for this benefit (e.g., EVENT_DISC_20, JOURNAL_FREE)'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive benefits are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this benefit for members'
    )
    
    short_description = fields.Char(
        string='Short Description',
        translate=True,
        help='Brief one-line description for lists and summaries'
    )
    
    icon = fields.Char(
        string='Icon',
        help='Font Awesome icon class (e.g., fa-star, fa-gift, fa-trophy)'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # BENEFIT CLASSIFICATION
    # ==========================================
    
    category = fields.Selection([
        ('discount', 'Discounts'),
        ('access', 'Access & Resources'),
        ('publication', 'Publications'),
        ('event', 'Events & Conferences'),
        ('education', 'Education & Training'),
        ('networking', 'Networking'),
        ('professional', 'Professional Development'),
        ('recognition', 'Recognition & Awards'),
        ('other', 'Other')
    ], string='Benefit Category',
       required=True,
       default='other',
       help='Type of benefit')
    
    benefit_type = fields.Selection([
        ('monetary', 'Monetary Value'),
        ('service', 'Service Access'),
        ('resource', 'Resource Access'),
        ('privilege', 'Privilege/Priority'),
        ('recognition', 'Recognition'),
        ('tangible', 'Tangible Item')
    ], string='Benefit Type',
       default='service',
       required=True,
       help='Nature of the benefit')
    
    is_premium_benefit = fields.Boolean(
        string='Premium Benefit',
        default=False,
        help='This is a premium benefit for higher-tier memberships'
    )
    
    is_highlighted = fields.Boolean(
        string='Highlight Benefit',
        default=False,
        help='Highlight this benefit in marketing materials'
    )

    # ==========================================
    # VALUE & QUANTIFICATION
    # ==========================================
    
    has_monetary_value = fields.Boolean(
        string='Has Monetary Value',
        default=False,
        help='This benefit has a quantifiable monetary value'
    )
    
    monetary_value = fields.Monetary(
        string='Estimated Value',
        default=0.0,
        help='Estimated monetary value of this benefit'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    quantifiable_value = fields.Char(
        string='Quantifiable Value',
        help='Quantity description (e.g., "Up to 5 events", "Unlimited downloads")'
    )

    # ==========================================
    # PRODUCT ASSOCIATIONS
    # ==========================================
    
    product_ids = fields.Many2many(
        'product.template',
        'product_benefit_rel',
        'benefit_id',
        'product_id',
        string='Associated Products',
        help='Membership products that include this benefit'
    )
    
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
        help='Number of products offering this benefit'
    )
    
    category_ids = fields.Many2many(
        'membership.category',
        'category_benefit_rel',
        'benefit_id',
        'category_id',
        string='Associated Categories',
        help='Member categories eligible for this benefit'
    )

    @api.depends('product_ids')
    def _compute_product_count(self):
        """Count associated products"""
        for benefit in self:
            benefit.product_count = len(benefit.product_ids)

    # ==========================================
    # LINKED FEATURE
    # ==========================================
    
    feature_id = fields.Many2one(
        'membership.feature',
        string='Linked Feature',
        help='Technical feature that enables this benefit'
    )

    # ==========================================
    # MARKETING & DISPLAY
    # ==========================================
    
    display_on_website = fields.Boolean(
        string='Display on Website',
        default=True,
        help='Show this benefit on public website'
    )
    
    display_order = fields.Integer(
        string='Display Order',
        default=10,
        help='Order for displaying on website/marketing materials'
    )
    
    marketing_tagline = fields.Char(
        string='Marketing Tagline',
        translate=True,
        help='Catchy tagline for marketing (e.g., "Save up to $500!")'
    )

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def check_eligibility(self, partner_id, date=None):
        """
        Check if a partner is eligible for this benefit
        
        Args:
            partner_id: res.partner record or ID
            date: Date to check (defaults to today)
        
        Returns:
            tuple: (bool: is_eligible, str: reason if not eligible)
        """
        self.ensure_one()
        
        if date is None:
            date = fields.Date.today()
        
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        # Check if partner has subscription with this benefit
        has_benefit = bool(
            partner.membership_subscription_ids.filtered(
                lambda s: s.state in ['trial', 'active'] and 
                         self in s.plan_id.product_template_id.benefit_ids
            )
        )
        
        if not has_benefit:
            return (False, _("Your membership does not include this benefit"))
        
        # Check category restrictions
        if self.category_ids:
            if partner.membership_category_id not in self.category_ids:
                return (False, _("Your member category is not eligible for this benefit"))
        
        return (True, '')

    def action_view_products(self):
        """View products that include this benefit"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products with Benefit: %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    @api.model
    def get_benefit_by_code(self, code):
        """
        Get benefit by code (helper method)
        
        Args:
            code: Benefit code
        
        Returns:
            membership.benefit record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"{name} [{record.code}]"
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure benefit code is unique"""
        for benefit in self:
            if self.search_count([
                ('code', '=', benefit.code),
                ('id', '!=', benefit.id)
            ]) > 0:
                raise ValidationError(
                    _("Benefit code must be unique. '%s' is already used.") % benefit.code
                )

    @api.constrains('monetary_value')
    def _check_monetary_value(self):
        """Validate monetary value"""
        for benefit in self:
            if benefit.monetary_value < 0:
                raise ValidationError(_("Monetary value cannot be negative."))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Benefit code must be unique!'),
    ]