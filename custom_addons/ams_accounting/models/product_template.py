from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Enhanced product template with AMS-specific accounting features
    """
    _inherit = 'product.template'
    
    # AMS Product Classification
    is_ams_product = fields.Boolean('AMS Product', default=False,
        help="Mark this product as AMS-specific")
    
    ams_product_type = fields.Selection([
        ('membership', 'Membership'),
        ('subscription', 'Subscription'),
        ('chapter_fee', 'Chapter Fee'),
        ('publication', 'Publication'),
        ('event_ticket', 'Event Ticket'),
        ('donation', 'Donation'),
        ('merchandise', 'Merchandise'),
        ('service', 'Service'),
        ('training', 'Training/Education'),
        ('certification', 'Certification')
    ], string='AMS Product Type',
    help="Classification for AMS-specific products")
    
    # Enhanced Subscription Features
    is_subscription_product = fields.Boolean('Subscription Product', default=False)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type')
    
    # Recurring Configuration
    is_recurring = fields.Boolean('Recurring Product', default=False)
    recurring_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Period')
    ], string='Recurring Period', default='yearly')
    
    custom_period_months = fields.Integer('Custom Period (Months)', default=12,
        help="Number of months for custom recurring period")
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('proportional', 'Proportional Over Period')
    ], string='Revenue Recognition', default='immediate',
    help="How revenue should be recognized for this product")
    
    deferred_revenue_account_id = fields.Many2one('account.account', 'Deferred Revenue Account',
        domain="[('account_type', '=', 'liability_current')]",
        help="Account for deferred revenue recognition")
    
    # Chapter Integration
    chapter_specific = fields.Boolean('Chapter Specific', default=False,
        help="This product is specific to certain chapters")
    
    allowed_chapter_ids = fields.Many2many('ams.chapter', 'product_chapter_rel',
                                          'product_id', 'chapter_id', 'Allowed Chapters',
                                          help="Chapters that can use this product")
    
    chapter_allocation_percentage = fields.Float('Chapter Allocation %', default=0.0,
        help="Percentage of revenue to allocate to chapter")
    
    # Membership Features
    creates_membership = fields.Boolean('Creates Membership', default=False,
        help="Purchasing this product creates or renews membership")
    
    membership_duration_months = fields.Integer('Membership Duration (Months)', default=12)
    
    auto_create_chapters = fields.Boolean('Auto Create Chapter Subscriptions', default=False,
        help="Automatically create chapter subscriptions with membership")
    
    default_chapter_ids = fields.Many2many('ams.chapter', 'product_default_chapter_rel',
                                          'product_id', 'chapter_id', 'Default Chapters',
                                          help="Default chapters to add with membership")
    
    # Pricing and Discounts
    member_price = fields.Float('Member Price',
        help="Special price for AMS members")
    
    early_bird_price = fields.Float('Early Bird Price',
        help="Early registration price")
    
    early_bird_deadline = fields.Date('Early Bird Deadline')
    
    volume_discount_rules = fields.One2many('ams.product.volume.discount', 'product_id', 'Volume Discounts')
    
    # Taxation
    member_tax_exempt = fields.Boolean('Member Tax Exempt', default=False,
        help="Tax exempt for AMS members")
    
    donation_tax_deductible = fields.Boolean('Tax Deductible Donation', default=False,
        help="This donation is tax deductible")
    
    # Analytics and Tracking
    subscription_count = fields.Integer('Subscription Count', compute='_compute_subscription_analytics')
    active_subscription_count = fields.Integer('Active Subscriptions', compute='_compute_subscription_analytics')
    total_subscription_revenue = fields.Float('Total Subscription Revenue', compute='_compute_subscription_analytics')
    
    # E-commerce Settings
    website_published = fields.Boolean('Published on Website', default=False)
    portal_access_required = fields.Boolean('Portal Access Required', default=False,
        help="Require member portal login to purchase")
    
    # Inventory and Fulfillment
    requires_shipping = fields.Boolean('Requires Shipping', default=False)
    digital_delivery = fields.Boolean('Digital Delivery', default=False)
    fulfillment_method = fields.Selection([
        ('automatic', 'Automatic'),
        ('manual', 'Manual Processing'),
        ('email', 'Email Delivery'),
        ('download', 'Download Link'),
        ('shipping', 'Physical Shipping')
    ], string='Fulfillment Method', default='automatic')
    
    # Communication Templates
    purchase_email_template_id = fields.Many2one('mail.template', 'Purchase Email Template',
        domain="[('model', '=', 'account.move')]")
    
    welcome_email_template_id = fields.Many2one('mail.template', 'Welcome Email Template',
        domain="[('model', '=', 'res.partner')]")
    
    @api.depends('product_variant_ids')
    def _compute_subscription_analytics(self):
        for template in self:
            subscription_count = 0
            active_count = 0
            total_revenue = 0.0
            
            for variant in template.product_variant_ids:
                subscriptions = self.env['ams.subscription'].search([
                    ('product_id', '=', variant.id)
                ])
                
                subscription_count += len(subscriptions)
                active_count += len(subscriptions.filtered(lambda s: s.state == 'active'))
                total_revenue += sum(subscriptions.mapped('total_invoiced'))
            
            template.subscription_count = subscription_count
            template.active_subscription_count = active_count
            template.total_subscription_revenue = total_revenue
    
    @api.onchange('is_ams_product')
    def _onchange_is_ams_product(self):
        """Set defaults when marking as AMS product"""
        if self.is_ams_product:
            self.detailed_type = 'service'
            if not self.ams_product_type:
                self.ams_product_type = 'service'
    
    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Set defaults based on AMS product type"""
        if self.ams_product_type == 'membership':
            self.is_subscription_product = True
            self.creates_membership = True
            self.is_recurring = True
            self.revenue_recognition_method = 'proportional'
        elif self.ams_product_type == 'subscription':
            self.is_subscription_product = True
            self.is_recurring = True
            self.revenue_recognition_method = 'proportional'
        elif self.ams_product_type == 'chapter_fee':
            self.chapter_specific = True
            self.revenue_recognition_method = 'immediate'
        elif self.ams_product_type == 'donation':
            self.donation_tax_deductible = True
            self.revenue_recognition_method = 'immediate'
        elif self.ams_product_type == 'event_ticket':
            self.revenue_recognition_method = 'deferred'
        elif self.ams_product_type in ['merchandise', 'publication']:
            self.requires_shipping = True
            self.fulfillment_method = 'shipping'
        elif self.ams_product_type in ['training', 'certification']:
            self.digital_delivery = True
            self.fulfillment_method = 'email'
    
    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Set subscription defaults"""
        if self.is_subscription_product:
            self.detailed_type = 'service'
            self.is_recurring = True
            if not self.subscription_type_id:
                # Try to find membership subscription type
                membership_type = self.env['ams.subscription.type'].search([
                    ('code', '=', 'membership')
                ], limit=1)
                if membership_type:
                    self.subscription_type_id = membership_type.id
    
    @api.onchange('creates_membership')
    def _onchange_creates_membership(self):
        """Set membership defaults"""
        if self.creates_membership:
            self.ams_product_type = 'membership'
            self.is_subscription_product = True
            self.auto_create_chapters = True
    
    @api.onchange('member_price', 'list_price')
    def _onchange_member_pricing(self):
        """Validate member pricing"""
        if self.member_price and self.member_price > self.list_price:
            return {
                'warning': {
                    'title': _('Member Price Warning'),
                    'message': _('Member price is higher than regular price.')
                }
            }
    
    def get_effective_price(self, partner=None, quantity=1, date=None):
        """Get effective price based on member status, early bird, volume discounts"""
        price = self.list_price
        
        if not date:
            date = fields.Date.today()
        
        # Early bird pricing
        if self.early_bird_price and self.early_bird_deadline and date <= self.early_bird_deadline:
            price = min(price, self.early_bird_price)
        
        # Member pricing
        if partner and self.member_price:
            if hasattr(partner, 'active_subscription_count') and partner.active_subscription_count > 0:
                price = min(price, self.member_price)
        
        # Volume discounts
        if quantity > 1 and self.volume_discount_rules:
            applicable_rule = self.volume_discount_rules.filtered(
                lambda r: r.min_quantity <= quantity
            ).sorted('min_quantity', reverse=True)
            
            if applicable_rule:
                rule = applicable_rule[0]
                if rule.discount_type == 'percentage':
                    price = price * (1 - rule.discount_value / 100)
                else:
                    price = max(0, price - rule.discount_value)
        
        return price
    
    def get_applicable_taxes(self, partner=None):
        """Get applicable taxes based on member status and product settings"""
        taxes = self.taxes_id
        
        if partner and self.member_tax_exempt:
            if hasattr(partner, 'active_subscription_count') and partner.active_subscription_count > 0:
                # Remove taxes for members if product is member tax exempt
                taxes = self.env['account.tax']
        
        return taxes
    
    def create_subscription_from_sale(self, sale_line):
        """Create subscription when product is sold"""
        if not self.is_subscription_product:
            return False
        
        # Calculate subscription period
        start_date = fields.Date.today()
        
        if self.recurring_period == 'monthly':
            end_date = start_date + relativedelta(months=1)
        elif self.recurring_period == 'quarterly':
            end_date = start_date + relativedelta(months=3)
        elif self.recurring_period == 'yearly':
            end_date = start_date + relativedelta(years=1)
        elif self.recurring_period == 'custom':
            end_date = start_date + relativedelta(months=self.custom_period_months)
        else:
            end_date = start_date + relativedelta(years=1)
        
        subscription_vals = {
            'partner_id': sale_line.order_id.partner_id.id,
            'subscription_type_id': self.subscription_type_id.id,
            'product_id': sale_line.product_id.id,
            'name': f"{self.name} - {sale_line.order_id.partner_id.name}",
            'sale_order_line_id': sale_line.id,
            'amount': sale_line.price_unit,
            'start_date': start_date,
            'end_date': end_date,
            'is_recurring': self.is_recurring,
            'recurring_period': self.recurring_period,
            'auto_renewal': True,
            'next_renewal_date': end_date,
            'state': 'active',
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        # Auto-create chapter subscriptions if enabled
        if self.auto_create_chapters and self.default_chapter_ids and self.creates_membership:
            subscription._create_chapter_subscriptions(self.default_chapter_ids)
        
        return subscription
    
    def action_view_subscriptions(self):
        """View subscriptions created from this product"""
        subscriptions = self.env['ams.subscription'].search([
            ('product_id', 'in', self.product_variant_ids.ids)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', subscriptions.ids)],
            'context': {'default_product_id': self.product_variant_id.id}
        }
    
    def action_create_subscription(self):
        """Create subscription manually from product"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Subscription',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'context': {
                'default_subscription_type_id': self.subscription_type_id.id,
                'default_product_id': self.product_variant_id.id,
                'default_amount': self.list_price,
                'default_is_recurring': self.is_recurring,
                'default_recurring_period': self.recurring_period,
            }
        }
    
    def action_setup_volume_discounts(self):
        """Setup volume discount rules"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Volume Discount Rules',
            'res_model': 'ams.product.volume.discount',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }
    
    @api.constrains('member_price', 'list_price')
    def _check_member_price(self):
        """Validate member price"""
        for product in self:
            if product.member_price < 0:
                raise ValidationError(_('Member price cannot be negative.'))
    
    @api.constrains('chapter_allocation_percentage')
    def _check_chapter_allocation(self):
        """Validate chapter allocation percentage"""
        for product in self:
            if product.chapter_allocation_percentage < 0 or product.chapter_allocation_percentage > 100:
                raise ValidationError(_('Chapter allocation percentage must be between 0 and 100.'))
    
    @api.constrains('custom_period_months')
    def _check_custom_period(self):
        """Validate custom period"""
        for product in self:
            if product.recurring_period == 'custom' and product.custom_period_months <= 0:
                raise ValidationError(_('Custom period must be greater than 0 months.'))


class AMSProductVolumeDiscount(models.Model):
    """
    Volume discount rules for AMS products
    """
    _name = 'ams.product.volume.discount'
    _description = 'AMS Product Volume Discount'
    _order = 'product_id, min_quantity'
    
    product_id = fields.Many2one('product.template', 'Product', required=True, ondelete='cascade')
    
    min_quantity = fields.Integer('Minimum Quantity', required=True, default=1)
    max_quantity = fields.Integer('Maximum Quantity',
        help="Leave blank for no upper limit")
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type', required=True, default='percentage')
    
    discount_value = fields.Float('Discount Value', required=True)
    
    description = fields.Char('Description')
    
    # Date Restrictions
    valid_from = fields.Date('Valid From')
    valid_to = fields.Date('Valid To')
    
    # Member Restrictions
    members_only = fields.Boolean('Members Only', default=False)
    
    def name_get(self):
        result = []
        for discount in self:
            if discount.discount_type == 'percentage':
                discount_text = f"{discount.discount_value}%"
            else:
                discount_text = f"${discount.discount_value}"
            
            name = f"{discount.min_quantity}+ units: {discount_text} off"
            result.append((discount.id, name))
        return result
    
    @api.constrains('min_quantity', 'max_quantity')
    def _check_quantities(self):
        """Validate quantity ranges"""
        for discount in self:
            if discount.min_quantity <= 0:
                raise ValidationError(_('Minimum quantity must be greater than 0.'))
            
            if discount.max_quantity and discount.max_quantity < discount.min_quantity:
                raise ValidationError(_('Maximum quantity must be greater than minimum quantity.'))
    
    @api.constrains('discount_value')
    def _check_discount_value(self):
        """Validate discount value"""
        for discount in self:
            if discount.discount_value <= 0:
                raise ValidationError(_('Discount value must be greater than 0.'))
            
            if discount.discount_type == 'percentage' and discount.discount_value > 100:
                raise ValidationError(_('Percentage discount cannot exceed 100%.'))


class ProductProduct(models.Model):
    """
    Enhanced product variant with AMS features
    """
    _inherit = 'product.product'
    
    # Subscription tracking
    subscription_ids = fields.One2many('ams.subscription', 'product_id', 'Related Subscriptions')
    
    def get_subscription_analytics(self):
        """Get subscription analytics for this product variant"""
        subscriptions = self.subscription_ids
        
        return {
            'total_subscriptions': len(subscriptions),
            'active_subscriptions': len(subscriptions.filtered(lambda s: s.state == 'active')),
            'total_revenue': sum(subscriptions.mapped('total_invoiced')),
            'monthly_recurring_revenue': sum(subscriptions.filtered(lambda s: s.state == 'active').mapped('monthly_recurring_revenue')),
            'average_subscription_value': sum(subscriptions.mapped('amount')) / len(subscriptions) if subscriptions else 0,
        }