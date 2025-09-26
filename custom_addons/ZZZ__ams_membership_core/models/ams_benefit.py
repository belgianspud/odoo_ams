# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AMSBenefit(models.Model):
    _name = 'ams.benefit'
    _description = 'Member/Subscriber Benefit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char('Benefit Name', required=True, tracking=True)
    code = fields.Char('Benefit Code', help='Unique code for this benefit')
    description = fields.Html('Description', help='Detailed description of this benefit')
    sequence = fields.Integer('Sequence', default=10, help='Order in which benefits are displayed')
    active = fields.Boolean('Active', default=True, tracking=True)
    
    # Enhanced Benefit Configuration for Chapter Support
    benefit_type = fields.Selection([
        ('access', 'Access/Permission'),
        ('discount', 'Discount/Pricing'),
        ('content', 'Content Access'),
        ('service', 'Service/Support'),
        ('physical', 'Physical Item'),
        ('digital', 'Digital Resource'),
        ('event', 'Event Access'),
        ('networking', 'Networking'),
        ('chapter', 'Chapter-Specific'),  # NEW: Chapter-specific benefits
        ('other', 'Other'),
    ], string='Benefit Type', required=True, default='access')
    
    # Enhanced Applicability for Chapter Support
    applies_to = fields.Selection([
        ('membership', 'Regular Memberships Only'),
        ('chapter', 'Chapter Memberships Only'),  # NEW: Chapter-specific
        ('subscription', 'Subscriptions Only'),
        ('membership_and_chapter', 'All Memberships'),  # NEW: Both regular and chapter memberships
        ('all', 'All (Memberships & Subscriptions)'),
    ], string='Applies To', default='all', required=True)
    
    # Chapter-Specific Benefit Configuration
    chapter_access_level_required = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('leadership', 'Leadership Access'),
        ('officer', 'Officer Access'),
        ('board', 'Board Member'),
    ], string='Chapter Access Level Required',
       help='Minimum chapter access level required for this benefit')
    
    chapter_type_restriction = fields.Selection([
        ('any', 'Any Chapter Type'),
        ('local', 'Local Chapters Only'),
        ('regional', 'Regional Chapters Only'),
        ('state', 'State Chapters Only'),
        ('national', 'National Chapters Only'),
        ('special', 'Special Interest Only'),
    ], string='Chapter Type Restriction', default='any',
       help='Restrict benefit to specific chapter types')
    
    geographic_restriction = fields.Boolean('Geographic Restriction',
                                          help='Benefit is restricted by geographic location')
    restricted_countries = fields.Many2many('res.country', string='Restricted Countries',
                                          help='Countries where this benefit applies')
    restricted_states = fields.Text('Restricted States/Provinces',
                                   help='States or provinces where this benefit applies (comma-separated)')
    
    # Benefit Details
    is_quantifiable = fields.Boolean('Has Quantity/Limit', 
                                   help='This benefit has a usage limit or quantity')
    quantity_limit = fields.Integer('Quantity Limit', 
                                   help='Maximum number of times this benefit can be used')
    reset_period = fields.Selection([
        ('never', 'Never Reset'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('membership_period', 'Per Membership Period'),
        ('chapter_term', 'Per Chapter Term'),  # NEW: Chapter-specific reset
    ], string='Reset Period', default='never',
       help='How often the quantity limit resets')
    
    # Discount Configuration (for discount-type benefits)
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Type', default='percentage')
    discount_percentage = fields.Float('Discount Percentage', 
                                     help='Discount percentage (0-100)')
    discount_amount = fields.Monetary('Discount Amount', currency_field='currency_id',
                                    help='Fixed discount amount')
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Product Integration (for discount benefits)
    applies_to_products = fields.Boolean('Applies to Specific Products')
    product_ids = fields.Many2many('product.product', string='Products',
                                  help='Products this benefit applies to')
    product_category_ids = fields.Many2many('product.category', string='Product Categories',
                                           help='Product categories this benefit applies to')
    
    # Enhanced Chapter-Specific Product Integration
    applies_to_chapter_products = fields.Boolean('Chapter Product Discounts',
                                                help='Applies discounts to other chapter products')
    excluded_chapter_products = fields.Many2many('product.product', 
                                                relation='benefit_excluded_chapter_rel',
                                                string='Excluded Chapter Products',
                                                domain=[('subscription_product_type', '=', 'chapter')],
                                                help='Chapter products excluded from discount')
    
    # Access Control (for access-type benefits)
    portal_access_group_ids = fields.Many2many('res.groups', 
                                              relation='benefit_portal_group_rel',
                                              string='Portal Access Groups',
                                              help='Portal groups granted by this benefit')
    website_access_pages = fields.Text('Website Access Pages',
                                      help='Website pages/sections accessible with this benefit')
    
    # Enhanced Chapter Access Control
    chapter_portal_groups = fields.Many2many('res.groups',
                                           relation='benefit_chapter_portal_rel',
                                           string='Chapter Portal Groups',
                                           help='Additional portal groups for chapter members')
    chapter_resource_access = fields.Text('Chapter Resource Access',
                                        help='Chapter-specific resources accessible with this benefit')
    
    # Content Access (for content-type benefits)
    content_categories = fields.Text('Content Categories',
                                   help='Categories of content accessible with this benefit')
    digital_resources = fields.Text('Digital Resources',
                                   help='Digital resources included with this benefit')
    
    # Enhanced Chapter Content Access
    chapter_document_access = fields.Boolean('Chapter Document Access',
                                           help='Access to chapter-specific documents')
    chapter_training_access = fields.Boolean('Chapter Training Access',
                                           help='Access to chapter training materials')
    chapter_meeting_access = fields.Boolean('Chapter Meeting Access',
                                          help='Access to chapter meeting recordings/materials')
    
    # Event Access (for event-type benefits)
    event_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('vip', 'VIP Access'),
        ('speaker', 'Speaker Access'),
    ], string='Event Access Level', default='basic')
    early_bird_access = fields.Boolean('Early Bird Registration',
                                      help='Access to early bird event registration')
    
    # Enhanced Chapter Event Access
    chapter_event_priority = fields.Boolean('Chapter Event Priority',
                                          help='Priority registration for chapter events')
    multi_chapter_events = fields.Boolean('Multi-Chapter Event Access',
                                        help='Access to events from other chapters')
    
    # Physical Benefits
    shipping_required = fields.Boolean('Requires Shipping',
                                      help='This benefit requires physical shipping')
    shipping_frequency = fields.Selection([
        ('once', 'One Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('chapter_schedule', 'Per Chapter Schedule'),  # NEW: Chapter-specific schedule
    ], string='Shipping Frequency', default='once')
    
    # Chapter-Specific Physical Benefits
    chapter_materials_shipping = fields.Boolean('Chapter Materials Shipping',
                                               help='Ships chapter-specific materials')
    local_pickup_available = fields.Boolean('Local Pickup Available',
                                           help='Available for local pickup at chapter location')
    
    # Automation Settings
    auto_apply = fields.Boolean('Auto Apply',
                               help='Automatically apply this benefit when conditions are met')
    requires_approval = fields.Boolean('Requires Approval',
                                      help='Manual approval required before granting this benefit')
    
    # Enhanced Chapter Automation
    chapter_officer_approval = fields.Boolean('Chapter Officer Approval',
                                            help='Requires approval from chapter officer')
    auto_apply_chapter_role = fields.Selection([
        ('member', 'All Chapter Members'),
        ('volunteer', 'Chapter Volunteers'),
        ('committee_member', 'Committee Members'),
        ('officer', 'Chapter Officers'),
        ('board_member', 'Board Members'),
    ], string='Auto Apply to Role',
       help='Automatically apply to members with specific chapter roles')
    
    # Tracking and Analytics
    usage_count = fields.Integer('Total Usage Count', readonly=True, default=0)
    member_count = fields.Integer('Active Members with Benefit', 
                                 compute='_compute_member_count', store=True)
    chapter_member_count = fields.Integer('Chapter Members with Benefit',
                                        compute='_compute_member_count', store=True)
    
    # Related Records - Enhanced for Chapter Support
    membership_ids = fields.Many2many('ams.membership', 'membership_benefit_rel',
                                     'benefit_id', 'membership_id', 
                                     string='Active Memberships')
    subscription_ids = fields.Many2many('ams.subscription', 'subscription_benefit_rel',
                                       'benefit_id', 'subscription_id',
                                       string='Active Subscriptions')
    
    # Chapter-Specific Relations
    chapter_membership_ids = fields.Many2many('ams.membership', 'chapter_membership_benefit_rel',
                                            'benefit_id', 'membership_id',
                                            string='Active Chapter Memberships',
                                            domain=[('is_chapter_membership', '=', True)])
    
    # Usage Tracking
    usage_log_ids = fields.One2many('ams.benefit.usage', 'benefit_id', 'Usage Log')
    
    @api.depends('membership_ids', 'subscription_ids', 'membership_ids.is_chapter_membership')
    def _compute_member_count(self):
        for benefit in self:
            # Regular member count (all active memberships + subscriptions)
            active_memberships = benefit.membership_ids.filtered(lambda m: m.state == 'active')
            active_subscriptions = benefit.subscription_ids.filtered(lambda s: s.state == 'active')
            
            unique_partners = set()
            unique_partners.update(active_memberships.mapped('partner_id.id'))
            unique_partners.update(active_subscriptions.mapped('partner_id.id'))
            
            benefit.member_count = len(unique_partners)
            
            # Chapter member count (only chapter memberships)
            chapter_memberships = active_memberships.filtered(lambda m: m.is_chapter_membership)
            chapter_partners = set(chapter_memberships.mapped('partner_id.id'))
            benefit.chapter_member_count = len(chapter_partners)
    
    @api.model
    def create(self, vals):
        """Generate unique code if not provided"""
        if not vals.get('code'):
            # Generate code from name
            name = vals.get('name', '')
            code = ''.join([c.upper() for c in name if c.isalnum()])[:10]
            if code:
                # Ensure uniqueness
                counter = 1
                original_code = code
                while self.search([('code', '=', code)]):
                    code = f"{original_code}{counter}"
                    counter += 1
                vals['code'] = code
        
        return super().create(vals)
    
    def get_discount_amount(self, original_amount):
        """Calculate discount amount for a given original amount"""
        self.ensure_one()
        
        if self.benefit_type != 'discount':
            return 0.0
        
        if self.discount_type == 'percentage':
            return original_amount * (self.discount_percentage / 100.0)
        else:
            return min(self.discount_amount, original_amount)
    
    def check_usage_limit(self, partner_id, period_start=None):
        """Check if usage limit is exceeded for a partner"""
        self.ensure_one()
        
        if not self.is_quantifiable:
            return True, 0  # No limit
        
        # Calculate usage in current period
        domain = [
            ('benefit_id', '=', self.id),
            ('partner_id', '=', partner_id),
        ]
        
        if period_start:
            domain.append(('usage_date', '>=', period_start))
        
        usage_count = len(self.env['ams.benefit.usage'].search(domain))
        
        remaining = self.quantity_limit - usage_count
        can_use = remaining > 0
        
        return can_use, remaining
    
    def is_applicable_to_membership(self, membership):
        """Check if this benefit is applicable to a specific membership"""
        self.ensure_one()
        
        # Check basic applicability
        if self.applies_to == 'subscription':
            return False
        elif self.applies_to == 'membership' and membership.is_chapter_membership:
            return False
        elif self.applies_to == 'chapter' and not membership.is_chapter_membership:
            return False
        
        # For chapter memberships, check additional restrictions
        if membership.is_chapter_membership:
            # Check chapter access level requirement
            if (self.chapter_access_level_required and 
                membership.chapter_access_level != self.chapter_access_level_required):
                return False
            
            # Check chapter type restriction
            if (self.chapter_type_restriction != 'any' and 
                membership.chapter_type != self.chapter_type_restriction):
                return False
            
            # Check geographic restrictions
            if self.geographic_restriction:
                if not self._check_geographic_eligibility(membership):
                    return False
            
            # Check role-based auto-application
            if (self.auto_apply_chapter_role and 
                membership.chapter_role != self.auto_apply_chapter_role):
                return False
        
        return True
    
    def _check_geographic_eligibility(self, membership):
        """Check if membership meets geographic restrictions"""
        self.ensure_one()
        
        if not self.geographic_restriction:
            return True
        
        # Check country restrictions
        if self.restricted_countries:
            member_country = membership.partner_id.country_id
            chapter_country = membership.chapter_country_id
            
            if member_country not in self.restricted_countries and chapter_country not in self.restricted_countries:
                return False
        
        # Check state/province restrictions
        if self.restricted_states:
            restricted_states = [s.strip().lower() for s in self.restricted_states.split(',')]
            member_state = (membership.partner_id.state_id.name or '').lower()
            chapter_state = (membership.chapter_state or '').lower()
            
            if member_state not in restricted_states and chapter_state not in restricted_states:
                return False
        
        return True
    
    def record_usage(self, partner_id, quantity=1, notes=None, membership_id=None):
        """Enhanced usage recording with chapter context"""
        self.ensure_one()
        
        # Check if usage is allowed
        can_use, remaining = self.check_usage_limit(partner_id)
        if not can_use:
            raise ValidationError(_("Usage limit exceeded for benefit: %s") % self.name)
        
        # Create usage record with chapter context
        usage_vals = {
            'benefit_id': self.id,
            'partner_id': partner_id,
            'quantity': quantity,
            'usage_date': fields.Datetime.now(),
            'notes': notes or '',
        }
        
        # Add chapter context if available
        if membership_id:
            membership = self.env['ams.membership'].browse(membership_id)
            if membership.is_chapter_membership:
                usage_vals['notes'] = (usage_vals['notes'] + 
                                     f"\nChapter: {membership.product_id.name}")
        
        usage = self.env['ams.benefit.usage'].create(usage_vals)
        
        # Update usage count
        self.usage_count += quantity
        
        return usage
    
    def apply_to_partner(self, partner_id, membership_id=None):
        """Enhanced partner application with chapter support"""
        self.ensure_one()
        
        partner = self.env['res.partner'].browse(partner_id)
        membership = self.env['ams.membership'].browse(membership_id) if membership_id else None
        
        # Add portal groups
        if self.portal_access_group_ids and partner.portal_user_id:
            partner.portal_user_id.groups_id = [(4, group.id) for group in self.portal_access_group_ids]
        
        # Add chapter-specific portal groups
        if (membership and membership.is_chapter_membership and 
            self.chapter_portal_groups and partner.portal_user_id):
            partner.portal_user_id.groups_id = [(4, group.id) for group in self.chapter_portal_groups]
        
        # Log the benefit application
        context_msg = ""
        if membership and membership.is_chapter_membership:
            context_msg = f" for {membership.product_id.name}"
        
        partner.message_post(
            body=_("Benefit applied: %s%s") % (self.name, context_msg),
            message_type='notification'
        )
    
    def remove_from_partner(self, partner_id, membership_id=None):
        """Enhanced partner removal with chapter support"""
        self.ensure_one()
        
        partner = self.env['res.partner'].browse(partner_id)
        membership = self.env['ams.membership'].browse(membership_id) if membership_id else None
        
        # Remove portal groups
        if self.portal_access_group_ids and partner.portal_user_id:
            partner.portal_user_id.groups_id = [(3, group.id) for group in self.portal_access_group_ids]
        
        # Remove chapter-specific portal groups
        if (membership and membership.is_chapter_membership and 
            self.chapter_portal_groups and partner.portal_user_id):
            partner.portal_user_id.groups_id = [(3, group.id) for group in self.chapter_portal_groups]
        
        # Log the benefit removal
        context_msg = ""
        if membership and membership.is_chapter_membership:
            context_msg = f" from {membership.product_id.name}"
        
        partner.message_post(
            body=_("Benefit removed: %s%s") % (self.name, context_msg),
            message_type='notification'
        )
    
    def action_view_usage_log(self):
        """View usage log for this benefit"""
        return {
            'name': _('Usage Log: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.benefit.usage',
            'view_mode': 'list,form',
            'domain': [('benefit_id', '=', self.id)],
            'context': {'default_benefit_id': self.id},
        }
    
    def action_view_active_members(self):
        """View members who have this benefit active"""
        self.ensure_one()
        
        # Get unique partner IDs from active memberships and subscriptions
        active_memberships = self.membership_ids.filtered(lambda m: m.state == 'active')
        active_subscriptions = self.subscription_ids.filtered(lambda s: s.state == 'active')
        
        partner_ids = set()
        partner_ids.update(active_memberships.mapped('partner_id.id'))
        partner_ids.update(active_subscriptions.mapped('partner_id.id'))
        
        return {
            'name': _('Active Members: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', list(partner_ids))],
            'context': {'search_default_is_member': 1}
        }
    
    def action_view_chapter_members(self):
        """View chapter members who have this benefit active"""
        self.ensure_one()
        
        # Get unique partner IDs from active chapter memberships only
        chapter_memberships = self.membership_ids.filtered(
            lambda m: m.state == 'active' and m.is_chapter_membership
        )
        
        partner_ids = list(set(chapter_memberships.mapped('partner_id.id')))
        
        return {
            'name': _('Active Chapter Members: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', partner_ids)],
            'context': {'search_default_is_member': 1}
        }
    
    def action_record_usage(self):
        """Record usage of this benefit (wizard/form method)"""
        self.ensure_one()
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Benefit Usage'),
            'res_model': 'ams.benefit.usage',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_benefit_id': self.id,
                'default_usage_date': fields.Datetime.now(),
                'default_quantity': 1,
            }
        }
    
    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for benefit in self:
            if benefit.discount_percentage < 0 or benefit.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100"))
    
    @api.constrains('quantity_limit')
    def _check_quantity_limit(self):
        for benefit in self:
            if benefit.is_quantifiable and benefit.quantity_limit <= 0:
                raise ValidationError(_("Quantity limit must be greater than 0 when benefit is quantifiable"))
    
    @api.constrains('applies_to', 'chapter_access_level_required')
    def _check_chapter_settings(self):
        for benefit in self:
            if (benefit.chapter_access_level_required and 
                benefit.applies_to not in ['chapter', 'membership_and_chapter', 'all']):
                raise ValidationError(_("Chapter access level can only be set for benefits that apply to chapters"))


class AMSBenefitUsage(models.Model):
    _name = 'ams.benefit.usage'
    _description = 'Benefit Usage Log'
    _order = 'usage_date desc'
    
    benefit_id = fields.Many2one('ams.benefit', 'Benefit', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Member/Subscriber', required=True)
    quantity = fields.Integer('Quantity Used', default=1, required=True)
    usage_date = fields.Datetime('Usage Date', default=fields.Datetime.now, required=True)
    notes = fields.Text('Notes')
    
    # Enhanced relations for chapter context
    membership_id = fields.Many2one('ams.membership', 'Related Membership',
                                   help='Membership context for this usage')
    is_chapter_usage = fields.Boolean('Chapter Usage', 
                                     compute='_compute_is_chapter_usage', store=True)
    
    # Optional reference to related records
    sale_order_id = fields.Many2one('sale.order', 'Related Sale Order')
    invoice_id = fields.Many2one('account.move', 'Related Invoice')
    
    @api.depends('membership_id.is_chapter_membership')
    def _compute_is_chapter_usage(self):
        for usage in self:
            usage.is_chapter_usage = bool(usage.membership_id and usage.membership_id.is_chapter_membership)
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for usage in self:
            if usage.quantity <= 0:
                raise ValidationError(_("Usage quantity must be greater than 0"))


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Enhanced Benefit Configuration for Chapter Support
    benefit_ids = fields.Many2many('ams.benefit', 'product_benefit_rel',
                                  'product_id', 'benefit_id',
                                  string='Included Benefits',
                                  help='Benefits automatically granted with this product')
    
    # Chapter-Specific Benefits
    chapter_specific_benefits = fields.Many2many('ams.benefit', 'product_chapter_benefit_rel',
                                                'product_id', 'benefit_id',
                                                string='Chapter-Specific Benefits',
                                                domain=[('applies_to', 'in', ['chapter', 'membership_and_chapter', 'all'])],
                                                help='Additional benefits for chapter memberships only')
    
    def action_configure_benefits(self):
        """Open benefit configuration wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Benefits'),
            'res_model': 'product.benefit.config.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_is_chapter_product': self.subscription_product_type == 'chapter'
            },
        }