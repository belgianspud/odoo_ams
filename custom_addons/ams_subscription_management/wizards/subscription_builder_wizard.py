from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AMSSubscriptionBuilderWizard(models.TransientModel):
    """Guided wizard for creating subscription products with smart defaults."""
    _name = 'ams.subscription.builder.wizard'
    _description = 'Subscription Product Builder Wizard'

    # ==========================================
    # WIZARD STATE MANAGEMENT
    # ==========================================
    
    state = fields.Selection([
        ('basic', 'Basic Information'),
        ('configuration', 'Configuration'),
        ('pricing', 'Pricing Setup'),
        ('review', 'Review & Create'),
        ('complete', 'Complete')
    ], string='Wizard Step', default='basic', required=True)
    
    # ==========================================
    # BASIC INFORMATION FIELDS
    # ==========================================
    
    product_id = fields.Many2one(
        'product.template',
        string='Base Product',
        help='Existing product to convert to subscription'
    )
    
    create_new_product = fields.Boolean(
        string='Create New Product',
        default=True,
        help='Create a new product instead of using existing one'
    )
    
    product_name = fields.Char(
        string='Product Name',
        required=True,
        help='Name for the subscription product'
    )
    
    product_code = fields.Char(
        string='Product Code',
        help='Unique code for the product'
    )
    
    subscription_scope = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('enterprise', 'Enterprise Subscription')
    ], string='Subscription Scope',
       required=True,
       default='individual',
       help='Target audience for this subscription')
    
    product_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('committee', 'Committee'),
        ('publication', 'Publication')
    ], string='Product Type',
       required=True,
       default='membership',
       help='Type of subscription offering')
    
    # ==========================================
    # CONFIGURATION FIELDS
    # ==========================================
    
    default_duration = fields.Integer(
        string='Duration',
        required=True,
        default=12,
        help='Subscription duration'
    )
    
    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Duration Unit',
       required=True,
       default='months',
       help='Unit for duration calculation')
    
    default_price = fields.Monetary(
        string='Base Price',
        required=True,
        currency_field='currency_id',
        help='Base subscription price'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Currency for pricing'
    )
    
    # ==========================================
    # ADVANCED CONFIGURATION
    # ==========================================
    
    is_renewable = fields.Boolean(
        string='Is Renewable',
        default=True,
        help='Subscription can be renewed'
    )
    
    auto_renewal_enabled = fields.Boolean(
        string='Auto-Renewal Available',
        help='Subscription supports automatic renewal'
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        help='Staff approval required before activation'
    )
    
    member_only = fields.Boolean(
        string='Members Only',
        help='Restricted to current association members'
    )
    
    # ==========================================
    # ENTERPRISE SPECIFIC FIELDS
    # ==========================================
    
    default_seat_count = fields.Integer(
        string='Default Seats',
        default=10,
        help='Default number of seats for enterprise subscriptions'
    )
    
    allow_seat_purchase = fields.Boolean(
        string='Allow Additional Seats',
        default=True,
        help='Enable purchasing extra seats beyond default allocation'
    )
    
    # ==========================================
    # PRICING CONFIGURATION
    # ==========================================
    
    setup_member_pricing = fields.Boolean(
        string='Setup Member Pricing',
        default=True,
        help='Configure different pricing for member types'
    )
    
    pricing_strategy = fields.Selection([
        ('manual', 'Manual Pricing'),
        ('percentage', 'Percentage Discounts'),
        ('template', 'Use Template')
    ], string='Pricing Strategy',
       default='percentage',
       help='How to configure member pricing')
    
    student_discount = fields.Float(
        string='Student Discount %',
        default=50.0,
        help='Percentage discount for student members'
    )
    
    retired_discount = fields.Float(
        string='Retired Discount %',
        default=25.0,
        help='Percentage discount for retired members'
    )
    
    corporate_markup = fields.Float(
        string='Corporate Markup %',
        default=0.0,
        help='Percentage markup for corporate members'
    )
    
    # ==========================================
    # TEMPLATE SELECTION
    # ==========================================
    
    subscription_template = fields.Selection([
        ('professional_association', 'Professional Association'),
        ('trade_organization', 'Trade Organization'),
        ('academic_institution', 'Academic Institution'),
        ('membership_club', 'Membership Club'),
        ('custom', 'Custom Configuration')
    ], string='Subscription Template',
       default='professional_association',
       help='Pre-configured template for common subscription types')
    
    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    estimated_student_price = fields.Monetary(
        string='Estimated Student Price',
        compute='_compute_estimated_prices',
        currency_field='currency_id',
        help='Calculated student price'
    )
    
    estimated_retired_price = fields.Monetary(
        string='Estimated Retired Price',
        compute='_compute_estimated_prices',
        currency_field='currency_id',
        help='Calculated retired price'
    )
    
    estimated_corporate_price = fields.Monetary(
        string='Estimated Corporate Price',
        compute='_compute_estimated_prices',
        currency_field='currency_id',
        help='Calculated corporate price'
    )
    
    duration_display = fields.Char(
        string='Duration Display',
        compute='_compute_duration_display',
        help='Human-readable duration'
    )
    
    # ==========================================
    # RESULT FIELDS
    # ==========================================
    
    created_product_id = fields.Many2one(
        'product.template',
        string='Created Product',
        readonly=True,
        help='Product created by the wizard'
    )
    
    created_subscription_id = fields.Many2one(
        'ams.subscription.product',
        string='Created Subscription',
        readonly=True,
        help='Subscription product created by the wizard'
    )

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('default_price', 'student_discount', 'retired_discount', 'corporate_markup')
    def _compute_estimated_prices(self):
        """Calculate estimated prices based on discounts."""
        for record in self:
            if record.default_price:
                # Student price (discount)
                student_discount_amount = record.default_price * (record.student_discount / 100)
                record.estimated_student_price = record.default_price - student_discount_amount
                
                # Retired price (discount)
                retired_discount_amount = record.default_price * (record.retired_discount / 100)
                record.estimated_retired_price = record.default_price - retired_discount_amount
                
                # Corporate price (markup)
                corporate_markup_amount = record.default_price * (record.corporate_markup / 100)
                record.estimated_corporate_price = record.default_price + corporate_markup_amount
            else:
                record.estimated_student_price = 0.0
                record.estimated_retired_price = 0.0
                record.estimated_corporate_price = 0.0

    @api.depends('default_duration', 'duration_unit')
    def _compute_duration_display(self):
        """Generate human-readable duration display."""
        for record in self:
            if record.default_duration and record.duration_unit:
                unit_name = dict(record._fields['duration_unit'].selection)[record.duration_unit]
                if record.default_duration == 1:
                    unit_name = unit_name.rstrip('s')
                record.duration_display = f"{record.default_duration} {unit_name}"
            else:
                record.duration_display = "Not configured"

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('subscription_template')
    def _onchange_subscription_template(self):
        """Apply template defaults when template is selected."""
        if self.subscription_template == 'professional_association':
            self.product_type = 'membership'
            self.subscription_scope = 'individual'
            self.default_duration = 12
            self.duration_unit = 'months'
            self.is_renewable = True
            self.auto_renewal_enabled = True
            self.requires_approval = False
            self.member_only = False
            self.student_discount = 50.0
            self.retired_discount = 25.0
            self.corporate_markup = 0.0
        
        elif self.subscription_template == 'trade_organization':
            self.product_type = 'membership'
            self.subscription_scope = 'individual'
            self.default_duration = 12
            self.duration_unit = 'months'
            self.is_renewable = True
            self.auto_renewal_enabled = True
            self.requires_approval = False
            self.member_only = False
            self.student_discount = 25.0
            self.retired_discount = 15.0
            self.corporate_markup = 50.0
        
        elif self.subscription_template == 'academic_institution':
            self.product_type = 'membership'
            self.subscription_scope = 'individual'
            self.default_duration = 9
            self.duration_unit = 'months'
            self.is_renewable = True
            self.auto_renewal_enabled = False
            self.requires_approval = True
            self.member_only = False
            self.student_discount = 75.0
            self.retired_discount = 50.0
            self.corporate_markup = 0.0
        
        elif self.subscription_template == 'membership_club':
            self.product_type = 'membership'
            self.subscription_scope = 'individual'
            self.default_duration = 12
            self.duration_unit = 'months'
            self.is_renewable = True
            self.auto_renewal_enabled = True
            self.requires_approval = False
            self.member_only = True
            self.student_discount = 30.0
            self.retired_discount = 20.0
            self.corporate_markup = 0.0

    @api.onchange('create_new_product')
    def _onchange_create_new_product(self):
        """Clear product selection when switching modes."""
        if self.create_new_product:
            self.product_id = False
        else:
            self.product_name = ""
            self.product_code = ""

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill fields from selected product."""
        if self.product_id and not self.create_new_product:
            # Ensure we have a valid product record
            product = self.product_id
            if product and hasattr(product, 'name'):
                self.product_name = product.name or ""
                self.product_code = product.default_code or ""
                self.default_price = product.list_price or 0.0

    @api.onchange('subscription_scope')
    def _onchange_subscription_scope(self):
        """Update enterprise-specific defaults."""
        if self.subscription_scope == 'enterprise':
            if not self.default_seat_count:
                self.default_seat_count = 10
            self.allow_seat_purchase = True
        else:
            self.default_seat_count = 0
            self.allow_seat_purchase = False

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('default_duration')
    def _validate_duration(self):
        """Validate duration is positive."""
        for record in self:
            if record.default_duration <= 0:
                raise ValidationError("Duration must be positive.")

    @api.constrains('default_price')
    def _validate_price(self):
        """Validate price is non-negative."""
        for record in self:
            if record.default_price < 0:
                raise ValidationError("Price cannot be negative.")

    @api.constrains('student_discount', 'retired_discount')
    def _validate_discounts(self):
        """Validate discount percentages."""
        for record in self:
            if record.student_discount < 0 or record.student_discount > 100:
                raise ValidationError("Student discount must be between 0 and 100%.")
            if record.retired_discount < 0 or record.retired_discount > 100:
                raise ValidationError("Retired discount must be between 0 and 100%.")

    # ==========================================
    # WIZARD NAVIGATION METHODS
    # ==========================================

    def action_next_step(self):
        """Move to next wizard step."""
        if self.state == 'basic':
            self._validate_basic_info()
            self.state = 'configuration'
        elif self.state == 'configuration':
            self._validate_configuration()
            self.state = 'pricing'
        elif self.state == 'pricing':
            self._validate_pricing()
            self.state = 'review'
        elif self.state == 'review':
            return self.action_create_subscription()
        
        return self._reload_wizard()

    def action_previous_step(self):
        """Move to previous wizard step."""
        if self.state == 'configuration':
            self.state = 'basic'
        elif self.state == 'pricing':
            self.state = 'configuration'
        elif self.state == 'review':
            self.state = 'pricing'
        
        return self._reload_wizard()

    def action_skip_step(self):
        """Skip current step with defaults."""
        return self.action_next_step()

    def _reload_wizard(self):
        """Reload wizard form."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    def _validate_basic_info(self):
        """Validate basic information step."""
        if not self.product_name:
            raise ValidationError("Product name is required.")
        
        if not self.create_new_product and not self.product_id:
            raise ValidationError("Please select an existing product or choose to create a new one.")

    def _validate_configuration(self):
        """Validate configuration step."""
        if self.default_duration <= 0:
            raise ValidationError("Duration must be positive.")
        
        if self.default_price < 0:
            raise ValidationError("Price cannot be negative.")
        
        if self.subscription_scope == 'enterprise' and self.default_seat_count <= 0:
            raise ValidationError("Enterprise subscriptions must have at least 1 default seat.")

    def _validate_pricing(self):
        """Validate pricing step."""
        if self.setup_member_pricing and self.pricing_strategy == 'percentage':
            if self.student_discount < 0 or self.student_discount > 100:
                raise ValidationError("Student discount must be between 0 and 100%.")
            if self.retired_discount < 0 or self.retired_discount > 100:
                raise ValidationError("Retired discount must be between 0 and 100%.")

    # ==========================================
    # CREATION METHODS
    # ==========================================

    def action_create_subscription(self):
        """Create the subscription product."""
        try:
            # Create or get product
            if self.create_new_product:
                product = self._create_product()
            else:
                product = self.product_id
                # Ensure we have a valid product record before calling write
                if product and hasattr(product, 'write'):
                    # Update product to be subscription-enabled
                    product.write({
                        'is_subscription_product': True,
                        'detailed_type': 'service',
                        'sale_ok': True,
                    })
            
            # Create subscription configuration
            subscription = self._create_subscription_product(product)
            
            # Setup pricing tiers
            if self.setup_member_pricing:
                self._create_pricing_tiers(subscription)
            
            # Store results
            self.created_product_id = product.id
            self.created_subscription_id = subscription.id
            self.state = 'complete'
            
            return self._show_success_message()
            
        except Exception as e:
            raise UserError(f"Failed to create subscription: {str(e)}")

    def _create_product(self):
        """Create new product."""
        vals = {
            'name': self.product_name,
            'default_code': self.product_code,
            'list_price': self.default_price,
            'detailed_type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'is_subscription_product': True,
        }
        
        return self.env['product.template'].create(vals)

    def _create_subscription_product(self, product):
        """Create subscription configuration."""
        vals = {
            'name': f"{product.name} Subscription",
            'code': self._generate_subscription_code(product),
            'product_id': product.id,
            'subscription_scope': self.subscription_scope,
            'product_type': self.product_type,
            'default_duration': self.default_duration,
            'duration_unit': self.duration_unit,
            'default_price': self.default_price,
            'currency_id': self.currency_id.id,
            'is_renewable': self.is_renewable,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'requires_approval': self.requires_approval,
            'member_only': self.member_only,
        }
        
        # Add enterprise-specific fields
        if self.subscription_scope == 'enterprise':
            vals.update({
                'default_seat_count': self.default_seat_count,
                'allow_seat_purchase': self.allow_seat_purchase,
            })
        
        return self.env['ams.subscription.product'].create(vals)

    def _create_pricing_tiers(self, subscription):
        """Create member pricing tiers."""
        if self.pricing_strategy != 'percentage':
            return
        
        # Get member types
        member_types = self.env['ams.member.type'].search([])
        
        for member_type in member_types:
            price = self.default_price
            
            # Apply discounts/markups based on member type
            if member_type.code == 'student' and self.student_discount > 0:
                price = self.default_price * (1 - self.student_discount / 100)
            elif member_type.code == 'retired' and self.retired_discount > 0:
                price = self.default_price * (1 - self.retired_discount / 100)
            elif member_type.code == 'corporate' and self.corporate_markup > 0:
                price = self.default_price * (1 + self.corporate_markup / 100)
            
            # Only create tier if price is different from default
            if abs(price - self.default_price) > 0.01:
                self.env['ams.subscription.pricing.tier'].create({
                    'subscription_product_id': subscription.id,
                    'member_type_id': member_type.id,
                    'price': price,
                    'currency_id': self.currency_id.id,
                })

    def _generate_subscription_code(self, product):
        """Generate unique subscription code."""
        base_code = product.default_code or f"SUB_{product.id}"
        
        # Ensure uniqueness
        existing = self.env['ams.subscription.product'].search([
            ('code', '=', base_code)
        ])
        
        if existing:
            counter = 1
            while True:
                candidate = f"{base_code}_{counter}"
                if not self.env['ams.subscription.product'].search([('code', '=', candidate)]):
                    return candidate
                counter += 1
        
        return base_code

    def _show_success_message(self):
        """Show success message and options."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_created_product(self):
        """View the created product."""
        if not self.created_product_id:
            raise UserError("No product has been created yet.")
        
        return {
            'name': f'Product - {self.created_product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.created_product_id.id,
        }

    def action_view_created_subscription(self):
        """View the created subscription."""
        if not self.created_subscription_id:
            raise UserError("No subscription has been created yet.")
        
        return {
            'name': f'Subscription - {self.created_subscription_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': self.created_subscription_id.id,
        }

    def action_create_another(self):
        """Create another subscription."""
        return {
            'name': 'Create Subscription Product',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_template': self.subscription_template},
        }