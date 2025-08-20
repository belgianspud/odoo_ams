# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ===== PRIVACY FLAGS =====
    legal_hold = fields.Boolean(
        string='Legal Hold',
        default=False,
        tracking=True,
        groups='ams_core_base.group_ams_admin',
        help="Records under legal hold cannot be deleted"
    )

    legal_hold_reason = fields.Text(
        string='Legal Hold Reason',
        groups='ams_core_base.group_ams_admin',
        help="Reason for legal hold"
    )

    legal_hold_date = fields.Date(
        string='Legal Hold Date',
        groups='ams_core_base.group_ams_admin',
        help="Date legal hold was placed"
    )

    # ===== PRIVACY CONSENT TRACKING =====
    consent_ids = fields.One2many(
        'ams.privacy.consent',
        'partner_id',
        string='Privacy Consents',
        help="All privacy consent records for this partner"
    )

    # ===== COMPUTED CONSENT STATUS =====
    marketing_consent_status = fields.Selection([
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('pending', 'Pending'),
    ], string='Marketing Consent Status', 
       compute='_compute_consent_status', 
       store=True,
       help="Current marketing consent status")

    directory_consent_status = fields.Selection([
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('pending', 'Pending'),
    ], string='Directory Consent Status', 
       compute='_compute_consent_status', 
       store=True,
       help="Current directory listing consent status")

    photo_consent_status = fields.Selection([
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('pending', 'Pending'),
    ], string='Photo Consent Status', 
       compute='_compute_consent_status', 
       store=True,
       help="Current photo usage consent status")

    data_sharing_consent_status = fields.Selection([
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('pending', 'Pending'),
    ], string='Data Sharing Consent Status', 
       compute='_compute_consent_status', 
       store=True,
       help="Current data sharing consent status")

    # ===== PRIVACY COMPLIANCE =====
    privacy_compliance_score = fields.Float(
        string='Privacy Compliance Score',
        compute='_compute_privacy_compliance_score',
        store=True,
        help="Overall privacy compliance score (0-100)"
    )

    consents_up_to_date = fields.Boolean(
        string='Consents Up to Date',
        compute='_compute_privacy_compliance_score',
        store=True,
        help="Whether all consents are current and valid"
    )

    next_consent_expiry = fields.Date(
        string='Next Consent Expiry',
        compute='_compute_next_consent_expiry',
        store=True,
        help="Date of next consent expiry"
    )

    # ===== DATA RETENTION =====
    data_retention_eligible = fields.Boolean(
        string='Data Retention Eligible',
        compute='_compute_data_retention_eligible',
        help="Whether this record is eligible for data retention deletion"
    )

    retention_hold_reason = fields.Text(
        string='Retention Hold Reason',
        help="Reason why record is exempt from retention deletion"
    )

    # ===== GDPR RIGHTS TRACKING =====
    last_data_export = fields.Datetime(
        string='Last Data Export',
        readonly=True,
        help="When member data was last exported (GDPR Article 20)"
    )

    data_export_count = fields.Integer(
        string='Data Export Count',
        default=0,
        readonly=True,
        help="Number of times member data has been exported"
    )

    rectification_requests = fields.Integer(
        string='Rectification Requests',
        default=0,
        help="Number of data rectification requests (GDPR Article 16)"
    )

    erasure_requests = fields.Integer(
        string='Erasure Requests',
        default=0,
        help="Number of data erasure requests (GDPR Article 17)"
    )

    # ===== COMMUNICATION PREFERENCES =====
    communication_consent_ids = fields.One2many(
        'ams.privacy.consent',
        'partner_id',
        domain=[('consent_type_id.category', '=', 'communications')],
        string='Communication Consents',
        help="Communication-specific consent records"
    )

    opt_out_all_communications = fields.Boolean(
        string='Opt Out All Communications',
        default=False,
        tracking=True,
        help="Member has opted out of all communications"
    )

    opt_out_date = fields.Datetime(
        string='Opt Out Date',
        tracking=True,
        help="When member opted out of all communications"
    )

    @api.depends('consent_ids.status', 'consent_ids.consent_type_id')
    def _compute_consent_status(self):
        """Compute consent status for each type"""
        for partner in self:
            # Get latest consent for each type
            marketing_consent = partner._get_latest_consent('marketing')
            directory_consent = partner._get_latest_consent('directory')
            photo_consent = partner._get_latest_consent('photos')
            data_sharing_consent = partner._get_latest_consent('data_sharing')
            
            partner.marketing_consent_status = marketing_consent.status if marketing_consent else 'pending'
            partner.directory_consent_status = directory_consent.status if directory_consent else 'pending'
            partner.photo_consent_status = photo_consent.status if photo_consent else 'pending'
            partner.data_sharing_consent_status = data_sharing_consent.status if data_sharing_consent else 'pending'

    @api.depends('consent_ids.status', 'consent_ids.consent_given', 'consent_ids.is_expired')
    def _compute_privacy_compliance_score(self):
        """Compute overall privacy compliance score"""
        for partner in self:
            if not partner.is_member:
                partner.privacy_compliance_score = 100.0
                partner.consents_up_to_date = True
                continue
            
            total_weight = 0
            compliance_points = 0
            all_up_to_date = True
            
            # Required consent types for members
            required_consent_types = partner._get_required_consent_types()
            
            for consent_type in required_consent_types:
                weight = consent_type.get('weight', 1.0)
                total_weight += weight
                
                latest_consent = partner._get_latest_consent(consent_type['category'])
                
                if latest_consent:
                    if latest_consent.status == 'active':
                        compliance_points += weight
                    elif latest_consent.status in ['expired', 'withdrawn']:
                        all_up_to_date = False
                    # Denied consent still counts as compliant (they made a choice)
                    elif latest_consent.status == 'denied':
                        compliance_points += weight * 0.8  # Slightly lower score
                else:
                    all_up_to_date = False
            
            if total_weight > 0:
                partner.privacy_compliance_score = (compliance_points / total_weight) * 100
            else:
                partner.privacy_compliance_score = 100.0
            
            partner.consents_up_to_date = all_up_to_date

    @api.depends('consent_ids.expiry_date', 'consent_ids.status')
    def _compute_next_consent_expiry(self):
        """Compute next consent expiry date"""
        for partner in self:
            active_consents = partner.consent_ids.filtered(
                lambda c: c.status == 'active' and c.expiry_date
            )
            
            if active_consents:
                partner.next_consent_expiry = min(active_consents.mapped('expiry_date'))
            else:
                partner.next_consent_expiry = False

    def _compute_data_retention_eligible(self):
        """Compute if record is eligible for data retention deletion"""
        for partner in self:
            # Check basic eligibility
            eligible = True
            
            # Exempt if under legal hold
            if partner.legal_hold:
                eligible = False
            
            # Exempt if active member
            if partner.is_member and partner.member_status == 'active':
                eligible = False
            
            # Exempt if has recent activity
            if partner.write_date and partner.write_date > fields.Datetime.now().replace(year=fields.Datetime.now().year - 1):
                eligible = False
            
            # Exempt if has retention hold reason
            if partner.retention_hold_reason:
                eligible = False
            
            partner.data_retention_eligible = eligible

    def _get_latest_consent(self, category):
        """Get latest consent record for a category"""
        self.ensure_one()
        consent = self.consent_ids.filtered(
            lambda c: c.consent_type_id.category == category
        ).sorted('consent_date', reverse=True)
        return consent[0] if consent else None

    def _get_required_consent_types(self):
        """Get required consent types for this partner"""
        # Basic required consents for all members
        required_types = [
            {'category': 'marketing', 'weight': 1.0},
            {'category': 'communications', 'weight': 1.0},
            {'category': 'directory', 'weight': 0.8},
        ]
        
        # Add photo consent if member participates in events
        if self.is_member:
            required_types.append({'category': 'photos', 'weight': 0.6})
        
        # Add data sharing consent for corporate members
        if self.is_company:
            required_types.append({'category': 'data_sharing', 'weight': 0.8})
        
        return required_types

    def action_view_consents(self):
        """Action to view all consents for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Privacy Consents: {self.name}',
            'res_model': 'ams.privacy.consent',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_grant_consent(self):
        """Action to grant consent via wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Grant Consent: {self.name}',
            'res_model': 'ams.privacy.consent.grant.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def action_withdraw_consent(self):
        """Action to withdraw consent via wizard"""
        self.ensure_one()
        active_consents = self.consent_ids.filtered(lambda c: c.status == 'active')
        
        if not active_consents:
            raise UserError(_("No active consents to withdraw for %s") % self.name)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Withdraw Consent: {self.name}',
            'res_model': 'ams.privacy.consent.withdraw.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_ids': [(6, 0, [self.id])]},
        }

    def action_export_data(self):
        """Action to export member data (GDPR Article 20)"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Export Data: {self.name}',
            'res_model': 'ams.privacy.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_ids': [(6, 0, [self.id])]},
        }

    def action_place_legal_hold(self):
        """Place legal hold on record"""
        self.ensure_one()
        
        if not self.env.user.has_group('ams_core_base.group_ams_admin'):
            raise UserError(_("Only administrators can place legal holds"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Legal Hold: {self.name}',
            'res_model': 'ams.privacy.legal.hold.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def action_remove_legal_hold(self):
        """Remove legal hold from record"""
        self.ensure_one()
        
        if not self.env.user.has_group('ams_core_base.group_ams_admin'):
            raise UserError(_("Only administrators can remove legal holds"))
        
        if not self.legal_hold:
            raise UserError(_("No legal hold to remove for %s") % self.name)
        
        self.write({
            'legal_hold': False,
            'legal_hold_reason': False,
            'legal_hold_date': False,
        })
        
        # Log the removal
        self.env['ams.audit.log'].create({
            'model_name': self._name,
            'record_id': self.id,
            'operation': 'write',
            'description': 'Legal hold removed',
            'user_id': self.env.user.id,
            'data': str({'legal_hold_removed': True}),
            'related_partner_id': self.id,
            'privacy_impact': True,
            'risk_level': 'high',
        })
        
        return True

    def action_opt_out_all(self):
        """Opt out of all communications"""
        self.ensure_one()
        
        self.write({
            'opt_out_all_communications': True,
            'opt_out_date': fields.Datetime.now(),
        })
        
        # Withdraw all active communication consents
        comm_consents = self.consent_ids.filtered(
            lambda c: c.status == 'active' and c.consent_type_id.category in ['marketing', 'communications']
        )
        
        for consent in comm_consents:
            consent.write({
                'consent_given': False,
                'withdrawal_date': fields.Datetime.now(),
                'withdrawal_reason': 'Opted out of all communications',
                'withdrawal_method': 'admin',
            })
        
        # Log the opt-out
        self.env['ams.audit.log'].create({
            'model_name': self._name,
            'record_id': self.id,
            'operation': 'write',
            'description': 'Opted out of all communications',
            'user_id': self.env.user.id,
            'data': str({'opted_out_all': True, 'consents_withdrawn': len(comm_consents)}),
            'related_partner_id': self.id,
            'privacy_impact': True,
        })
        
        return True

    def action_privacy_dashboard(self):
        """Open privacy dashboard for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Privacy Dashboard: {self.name}',
            'res_model': 'ams.privacy.dashboard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def check_consent_for_communication(self, communication_type='marketing'):
        """Check if partner has valid consent for communication type"""
        self.ensure_one()
        
        # Check global opt-out
        if self.opt_out_all_communications:
            return False
        
        # Get latest consent for communication type
        latest_consent = self._get_latest_consent(communication_type)
        
        if not latest_consent:
            return False
        
        return latest_consent.status == 'active'

    def enforce_communication_consent(self, communication_type='marketing'):
        """Enforce communication consent - raise error if not valid"""
        self.ensure_one()
        
        if not self.check_consent_for_communication(communication_type):
            raise UserError(
                _("Cannot send %s communications to %s - no valid consent") % 
                (communication_type, self.name)
            )
        
        return True

    @api.model
    def get_partners_with_consent(self, consent_type='marketing', status='active'):
        """Get partners with specific consent type and status"""
        partners = self.search([('is_member', '=', True)])
        valid_partners = []
        
        for partner in partners:
            consent = partner._get_latest_consent(consent_type)
            if consent and consent.status == status:
                valid_partners.append(partner.id)
        
        return self.browse(valid_partners)

    @api.model
    def update_legacy_consent_fields(self):
        """Migrate legacy consent fields to new consent records"""
        # This method helps migrate from the basic consent fields in member_profile
        # to the new granular consent tracking system
        
        partners_to_migrate = self.search([
            ('is_member', '=', True),
            ('consent_ids', '=', False),  # No consent records yet
        ])
        
        consent_type_mapping = {
            'marketing': 'marketing_consent',
            'directory': 'directory_listing_consent', 
            'photos': 'photo_permission',
            'data_sharing': 'data_sharing_consent',
        }
        
        migrated_count = 0
        
        for partner in partners_to_migrate:
            if not partner.member_profile_id:
                continue
            
            profile = partner.member_profile_id[0]
            
            for consent_category, profile_field in consent_type_mapping.items():
                if hasattr(profile, profile_field):
                    consent_given = getattr(profile, profile_field, False)
                    
                    # Find consent type
                    consent_type = self.env['ams.privacy.consent.type'].search([
                        ('category', '=', consent_category)
                    ], limit=1)
                    
                    if consent_type:
                        # Create consent record
                        self.env['ams.privacy.consent'].create({
                            'partner_id': partner.id,
                            'consent_type_id': consent_type.id,
                            'consent_given': consent_given,
                            'consent_method': 'import',
                            'legal_basis': 'consent',
                            'purpose': f'Migrated from legacy {profile_field} field',
                        })
            
            migrated_count += 1
        
        _logger.info(f"Migrated consent data for {migrated_count} members")
        return migrated_count

    @api.constrains('legal_hold', 'legal_hold_reason')
    def _check_legal_hold(self):
        """Validate legal hold requirements"""
        for partner in self:
            if partner.legal_hold and not partner.legal_hold_reason:
                raise ValidationError(_("Legal hold reason is required when placing a legal hold"))

    def write(self, vals):
        """Override write to track privacy-related changes"""
        # Track legal hold changes
        if 'legal_hold' in vals:
            for partner in self:
                if vals['legal_hold'] != partner.legal_hold:
                    self.env['ams.audit.log'].create({
                        'model_name': self._name,
                        'record_id': partner.id,
                        'operation': 'write',
                        'description': f'Legal hold {"placed" if vals["legal_hold"] else "removed"}',
                        'user_id': self.env.user.id,
                        'data': str({
                            'legal_hold': vals['legal_hold'],
                            'reason': vals.get('legal_hold_reason', ''),
                        }),
                        'related_partner_id': partner.id,
                        'privacy_impact': True,
                        'risk_level': 'high',
                    })
        
        # Track opt-out changes
        if 'opt_out_all_communications' in vals:
            for partner in self:
                if vals['opt_out_all_communications'] != partner.opt_out_all_communications:
                    self.env['ams.audit.log'].create({
                        'model_name': self._name,
                        'record_id': partner.id,
                        'operation': 'write',
                        'description': f'Communication opt-out {"enabled" if vals["opt_out_all_communications"] else "disabled"}',
                        'user_id': self.env.user.id,
                        'data': str({'opt_out_all': vals['opt_out_all_communications']}),
                        'related_partner_id': partner.id,
                        'privacy_impact': True,
                    })
        
        return super(ResPartner, self).write(vals)

    def unlink(self):
        """Override unlink to check privacy constraints"""
        for partner in self:
            # Check legal hold
            if partner.legal_hold:
                raise UserError(
                    _("Cannot delete partner %s - record is under legal hold: %s") % 
                    (partner.name, partner.legal_hold_reason)
                )
            
            # Log deletion attempt
            self.env['ams.audit.log'].create({
                'model_name': self._name,
                'record_id': partner.id,
                'operation': 'unlink',
                'description': f'Partner deletion: {partner.name}',
                'user_id': self.env.user.id,
                'data': str({
                    'partner_name': partner.name,
                    'member_id': partner.member_id,
                    'member_status': partner.member_status,
                }),
                'related_partner_id': partner.id,
                'privacy_impact': True,
                'risk_level': 'critical',
            })
        
        return super(ResPartner, self).unlink()