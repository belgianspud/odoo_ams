# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerCommunication(models.Model):
    """Communication-specific extensions to res.partner"""
    _inherit = 'res.partner'

    # ========================================================================
    # COMMUNICATION PREFERENCE FIELDS
    # ========================================================================
    
    communication_preference_ids = fields.One2many(
        'ams.communication.preference',
        'partner_id',
        string="Communication Preferences",
        help="Detailed communication preferences by type and category"
    )
    
    # ========================================================================
    # GLOBAL COMMUNICATION SETTINGS
    # ========================================================================
    
    communication_opt_out = fields.Boolean(
        string="Global Communication Opt-out",
        default=False,
        help="If checked, member has opted out of ALL communications"
    )
    
    preferred_communication_method = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'), 
        ('mail', 'Physical Mail'),
        ('phone', 'Phone'),
        ('portal', 'Member Portal')
    ], string="Preferred Communication Method", default='email')
    
    communication_frequency = fields.Selection([
        ('immediate', 'Immediate'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Summary'),
        ('quarterly', 'Quarterly Only')
    ], string="Communication Frequency", default='immediate')
    
    preferred_language = fields.Selection([
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('other', 'Other')
    ], string="Preferred Language", default='en')
    
    # ========================================================================
    # DO NOT CONTACT FLAGS
    # ========================================================================
    
    do_not_email = fields.Boolean(
        string="Do Not Email",
        default=False,
        help="Do not send emails to this contact"
    )
    
    do_not_sms = fields.Boolean(
        string="Do Not SMS", 
        default=False,
        help="Do not send SMS messages to this contact"
    )
    
    do_not_mail = fields.Boolean(
        string="Do Not Mail",
        default=False, 
        help="Do not send physical mail to this contact"
    )
    
    do_not_call = fields.Boolean(
        string="Do Not Call",
        default=False,
        help="Do not make phone calls to this contact"
    )
    
    # ========================================================================
    # GDPR AND PRIVACY FIELDS  
    # ========================================================================
    
    gdpr_consent_given = fields.Boolean(
        string="GDPR Consent Given",
        default=False,
        tracking=True,
        help="Member has given explicit GDPR consent"
    )
    
    gdpr_consent_date = fields.Datetime(
        string="GDPR Consent Date",
        help="When GDPR consent was obtained"
    )
    
    privacy_policy_accepted = fields.Boolean(
        string="Privacy Policy Accepted",
        default=False,
        tracking=True,
        help="Member has accepted current privacy policy"
    )
    
    privacy_policy_date = fields.Datetime(
        string="Privacy Policy Date", 
        help="When privacy policy was accepted"
    )
    
    # ========================================================================
    # EMAIL BOUNCE TRACKING
    # ========================================================================
    
    email_bounce_count = fields.Integer(
        string="Email Bounce Count",
        default=0,
        help="Number of consecutive email bounces"
    )
    
    last_email_bounce_date = fields.Datetime(
        string="Last Email Bounce",
        help="Date of most recent email bounce"
    )
    
    # ========================================================================
    # COMPUTED COMMUNICATION FIELDS
    # ========================================================================
    
    email_opt_in_count = fields.Integer(
        string="Email Opt-ins",
        compute='_compute_communication_stats',
        store=True,
        help="Number of email categories opted into"
    )
    
    sms_opt_in_count = fields.Integer(
        string="SMS Opt-ins", 
        compute='_compute_communication_stats',
        store=True,
        help="Number of SMS categories opted into"
    )
    
    total_opt_ins = fields.Integer(
        string="Total Opt-ins",
        compute='_compute_communication_stats', 
        store=True,
        help="Total number of communication preferences opted into"
    )
    
    communication_compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('needs_attention', 'Needs Attention'),
        ('non_compliant', 'Non-compliant')
    ], string="Compliance Status",
       compute='_compute_compliance_status',
       store=True)
    
    # ========================================================================
    # PERMISSION COMPUTED FIELDS
    # ========================================================================
    
    can_email = fields.Boolean(
        string="Can Email",
        compute='_compute_communication_permissions',
        help="Whether we can send emails to this contact"
    )
    
    can_sms = fields.Boolean(
        string="Can SMS",
        compute='_compute_communication_permissions', 
        help="Whether we can send SMS to this contact"
    )
    
    can_mail = fields.Boolean(
        string="Can Mail",
        compute='_compute_communication_permissions',
        help="Whether we can send physical mail to this contact"
    )
    
    can_call = fields.Boolean(
        string="Can Call",
        compute='_compute_communication_permissions',
        help="Whether we can make phone calls to this contact"
    )

    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    @api.depends('communication_preference_ids.opted_in', 'communication_preference_ids.communication_type')
    def _compute_communication_stats(self):
        """Compute communication preference statistics"""
        for partner in self:
            prefs = partner.communication_preference_ids.filtered('opted_in')
            partner.email_opt_in_count = len(prefs.filtered(lambda p: p.communication_type == 'email'))
            partner.sms_opt_in_count = len(prefs.filtered(lambda p: p.communication_type == 'sms'))
            partner.total_opt_ins = len(prefs)
    
    @api.depends('communication_preference_ids.compliance_status', 'gdpr_consent_given')
    def _compute_compliance_status(self):
        """Compute overall communication compliance status"""
        for partner in self:
            prefs = partner.communication_preference_ids
            if not prefs:
                partner.communication_compliance_status = 'needs_attention'
                continue
                
            non_compliant = prefs.filtered(lambda p: p.compliance_status == 'non_compliant')
            needs_confirmation = prefs.filtered(lambda p: p.compliance_status == 'needs_confirmation')
            
            if non_compliant:
                partner.communication_compliance_status = 'non_compliant'
            elif needs_confirmation:
                partner.communication_compliance_status = 'needs_attention'  
            else:
                partner.communication_compliance_status = 'compliant'
    
    @api.depends('communication_opt_out', 'do_not_email', 'do_not_sms', 'do_not_mail', 'do_not_call', 'email_bounce_count')
    def _compute_communication_permissions(self):
        """Compute what communication methods are allowed"""
        for partner in self:
            if partner.communication_opt_out:
                partner.can_email = False
                partner.can_sms = False
                partner.can_mail = False
                partner.can_call = False
            else:
                partner.can_email = not partner.do_not_email and partner.email_bounce_count < 5
                partner.can_sms = not partner.do_not_sms
                partner.can_mail = not partner.do_not_mail  
                partner.can_call = not partner.do_not_call

    # ========================================================================
    # CONSTRAINT METHODS  
    # ========================================================================
    
    @api.constrains('email_bounce_count')
    def _check_bounce_count(self):
        """Auto-disable email for high bounce counts"""
        for partner in self:
            if partner.email_bounce_count >= 5 and not partner.do_not_email:
                partner.do_not_email = True

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('email')
    def _onchange_email_reset_bounces(self):
        """Reset bounce count when email address changes"""
        if self.email and self.email_bounce_count > 0:
            self.email_bounce_count = 0
            self.last_email_bounce_date = False
            self.do_not_email = False

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
        preference = self.communication_preference_ids.filtered(
            lambda p: p.communication_type == communication_type and p.category == category
        )
        
        if preference:
            return preference[0].opted_in
        else:
            # Default behavior if no specific preference exists
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
        
        # Opt out of all existing preferences
        self.communication_preference_ids.write({'opted_in': False})
        
        # Log the action
        self.message_post(
            body=_("Member opted out of all communications"),
            message_type='notification'
        )
    
    def action_global_opt_in(self):
        """Opt back into communications"""
        self.ensure_one()
        self.write({
            'communication_opt_out': False,
            'do_not_email': False,
            'do_not_sms': False,
            'do_not_mail': False,
            'do_not_call': False,
        })
        
        # Log the action
        self.message_post(
            body=_("Member opted back into communications"),
            message_type='notification'
        )
    
    def action_gdpr_consent(self):
        """Record GDPR consent"""
        self.ensure_one()
        self.write({
            'gdpr_consent_given': True,
            'gdpr_consent_date': fields.Datetime.now(),
        })
        
        # Log the action
        self.message_post(
            body=_("GDPR consent recorded"),
            message_type='notification'
        )
    
    def action_accept_privacy_policy(self):
        """Record privacy policy acceptance"""
        self.ensure_one()
        self.write({
            'privacy_policy_accepted': True,
            'privacy_policy_date': fields.Datetime.now(),
        })
        
        # Log the action  
        self.message_post(
            body=_("Privacy policy acceptance recorded"),
            message_type='notification'
        )
    
    def record_email_bounce(self):
        """Record an email bounce"""
        self.ensure_one()
        self.write({
            'email_bounce_count': self.email_bounce_count + 1,
            'last_email_bounce_date': fields.Datetime.now(),
        })
        
        # Auto-disable email if too many bounces
        if self.email_bounce_count >= 5:
            self.do_not_email = True
            self.message_post(
                body=_("Email automatically disabled due to %s consecutive bounces") % self.email_bounce_count,
                message_type='notification'
            )
    
    def reset_email_bounces(self):
        """Reset email bounce counter"""
        self.ensure_one()
        self.write({
            'email_bounce_count': 0,
            'last_email_bounce_date': False,
            'do_not_email': False,
        })
        
        self.message_post(
            body=_("Email bounce counter reset"),
            message_type='notification'
        )
    
    def get_communication_summary(self):
        """Get communication preferences summary"""
        self.ensure_one()
        prefs = self.communication_preference_ids
        
        summary = {
            'total_preferences': len(prefs),
            'opted_in': len(prefs.filtered('opted_in')),
            'opted_out': len(prefs.filtered(lambda p: not p.opted_in)),
            'by_type': {},
            'by_category': {},
        }
        
        # Group by communication type
        for comm_type in ['email', 'sms', 'mail', 'phone']:
            type_prefs = prefs.filtered(lambda p: p.communication_type == comm_type)
            summary['by_type'][comm_type] = {
                'opted_in': len(type_prefs.filtered('opted_in')),
                'total': len(type_prefs),
            }
        
        # Group by category
        for category in ['marketing', 'membership', 'events', 'education', 'fundraising', 'governance']:
            cat_prefs = prefs.filtered(lambda p: p.category == category)
            summary['by_category'][category] = {
                'opted_in': len(cat_prefs.filtered('opted_in')),
                'total': len(cat_prefs),
            }
        
        return summary

    # ========================================================================
    # OVERRIDE METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create communication preferences for new members"""
        partners = super().create(vals_list)
        
        for partner in partners:
            if partner.is_member and not partner.communication_preference_ids:
                try:
                    # Use with_context to avoid conflicts during data loading
                    self.env['ams.communication.preference'].with_context(
                        skip_constraint_validation=True
                    ).create_default_preferences(partner.id)
                except Exception as e:
                    # Log the error but don't fail partner creation
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(
                        f"Failed to create communication preferences for partner {partner.id}: {str(e)}"
                    )
        
        return partners
    
    def write(self, vals):
        """Handle communication-related field changes"""
        # Reset bounces when email changes
        if 'email' in vals:
            for partner in self:
                if partner.email != vals['email'] and partner.email_bounce_count > 0:
                    vals.update({
                        'email_bounce_count': 0,
                        'last_email_bounce_date': False,
                        'do_not_email': False,
                    })
        
        return super().write(vals)