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
    
    # Enhanced subscription types with better chapter support
    subscription_product_type = fields.Selection([
        ('membership', 'Regular Membership'),
        ('chapter', 'Chapter Membership'),
        ('subscription', 'General Subscription'),
        ('publication', 'Publication'),
    ], string='Subscription Type', default='membership',
       help='Type of subscription this product creates')
    
    # Chapter product classification
    is_chapter_product = fields.Boolean(
        string='Chapter Product',
        compute='_compute_is_chapter_product',
        store=True,
        help='Automatically set when subscription type is chapter'
    )
    
    # Enhanced chapter-specific settings
    chapter_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('leadership', 'Leadership Access'),
        ('officer', 'Officer Access'),
        ('board', 'Board Member'),
    ], string='Chapter Access Level', default='basic',
       help='Access level granted by this chapter membership')
    
    chapter_type = fields.Selection([
        ('local', 'Local Chapter'),
        ('regional', 'Regional Chapter'),
        ('state', 'State Chapter'),
        ('national', 'National Chapter'),
        ('international', 'International Chapter'),
        ('special', 'Special Interest Chapter'),
        ('student', 'Student Chapter'),
        ('professional', 'Professional Chapter'),
    ], string='Chapter Type', default='local',
       help='Type and scope of chapter this membership provides access to')
    
    # Enhanced geographic support
    chapter_location = fields.Char('Chapter Location', 
                                  help='Primary geographic location or area of focus')
    chapter_city = fields.Char('Chapter City')
    chapter_state = fields.Char('Chapter State/Province') 
    chapter_country_id = fields.Many2one('res.country', 'Chapter Country')
    chapter_zip = fields.Char('Chapter ZIP/Postal Code')
    chapter_timezone = fields.Selection('_tz_get', string='Chapter Timezone')
    
    # Chapter hierarchy support
    parent_chapter_id = fields.Many2one('product.template', 'Parent Chapter',
                                       domain=[('is_chapter_product', '=', True)],
                                       help='Parent chapter for hierarchical structures')
    child_chapter_ids = fields.One2many('product.template', 'parent_chapter_id', 
                                       'Child Chapters')
    chapter_level = fields.Integer('Chapter Level', default=1,
                                  help='Hierarchical level (1=top level, 2=sub-chapter, etc.)')
    
    # Chapter contact information
    chapter_president = fields.Char('Chapter President/Leader')
    chapter_contact_email = fields.Char('Chapter Contact Email')
    chapter_contact_phone = fields.Char('Chapter Contact Phone')
    chapter_website = fields.Char('Chapter Website')
    
    # Chapter meeting and activity information
    chapter_meeting_schedule = fields.Text('Meeting Schedule')
    chapter_meeting_location = fields.Text('Meeting Location')
    chapter_established_date = fields.Date('Chapter Established Date')
    
    # Enhanced chapter benefits and features
    provides_local_events = fields.Boolean('Provides Local Events Access', default=True)
    provides_chapter_documents = fields.Boolean('Provides Chapter Documents', default=True)
    provides_chapter_training = fields.Boolean('Provides Chapter Training', default=True)
    provides_networking_access = fields.Boolean('Provides Networking Access', default=True)
    provides_mentorship = fields.Boolean('Provides Mentorship Programs', default=False)
    provides_certification = fields.Boolean('Provides Certification Programs', default=False)
    provides_job_board = fields.Boolean('Provides Job Board Access', default=False)
    provides_newsletter = fields.Boolean('Provides Chapter Newsletter', default=True)
    
    # Chapter status and activity
    chapter_status = fields.Selection([
        ('active', 'Active'),
        ('forming', 'Forming'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('dissolved', 'Dissolved'),
    ], string='Chapter Status', default='active')
    
    chapter_member_limit = fields.Integer('Member Limit', 
                                         help='Maximum number of members (0 = unlimited)')
    chapter_minimum_members = fields.Integer('Minimum Members Required', default=10,
                                           help='Minimum members needed to maintain chapter status')
    
    # Regular subscription settings (existing)
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
    
    # Lifecycle Settings
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
    
    # Publication-specific settings (existing)
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
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Over Period'),
        ('milestone', 'Milestone-Based'),
    ], string='Revenue Recognition', default='deferred',
       help='How revenue should be recognized for this subscription')
    
    # Enhanced Statistics and Reporting
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
    
    # Chapter-specific statistics
    chapter_member_count = fields.Integer(
        string='Chapter Members',
        compute='_compute_chapter_stats',
        help='Current number of active chapter members'
    )
    
    chapter_retention_rate = fields.Float(
        string='Retention Rate (%)',
        compute='_compute_chapter_stats',
        help='Chapter membership retention rate'
    )

    @api.model
    def _tz_get(self):
        """Get timezone options"""
        from pytz import timezone, all_timezones
        timezones = [(tz, tz) for tz in sorted(all_timezones)]
        return timezones

    @api.depends('subscription_product_type')
    def _compute_is_chapter_product(self):
        """Auto-set chapter product flag when subscription type is chapter"""
        for product in self:
            product.is_chapter_product = (product.subscription_product_type == 'chapter')

    @api.depends('subscription_product_type', 'is_chapter_product')
    def _compute_membership_stats(self):
        """Compute membership statistics including chapters"""
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
    
    @api.depends('is_chapter_product', 'active_memberships_count')
    def _compute_chapter_stats(self):
        """Compute chapter-specific statistics"""
        for product in self:
            if product.is_chapter_product:
                # Get active chapter memberships
                active_memberships = self.env['ams.membership'].search([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                
                product.chapter_member_count = len(active_memberships)
                
                # Calculate retention rate (simplified)
                if active_memberships:
                    renewed_count = active_memberships.filtered(lambda m: m.last_renewal_date).ids
                    if len(active_memberships) > 0:
                        product.chapter_retention_rate = (len(renewed_count) / len(active_memberships)) * 100
                    else:
                        product.chapter_retention_rate = 0.0
                else:
                    product.chapter_retention_rate = 0.0
            else:
                product.chapter_member_count = 0
                product.chapter_retention_rate = 0.0
    
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
        """Handle subscription type changes with enhanced chapter support"""
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
                self.provides_networking_access = True
                self.provides_newsletter = True
                # Set some smart defaults for chapters
                if not self.chapter_location:
                    self.chapter_location = 'Local Area'
            
            # Update category
            self._set_subscription_category()
    
    @api.onchange('parent_chapter_id')
    def _onchange_parent_chapter(self):
        """Update chapter level based on parent"""
        if self.parent_chapter_id:
            self.chapter_level = self.parent_chapter_id.chapter_level + 1
            # Inherit some settings from parent
            if not self.chapter_country_id and self.parent_chapter_id.chapter_country_id:
                self.chapter_country_id = self.parent_chapter_id.chapter_country_id
            if not self.chapter_state and self.parent_chapter_id.chapter_state:
                self.chapter_state = self.parent_chapter_id.chapter_state
        else:
            self.chapter_level = 1
    
    def _set_subscription_category(self):
        """Set appropriate product category based on subscription type"""
        if not self.is_subscription_product:
            return
            
        category_mapping = {
            'membership': 'Membership Products',
            'subscription': 'Subscription Products',
            'publication': 'Publication Subscriptions',
            'chapter': 'Chapter Memberships',
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
    
    # Chapter-specific actions
    def action_view_chapter_members(self):
        """View chapter members"""
        self.ensure_one()
        
        if not self.is_chapter_product:
            raise UserError(_("This is not a chapter product."))
        
        return {
            'name': f'Chapter Members: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership',
            'view_mode': 'list,kanban,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id), ('is_chapter_membership', '=', True)],
            'context': {
                'default_product_id': self.product_variant_id.id,
                'search_default_active': 1,
                'group_by': 'chapter_access_level',
            }
        }
    
    def action_chapter_dashboard(self):
        """Open chapter dashboard"""
        self.ensure_one()
        
        if not self.is_chapter_product:
            raise UserError(_("This is not a chapter product."))
        
        return {
            'name': f'Chapter Dashboard: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'chapter.dashboard.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_chapter_product_id': self.id}
        }
    
    def action_view_child_chapters(self):
        """View child chapters"""
        self.ensure_one()
        
        return {
            'name': f'Sub-Chapters of: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'kanban,list,form',
            'domain': [('parent_chapter_id', '=', self.id)],
            'context': {
                'default_parent_chapter_id': self.id,
                'default_is_subscription_product': True,
                'default_subscription_product_type': 'chapter',
            }
        }
    
    def action_create_sub_chapter(self):
        """Create a sub-chapter"""
        self.ensure_one()
        
        if not self.is_chapter_product:
            raise UserError(_("Only chapter products can have sub-chapters."))
        
        return {
            'name': f'Create Sub-Chapter of: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_parent_chapter_id': self.id,
                'default_is_subscription_product': True,
                'default_subscription_product_type': 'chapter',
                'default_chapter_level': self.chapter_level + 1,
                'default_chapter_country_id': self.chapter_country_id.id if self.chapter_country_id else False,
                'default_chapter_state': self.chapter_state,
            }
        }
    
    # Existing methods (abbreviated for space)
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
    
    # Integration with sale and invoice processing
    def create_subscription_from_sale(self, sale_line):
        """Create subscription/membership from sale order line"""
        if self.subscription_product_type in ['membership', 'chapter']:
            return self._create_membership_from_sale(sale_line)
        else:
            return self._create_subscription_from_sale(sale_line)
    
    def _create_membership_from_sale(self, sale_line):
        """Create membership from sale order line - Enhanced for chapters"""
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
        
        # Add chapter-specific notes and information
        if self.subscription_product_type == 'chapter':
            chapter_info = f"{self.chapter_type.title() if self.chapter_type else 'Local'} Chapter"
            if self.chapter_location:
                chapter_info += f" - {self.chapter_location}"
            if self.chapter_city:
                chapter_info += f", {self.chapter_city}"
            if self.chapter_state:
                chapter_info += f", {self.chapter_state}"
            
            membership_vals['notes'] = f"Chapter Membership: {chapter_info}\n"
            if self.chapter_contact_email:
                membership_vals['notes'] += f"Chapter Contact: {self.chapter_contact_email}\n"
            if self.chapter_meeting_schedule:
                membership_vals['notes'] += f"Meeting Schedule: {self.chapter_meeting_schedule}\n"
        
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
    
    @api.constrains('parent_chapter_id')
    def _check_chapter_hierarchy(self):
        """Validate chapter hierarchy to prevent loops"""
        for product in self:
            if product.parent_chapter_id:
                # Check for circular references
                parent = product.parent_chapter_id
                visited = set()
                while parent:
                    if parent.id in visited or parent.id == product.id:
                        raise ValidationError(_("Circular chapter hierarchy detected."))
                    visited.add(parent.id)
                    parent = parent.parent_chapter_id
    
    @api.constrains('chapter_member_limit')
    def _check_member_limit(self):
        """Validate chapter member limits"""
        for product in self:
            if (product.is_chapter_product and 
                product.chapter_member_limit > 0 and 
                product.chapter_member_count > product.chapter_member_limit):
                raise ValidationError(
                    _("Chapter already has %d members, which exceeds the limit of %d") % 
                    (product.chapter_member_count, product.chapter_member_limit)
                )
    
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
        
        context = {
            'default_product_id': self.id,
            'default_membership_fee': self.list_price,
        }
        
        # Add chapter-specific context
        if self.subscription_product_type == 'chapter':
            context.update({
                'default_is_chapter_membership': True,
                'default_notes': f"Chapter: {self.chapter_location or self.name}"
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Membership'),
            'res_model': 'ams.membership',
            'view_mode': 'form',
            'target': 'new',
            'context': context
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