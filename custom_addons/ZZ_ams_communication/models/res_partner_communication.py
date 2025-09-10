# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerCommunication(models.Model):
    """Extend res.partner with communication preference and tracking fields."""
    _inherit = 'res.partner'

    # ==========================================
    # RELATIONSHIP FIELDS
    # ==========================================

    communication_preference_ids = fields.One2many(
        'ams.communication.preference',
        'partner_id',
        string='Communication Preferences',
        help='Member communication preferences by type and category'
    )

    communication_log_ids = fields.One2many(
        'ams.communication.log',
        'partner_id',
        string='Communication History',
        help='Log of all communications sent to this member'
    )

    # ==========================================
    # COMPUTED PREFERENCE FIELDS (BY TYPE)
    # ==========================================

    email_opted_in = fields.Boolean(
        string='Email Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to any email communications'
    )

    sms_opted_in = fields.Boolean(
        string='SMS Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to any SMS communications'
    )

    mail_opted_in = fields.Boolean(
        string='Mail Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to any mail communications'
    )

    phone_opted_in = fields.Boolean(
        string='Phone Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to any phone communications'
    )

    # ==========================================
    # COMPUTED PREFERENCE FIELDS (BY CATEGORY)
    # ==========================================

    marketing_communications = fields.Boolean(
        string='Marketing Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to marketing communications'
    )

    membership_communications = fields.Boolean(
        string='Membership Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to membership communications'
    )

    event_communications = fields.Boolean(
        string='Event Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to event communications'
    )

    education_communications = fields.Boolean(
        string='Education Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to education communications'
    )

    committee_communications = fields.Boolean(
        string='Committee Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to committee communications'
    )

    fundraising_communications = fields.Boolean(
        string='Fundraising Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to fundraising communications'
    )

    emergency_communications = fields.Boolean(
        string='Emergency Communications',
        compute='_compute_communication_preferences',
        store=True,
        help='True if member is opted in to emergency communications'
    )

    # ==========================================
    # COMMUNICATION STATISTICS
    # ==========================================

    last_communication_date = fields.Datetime(
        string='Last Communication',
        compute='_compute_communication_stats',
        store=True,
        help='Date of most recent communication sent to this member'
    )

    total_communications_sent = fields.Integer(
        string='Total Communications',
        compute='_compute_communication_stats',
        store=True,
        help='Total number of communications sent to this member'
    )

    email_bounce_count = fields.Integer(
        string='Email Bounces',
        compute='_compute_communication_stats',
        store=True,
        help='Number of email bounces for this member'
    )

    last_email_open_date = fields.Datetime(
        string='Last Email Opened',
        compute='_compute_communication_stats',
        store=True,
        help='Date this member last opened an email'
    )

    communication_engagement_score = fields.Float(
        string='Engagement Score',
        compute='_compute_communication_stats',
        store=True,
        help='Average engagement score across all communications'
    )

    # ==========================================
    # PREFERENCE SUMMARY FIELDS
    # ==========================================

    has_communication_preferences = fields.Boolean(
        string='Has Preferences',
        compute='_compute_preference_summary',
        store=True,
        help='True if member has any communication preferences set'
    )

    preference_count = fields.Integer(
        string='Preference Count',
        compute='_compute_preference_summary',
        store=True,
        help='Number of communication preferences configured'
    )

    opted_in_count = fields.Integer(
        string='Opted In Count',
        compute='_compute_preference_summary',
        store=True,
        help='Number of communications member is opted in to receive'
    )

    opted_out_count = fields.Integer(
        string='Opted Out Count',
        compute='_compute_preference_summary',
        store=True,
        help='Number of communications member has opted out of'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('communication_preference_ids.opted_in', 'communication_preference_ids.communication_type', 'communication_preference_ids.category')
    def _compute_communication_preferences(self):
        """Compute communication preference summary fields."""
        for partner in self:
            prefs = partner.communication_preference_ids
            
            # Compute by communication type (any category opted in)
            partner.email_opted_in = any(
                p.opted_in for p in prefs if p.communication_type == 'email'
            )
            partner.sms_opted_in = any(
                p.opted_in for p in prefs if p.communication_type == 'sms'
            )
            partner.mail_opted_in = any(
                p.opted_in for p in prefs if p.communication_type == 'mail'
            )
            partner.phone_opted_in = any(
                p.opted_in for p in prefs if p.communication_type == 'phone'
            )
            
            # Compute by category (any communication type opted in)
            partner.marketing_communications = any(
                p.opted_in for p in prefs if p.category == 'marketing'
            )
            partner.membership_communications = any(
                p.opted_in for p in prefs if p.category == 'membership'
            )
            partner.event_communications = any(
                p.opted_in for p in prefs if p.category == 'events'
            )
            partner.education_communications = any(
                p.opted_in for p in prefs if p.category == 'education'
            )
            partner.committee_communications = any(
                p.opted_in for p in prefs if p.category == 'committee'
            )
            partner.fundraising_communications = any(
                p.opted_in for p in prefs if p.category == 'fundraising'
            )
            partner.emergency_communications = any(
                p.opted_in for p in prefs if p.category == 'emergency'
            )

    @api.depends('communication_log_ids.sent_date', 'communication_log_ids.delivery_status', 'communication_log_ids.engagement_score')
    def _compute_communication_stats(self):
        """Compute communication statistics."""
        for partner in self:
            logs = partner.communication_log_ids
            
            if logs:
                # Basic statistics
                partner.total_communications_sent = len(logs)
                partner.last_communication_date = max(logs.mapped('sent_date')) if logs.mapped('sent_date') else False
                
                # Email specific statistics
                email_logs = logs.filtered(lambda l: l.communication_type == 'email')
                partner.email_bounce_count = len(email_logs.filtered(lambda l: l.delivery_status == 'bounced'))
                
                # Find last email opened
                opened_emails = email_logs.filtered(lambda l: l.opened_date)
                partner.last_email_open_date = max(opened_emails.mapped('opened_date')) if opened_emails else False
                
                # Calculate average engagement score
                engagement_scores = logs.mapped('engagement_score')
                partner.communication_engagement_score = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0.0
            else:
                partner.total_communications_sent = 0
                partner.last_communication_date = False
                partner.email_bounce_count = 0
                partner.last_email_open_date = False
                partner.communication_engagement_score = 0.0

    @api.depends('communication_preference_ids.opted_in')
    def _compute_preference_summary(self):
        """Compute preference summary statistics."""
        for partner in self:
            prefs = partner.communication_preference_ids
            
            partner.has_communication_preferences = bool(prefs)
            partner.preference_count = len(prefs)
            partner.opted_in_count = len(prefs.filtered('opted_in'))
            partner.opted_out_count = len(prefs.filtered(lambda p: not p.opted_in))

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def can_send_communication(self, communication_type, category):
        """Check if communication can be sent to this partner."""
        self.ensure_one()
        
        # Emergency communications always allowed (business rule)
        if category == 'emergency':
            return True
            
        # Check for specific preference
        preference = self.communication_preference_ids.filtered(
            lambda p: p.communication_type == communication_type and p.category == category
        )
        
        if preference:
            return preference.opted_in
            
        # If no preference exists, use system defaults from preference model
        CommunicationPreference = self.env['ams.communication.preference']
        return CommunicationPreference._get_default_preference(communication_type, category)

    def get_communication_preference(self, communication_type, category):
        """Get specific communication preference for this partner."""
        self.ensure_one()
        return self.communication_preference_ids.filtered(
            lambda p: p.communication_type == communication_type and p.category == category
        )

    def set_communication_preference(self, communication_type, category, opted_in, 
                                   consent_source=None, consent_method=None, ip_address=None):
        """Set communication preference for this partner."""
        self.ensure_one()
        
        existing_pref = self.get_communication_preference(communication_type, category)
        
        if existing_pref:
            # Update existing preference
            existing_pref.update_preference(
                opted_in=opted_in,
                consent_source=consent_source,
                consent_method=consent_method,
                ip_address=ip_address
            )
            return existing_pref
        else:
            # Create new preference
            vals = {
                'partner_id': self.id,
                'communication_type': communication_type,
                'category': category,
                'opted_in': opted_in,
            }
            
            if consent_source:
                vals['consent_source'] = consent_source
            if consent_method:
                vals['consent_method'] = consent_method
            if ip_address:
                vals['ip_address'] = ip_address
                
            return self.env['ams.communication.preference'].create(vals)

    def create_default_communication_preferences(self):
        """Create default communication preferences for this partner."""
        self.ensure_one()
        CommunicationPreference = self.env['ams.communication.preference']
        return CommunicationPreference.create_default_preferences(self.id)

    def opt_out_all_marketing(self):
        """Opt this partner out of all marketing communications."""
        self.ensure_one()
        marketing_prefs = self.communication_preference_ids.filtered(
            lambda p: p.category == 'marketing'
        )
        
        for pref in marketing_prefs:
            pref.write({
                'opted_in': False,
                'date_updated': fields.Datetime.now(),
                'consent_method': 'staff_update',
                'consent_source': 'Bulk opt-out from marketing'
            })
            
        return True

    def log_communication(self, communication_type, category, subject=None, template_id=None, 
                         campaign_id=None, body_plain=None, body_html=None, external_message_id=None):
        """Log a communication sent to this partner."""
        self.ensure_one()
        
        return self.env['ams.communication.log'].log_communication(
            partner_id=self.id,
            communication_type=communication_type,
            category=category,
            subject=subject,
            template_id=template_id,
            campaign_id=campaign_id,
            body_plain=body_plain,
            body_html=body_html,
            external_message_id=external_message_id
        )

    # ==========================================
    # GDPR & COMPLIANCE METHODS
    # ==========================================

    def get_communication_data_export(self):
        """Export all communication data for GDPR compliance."""
        self.ensure_one()
        
        # Export preferences
        preferences_data = []
        for pref in self.communication_preference_ids:
            preferences_data.append({
                'communication_type': pref.communication_type,
                'category': pref.category,
                'opted_in': pref.opted_in,
                'date_updated': pref.date_updated.isoformat() if pref.date_updated else None,
                'consent_source': pref.consent_source,
                'consent_method': pref.consent_method,
                'ip_address': pref.ip_address,
            })
        
        # Export communication log (anonymized content)
        communications_data = []
        for log in self.communication_log_ids:
            communications_data.append({
                'communication_type': log.communication_type,
                'category': log.category,
                'subject': log.subject,
                'sent_date': log.sent_date.isoformat() if log.sent_date else None,
                'delivery_status': log.delivery_status,
                'opened': bool(log.opened_date),
                'clicked': bool(log.clicked_date),
                'engagement_score': log.engagement_score,
            })
        
        return {
            'partner_name': self.name,
            'export_date': fields.Datetime.now().isoformat(),
            'communication_preferences': preferences_data,
            'communication_history': communications_data,
            'statistics': {
                'total_communications': self.total_communications_sent,
                'email_bounces': self.email_bounce_count,
                'engagement_score': self.communication_engagement_score,
                'last_communication': self.last_communication_date.isoformat() if self.last_communication_date else None,
            }
        }

    def delete_communication_data(self):
        """Delete all communication data for right to be forgotten."""
        self.ensure_one()
        
        # Delete communication logs
        self.communication_log_ids.unlink()
        
        # Delete communication preferences
        self.communication_preference_ids.unlink()
        
        return True

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_communication_preferences(self):
        """Open communication preferences for this partner."""
        self.ensure_one()
        
        return {
            'name': f'Communication Preferences - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.communication.preference',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'create': True,
            }
        }

    def action_view_communication_log(self):
        """Open communication log for this partner.""" 
        self.ensure_one()
        
        return {
            'name': f'Communication History - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.communication.log',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'create': False,  # Logs should be created programmatically
            }
        }

    def action_create_default_preferences(self):
        """Action to create default communication preferences."""
        for partner in self:
            if not partner.communication_preference_ids:
                partner.create_default_communication_preferences()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # ==========================================
    # OVERRIDE LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set up communication preferences for members."""
        partners = super().create(vals_list)
        
        # Create default preferences for new members
        for partner in partners:
            if partner.member_type_id:  # Only for actual members
                partner.create_default_communication_preferences()
                
        return partners

    def write(self, vals):
        """Override write to handle communication-related updates."""
        result = super().write(vals)
        
        # If member type is being set for the first time, create preferences
        if vals.get('member_type_id'):
            for partner in self:
                if not partner.communication_preference_ids:
                    partner.create_default_communication_preferences()
        
        # Update email bounce tracking if email changed
        if 'email' in vals:
            # Reset bounce count when email address changes
            self.mapped('communication_log_ids').filtered(
                lambda l: l.communication_type == 'email' and l.delivery_status == 'bounced'
            ).write({'delivery_status': 'sent'})  # Reset bounced status
                    
        return result

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_preferred_communication_method(self, category='membership'):
        """Get the preferred communication method for this partner for a specific category."""
        self.ensure_one()
        
        # Check preferences in order of preference: email, sms, mail, phone
        preferences_order = ['email', 'sms', 'mail', 'phone']
        
        for comm_type in preferences_order:
            if self.can_send_communication(comm_type, category):
                # Also check if partner has the necessary contact info
                if comm_type == 'email' and self.email:
                    return 'email'
                elif comm_type == 'sms' and self.mobile:
                    return 'sms'
                elif comm_type == 'phone' and (self.phone or self.mobile):
                    return 'phone' 
                elif comm_type == 'mail' and self.street:
                    return 'mail'
                    
        return None

    def get_communication_summary(self):
        """Get a summary of communication preferences and activity."""
        self.ensure_one()
        
        return {
            'partner_name': self.name,
            'preferences': {
                'email': self.email_opted_in,
                'sms': self.sms_opted_in,
                'mail': self.mail_opted_in,
                'phone': self.phone_opted_in,
            },
            'categories': {
                'marketing': self.marketing_communications,
                'membership': self.membership_communications,
                'events': self.event_communications,
                'education': self.education_communications,
                'committee': self.committee_communications,
                'fundraising': self.fundraising_communications,
                'emergency': self.emergency_communications,
            },
            'statistics': {
                'total_sent': self.total_communications_sent,
                'email_bounces': self.email_bounce_count,
                'engagement_score': self.communication_engagement_score,
                'last_communication': self.last_communication_date,
                'last_email_opened': self.last_email_open_date,
            }
        }