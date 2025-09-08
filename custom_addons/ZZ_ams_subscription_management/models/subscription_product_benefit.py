from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSSubscriptionProductBenefit(models.Model):
    """Benefits attached to subscription products."""
    _name = 'ams.subscription.product.benefit'
    _description = 'Subscription Product Benefit'
    _order = 'subscription_product_id, sequence, name'
    _rec_name = 'name'

    # ==========================================
    # CORE FIELDS
    # ==========================================
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Product',
        required=True,
        ondelete='cascade',
        help='Parent subscription product'
    )
    
    name = fields.Char(
        string='Benefit Name',
        required=True,
        help='Name of the benefit provided by this subscription'
    )
    
    description = fields.Text(
        string='Benefit Description',
        help='Detailed description of the benefit'
    )
    
    # ==========================================
    # ORGANIZATION FIELDS
    # ==========================================
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order for display in lists'
    )
    
    benefit_type = fields.Selection([
        ('access', 'Access Benefit'),
        ('discount', 'Discount Benefit'),
        ('service', 'Service Benefit'),
        ('product', 'Product Benefit'),
        ('digital', 'Digital Benefit'),
        ('other', 'Other Benefit')
    ], string='Benefit Type',
       default='access',
       help='Category of benefit provided')
    
    # ==========================================
    # BENEFIT CONFIGURATION
    # ==========================================
    
    is_member_exclusive = fields.Boolean(
        string='Member Exclusive',
        default=True,
        help='Benefit only available to subscription holders'
    )
    
    is_transferable = fields.Boolean(
        string='Transferable',
        default=False,
        help='Benefit can be transferred to another person'
    )
    
    has_expiry = fields.Boolean(
        string='Has Expiry',
        default=False,
        help='Benefit expires independently of subscription'
    )
    
    expiry_days = fields.Integer(
        string='Expires After (Days)',
        help='Days after which benefit expires (0 = subscription duration)'
    )
    
    # ==========================================
    # VALUE FIELDS
    # ==========================================
    
    monetary_value = fields.Monetary(
        string='Monetary Value',
        currency_field='currency_id',
        help='Estimated monetary value of this benefit'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='subscription_product_id.currency_id',
        readonly=True,
        help='Currency for monetary value'
    )
    
    discount_percentage = fields.Float(
        string='Discount Percentage',
        help='Discount percentage for discount-type benefits'
    )
    
    # ==========================================
    # USAGE TRACKING
    # ==========================================
    
    usage_limit = fields.Integer(
        string='Usage Limit',
        help='Maximum number of times benefit can be used (0 = unlimited)'
    )
    
    usage_period = fields.Selection([
        ('subscription', 'Per Subscription Period'),
        ('month', 'Per Month'),
        ('quarter', 'Per Quarter'),
        ('year', 'Per Year'),
        ('lifetime', 'Lifetime')
    ], string='Usage Period',
       default='subscription',
       help='Period for usage limit calculation')
    
    # ==========================================
    # DIGITAL BENEFIT FIELDS
    # ==========================================
    
    digital_access_url = fields.Char(
        string='Digital Access URL',
        help='URL for digital benefit access'
    )
    
    access_code_required = fields.Boolean(
        string='Access Code Required',
        help='Benefit requires access code generation'
    )
    
    # ==========================================
    # INTEGRATION FIELDS
    # ==========================================
    
    external_benefit_id = fields.Char(
        string='External Benefit ID',
        help='ID in external benefit management system'
    )
    
    integration_data = fields.Text(
        string='Integration Data',
        help='JSON data for external system integration'
    )
    
    # ==========================================
    # STATUS FIELDS
    # ==========================================
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this benefit is currently offered'
    )
    
    available_from = fields.Date(
        string='Available From',
        help='Date from which benefit becomes available'
    )
    
    available_until = fields.Date(
        string='Available Until',
        help='Date until which benefit is available'
    )
    
    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    is_currently_available = fields.Boolean(
        string='Currently Available',
        compute='_compute_is_currently_available',
        help='Whether benefit is currently available'
    )
    
    benefit_summary = fields.Char(
        string='Benefit Summary',
        compute='_compute_benefit_summary',
        help='Short summary of benefit details'
    )
    
    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('available_from', 'available_until', 'active')
    def _compute_is_currently_available(self):
        """Check if benefit is currently available."""
        today = fields.Date.today()
        
        for record in self:
            is_available = record.active
            
            if record.available_from and today < record.available_from:
                is_available = False
            
            if record.available_until and today > record.available_until:
                is_available = False
            
            record.is_currently_available = is_available

    @api.depends('name', 'benefit_type', 'monetary_value', 'discount_percentage')
    def _compute_benefit_summary(self):
        """Generate benefit summary."""
        for record in self:
            summary_parts = [record.name]
            
            if record.benefit_type == 'discount' and record.discount_percentage:
                summary_parts.append(f"({record.discount_percentage}% off)")
            elif record.monetary_value:
                summary_parts.append(f"(${record.monetary_value} value)")
            
            if record.usage_limit:
                summary_parts.append(f"- {record.usage_limit} uses per {record.usage_period}")
            
            record.benefit_summary = " ".join(summary_parts)

    # ==========================================
    # VALIDATION CONSTRAINTS
    # ==========================================

    @api.constrains('expiry_days')
    def _validate_expiry_days(self):
        """Validate expiry days configuration."""
        for record in self:
            if record.has_expiry and record.expiry_days < 0:
                raise ValidationError("Expiry days cannot be negative")

    @api.constrains('discount_percentage')
    def _validate_discount_percentage(self):
        """Validate discount percentage is reasonable."""
        for record in self:
            if record.discount_percentage:
                if record.discount_percentage < 0 or record.discount_percentage > 100:
                    raise ValidationError("Discount percentage must be between 0 and 100")

    @api.constrains('usage_limit')
    def _validate_usage_limit(self):
        """Validate usage limit is reasonable."""
        for record in self:
            if record.usage_limit < 0:
                raise ValidationError("Usage limit cannot be negative")

    @api.constrains('available_from', 'available_until')
    def _validate_availability_dates(self):
        """Validate availability date range."""
        for record in self:
            if (record.available_from and record.available_until and 
                record.available_from > record.available_until):
                raise ValidationError("Available from date must be before available until date")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_benefit_details(self):
        """Get comprehensive benefit details.
        
        Returns:
            dict: Detailed benefit information
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.benefit_type,
            'summary': self.benefit_summary,
            'configuration': {
                'is_member_exclusive': self.is_member_exclusive,
                'is_transferable': self.is_transferable,
                'has_expiry': self.has_expiry,
                'expiry_days': self.expiry_days,
            },
            'value': {
                'monetary_value': self.monetary_value,
                'currency': self.currency_id.name if self.currency_id else None,
                'discount_percentage': self.discount_percentage,
            },
            'usage': {
                'limit': self.usage_limit,
                'period': self.usage_period,
            },
            'availability': {
                'is_active': self.active,
                'is_currently_available': self.is_currently_available,
                'available_from': self.available_from,
                'available_until': self.available_until,
            },
            'digital': {
                'access_url': self.digital_access_url,
                'requires_access_code': self.access_code_required,
            }
        }

    def is_available_for_date(self, check_date=None):
        """Check if benefit is available for given date.
        
        Args:
            check_date: Date to check (defaults to today)
            
        Returns:
            bool: True if available
        """
        self.ensure_one()
        
        if not check_date:
            check_date = fields.Date.today()
        
        if not self.active:
            return False
        
        if self.available_from and check_date < self.available_from:
            return False
        
        if self.available_until and check_date > self.available_until:
            return False
        
        return True

    def generate_access_code(self):
        """Generate access code for digital benefits.
        
        Returns:
            str: Generated access code
        """
        self.ensure_one()
        
        if not self.access_code_required:
            return None
        
        # Generate a simple access code
        import secrets
        import string
        
        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        return f"AMS-{code}"

    def calculate_benefit_value(self, base_amount=None):
        """Calculate benefit value for a given base amount.
        
        Args:
            base_amount: Base amount to calculate discount on
            
        Returns:
            float: Calculated benefit value
        """
        self.ensure_one()
        
        if self.benefit_type == 'discount' and self.discount_percentage and base_amount:
            return base_amount * (self.discount_percentage / 100)
        elif self.monetary_value:
            return self.monetary_value
        else:
            return 0.0

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults."""
        for vals in vals_list:
            # Set sequence if not provided
            if not vals.get('sequence'):
                max_sequence = self.search([
                    ('subscription_product_id', '=', vals.get('subscription_product_id'))
                ]).mapped('sequence')
                vals['sequence'] = (max(max_sequence) + 10) if max_sequence else 10
        
        return super().create(vals_list)

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_subscription(self):
        """View parent subscription product."""
        self.ensure_one()
        
        return {
            'name': f'Subscription - {self.subscription_product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': self.subscription_product_id.id,
        }

    def action_test_benefit_access(self):
        """Test benefit access (for digital benefits)."""
        self.ensure_one()
        
        if self.digital_access_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.digital_access_url,
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Benefit Test',
                    'message': f'Testing access to benefit: {self.name}',
                    'type': 'info',
                }
            }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_benefits_by_type(self, benefit_type):
        """Get all benefits of a specific type.
        
        Args:
            benefit_type: Type of benefit to retrieve
            
        Returns:
            recordset: Benefits of specified type
        """
        return self.search([
            ('benefit_type', '=', benefit_type),
            ('active', '=', True)
        ])

    @api.model
    def get_available_benefits(self, subscription_product_id, check_date=None):
        """Get all currently available benefits for a subscription.
        
        Args:
            subscription_product_id: ID of subscription product
            check_date: Date to check availability (defaults to today)
            
        Returns:
            recordset: Available benefits
        """
        if not check_date:
            check_date = fields.Date.today()
        
        domain = [
            ('subscription_product_id', '=', subscription_product_id),
            ('active', '=', True),
            '|',
                ('available_from', '=', False),
                ('available_from', '<=', check_date),
            '|',
                ('available_until', '=', False),
                ('available_until', '>=', check_date),
        ]
        
        return self.search(domain)

    def get_benefit_display_text(self):
        """Get formatted display text for the benefit."""
        self.ensure_one()
        
        text_parts = [self.name]
        
        if self.benefit_type == 'discount' and self.discount_percentage:
            text_parts.append(f"- {self.discount_percentage}% discount")
        elif self.monetary_value:
            text_parts.append(f"- ${self.monetary_value} value")
        
        if self.usage_limit:
            text_parts.append(f"(Limited to {self.usage_limit} uses per {self.usage_period})")
        
        return " ".join(text_parts)

    # ==========================================
    # DISPLAY AND SEARCH METHODS
    # ==========================================

    def name_get(self):
        """Custom display name with benefit type."""
        result = []
        for record in self:
            if record.benefit_type:
                type_label = dict(record._fields['benefit_type'].selection)[record.benefit_type]
                name = f"[{type_label}] {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including description and subscription name."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|',
                     ('name', operator, name),
                     ('description', operator, name),
                     ('subscription_product_id.name', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)