from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AMSPricingTierWizard(models.TransientModel):
    """Wizard for bulk pricing tier management and setup."""
    _name = 'ams.pricing.tier.wizard'
    _description = 'Pricing Tier Management Wizard'

    # ==========================================
    # WIZARD CONFIGURATION
    # ==========================================
    
    wizard_type = fields.Selection([
        ('bulk_create', 'Bulk Create Pricing Tiers'),
        ('bulk_update', 'Bulk Update Pricing Tiers'),
        ('copy_pricing', 'Copy Pricing from Another Subscription'),
        ('percentage_adjustment', 'Percentage Price Adjustment'),
        ('template_application', 'Apply Pricing Template')
    ], string='Wizard Type',
       required=True,
       default='bulk_create',
       help='Type of pricing operation to perform')
    
    state = fields.Selection([
        ('selection', 'Selection'),
        ('configuration', 'Configuration'),
        ('review', 'Review'),
        ('complete', 'Complete')
    ], string='Wizard Step', default='selection', required=True)
    
    # ==========================================
    # TARGET SELECTION
    # ==========================================
    
    subscription_product_ids = fields.Many2many(
        'ams.subscription.product',
        string='Target Subscription Products',
        help='Subscription products to apply pricing changes to'
    )
    
    member_type_ids = fields.Many2many(
        'ams.member.type',
        string='Target Member Types',
        help='Member types to create/update pricing for'
    )
    
    apply_to_all_subscriptions = fields.Boolean(
        string='Apply to All Active Subscriptions',
        help='Apply changes to all active subscription products'
    )
    
    apply_to_all_member_types = fields.Boolean(
        string='Apply to All Member Types',
        help='Apply changes to all member types'
    )
    
    # ==========================================
    # PRICING CONFIGURATION
    # ==========================================
    
    pricing_method = fields.Selection([
        ('fixed_amount', 'Fixed Amount'),
        ('percentage_discount', 'Percentage Discount from Default'),
        ('percentage_markup', 'Percentage Markup from Default'),
        ('copy_from_tier', 'Copy from Existing Tier')
    ], string='Pricing Method',
       default='percentage_discount',
       help='How to calculate the new prices')
    
    fixed_price = fields.Monetary(
        string='Fixed Price',
        currency_field='currency_id',
        help='Fixed price amount'
    )
    
    percentage_value = fields.Float(
        string='Percentage',
        help='Percentage for discount/markup calculation'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency for pricing'
    )
    
    # ==========================================
    # COPY/TEMPLATE SOURCE
    # ==========================================
    
    source_subscription_id = fields.Many2one(
        'ams.subscription.product',
        string='Source Subscription',
        help='Subscription to copy pricing from'
    )
    
    source_member_type_id = fields.Many2one(
        'ams.member.type',
        string='Source Member Type',
        help='Member type to copy pricing from'
    )
    
    pricing_template = fields.Selection([
        ('student_heavy_discount', 'Student Heavy Discount (75% off)'),
        ('student_standard_discount', 'Student Standard Discount (50% off)'),
        ('student_light_discount', 'Student Light Discount (25% off)'),
        ('retired_standard_discount', 'Retired Standard Discount (25% off)'),
        ('corporate_premium', 'Corporate Premium (+50%)'),
        ('nonprofit_discount', 'Nonprofit Discount (30% off)'),
        ('custom', 'Custom Template')
    ], string='Pricing Template',
       help='Pre-defined pricing template to apply')
    
    # ==========================================
    # VALIDITY AND CONDITIONS
    # ==========================================
    
    set_validity_period = fields.Boolean(
        string='Set Validity Period',
        help='Set start and end dates for the pricing'
    )
    
    valid_from = fields.Date(
        string='Valid From',
        help='Start date for the pricing'
    )
    
    valid_to = fields.Date(
        string='Valid Until',
        help='End date for the pricing'
    )
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        help='Member eligibility must be verified for this pricing'
    )
    
    verification_criteria = fields.Text(
        string='Verification Criteria',
        help='Specific requirements for eligibility verification'
    )
    
    # ==========================================
    # OPERATION OPTIONS
    # ==========================================
    
    overwrite_existing = fields.Boolean(
        string='Overwrite Existing Tiers',
        default=False,
        help='Replace existing pricing tiers for selected combinations'
    )
    
    archive_old_tiers = fields.Boolean(
        string='Archive Old Tiers',
        help='Archive existing tiers instead of deleting them'
    )
    
    round_prices = fields.Boolean(
        string='Round Prices',
        default=True,
        help='Round calculated prices to nearest currency unit'
    )
    
    minimum_price = fields.Monetary(
        string='Minimum Price',
        currency_field='currency_id',
        help='Minimum price floor (leave 0 for no minimum)'
    )
    
    # ==========================================
    # PREVIEW AND RESULTS
    # ==========================================
    
    preview_line_ids = fields.One2many(
        'ams.pricing.tier.wizard.line',
        'wizard_id',
        string='Pricing Preview',
        help='Preview of pricing changes to be made'
    )
    
    created_tier_count = fields.Integer(
        string='Created Tiers',
        readonly=True,
        help='Number of pricing tiers created'
    )
    
    updated_tier_count = fields.Integer(
        string='Updated Tiers',
        readonly=True,
        help='Number of pricing tiers updated'
    )
    
    error_count = fields.Integer(
        string='Errors',
        readonly=True,
        help='Number of errors encountered'
    )
    
    operation_log = fields.Text(
        string='Operation Log',
        readonly=True,
        help='Log of operations performed'
    )

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('wizard_type')
    def _onchange_wizard_type(self):
        """Reset fields when wizard type changes."""
        self.state = 'selection'
        self.preview_line_ids = [(5, 0, 0)]  # Clear preview lines

    @api.onchange('apply_to_all_subscriptions')
    def _onchange_apply_to_all_subscriptions(self):
        """Clear subscription selection when applying to all."""
        if self.apply_to_all_subscriptions:
            self.subscription_product_ids = [(5, 0, 0)]

    @api.onchange('apply_to_all_member_types')
    def _onchange_apply_to_all_member_types(self):
        """Clear member type selection when applying to all."""
        if self.apply_to_all_member_types:
            self.member_type_ids = [(5, 0, 0)]

    @api.onchange('pricing_template')
    def _onchange_pricing_template(self):
        """Apply template defaults."""
        if self.pricing_template == 'student_heavy_discount':
            self.pricing_method = 'percentage_discount'
            self.percentage_value = 75.0
            self.requires_verification = True
            self.verification_criteria = "Valid student ID or enrollment verification required."
        
        elif self.pricing_template == 'student_standard_discount':
            self.pricing_method = 'percentage_discount'
            self.percentage_value = 50.0
            self.requires_verification = True
            self.verification_criteria = "Student status verification required."
        
        elif self.pricing_template == 'student_light_discount':
            self.pricing_method = 'percentage_discount'
            self.percentage_value = 25.0
            self.requires_verification = False
        
        elif self.pricing_template == 'retired_standard_discount':
            self.pricing_method = 'percentage_discount'
            self.percentage_value = 25.0
            self.requires_verification = False
        
        elif self.pricing_template == 'corporate_premium':
            self.pricing_method = 'percentage_markup'
            self.percentage_value = 50.0
            self.requires_verification = False
        
        elif self.pricing_template == 'nonprofit_discount':
            self.pricing_method = 'percentage_discount'
            self.percentage_value = 30.0
            self.requires_verification = True
            self.verification_criteria = "Nonprofit organization verification required."

    @api.onchange('set_validity_period')
    def _onchange_set_validity_period(self):
        """Clear validity dates when not setting period."""
        if not self.set_validity_period:
            self.valid_from = False
            self.valid_to = False

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('valid_from', 'valid_to')
    def _validate_validity_period(self):
        """Validate validity period dates."""
        for record in self:
            if record.valid_from and record.valid_to and record.valid_from > record.valid_to:
                raise ValidationError("Valid from date must be before valid until date.")

    @api.constrains('percentage_value')
    def _validate_percentage(self):
        """Validate percentage values."""
        for record in self:
            if record.pricing_method in ['percentage_discount', 'percentage_markup']:
                if record.percentage_value < 0 or record.percentage_value > 100:
                    raise ValidationError("Percentage must be between 0 and 100.")

    @api.constrains('minimum_price')
    def _validate_minimum_price(self):
        """Validate minimum price is non-negative."""
        for record in self:
            if record.minimum_price < 0:
                raise ValidationError("Minimum price cannot be negative.")

    # ==========================================
    # WIZARD NAVIGATION
    # ==========================================

    def action_next_step(self):
        """Move to next wizard step."""
        if self.state == 'selection':
            self._validate_selection()
            self.state = 'configuration'
        elif self.state == 'configuration':
            self._validate_configuration()
            self._generate_preview()
            self.state = 'review'
        elif self.state == 'review':
            return self.action_apply_changes()
        
        return self._reload_wizard()

    def action_previous_step(self):
        """Move to previous wizard step."""
        if self.state == 'configuration':
            self.state = 'selection'
        elif self.state == 'review':
            self.state = 'configuration'
        
        return self._reload_wizard()

    def _reload_wizard(self):
        """Reload wizard form."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.pricing.tier.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # VALIDATION HELPERS
    # ==========================================

    def _validate_selection(self):
        """Validate selection step."""
        # Check if we have target subscriptions
        subscriptions = self._get_target_subscriptions()
        if not subscriptions:
            raise ValidationError("Please select at least one subscription product.")
        
        # Check if we have target member types
        member_types = self._get_target_member_types()
        if not member_types:
            raise ValidationError("Please select at least one member type.")
        
        # Validate copy source if needed
        if self.wizard_type == 'copy_pricing' and not self.source_subscription_id:
            raise ValidationError("Please select a source subscription to copy from.")

    def _validate_configuration(self):
        """Validate configuration step."""
        if self.pricing_method == 'fixed_amount' and self.fixed_price <= 0:
            raise ValidationError("Fixed price must be greater than zero.")
        
        if self.pricing_method in ['percentage_discount', 'percentage_markup'] and self.percentage_value <= 0:
            raise ValidationError("Percentage value must be greater than zero.")
        
        if self.requires_verification and not self.verification_criteria:
            raise ValidationError("Verification criteria must be specified when verification is required.")

    # ==========================================
    # TARGET SELECTION HELPERS
    # ==========================================

    def _get_target_subscriptions(self):
        """Get target subscription products."""
        if self.apply_to_all_subscriptions:
            return self.env['ams.subscription.product'].search([('active', '=', True)])
        else:
            return self.subscription_product_ids

    def _get_target_member_types(self):
        """Get target member types."""
        if self.apply_to_all_member_types:
            return self.env['ams.member.type'].search([])
        else:
            return self.member_type_ids

    # ==========================================
    # PREVIEW GENERATION
    # ==========================================

    def _generate_preview(self):
        """Generate preview of pricing changes."""
        self.preview_line_ids = [(5, 0, 0)]  # Clear existing lines
        
        subscriptions = self._get_target_subscriptions()
        member_types = self._get_target_member_types()
        
        # Ensure we have proper recordsets
        if not subscriptions.exists() or not member_types.exists():
            return
        
        preview_lines = []
        
        for subscription_id in subscriptions.ids:
            subscription = self.env['ams.subscription.product'].browse(subscription_id)
            if not subscription.exists():
                continue
                
            for member_type_id in member_types.ids:
                member_type = self.env['ams.member.type'].browse(member_type_id)
                if not member_type.exists():
                    continue
                    
                # Calculate new price
                new_price = self._calculate_price(subscription, member_type)
                
                # Check for existing tier
                existing_tier = self.env['ams.subscription.pricing.tier'].search([
                    ('subscription_product_id', '=', subscription.id),
                    ('member_type_id', '=', member_type.id),
                ], limit=1)
                
                action = 'create'
                current_price = 0.0
                if existing_tier:
                    action = 'update' if self.overwrite_existing else 'skip'
                    current_price = existing_tier.price
                
                preview_lines.append({
                    'wizard_id': self.id,
                    'subscription_product_id': subscription.id,
                    'member_type_id': member_type.id,
                    'current_price': current_price,
                    'new_price': new_price,
                    'action': action,
                    'has_existing': bool(existing_tier),
                })
        
        # Create preview lines
        for line_vals in preview_lines:
            self.env['ams.pricing.tier.wizard.line'].create(line_vals)

    def _calculate_price(self, subscription, member_type):
        """Calculate new price for subscription/member type combination."""
        base_price = subscription.default_price
        
        if self.pricing_method == 'fixed_amount':
            new_price = self.fixed_price
        
        elif self.pricing_method == 'percentage_discount':
            discount_amount = base_price * (self.percentage_value / 100)
            new_price = base_price - discount_amount
        
        elif self.pricing_method == 'percentage_markup':
            markup_amount = base_price * (self.percentage_value / 100)
            new_price = base_price + markup_amount
        
        elif self.pricing_method == 'copy_from_tier':
            source_tier = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.source_subscription_id.id),
                ('member_type_id', '=', self.source_member_type_id.id),
            ], limit=1)
            new_price = source_tier.price if source_tier else base_price
        
        else:
            new_price = base_price
        
        # Apply minimum price
        if self.minimum_price > 0:
            new_price = max(new_price, self.minimum_price)
        
        # Round if requested
        if self.round_prices:
            new_price = round(new_price, 2)
        
        return new_price

    # ==========================================
    # APPLY CHANGES
    # ==========================================

    def action_apply_changes(self):
        """Apply the pricing changes."""
        created_count = 0
        updated_count = 0
        error_count = 0
        log_entries = []
        
        try:
            for line in self.preview_line_ids:
                if line.action == 'skip':
                    continue
                
                try:
                    if line.action == 'create':
                        self._create_pricing_tier(line)
                        created_count += 1
                        subscription_name = line.subscription_product_id.name if line.subscription_product_id else "Unknown"
                        member_type_name = line.member_type_id.name if line.member_type_id else "Unknown"
                        log_entries.append(f"Created: {subscription_name} - {member_type_name}")
                    
                    elif line.action == 'update':
                        self._update_pricing_tier(line)
                        updated_count += 1
                        subscription_name = line.subscription_product_id.name if line.subscription_product_id else "Unknown"
                        member_type_name = line.member_type_id.name if line.member_type_id else "Unknown"
                        log_entries.append(f"Updated: {subscription_name} - {member_type_name}")
                
                except Exception as e:
                    error_count += 1
                    subscription_name = line.subscription_product_id.name if line.subscription_product_id else "Unknown"
                    member_type_name = line.member_type_id.name if line.member_type_id else "Unknown"
                    log_entries.append(f"Error: {subscription_name} - {member_type_name}: {str(e)}")
        
        except Exception as e:
            raise UserError(f"Failed to apply pricing changes: {str(e)}")
        
        # Update results
        self.created_tier_count = created_count
        self.updated_tier_count = updated_count
        self.error_count = error_count
        self.operation_log = "\n".join(log_entries)
        self.state = 'complete'
        
        return self._reload_wizard()

    def _create_pricing_tier(self, line):
        """Create new pricing tier."""
        vals = {
            'subscription_product_id': line.subscription_product_id.id,
            'member_type_id': line.member_type_id.id,
            'price': line.new_price,
            'currency_id': self.currency_id.id,
            'requires_verification': self.requires_verification,
            'verification_criteria': self.verification_criteria,
        }
        
        if self.set_validity_period:
            vals.update({
                'valid_from': self.valid_from,
                'valid_to': self.valid_to,
            })
        
        self.env['ams.subscription.pricing.tier'].create(vals)

    def _update_pricing_tier(self, line):
        """Update existing pricing tier."""
        existing_tier = self.env['ams.subscription.pricing.tier'].search([
            ('subscription_product_id', '=', line.subscription_product_id.id),
            ('member_type_id', '=', line.member_type_id.id),
        ], limit=1)
        
        if existing_tier:
            vals = {
                'price': line.new_price,
                'requires_verification': self.requires_verification,
                'verification_criteria': self.verification_criteria,
            }
            
            if self.set_validity_period:
                vals.update({
                    'valid_from': self.valid_from,
                    'valid_to': self.valid_to,
                })
            
            existing_tier.write(vals)

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_close_wizard(self):
        """Close the wizard."""
        return {'type': 'ir.actions.act_window_close'}

    def action_view_created_tiers(self):
        """View created pricing tiers."""
        return {
            'name': 'Created Pricing Tiers',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'list,form',
            'domain': [
                ('subscription_product_id', 'in', self._get_target_subscriptions().ids),
                ('member_type_id', 'in', self._get_target_member_types().ids),
            ],
        }


class AMSPricingTierWizardLine(models.TransientModel):
    """Preview line for pricing tier wizard."""
    _name = 'ams.pricing.tier.wizard.line'
    _description = 'Pricing Tier Wizard Preview Line'

    wizard_id = fields.Many2one(
        'ams.pricing.tier.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Product',
        required=True
    )
    
    member_type_id = fields.Many2one(
        'ams.member.type',
        string='Member Type',
        required=True
    )
    
    current_price = fields.Monetary(
        string='Current Price',
        currency_field='currency_id'
    )
    
    new_price = fields.Monetary(
        string='New Price',
        currency_field='currency_id'
    )
    
    price_change = fields.Monetary(
        string='Price Change',
        compute='_compute_price_change',
        currency_field='currency_id'
    )
    
    percentage_change = fields.Float(
        string='% Change',
        compute='_compute_price_change'
    )
    
    action = fields.Selection([
        ('create', 'Create New'),
        ('update', 'Update Existing'),
        ('skip', 'Skip')
    ], string='Action', required=True)
    
    has_existing = fields.Boolean(
        string='Has Existing Tier'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id'
    )

    @api.depends('current_price', 'new_price')
    def _compute_price_change(self):
        """Compute price change amount and percentage."""
        for line in self:
            line.price_change = line.new_price - line.current_price
            
            if line.current_price > 0:
                line.percentage_change = (line.price_change / line.current_price) * 100
            else:
                line.percentage_change = 0.0