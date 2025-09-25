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
    
    # UPDATED: Remove 'chapter' from subscription types
    subscription_product_type = fields.Selection([
        ('membership', 'Membership'),
        ('subscription', 'General Subscription'),
        ('publication', 'Publication'),
        # Removed 'chapter' - will be handled by ams_chapters module
    ], string='Subscription Type', default='membership',
       help='Type of subscription this product creates')
    
    # NEW: Chapter product classification (separate from subscriptions)
    is_chapter_product = fields.Boolean(
        string='Chapter Product',
        default=False,
        help='Enable this for chapter membership products (requires ams_chapters module)'
    )
    
    chapter_product_type = fields.Selection([
        ('chapter_membership', 'Chapter Membership'),
        ('chapter_leadership', 'Chapter Leadership'),
        ('chapter_event_access', 'Chapter Event Access'),
    ], string='Chapter Product Type', 
       help='Type of chapter product (handled by ams_chapters module)')
    
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
    
    # REMOVED: Chapter-specific settings (moved to ams_chapters module)
    # These will be handled by the dedicated ams_chapters module
    
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
    
    # NEW: Chapter statistics (computed by ams_chapters module if installed)
    active_chapter_memberships_count = fields.Integer(
        string='Active Chapter Memberships',
        compute='_compute_chapter_stats',
        help='Number of active chapter memberships (requires ams_chapters module)'
    )
    
    total_subscription_revenue = fields.Monetary(
        string='Total Subscription Revenue',
        compute='_compute_revenue_stats',
        currency_field='currency_id',
        help='Total revenue from subscriptions of this product'
    )

    @api.depends('subscription_product_type')
    def _compute_membership_stats(self):
        """Compute membership statistics"""
        for product in self:
            if product.subscription_product_type == 'membership':
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
            if product.subscription_product_type not in ['membership']:  # Removed 'chapter' from exclusion
                active_count = self.env['ams.subscription'].search_count([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                product.active_subscriptions_count = active_count
            else:
                product.active_subscriptions_count = 0
    
    def _compute_chapter_stats(self):
        """Compute chapter statistics - handled by ams_chapters module if installed"""
        for product in self:
            if product.is_chapter_product and 'ams.chapter.membership' in self.env:
                # This will be implemented by the ams_chapters module
                try:
                    active_count = self.env['ams.chapter.membership'].search_count([
                        ('product_id.product_tmpl_id', '=', product.id),
                        ('state', '=', 'active')
                    ])
                    product.active_chapter_memberships_count = active_count
                except Exception:
                    product.active_chapter_memberships_count = 0
            else:
                product.active_chapter_memberships_count = 0
    
    def _compute_revenue_stats(self):
        """Compute revenue statistics"""
        for product in self:
            # Get total revenue from memberships
            membership_revenue = sum(self.env['ams.membership'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ]).mapped('membership_fee'))
            
            # Get total revenue from subscriptions  
            subscription_revenue = sum(self.env['ams.subscription'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('state', '=', 'active')
            ]).mapped('subscription_fee'))
            
            # Get chapter revenue if ams_chapters module is installed
            chapter_revenue = 0
            if product.is_chapter_product and 'ams.chapter.membership' in self.env:
                try:
                    chapter_revenue = sum(self.env['ams.chapter.membership'].search([
                        ('product_id.product_tmpl_id', '=', product.id),
                        ('state', '=', 'active')
                    ]).mapped('membership_fee'))
                except Exception:
                    chapter_revenue = 0
            
            product.total_subscription_revenue = membership_revenue + subscription_revenue + chapter_revenue

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
    
    @api.onchange('is_chapter_product')
    def _onchange_is_chapter_product(self):
        """Handle chapter product toggle changes"""
        if self.is_chapter_product:
            # Set smart defaults for chapter products
            self.sale_ok = True
            
            # Handle different field names across Odoo versions
            if hasattr(self, 'detailed_type'):
                self.detailed_type = 'service'  # Odoo 15+
            else:
                self.type = 'service'  # Older versions
            
            # Set chapter category
            self._set_chapter_category()
            
            # Chapter products should not also be subscription products
            self.is_subscription_product = False
        else:
            # Reset chapter-specific fields
            self.chapter_product_type = False
    
    @api.onchange('subscription_product_type')
    def _onchange_subscription_product_type(self):
        """Handle subscription type changes"""
        if self.subscription_product_type:
            # Set type-specific defaults
            if self.subscription_product_type == 'publication':
                self.subscription_period = 'monthly'
                self.publication_digital_access = True
            elif self.subscription_product_type == 'membership':
                self.subscription_period = 'annual'
                self.grant_portal_access = True
            
            # Update category
            self._set_subscription_category()
    
    def _set_subscription_category(self):
        """Set appropriate product category based on subscription type"""
        if not self.is_subscription_product:
            return
            
        category_mapping = {
            'membership': 'Membership Products',
            'subscription': 'Subscription Products',
            'publication': 'Publication Subscriptions',
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
    
    def _set_chapter_category(self):
        """Set appropriate product category for chapter products"""
        category_name = 'Chapter Products'
        
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
    
    def action_view_chapter_memberships(self):
        """View chapter memberships created by this product"""
        self.ensure_one()
        
        if not self.is_chapter_product or 'ams.chapter.membership' not in self.env:
            raise UserError(_("This requires the ams_chapters module to be installed."))
        
        return {
            'name': f'Chapter Memberships: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.chapter.membership',
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
                'default_applies_to': 'membership' if self.subscription_product_type == 'membership' else 'subscription',
                'search_default_active': 1,
            },
            'target': 'new',
        }
    
    def create_sample_subscription(self):
        """Create a sample subscription for testing (development helper)"""
        self.ensure_one()
        
        if not self.is_subscription_product and not self.is_chapter_product:
            raise UserError(_("This is not a subscription or chapter product."))
        
        # Find a test partner or create one
        test_partner = self.env['res.partner'].search([('email', '=', 'test@example.com')], limit=1)
        if not test_partner:
            test_partner = self.env['res.partner'].create({
                'name': 'Test Member',
                'email': 'test@example.com',
                'is_member': True,
            })
        
        if self.is_chapter_product:
            # Chapter products will be handled by ams_chapters module
            raise UserError(_("Chapter product testing requires the ams_chapters module."))
        elif self.subscription_product_type == 'membership':
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
        if self.is_chapter_product:
            # Chapter products are handled by ams_chapters module
            return self._delegate_to_chapter_module(sale_line)
        elif self.is_subscription_product:
            if self.subscription_product_type == 'membership':
                return self._create_membership_from_sale(sale_line)
            else:
                return self._create_subscription_from_sale(sale_line)
        
        return False
    
    def _delegate_to_chapter_module(self, sale_line):
        """Delegate chapter product handling to ams_chapters module"""
        if 'ams.chapter.membership' in self.env:
            # Call the ams_chapters module method
            try:
                return self.env['ams.chapter.membership'].create_from_sale_line(sale_line)
            except Exception as e:
                from odoo.exceptions import UserError
                raise UserError(f"Chapter module error: {str(e)}")
        else:
            from odoo.exceptions import UserError
            raise UserError(_("Chapter products require the ams_chapters module to be installed."))
    
    def _create_membership_from_sale(self, sale_line):
        """Create membership from sale order line"""
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
    
    @api.constrains('is_subscription_product', 'is_chapter_product')
    def _check_product_type_conflict(self):
        """Ensure product is not both subscription and chapter product"""
        for product in self:
            if product.is_subscription_product and product.is_chapter_product:
                raise ValidationError(_("A product cannot be both a subscription product and a chapter product."))
    
    @api.constrains('renewal_reminder_days')
    def _check_reminder_days(self):
        """Validate reminder days"""
        for product in self:
            if (product.is_subscription_product or product.is_chapter_product) and product.renewal_reminder_days < 0:
                raise ValidationError(_("Renewal reminder days cannot be negative."))
    
    @api.constrains('grace_period_days')
    def _check_grace_period(self):
        """Validate grace period"""
        for product in self:
            if (product.is_subscription_product or product.is_chapter_product) and product.grace_period_days < 0:
                raise ValidationError(_("Grace period days cannot be negative."))


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def action_create_membership_quick(self):
        """Quick action to create membership for this product variant"""
        self.ensure_one()
        
        if not self.is_subscription_product or self.subscription_product_type != 'membership':
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
        
        if not self.is_subscription_product or self.subscription_product_type == 'membership':
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
    
    def action_create_chapter_membership_quick(self):
        """Quick action to create chapter membership for this product variant"""
        self.ensure_one()
        
        if not self.is_chapter_product:
            raise UserError(_("This product does not create chapter memberships."))
        
        if 'ams.chapter.membership' not in self.env:
            raise UserError(_("Chapter functionality requires the ams_chapters module."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Chapter Membership'),
            'res_model': 'ams.chapter.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_membership_fee': self.list_price,
            }
        }