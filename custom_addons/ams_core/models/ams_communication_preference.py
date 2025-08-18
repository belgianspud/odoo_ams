# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AmsCommunicationPreferenceType(models.Model):
    _name = 'ams.communication.preference.type'
    _description = 'Communication Preference Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Preference Name',
        required=True,
        help="Name of the communication preference (e.g., Newsletter, Event Notifications)"
    )
    code = fields.Char(
        string='Code',
        required=True,
        help="Technical code for this preference type"
    )
    description = fields.Text(
        string='Description',
        help="Description of what this preference controls"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order in which preferences are displayed"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to hide this preference type"
    )
    
    # Communication channels
    applies_to_email = fields.Boolean(
        string='Email',
        default=True,
        help="This preference applies to email communications"
    )
    applies_to_phone = fields.Boolean(
        string='Phone',
        default=False,
        help="This preference applies to phone communications"
    )
    applies_to_mail = fields.Boolean(
        string='Postal Mail',
        default=False,
        help="This preference applies to postal mail"
    )
    applies_to_sms = fields.Boolean(
        string='SMS',
        default=False,
        help="This preference applies to SMS communications"
    )

    # Default settings
    default_opt_in = fields.Boolean(
        string='Default Opt-In',
        default=True,
        help="Default opt-in status for new members"
    )
    required_preference = fields.Boolean(
        string='Required Preference',
        default=False,
        help="Members must have this preference set (cannot be undefined)"
    )
    
    # Legal and compliance
    requires_explicit_consent = fields.Boolean(
        string='Requires Explicit Consent',
        default=False,
        help="This preference requires explicit consent (GDPR compliance)"
    )
    legal_basis = fields.Selection([
        ('consent', 'Consent'),
        ('contract', 'Contract'),
        ('legal_obligation', 'Legal Obligation'),
        ('vital_interests', 'Vital Interests'),
        ('public_task', 'Public Task'),
        ('legitimate_interests', 'Legitimate Interests')
    ], string='Legal Basis', default='consent',
    help="Legal basis for processing (GDPR)")

    # Related preferences
    preference_ids = fields.One2many(
        'ams.communication.preference',
        'preference_type_id',
        string='Member Preferences'
    )
    preference_count = fields.Integer(
        string='Preference Count',
        compute='_compute_preference_count'
    )

    @api.depends('preference_ids')
    def _compute_preference_count(self):
        """Compute number of member preferences for this type"""
        for pref_type in self:
            pref_type.preference_count = len(pref_type.preference_ids)

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure preference codes are unique"""
        for pref_type in self:
            if pref_type.code:
                duplicate = self.search([
                    ('code', '=', pref_type.code),
                    ('id', '!=', pref_type.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Preference code '%s' already exists. Codes must be unique.") % pref_type.code
                    )

    def name_get(self):
        """Custom name display including code"""
        result = []
        for pref_type in self:
            if pref_type.code:
                name = f"[{pref_type.code}] {pref_type.name}"
            else:
                name = pref_type.name
            result.append((pref_type.id, name))
        return result

    def action_view_preferences(self):
        """Action to view member preferences for this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member Preferences: %s') % self.name,
            'res_model': 'ams.communication.preference',
            'view_mode': 'tree,form',
            'domain': [('preference_type_id', '=', self.id)],
            'context': {'default_preference_type_id': self.id}
        }


class AmsCommunicationPreference(models.Model):
    _name = 'ams.communication.preference'
    _description = 'Member Communication Preference'
    _order = 'partner_id, preference_type_id'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        ondelete='cascade',
        help="The contact this preference applies to"
    )
    preference_type_id = fields.Many2one(
        'ams.communication.preference.type',
        string='Preference Type',
        required=True,
        ondelete='cascade',
        help="Type of communication preference"
    )
    
    # Preference settings by channel
    email_opt_in = fields.Boolean(
        string='Email Opt-In',
        help="Opted in to receive this type of communication via email"
    )
    phone_opt_in = fields.Boolean(
        string='Phone Opt-In',
        help="Opted in to receive this type of communication via phone"
    )
    mail_opt_in = fields.Boolean(
        string='Mail Opt-In',
        help="Opted in to receive this type of communication via postal mail"
    )
    sms_opt_in = fields.Boolean(
        string='SMS Opt-In',
        help="Opted in to receive this type of communication via SMS"
    )

    # Consent tracking
    consent_date = fields.Datetime(
        string='Consent Date',
        help="When consent was given or updated"
    )
    consent_method = fields.Selection([
        ('website', 'Website Form'),
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('mail', 'Postal Mail'),
        ('in_person', 'In Person'),
        ('import', 'Data Import'),
        ('admin', 'Admin Override')
    ], string='Consent Method',
    help="How consent was obtained")
    
    consent_ip_address = fields.Char(
        string='IP Address',
        help="IP address when consent was given (for website forms)"
    )
    consent_user_agent = fields.Text(
        string='User Agent',
        help="Browser user agent when consent was given (for website forms)"
    )
    consent_notes = fields.Text(
        string='Consent Notes',
        help="Additional notes about how consent was obtained"
    )

    # Status tracking
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Whether this preference record is active"
    )
    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
        help="When this preference was last updated"
    )
    updated_by = fields.Many2one(
        'res.users',
        string='Updated By',
        default=lambda self: self.env.user,
        help="User who last updated this preference"
    )

    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    any_opt_in = fields.Boolean(
        string='Any Opt-In',
        compute='_compute_any_opt_in',
        store=True,
        help="True if opted in to any communication channel for this preference"
    )

    @api.depends('partner_id.name', 'preference_type_id.name')
    def _compute_display_name(self):
        """Compute display name for preference"""
        for preference in self:
            if preference.partner_id and preference.preference_type_id:
                preference.display_name = (
                    f"{preference.partner_id.name} - {preference.preference_type_id.name}"
                )
            else:
                preference.display_name = _("Communication Preference")

    @api.depends('email_opt_in', 'phone_opt_in', 'mail_opt_in', 'sms_opt_in')
    def _compute_any_opt_in(self):
        """Compute if opted in to any channel"""
        for preference in self:
            preference.any_opt_in = any([
                preference.email_opt_in,
                preference.phone_opt_in,
                preference.mail_opt_in,
                preference.sms_opt_in
            ])

    @api.model
    def create(self, vals):
        """Override create to set default preferences and log creation"""
        # Set default opt-in values based on preference type
        if 'preference_type_id' in vals:
            pref_type = self.env['ams.communication.preference.type'].browse(vals['preference_type_id'])
            
            # Set defaults if not explicitly provided
            if 'email_opt_in' not in vals and pref_type.applies_to_email:
                vals['email_opt_in'] = pref_type.default_opt_in
            if 'phone_opt_in' not in vals and pref_type.applies_to_phone:
                vals['phone_opt_in'] = pref_type.default_opt_in
            if 'mail_opt_in' not in vals and pref_type.applies_to_mail:
                vals['mail_opt_in'] = pref_type.default_opt_in
            if 'sms_opt_in' not in vals and pref_type.applies_to_sms:
                vals['sms_opt_in'] = pref_type.default_opt_in

        # Set consent tracking
        if 'consent_date' not in vals:
            vals['consent_date'] = fields.Datetime.now()
        if 'consent_method' not in vals:
            vals['consent_method'] = 'admin'

        preference = super().create(vals)
        
        # Log preference creation
        try:
            self.env['ams.audit.log'].create({
                'partner_id': preference.partner_id.id,
                'activity_type': 'preference_created',
                'description': f"Created communication preference: {preference.preference_type_id.name}",
                'user_id': self.env.user.id,
                'timestamp': fields.Datetime.now()
            })
        except Exception as e:
            _logger.warning(f"Failed to log preference creation: {e}")
            
        return preference

    def write(self, vals):
        """Override write to track preference changes and consent updates"""
        # Track if any opt-in values are changing
        opt_in_fields = ['email_opt_in', 'phone_opt_in', 'mail_opt_in', 'sms_opt_in']
        opt_in_changed = any(field in vals for field in opt_in_fields)
        
        if opt_in_changed:
            # Update consent tracking
            vals.update({
                'consent_date': fields.Datetime.now(),
                'last_updated': fields.Datetime.now(),
                'updated_by': self.env.user.id
            })
            
            # Log the change
            for preference in self:
                try:
                    changes = []
                    for field in opt_in_fields:
                        if field in vals:
                            old_value = getattr(preference, field)
                            new_value = vals[field]
                            if old_value != new_value:
                                channel = field.replace('_opt_in', '')
                                status = 'opted in' if new_value else 'opted out'
                                changes.append(f"{channel}: {status}")
                    
                    if changes:
                        self.env['ams.audit.log'].create({
                            'partner_id': preference.partner_id.id,
                            'activity_type': 'preference_updated',
                            'description': f"Updated {preference.preference_type_id.name} - {', '.join(changes)}",
                            'user_id': self.env.user.id,
                            'timestamp': fields.Datetime.now()
                        })
                except Exception as e:
                    _logger.warning(f"Failed to log preference update: {e}")

        return super().write(vals)

    @api.constrains('partner_id', 'preference_type_id')
    def _check_unique_partner_preference(self):
        """Ensure each partner has only one record per preference type"""
        for preference in self:
            duplicate = self.search([
                ('partner_id', '=', preference.partner_id.id),
                ('preference_type_id', '=', preference.preference_type_id.id),
                ('id', '!=', preference.id)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    _("Partner '%s' already has a preference record for '%s'.") 
                    % (preference.partner_id.name, preference.preference_type_id.name)
                )

    def action_opt_in_all(self):
        """Action to opt in to all applicable channels"""
        for preference in self:
            vals = {}
            if preference.preference_type_id.applies_to_email:
                vals['email_opt_in'] = True
            if preference.preference_type_id.applies_to_phone:
                vals['phone_opt_in'] = True
            if preference.preference_type_id.applies_to_mail:
                vals['mail_opt_in'] = True
            if preference.preference_type_id.applies_to_sms:
                vals['sms_opt_in'] = True
            
            if vals:
                vals['consent_method'] = 'admin'
                preference.write(vals)
        return True

    def action_opt_out_all(self):
        """Action to opt out of all channels"""
        for preference in self:
            vals = {
                'email_opt_in': False,
                'phone_opt_in': False,
                'mail_opt_in': False,
                'sms_opt_in': False,
                'consent_method': 'admin'
            }
            preference.write(vals)
        return True

    @api.model
    def get_partner_preferences(self, partner_id):
        """Get all communication preferences for a partner"""
        preferences = {}
        partner_prefs = self.search([('partner_id', '=', partner_id), ('active', '=', True)])
        
        for pref in partner_prefs:
            preferences[pref.preference_type_id.code] = {
                'email': pref.email_opt_in,
                'phone': pref.phone_opt_in,
                'mail': pref.mail_opt_in,
                'sms': pref.sms_opt_in,
                'consent_date': pref.consent_date,
                'consent_method': pref.consent_method
            }
        
        return preferences

    @api.model
    def can_send_communication(self, partner_id, preference_code, channel='email'):
        """Check if we can send a specific type of communication to a partner"""
        preference = self.search([
            ('partner_id', '=', partner_id),
            ('preference_type_id.code', '=', preference_code),
            ('active', '=', True)
        ], limit=1)
        
        if not preference:
            # If no preference record exists, check default
            pref_type = self.env['ams.communication.preference.type'].search([
                ('code', '=', preference_code),
                ('active', '=', True)
            ], limit=1)
            return pref_type.default_opt_in if pref_type else False
        
        # Check specific channel opt-in
        field_name = f"{channel}_opt_in"
        return getattr(preference, field_name, False)

    @api.model
    def create_default_preferences(self, partner_id):
        """Create default preferences for a new partner"""
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return False
            
        pref_types = self.env['ams.communication.preference.type'].search([('active', '=', True)])
        created_prefs = []
        
        for pref_type in pref_types:
            existing = self.search([
                ('partner_id', '=', partner_id),
                ('preference_type_id', '=', pref_type.id)
            ], limit=1)
            
            if not existing:
                pref_vals = {
                    'partner_id': partner_id,
                    'preference_type_id': pref_type.id,
                    'consent_method': 'admin',
                    'consent_notes': 'Default preferences created automatically'
                }
                
                # Set default opt-in values
                if pref_type.applies_to_email:
                    pref_vals['email_opt_in'] = pref_type.default_opt_in
                if pref_type.applies_to_phone:
                    pref_vals['phone_opt_in'] = pref_type.default_opt_in
                if pref_type.applies_to_mail:
                    pref_vals['mail_opt_in'] = pref_type.default_opt_in
                if pref_type.applies_to_sms:
                    pref_vals['sms_opt_in'] = pref_type.default_opt_in
                
                created_prefs.append(self.create(pref_vals))
        
        return created_prefs