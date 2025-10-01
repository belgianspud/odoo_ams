# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class MembershipRecord(models.Model):
    _name = 'membership.record'
    _description = 'Membership Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    # ==========================================
    # CORE IDENTITY
    # ==========================================
    
    name = fields.Char(
        string='Membership Number',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        tracking=True,
        ondelete='restrict'
    )
    
    # ==========================================
    # SUBSCRIPTION INTEGRATION
    # Link to subscription_management for billing/renewal
    # ==========================================
    
    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Subscription',
        help='Links to subscription for billing and renewal management',
        ondelete='restrict',
        tracking=True
    )
    
    # Delegate key fields from subscription
    product_id = fields.Many2one(
        'product.template',
        string='Membership Product',
        compute='_compute_from_subscription',
        store=True,
        readonly=False
    )
    
    start_date = fields.Date(
        string='Start Date',
        compute='_compute_from_subscription',
        store=True,
        readonly=False,
        default=fields.Date.today,
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        compute='_compute_from_subscription',
        store=True,
        readonly=False,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Status',
       compute='_compute_from_subscription',
       store=True,
       readonly=False,
       default='draft',
       tracking=True)
    
    # ==========================================
    # MEMBER-SPECIFIC DATA
    # This is what membership_community adds beyond subscriptions
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Membership Category',
        required=True,
        tracking=True,
        help='Member category (Individual, Student, Corporate, etc.)'
    )
    
    member_type = fields.Selection(
        related='membership_category_id.category_type',
        string='Member Type',
        store=True,
        readonly=True
    )
    
    join_date = fields.Date(
        string='Original Join Date',
        tracking=True,
        help='Date when member first joined (historical tracking)'
    )
    
    membership_year_type = fields.Selection([
        ('calendar', 'Calendar Year'),
        ('anniversary', 'Anniversary Year')
    ], string='Membership Year Type',
       default='anniversary',
       required=True,
       help='Calendar = Jan-Dec, Anniversary = 12 months from start date')
    
    anniversary_month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Anniversary Month',
       compute='_compute_anniversary_month',
       store=True,
       help='Month when anniversary renewal occurs')
    
    # ==========================================
    # SOURCE TRACKING
    # Track how this membership was created
    # ==========================================
    
    source_type = fields.Selection([
        ('direct', 'Direct Signup'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('transfer', 'Transfer'),
        ('organizational_seat', 'Organizational Seat'),
        ('chapter', 'Chapter'),
        ('promotion', 'Promotion'),
        ('import', 'Data Import'),
        ('admin', 'Admin Created')
    ], string='Source Type',
       default='direct',
       tracking=True,
       help='How this membership was created')
    
    source_id = fields.Integer(
        string='Source Record ID',
        help='ID of the source record (e.g., seat ID, previous membership ID)'
    )
    
    source_model = fields.Char(
        string='Source Model',
        help='Model name of source record'
    )
    
    # ==========================================
    # ORGANIZATIONAL HIERARCHY
    # For organizational memberships with seats
    # ==========================================
    
    parent_membership_id = fields.Many2one(
        'membership.record',
        string='Parent Membership',
        tracking=True,
        help='For organizational seats - links to parent org membership'
    )
    
    child_membership_ids = fields.One2many(
        'membership.record',
        'parent_membership_id',
        string='Child Memberships',
        help='For organizational memberships - linked seat memberships'
    )
    
    is_organizational_parent = fields.Boolean(
        string='Is Organizational Parent',
        compute='_compute_organizational_flags',
        store=True
    )
    
    is_organizational_child = fields.Boolean(
        string='Is Organizational Child',
        compute='_compute_organizational_flags',
        store=True
    )
    
    child_membership_count = fields.Integer(
        string='Child Memberships',
        compute='_compute_organizational_flags',
        store=True
    )
    
    # ==========================================
    # FINANCIAL (from subscription)
    # ==========================================
    
    amount = fields.Float(
        string='Membership Fee',
        compute='_compute_from_subscription',
        store=True,
        readonly=False,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # ==========================================
    # RENEWAL (leverages subscription)
    # ==========================================
    
    can_renew = fields.Boolean(
        string='Can Renew',
        compute='_compute_can_renew',
        store=True
    )
    
    renewal_date = fields.Date(
        string='Renewal Date',
        help='Date when renewal becomes available'
    )
    
    renewed_membership_id = fields.Many2one(
        'membership.record',
        string='Renewed To',
        help='The membership this was renewed to'
    )
    
    previous_membership_id = fields.Many2one(
        'membership.record',
        string='Renewed From',
        help='The membership this renewed from'
    )
    
    # ==========================================
    # EXTENSION DATA
    # For professional and organizational modules
    # ==========================================
    
    extension_data = fields.Json(
        string='Extension Data',
        help='JSON field for additional module data without schema changes'
    )
    
    # ==========================================
    # PORTAL ACCESS
    # ==========================================
    
    portal_enabled = fields.Boolean(
        string='Portal Access Enabled',
        default=True,
        help='Whether this member can access the portal'
    )
    
    portal_access_level = fields.Selection([
        ('none', 'No Access'),
        ('basic', 'Basic Access'),
        ('standard', 'Standard Access'),
        ('premium', 'Premium Access'),
        ('admin', 'Organization Admin')
    ], string='Portal Access Level',
       default='standard')
    
    # ==========================================
    # MODULE INTEGRATION FLAGS
    # ==========================================
    
    has_professional_profile = fields.Boolean(
        string='Has Professional Profile',
        compute='_compute_module_flags',
        help='Indicates if professional module features are active'
    )
    
    has_organizational_seat = fields.Boolean(
        string='Has Organizational Seat',
        compute='_compute_module_flags',
        help='Indicates if this is from an organizational seat'
    )
    
    # ==========================================
    # ELIGIBILITY & VERIFICATION
    # ==========================================
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False,
        tracking=True
    )
    
    eligibility_verified_by = fields.Many2one(
        'res.users',
        string='Verified By'
    )
    
    eligibility_verified_date = fields.Date(
        string='Verification Date'
    )
    
    requirements_met = fields.Json(
        string='Requirements Met',
        help='JSON tracking of requirement completion'
    )
    
    # ==========================================
    # NOTES
    # ==========================================
    
    notes = fields.Text(string='Internal Notes')
    
    # ==========================================
    # COMPUTED STATUS FIELDS
    # ==========================================
    
    is_active = fields.Boolean(
        string='Is Active',
        compute='_compute_is_active',
        store=True
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True
    )
    
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('subscription_id', 'subscription_id.product_id', 
                 'subscription_id.date_start', 'subscription_id.date_end',
                 'subscription_id.state', 'subscription_id.recurring_total')
    def _compute_from_subscription(self):
        """Pull key data from linked subscription"""
        for record in self:
            if record.subscription_id:
                record.product_id = record.subscription_id.product_id.product_tmpl_id
                record.start_date = record.subscription_id.date_start
                record.end_date = record.subscription_id.date_end
                record.amount = record.subscription_id.recurring_total
                
                # Map subscription state to membership state
                sub_state = record.subscription_id.state
                if sub_state == 'draft':
                    record.state = 'draft'
                elif sub_state in ['open', 'active']:
                    record.state = 'active'
                elif sub_state == 'pending':
                    record.state = 'pending'
                elif sub_state == 'close':
                    record.state = 'expired'
                elif sub_state == 'cancel':
                    record.state = 'cancelled'
                else:
                    record.state = 'draft'
            else:
                # No subscription linked - keep manual values
                pass

    @api.depends('start_date', 'membership_year_type')
    def _compute_anniversary_month(self):
        """Calculate anniversary month from start date"""
        for record in self:
            if record.membership_year_type == 'anniversary' and record.start_date:
                record.anniversary_month = str(record.start_date.month)
            else:
                record.anniversary_month = False

    @api.depends('child_membership_ids', 'parent_membership_id')
    def _compute_organizational_flags(self):
        """Compute organizational membership flags"""
        for record in self:
            record.is_organizational_parent = bool(record.child_membership_ids)
            record.is_organizational_child = bool(record.parent_membership_id)
            record.child_membership_count = len(record.child_membership_ids)

    def _compute_module_flags(self):
        """Check if additional modules are installed and have data"""
        for record in self:
            # Check professional module
            professional_installed = self.env['ir.module.module'].search([
                ('name', '=', 'membership_professional'),
                ('state', '=', 'installed')
            ], limit=1)
            
            if professional_installed and self.env['ir.model'].search([
                ('model', '=', 'professional.profile')
            ], limit=1):
                record.has_professional_profile = bool(
                    self.env['professional.profile'].search([
                        ('partner_id', '=', record.partner_id.id)
                    ], limit=1)
                )
            else:
                record.has_professional_profile = False
            
            # Check organizational module
            organizational_installed = self.env['ir.module.module'].search([
                ('name', '=', 'membership_organizational'),
                ('state', '=', 'installed')
            ], limit=1)
            
            if organizational_installed and self.env['ir.model'].search([
                ('model', '=', 'membership.seat')
            ], limit=1):
                record.has_organizational_seat = bool(
                    self.env['membership.seat'].search([
                        ('assigned_to_id', '=', record.partner_id.id),
                        ('state', '=', 'assigned')
                    ], limit=1)
                )
            else:
                record.has_organizational_seat = False

    @api.depends('state')
    def _compute_is_active(self):
        """Check if membership is active"""
        for record in self:
            record.is_active = record.state == 'active'

    @api.depends('end_date', 'state')
    def _compute_is_expired(self):
        """Check if membership is expired"""
        today = fields.Date.today()
        for record in self:
            record.is_expired = record.end_date < today if record.end_date else False

    @api.depends('end_date')
    def _compute_days_until_expiry(self):
        """Calculate days until membership expires"""
        today = fields.Date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_until_expiry = delta.days
            else:
                record.days_until_expiry = 0

    @api.depends('end_date', 'state', 'subscription_id.to_renew')
    def _compute_can_renew(self):
        """Determine if membership can be renewed"""
        for record in self:
            if record.subscription_id:
                # Use subscription's renewal logic
                record.can_renew = record.subscription_id.to_renew
            else:
                # Fallback logic
                if record.state in ['active', 'expired']:
                    if record.end_date:
                        days_until = (record.end_date - fields.Date.today()).days
                        record.can_renew = days_until <= 90
                    else:
                        record.can_renew = False
                else:
                    record.can_renew = False

    # ==========================================
    # CRUD METHODS
    # ==========================================

    @api.model
    def create(self, vals):
        """Override create to set sequence and create subscription if needed"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('membership.record') or 'New'
        
        # Set join_date if not provided
        if not vals.get('join_date'):
            vals['join_date'] = vals.get('start_date', fields.Date.today())
        
        # Create subscription if product provided but no subscription
        if vals.get('product_id') and not vals.get('subscription_id'):
            product = self.env['product.template'].browse(vals['product_id'])
            
            # Only create subscription if product has subscription features
            if hasattr(product, 'is_subscription') and product.is_subscription:
                subscription_vals = {
                    'partner_id': vals['partner_id'],
                    'product_id': product.product_variant_id.id,
                    'date_start': vals.get('start_date', fields.Date.today()),
                }
                
                subscription = self.env['subscription.subscription'].create(subscription_vals)
                vals['subscription_id'] = subscription.id
        
        return super(MembershipRecord, self).create(vals)

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def get_extension_data(self, key, default=None):
        """Safely get extension data"""
        self.ensure_one()
        if not self.extension_data:
            return default
        return self.extension_data.get(key, default)

    def set_extension_data(self, key, value):
        """Safely set extension data"""
        self.ensure_one()
        data = self.extension_data or {}
        data[key] = value
        self.extension_data = data

    @api.model
    def create_from_source(self, partner_id, product_id, source_type, 
                          membership_category_id, source_id=None, 
                          source_model=None, **kwargs):
        """
        Create membership with source tracking
        Used by other modules to create memberships
        """
        vals = {
            'partner_id': partner_id,
            'product_id': product_id,
            'membership_category_id': membership_category_id,
            'source_type': source_type,
            'source_id': source_id,
            'source_model': source_model,
            'state': kwargs.pop('state', 'active'),
            'start_date': kwargs.pop('start_date', fields.Date.today()),
        }
        vals.update(kwargs)
        return self.create(vals)

    def action_activate(self):
        """Activate membership and subscription"""
        for record in self:
            if record.subscription_id:
                record.subscription_id.set_open()
            record.state = 'active'
            record.partner_id.is_member = True

    def action_suspend(self):
        """Suspend membership"""
        self.write({'state': 'suspended'})
        # Optionally suspend subscription too
        for record in self:
            if record.subscription_id:
                record.subscription_id.set_close()

    def action_cancel(self):
        """Cancel membership and subscription"""
        for record in self:
            if record.subscription_id:
                record.subscription_id.set_cancel()
            record.state = 'cancelled'

    def action_renew(self):
        """Create renewal membership (uses subscription renewal)"""
        self.ensure_one()
        
        if not self.can_renew:
            raise ValidationError(_("This membership cannot be renewed at this time."))
        
        # If linked to subscription, use subscription renewal
        if self.subscription_id:
            # Trigger subscription renewal
            renewed_sub = self.subscription_id.action_renew()
            
            # Create new membership record linked to renewed subscription
            renewal = self.create({
                'partner_id': self.partner_id.id,
                'product_id': self.product_id.id,
                'membership_category_id': self.membership_category_id.id,
                'subscription_id': renewed_sub.id,
                'source_type': 'renewal',
                'source_id': self.id,
                'source_model': 'membership.record',
                'previous_membership_id': self.id,
                'membership_year_type': self.membership_year_type,
                'portal_access_level': self.portal_access_level,
                'state': 'draft',
            })
        else:
            # Manual renewal without subscription
            new_start = self.end_date + relativedelta(days=1)
            
            if self.membership_year_type == 'calendar':
                # Calendar year: ends Dec 31
                new_end = fields.Date.from_string(f"{new_start.year}-12-31")
            else:
                # Anniversary: 12 months from start
                new_end = new_start + relativedelta(years=1, days=-1)
            
            renewal = self.create({
                'partner_id': self.partner_id.id,
                'product_id': self.product_id.id,
                'membership_category_id': self.membership_category_id.id,
                'start_date': new_start,
                'end_date': new_end,
                'source_type': 'renewal',
                'source_id': self.id,
                'source_model': 'membership.record',
                'previous_membership_id': self.id,
                'membership_year_type': self.membership_year_type,
                'portal_access_level': self.portal_access_level,
                'state': 'draft',
            })
        
        # Link back to this membership
        self.renewed_membership_id = renewal.id
        
        return renewal

    # ==========================================
    # EXTENSION HOOKS
    # ==========================================

    def _get_portal_url(self):
        """Hook for other modules to override portal URL"""
        self.ensure_one()
        if hasattr(self, '_portal_url_override'):
            return self._portal_url_override()
        return f'/my/membership/{self.id}'

    def _compute_feature_access(self):
        """Hook for other modules to add feature flags"""
        self.ensure_one()
        features = {
            'portal_access': self.portal_enabled,
            'portal_level': self.portal_access_level,
        }
        
        # Call hooks from other modules
        for func_name in dir(self):
            if func_name.startswith('_feature_hook_'):
                func = getattr(self, func_name)
                if callable(func):
                    features.update(func())
        
        return features

    def _prepare_portal_values(self):
        """Hook for preparing portal context"""
        self.ensure_one()
        values = {
            'membership': self,
            'partner': self.partner_id,
            'product': self.product_id,
            'subscription': self.subscription_id,
            'can_renew': self.can_renew,
            'is_active': self.is_active,
            'days_until_expiry': self.days_until_expiry,
        }
        
        # Call hooks from other modules
        for func_name in dir(self):
            if func_name.startswith('_portal_values_hook_'):
                func = getattr(self, func_name)
                if callable(func):
                    values.update(func())
        
        return values

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate dates"""
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise ValidationError(_("End date must be after start date."))

    @api.constrains('parent_membership_id')
    def _check_circular_hierarchy(self):
        """Prevent circular parent-child relationships"""
        for record in self:
            if record.parent_membership_id:
                parent = record.parent_membership_id
                visited = set()
                while parent:
                    if parent.id in visited:
                        raise ValidationError(_("Circular parent-child relationship detected."))
                    visited.add(parent.id)
                    parent = parent.parent_membership_id