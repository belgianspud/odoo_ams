from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class ProductTemplateSubscription(models.Model):
    """Extend product.template with subscription toggle functionality."""
    _inherit = 'product.template'

    # ==========================================
    # CORE SUBSCRIPTION TOGGLE
    # ==========================================
    
    is_subscription_product = fields.Boolean(
        string='Subscription',
        default=False,
        help='Enable subscription features for this product'
    )
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Definition',
        help='Related subscription configuration record'
    )
    
    # ==========================================
    # SUBSCRIPTION INDICATORS (READ-ONLY)
    # ==========================================
    
    subscription_scope = fields.Selection(
        related='subscription_product_id.subscription_scope',
        readonly=True,
        help='Individual or Enterprise subscription'
    )
    
    subscription_product_type = fields.Selection(
        related='subscription_product_id.product_type',
        readonly=True,
        help='Membership, Chapter, Committee, or Publication'
    )
    
    default_duration = fields.Integer(
        related='subscription_product_id.default_duration',
        readonly=True,
        help='Default subscription duration'
    )
    
    duration_unit = fields.Selection(
        related='subscription_product_id.duration_unit',
        readonly=True,
        help='Duration unit (days, months, years)'
    )
    
    subscription_price = fields.Monetary(
        related='subscription_product_id.default_price',
        readonly=True,
        help='Base subscription price'
    )
    
    pricing_tier_count = fields.Integer(
        string='Pricing Tiers',
        compute='_compute_pricing_tier_count',
        help='Number of member-type pricing tiers'
    )
    
    is_renewable = fields.Boolean(
        related='subscription_product_id.is_renewable',
        readonly=True,
        help='Subscription supports renewal'
    )
    
    auto_renewal_enabled = fields.Boolean(
        related='subscription_product_id.auto_renewal_enabled',
        readonly=True,
        help='Auto-renewal available'
    )
    
    requires_approval = fields.Boolean(
        related='subscription_product_id.requires_approval',
        readonly=True,
        help='Subscription needs staff approval'
    )
    
    member_only = fields.Boolean(
        related='subscription_product_id.member_only',
        readonly=True,
        help='Restricted to current members only'
    )

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('subscription_product_id.pricing_tier_ids')
    def _compute_pricing_tier_count(self):
        """Compute number of pricing tiers."""
        for record in self:
            if record.subscription_product_id:
                record.pricing_tier_count = len(record.subscription_product_id.pricing_tier_ids)
            else:
                record.pricing_tier_count = 0

    # ==========================================
    # ONCHANGE METHODS - SMART AUTO-CONFIGURATION
    # ==========================================

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Transform product into subscription with smart defaults."""
        if self.is_subscription_product:
            # Configure as service for subscription model
            if self.detailed_type != 'service':
                self.detailed_type = 'service'
            
            # Ensure product is sellable
            if not self.sale_ok:
                self.sale_ok = True
                
            # Enable website publication by default
            if hasattr(self, 'website_published') and not self.website_published:
                self.website_published = True
            
            # Auto-create subscription definition if it doesn't exist
            if not self.subscription_product_id and not self._context.get('skip_auto_create'):
                # We'll create this in the write method to avoid issues with new records
                pass
        else:
            # When disabling subscription, clear the subscription definition
            if self.subscription_product_id:
                # Don't delete here, just clear the link - actual deletion handled separately
                self.subscription_product_id = False

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle subscription auto-creation."""
        products = super().create(vals_list)
        
        # Auto-create subscription definitions for new subscription products
        for product in products:
            if product.is_subscription_product and not product.subscription_product_id:
                product._create_subscription_definition()
        
        return products

    def write(self, vals):
        """Override write to handle subscription toggle changes."""
        result = super().write(vals)
        
        # Handle subscription enablement
        if 'is_subscription_product' in vals:
            for record in self:
                if record.is_subscription_product and not record.subscription_product_id:
                    record._create_subscription_definition()
                elif not record.is_subscription_product and record.subscription_product_id:
                    # Optionally clean up subscription definition
                    # For now, we'll keep it for data integrity
                    pass
        
        return result

    # ==========================================
    # SUBSCRIPTION MANAGEMENT METHODS
    # ==========================================

    def _create_subscription_definition(self):
        """Auto-create subscription configuration with smart defaults."""
        self.ensure_one()
        
        if self.subscription_product_id:
            return self.subscription_product_id
        
        # Determine smart defaults based on product characteristics
        defaults = self._determine_subscription_defaults()
        
        # Create subscription definition
        subscription_vals = {
            'name': f"{self.name} Subscription",
            'code': self._generate_subscription_code(),
            'product_id': self.product_tmpl_id.id,
            'subscription_scope': defaults['scope'],
            'product_type': defaults['type'],
            'default_duration': defaults['duration'],
            'duration_unit': defaults['unit'],
            'default_price': self.list_price or 0.0,
            'currency_id': self.currency_id.id or self.env.company.currency_id.id,
        }
        
        subscription_product = self.env['ams.subscription.product'].create(subscription_vals)
        self.subscription_product_id = subscription_product.id
        
        return subscription_product

    def _determine_subscription_defaults(self):
        """Determine smart defaults based on product characteristics."""
        self.ensure_one()
        
        # Default to individual membership
        scope = 'individual'
        product_type = 'membership'
        duration = 12
        unit = 'months'
        
        # Analyze product name for clues
        name_lower = (self.name or '').lower()
        
        # Detect enterprise/corporate products
        if any(term in name_lower for term in ['enterprise', 'corporate', 'organization', 'company']):
            scope = 'enterprise'
        
        # Detect product types
        if any(term in name_lower for term in ['chapter', 'local']):
            product_type = 'chapter'
        elif any(term in name_lower for term in ['committee', 'board', 'governance']):
            product_type = 'committee'
        elif any(term in name_lower for term in ['publication', 'journal', 'magazine', 'newsletter']):
            product_type = 'publication'
        
        # Detect duration patterns
        if any(term in name_lower for term in ['monthly']):
            duration = 1
            unit = 'months'
        elif any(term in name_lower for term in ['quarterly']):
            duration = 3
            unit = 'months'
        elif any(term in name_lower for term in ['annual', 'yearly']):
            duration = 12
            unit = 'months'
        elif any(term in name_lower for term in ['lifetime']):
            duration = 99
            unit = 'years'
        
        return {
            'scope': scope,
            'type': product_type,
            'duration': duration,
            'unit': unit
        }

    def _generate_subscription_code(self):
        """Generate unique subscription code."""
        self.ensure_one()
        
        base_code = self.default_code or f"SUB_{self.id}"
        
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

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_configure_subscription(self):
        """Open subscription configuration form."""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError("This product is not configured as a subscription product.")
        
        if not self.subscription_product_id:
            self._create_subscription_definition()
        
        return {
            'name': f'Configure Subscription - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': self.subscription_product_id.id,
            'target': 'new',
            'context': {'default_product_id': self.product_tmpl_id.id}
        }

    def action_manage_pricing_tiers(self):
        """Open pricing tier management."""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.subscription_product_id:
            raise UserError("This product must be a subscription product to manage pricing tiers.")
        
        return {
            'name': f'Pricing Tiers - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'tree,form',
            'domain': [('subscription_product_id', '=', self.subscription_product_id.id)],
            'context': {
                'default_subscription_product_id': self.subscription_product_id.id,
                'default_currency_id': self.subscription_product_id.currency_id.id,
            }
        }

    def action_create_subscription_wizard(self):
        """Launch subscription creation wizard."""
        self.ensure_one()
        
        return {
            'name': f'Create Subscription - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_tmpl_id.id,
            }
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_subscription_summary(self):
        """Get subscription configuration summary."""
        self.ensure_one()
        
        if not self.is_subscription_product or not self.subscription_product_id:
            return {'is_subscription': False}
        
        sub = self.subscription_product_id
        return {
            'is_subscription': True,
            'scope': sub.subscription_scope,
            'type': sub.product_type,
            'duration': f"{sub.default_duration} {sub.duration_unit}",
            'price': sub.default_price,
            'currency': sub.currency_id.name,
            'pricing_tiers': len(sub.pricing_tier_ids),
            'is_renewable': sub.is_renewable,
            'auto_renewal': sub.auto_renewal_enabled,
            'requires_approval': sub.requires_approval,
            'member_only': sub.member_only,
        }

    @api.model
    def get_subscription_products(self):
        """Get all products with subscription features enabled."""
        return self.search([('is_subscription_product', '=', True)])

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('is_subscription_product', 'detailed_type')
    def _check_subscription_product_type(self):
        """Validate subscription products are configured as services."""
        for record in self:
            if record.is_subscription_product and record.detailed_type not in ['service']:
                raise ValidationError(
                    f"Subscription products should be configured as 'Service' type. "
                    f"Product '{record.name}' is currently set to '{record.detailed_type}'."
                )

    @api.constrains('is_subscription_product', 'sale_ok')
    def _check_subscription_saleable(self):
        """Ensure subscription products are saleable."""
        for record in self:
            if record.is_subscription_product and not record.sale_ok:
                raise ValidationError(
                    f"Subscription product '{record.name}' must be saleable. "
                    f"Please enable 'Can be Sold' option."
                )

    # ==========================================
    # SEARCH AND DISPLAY METHODS
    # ==========================================

    def name_get(self):
        """Enhanced name display for subscription products."""
        result = super().name_get()
        
        # Add subscription indicator to display name
        new_result = []
        for record_id, name in result:
            record = self.browse(record_id)
            if record.is_subscription_product:
                name = f"[SUBSCRIPTION] {name}"
            new_result.append((record_id, name))
        
        return new_result