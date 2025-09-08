# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSCommunicationPreference(models.Model):
    """Member communication preferences and consent tracking."""
    _name = 'ams.communication.preference'
    _description = 'Communication Preference'
    _order = 'partner_id, communication_type, category'
    _rec_name = 'display_name'

    # ==========================================
    # CORE FIELDS
    # ==========================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
        help='Related member or contact'
    )

    communication_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('mail', 'Mail'),
        ('phone', 'Phone')
    ], string='Communication Type', required=True, help='Method of communication')

    category = fields.Selection([
        ('marketing', 'Marketing'),
        ('membership', 'Membership'),
        ('events', 'Events'),
        ('education', 'Education'),
        ('committee', 'Committee'),
        ('fundraising', 'Fundraising'),
        ('emergency', 'Emergency')
    ], string='Category', required=True, help='Purpose of communication')

    opted_in = fields.Boolean(
        string='Opted In',
        required=True,
        default=True,
        help='Consent status - True means member has opted in to receive communications'
    )

    # ==========================================
    # COMPLIANCE TRACKING (GDPR)
    # ==========================================

    date_updated = fields.Datetime(
        string='Last Updated',
        required=True,
        default=fields.Datetime.now,
        help='When this preference was last modified'
    )

    ip_address = fields.Char(
        string='IP Address',
        help='IP address when consent was given (for GDPR compliance)'
    )

    consent_source = fields.Char(
        string='Consent Source',
        help='Source where consent was obtained (e.g., website URL, form name)'
    )

    consent_method = fields.Selection([
        ('website_form', 'Website Form'),
        ('phone_call', 'Phone Call'),
        ('paper_form', 'Paper Form'),
        ('email_reply', 'Email Reply'),
        ('staff_update', 'Staff Update'),
        ('import', 'Data Import')
    ], string='Consent Method', help='How the consent was obtained')

    # ==========================================
    # COMPUTED & HELPER FIELDS
    # ==========================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    partner_email = fields.Char(
        related='partner_id.email',
        string='Partner Email',
        readonly=True
    )

    partner_phone = fields.Char(
        related='partner_id.phone',
        string='Partner Phone',
        readonly=True
    )

    partner_mobile = fields.Char(
        related='partner_id.mobile',
        string='Partner Mobile',
        readonly=True
    )

    is_member = fields.Boolean(
        related='partner_id.is_member',
        string='Is Member',
        readonly=True
    )

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    _sql_constraints = [
        ('unique_preference', 
         'UNIQUE(partner_id, communication_type, category)', 
         'Only one preference record per partner, communication type, and category combination is allowed.'),
    ]

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('partner_id', 'communication_type', 'category', 'opted_in')
    def _compute_display_name(self):
        """Compute display name for preference records."""
        for record in self:
            partner_name = record.partner_id.name or 'Unknown'
            comm_type = dict(record._fields['communication_type'].selection).get(
                record.communication_type, record.communication_type
            )
            category = dict(record._fields['category'].selection).get(
                record.category, record.category
            )
            status = 'Opted In' if record.opted_in else 'Opted Out'
            
            record.display_name = f"{partner_name} - {comm_type} - {category} ({status})"

    # ==========================================
    # VALIDATION
    # ==========================================

    @api.constrains('communication_type', 'partner_id')
    def _validate_communication_availability(self):
        """Validate that the communication type is available for the partner."""
        for record in self:
            partner = record.partner_id
            
            # Email validation
            if record.communication_type == 'email' and not partner.email:
                if record.opted_in:
                    raise ValidationError(
                        f"Cannot opt in {partner.name} for email communications - no email address on file."
                    )
            
            # Phone validation
            if record.communication_type == 'phone' and not (partner.phone or partner.mobile):
                if record.opted_in:
                    raise ValidationError(
                        f"Cannot opt in {partner.name} for phone communications - no phone number on file."
                    )
            
            # SMS validation
            if record.communication_type == 'sms' and not partner.mobile:
                if record.opted_in:
                    raise ValidationError(
                        f"Cannot opt in {partner.name} for SMS communications - no mobile phone number on file."
                    )
            
            # Mail validation (requires physical address)
            if record.communication_type == 'mail' and not partner.street:
                if record.opted_in:
                    raise ValidationError(
                        f"Cannot opt in {partner.name} for mail communications - no address on file."
                    )

    @api.constrains('category', 'communication_type')
    def _validate_emergency_communications(self):
        """Ensure emergency communications have reasonable defaults."""
        for record in self:
            # Emergency communications should generally default to opted in
            # This is a business rule that can be customized
            if record.category == 'emergency':
                # Log a warning if someone opts out of emergency communications
                if not record.opted_in:
                    # We'll just log this rather than prevent it, as members should have choice
                    pass

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    @api.model
    def get_partner_preferences(self, partner_id, communication_type=None, category=None):
        """Get preferences for a specific partner with optional filtering."""
        domain = [('partner_id', '=', partner_id)]
        
        if communication_type:
            domain.append(('communication_type', '=', communication_type))
        if category:
            domain.append(('category', '=', category))
            
        return self.search(domain)

    @api.model
    def check_communication_allowed(self, partner_id, communication_type, category):
        """Check if communication is allowed for partner/type/category combination."""
        preference = self.search([
            ('partner_id', '=', partner_id),
            ('communication_type', '=', communication_type),
            ('category', '=', category)
        ], limit=1)
        
        if preference:
            return preference.opted_in
        
        # If no preference exists, check for system defaults
        return self._get_default_preference(communication_type, category)

    @api.model
    def _get_default_preference(self, communication_type, category):
        """Get system default preference for communication type/category combination."""
        # Emergency communications are always allowed by default
        if category == 'emergency':
            return True
        
        # Membership communications default to True (essential communications)
        if category == 'membership':
            return True
            
        # Marketing defaults to False (opt-in required)
        if category == 'marketing':
            return False
            
        # Events, Education, Committee default to True for members
        if category in ['events', 'education', 'committee']:
            return True
            
        # Fundraising defaults to True but should respect member preferences
        if category == 'fundraising':
            return True
            
        # Default to True for unlisted categories
        return True

    @api.model
    def create_default_preferences(self, partner_id):
        """Create default communication preferences for a new member."""
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return False

        preferences_to_create = []
        
        # Define default preferences based on what the partner can receive
        communication_types = ['email', 'sms', 'mail', 'phone']
        categories = ['marketing', 'membership', 'events', 'education', 'committee', 'fundraising', 'emergency']
        
        for comm_type in communication_types:
            for category in categories:
                # Check if partner can receive this type of communication
                can_receive = self._partner_can_receive_communication(partner, comm_type)
                
                if can_receive:
                    # Only create if preference doesn't already exist
                    existing = self.search([
                        ('partner_id', '=', partner_id),
                        ('communication_type', '=', comm_type),
                        ('category', '=', category)
                    ], limit=1)
                    
                    if not existing:
                        default_opted_in = self._get_default_preference(comm_type, category)
                        preferences_to_create.append({
                            'partner_id': partner_id,
                            'communication_type': comm_type,
                            'category': category,
                            'opted_in': default_opted_in,
                            'consent_method': 'staff_update',
                            'consent_source': 'Default preferences on member creation',
                        })
        
        if preferences_to_create:
            return self.create(preferences_to_create)
        return self.browse()

    def _partner_can_receive_communication(self, partner, communication_type):
        """Check if partner has the necessary contact info for communication type."""
        if communication_type == 'email':
            return bool(partner.email)
        elif communication_type == 'sms':
            return bool(partner.mobile)
        elif communication_type == 'phone':
            return bool(partner.phone or partner.mobile)
        elif communication_type == 'mail':
            return bool(partner.street and partner.city)
        return False

    def toggle_preference(self):
        """Toggle the opted_in status and update tracking fields."""
        self.ensure_one()
        self.write({
            'opted_in': not self.opted_in,
            'date_updated': fields.Datetime.now(),
            'consent_method': 'staff_update',
            'consent_source': 'Manual toggle by staff'
        })
        return True

    def update_preference(self, opted_in, consent_source=None, consent_method=None, ip_address=None):
        """Update preference with proper consent tracking."""
        self.ensure_one()
        
        update_vals = {
            'opted_in': opted_in,
            'date_updated': fields.Datetime.now(),
        }
        
        if consent_source:
            update_vals['consent_source'] = consent_source
        if consent_method:
            update_vals['consent_method'] = consent_method
        if ip_address:
            update_vals['ip_address'] = ip_address
            
        self.write(update_vals)
        return True

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure proper defaults and validation."""
        for vals in vals_list:
            # Set date_updated if not provided
            if 'date_updated' not in vals:
                vals['date_updated'] = fields.Datetime.now()
                
            # Set default consent method if not provided
            if 'consent_method' not in vals:
                vals['consent_method'] = 'staff_update'
                
        return super().create(vals_list)

    def write(self, vals):
        """Override write to track preference changes."""
        # Update the date_updated when preference changes
        if 'opted_in' in vals:
            vals['date_updated'] = fields.Datetime.now()
            
        return super().write(vals)

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_opt_in(self):
        """Action to opt member in to communication."""
        return self.write({
            'opted_in': True,
            'date_updated': fields.Datetime.now(),
            'consent_method': 'staff_update'
        })

    def action_opt_out(self):
        """Action to opt member out of communication."""
        return self.write({
            'opted_in': False,
            'date_updated': fields.Datetime.now(),
            'consent_method': 'staff_update'
        })

    # ==========================================
    # REPORTING METHODS
    # ==========================================

    @api.model
    def get_opt_out_summary(self):
        """Get summary of opt-out preferences by category and type."""
        opt_outs = self.search([('opted_in', '=', False)])
        
        summary = {}
        for preference in opt_outs:
            category = preference.category
            comm_type = preference.communication_type
            
            if category not in summary:
                summary[category] = {}
            if comm_type not in summary[category]:
                summary[category][comm_type] = 0
                
            summary[category][comm_type] += 1
            
        return summary

    @api.model
    def get_compliance_report(self):
        """Get GDPR compliance report showing consent documentation."""
        preferences = self.search([])
        
        missing_consent_source = preferences.filtered(lambda p: not p.consent_source)
        missing_consent_method = preferences.filtered(lambda p: not p.consent_method)
        missing_ip_address = preferences.filtered(lambda p: p.opted_in and not p.ip_address and p.consent_method == 'website_form')
        
        return {
            'total_preferences': len(preferences),
            'missing_consent_source': len(missing_consent_source),
            'missing_consent_method': len(missing_consent_method),
            'missing_ip_address': len(missing_ip_address),
            'compliance_percentage': ((len(preferences) - len(missing_consent_source) - len(missing_consent_method)) / len(preferences) * 100) if preferences else 100
        }