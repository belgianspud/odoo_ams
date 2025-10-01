# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipFeature(models.Model):
    _name = 'membership.feature'
    _description = 'Membership Feature'
    _order = 'category, sequence, name'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Feature Name',
        required=True,
        translate=True,
        help='Display name for this feature (e.g., "Event Registration Discount", "Journal Access")'
    )
    
    code = fields.Char(
        string='Feature Code',
        required=True,
        help='Unique code for this feature (e.g., EVENT_DISC, JOURNAL_ACCESS)'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive features are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this feature'
    )
    
    icon = fields.Char(
        string='Icon',
        help='Font Awesome icon class (e.g., fa-star, fa-book)'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # FEATURE CLASSIFICATION
    # ==========================================
    
    category = fields.Selection([
        ('access', 'Access Rights'),
        ('discount', 'Discounts'),
        ('publication', 'Publications'),
        ('event', 'Events'),
        ('professional', 'Professional Services'),
        ('networking', 'Networking'),
        ('education', 'Education & Training'),
        ('certification', 'Certification'),
        ('portal', 'Portal Features'),
        ('directory', 'Directory'),
        ('other', 'Other')
    ], string='Feature Category',
       required=True,
       default='other',
       help='Type of benefit this feature provides')
    
    feature_type = fields.Selection([
        ('boolean', 'Yes/No'),
        ('quantity', 'Quantity'),
        ('percentage', 'Percentage'),
        ('amount', 'Amount'),
        ('text', 'Text Value'),
        ('unlimited', 'Unlimited')
    ], string='Feature Type',
       default='boolean',
       required=True,
       help='How this feature is quantified')
    
    is_premium_feature = fields.Boolean(
        string='Premium Feature',
        default=False,
        help='This is a premium feature for higher-tier memberships'
    )
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Member must verify eligibility to use this feature'
    )

    # ==========================================
    # FEATURE VALUE CONFIGURATION
    # ==========================================
    
    default_value = fields.Char(
        string='Default Value',
        help='Default value for this feature (format depends on feature_type)'
    )
    
    value_uom = fields.Char(
        string='Unit of Measure',
        help='Unit for quantity features (e.g., "credits", "downloads", "attendees")'
    )
    
    min_value = fields.Float(
        string='Minimum Value',
        default=0.0,
        help='Minimum allowed value (for quantity/percentage/amount types)'
    )
    
    max_value = fields.Float(
        string='Maximum Value',
        default=0.0,
        help='Maximum allowed value (0 = unlimited, for quantity types)'
    )

    # ==========================================
    # DISCOUNT FEATURES
    # (when category = 'discount')
    # ==========================================
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('early_bird', 'Early Bird'),
        ('member_only', 'Member-Only Pricing')
    ], string='Discount Type',
       help='Type of discount provided')
    
    applies_to = fields.Selection([
        ('events', 'Event Registrations'),
        ('products', 'Product Purchases'),
        ('publications', 'Publications'),
        ('certifications', 'Certifications'),
        ('all', 'All Purchases')
    ], string='Applies To',
       help='What this discount applies to')
    
    discount_percentage = fields.Float(
        string='Discount %',
        default=0.0,
        help='Discount percentage (if discount_type = percentage)'
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        default=0.0,
        help='Fixed discount amount (if discount_type = fixed)'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # ==========================================
    # ACCESS FEATURES
    # (when category = 'access')
    # ==========================================
    
    grants_portal_access = fields.Boolean(
        string='Grants Portal Access',
        default=False,
        help='This feature enables portal access'
    )
    
    portal_access_level = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('admin', 'Admin')
    ], string='Portal Access Level',
       help='Level of portal access granted')
    
    grants_directory_listing = fields.Boolean(
        string='Grants Directory Listing',
        default=False,
        help='Member appears in public directory'
    )
    
    directory_visibility = fields.Selection([
        ('basic', 'Basic Info Only'),
        ('standard', 'Standard Info'),
        ('full', 'Full Profile')
    ], string='Directory Visibility',
       help='What information is shown in directory')

    # ==========================================
    # PUBLICATION FEATURES
    # (when category = 'publication')
    # ==========================================
    
    publication_access_type = fields.Selection([
        ('digital', 'Digital Only'),
        ('print', 'Print Only'),
        ('both', 'Digital + Print')
    ], string='Publication Access',
       help='Type of publication access')
    
    publication_ids = fields.Many2many(
        'product.template',
        'feature_publication_rel',
        'feature_id',
        'publication_id',
        string='Included Publications',
        domain=[('subscription_product_type', 'in', ['journal', 'newsletter', 'subscription'])],
        help='Which publications are included'
    )
    
    download_limit = fields.Integer(
        string='Download Limit',
        default=0,
        help='Maximum downloads per period (0 = unlimited)'
    )
    
    archive_access_years = fields.Integer(
        string='Archive Access (Years)',
        default=0,
        help='How many years of archives are accessible (0 = current only)'
    )

    # ==========================================
    # EVENT FEATURES
    # (when category = 'event')
    # ==========================================
    
    event_registration_benefit = fields.Selection([
        ('priority', 'Priority Registration'),
        ('discount', 'Discounted Registration'),
        ('free', 'Free Registration'),
        ('unlimited', 'Unlimited Events')
    ], string='Event Benefit Type',
       help='Type of event benefit')
    
    free_event_count = fields.Integer(
        string='Free Events Per Year',
        default=0,
        help='Number of free event registrations (0 = none)'
    )
    
    event_discount_percentage = fields.Float(
        string='Event Discount %',
        default=0.0,
        help='Percentage discount on event registrations'
    )
    
    early_registration_days = fields.Integer(
        string='Early Registration Period (Days)',
        default=0,
        help='Days before public when member can register'
    )

    # ==========================================
    # PROFESSIONAL FEATURES
    # (when category = 'professional')
    # ==========================================
    
    enables_credential_tracking = fields.Boolean(
        string='Credential Tracking',
        default=False,
        help='Access to credential tracking system'
    )
    
    enables_ce_tracking = fields.Boolean(
        string='CE/CME Tracking',
        default=False,
        help='Access to continuing education tracking'
    )
    
    ce_credit_reporting = fields.Boolean(
        string='CE Credit Reporting',
        default=False,
        help='Automated CE reporting to licensing boards'
    )
    
    enables_designation_application = fields.Boolean(
        string='Designation Application',
        default=False,
        help='Can apply for professional designations (Fellow, etc.)'
    )
    
    certification_discount = fields.Float(
        string='Certification Discount %',
        default=0.0,
        help='Discount on certification exams'
    )

    # ==========================================
    # NETWORKING FEATURES
    # (when category = 'networking')
    # ==========================================
    
    enables_member_directory = fields.Boolean(
        string='Member Directory Access',
        default=False,
        help='Can search member directory'
    )
    
    enables_messaging = fields.Boolean(
        string='Member Messaging',
        default=False,
        help='Can message other members'
    )
    
    enables_mentorship = fields.Boolean(
        string='Mentorship Program',
        default=False,
        help='Access to mentorship program'
    )
    
    enables_job_board = fields.Boolean(
        string='Job Board Access',
        default=False,
        help='Can post/view jobs on member job board'
    )
    
    networking_event_access = fields.Boolean(
        string='Networking Events',
        default=False,
        help='Invitation to exclusive networking events'
    )

    # ==========================================
    # MODULE INTEGRATION
    # ==========================================
    
    requires_module = fields.Char(
        string='Requires Module',
        help='Technical name of required Odoo module (e.g., membership_professional)'
    )
    
    module_installed = fields.Boolean(
        string='Module Installed',
        compute='_compute_module_installed',
        help='Required module is currently installed'
    )
    
    integration_data = fields.Json(
        string='Integration Data',
        help='JSON data for module integration'
    )

    # ==========================================
    # USAGE TRACKING
    # ==========================================
    
    is_trackable = fields.Boolean(
        string='Track Usage',
        default=False,
        help='Track how often this feature is used'
    )
    
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        help='Total times this feature has been used'
    )
    
    active_users_count = fields.Integer(
        string='Active Users',
        compute='_compute_usage_count',
        help='Number of members currently using this feature'
    )

    # ==========================================
    # PRODUCT ASSOCIATIONS
    # ==========================================
    
    product_ids = fields.Many2many(
        'product.template',
        'product_feature_rel',
        'feature_id',
        'product_id',
        string='Associated Products',
        help='Membership products that include this feature'
    )
    
    product_count = fields.Integer(
        string='Product Count',
        compute='_compute_product_count',
        help='Number of products using this feature'
    )

    # ==========================================
    # VALIDITY & RESTRICTIONS
    # ==========================================
    
    start_date = fields.Date(
        string='Valid From',
        help='Date when this feature becomes available'
    )
    
    end_date = fields.Date(
        string='Valid Until',
        help='Date when this feature expires'
    )
    
    is_currently_valid = fields.Boolean(
        string='Currently Valid',
        compute='_compute_is_valid',
        help='Feature is currently within validity period'
    )
    
    seasonal = fields.Boolean(
        string='Seasonal Feature',
        default=False,
        help='Feature is only available during certain months'
    )
    
    available_months = fields.Char(
        string='Available Months',
        help='Months when seasonal feature is available (e.g., "6,7,8" for summer)'
    )

    # ==========================================
    # TERMS & CONDITIONS
    # ==========================================
    
    requires_acceptance = fields.Boolean(
        string='Requires Terms Acceptance',
        default=False,
        help='Member must accept terms before using'
    )
    
    terms_and_conditions = fields.Html(
        string='Terms & Conditions',
        translate=True,
        help='Terms that must be accepted'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('requires_module')
    def _compute_module_installed(self):
        """Check if required module is installed"""
        for feature in self:
            if feature.requires_module:
                module = self.env['ir.module.module'].search([
                    ('name', '=', feature.requires_module),
                    ('state', '=', 'installed')
                ], limit=1)
                feature.module_installed = bool(module)
            else:
                feature.module_installed = True  # No requirement = always available

    def _compute_usage_count(self):
        """Calculate usage statistics"""
        for feature in self:
            if feature.is_trackable:
                # This would integrate with a usage tracking system
                # For now, set to 0
                feature.usage_count = 0
                feature.active_users_count = 0
            else:
                feature.usage_count = 0
                feature.active_users_count = 0

    @api.depends('product_ids')
    def _compute_product_count(self):
        """Count associated products"""
        for feature in self:
            feature.product_count = len(feature.product_ids)

    @api.depends('start_date', 'end_date')
    def _compute_is_valid(self):
        """Check if feature is currently valid"""
        today = fields.Date.today()
        for feature in self:
            is_valid = True
            
            if feature.start_date and today < feature.start_date:
                is_valid = False
            
            if feature.end_date and today > feature.end_date:
                is_valid = False
            
            feature.is_currently_valid = is_valid

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def check_availability(self, partner_id, date=None):
        """
        Check if feature is available to a partner
        
        Args:
            partner_id: res.partner record or ID
            date: Date to check (defaults to today)
        
        Returns:
            tuple: (bool: is_available, str: reason if not available)
        """
        self.ensure_one()
        
        if date is None:
            date = fields.Date.today()
        
        # Check module requirement
        if not self.module_installed:
            return (False, _("Required module '%s' is not installed") % self.requires_module)
        
        # Check validity period
        if self.start_date and date < self.start_date:
            return (False, _("Feature not available until %s") % self.start_date)
        
        if self.end_date and date > self.end_date:
            return (False, _("Feature expired on %s") % self.end_date)
        
        # Check seasonal availability
        if self.seasonal and self.available_months:
            current_month = str(date.month)
            available = current_month in self.available_months.split(',')
            if not available:
                return (False, _("Feature not available this month"))
        
        # Check if partner has membership with this feature
        if isinstance(partner_id, int):
            partner = self.env['res.partner'].browse(partner_id)
        else:
            partner = partner_id
        
        has_feature = False
        active_memberships = self.env['membership.record'].search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'active')
        ])
        
        for membership in active_memberships:
            if self in membership.product_id.feature_ids:
                has_feature = True
                break
        
        if not has_feature:
            return (False, _("Your membership does not include this feature"))
        
        return (True, '')

    def get_value_for_membership(self, membership_id):
        """
        Get the configured value of this feature for a specific membership
        
        Args:
            membership_id: membership.record ID or record
        
        Returns:
            Value based on feature_type
        """
        self.ensure_one()
        
        # Could be extended to allow per-membership overrides
        # For now, return default value
        
        if self.feature_type == 'boolean':
            return True
        elif self.feature_type == 'unlimited':
            return 'unlimited'
        else:
            return self.default_value

    def action_view_products(self):
        """View products that include this feature"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products with Feature: %s') % self.name,
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.product_ids.ids)],
        }

    def action_track_usage(self):
        """View usage tracking for this feature"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Feature Usage: %s') % self.name,
            'res_model': 'membership.feature.usage',
            'view_mode': 'tree,graph',
            'domain': [('feature_id', '=', self.id)],
            'context': {'default_feature_id': self.id}
        }

    @api.model
    def get_feature_by_code(self, code):
        """
        Get feature by code (helper method)
        
        Args:
            code: Feature code
        
        Returns:
            membership.feature record or False
        """
        return self.search([('code', '=', code)], limit=1)

    def toggle_for_membership(self, membership_id, enable=True):
        """
        Enable or disable this feature for a specific membership
        (Would require a junction table for per-membership overrides)
        
        Args:
            membership_id: membership.record ID
            enable: True to enable, False to disable
        """
        self.ensure_one()
        # Implementation would depend on feature override system
        pass

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure feature code is unique"""
        for feature in self:
            if self.search_count([
                ('code', '=', feature.code),
                ('id', '!=', feature.id)
            ]) > 0:
                raise ValidationError(_("Feature code must be unique. '%s' is already used.") % feature.code)

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for feature in self:
            if feature.discount_percentage < 0 or feature.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    @api.constrains('min_value', 'max_value')
    def _check_value_range(self):
        """Validate value range"""
        for feature in self:
            if feature.max_value > 0 and feature.min_value > feature.max_value:
                raise ValidationError(_("Minimum value cannot be greater than maximum value."))

    @api.constrains('start_date', 'end_date')
    def _check_validity_dates(self):
        """Validate validity dates"""
        for feature in self:
            if feature.start_date and feature.end_date:
                if feature.end_date < feature.start_date:
                    raise ValidationError(_("End date must be after start date."))

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Feature code must be unique!'),
    ]