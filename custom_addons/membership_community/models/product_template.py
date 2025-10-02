# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """
    Extended Product Template for Membership Management
    Supports both organizational memberships and seat products
    """
    _inherit = 'product.template'

    # ==========================================
    # CORE MEMBERSHIP FLAG
    # ==========================================
    
    is_membership_product = fields.Boolean(
        string='Membership',
        default=False,
        help="Check this if this product represents a membership. "
             "Works with subscription features for billing and renewal."
    )
    
    # ==========================================
    # SUBSCRIPTION TYPE - Extended by specialized modules
    # ==========================================
    
    subscription_product_type = fields.Selection(
        selection='_get_subscription_product_types',
        string='Subscription Type',
        help='Type of subscription this product represents'
    )
    
    @api.model
    def _get_subscription_product_types(self):
        """Base types - extended by specialized modules"""
        return [
            ('membership', 'Individual Membership'),
            ('organizational_membership', 'Organizational Membership'),
            ('chapter', 'Chapter Membership'),
        ]

    # ==========================================
    # CATEGORY MAPPING
    # ==========================================
    
    default_member_category_id = fields.Many2one(
        'membership.category',
        string='Default Member Category',
        help='Default category when creating membership with this product'
    )

    # ==========================================
    # FEATURES & BENEFITS
    # ==========================================
    
    benefit_ids = fields.Many2many(
        'membership.benefit',
        'product_benefit_rel',
        'product_id',
        'benefit_id',
        string='Benefits',
        help="Benefits included with this membership"
    )
    
    feature_ids = fields.Many2many(
        'membership.feature',
        'product_feature_rel',
        'product_id',
        'feature_id',
        string='Features',
        help="Features included with this membership"
    )

    # ==========================================
    # PORTAL ACCESS
    # ==========================================
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access')
    ], string='Portal Access Level',
       default='standard',
       help="Default portal access level for members with this product")

    # ==========================================
    # SEAT PRODUCT DEFINITION (NEW)
    # ==========================================
    
    provides_seats = fields.Boolean(
        string='Provides Seats',
        default=False,
        help='This product adds seats to an organizational membership'
    )
    
    seat_quantity = fields.Integer(
        string='Number of Seats Provided',
        default=1,
        help='How many seats does this product provide? (e.g., "5-Seat Pack" = 5)'
    )
    
    is_seat_addon = fields.Boolean(
        string='Is Seat Add-on',
        compute='_compute_is_seat_addon',
        store=True,
        help='This product is used to add seats to organizational memberships'
    )
    
    parent_membership_product_id = fields.Many2one(
        'product.template',
        string='Parent Membership Product',
        domain=[('subscription_product_type', '=', 'organizational_membership')],
        help='The organizational membership product this seat add-on is for'
    )
    
    price_per_seat = fields.Float(
        string='Price Per Seat',
        compute='_compute_price_per_seat',
        store=True,
        help='Calculated price per individual seat'
    )
    
    @api.depends('subscription_product_type', 'provides_seats', 'parent_membership_product_id')
    def _compute_is_seat_addon(self):
        """Determine if this is a seat add-on product"""
        for product in self:
            product.is_seat_addon = (
                product.provides_seats or 
                (product.subscription_product_type == 'membership' and 
                 product.parent_membership_product_id)
            )
    
    @api.depends('list_price', 'seat_quantity')
    def _compute_price_per_seat(self):
        """Calculate price per individual seat"""
        for product in self:
            if product.seat_quantity > 0:
                product.price_per_seat = product.list_price / product.seat_quantity
            else:
                product.price_per_seat = product.list_price

    # ==========================================
    # ORGANIZATIONAL MEMBERSHIP SETTINGS (NEW)
    # ==========================================
    
    requires_organization_info = fields.Boolean(
        string='Requires Organization Info',
        default=False,
        help='Collect organization details during signup'
    )
    
    requires_primary_contact = fields.Boolean(
        string='Requires Primary Contact',
        default=True,
        help='Organization must designate a primary contact'
    )
    
    allow_multiple_admins = fields.Boolean(
        string='Allow Multiple Administrators',
        default=True,
        help='Organization can have multiple admin users'
    )
    
    seat_allocation_type = fields.Selection([
        ('admin_managed', 'Admin Allocates Seats'),
        ('self_service', 'Users Can Request Seats'),
        ('automatic', 'Automatic Allocation'),
    ], string='Seat Allocation Method',
       default='admin_managed',
       help='How are seats assigned to employees?')
    
    seat_approval_required = fields.Boolean(
        string='Seat Requests Need Approval',
        default=False,
        help='Seat allocations must be approved by organization admin'
    )
    
    require_org_tax_id = fields.Boolean(
        string='Require Tax ID',
        default=False,
        help='Organization must provide tax ID (EIN, VAT, etc.)'
    )
    
    require_org_address = fields.Boolean(
        string='Require Organization Address',
        default=True,
        help='Organization must provide physical address'
    )
    
    max_org_size = fields.Integer(
        string='Maximum Organization Size',
        default=0,
        help='Maximum number of employees/members (0 = unlimited)'
    )

    # ==========================================
    # MEMBER COUNT
    # ==========================================
    
    current_member_count = fields.Integer(
        string='Current Members',
        compute='_compute_current_member_count',
        help="Number of current active members"
    )

    @api.depends('is_membership_product')
    def _compute_current_member_count(self):
        """Calculate current active members"""
        for product in self:
            if product.is_membership_product:
                count = self.env['subscription.subscription'].search_count([
                    ('plan_id.product_template_id', '=', product.id),
                    ('state', 'in', ['trial', 'active'])
                ])
                product.current_member_count = count
            else:
                product.current_member_count = 0

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('is_membership_product')
    def _onchange_is_membership_product(self):
        """Set defaults for membership products"""
        if self.is_membership_product:
            # Set as subscription product
            if hasattr(self, 'is_subscription'):
                self.is_subscription = True
            
            # Set default subscription type if not set
            if not self.subscription_product_type:
                self.subscription_product_type = 'membership'
            
            # Set as service product
            if not self.type:
                self.type = 'service'
            
            # Set default portal access
            if not self.portal_access_level:
                self.portal_access_level = 'standard'

    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_product_type in ['membership', 'chapter', 'organizational_membership']:
            self.is_membership_product = True
            
            # Set organizational defaults
            if self.subscription_product_type == 'organizational_membership':
                self.requires_organization_info = True
                self.requires_primary_contact = True
                self.allow_multiple_admins = True
                self.seat_allocation_type = 'admin_managed'
                self.require_org_address = True
    
    @api.onchange('provides_seats')
    def _onchange_provides_seats(self):
        """Set defaults when enabling seat provision"""
        if self.provides_seats:
            if not self.seat_quantity or self.seat_quantity <= 0:
                self.seat_quantity = 5
            
            # Suggest this is a seat addon
            if not self.parent_membership_product_id:
                # Try to find an organizational membership product
                org_product = self.env['product.template'].search([
                    ('subscription_product_type', '=', 'organizational_membership'),
                    ('active', '=', True)
                ], limit=1)
                if org_product:
                    self.parent_membership_product_id = org_product.id
    
    @api.onchange('list_price', 'seat_quantity')
    def _onchange_calculate_seat_price(self):
        """Update description when seat quantity changes"""
        if self.provides_seats and self.seat_quantity > 1:
            if self.name and 'Seat Pack' not in self.name and 'Seat' not in self.name:
                # Suggest adding seat quantity to name
                pass

    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    @api.constrains('seat_quantity')
    def _check_seat_quantity(self):
        """Validate seat quantity"""
        for product in self:
            if product.provides_seats and product.seat_quantity <= 0:
                raise ValidationError(_(
                    'Seat quantity must be greater than 0 for products that provide seats.'
                ))
    
    @api.constrains('parent_membership_product_id')
    def _check_parent_membership(self):
        """Validate parent membership product"""
        for product in self:
            if product.parent_membership_product_id:
                if product.parent_membership_product_id == product:
                    raise ValidationError(_(
                        'A product cannot be its own parent membership.'
                    ))
                
                if product.parent_membership_product_id.subscription_product_type != 'organizational_membership':
                    raise ValidationError(_(
                        'Parent membership product must be of type "Organizational Membership".'
                    ))
    
    @api.constrains('max_org_size')
    def _check_max_org_size(self):
        """Validate max organization size"""
        for product in self:
            if product.max_org_size < 0:
                raise ValidationError(_(
                    'Maximum organization size cannot be negative. Use 0 for unlimited.'
                ))

    # ==========================================
    # ACTIONS
    # ==========================================

    def action_view_members(self):
        """View all members with this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [
                ('membership_subscription_ids.plan_id.product_template_id', '=', self.id),
                ('membership_subscription_ids.state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_id': self.id}
        }

    def action_view_active_subscriptions(self):
        """View active subscriptions for this product"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Subscriptions - %s') % self.name,
            'res_model': 'subscription.subscription',
            'view_mode': 'list,form',
            'domain': [
                ('plan_id.product_template_id', '=', self.id),
                ('state', 'in', ['trial', 'active'])
            ],
            'context': {'default_product_template_id': self.id}
        }
    
    def action_view_seat_addons(self):
        """View seat add-on products for this organizational membership"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Seat Add-ons - %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('parent_membership_product_id', '=', self.id)],
            'context': {'default_parent_membership_product_id': self.id}
        }
    
    # ==========================================
    # NAME/DESCRIPTION HELPERS
    # ==========================================
    
    def name_get(self):
        """Enhanced name display for seat products"""
        result = []
        for product in self:
            name = product.name
            if product.provides_seats and product.seat_quantity > 1:
                name = f"{name} ({product.seat_quantity} seats)"
            result.append((product.id, name))
        return result