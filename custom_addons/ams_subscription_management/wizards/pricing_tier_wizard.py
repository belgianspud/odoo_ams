from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class AMSPricingTierWizard(models.TransientModel):
    """Wizard for bulk creation and management of subscription pricing tiers."""
    _name = 'ams.pricing.tier.wizard'
    _description = 'Pricing Tier Management Wizard'

    # ==========================================
    # WIZARD MODE FIELDS
    # ==========================================
    
    wizard_mode = fields.Selection([
        ('create_bulk', 'Create Multiple Pricing Tiers'),
        ('update_bulk', 'Update Existing Pricing Tiers'),
        ('copy_tiers', 'Copy Tiers Between Products'),
        ('promotional', 'Create Promotional Pricing'),
    ], string='Wizard Mode', default='create_bulk', required=True)
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Product',
        required=True,
        help='Target subscription product for pricing tiers'
    )
    
    subscription_product_name = fields.Char(
        string='Product Name',
        related='subscription_product_id.name',
        readonly=True
    )
    
    # FIXED: Changed to computed field to handle type mismatch
    base_price = fields.Monetary(
        string='Base Product Price',
        compute='_compute_base_price',
        readonly=True,
        currency_field='currency_id',
        help='Base price from subscription product'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='subscription_product_id.currency_id',
        readonly=True
    )

    # ==========================================
    # COMPUTED METHOD FOR BASE PRICE
    # ==========================================
    
    @api.depends('subscription_product_id.default_price')
    def _compute_base_price(self):
        """Compute base price from subscription product."""
        for wizard in self:
            wizard.base_price = wizard.subscription_product_id.default_price if wizard.subscription_product_id else 0.0

    # ==========================================
    # BULK CREATION FIELDS
    # ==========================================
    
    tier_creation_method = fields.Selection([
        ('standard_tiers', 'Standard Member Types'),
        ('percentage_discounts', 'Percentage-Based Discounts'),
        ('fixed_prices', 'Fixed Price Tiers'),
        ('template', 'Use Pricing Template'),
    ], string='Creation Method', default='standard_tiers')
    
    # Standard member type selection
    member_type_ids = fields.Many2many(
        'ams.member.type',
        'wizard_member_type_rel',  # Added explicit relation table name
        'wizard_id',
        'member_type_id',
        string='Member Types',
        help='Member types to create pricing tiers for'
    )
    
    # Percentage-based creation
    discount_percentage = fields.Float(
        string='Default Discount %',
        default=20.0,
        help='Default discount percentage for all selected member types'
    )
    
    use_graduated_discounts = fields.Boolean(
        string='Graduated Discounts',
        default=False,
        help='Apply different discount levels based on member type'
    )
    
    student_discount = fields.Float(
        string='Student Discount %',
        default=50.0
    )
    
    senior_discount = fields.Float(
        string='Senior/Retired Discount %',
        default=25.0
    )
    
    professional_discount = fields.Float(
        string='Professional Discount %',
        default=15.0
    )
    
    international_discount = fields.Float(
        string='International Discount %',
        default=20.0
    )

    # ==========================================
    # PROMOTIONAL PRICING FIELDS
    # ==========================================
    
    is_promotional = fields.Boolean(
        string='Create Promotional Pricing',
        default=False,
        help='Create time-limited promotional pricing'
    )
    
    promotional_discount = fields.Float(
        string='Promotional Discount %',
        default=30.0,
        help='Promotional discount percentage'
    )
    
    promo_valid_from = fields.Date(
        string='Promotion Start Date',
        default=fields.Date.today,
        help='When promotional pricing becomes active'
    )
    
    promo_valid_to = fields.Date(
        string='Promotion End Date',
        help='When promotional pricing expires'
    )
    
    promo_description = fields.Text(
        string='Promotional Description',
        default='Limited time offer',
        help='Description of promotional offer'
    )

    # ==========================================
    # VERIFICATION SETTINGS FIELDS
    # ==========================================
    
    apply_verification_requirements = fields.Boolean(
        string='Add Verification Requirements',
        default=False,
        help='Add verification requirements to applicable tiers'
    )
    
    auto_verification_criteria = fields.Boolean(
        string='Auto-Generate Verification Criteria',
        default=True,
        help='Automatically generate verification text based on member type'
    )
    
    default_verification_text = fields.Text(
        string='Default Verification Text',
        default='Member status verification required',
        help='Default verification criteria text'
    )

    # ==========================================
    # BULK UPDATE FIELDS
    # ==========================================
    
    existing_tier_ids = fields.Many2many(
        'ams.subscription.pricing.tier',
        'wizard_existing_tier_rel',  # Added explicit relation table name
        'wizard_id',
        'tier_id',
        string='Existing Pricing Tiers',
        help='Existing tiers to update'
    )
    
    update_action = fields.Selection([
        ('adjust_prices', 'Adjust All Prices'),
        ('extend_validity', 'Extend Validity Period'),
        ('add_verification', 'Add Verification Requirements'),
        ('deactivate', 'Deactivate Tiers'),
    ], string='Update Action', default='adjust_prices')
    
    price_adjustment_type = fields.Selection([
        ('percentage', 'Percentage Adjustment'),
        ('fixed_amount', 'Fixed Amount Adjustment'),
        ('set_price', 'Set Specific Price'),
    ], string='Price Adjustment Type', default='percentage')
    
    adjustment_value = fields.Float(
        string='Adjustment Value',
        help='Percentage, amount, or specific price depending on adjustment type'
    )

    # ==========================================
    # COPY TIERS FIELDS
    # ==========================================
    
    source_subscription_id = fields.Many2one(
        'ams.subscription.product',
        string='Source Subscription Product',
        help='Product to copy pricing tiers from'
    )
    
    copy_all_tiers = fields.Boolean(
        string='Copy All Tiers',
        default=True,
        help='Copy all pricing tiers from source product'
    )
    
    source_tier_ids = fields.Many2many(
        'ams.subscription.pricing.tier',
        'wizard_source_tier_rel',  # Added explicit relation table name
        'wizard_id',
        'source_tier_id',
        string='Source Tiers',
        help='Specific tiers to copy'
    )
    
    adjust_copied_prices = fields.Boolean(
        string='Adjust Copied Prices',
        default=False,
        help='Adjust prices when copying based on price difference'
    )

    # ==========================================
    # PREVIEW AND RESULTS FIELDS
    # ==========================================
    
    tier_preview_ids = fields.One2many(
        'ams.pricing.tier.preview',
        'wizard_id',
        string='Tier Preview',
        help='Preview of tiers to be created'
    )
    
    show_preview = fields.Boolean(
        string='Show Preview',
        default=False,
        help='Display preview of tiers before creation'
    )
    
    creation_summary = fields.Text(
        string='Creation Summary',
        readonly=True,
        help='Summary of created tiers'
    )

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('wizard_mode')
    def _onchange_wizard_mode(self):
        """Handle wizard mode changes."""
        # Clear mode-specific fields
        self.member_type_ids = [(5, 0, 0)]  # Clear all
        self.existing_tier_ids = [(5, 0, 0)]
        self.source_subscription_id = False
        self.show_preview = False

    @api.onchange('tier_creation_method')
    def _onchange_tier_creation_method(self):
        """Handle creation method changes."""
        if self.tier_creation_method == 'standard_tiers':
            # Load common member types
            common_types = self.env['ams.member.type'].search([
                ('code', 'in', ['student', 'professional', 'senior', 'retired', 'international'])
            ])
            self.member_type_ids = [(6, 0, common_types.ids)]
        
        elif self.tier_creation_method == 'percentage_discounts':
            self.use_graduated_discounts = True

    @api.onchange('subscription_product_id')
    def _onchange_subscription_product_id(self):
        """Handle subscription product changes."""
        if self.subscription_product_id:
            # Load existing tiers for update mode
            existing_tiers = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.subscription_product_id.id)
            ])
            self.existing_tier_ids = [(6, 0, existing_tiers.ids)]

    @api.onchange('source_subscription_id')
    def _onchange_source_subscription_id(self):
        """Handle source subscription changes."""
        if self.source_subscription_id:
            source_tiers = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.source_subscription_id.id),
                ('active', '=', True)  # Only get active tiers
            ])
            self.source_tier_ids = [(6, 0, source_tiers.ids)]

    @api.onchange('use_graduated_discounts')
    def _onchange_use_graduated_discounts(self):
        """Set default graduated discount values."""
        if not self.use_graduated_discounts:
            # Reset all discounts to default
            self.student_discount = self.discount_percentage
            self.senior_discount = self.discount_percentage
            self.professional_discount = self.discount_percentage
            self.international_discount = self.discount_percentage

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('promo_valid_from', 'promo_valid_to')
    def _check_promotional_dates(self):
        """Validate promotional pricing dates."""
        for wizard in self:
            if wizard.is_promotional and wizard.promo_valid_to:
                if wizard.promo_valid_from > wizard.promo_valid_to:
                    raise ValidationError("Promotion end date must be after start date")

    @api.constrains('discount_percentage', 'student_discount', 'senior_discount', 
                    'professional_discount', 'international_discount', 'promotional_discount')
    def _check_discount_percentages(self):
        """Validate discount percentages."""
        for wizard in self:
            discount_fields = [
                ('discount_percentage', 'Default Discount'),
                ('student_discount', 'Student Discount'),
                ('senior_discount', 'Senior Discount'),
                ('professional_discount', 'Professional Discount'),
                ('international_discount', 'International Discount'),
                ('promotional_discount', 'Promotional Discount')
            ]
            
            for field_name, field_label in discount_fields:
                value = getattr(wizard, field_name)
                if value < 0 or value > 100:
                    raise ValidationError(f"{field_label} must be between 0 and 100")

    # ==========================================
    # PREVIEW METHODS
    # ==========================================

    def action_generate_preview(self):
        """Generate preview of tiers to be created."""
        self.tier_preview_ids.unlink()  # Clear existing preview
        
        try:
            if self.wizard_mode == 'create_bulk':
                preview_data = self._generate_creation_preview()
            elif self.wizard_mode == 'copy_tiers':
                preview_data = self._generate_copy_preview()
            elif self.wizard_mode == 'update_bulk':
                preview_data = self._generate_update_preview()
            elif self.wizard_mode == 'promotional':
                preview_data = self._generate_promotional_preview()
            else:
                preview_data = []
            
            # Create preview records
            for data in preview_data:
                data['wizard_id'] = self.id
                self.env['ams.pricing.tier.preview'].create(data)
            
            self.show_preview = True
            return self._return_wizard_action()
            
        except Exception as e:
            raise UserError(f"Error generating preview: {str(e)}")

    def _generate_creation_preview(self):
        """Generate preview for bulk creation."""
        preview_data = []
        
        if not self.member_type_ids:
            raise UserError("Please select member types to create tiers for")
        
        for member_type in self.member_type_ids:
            # Determine discount percentage
            if self.use_graduated_discounts:
                discount = self._get_graduated_discount(member_type)
            else:
                discount = self.discount_percentage
            
            # Calculate price
            price = self.base_price * (1 - discount / 100)
            
            # Determine verification requirements
            requires_verification = self._should_require_verification(member_type)
            
            preview_data.append({
                'member_type_id': member_type.id,
                'member_type_name': member_type.name,
                'original_price': self.base_price,
                'new_price': price,
                'discount_percentage': discount,
                'requires_verification': requires_verification,
                'action_type': 'create',
                'preview_description': f"Create {member_type.name} tier at {price:.2f} ({discount:.0f}% off)"
            })
        
        return preview_data

    def _generate_copy_preview(self):
        """Generate preview for copying tiers."""
        preview_data = []
        
        if not self.source_subscription_id:
            raise UserError("Please select a source subscription product")
        
        # FIXED: Proper logic for determining tiers to copy
        if self.copy_all_tiers:
            tiers_to_copy = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.source_subscription_id.id),
                ('active', '=', True)
            ])
        else:
            tiers_to_copy = self.source_tier_ids
        
        if not tiers_to_copy:
            raise UserError("No tiers found to copy")
        
        # Calculate price adjustment ratio if needed
        price_ratio = 1.0
        if self.adjust_copied_prices and self.source_subscription_id.default_price > 0:
            price_ratio = self.base_price / self.source_subscription_id.default_price
        
        for tier in tiers_to_copy:
            new_price = tier.price * price_ratio if self.adjust_copied_prices else tier.price
            
            preview_data.append({
                'member_type_id': tier.member_type_id.id,
                'member_type_name': tier.member_type_id.name,
                'original_price': tier.price,
                'new_price': new_price,
                'discount_percentage': ((self.base_price - new_price) / self.base_price * 100) if self.base_price > 0 else 0,
                'requires_verification': tier.requires_verification,
                'action_type': 'copy',
                'preview_description': f"Copy {tier.member_type_id.name} tier from {self.source_subscription_id.name}"
            })
        
        return preview_data

    def _generate_update_preview(self):
        """Generate preview for bulk updates."""
        preview_data = []
        
        if not self.existing_tier_ids:
            raise UserError("Please select existing tiers to update")
        
        for tier in self.existing_tier_ids:
            if self.update_action == 'adjust_prices':
                new_price = self._calculate_adjusted_price(tier.price)
                action_desc = f"Adjust price from {tier.price:.2f} to {new_price:.2f}"
            elif self.update_action == 'extend_validity':
                action_desc = f"Extend validity to {self.promo_valid_to}"
                new_price = tier.price
            elif self.update_action == 'add_verification':
                action_desc = "Add verification requirement"
                new_price = tier.price
            else:  # deactivate
                action_desc = "Deactivate tier"
                new_price = tier.price
            
            preview_data.append({
                'member_type_id': tier.member_type_id.id,
                'member_type_name': tier.member_type_id.name,
                'original_price': tier.price,
                'new_price': new_price,
                'discount_percentage': tier.discount_percentage,
                'requires_verification': tier.requires_verification,
                'action_type': 'update',
                'preview_description': action_desc
            })
        
        return preview_data

    def _generate_promotional_preview(self):
        """Generate preview for promotional pricing."""
        preview_data = []
        
        if not self.member_type_ids:
            raise UserError("Please select member types for promotional pricing")
        
        for member_type in self.member_type_ids:
            original_price = self.base_price
            promo_price = original_price * (1 - self.promotional_discount / 100)
            
            preview_data.append({
                'member_type_id': member_type.id,
                'member_type_name': member_type.name,
                'original_price': original_price,
                'new_price': promo_price,
                'discount_percentage': self.promotional_discount,
                'requires_verification': False,
                'action_type': 'promotional',
                'preview_description': f"Create promotional pricing for {member_type.name}: {promo_price:.2f} (was {original_price:.2f})"
            })
        
        return preview_data

    # ==========================================
    # EXECUTION METHODS
    # ==========================================

    def action_execute_wizard(self):
        """Execute the wizard action based on mode."""
        try:
            if self.wizard_mode == 'create_bulk':
                result = self._execute_bulk_creation()
            elif self.wizard_mode == 'copy_tiers':
                result = self._execute_copy_tiers()
            elif self.wizard_mode == 'update_bulk':
                result = self._execute_bulk_update()
            elif self.wizard_mode == 'promotional':
                result = self._execute_promotional_creation()
            else:
                raise UserError("Invalid wizard mode")
            
            return result
            
        except Exception as e:
            raise UserError(f"Error executing wizard: {str(e)}")

    def _execute_bulk_creation(self):
        """Execute bulk creation of pricing tiers."""
        created_tiers = []
        skipped_count = 0
        
        for member_type in self.member_type_ids:
            # Skip if tier already exists and is active
            existing_tier = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.subscription_product_id.id),
                ('member_type_id', '=', member_type.id),
                ('active', '=', True)
            ], limit=1)
            
            if existing_tier:
                skipped_count += 1
                continue  # Skip existing tiers
            
            # Calculate pricing
            if self.use_graduated_discounts:
                discount = self._get_graduated_discount(member_type)
            else:
                discount = self.discount_percentage
            
            price = self.base_price * (1 - discount / 100)
            
            # Determine verification requirements
            requires_verification = (
                self.apply_verification_requirements and 
                self._should_require_verification(member_type)
            )
            
            verification_text = None
            if requires_verification:
                if self.auto_verification_criteria:
                    verification_text = self._generate_verification_text(member_type)
                else:
                    verification_text = self.default_verification_text
            
            # Create tier
            tier_vals = {
                'subscription_product_id': self.subscription_product_id.id,
                'member_type_id': member_type.id,
                'price': price,
                'currency_id': self.currency_id.id,
                'requires_verification': requires_verification,
                'verification_criteria': verification_text,
            }
            
            # Add promotional dates if applicable
            if self.is_promotional:
                tier_vals.update({
                    'valid_from': self.promo_valid_from,
                    'valid_to': self.promo_valid_to,
                    'description': self.promo_description,
                })
            
            tier = self.env['ams.subscription.pricing.tier'].create(tier_vals)
            created_tiers.append(tier)
        
        # Generate summary
        summary_parts = [f"Created {len(created_tiers)} pricing tiers"]
        if skipped_count > 0:
            summary_parts.append(f"Skipped {skipped_count} existing tiers")
        
        self.creation_summary = "\n".join(summary_parts)
        
        return self._show_success_action(created_tiers)

    def _execute_copy_tiers(self):
        """Execute copying tiers between products."""
        # FIXED: Proper logic for determining tiers to copy
        if self.copy_all_tiers:
            tiers_to_copy = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.source_subscription_id.id),
                ('active', '=', True)
            ])
        else:
            tiers_to_copy = self.source_tier_ids
            
        if not tiers_to_copy:
            raise UserError("No tiers found to copy")
        
        created_tiers = []
        skipped_count = 0
        
        # Calculate price adjustment ratio
        price_ratio = 1.0
        if self.adjust_copied_prices and self.source_subscription_id.default_price > 0:
            price_ratio = self.base_price / self.source_subscription_id.default_price
        
        for source_tier in tiers_to_copy:
            # Check if tier already exists
            existing_tier = self.env['ams.subscription.pricing.tier'].search([
                ('subscription_product_id', '=', self.subscription_product_id.id),
                ('member_type_id', '=', source_tier.member_type_id.id),
                ('active', '=', True)
            ], limit=1)
            
            if existing_tier:
                skipped_count += 1
                continue  # Skip existing
            
            new_price = source_tier.price * price_ratio if self.adjust_copied_prices else source_tier.price
            
            tier_vals = {
                'subscription_product_id': self.subscription_product_id.id,
                'member_type_id': source_tier.member_type_id.id,
                'price': new_price,
                'currency_id': self.currency_id.id,
                'requires_verification': source_tier.requires_verification,
                'verification_criteria': source_tier.verification_criteria,
                'description': f"Copied from {self.source_subscription_id.name}",
            }
            
            tier = self.env['ams.subscription.pricing.tier'].create(tier_vals)
            created_tiers.append(tier)
        
        # Generate summary
        summary_parts = [f"Copied {len(created_tiers)} pricing tiers"]
        if skipped_count > 0:
            summary_parts.append(f"Skipped {skipped_count} existing tiers")
            
        self.creation_summary = "\n".join(summary_parts)
        return self._show_success_action(created_tiers)

    def _execute_bulk_update(self):
        """Execute bulk update of existing tiers."""
        updated_count = 0
        
        for tier in self.existing_tier_ids:
            update_vals = {}
            
            if self.update_action == 'adjust_prices':
                new_price = self._calculate_adjusted_price(tier.price)
                update_vals['price'] = new_price
            
            elif self.update_action == 'extend_validity':
                if self.promo_valid_to:
                    update_vals['valid_to'] = self.promo_valid_to
            
            elif self.update_action == 'add_verification':
                update_vals.update({
                    'requires_verification': True,
                    'verification_criteria': self.default_verification_text
                })
            
            elif self.update_action == 'deactivate':
                update_vals['active'] = False
            
            if update_vals:
                tier.write(update_vals)
                updated_count += 1
        
        self.creation_summary = f"Updated {updated_count} pricing tiers"
        return self._show_success_action(self.existing_tier_ids)

    def _execute_promotional_creation(self):
        """Execute promotional pricing creation."""
        # Use the same logic as bulk creation but with promotional settings
        self.is_promotional = True
        return self._execute_bulk_creation()

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def _get_graduated_discount(self, member_type):
        """Get appropriate discount percentage for member type."""
        if not member_type or not member_type.code:
            return self.discount_percentage
            
        code = member_type.code.lower()
        
        if 'student' in code:
            return self.student_discount
        elif 'senior' in code or 'retired' in code:
            return self.senior_discount
        elif 'professional' in code:
            return self.professional_discount
        elif 'international' in code:
            return self.international_discount
        else:
            return self.discount_percentage

    def _should_require_verification(self, member_type):
        """Determine if member type should require verification."""
        if not self.apply_verification_requirements or not member_type or not member_type.code:
            return False
            
        code = member_type.code.lower()
        verification_types = ['student', 'senior', 'retired']
        
        return any(vtype in code for vtype in verification_types)

    def _generate_verification_text(self, member_type):
        """Generate verification text based on member type."""
        if not member_type or not member_type.code:
            return self.default_verification_text
            
        code = member_type.code.lower()
        
        if 'student' in code:
            return "Valid student enrollment verification required"
        elif 'senior' in code or 'retired' in code:
            return "Age or retirement status verification required"
        else:
            return self.default_verification_text

    def _calculate_adjusted_price(self, current_price):
        """Calculate adjusted price based on adjustment settings."""
        if self.price_adjustment_type == 'percentage':
            return current_price * (1 + self.adjustment_value / 100)
        elif self.price_adjustment_type == 'fixed_amount':
            return current_price + self.adjustment_value
        elif self.price_adjustment_type == 'set_price':
            return self.adjustment_value
        else:
            return current_price

    def _show_success_action(self, tiers):
        """Show success message and pricing tier view."""
        return {
            'name': f'Pricing Tiers - {self.subscription_product_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'tree,form',
            'domain': [('subscription_product_id', '=', self.subscription_product_id.id)],
            'context': {
                'default_subscription_product_id': self.subscription_product_id.id,
            },
        }

    def _return_wizard_action(self):
        """Return action to stay in wizard."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.pricing.tier.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class AMSPricingTierPreview(models.TransientModel):
    """Preview model for pricing tier wizard."""
    _name = 'ams.pricing.tier.preview'
    _description = 'Pricing Tier Preview'
    _order = 'member_type_name'

    wizard_id = fields.Many2one(
        'ams.pricing.tier.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    member_type_id = fields.Many2one(
        'ams.member.type',
        string='Member Type',
        required=True
    )
    
    member_type_name = fields.Char(
        string='Member Type',
        required=True
    )
    
    original_price = fields.Monetary(
        string='Original Price',
        currency_field='currency_id'
    )
    
    new_price = fields.Monetary(
        string='New Price',
        currency_field='currency_id'
    )
    
    discount_percentage = fields.Float(
        string='Discount %'
    )
    
    requires_verification = fields.Boolean(
        string='Verification Required'
    )
    
    action_type = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('copy', 'Copy'),
        ('promotional', 'Promotional')
    ], string='Action')
    
    preview_description = fields.Char(
        string='Description'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True
    )