# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AMSCommunicationPreference(models.Model):
    """Communication preferences for association members"""
    
    _name = 'ams.communication.preference'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'AMS Communication Preference'
    _order = 'partner_id, category, communication_type'
    _rec_name = 'preference_summary'

    # ========================================================================
    # CORE FIELDS
    # ========================================================================

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Uncheck to archive this preference record"
    )

    partner_id = fields.Many2one(
        'res.partner', 
        string="Member", 
        required=True,
        ondelete='cascade',
        tracking=True,
        help="Member for whom this preference applies"
    )

    communication_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('mail', 'Physical Mail'),
        ('phone', 'Phone')
    ], string="Communication Type", required=True,
       tracking=True,
       help="Type of communication channel")

    category = fields.Selection([
        ('marketing', 'Marketing'),
        ('membership', 'Membership'),
        ('events', 'Events'),
        ('education', 'Education'),
        ('fundraising', 'Fundraising'),
        ('governance', 'Governance')
    ], string="Category", required=True,
       tracking=True,
       help="Category of communications")

    opted_in = fields.Boolean(
        string="Opted In", 
        default=True,
        tracking=True,
        help="Whether member has opted in to receive this type of communication"
    )

    # ========================================================================
    # TRACKING AND COMPLIANCE FIELDS
    # ========================================================================

    date_updated = fields.Datetime(
        string="Last Updated", 
        default=fields.Datetime.now,
        required=True,
        help="When this preference was last updated"
    )

    ip_address = fields.Char(
        string="IP Address",
        help="IP address when preference was set (for compliance tracking)"
    )

    consent_source = fields.Char(
        string="Consent Source",
        tracking=True,
        help="How/where the consent was obtained (e.g., 'website signup', 'phone call', 'event registration')"
    )

    updated_by = fields.Many2one(
        'res.users',
        string="Updated By",
        default=lambda self: self.env.user,
        help="User who last updated this preference"
    )

    # ========================================================================
    # ADDITIONAL TRACKING FIELDS
    # ========================================================================

    original_opt_in_date = fields.Datetime(
        string="Original Opt-in Date",
        help="When the member first opted in to this communication type/category"
    )

    opt_out_date = fields.Datetime(
        string="Opt-out Date",
        help="When the member opted out (if applicable)"
    )

    double_opt_in = fields.Boolean(
        string="Double Opt-in Confirmed",
        default=False,
        tracking=True,
        help="Whether double opt-in confirmation was completed"
    )

    double_opt_in_date = fields.Datetime(
        string="Double Opt-in Date",
        help="When double opt-in was confirmed"
    )

    # ========================================================================
    # COMPLIANCE AND LEGAL FIELDS
    # ========================================================================

    gdpr_consent = fields.Boolean(
        string="GDPR Consent",
        default=False,
        tracking=True,
        help="Explicit GDPR consent obtained"
    )

    gdpr_consent_date = fields.Datetime(
        string="GDPR Consent Date",
        help="When GDPR consent was obtained"
    )

    can_spam_compliant = fields.Boolean(
        string="CAN-SPAM Compliant",
        default=True,
        help="Whether this preference complies with CAN-SPAM requirements"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    preference_summary = fields.Char(
        string="Preference Summary",
        compute='_compute_preference_summary',
        store=True,
        help="Human-readable summary of this preference"
    )

    status_display = fields.Char(
        string="Status",
        compute='_compute_status_display',
        help="Current status of this preference"
    )

    compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('needs_confirmation', 'Needs Confirmation'),
        ('expired', 'Consent Expired'),
        ('non_compliant', 'Non-compliant')
    ], string="Compliance Status", 
       compute='_compute_compliance_status',
       store=True,  # Make it stored so it can be searched
       help="Compliance status of this preference")

    # ========================================================================
    # CONSTRAINTS
    # ========================================================================

    _sql_constraints = [
        ('unique_preference', 
         'UNIQUE(partner_id, communication_type, category)', 
         'A member can only have one preference setting per communication type and category!'),
    ]

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('partner_id', 'communication_type', 'category', 'opted_in')
    def _compute_preference_summary(self):
        """Compute human-readable preference summary"""
        for record in self:
            if record.partner_id and record.communication_type and record.category:
                status = "Opted In" if record.opted_in else "Opted Out"
                record.preference_summary = f"{record.partner_id.display_name} - {record.communication_type.title()} - {record.category.title()} ({status})"
            else:
                record.preference_summary = "Incomplete Preference"

    @api.depends('opted_in', 'double_opt_in', 'gdpr_consent')
    def _compute_status_display(self):
        """Compute status display"""
        for record in self:
            if not record.opted_in:
                record.status_display = "Opted Out"
            elif record.gdpr_consent and record.double_opt_in:
                record.status_display = "Confirmed (GDPR + Double Opt-in)"
            elif record.gdpr_consent:
                record.status_display = "GDPR Consent"
            elif record.double_opt_in:
                record.status_display = "Double Opt-in Confirmed"
            else:
                record.status_display = "Basic Opt-in"

    @api.depends('opted_in', 'gdpr_consent', 'double_opt_in', 'can_spam_compliant', 'communication_type')
    def _compute_compliance_status(self):
        """Compute compliance status"""
        for record in self:
            if not record.opted_in:
                record.compliance_status = 'compliant'  # Opted out is always compliant
            elif record.communication_type == 'email':
                # Email requires more stringent compliance
                if record.gdpr_consent and record.double_opt_in and record.can_spam_compliant:
                    record.compliance_status = 'compliant'
                elif record.gdpr_consent or record.double_opt_in:
                    record.compliance_status = 'needs_confirmation'
                else:
                    record.compliance_status = 'non_compliant'
            else:
                # Other communication types
                if record.gdpr_consent or record.double_opt_in:
                    record.compliance_status = 'compliant'
                else:
                    record.compliance_status = 'needs_confirmation'

    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================

    @api.constrains('communication_type', 'category')
    def _check_valid_combination(self):
        """Validate communication type and category combination"""
        # Skip validation during data loading/installation
        if self.env.context.get('install_mode') or self.env.context.get('module_loading') or self.env.context.get('skip_constraint_validation'):
            return
            
        for record in self:
            if self._is_invalid_combination(record.communication_type, record.category):
                invalid_combinations_text = {
                    ('sms', 'governance'): _("SMS is not appropriate for governance communications"),
                }
                error_msg = invalid_combinations_text.get(
                    (record.communication_type, record.category),
                    _("Invalid communication type and category combination")
                )
                raise ValidationError(error_msg)

    # ========================================================================
    # CRUD METHODS
    # ========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set initial tracking fields"""
        for vals in vals_list:
            # Set original opt-in date if opted in
            if vals.get('opted_in') and not vals.get('original_opt_in_date'):
                vals['original_opt_in_date'] = fields.Datetime.now()
        
        return super().create(vals_list)

    def write(self, vals):
        """Override write to track preference changes"""
        for record in self:
            # Track opt-out date
            if 'opted_in' in vals:
                if vals['opted_in'] and not record.opted_in:
                    # Member is opting back in
                    vals['opt_out_date'] = False
                    if not record.original_opt_in_date:
                        vals['original_opt_in_date'] = fields.Datetime.now()
                elif not vals['opted_in'] and record.opted_in:
                    # Member is opting out
                    vals['opt_out_date'] = fields.Datetime.now()

            # Update last modified date
            vals['date_updated'] = fields.Datetime.now()
            vals['updated_by'] = self.env.user.id

            # Track GDPR consent date
            if 'gdpr_consent' in vals and vals['gdpr_consent'] and not record.gdpr_consent:
                vals['gdpr_consent_date'] = fields.Datetime.now()

            # Track double opt-in date
            if 'double_opt_in' in vals and vals['double_opt_in'] and not record.double_opt_in:
                vals['double_opt_in_date'] = fields.Datetime.now()

        return super().write(vals)

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def _is_invalid_combination(self, communication_type, category):
        """Check if a communication type and category combination is invalid"""
        # Add validation rules here
        invalid_combinations = [
            ('sms', 'governance'),  # SMS not appropriate for governance
            # Add more invalid combinations as needed
        ]
        
        return (communication_type, category) in invalid_combinations

    @api.model
    def get_member_preferences(self, partner_id, communication_type=None, category=None):
        """Get communication preferences for a member"""
        domain = [('partner_id', '=', partner_id)]
        
        if communication_type:
            domain.append(('communication_type', '=', communication_type))
        if category:
            domain.append(('category', '=', category))
            
        return self.search(domain)

    @api.model
    def check_communication_allowed(self, partner_id, communication_type, category):
        """Check if a specific communication is allowed for a member"""
        preference = self.search([
            ('partner_id', '=', partner_id),
            ('communication_type', '=', communication_type),
            ('category', '=', category)
        ], limit=1)
        
        if preference:
            return preference.opted_in
        else:
            # Default behavior - can be configured
            return True

    @api.model
    def create_default_preferences(self, partner_id):
        """Create default communication preferences for a new member"""
        communication_types = ['email', 'sms', 'mail', 'phone']
        categories = ['marketing', 'membership', 'events', 'education', 'fundraising', 'governance']
        
        preferences_to_create = []
        
        for comm_type in communication_types:
            for category in categories:
                # Skip invalid combinations
                if self._is_invalid_combination(comm_type, category):
                    continue
                    
                # Check if preference already exists
                existing = self.search([
                    ('partner_id', '=', partner_id),
                    ('communication_type', '=', comm_type),
                    ('category', '=', category)
                ])
                
                if not existing:
                    # Default opt-in rules - can be customized
                    default_opt_in = True
                    if comm_type == 'sms' and category in ['marketing', 'fundraising']:
                        default_opt_in = False  # More restrictive for SMS marketing
                    
                    preferences_to_create.append({
                        'partner_id': partner_id,
                        'communication_type': comm_type,
                        'category': category,
                        'opted_in': default_opt_in,
                        'consent_source': 'default_creation',
                    })
        
        if preferences_to_create:
            return self.create(preferences_to_create)
        else:
            return self.browse()

    def action_opt_in(self):
        """Action to opt in to communications"""
        self.ensure_one()
        self.write({
            'opted_in': True,
            'consent_source': 'manual_opt_in',
            'ip_address': self.env.context.get('ip_address', ''),
        })

    def action_opt_out(self):
        """Action to opt out of communications"""
        self.ensure_one()
        self.write({
            'opted_in': False,
            'consent_source': 'manual_opt_out',
            'ip_address': self.env.context.get('ip_address', ''),
        })

    def action_confirm_gdpr_consent(self):
        """Action to confirm GDPR consent"""
        self.ensure_one()
        self.write({
            'gdpr_consent': True,
            'opted_in': True,  # GDPR consent implies opt-in
        })

    def action_confirm_double_opt_in(self):
        """Action to confirm double opt-in"""
        self.ensure_one()
        self.write({
            'double_opt_in': True,
            'opted_in': True,  # Double opt-in implies opt-in
        })

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.preference_summary or "Communication Preference"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search"""
        args = args or []
        
        if name:
            # Search in partner name, communication type, and category
            domain = [
                '|', '|', '|',
                ('partner_id.name', operator, name),
                ('partner_id.display_name', operator, name),
                ('communication_type', operator, name),
                ('category', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)