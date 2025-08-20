# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class PrivacyConsent(models.Model):
    _name = 'ams.privacy.consent'
    _description = 'Privacy Consent Records'
    _order = 'partner_id, consent_type_id, consent_date desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ===== CORE FIELDS =====
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help="Partner this consent record applies to"
    )

    consent_type_id = fields.Many2one(
        'ams.privacy.consent.type',
        string='Consent Type',
        required=True,
        tracking=True,
        help="Type of consent being tracked"
    )

    # ===== CONSENT STATUS =====
    consent_given = fields.Boolean(
        string='Consent Given',
        default=False,
        tracking=True,
        help="Whether consent has been given"
    )

    consent_date = fields.Datetime(
        string='Consent Date',
        default=fields.Datetime.now,
        tracking=True,
        help="When consent was given or withdrawn"
    )

    consent_method = fields.Selection([
        ('website', 'Website Form'),
        ('email', 'Email Response'),
        ('phone', 'Phone Call'),
        ('mail', 'Physical Mail'),
        ('in_person', 'In Person'),
        ('import', 'Data Import'),
        ('admin', 'Administrative'),
        ('auto', 'Automatic'),
    ], string='Consent Method', required=True, default='website',
       tracking=True, help="How consent was obtained")

    # ===== EXPIRATION =====
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help="When this consent expires (if applicable)"
    )

    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_is_expired',
        store=True,
        help="Whether this consent has expired"
    )

    auto_renew = fields.Boolean(
        string='Auto Renew',
        default=False,
        help="Automatically renew consent before expiry"
    )

    # ===== LEGAL BASIS =====
    legal_basis = fields.Selection([
        ('consent', 'Consent'),
        ('contract', 'Contract'),
        ('legal_obligation', 'Legal Obligation'),
        ('vital_interests', 'Vital Interests'),
        ('public_task', 'Public Task'),
        ('legitimate_interests', 'Legitimate Interests'),
    ], string='Legal Basis', required=True, default='consent',
       tracking=True, help="GDPR legal basis for processing")

    # ===== DETAILED INFORMATION =====
    purpose = fields.Text(
        string='Purpose',
        help="Specific purpose for which consent is given"
    )

    data_categories = fields.Text(
        string='Data Categories',
        help="Categories of personal data covered by this consent"
    )

    processing_activities = fields.Text(
        string='Processing Activities',
        help="Specific processing activities covered"
    )

    third_parties = fields.Text(
        string='Third Parties',
        help="Third parties who may receive data under this consent"
    )

    # ===== WITHDRAWAL =====
    can_withdraw = fields.Boolean(
        string='Can Withdraw',
        default=True,
        help="Whether this consent can be withdrawn"
    )

    withdrawal_date = fields.Datetime(
        string='Withdrawal Date',
        tracking=True,
        help="When consent was withdrawn"
    )

    withdrawal_reason = fields.Text(
        string='Withdrawal Reason',
        help="Reason for withdrawing consent"
    )

    withdrawal_method = fields.Selection([
        ('website', 'Website'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mail', 'Mail'),
        ('in_person', 'In Person'),
    ], string='Withdrawal Method', help="How consent was withdrawn")

    # ===== VERIFICATION =====
    verified = fields.Boolean(
        string='Verified',
        default=False,
        help="Whether consent has been verified"
    )

    verification_date = fields.Datetime(
        string='Verification Date',
        help="When consent was last verified"
    )

    verification_method = fields.Text(
        string='Verification Method',
        help="How consent was verified"
    )

    # ===== AUDIT TRAIL =====
    ip_address = fields.Char(
        string='IP Address',
        help="IP address when consent was given"
    )

    user_agent = fields.Text(
        string='User Agent',
        help="Browser/device information when consent was given"
    )

    source_url = fields.Char(
        string='Source URL',
        help="URL where consent was given"
    )

    # ===== RELATED RECORDS =====
    parent_consent_id = fields.Many2one(
        'ams.privacy.consent',
        string='Parent Consent',
        help="Parent consent record (for renewals/updates)"
    )

    child_consent_ids = fields.One2many(
        'ams.privacy.consent',
        'parent_consent_id',
        string='Child Consents',
        help="Related consent records (renewals/updates)"
    )

    # ===== COMPUTED FIELDS =====
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help="Human-readable description of this consent record"
    )

    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('pending', 'Pending'),
    ], string='Status', compute='_compute_status', store=True)

    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
        help="Number of days until consent expires"
    )

    # ===== METADATA =====
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this consent record"
    )

    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        """Compute if consent has expired"""
        today = fields.Date.today()
        for consent in self:
            consent.is_expired = (
                consent.expiry_date and 
                consent.expiry_date < today
            )

    @api.depends('partner_id', 'consent_type_id', 'consent_given')
    def _compute_display_name(self):
        """Compute display name for consent record"""
        for consent in self:
            if consent.partner_id and consent.consent_type_id:
                status = "Granted" if consent.consent_given else "Denied"
                consent.display_name = f"{consent.partner_id.name} - {consent.consent_type_id.name} ({status})"
            else:
                consent.display_name = "New Consent Record"

    @api.depends('consent_given', 'is_expired', 'withdrawal_date')
    def _compute_status(self):
        """Compute overall consent status"""
        for consent in self:
            if consent.withdrawal_date:
                consent.status = 'withdrawn'
            elif not consent.consent_given:
                consent.status = 'pending'
            elif consent.is_expired:
                consent.status = 'expired'
            else:
                consent.status = 'active'

    @api.depends('expiry_date')
    def _compute_days_until_expiry(self):
        """Compute days until expiry"""
        today = fields.Date.today()
        for consent in self:
            if consent.expiry_date:
                delta = consent.expiry_date - today
                consent.days_until_expiry = delta.days
            else:
                consent.days_until_expiry = 0

    @api.constrains('consent_date', 'expiry_date')
    def _check_dates(self):
        """Validate date logic"""
        for consent in self:
            if consent.expiry_date and consent.consent_date:
                consent_date = fields.Date.from_string(consent.consent_date.date())
                if consent.expiry_date <= consent_date:
                    raise ValidationError(_("Expiry date must be after consent date"))

    @api.constrains('withdrawal_date', 'consent_date')
    def _check_withdrawal_date(self):
        """Validate withdrawal date"""
        for consent in self:
            if consent.withdrawal_date and consent.consent_date:
                if consent.withdrawal_date < consent.consent_date:
                    raise ValidationError(_("Withdrawal date cannot be before consent date"))

    def action_grant_consent(self):
        """Grant consent"""
        self.ensure_one()
        if self.consent_given:
            raise UserError(_("Consent has already been granted"))
        
        self.write({
            'consent_given': True,
            'consent_date': fields.Datetime.now(),
            'withdrawal_date': False,
            'withdrawal_reason': False,
        })
        
        # Log audit trail
        self._log_consent_change('granted', 'Consent granted')
        
        return True

    def action_withdraw_consent(self):
        """Withdraw consent"""
        self.ensure_one()
        if not self.consent_given:
            raise UserError(_("Cannot withdraw consent that was not given"))
        
        if not self.can_withdraw:
            raise UserError(_("This consent cannot be withdrawn"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Withdraw Consent'),
            'res_model': 'ams.privacy.consent.withdraw.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_consent_id': self.id},
        }

    def action_renew_consent(self):
        """Renew consent (create new record)"""
        self.ensure_one()
        
        # Create new consent record
        new_consent = self.create({
            'partner_id': self.partner_id.id,
            'consent_type_id': self.consent_type_id.id,
            'consent_given': True,
            'consent_method': 'admin',
            'legal_basis': self.legal_basis,
            'purpose': self.purpose,
            'data_categories': self.data_categories,
            'processing_activities': self.processing_activities,
            'parent_consent_id': self.id,
            'expiry_date': self._calculate_new_expiry_date(),
        })
        
        # Log audit trail
        self._log_consent_change('renewed', f'Consent renewed with new record ID: {new_consent.id}')
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed Consent'),
            'res_model': 'ams.privacy.consent',
            'view_mode': 'form',
            'res_id': new_consent.id,
        }

    def action_verify_consent(self):
        """Verify consent"""
        self.ensure_one()
        self.write({
            'verified': True,
            'verification_date': fields.Datetime.now(),
            'verification_method': 'Manual verification by administrator',
        })
        
        self._log_consent_change('verified', 'Consent verified by administrator')
        
        return True

    def _calculate_new_expiry_date(self):
        """Calculate expiry date for renewed consent"""
        if self.consent_type_id.default_expiry_days:
            return fields.Date.today() + timedelta(days=self.consent_type_id.default_expiry_days)
        return False

    def _log_consent_change(self, operation, description):
        """Log consent changes to audit trail"""
        try:
            self.env['ams.audit.log'].sudo().create({
                'model_name': self._name,
                'record_id': self.id,
                'operation': operation,
                'description': description,
                'user_id': self.env.user.id,
                'data': str({
                    'partner': self.partner_id.name,
                    'consent_type': self.consent_type_id.name,
                    'consent_given': self.consent_given,
                    'legal_basis': self.legal_basis,
                }),
                'timestamp': fields.Datetime.now(),
                'related_partner_id': self.partner_id.id,
                'privacy_impact': True,
                'is_sensitive': True,
            })
        except Exception as e:
            _logger.warning(f"Failed to log consent audit trail: {e}")

    @api.model
    def check_expiring_consents(self, days_ahead=30):
        """Check for consents expiring soon"""
        expiry_threshold = fields.Date.today() + timedelta(days=days_ahead)
        expiring_consents = self.search([
            ('status', '=', 'active'),
            ('expiry_date', '<=', expiry_threshold),
            ('expiry_date', '>', fields.Date.today()),
        ])
        
        for consent in expiring_consents:
            if consent.auto_renew:
                consent.action_renew_consent()
            else:
                # Create activity for manual review
                consent.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=consent.expiry_date,
                    summary=f'Consent expiring: {consent.consent_type_id.name}',
                    note=f'Consent for {consent.partner_id.name} expires on {consent.expiry_date}',
                    user_id=self.env.ref('ams_core_base.group_ams_privacy_officer').users[0].id,
                )
        
        return expiring_consents

    @api.model
    def cleanup_expired_consents(self, days_expired=365):
        """Clean up very old expired consents"""
        cutoff_date = fields.Date.today() - timedelta(days=days_expired)
        old_consents = self.search([
            ('status', '=', 'expired'),
            ('expiry_date', '<', cutoff_date),
        ])
        
        count = len(old_consents)
        if old_consents:
            old_consents.unlink()
            _logger.info(f"Cleaned up {count} expired consent records")
        
        return count

    def name_get(self):
        """Override name_get for better display"""
        result = []
        for consent in self:
            name = f"{consent.partner_id.name} - {consent.consent_type_id.name}"
            if consent.status:
                name += f" ({consent.status.title()})"
            result.append((consent.id, name))
        return result


class PrivacyConsentType(models.Model):
    _name = 'ams.privacy.consent.type'
    _description = 'Privacy Consent Types'
    _order = 'sequence, name'
    _rec_name = 'name'

    # ===== BASIC INFORMATION =====
    name = fields.Char(
        string='Consent Type',
        required=True,
        translate=True,
        help="Name of the consent type"
    )

    code = fields.Char(
        string='Code',
        help="Short code for the consent type"
    )

    description = fields.Text(
        string='Description',
        translate=True,
        help="Detailed description of what this consent covers"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order for displaying consent types"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive this consent type"
    )

    # ===== CLASSIFICATION =====
    category = fields.Selection([
        ('marketing', 'Marketing'),
        ('communications', 'Communications'),
        ('directory', 'Directory'),
        ('photos', 'Photos/Media'),
        ('research', 'Research'),
        ('data_sharing', 'Data Sharing'),
        ('profiling', 'Profiling'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')

    # ===== EXPIRY SETTINGS =====
    has_expiry = fields.Boolean(
        string='Has Expiry',
        default=True,
        help="Whether this consent type expires"
    )

    default_expiry_days = fields.Integer(
        string='Default Expiry (Days)',
        default=365,
        help="Default number of days until expiry"
    )

    # ===== LEGAL BASIS =====
    default_legal_basis = fields.Selection([
        ('consent', 'Consent'),
        ('contract', 'Contract'),
        ('legal_obligation', 'Legal Obligation'),
        ('vital_interests', 'Vital Interests'),
        ('public_task', 'Public Task'),
        ('legitimate_interests', 'Legitimate Interests'),
    ], string='Default Legal Basis', default='consent')

    # ===== REQUIREMENTS =====
    requires_explicit_consent = fields.Boolean(
        string='Requires Explicit Consent',
        default=True,
        help="Whether explicit consent is required"
    )

    can_be_withdrawn = fields.Boolean(
        string='Can Be Withdrawn',
        default=True,
        help="Whether this consent can be withdrawn"
    )

    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help="Whether consent requires verification"
    )

    # ===== STATISTICS =====
    consent_count = fields.Integer(
        string='Consent Count',
        compute='_compute_consent_count',
        help="Number of consent records of this type"
    )

    # ===== METADATA =====
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.depends('name')  # This will be updated when consent records are created
    def _compute_consent_count(self):
        """Compute number of consent records"""
        for consent_type in self:
            consent_type.consent_count = self.env['ams.privacy.consent'].search_count([
                ('consent_type_id', '=', consent_type.id)
            ])

    def action_view_consents(self):
        """View all consents of this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Consents: {self.name}',
            'res_model': 'ams.privacy.consent',
            'view_mode': 'tree,form',
            'domain': [('consent_type_id', '=', self.id)],
            'context': {'default_consent_type_id': self.id},
        }