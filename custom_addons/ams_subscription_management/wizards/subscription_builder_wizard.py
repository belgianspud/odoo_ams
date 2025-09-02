from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AMSSubscriptionBuilderWizard(models.TransientModel):
    """Guided wizard for setting up subscription products with intelligent defaults."""
    _name = 'ams.subscription.builder.wizard'
    _description = 'Subscription Builder Wizard'

    # ==========================================
    # STEP TRACKING FIELDS
    # ==========================================
    
    current_step = fields.Selection([
        ('basic', 'Basic Information'),
        ('pricing', 'Pricing Setup'),
        ('enterprise', 'Enterprise Settings'),
        ('advanced', 'Advanced Options'),
        ('review', 'Review & Create')
    ], string='Current Step', default='basic', required=True)
    
    total_steps = fields.Integer(
        string='Total Steps',
        default=5,
        help='Total number of steps in wizard'
    )

    # ==========================================
    # BASIC INFORMATION FIELDS (Step 1)
    # ==========================================
    
    product_id = fields.Many2one(
        'product.template',
        string='Base Product',
        required=True,
        help='Product to convert to subscription'
    )
    
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name',
        readonly=True
    )
    
    base_price = fields.Monetary(
        string='Base Product Price',
        related='product_id.list_price',
        readonly=True,
        currency_field='currency_id'
    )
    
    subscription_scope = fields.Selection([
        ('individual', 'Individual Subscription'),
        ('enterprise', 'Enterprise Subscription')
    ], string='Subscription Type', required=True, default='individual',
       help='Individual for single users, Enterprise for organizations')
    
    product_type = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('committee', 'Committee'),
        ('publication', 'Publication')
    ], string='Subscription Category', required=True, default='membership',
       help='Type of subscription for business logic')
    
    subscription_name = fields.Char(
        string='Subscription Name',
        help='Name for the subscription product (auto-generated if empty)'
    )

    # ==========================================
    # DURATION & LIFECYCLE FIELDS (Step 1)
    # ==========================================
    
    default_duration = fields.Integer(
        string='Subscription Duration',
        required=True,
        default=12,
        help='Length of subscription'
    )
    
    duration_unit = fields.Selection([
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Duration Unit', required=True, default='months')
    
    billing_period_id = fields.Many2one(
        'ams.billing.period',
        string='Billing Period',
        help='How often customer is billed'
    )
    
    is_renewable = fields.Boolean(
        string='Renewable Subscription',
        default=True,
        help='Subscription can be renewed'
    )

    # ==========================================
    # PRICING CONFIGURATION FIELDS (Step 2)
    # ==========================================
    
    pricing_strategy = fields.Selection([
        ('simple', 'Simple Pricing (One Price)'),
        ('member_tiers', 'Member Pricing Tiers'),
        ('promotional', 'Promotional Pricing'),
        ('custom', 'Custom Configuration')
    ], string='Pricing Strategy', default='simple', required=True)
    
    default_price = fields.Monetary(
        string='Default Subscription Price',
        required=True,
        currency_field='currency_id',
        help='Base subscription price'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    # Member pricing quick setup
    enable_student_pricing = fields.Boolean(
        string='Student Discount',
        default=False,
        help='Offer discounted pricing for students'
    )
    
    student_discount_percentage = fields.Float(
        string='Student Discount %',
        default=50.0,
        help='Discount percentage for students'
    )
    
    enable_senior_pricing = fields.Boolean(
        string='Senior/Retired Discount',
        default=False,
        help='Offer discounted pricing for seniors/retired members'
    )
    
    senior_discount_percentage = fields.Float(
        string='Senior Discount %',
        default=25.0,
        help='Discount percentage for seniors'
    )
    
    enable_international_pricing = fields.Boolean(
        string='International Pricing',
        default=False,
        help='Different pricing for international members'
    )
    
    international_discount_percentage = fields.Float(
        string='International Discount %',
        default=20.0,
        help='Discount percentage for international members'
    )

    # ==========================================
    # ENTERPRISE SETTINGS FIELDS (Step 3)
    # ==========================================
    
    default_seat_count = fields.Integer(
        string='Default Number of Seats',
        default=5,
        help='Base number of seats included'
    )
    
    allow_additional_seats = fields.Boolean(
        string='Allow Additional Seat Purchase',
        default=True,
        help='Customers can buy extra seats'
    )
    
    additional_seat_price = fields.Monetary(
        string='Additional Seat Price',
        currency_field='currency_id',
        help='Price per additional seat'
    )
    
    max_additional_seats = fields.Integer(
        string='Maximum Additional Seats',
        default=100,
        help='Maximum extra seats allowed (0 = unlimited)'
    )

    # ==========================================
    # ADVANCED OPTIONS FIELDS (Step 4)
    # ==========================================
    
    requires_approval = fields.Boolean(
        string='Requires Staff Approval',
        default=False,
        help='Staff must approve subscription purchases'
    )
    
    member_only = fields.Boolean(
        string='Members Only',
        default=False,
        help='Restrict to current association members'
    )
    
    auto_renewal_enabled = fields.Boolean(
        string='Enable Auto-Renewal',
        default=False,
        help='Support automatic renewal'
    )
    
    renewal_window_days = fields.Integer(
        string='Renewal Window (Days)',
        default=90,
        help='Days before expiration to allow renewal'
    )
    
    eligible_member_types = fields.Many2many(
        'ams.member.type',
        string='Eligible Member Types',
        help='Restrict to specific member types (empty = all types)'
    )

    # ==========================================
    # REVIEW AND CREATION FIELDS (Step 5)
    # ==========================================
    
    subscription_description = fields.Html(
        string='Subscription Description',
        help='Detailed description of subscription benefits'
    )
    
    terms_and_conditions = fields.Html(
        string='Terms & Conditions',
        help='Subscription-specific terms and conditions'
    )
    
    create_immediately = fields.Boolean(
        string='Create Subscription Product',
        default=True,
        help='Create the subscription product when wizard completes'
    )
    
    # Summary fields for review
    pricing_summary = fields.Text(
        string='Pricing Summary',
        compute='_compute_pricing_summary',
        help='Summary of pricing configuration'
    )
    
    configuration_summary = fields.Text(
        string='Configuration Summary',
        compute='_compute_configuration_summary',
        help='Summary of subscription configuration'
    )

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('default_price', 'enable_student_pricing', 'student_discount_percentage',
                 'enable_senior_pricing', 'senior_discount_percentage',
                 'enable_international_pricing', 'international_discount_percentage')
    def _compute_pricing_summary(self):
        """Generate pricing summary for review."""
        for wizard in self:
            summary = [f"Base Price: {wizard.default_price:.2f} {wizard.currency_id.name}"]
            
            if wizard.enable_student_pricing:
                student_price = wizard.default_price * (1 - wizard.student_discount_percentage / 100)
                summary.append(f"Student Price: {student_price:.2f} ({wizard.student_discount_percentage:.0f}% off)")
            
            if wizard.enable_senior_pricing:
                senior_price = wizard.default_price * (1 - wizard.senior_discount_percentage / 100)
                summary.append(f"Senior Price: {senior_price:.2f} ({wizard.senior_discount_percentage:.0f}% off)")
            
            if wizard.enable_international_pricing:
                intl_price = wizard.default_price * (1 - wizard.international_discount_percentage / 100)
                summary.append(f"International Price: {intl_price:.2f} ({wizard.international_discount_percentage:.0f}% off)")
            
            wizard.pricing_summary = "\n".join(summary)

    @api.depends('subscription_scope', 'product_type', 'default_duration', 'duration_unit',
                 'default_seat_count', 'requires_approval', 'member_only')
    def _compute_configuration_summary(self):
        """Generate configuration summary for review."""
        for wizard in self:
            summary = []
            
            # Basic configuration
            summary.append(f"Type: {dict(wizard._fields['product_type'].selection)[wizard.product_type]}")
            summary.append(f"Scope: {dict(wizard._fields['subscription_scope'].selection)[wizard.subscription_scope]}")
            summary.append(f"Duration: {wizard.default_duration} {wizard.duration_unit}")
            
            # Enterprise settings
            if wizard.subscription_scope == 'enterprise':
                summary.append(f"Base Seats: {wizard.default_seat_count}")
                if wizard.allow_additional_seats:
                    summary.append(f"Additional Seats: {wizard.additional_seat_price:.2f} each")
            
            # Access restrictions
            if wizard.member_only:
                summary.append("Access: Members Only")
            if wizard.requires_approval:
                summary.append("Requires: Staff Approval")
            
            # Renewal settings
            if wizard.is_renewable:
                summary.append(f"Renewable: Yes ({wizard.renewal_window_days} days window)")
                if wizard.auto_renewal_enabled:
                    summary.append("Auto-Renewal: Enabled")
            
            wizard.configuration_summary = "\n".join(summary)

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set intelligent defaults based on product selection."""
        if self.product_id:
            # Auto-generate subscription name
            self.subscription_name = f"{self.product_id.name} Subscription"
            
            # Set default price from product
            self.default_price = self.product_id.list_price
            
            # Intelligent defaults based on product name
            product_name = self.product_id.name.lower()
            
            # Determine product type
            if any(word in product_name for word in ['member', 'membership']):
                self.product_type = 'membership'
            elif any(word in product_name for word in ['chapter', 'local']):
                self.product_type = 'chapter'
            elif any(word in product_name for word in ['committee', 'board']):
                self.product_type = 'committee'
            elif any(word in product_name for word in ['journal', 'publication', 'magazine']):
                self.product_type = 'publication'
            
            # Determine scope
            if any(word in product_name for word in ['enterprise', 'corporate', 'organization']):
                self.subscription_scope = 'enterprise'
            else:
                self.subscription_scope = 'individual'

    @api.onchange('subscription_scope')
    def _onchange_subscription_scope(self):
        """Handle subscription scope changes."""
        if self.subscription_scope == 'individual':
            # Clear enterprise-specific fields
            self.default_seat_count = 1
            self.allow_additional_seats = False
            self.additional_seat_price = 0.0
            self.max_additional_seats = 0
        else:
            # Set enterprise defaults
            if not self.default_seat_count or self.default_seat_count == 1:
                self.default_seat_count = 5
            self.allow_additional_seats = True
            if not self.additional_seat_price:
                self.additional_seat_price = self.default_price * 0.2  # 20% of base price

    @api.onchange('pricing_strategy')
    def _onchange_pricing_strategy(self):
        """Handle pricing strategy changes."""
        if self.pricing_strategy == 'simple':
            # Disable all member pricing options
            self.enable_student_pricing = False
            self.enable_senior_pricing = False
            self.enable_international_pricing = False
        elif self.pricing_strategy == 'member_tiers':
            # Enable common member pricing tiers
            self.enable_student_pricing = True
            self.enable_senior_pricing = True

    @api.onchange('default_price')
    def _onchange_default_price(self):
        """Update additional seat price when default price changes."""
        if self.subscription_scope == 'enterprise' and not self.additional_seat_price:
            self.additional_seat_price = self.default_price * 0.2

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('student_discount_percentage', 'senior_discount_percentage', 'international_discount_percentage')
    def _check_discount_percentages(self):
        """Validate discount percentages are reasonable."""
        for wizard in self:
            for field_name, label in [
                ('student_discount_percentage', 'Student'),
                ('senior_discount_percentage', 'Senior'),
                ('international_discount_percentage', 'International')
            ]:
                value = getattr(wizard, field_name)
                if value < 0 or value > 100:
                    raise ValidationError(f"{label} discount percentage must be between 0 and 100")

    @api.constrains('default_seat_count', 'max_additional_seats')
    def _check_seat_counts(self):
        """Validate seat count settings."""
        for wizard in self:
            if wizard.subscription_scope == 'enterprise':
                if wizard.default_seat_count < 1:
                    raise ValidationError("Default seat count must be at least 1 for enterprise subscriptions")
                if wizard.max_additional_seats < 0:
                    raise ValidationError("Maximum additional seats cannot be negative")

    # ==========================================
    # NAVIGATION METHODS
    # ==========================================

    def action_next_step(self):
        """Move to the next step in the wizard."""
        steps = ['basic', 'pricing', 'enterprise', 'advanced', 'review']
        current_index = steps.index(self.current_step)
        
        # Validate current step before proceeding
        self._validate_current_step()
        
        # Skip enterprise step for individual subscriptions
        if self.current_step == 'pricing' and self.subscription_scope == 'individual':
            self.current_step = 'advanced'
        elif current_index < len(steps) - 1:
            self.current_step = steps[current_index + 1]
        
        return self._return_wizard_action()

    def action_previous_step(self):
        """Move to the previous step in the wizard."""
        steps = ['basic', 'pricing', 'enterprise', 'advanced', 'review']
        current_index = steps.index(self.current_step)
        
        # Skip enterprise step for individual subscriptions
        if self.current_step == 'advanced' and self.subscription_scope == 'individual':
            self.current_step = 'pricing'
        elif current_index > 0:
            self.current_step = steps[current_index - 1]
        
        return self._return_wizard_action()

    def action_jump_to_step(self, step):
        """Jump directly to a specific step."""
        valid_steps = ['basic', 'pricing', 'enterprise', 'advanced', 'review']
        if step in valid_steps:
            self.current_step = step
        return self._return_wizard_action()

    def _validate_current_step(self):
        """Validate the current step before proceeding."""
        if self.current_step == 'basic':
            if not self.product_id:
                raise UserError("Please select a base product")
            if not self.subscription_name:
                raise UserError("Please enter a subscription name")
        
        elif self.current_step == 'pricing':
            if not self.default_price or self.default_price <= 0:
                raise UserError("Please enter a valid default price")
        
        elif self.current_step == 'enterprise' and self.subscription_scope == 'enterprise':
            if not self.default_seat_count or self.default_seat_count < 1:
                raise UserError("Please enter a valid default seat count")

    def _return_wizard_action(self):
        """Return action to refresh wizard view."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # CREATION METHODS
    # ==========================================

    def action_create_subscription(self):
        """Create the subscription product based on wizard configuration."""
        self._validate_all_steps()
        
        # Create subscription product
        subscription_vals = self._prepare_subscription_values()
        subscription_product = self.env['ams.subscription.product'].create(subscription_vals)
        
        # Update base product
        self.product_id.write({
            'is_subscription_product': True,
            'subscription_product_id': subscription_product.id,
            'detailed_type': 'service',
        })
        
        # Create pricing tiers if configured
        self._create_pricing_tiers(subscription_product)
        
        # Show success message and open created subscription
        return {
            'name': f'Subscription Product Created - {subscription_product.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'res_id': subscription_product.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_subscription_values(self):
        """Prepare values for subscription product creation."""
        return {
            'name': self.subscription_name,
            'code': f"SUB_{self.product_id.default_code or self.product_id.id}",
            'product_id': self.product_id.id,
            'subscription_scope': self.subscription_scope,
            'product_type': self.product_type,
            'default_duration': self.default_duration,
            'duration_unit': self.duration_unit,
            'default_price': self.default_price,
            'currency_id': self.currency_id.id,
            'default_seat_count': self.default_seat_count if self.subscription_scope == 'enterprise' else 0,
            'allow_seat_purchase': self.allow_additional_seats,
            'is_renewable': self.is_renewable,
            'renewal_window_days': self.renewal_window_days,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'requires_approval': self.requires_approval,
            'member_only': self.member_only,
            'description': self.subscription_description,
            'terms_and_conditions': self.terms_and_conditions,
            'active': True,
        }

    def _create_pricing_tiers(self, subscription_product):
        """Create pricing tiers based on wizard configuration."""
        tiers_to_create = []
        
        if self.enable_student_pricing:
            student_type = self.env['ams.member.type'].search([
                ('code', 'ilike', 'student')
            ], limit=1)
            if student_type:
                student_price = self.default_price * (1 - self.student_discount_percentage / 100)
                tiers_to_create.append({
                    'subscription_product_id': subscription_product.id,
                    'member_type_id': student_type.id,
                    'price': student_price,
                    'currency_id': self.currency_id.id,
                    'requires_verification': True,
                    'verification_criteria': 'Valid student enrollment verification required',
                })
        
        if self.enable_senior_pricing:
            senior_type = self.env['ams.member.type'].search([
                '|', ('code', 'ilike', 'senior'), ('code', 'ilike', 'retired')
            ], limit=1)
            if senior_type:
                senior_price = self.default_price * (1 - self.senior_discount_percentage / 100)
                tiers_to_create.append({
                    'subscription_product_id': subscription_product.id,
                    'member_type_id': senior_type.id,
                    'price': senior_price,
                    'currency_id': self.currency_id.id,
                })
        
        if self.enable_international_pricing:
            intl_type = self.env['ams.member.type'].search([
                ('code', 'ilike', 'international')
            ], limit=1)
            if intl_type:
                intl_price = self.default_price * (1 - self.international_discount_percentage / 100)
                tiers_to_create.append({
                    'subscription_product_id': subscription_product.id,
                    'member_type_id': intl_type.id,
                    'price': intl_price,
                    'currency_id': self.currency_id.id,
                })
        
        if tiers_to_create:
            self.env['ams.subscription.pricing.tier'].create(tiers_to_create)

    def _validate_all_steps(self):
        """Validate all wizard steps before creation."""
        self._validate_current_step()  # Validate current step
        
        if not self.create_immediately:
            raise UserError("Creation is disabled")

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def action_cancel_wizard(self):
        """Cancel wizard and return to product form."""
        return {
            'name': f'Product - {self.product_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def default_get(self, fields_list):
        """Set intelligent defaults when wizard is opened."""
        defaults = super().default_get(fields_list)
        
        # Get product from context if provided
        product_id = self.env.context.get('default_product_id')
        if product_id:
            product = self.env['product.template'].browse(product_id)
            if product.exists():
                defaults.update({
                    'product_name': product.name,
                    'base_price': product.list_price,
                    'default_price': product.list_price,
                    'subscription_name': f"{product.name} Subscription",
                })
        
        return defaults