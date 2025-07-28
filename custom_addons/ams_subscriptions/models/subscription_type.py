from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionType(models.Model):
    _name = 'ams.subscription.type'
    _description = 'AMS Subscription Type Configuration'
    _order = 'sequence, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Type Name', 
        required=True, 
        tracking=True,
        help="Name of the subscription type (e.g., Premium Membership, Chapter Access)"
    )
    
    code = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string='Type Code', required=True, tracking=True,
       help="Classification code for this subscription type")
    
    sequence = fields.Integer(
        string='Sequence', 
        default=10,
        help="Order in which subscription types are displayed"
    )
    
    active = fields.Boolean(
        string='Active', 
        default=True, 
        tracking=True,
        help="Whether this subscription type is currently available"
    )
    
    description = fields.Html(
        string='Description',
        help="Detailed description of this subscription type and its benefits"
    )
    
    short_description = fields.Char(
        string='Short Description',
        help="Brief description for display in lists and cards"
    )
    
    # Product Integration
    is_product = fields.Boolean(
        string='Is Product', 
        default=True,
        tracking=True,
        help="Whether this subscription type can be sold as a product"
    )
    
    auto_create_product = fields.Boolean(
        string='Auto Create Product', 
        default=True,
        help="Automatically create a product template for this subscription type"
    )
    
    product_template_id = fields.Many2one(
        'product.template',
        string='Related Product Template',
        help="Product template associated with this subscription type"
    )
    
    default_price = fields.Monetary(
        string='Default Price',
        currency_field='currency_id',
        help="Default price for this subscription type"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Invoicing and Billing Configuration
    creates_invoice = fields.Boolean(
        string='Creates Invoice', 
        default=True,
        tracking=True,
        help="Whether subscriptions of this type automatically create invoices"
    )
    
    invoice_policy = fields.Selection([
        ('immediate', 'Immediate'),
        ('monthly', 'Monthly Billing'),
        ('quarterly', 'Quarterly Billing'),
        ('yearly', 'Yearly Billing')
    ], string='Invoice Policy', default='immediate',
       help="When to create invoices for this subscription type")
    
    # Hierarchy and Relationship Configuration
    can_have_children = fields.Boolean(
        string='Can Have Children', 
        default=False,
        help="Whether subscriptions of this type can have child subscriptions"
    )
    
    requires_parent = fields.Boolean(
        string='Requires Parent Subscription', 
        default=False,
        help="Whether subscriptions of this type require a parent subscription"
    )
    
    parent_type_ids = fields.Many2many(
        'ams.subscription.type',
        'subscription_type_parent_rel',
        'child_id', 'parent_id',
        string='Allowed Parent Types',
        help="Subscription types that can be parents of this type"
    )
    
    max_child_subscriptions = fields.Integer(
        string='Max Child Subscriptions',
        default=0,
        help="Maximum number of child subscriptions allowed (0 = unlimited)"
    )
    
    # E-commerce and Sales Configuration
    website_published = fields.Boolean(
        string='Published on Website', 
        default=False,
        tracking=True,
        help="Whether this subscription type is available for purchase on the website"
    )
    
    website_sequence = fields.Integer(
        string='Website Sequence',
        default=10,
        help="Display order on website"
    )
    
    website_ribbon_text = fields.Char(
        string='Website Ribbon Text',
        help="Text to display on website ribbon (e.g., 'Popular', 'Best Value')"
    )
    
    pos_available = fields.Boolean(
        string='Available in POS', 
        default=False,
        help="Whether this subscription type is available in Point of Sale"
    )
    
    pos_category_id = fields.Many2one(
        'pos.category',
        string='POS Category',
        help="Category for organizing in POS interface"
    )
    
    # Sales Features
    allow_quantity_selection = fields.Boolean(
        string='Allow Quantity Selection',
        default=False,
        help="Allow customers to select quantity when purchasing"
    )
    
    min_quantity = fields.Integer(
        string='Minimum Quantity',
        default=1,
        help="Minimum quantity that can be purchased"
    )
    
    max_quantity = fields.Integer(
        string='Maximum Quantity',
        default=1,
        help="Maximum quantity that can be purchased (0 = unlimited)"
    )
    
    allow_custom_duration = fields.Boolean(
        string='Allow Custom Duration',
        default=False,
        help="Allow customers to specify custom subscription duration"
    )
    
    default_duration_months = fields.Integer(
        string='Default Duration (Months)',
        default=12,
        help="Default subscription duration in months"
    )
    
    # Renewal Configuration
    default_renewal_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('yearly', 'Yearly')
    ], string='Default Renewal Period', default='yearly',
       help="Default renewal frequency for subscriptions of this type")
    
    auto_renewal_default = fields.Boolean(
        string='Auto Renewal Default',
        default=True,
        help="Whether auto-renewal is enabled by default for this subscription type"
    )
    
    renewal_reminder_days = fields.Integer(
        string='Renewal Reminder Days',
        default=30,
        help="Days before renewal to send reminder emails"
    )
    
    # Lifecycle Management
    grace_period_days = fields.Integer(
        string='Grace Period Days',
        default=30,
        help="Days after expiry before moving to grace status"
    )
    
    suspension_period_days = fields.Integer(
        string='Suspension Period Days',
        default=60,
        help="Days after grace period before suspension"
    )
    
    termination_period_days = fields.Integer(
        string='Termination Period Days',
        default=90,
        help="Days after suspension before termination"
    )
    
    # Type-Specific Configuration
    
    # Membership-specific fields
    membership_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('elite', 'Elite')
    ], string='Membership Tier',
       help="Membership tier level for membership types")
    
    voting_rights = fields.Boolean(
        string='Voting Rights',
        default=True,
        help="Whether members with this subscription have voting rights"
    )
    
    board_eligibility = fields.Boolean(
        string='Board Eligibility',
        default=True,
        help="Whether members are eligible for board positions"
    )
    
    auto_create_chapters = fields.Boolean(
        string='Auto Create Chapters',
        default=False,
        help="Automatically create chapter subscriptions with this membership"
    )
    
    default_chapter_ids = fields.Many2many(
        'ams.chapter',
        'subscription_type_chapter_rel',
        'subscription_type_id', 'chapter_id',
        string='Default Chapters',
        help="Chapters to automatically add with this membership type"
    )
    
    # Chapter-specific fields
    is_regional = fields.Boolean(
        string='Is Regional',
        default=False,
        help="Whether this is a regional chapter subscription"
    )
    
    chapter_scope = fields.Selection([
        ('local', 'Local'),
        ('regional', 'Regional'),
        ('national', 'National'),
        ('international', 'International')
    ], string='Chapter Scope',
       help="Geographic scope of chapter activities")
    
    requires_membership_validation = fields.Boolean(
        string='Requires Membership Validation',
        default=True,
        help="Whether chapter membership requires existing association membership"
    )
    
    chapter_meeting_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Meeting Frequency',
       help="Typical frequency of chapter meetings")
    
    # Publication-specific fields
    publication_format = fields.Selection([
        ('print', 'Print Only'),
        ('digital', 'Digital Only'),
        ('both', 'Print + Digital')
    ], string='Available Formats',
       help="Available formats for publication subscriptions")
    
    issue_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Issue Frequency',
       help="How often publications are issued")
    
    digital_access_only = fields.Boolean(
        string='Digital Access Only',
        default=False,
        help="Whether this subscription only provides digital access"
    )
    
    archive_access_months = fields.Integer(
        string='Archive Access (Months)',
        default=12,
        help="Number of months of archive access included"
    )
    
    # Access and Benefits Configuration
    access_level = fields.Selection([
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access'),
        ('full', 'Full Access')
    ], string='Access Level', default='standard',
       help="Level of access provided by this subscription")
    
    digital_benefits = fields.Text(
        string='Digital Benefits',
        help="List of digital benefits included with this subscription"
    )
    
    physical_benefits = fields.Text(
        string='Physical Benefits',
        help="List of physical benefits included with this subscription"
    )
    
    member_benefits = fields.Html(
        string='Member Benefits',
        help="Detailed description of member benefits for website display"
    )
    
    # Marketing and SEO
    marketing_color = fields.Char(
        string='Marketing Color',
        default='#875A7B',
        help="Color used for marketing materials and website display"
    )
    
    website_meta_title = fields.Char(
        string='Website Meta Title',
        help="SEO meta title for website pages"
    )
    
    website_meta_description = fields.Text(
        string='Website Meta Description',
        help="SEO meta description for website pages"
    )
    
    website_meta_keywords = fields.Char(
        string='Website Meta Keywords',
        help="SEO meta keywords for website pages"
    )
    
    terms_and_conditions = fields.Html(
        string='Terms and Conditions',
        help="Terms and conditions specific to this subscription type"
    )
    
    # Subscription Rules Integration
    subscription_rule_ids = fields.One2many(
        'ams.subscription.rule',
        'subscription_type_id',
        string='Lifecycle Rules',
        help="Rules that apply to subscriptions of this type"
    )
    
    # Statistics and Analytics
    subscription_count = fields.Integer(
        string='Total Subscriptions',
        compute='_compute_subscription_stats',
        store=True,
        help="Total number of subscriptions of this type"
    )
    
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_stats',  
        store=True,
        help="Number of currently active subscriptions"
    )
    
    total_revenue_ytd = fields.Monetary(
        string='Revenue YTD',
        currency_field='currency_id',
        compute='_compute_financial_stats',
        store=True,
        help="Total revenue year-to-date for this subscription type"
    )
    
    renewal_rate_percentage = fields.Float(
        string='Renewal Rate %',
        compute='_compute_performance_stats',
        store=True,
        help="Percentage of subscriptions that renew"
    )
    
    average_subscription_duration = fields.Float(
        string='Avg Duration (Months)',
        compute='_compute_performance_stats',
        store=True,
        help="Average subscription duration in months"
    )
    
    churn_rate_percentage = fields.Float(
        string='Churn Rate %',
        compute='_compute_performance_stats',
        store=True,
        help="Percentage of subscriptions that are cancelled or terminated"
    )
    
    # Computed Statistics
    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_subscription_stats(self):
        """Compute subscription statistics"""
        for sub_type in self:
            subscriptions = self.env['ams.subscription'].search([
                ('subscription_type_id', '=', sub_type.id)
            ])
            sub_type.subscription_count = len(subscriptions)
            sub_type.active_subscription_count = len(
                subscriptions.filtered(lambda s: s.state == 'active')
            )
    
    @api.depends('subscription_ids', 'subscription_ids.amount', 'subscription_ids.state')
    def _compute_financial_stats(self):
        """Compute financial statistics"""
        current_year = fields.Date.today().year
        for sub_type in self:
            # Get subscriptions created this year that are active
            subscriptions = self.env['ams.subscription'].search([
                ('subscription_type_id', '=', sub_type.id),
                ('state', '=', 'active'),
                ('create_date', '>=', f'{current_year}-01-01'),
                ('create_date', '<=', f'{current_year}-12-31'),
            ])
            sub_type.total_revenue_ytd = sum(subscriptions.mapped('amount'))
    
    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.start_date', 'subscription_ids.end_date')
    def _compute_performance_stats(self):
        """Compute performance statistics"""
        for sub_type in self:
            subscriptions = self.env['ams.subscription'].search([
                ('subscription_type_id', '=', sub_type.id)
            ])
            
            if not subscriptions:
                sub_type.renewal_rate_percentage = 0.0
                sub_type.average_subscription_duration = 0.0
                sub_type.churn_rate_percentage = 0.0
                continue
            
            # Renewal rate calculation
            renewable_subs = subscriptions.filtered('is_recurring')
            if renewable_subs:
                renewed_count = len(renewable_subs.filtered(lambda s: s.last_renewal_date))
                sub_type.renewal_rate_percentage = (renewed_count / len(renewable_subs)) * 100
            else:
                sub_type.renewal_rate_percentage = 0.0
            
            # Average duration calculation
            ended_subs = subscriptions.filtered(lambda s: s.end_date and s.start_date)
            if ended_subs:
                total_days = sum([
                    (sub.end_date - sub.start_date).days for sub in ended_subs
                ])
                sub_type.average_subscription_duration = (total_days / len(ended_subs)) / 30.44  # Convert to months
            else:
                sub_type.average_subscription_duration = 0.0
            
            # Churn rate calculation
            churned_subs = subscriptions.filtered(lambda s: s.state in ('cancelled', 'terminated'))
            sub_type.churn_rate_percentage = (len(churned_subs) / len(subscriptions)) * 100

    # Reverse relationship to subscriptions
    subscription_ids = fields.One2many(
        'ams.subscription',
        'subscription_type_id',
        string='Subscriptions',
        help="All subscriptions of this type"
    )

    # Model Creation and Management
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle product creation and defaults"""
        subscription_types = super().create(vals_list)
        
        for subscription_type in subscription_types:
            # Auto-create product if enabled
            if subscription_type.auto_create_product and subscription_type.is_product:
                subscription_type._create_related_product()
            
            # Set up default rules if none exist
            subscription_type._create_default_rules()
        
        return subscription_types

    def _create_related_product(self):
        """Create related product template for this subscription type"""
        self.ensure_one()
        
        if self.product_template_id:
            return  # Product already exists
        
        product_vals = {
            'name': self.name,
            'type': 'service',
            'categ_id': self.env.ref('product.product_category_all').id,
            'list_price': self.default_price or 0.0,
            'standard_price': 0.0,
            'description_sale': self.short_description or self.name,
            'description': self.description,
            'is_subscription_product': True,
            'subscription_type_id': self.id,
            'website_published': self.website_published,
            'available_in_pos': self.pos_available,
            'pos_categ_id': self.pos_category_id.id if self.pos_category_id else False,
        }
        
        # Add subscription-specific settings to product
        if hasattr(self.env['product.template'], 'is_recurring'):
            product_vals.update({
                'is_recurring': True,
                'recurring_period': self.default_renewal_period,
                'auto_renewal': self.auto_renewal_default,
                'grace_period_days': self.grace_period_days,
            })
        
        product_template = self.env['product.template'].create(product_vals)
        self.product_template_id = product_template.id
        
        _logger.info(f"Created product template for subscription type: {self.name}")

    def _create_default_rules(self):
        """Create default lifecycle rules for this subscription type"""
        self.ensure_one()
        
        # Only create rules if none exist
        if self.subscription_rule_ids:
            return
        
        rule_vals_list = []
        
        # Grace period rule
        if self.grace_period_days > 0:
            rule_vals_list.append({
                'name': f'{self.name} - Grace Period',
                'subscription_type_id': self.id,
                'rule_type': 'grace_period',
                'trigger_days': self.grace_period_days,
                'action': 'status_change',
                'target_status': 'grace',
                'active': True,
                'sequence': 10,
            })
        
        # Suspension rule
        if self.suspension_period_days > 0:
            rule_vals_list.append({
                'name': f'{self.name} - Suspension',
                'subscription_type_id': self.id,
                'rule_type': 'suspend_period',
                'trigger_days': self.suspension_period_days,
                'action': 'status_change',
                'target_status': 'suspended',
                'active': True,
                'sequence': 20,
            })
        
        # Termination rule
        if self.termination_period_days > 0:
            rule_vals_list.append({
                'name': f'{self.name} - Termination',
                'subscription_type_id': self.id,
                'rule_type': 'terminate_period',
                'trigger_days': self.termination_period_days,
                'action': 'status_change',
                'target_status': 'terminated',
                'active': True,
                'sequence': 30,
            })
        
        if rule_vals_list:
            self.env['ams.subscription.rule'].create(rule_vals_list)

    # Business Logic Methods
    def action_create_product(self):
        """Manual action to create related product"""
        self.ensure_one()
        if not self.product_template_id:
            self._create_related_product()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Product Created'),
                    'message': _('Product template has been created successfully.'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Product Exists'),
                    'message': _('Product template already exists for this subscription type.'),
                    'type': 'info',
                }
            }

    def action_view_subscriptions(self):
        """Action to view all subscriptions of this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form,kanban',
            'domain': [('subscription_type_id', '=', self.id)],
            'context': {
                'default_subscription_type_id': self.id,
                'search_default_active': 1,
            }
        }

    def action_view_products(self):
        """Action to view related product"""
        self.ensure_one()
        if self.product_template_id:
            return {
                'type': 'ir.actions.act_window',
                'name': f'{self.name} - Product',
                'res_model': 'product.template',
                'view_mode': 'form',
                'res_id': self.product_template_id.id,
            }

    def action_view_rules(self):
        """Action to view lifecycle rules"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Rules',
            'res_model': 'ams.subscription.rule',
            'view_mode': 'tree,form',
            'domain': [('subscription_type_id', '=', self.id)],
            'context': {'default_subscription_type_id': self.id}
        }

    def action_duplicate_type(self):
        """Action to duplicate this subscription type"""
        self.ensure_one()
        copy_vals = {
            'name': f"{self.name} (Copy)",
            'active': False,  # Start as inactive
            'product_template_id': False,  # Don't copy product link
        }
        new_type = self.copy(copy_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Type'),
            'res_model': 'ams.subscription.type',
            'view_mode': 'form',
            'res_id': new_type.id,
            'target': 'current',
        }

    # Onchange Methods
    @api.onchange('code')
    def _onchange_code(self):
        """Set default values based on subscription type code"""
        if self.code == 'membership':
            self.can_have_children = True
            self.requires_parent = False
            self.is_regional = False
            self.default_renewal_period = 'yearly'
            self.grace_period_days = 30
            self.suspension_period_days = 60
            self.termination_period_days = 90
            
        elif self.code == 'chapter':
            self.can_have_children = False
            self.requires_parent = True
            self.is_regional = True
            self.default_renewal_period = 'yearly'
            self.grace_period_days = 15
            self.suspension_period_days = 30
            self.termination_period_days = 45
            
            # Set allowed parent types to membership
            membership_types = self.search([('code', '=', 'membership')])
            if membership_types:
                self.parent_type_ids = [(6, 0, membership_types.ids)]
                
        elif self.code == 'publication':
            self.can_have_children = False
            self.requires_parent = False
            self.is_regional = False
            self.default_renewal_period = 'yearly'
            self.publication_format = 'both'
            self.issue_frequency = 'monthly'
            self.grace_period_days = 7
            self.suspension_period_days = 14
            self.termination_period_days = 30

    @api.onchange('website_published')
    def _onchange_website_published(self):
        """Update product when website publishing status changes"""
        if self.product_template_id:
            self.product_template_id.website_published = self.website_published

    @api.onchange('pos_available')
    def _onchange_pos_available(self):
        """Update product when POS availability changes"""
        if self.product_template_id:
            self.product_template_id.available_in_pos = self.pos_available

    @api.onchange('default_price')
    def _onchange_default_price(self):
        """Update product price when default price changes"""
        if self.product_template_id and self.default_price:
            self.product_template_id.list_price = self.default_price

    # Validation and Constraints
    @api.constrains('code', 'requires_parent', 'parent_type_ids')
    def _check_parent_requirements(self):
        """Validate parent type requirements"""
        for record in self:
            if record.requires_parent and not record.parent_type_ids:
                raise ValidationError(
                    _("Subscription types that require a parent must specify allowed parent types.")
                )

    @api.constrains('grace_period_days', 'suspension_period_days', 'termination_period_days')
    def _check_lifecycle_periods(self):
        """Validate lifecycle period progression"""
        for record in self:
            if record.grace_period_days < 0:
                raise ValidationError(_("Grace period days cannot be negative"))
            if record.suspension_period_days < 0:
                raise ValidationError(_("Suspension period days cannot be negative"))
            if record.termination_period_days < 0:
                raise ValidationError(_("Termination period days cannot be negative"))
            
            # Ensure logical progression
            if (record.suspension_period_days > 0 and 
                record.grace_period_days > 0 and 
                record.suspension_period_days <= record.grace_period_days):
                raise ValidationError(
                    _("Suspension period must be longer than grace period")
                )
            
            if (record.termination_period_days > 0 and 
                record.suspension_period_days > 0 and 
                record.termination_period_days <= record.suspension_period_days):
                raise ValidationError(
                    _("Termination period must be longer than suspension period")
                )

    @api.constrains('min_quantity', 'max_quantity')
    def _check_quantity_limits(self):
        """Validate quantity limits"""
        for record in self:
            if record.min_quantity < 1:
                raise ValidationError(_("Minimum quantity must be at least 1"))
            if record.max_quantity > 0 and record.max_quantity < record.min_quantity:
                raise ValidationError(_("Maximum quantity cannot be less than minimum quantity"))

    @api.constrains('default_price')
    def _check_default_price(self):
        """Validate default price"""
        for record in self:
            if record.default_price < 0:
                raise ValidationError(_("Default price cannot be negative"))

    @api.constrains('renewal_reminder_days')
    def _check_renewal_reminder_days(self):
        """Validate renewal reminder days"""
        for record in self:
            if record.renewal_reminder_days < 0:
                raise ValidationError(_("Renewal reminder days cannot be negative"))

    # Name and Display Methods
    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code.upper()}] {name}"
            if not record.active:
                name = f"{name} (Archived)"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced name search"""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    # SQL Constraints
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Subscription type name must be unique!'),
        ('code_name_unique', 'UNIQUE(code, name)', 'Combination of code and name must be unique!'),
        ('default_price_positive', 'CHECK(default_price >= 0)', 'Default price must be positive or zero!'),
        ('grace_period_positive', 'CHECK(grace_period_days >= 0)', 'Grace period days must be positive or zero!'),
        ('sequence_positive', 'CHECK(sequence >= 0)', 'Sequence must be positive or zero!'),
    ]