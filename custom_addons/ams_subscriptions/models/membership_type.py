from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class MembershipType(models.Model):
    _name = 'ams.membership.type'
    _description = 'Membership Type'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Membership Type Name', 
        required=True,
        help="Name of the membership type (e.g., 'Professional', 'Student', 'Corporate')"
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help="Short code for this membership type"
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this membership type"
    )
    
    description = fields.Html(
        string='Description',
        help="Detailed description of this membership type"
    )
    
    # Pricing and Duration
    price = fields.Float(
        string='Annual Price',
        digits='Product Price',
        help="Annual membership fee"
    )
    
    duration = fields.Integer(
        string='Duration (Months)',
        default=12,
        required=True,
        help="Duration of membership in months"
    )
    
    duration_type = fields.Selection([
        ('annual', 'Annual'),
        ('monthly', 'Monthly'),
        ('lifetime', 'Lifetime'),
        ('custom', 'Custom Duration')
    ], string='Duration Type', default='annual', required=True)
    
    # Member Categories
    member_category = fields.Selection([
        ('individual', 'Individual'),
        ('student', 'Student'),
        ('corporate', 'Corporate'),
        ('honorary', 'Honorary'),
        ('emeritus', 'Emeritus'),
        ('affiliate', 'Affiliate')
    ], string='Member Category', default='individual', required=True)
    
    # Eligibility and Requirements
    eligibility_requirements = fields.Html(
        string='Eligibility Requirements',
        help="Requirements that must be met to join this membership type"
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help="Check if membership applications require manual approval"
    )
    
    max_members = fields.Integer(
        string='Maximum Members',
        help="Maximum number of members allowed (0 = unlimited)"
    )
    
    # Chapter Support
    chapter_based = fields.Boolean(
        string='Chapter-Based Membership',
        default=False,
        help="Check if this membership type is tied to specific chapters"
    )
    
    allowed_chapter_ids = fields.Many2many(
        'ams.chapter',
        'membership_type_chapter_rel',
        'membership_type_id',
        'chapter_id',
        string='Allowed Chapters',
        help="Chapters where this membership type is available"
    )
    
    # Benefits
    benefit_ids = fields.One2many(
        'ams.subscription.benefit',
        'membership_type_id',
        string='Membership Benefits'
    )
    
    # Product Integration
    product_template_id = fields.Many2one(
        'product.template',
        string='Related Product',
        help="Product used for invoicing this membership type"
    )
    
    # Auto-create product when membership type is created
    auto_create_product = fields.Boolean(
        string='Auto-Create Product',
        default=True,
        help="Automatically create a product for this membership type"
    )
    
    # Renewal Settings
    auto_renew = fields.Boolean(
        string='Auto-Renewal Available',
        default=True,
        help="Allow members to set up automatic renewal"
    )
    
    renewal_notice_days = fields.Integer(
        string='Renewal Notice (Days)',
        default=30,
        help="Days before expiration to send renewal notice"
    )
    
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help="Days after expiration before marking as lapsed"
    )
    
    # Statistics
    current_member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_statistics',
        store=True,
        help="Number of currently active members"
    )
    
    total_revenue = fields.Float(
        string='Total Revenue',
        compute='_compute_member_statistics',
        store=True,
        help="Total revenue from this membership type"
    )
    
    subscription_ids = fields.One2many(
        'ams.member.subscription',
        'membership_type_id',
        string='Subscriptions'
    )

    @api.depends('subscription_ids.state', 'subscription_ids.total_amount')
    def _compute_member_statistics(self):
        for record in self:
            active_subscriptions = record.subscription_ids.filtered(
                lambda s: s.state in ['active', 'pending_renewal']
            )
            record.current_member_count = len(active_subscriptions)
            record.total_revenue = sum(active_subscriptions.mapped('total_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.auto_create_product and not record.product_template_id:
                record._create_related_product()
        return records

    def _create_related_product(self):
        """Create a related product for this membership type"""
        self.ensure_one()
        
        # Create product category for memberships if it doesn't exist
        category = self.env['product.category'].search([
            ('name', '=', 'Memberships')
        ], limit=1)
        
        if not category:
            category = self.env['product.category'].create({
                'name': 'Memberships',
                'parent_id': False,
            })
        
        # Create the product
        product_vals = {
            'name': f"{self.name} Membership",
            'type': 'service',
            'categ_id': category.id,
            'list_price': self.price,
            'standard_price': 0,
            'sale_ok': True,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'description_sale': self.description,
            'default_code': f"MEMBER-{self.code}",
        }
        
        product = self.env['product.template'].create(product_vals)
        self.product_template_id = product.id

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([
                ('code', '=', record.code),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_("Membership type code must be unique!"))

    @api.constrains('max_members')
    def _check_max_members(self):
        for record in self:
            if record.max_members > 0:
                if record.current_member_count > record.max_members:
                    raise ValidationError(
                        _("Cannot set maximum members below current member count (%s)") 
                        % record.current_member_count
                    )

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name}"
            if record.member_category != 'individual':
                name += f" ({record.member_category.title()})"
            result.append((record.id, name))
        return result

    def get_renewal_price(self, subscription=None):
        """Get the renewal price for this membership type"""
        # This can be extended later for discounts, promotions, etc.
        return self.price

    def is_available_for_chapter(self, chapter_id):
        """Check if this membership type is available for a specific chapter"""
        if not self.chapter_based:
            return True
        return chapter_id in self.allowed_chapter_ids.ids

    def get_expiration_date(self, start_date=None):
        """Calculate expiration date based on membership type duration"""
        if not start_date:
            start_date = fields.Date.today()
        
        if self.duration_type == 'lifetime':
            return False  # No expiration
        elif self.duration_type == 'annual':
            return start_date + relativedelta(years=1)
        elif self.duration_type == 'monthly':
            return start_date + relativedelta(months=1)
        else:  # custom
            return start_date + relativedelta(months=self.duration)