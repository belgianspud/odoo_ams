# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipLicense(models.Model):
    """
    Professional License Tracking
    """
    _name = 'membership.license'
    _description = 'Professional License'
    _order = 'expiration_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='License Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    credential_id = fields.Many2one(
        'membership.credential',
        string='Credential Type',
        required=True,
        domain=[('credential_type', 'in', ['professional', 'certification', 'board'])],
        tracking=True
    )
    
    license_number = fields.Char(
        string='License Number',
        required=True,
        tracking=True,
        help='Official license/registration number'
    )

    # ==========================================
    # ISSUING AUTHORITY
    # ==========================================
    
    issuing_authority = fields.Char(
        string='Issuing Authority',
        required=True,
        tracking=True,
        help='Organization that issued this license'
    )
    
    issuing_country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True
    )
    
    issuing_state_id = fields.Many2one(
        'res.country.state',
        string='State/Province',
        domain="[('country_id', '=', issuing_country_id)]"
    )

    # ==========================================
    # DATES & STATUS
    # ==========================================
    
    issue_date = fields.Date(
        string='Issue Date',
        required=True,
        tracking=True,
        help='Date when license was first issued'
    )
    
    expiration_date = fields.Date(
        string='Expiration Date',
        required=True,
        tracking=True,
        help='Date when license expires'
    )
    
    last_renewal_date = fields.Date(
        string='Last Renewal Date',
        tracking=True,
        help='Date of most recent renewal'
    )
    
    next_renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_next_renewal_date',
        store=True,
        help='Expected next renewal date'
    )
    
    status = fields.Selection([
        ('active', 'Active'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
        ('pending', 'Pending'),
    ], string='Status',
       compute='_compute_status',
       store=True,
       tracking=True,
       help='Current license status')
    
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry',
        help='Days remaining until expiration'
    )
    
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_status',
        store=True
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_status',
        store=True,
        help='License expires within warning period'
    )

    # ==========================================
    # VERIFICATION
    # ==========================================
    
    verification_status = fields.Selection([
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired_unverified', 'Expired - Not Verified'),
    ], string='Verification Status',
       default='pending',
       tracking=True)
    
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help='User who verified this license',
        tracking=True
    )
    
    verified_date = fields.Date(
        string='Verification Date',
        tracking=True
    )
    
    verification_notes = fields.Text(
        string='Verification Notes'
    )

    # ==========================================
    # CONTINUING EDUCATION
    # ==========================================
    
    ce_required = fields.Boolean(
        string='CE Required',
        default=False,
        help='Continuing education required for renewal'
    )
    
    ce_hours_required = fields.Float(
        string='CE Hours Required',
        help='Hours of continuing education required'
    )
    
    ce_hours_completed = fields.Float(
        string='CE Hours Completed',
        help='Hours of continuing education completed'
    )
    
    ce_hours_remaining = fields.Float(
        string='CE Hours Remaining',
        compute='_compute_ce_hours_remaining',
        help='Hours still needed'
    )
    
    ce_compliance = fields.Boolean(
        string='CE Compliant',
        compute='_compute_ce_compliance',
        help='Member has completed required CE hours'
    )

    # ==========================================
    # DOCUMENTS & NOTES
    # ==========================================
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Documents',
        help='License documents, certificates, etc.'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive licenses are archived'
    )

    # ==========================================
    # NOTIFICATIONS
    # ==========================================
    
    last_reminder_date = fields.Date(
        string='Last Reminder Sent',
        help='Date of last expiration reminder'
    )
    
    reminder_count = fields.Integer(
        string='Reminders Sent',
        default=0,
        help='Number of expiration reminders sent'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.model
    def create(self, vals):
        """Set license reference on create"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('membership.license') or _('New')
        return super().create(vals)

    @api.depends('expiration_date')
    def _compute_next_renewal_date(self):
        """Calculate expected renewal date (typically before expiration)"""
        for license in self:
            if license.expiration_date:
                # Suggest renewal 90 days before expiration
                license.next_renewal_date = license.expiration_date - timedelta(days=90)
            else:
                license.next_renewal_date = False

    @api.depends('expiration_date')
    def _compute_status(self):
        """Determine license status based on expiration date"""
        today = fields.Date.today()
        warning_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'membership_professional.license_expiry_warning_days', '90'
        ))
        
        for license in self:
            if not license.expiration_date:
                license.status = 'pending'
                license.is_expired = False
                license.is_expiring_soon = False
                continue
            
            # Check expiration
            if license.expiration_date < today:
                license.status = 'expired'
                license.is_expired = True
                license.is_expiring_soon = False
            elif license.expiration_date <= (today + timedelta(days=warning_days)):
                license.status = 'expiring_soon'
                license.is_expired = False
                license.is_expiring_soon = True
            else:
                license.status = 'active'
                license.is_expired = False
                license.is_expiring_soon = False

    @api.depends('expiration_date')
    def _compute_days_until_expiry(self):
        """Calculate days until expiration"""
        today = fields.Date.today()
        for license in self:
            if license.expiration_date:
                delta = license.expiration_date - today
                license.days_until_expiry = delta.days
            else:
                license.days_until_expiry = 0

    @api.depends('ce_hours_required', 'ce_hours_completed')
    def _compute_ce_hours_remaining(self):
        """Calculate remaining CE hours needed"""
        for license in self:
            if license.ce_required:
                license.ce_hours_remaining = max(0, 
                    license.ce_hours_required - license.ce_hours_completed
                )
            else:
                license.ce_hours_remaining = 0

    @api.depends('ce_hours_remaining')
    def _compute_ce_compliance(self):
        """Check if CE requirements are met"""
        for license in self:
            if license.ce_required:
                license.ce_compliance = license.ce_hours_remaining <= 0
            else:
                license.ce_compliance = True

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_verify(self):
        """Mark license as verified"""
        self.ensure_one()
        self.write({
            'verification_status': 'verified',
            'verified_by': self.env.user.id,
            'verified_date': fields.Date.today(),
        })
        self.message_post(
            body=_('License verified by %s') % self.env.user.name,
            message_type='notification'
        )

    def action_reject(self):
        """Reject license verification"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject License'),
            'res_model': 'membership.license.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_license_id': self.id},
        }

    def action_renew(self):
        """Renew license"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew License'),
            'res_model': 'membership.license.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_license_id': self.id},
        }

    def action_send_expiration_reminder(self):
        """Send expiration reminder email"""
        self.ensure_one()
        
        template = self.env.ref(
            'membership_professional.email_template_license_expiration',
            raise_if_not_found=False
        )
        
        if template:
            template.send_mail(self.id, force_send=False)
            self.write({
                'last_reminder_date': fields.Date.today(),
                'reminder_count': self.reminder_count + 1,
            })
            _logger.info(f"Sent expiration reminder for license {self.name}")

    # ==========================================
    # CRON METHODS
    # ==========================================

    @api.model
    def _cron_check_license_expiration(self):
        """Cron job to check for expiring licenses and send reminders"""
        today = fields.Date.today()
        
        # Get warning days from settings
        warning_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'membership_professional.license_expiry_warning_days', '90'
        ))
        
        # Find licenses expiring soon
        expiring_licenses = self.search([
            ('status', '=', 'expiring_soon'),
            ('verification_status', '=', 'verified'),
            ('active', '=', True),
            '|',
            ('last_reminder_date', '=', False),
            ('last_reminder_date', '<=', today - timedelta(days=30)),
        ])
        
        _logger.info(f"Found {len(expiring_licenses)} licenses expiring soon")
        
        for license in expiring_licenses:
            try:
                license.action_send_expiration_reminder()
            except Exception as e:
                _logger.error(f"Failed to send reminder for license {license.name}: {e}")

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('expiration_date', 'issue_date')
    def _check_dates(self):
        """Validate dates"""
        for license in self:
            if license.expiration_date and license.issue_date:
                if license.expiration_date <= license.issue_date:
                    raise ValidationError(_(
                        'Expiration date must be after issue date.'
                    ))

    @api.constrains('ce_hours_completed', 'ce_hours_required')
    def _check_ce_hours(self):
        """Validate CE hours"""
        for license in self:
            if license.ce_hours_completed < 0:
                raise ValidationError(_('CE hours completed cannot be negative.'))
            if license.ce_hours_required < 0:
                raise ValidationError(_('CE hours required cannot be negative.'))