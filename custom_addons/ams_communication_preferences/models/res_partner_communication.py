# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartnerCommunication(models.Model):
    """Extend res.partner with communication preference functionality"""
    
    _inherit = 'res.partner'

    # ========================================================================
    # COMMUNICATION PREFERENCE FIELDS
    # ========================================================================

    communication_preference_ids = fields.One2many(
        'ams.communication.preference',
        'partner_id',
        string="Communication Preferences",
        help="Member's communication preferences by type and category"
    )

    # ========================================================================
    # GLOBAL COMMUNICATION SETTINGS
    # ========================================================================

    communication_opt_out = fields.Boolean(
        string="Global Communication Opt-out",
        default=False,
        help="Member has opted out of ALL communications"
    )

    do_not_email = fields.Boolean(
        string="Do Not Email",
        default=False,
        help="Never send emails to this member"
    )

    do_not_sms = fields.Boolean(
        string="Do Not SMS",
        default=False,
        help="Never send SMS messages to this member"
    )

    do_not_mail = fields.Boolean(
        string="Do Not Mail",
        default=False,
        help="Never send physical mail to this member"
    )

    do_not_call = fields.Boolean(
        string="Do Not Call",
        default=False,
        help="Never call this member"
    )

    # ========================================================================
    # COMPLIANCE AND TRACKING
    # ========================================================================

    gdpr_consent_given = fields.Boolean(
        string="GDPR Consent Given",
        default=False,
        help="Member has given explicit GDPR consent"
    )

    gdpr_consent_date = fields.Datetime(
        string="GDPR Consent Date",
        help="When GDPR consent was given"
    )

    privacy_policy_accepted = fields.Boolean(
        string="Privacy Policy Accepted",
        default=False,
        help="Member has accepted the privacy policy"
    )

    privacy_policy_date = fields.Datetime(
        string="Privacy Policy Acceptance Date",
        help="When privacy policy was accepted"
    )

    email_bounce_count = fields.Integer(
        string="Email Bounce Count",
        default=0,
        help="Number of email bounces for this member"
    )

    last_email_bounce_date = fields.Datetime(
        string="Last Email Bounce",
        help="Date of last email bounce"
    )

    # ========================================================================
    # PREFERRED COMMUNICATION SETTINGS
    # ========================================================================

    preferred_communication_method = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('mail', 'Physical Mail'),
        ('phone', 'Phone')
    ], string="Preferred Communication Method",
       help="Member's preferred way to be contacted")

    preferred_language = fields.Many2one(
        'res.lang',
        string="Preferred Language",
        help="Member's preferred language for communications"
    )

    communication_frequency = fields.Selection([
        ('immediate', 'Immediate'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Newsletter'),
        ('quarterly', 'Quarterly Updates'),
        ('minimal', 'Minimal Communications')
    ], string="Communication Frequency",
       default='weekly',
       help="How frequently member wants to receive communications")

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    email_opt_in_count = fields.Integer(
        string="Email Opt-ins",
        compute='_compute_communication_stats',
        help="Number of email categories opted in to"
    )

    sms_opt_in_count = fields.Integer(
        string="SMS Opt-ins", 
        compute='_compute_communication_stats',
        help="Number of SMS categories opted in to"
    )

    total_opt_ins = fields.Integer(
        string="Total Opt-ins",
        compute='_compute_communication_stats',
        help="Total number of communication preferences opted in to"
    )

    communication_compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('needs_attention', 'Needs Attention'),
        ('non_compliant', 'Non-compliant')
    ], string="Compliance Status",
       compute='_compute_compliance_status',
       help="Overall communication compliance status")

    can_email = fields.Boolean(
        string="Can Email",
        compute='_compute_communication_permissions',
        help="Whether this member can be emailed"
    )

    can_sms = fields.Boolean(
        string="Can SMS",
        compute='_compute_communication_permissions',
        help="Whether this member can receive SMS"
    )

    can_mail = fields.Boolean(
        string="Can Mail",
        compute='_compute_communication_permissions', 
        help="Whether this member can receive physical mail"
    )

    can_call = fields.Boolean(
        string="Can Call",
        compute='_compute_communication_permissions',
        help="Whether this member can be called"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================

    @api.depends('communication_preference_ids.opted_in', 'communication_preference_ids.communication_type')
    def _compute_communication_stats(self):
        """Compute communication statistics"""
        for partner in self:
            email_count = len(partner.communication_preference_ids.filtered(
                lambda p: p.communication_type == 'email' and p.opted_in
            ))
            sms_count = len(partner.communication_preference_ids.filtered(
                lambda p: p.communication_type == 'sms' and p.opted_in
            ))
            total_count = len(partner.communication_preference_ids.filtered('opted_in'))
            
            partner.email_opt_in_count = email_count
            partner.sms_opt_in_count = sms_count
            partner.total_opt_ins = total_count

    @api.depends('communication_preference_ids.compliance_status', 'gdpr_consent_given', 'privacy_policy_accepted')
    def _compute_compliance_status(self):
        """Compute overall compliance status"""
        for partner in self:
            preferences = partner.communication_preference_ids
            
            if not preferences:
                partner.communication_compliance_status = 'compliant'
                continue
                
            non_compliant = preferences.filtered(lambda p: p.compliance_status == 'non_compliant')
            needs_attention = preferences.filtered(lambda p: p.compliance_status == 'needs_confirmation')
            
            if non_compliant:
                partner.communication_compliance_status = 'non_compliant'
            elif needs_attention:
                partner.communication_compliance_status = 'needs_attention'
            else:
                partner.communication_compliance_status = 'compliant'

    @api.depends('communication_opt_out', 'do_not_email', 'do_not_sms', 'do_not_mail', 'do_not_call',
                 'communication_preference_ids.opted_in', 'communication_preference_ids.communication_type')
    def _compute_communication_permissions(self):
        """Compute what communication types are allowed"""
        for partner in self:
            # Global opt-out overrides everything
            if partner.communication_opt_out:
                partner.can_email = False
                partner.can_sms = False
                partner.can_mail = False
                partner.can_call = False
                continue

            # Check specific do-not flags
            partner.can_email = not partner.do_not_email
            partner.can_sms = not partner.do_not_sms
            partner.can_mail = not partner.do_not_mail
            partner.can_call = not partner.do_not_call

            # Additional checks based on bounce count
            if partner.email_bounce_count >= 5:  # Configurable threshold
                partner.can_email = False

    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================

    def check_communication_allowed(self, communication_type, category):
        """Check if a specific communication is allowed"""
        self.ensure_one()
        
        # Check global opt-out
        if self.communication_opt_out:
            return False
        
        # Check specific do-not flags
        if communication_type == 'email' and self.do_not_email:
            return False
        elif communication_type == 'sms' and self.do_not_sms:
            return False
        elif communication_type == 'mail' and self.do_not_mail:
            return False
        elif communication_type == 'phone' and self.do_not_call:
            return False
        
        # Check specific preference
        preference = self.env['ams.communication.preference'].search([
            ('partner_id', '=', self.id),
            ('communication_type', '=', communication_type),
            ('category', '=', category)
        ], limit=1)
        
        if preference:
            return preference.opted_in
        else:
            # Default policy - can be configured
            return True

    def create_communication_preferences(self):
        """Create default communication preferences for this member"""
        self.ensure_one()
        return self.env['ams.communication.preference'].create_default_preferences(self.id)

    def action_global_opt_out(self):
        """Opt out of all communications"""
        self.ensure_one()
        self.write({
            'communication_opt_out': True,
            'do_not_email': True,
            'do_not_sms': True,
            'do_not_mail': True,
            'do_not_call': True,
        })
        # Also opt out of all specific preferences
        self.communication_preference_ids.write({'opted_in': False})

    def action_global_opt_in(self):
        """Opt back in to communications (with defaults)"""
        self.ensure_one()
        self.write({
            'communication_opt_out': False,
            'do_not_email': False,
            'do_not_sms': False,
            'do_not_mail': False,
            'do_not_call': False,
        })
        # Create default preferences if none exist
        if not self.communication_preference_ids:
            self.create_communication_preferences()

    def record_email_bounce(self):
        """Record an email bounce for this member"""
        self.ensure_one()
        self.write({
            'email_bounce_count': self.email_bounce_count + 1,
            'last_email_bounce_date': fields.Datetime.now(),
        })
        
        # Auto-disable email if too many bounces
        if self.email_bounce_count >= 5:
            self.write({'do_not_email': True})

    def reset_email_bounces(self):
        """Reset email bounce count (e.g., when email is updated)"""
        self.ensure_one()
        self.write({
            'email_bounce_count': 0,
            'last_email_bounce_date': False,
            'do_not_email': False,
        })

    def action_gdpr_consent(self):
        """Record GDPR consent"""
        self.ensure_one()
        self.write({
            'gdpr_consent_given': True,
            'gdpr_consent_date': fields.Datetime.now(),
        })
        # Also update all communication preferences
        self.communication_preference_ids.action_confirm_gdpr_consent()

    def action_accept_privacy_policy(self):
        """Record privacy policy acceptance"""
        self.ensure_one()
        self.write({
            'privacy_policy_accepted': True,
            'privacy_policy_date': fields.Datetime.now(),
        })

    def get_communication_summary(self):
        """Get a summary of communication preferences"""
        self.ensure_one()
        
        summary = {
            'total_preferences': len(self.communication_preference_ids),
            'opted_in': len(self.communication_preference_ids.filtered('opted_in')),
            'opted_out': len(self.communication_preference_ids.filtered(lambda p: not p.opted_in)),
            'by_type': {},
            'by_category': {},
            'compliance_issues': len(self.communication_preference_ids.filtered(
                lambda p: p.compliance_status in ['needs_confirmation', 'non_compliant']
            )),
        }
        
        # Break down by communication type
        for comm_type in ['email', 'sms', 'mail', 'phone']:
            prefs = self.communication_preference_ids.filtered(lambda p: p.communication_type == comm_type)
            summary['by_type'][comm_type] = {
                'total': len(prefs),
                'opted_in': len(prefs.filtered('opted_in')),
            }
        
        # Break down by category
        for category in ['marketing', 'membership', 'events', 'education', 'fundraising', 'governance']:
            prefs = self.communication_preference_ids.filtered(lambda p: p.category == category)
            summary['by_category'][category] = {
                'total': len(prefs),
                'opted_in': len(prefs.filtered('opted_in')),
            }
        
        return summary

    # ========================================================================
    # OVERRIDE METHODS
    # ========================================================================

    @api.model
    def create(self, vals):
        """Override create to set up communication preferences for new members"""
        partner = super().create(vals)
        
        # Auto-create communication preferences for members with member_id
        if partner.member_id and not partner.communication_preference_ids:
            partner.create_communication_preferences()
        
        return partner

    def write(self, vals):
        """Override write to handle email changes"""
        result = super().write(vals)
        
        # Reset email bounces when email is updated
        if 'email' in vals:
            for partner in self:
                if partner.email and partner.email_bounce_count > 0:
                    partner.reset_email_bounces()
        
        return result