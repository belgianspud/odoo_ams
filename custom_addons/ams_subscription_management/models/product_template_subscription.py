from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class ProductTemplateSubscription(models.Model):
    """Extend product.template with subscription toggle functionality."""
    _inherit = 'product.template'

    # ==========================================
    # SUBSCRIPTION TOGGLE - CORE FEATURE
    # ==========================================
    
    is_subscription_product = fields.Boolean(
        string='Subscription',
        default=False,
        help='Enable subscription features for this product'
    )
    
    subscription_product_id = fields.Many2one(
        'ams.subscription.product',
        string='Subscription Definition',
        help='Subscription configuration for this product'
    )
    
    # ==========================================
    # COMPUTED SUBSCRIPTION INDICATORS
    # ==========================================
    
    has_subscription_configuration = fields.Boolean(
        string='Has Subscription Configuration',
        compute='_compute_subscription_indicators',
        store=True,
        help='Product has complete subscription setup'
    )
    
    subscription_scope = fields.Selection(
        string='Subscription Scope',
        related='subscription_product_id.subscription_scope',
        readonly=True,
        help='Individual or Enterprise subscription'
    )
    
    subscription_type = fields.Selection(
        string='Subscription Type',
        related='subscription_product_id.product_type',
        readonly=True,
        help='Membership, Chapter, Committee, Publication'
    )
    
    subscription_member_price = fields.Monetary(
        string='Member Price',
        related='subscription_product_id.default_price',
        readonly=True,
        help='Base subscription price for members'
    )
    
    subscription_pricing_tier_count = fields.Integer(
        string='Pricing Tiers',
        compute='_compute_subscription_indicators',
        store=True,
        help='Number of member-type pricing tiers configured'
    )

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('subscription_product_id', 'subscription_product_id.pricing_tier_ids')
    def _compute_subscription_indicators(self):
        """Compute subscription-related indicators."""
        for product in self:
            if product.subscription_product_id:
                product.has_subscription_configuration = True
                product.subscription_pricing_tier_count = len(
                    product.subscription_product_id.pricing_tier_ids
                )
            else:
                product.has_subscription_configuration = False
                product.subscription_pricing_tier_count = 0

    # ==========================================
    # SUBSCRIPTION TOGGLE LOGIC
    # ==========================================

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Handle subscription toggle - core UX pattern."""
        if self.is_subscription_product:
            # Smart defaults when subscription features are enabled
            self.detailed_type = 'service'  # Subscriptions are services
            self.sale_ok = True
            
            # Only auto-create if no existing subscription definition
            if not self.subscription_product_id:
                return {
                    'warning': {
                        'title': 'Subscription Enabled',
                        'message': 'Product configured for subscriptions. Complete setup in the Subscription tab.'
                    }
                }
        else:
            # Clear subscription configuration when disabled
            if self.subscription_product_id:
                return {
                    'warning': {
                        'title': 'Subscription Disabled',
                        'message': 'Subscription configuration will be removed. This action cannot be undone.'
                    }
                }

    @api.onchange('name', 'list_price')
    def _onchange_product_basics(self):
        """Update subscription definition when product basics change."""
        if self.is_subscription_product and self.subscription_product_id:
            # Sync name changes to subscription definition
            if self.name != self.subscription_product_id.name:
                self.subscription_product_id.name = f"{self.name} Subscription"
            
            # Sync price changes if no custom pricing set
            if (self.list_price and 
                self.subscription_product_id.default_price == 0):
                self.subscription_product_id.default_price = self.list_price

    # ==========================================
    # SUBSCRIPTION MANAGEMENT METHODS
    # ==========================================

    def _create_subscription_definition(self):
        """Auto-create subscription definition with intelligent defaults."""
        self.ensure_one()
        
        if self.subscription_product_id:
            raise UserError("Product already has a subscription definition")
        
        # Determine intelligent defaults based on product characteristics
        product_type = self._determine_subscription_type()
        scope = self._determine_subscription_scope()
        duration, duration_unit = self._determine_subscription_duration(product_type)
        
        # Create subscription definition
        subscription_values = {
            'name': f"{self.name} Subscription",
            'code': self.default_code or f"SUB_{self.id}",
            'product_id': self.id,
            'subscription_scope': scope,
            'product_type': product_type,
            'default_duration': duration,
            'duration_unit': duration_unit,
            'default_price': self.list_price or 0.0,
            'currency_id': self.env.company.currency_id.id,
            'is_renewable': True,
            'auto_renewal_enabled': False,  # Conservative default
            'requires_approval': False,
            'member_only': False,
        }
        
        # Add enterprise-specific defaults
        if scope == 'enterprise':
            subscription_values.update({
                'default_seat_count': 5,  # Conservative default
                'allow_seat_purchase': True,
            })
        
        subscription_product = self.env['ams.subscription.product'].create(subscription_values)
        self.subscription_product_id = subscription_product.id
        
        return subscription_product

    def _determine_subscription_type(self):
        """Determine subscription type based on product characteristics."""
        product_name = (self.name or '').lower()
        
        # Pattern matching for intelligent defaults
        if any(word in product_name for word in ['member', 'membership']):
            return 'membership'
        elif any(word in product_name for word in ['chapter', 'local', 'regional']):
            return 'chapter'
        elif any(word in product_name for word in ['committee', 'board', 'governance']):
            return 'committee'
        elif any(word in product_name for word in ['journal', 'publication', 'magazine', 'newsletter']):
            return 'publication'
        else:
            return 'membership'  # Safe default

    def _determine_subscription_scope(self):
        """Determine subscription scope based on product characteristics."""
        product_name = (self.name or '').lower()
        
        # Look for enterprise/corporate indicators
        if any(word in product_name for word in [
            'enterprise', 'corporate', 'organization', 'company', 
            'business', 'institutional', 'multi-user', 'team'
        ]):
            return 'enterprise'
        else:
            return 'individual'  # Default scope

    def _determine_subscription_duration(self, product_type):
        """Determine appropriate duration based on subscription type."""
        duration_map = {
            'membership': (12, 'months'),      # Annual membership standard
            'chapter': (12, 'months'),        # Annual chapter dues
            'committee': (24, 'months'),       # Committee terms often 2 years
            'publication': (12, 'months'),     # Annual subscription standard
        }
        
        return duration_map.get(product_type, (12, 'months'))

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_configure_subscription(self):
        """Open subscription configuration wizard or form."""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError("Enable subscription features first using the Subscription toggle")
        
        # Create subscription definition if it doesn't exist
        if not self.subscription_product_id:
            self._create_subscription_definition()
        
        # Open subscription product form
        return {
            'name': f'Configure Subscription - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'form',
            'res_id': self.subscription_product_id.id,
            'target': 'current',
            'context': {
                'default_product_id': self.id,
            },
        }

    def action_manage_pricing_tiers(self):
        """Open pricing tier management."""
        self.ensure_one()
        
        if not self.subscription_product_id:
            raise UserError("Configure subscription first")
        
        return {
            'name': f'Pricing Tiers - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.pricing.tier',
            'view_mode': 'tree,form',
            'domain': [('subscription_product_id', '=', self.subscription_product_id.id)],
            'context': {
                'default_subscription_product_id': self.subscription_product_id.id,
                'default_currency_id': self.subscription_product_id.currency_id.id,
            },
        }

    def action_subscription_builder_wizard(self):
        """Open subscription builder wizard for guided setup."""
        self.ensure_one()
        
        return {
            'name': f'Subscription Builder - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.builder.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_product_name': self.name,
                'default_base_price': self.list_price,
            },
        }

    def action_view_subscription_analytics(self):
        """View subscription analytics (integration point for future analytics module)."""
        self.ensure_one()
        
        if not self.subscription_product_id:
            raise UserError("No subscription configuration found")
        
        # Placeholder for future ams_analytics integration
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Analytics Available Soon',
                'message': 'Subscription analytics will be available when ams_analytics module is installed.',
                'type': 'info',
            }
        }

    # ==========================================
    # INTEGRATION METHODS FOR OTHER MODULES
    # ==========================================

    def get_subscription_definition(self):
        """Get subscription definition for integration with other modules."""
        self.ensure_one()
        if not self.is_subscription_product or not self.subscription_product_id:
            return None
        return self.subscription_product_id

    def get_member_pricing_info(self, member_type_id=None):
        """Get pricing information for specific member type."""
        self.ensure_one()
        if not self.subscription_product_id:
            return None
        
        return self.subscription_product_id.get_member_pricing(member_type_id)

    def check_subscription_eligibility(self, partner_id):
        """Check if partner is eligible for this subscription."""
        self.ensure_one()
        if not self.subscription_product_id:
            return {'eligible': True, 'message': 'No subscription restrictions'}
        
        return self.subscription_product_id.check_member_eligibility(partner_id)

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle subscription setup."""
        products = super().create(vals_list)
        
        for product, vals in zip(products, vals_list):
            # Auto-create subscription definition if subscription toggle is enabled
            if vals.get('is_subscription_product') and not vals.get('subscription_product_id'):
                try:
                    product._create_subscription_definition()
                except Exception:
                    # Log error but don't fail product creation
                    pass
        
        return products

    def write(self, vals):
        """Override write to handle subscription toggle changes."""
        # Handle subscription toggle changes
        if 'is_subscription_product' in vals:
            for product in self:
                if vals['is_subscription_product'] and not product.subscription_product_id:
                    # Enabling subscription - create definition
                    product._create_subscription_definition()
                elif not vals['is_subscription_product'] and product.subscription_product_id:
                    # Disabling subscription - remove definition
                    product.subscription_product_id.unlink()
        
        return super().write(vals)

    def unlink(self):
        """Override unlink to clean up subscription definitions."""
        # Remove associated subscription definitions
        subscription_products = self.mapped('subscription_product_id')
        result = super().unlink()
        subscription_products.unlink()
        return result

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('is_subscription_product', 'detailed_type')
    def _check_subscription_product_type(self):
        """Validate that subscription products are services."""
        for product in self:
            if product.is_subscription_product and product.detailed_type not in ['service']:
                raise ValidationError(
                    "Subscription products must be of type 'Service'. "
                    "Please change the product type or disable subscription features."
                )

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_subscription_summary(self):
        """Get subscription configuration summary."""
        self.ensure_one()
        
        if not self.is_subscription_product:
            return {'is_subscription': False}
        
        if not self.subscription_product_id:
            return {
                'is_subscription': True,
                'configured': False,
                'message': 'Subscription enabled but not configured'
            }
        
        sub = self.subscription_product_id
        return {
            'is_subscription': True,
            'configured': True,
            'scope': sub.subscription_scope,
            'type': sub.product_type,
            'duration': f"{sub.default_duration} {sub.duration_unit}",
            'base_price': sub.default_price,
            'pricing_tiers': len(sub.pricing_tier_ids),
            'renewable': sub.is_renewable,
            'auto_renewal': sub.auto_renewal_enabled,
            'member_only': sub.member_only,
            'requires_approval': sub.requires_approval,
        }