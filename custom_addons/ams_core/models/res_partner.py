# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    # Core Member Fields
    member_id = fields.Char(
        string='Member ID',
        index=True,
        copy=False,
        help="Unique identifier for this member"
    )
    is_member = fields.Boolean(
        string='Is Member',
        default=False,
        help="Check this box if this contact is a member of the association"
    )
    member_since = fields.Date(
        string='Member Since',
        help="Date when this person became a member"
    )
    member_status = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('lapsed', 'Lapsed'),
        ('suspended', 'Suspended'),
        ('deceased', 'Deceased')
    ], string='Member Status', default='prospect', tracking=True)

    # Contact Role Fields
    contact_role_ids = fields.One2many(
        'ams.contact.role.assignment',
        'partner_id',
        string='Contact Roles'
    )
    primary_contact_for_ids = fields.One2many(
        'res.partner',
        'primary_contact_id',
        string='Primary Contact For'
    )
    primary_contact_id = fields.Many2one(
        'res.partner',
        string='Primary Contact',
        domain="[('is_company', '=', False)]",
        help="Primary contact person for this organization"
    )

    # Communication Preferences
    communication_preference_ids = fields.One2many(
        'ams.communication.preference',
        'partner_id',
        string='Communication Preferences'
    )
    email_opt_out = fields.Boolean(
        string='Email Opt-Out',
        help="If checked, this contact will not receive marketing emails"
    )
    phone_opt_out = fields.Boolean(
        string='Phone Opt-Out',
        help="If checked, this contact will not receive marketing phone calls"
    )
    mail_opt_out = fields.Boolean(
        string='Mail Opt-Out',
        help="If checked, this contact will not receive marketing mail"
    )

    # Computed Fields
    member_display_name = fields.Char(
        string='Member Display Name',
        compute='_compute_member_display_name',
        store=True
    )

    @api.depends('name', 'member_id')
    def _compute_member_display_name(self):
        """Compute display name including member ID if available"""
        for partner in self:
            if partner.member_id:
                partner.member_display_name = f"{partner.name} ({partner.member_id})"
            else:
                partner.member_display_name = partner.name

    @api.model
    def create(self, vals):
        """Override create to auto-generate member ID if needed"""
        # Auto-generate member ID if creating a member without one
        if vals.get('is_member') and not vals.get('member_id'):
            vals['member_id'] = self._generate_member_id()
            
        # Set member_since if not provided and is_member is True
        if vals.get('is_member') and not vals.get('member_since'):
            vals['member_since'] = fields.Date.today()
            
        # Set initial member status
        if vals.get('is_member') and not vals.get('member_status'):
            vals['member_status'] = 'active'

        partner = super().create(vals)
        
        # Log member creation
        if partner.is_member:
            self._log_member_activity(partner, 'created')
            
        return partner

    def write(self, vals):
        """Override write to handle member status changes"""
        result = super().write(vals)
        
        # Handle member status changes
        if 'is_member' in vals or 'member_status' in vals:
            for partner in self:
                if partner.is_member and not partner.member_id:
                    partner.member_id = self._generate_member_id()
                if partner.is_member and not partner.member_since:
                    partner.member_since = fields.Date.today()
                    
                # Log significant member changes
                if 'member_status' in vals:
                    self._log_member_activity(partner, 'status_changed', vals.get('member_status'))
                    
        return result

    @api.model
    def _generate_member_id(self):
        """Generate unique member ID using sequence"""
        try:
            return self.env['ir.sequence'].next_by_code('ams.member.id') or 'MEM-ERROR'
        except Exception as e:
            _logger.error(f"Error generating member ID: {e}")
            return f"MEM{self.env['res.partner'].search_count([]) + 1:05d}"

    def _log_member_activity(self, partner, activity_type, details=None):
        """Log member-related activities for audit trail"""
        try:
            self.env['ams.audit.log'].create({
                'partner_id': partner.id,
                'activity_type': activity_type,
                'description': f"Member {activity_type}: {details or ''}",
                'user_id': self.env.user.id,
                'timestamp': fields.Datetime.now()
            })
        except Exception as e:
            _logger.warning(f"Failed to log member activity: {e}")

    @api.constrains('member_id')
    def _check_member_id_unique(self):
        """Ensure member ID is unique"""
        for partner in self:
            if partner.member_id:
                duplicate = self.search([
                    ('member_id', '=', partner.member_id),
                    ('id', '!=', partner.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Member ID '%s' already exists for %s. Member IDs must be unique.") 
                        % (partner.member_id, duplicate.name)
                    )

    @api.constrains('is_member', 'member_status')
    def _check_member_status_consistency(self):
        """Ensure member status is consistent with is_member flag"""
        for partner in self:
            if partner.is_member and partner.member_status == 'prospect':
                # Auto-correct: if marked as member but status is prospect, update status
                partner.member_status = 'active'
            elif not partner.is_member and partner.member_status in ['active', 'inactive', 'suspended']:
                # Warning: member status set but not marked as member
                _logger.warning(
                    f"Partner {partner.name} has member status '{partner.member_status}' "
                    f"but is_member is False"
                )

    def action_make_member(self):
        """Action to convert prospect to member"""
        for partner in self:
            if not partner.is_member:
                partner.write({
                    'is_member': True,
                    'member_status': 'active',
                    'member_since': fields.Date.today()
                })
        return True

    def action_deactivate_member(self):
        """Action to deactivate member"""
        for partner in self:
            if partner.is_member and partner.member_status == 'active':
                partner.member_status = 'inactive'
        return True

    def action_reactivate_member(self):
        """Action to reactivate member"""
        for partner in self:
            if partner.is_member and partner.member_status in ['inactive', 'lapsed']:
                partner.member_status = 'active'
        return True

    @api.model
    def get_member_stats(self):
        """Get basic member statistics"""
        stats = {}
        members = self.search([('is_member', '=', True)])
        
        stats['total_members'] = len(members)
        for status in ['active', 'inactive', 'lapsed', 'suspended']:
            stats[f'{status}_members'] = len(members.filtered(lambda m: m.member_status == status))
            
        return stats

    def _get_communication_preferences(self):
        """Get communication preferences for this partner"""
        self.ensure_one()
        preferences = {}
        for pref in self.communication_preference_ids:
            preferences[pref.preference_type] = pref.is_opted_in
        return preferences

    @api.model
    def search_members(self, domain=None, limit=None):
        """Search members with default member filter"""
        member_domain = [('is_member', '=', True)]
        if domain:
            member_domain.extend(domain)
        return self.search(member_domain, limit=limit)