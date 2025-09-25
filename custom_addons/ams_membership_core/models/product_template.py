# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Main subscription toggle - this is the key field
    is_subscription_product = fields.Boolean(
        string='Subscription Product',
        default=False,
        help='Enable this to make the product create subscriptions/memberships when purchased'
    )
    
    # UPDATED: Add 'chapter' back to subscription types
    subscription_product_type = fields.Selection([
        ('membership', 'Membership'),
        ('subscription', 'General Subscription'),
        ('publication', 'Publication'),
        ('chapter', 'Chapter Membership'),  # Added back
    ], string='Subscription Type', default='membership',
       help='Type of subscription this product creates')
    
    # Chapter product classification can work alongside subscription products
    is_chapter_product = fields.Boolean(
        string='Chapter Product',
        compute='_compute_is_chapter_product',
        store=True,
        help='Automatically set when subscription type is chapter'
    )
    
    # Chapter-specific settings - ADDED BACK
    chapter_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('leadership', 'Leadership Access'),
        ('officer', 'Officer Access'),
    ], string='Chapter Access Level', default='basic',
       help='Access level granted by this chapter membership')
    
    chapter_type = fields.Selection([
        ('local', 'Local Chapter'),
        ('regional', 'Regional Chapter'),
        ('national', 'National Chapter'),
        ('special', 'Special Interest Chapter'),
    ], string='Chapter Type', default='local',
       help='Type of chapter this membership provides access to')
    
    chapter_location = fields.Char('Chapter Location', 
                                  help='Geographic location or specialty area of chapter')
    
    # Chapter-specific benefits
    provides_local_events = fields.Boolean('Provides Local Events Access', default=True)
    provides_chapter_documents = fields.Boolean('Provides Chapter Documents', default=True)
    provides_chapter_training = fields.Boolean('Provides Chapter Training', default=True)
    provides_networking_access = fields.Boolean('Provides Networking Access', default=True)
    
    subscription_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Subscription Period', default='annual',
       help='Default billing/renewal period for subscriptions created by this product')
    
    # Renewal Settings
    auto_renew_default = fields.Boolean(
        string='Auto-Renew by Default',
        default=True,
        help='New subscriptions will have auto-renewal enabled by default'
    )
    
    renewal_reminder_days = fields.Integer(
        string='Renewal Reminder Days',
        default=30,
        help='Send renewal reminders this many days before expiration'
    )
    
    # Lifecycle Settings (can override member type defaults)
    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help='Days after expiration before moving to next lifecycle state'
    )
    
    # Portal and Access Settings
    grant_portal_access = fields.Boolean(
        string='Grant Portal Access',
        default=True,
        help='Automatically grant portal access to subscribers'
    )
    
    portal_access_groups = fields.Many2many(
        'res.groups',
        'product_portal_group_rel',
        'product_id', 'group_id',
        string='Portal Access Groups',
        help='Additional portal groups granted to subscribers'
    )
    
    # Publication-specific settings
    publication_digital_access = fields.Boolean(
        string='Digital Access',
        default=True,
        help='Provides digital access to publication content'
    )
    
    publication_print_delivery = fields.Boolean(
        string='Print Delivery',
        default=False,
        help='Includes print delivery of publication'
    )
    
    publication_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], string='Publication Frequency', default='monthly')
    
    # Benefits Integration
    benefit_ids = fields.Many2many(
        'ams.benefit',
        'product_benefit_rel',
        'product_id', 'benefit_id',
        string='Included Benefits',
        help='Benefits automatically granted with this subscription product'
    )
    
    # Pricing and Financial Settings
    supports_proration = fields.Boolean(
        string='Supports Proration',
        default=True,
        help='Allow prorated billing for mid-cycle changes'
    )
    
    allows_upgrades = fields.Boolean(
        string='Allow Upgrades',
        default=True,
        help='Allow subscribers to upgrade to higher tiers'
    )
    
    allows_downgrades = fields.Boolean(
        string='Allow Downgrades',
        default=True,
        help='Allow subscribers to downgrade to lower tiers'
    )
    
    # Revenue Recognition (placeholder for future billing integration)
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Over Period'),
        ('milestone', 'Milestone-Based'),
    ], string='Revenue Recognition', default='deferred',
       help='How revenue should be recognized for this subscription')
    
    # Statistics and Reporting
    active_memberships_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_membership_stats',
        help='Number of active memberships created by this product'
    )
    
    active_subscriptions_count = fields.Integer(
        string='Active Subscriptions', 
        compute='_compute_subscription_stats',
        help='Number of active subscriptions created by this product'
    )
    
    total_subscription_revenue = fields.Monetary(
        string='Total Subscription Revenue',
        compute='_compute_revenue_stats',
        currency_field='currency_id',
        help='Total revenue from subscriptions of this product'
    )

    @api.depends('subscription_product_type')
    def _compute_is_chapter_product(self):
        """Auto-set chapter product flag when subscription type is chapter"""
        for product in self:
            product.is_chapter_product = (product.subscription_product_type == 'chapter')

    @api.depends('subscription_product_type')
    def _compute_membership_stats(self):
        """Compute membership statistics - UPDATED to include chapters"""
        for product in self:
            if product.subscription_product_type in ['membership', 'chapter']:
                active_count = self.env['ams.membership'].search_count([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                product.active_memberships_count = active_count
            else:
                product.active_memberships_count = 0
    
    @api.depends('subscription_product_type')
    def _compute_subscription_stats(self):
        """Compute subscription statistics"""
        for product in self:
            if product.subscription_product_type not in ['membership', 'chapter']:
                active_count = self.env['ams.subscription'].search_count([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                product.active_subscriptions_count = active_count
            else:
                product.active_subscriptions_count = 0
    
    def _compute_revenue_stats(self):
        """Compute revenue statistics"""
        for product in self:
            # Get total revenue from memberships (including chapters)
            membership_revenue = sum(self.env['ams.membership'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ]).mapped('membership_fee'))
            
            # Get total revenue from subscriptions  
            subscription_revenue = sum(self.env['ams.subscription'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ]).mapped('subscription_fee'))
            
            product.total_subscription_revenue = membership_revenue + subscription_revenue

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Handle subscription product toggle changes"""
        if self.is_subscription_product:
            # Set smart defaults for subscription products
            self.sale_ok = True
            
            # Handle different field names across Odoo versions
            if hasattr(self, 'detailed_type'):
                self.detailed_type = 'service'  # Odoo 15+
            else:
                self.type = 'service'  # Older versions
            
            # Set default category if not set
            if not self.categ_id or self.categ_id == self.env.ref('product.product_category_all'):
                self._set_subscription_category()
                
        else:
            # Reset subscription-specific fields
            self.subscription_product_type = 'membership'
            self.benefit_ids = [(5, 0, 0)]  # Clear benefits
    
    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Handle subscription type changes - UPDATED with chapter support"""
        if self.subscription_product_type:
            # Set type-specific defaults
            if self.subscription_product_type == 'publication':
                self.subscription_period = 'monthly'
                self.publication_digital_access = True
            elif self.subscription_product_type == 'membership':
                self.subscription_period = 'annual'
                self.grant_portal_access = True
            elif self.subscription_product_type == 'chapter':
                self.subscription_period = 'annual'
                self.grant_portal_access = True
                self.chapter_access_level = 'basic'
                self.provides_local_events = True
                self.provides_chapter_documents = True
            
            # Update category
            self._set_subscription_category()
    
    def _set_subscription_category(self):
        """Set appropriate product category based on subscription type - UPDATED"""
        if not self.is_subscription_product:
            return
            
        category_mapping = {
            'membership': 'Membership Products',
            'subscription': 'Subscription Products',
            'publication': 'Publication Subscriptions',
            'chapter': 'Chapter Memberships',  # Added
        }
        
        category_name = category_mapping.get(self.subscription_product_type, 'Subscription Products')
        
        # Find or create category
        category = self.env['product.category'].search([('name', '=', category_name)], limit=1)
        if not category:
            category = self.env['product.category'].create({
                'name': category_name,
                'parent_id': False,
            })
        
        self.categ_id = category.id
    
    def action_view_memberships(self):
        """View memberships created by this product"""
        self.ensure_one()
        
        return {
            'name': f'Memberships: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id,
                'search_default_active': 1,
            }
        }
    
    def action_view_subscriptions(self):
        """View subscriptions created by this product"""
        self.ensure_one()
        
        return {
            'name': f'Subscriptions: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id,
                'search_default_active': 1,
            }
        }
    
    def action_configure_benefits(self):
        """Configure benefits for this subscription product"""
        self.ensure_one()
        
        return {
            'name': f'Configure Benefits: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.benefit',
            'view_mode': 'list,form',
            'domain': [],
            'context': {
                'default_applies_to': 'membership' if self.subscription_product_type in ['membership', 'chapter'] else 'subscription',
                'search_default_active': 1,
            },
            'target': 'new',
        }
    
    def create_sample_subscription(self):
        """Create a sample subscription for testing (development helper)"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError(_("This is not a subscription product."))
        
        # Find a test partner or create one
        test_partner = self.env['res.partner'].search([('email', '=', 'test@example.com')], limit=1)
        if not test_partner:
            test_partner = self.env['res.partner'].create({
                'name': 'Test Member',
                'email': 'test@example.com',
                'is_member': True,
            })
        
        if self.subscription_product_type in ['membership', 'chapter']:
            record = self.env['ams.membership'].create({
                'partner_id': test_partner.id,
                'product_id': self.product_variant_id.id,
                'membership_fee': self.list_price,
                'state': 'active',
            })
            model = 'ams.membership'
        else:
            record = self.env['ams.subscription'].create({
                'partner_id': test_partner.id,
                'product_id': self.product_variant_id.id,
                'subscription_fee': self.list_price,
                'state': 'active',
            })
            model = 'ams.subscription'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample Subscription Created'),
            'res_model': model,
            'res_id': record.id,
            'view_mode': 'form',
        }
    
    # Integration with sale and invoice processing
    def create_subscription_from_sale(self, sale_line):
        """Create subscription/membership from sale order line"""
        if self.subscription_product_type in ['membership', 'chapter']:
            return self._create_membership_from_sale(sale_line)
        else:
            return self._create_subscription_from_sale(sale_line)
    
    def _create_membership_from_sale(self, sale_line):
        """Create membership from sale order line - UPDATED for chapters"""
        membership_vals = {
            'partner_id': sale_line.order_id.partner_id.id,
            'product_id': sale_line.product_id.id,
            'sale_order_id': sale_line.order_id.id,
            'sale_order_line_id': sale_line.id,
            'membership_fee': sale_line.price_subtotal,
            'auto_renew': self.auto_renew_default,
            'renewal_interval': self.subscription_period,
            'state': 'draft',  # Will be activated when invoice is paid
        }
        
        # Add chapter-specific notes
        if self.subscription_product_type == 'chapter':
            chapter_info = f"{self.chapter_type or 'Local'} Chapter"
            if self.chapter_location:
                chapter_info += f" - {self.chapter_location}"
            membership_vals['notes'] = f"Chapter Membership: {chapter_info}"
        
        return self.env['ams.membership'].create(membership_vals)
    
    def _create_subscription_from_sale(self, sale_line):
        """Create subscription from sale order line"""
        subscription_vals = {
            'partner_id': sale_line.order_id.partner_id.id,
            'product_id': sale_line.product_id.id,
            'sale_order_id': sale_line.order_id.id,
            'sale_order_line_id': sale_line.id,
            'subscription_fee': sale_line.price_subtotal,
            'auto_renew': self.auto_renew_default,
            'renewal_interval': self.subscription_period,
            'state': 'draft',  # Will be activated when invoice is paid
        }
        
        # Set publication-specific fields
        if self.subscription_product_type == 'publication':
            subscription_vals.update({
                'digital_access': self.publication_digital_access,
                'print_delivery': self.publication_print_delivery,
            })
        
        return self.env['ams.subscription'].create(subscription_vals)
    
    # Constraints and Validations
    @api.constrains('subscription_product_type', 'is_subscription_product')
    def _check_subscription_config(self):
        """Validate subscription configuration"""
        for product in self:
            if product.is_subscription_product and not product.subscription_product_type:
                raise ValidationError(_("Subscription products must have a subscription type."))
    
    @api.constrains('renewal_reminder_days')
    def _check_reminder_days(self):
        """Validate reminder days"""
        for product in self:
            if product.is_subscription_product and product.renewal_reminder_days < 0:
                raise ValidationError(_("Renewal reminder days cannot be negative."))
    
    @api.constrains('grace_period_days')
    def _check_grace_period(self):
        """Validate grace period"""
        for product in self:
            if product.is_subscription_product and product.grace_period_days < 0:
                raise ValidationError(_("Grace period days cannot be negative."))


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def action_create_membership_quick(self):
        """Quick action to create membership for this product variant"""
        self.ensure_one()
        
        if not self.is_subscription_product or self.subscription_product_type not in ['membership', 'chapter']:
            raise UserError(_("This product does not create memberships."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'ams.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_membership_fee': self.list_price,
            }
        }
    
    def action_create_subscription_quick(self):
        """Quick action to create subscription for this product variant"""
        self.ensure_one()
        
        if not self.is_subscription_product or self.subscription_product_type in ['membership', 'chapter']:
            raise UserError(_("This product does not create subscriptions."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Subscription'),
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_subscription_fee': self.list_price,
            }
        }