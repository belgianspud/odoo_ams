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
    
    # Benefit Configuration
    benefit_type = fields.Selection([
        ('access', 'Access/Permission'),
        ('discount', 'Discount/Pricing'),
        ('content', 'Content Access'),
        ('service', 'Service/Support'),
        ('physical', 'Physical Item'),
        ('digital', 'Digital Resource'),
        ('event', 'Event Access'),
        ('networking', 'Networking'),
        ('other', 'Other'),
    ], string='Benefit Type', required=True, default='access')
    
    # Applicability
    applies_to = fields.Selection([
        ('membership', 'Memberships Only'),
        ('subscription', 'Subscriptions Only'),
        ('both', 'Both Memberships & Subscriptions'),
    ], string='Applies To', default='both', required=True)
    
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
    
    # Access Control (for access-type benefits)
    portal_access_group_ids = fields.Many2many('res.groups', 
                                              relation='benefit_portal_group_rel',
                                              string='Portal Access Groups',
                                              help='Portal groups granted by this benefit')
    website_access_pages = fields.Text('Website Access Pages',
                                      help='Website pages/sections accessible with this benefit')
    
    # Content Access (for content-type benefits)
    content_categories = fields.Text('Content Categories',
                                    help='Categories of content accessible with this benefit')
    digital_resources = fields.Text('Digital Resources',
                                   help='Digital resources included with this benefit')
    
    # Event Access (for event-type benefits)
    event_access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('premium', 'Premium Access'),
        ('vip', 'VIP Access'),
        ('speaker', 'Speaker Access'),
    ], string='Event Access Level', default='basic')
    early_bird_access = fields.Boolean('Early Bird Registration',
                                      help='Access to early bird event registration')
    
    # Physical Benefits
    shipping_required = fields.Boolean('Requires Shipping',
                                      help='This benefit requires physical shipping')
    shipping_frequency = fields.Selection([
        ('once', 'One Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], string='Shipping Frequency', default='once')
    
    # Automation Settings
    auto_apply = fields.Boolean('Auto Apply',
                               help='Automatically apply this benefit when conditions are met')
    requires_approval = fields.Boolean('Requires Approval',
                                      help='Manual approval required before granting this benefit')
    
    # Tracking and Analytics
    usage_count = fields.Integer('Total Usage Count', readonly=True, default=0)
    member_count = fields.Integer('Active Members with Benefit', 
                                 compute='_compute_member_count', store=True)
    
    # Related Records
    membership_ids = fields.Many2many('ams.membership', 'membership_benefit_rel',
                                     'benefit_id', 'membership_id', 
                                     string='Active Memberships')
    subscription_ids = fields.Many2many('ams.subscription', 'subscription_benefit_rel',
                                       'benefit_id', 'subscription_id',
                                       string='Active Subscriptions')
    
    # Usage Tracking
    usage_log_ids = fields.One2many('ams.benefit.usage', 'benefit_id', 'Usage Log')
    
    @api.depends('membership_ids', 'subscription_ids')
    def _compute_member_count(self):
        for benefit in self:
            active_memberships = benefit.membership_ids.filtered(lambda m: m.state == 'active')
            active_subscriptions = benefit.subscription_ids.filtered(lambda s: s.state == 'active')
            
            unique_partners = set()
            unique_partners.update(active_memberships.mapped('partner_id.id'))
            unique_partners.update(active_subscriptions.mapped('partner_id.id'))
            
            benefit.member_count = len(unique_partners)
    
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
    
    def record_usage(self, partner_id, quantity=1, notes=None):
        """Record usage of this benefit"""
        self.ensure_one()
        
        # Check if usage is allowed
        can_use, remaining = self.check_usage_limit(partner_id)
        if not can_use:
            raise ValidationError(_("Usage limit exceeded for benefit: %s") % self.name)
        
        # Create usage record
        usage = self.env['ams.benefit.usage'].create({
            'benefit_id': self.id,
            'partner_id': partner_id,
            'quantity': quantity,
            'usage_date': fields.Datetime.now(),
            'notes': notes or '',
        })
        
        # Update usage count
        self.usage_count += quantity
        
        return usage
    
    def apply_to_partner(self, partner_id):
        """Apply this benefit to a partner"""
        self.ensure_one()
        
        partner = self.env['res.partner'].browse(partner_id)
        
        # Add portal groups if specified
        if self.portal_access_group_ids and partner.portal_user_id:
            partner.portal_user_id.groups_id = [(4, group.id) for group in self.portal_access_group_ids]
        
        # Log the benefit application
        partner.message_post(
            body=_("Benefit applied: %s") % self.name,
            message_type='notification'
        )
    
    def remove_from_partner(self, partner_id):
        """Remove this benefit from a partner"""
        self.ensure_one()
        
        partner = self.env['res.partner'].browse(partner_id)
        
        # Remove portal groups if specified
        if self.portal_access_group_ids and partner.portal_user_id:
            partner.portal_user_id.groups_id = [(3, group.id) for group in self.portal_access_group_ids]
        
        # Log the benefit removal
        partner.message_post(
            body=_("Benefit removed: %s") % self.name,
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


    def record_usage(self):
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

class AMSBenefitUsage(models.Model):
    _name = 'ams.benefit.usage'
    _description = 'Benefit Usage Log'
    _order = 'usage_date desc'
    
    benefit_id = fields.Many2one('ams.benefit', 'Benefit', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Member/Subscriber', required=True)
    quantity = fields.Integer('Quantity Used', default=1, required=True)
    usage_date = fields.Datetime('Usage Date', default=fields.Datetime.now, required=True)
    notes = fields.Text('Notes')
    
    # Optional reference to related records
    sale_order_id = fields.Many2one('sale.order', 'Related Sale Order')
    invoice_id = fields.Many2one('account.move', 'Related Invoice')
    
    @api.constrains('quantity')
    def _check_quantity(self):
        for usage in self:
            if usage.quantity <= 0:
                raise ValidationError(_("Usage quantity must be greater than 0"))


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Benefit Configuration for Subscription Products
    benefit_ids = fields.Many2many('ams.benefit', 'product_benefit_rel',
                                  'product_id', 'benefit_id',
                                  string='Included Benefits',
                                  help='Benefits automatically granted with this product')
    
    def action_configure_benefits(self):
        """Open benefit configuration wizard"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure Benefits'),
            'res_model': 'product.benefit.config.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.id},
        }