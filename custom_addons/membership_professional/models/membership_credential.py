# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCredential(models.Model):
    """
    Professional Credentials (MD, PhD, PE, CPA, etc.)
    """
    _name = 'membership.credential'
    _description = 'Professional Credential'
    _order = 'sequence, name'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    name = fields.Char(
        string='Credential Name',
        required=True,
        translate=True,
        help='Full name (e.g., Doctor of Medicine, Professional Engineer)'
    )
    
    code = fields.Char(
        string='Abbreviation',
        required=True,
        help='Standard abbreviation (e.g., MD, PE, PhD, CPA)'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive credentials are hidden but not deleted'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order in lists'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description of this credential'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color for visual identification in UI'
    )

    # ==========================================
    # CREDENTIAL CLASSIFICATION
    # ==========================================
    
    credential_type = fields.Selection([
        ('academic', 'Academic Degree'),
        ('professional', 'Professional License'),
        ('certification', 'Certification'),
        ('designation', 'Professional Designation'),
        ('fellowship', 'Fellowship'),
        ('board', 'Board Certification'),
    ], string='Credential Type',
       required=True,
       default='professional',
       help='Type of credential')
    
    credential_level = fields.Selection([
        ('basic', 'Basic/Entry Level'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert/Master'),
    ], string='Credential Level',
       default='intermediate',
       help='Level of credential')
    
    is_required_for_membership = fields.Boolean(
        string='Required for Membership',
        default=False,
        help='This credential is required for certain membership categories'
    )
    
    is_primary_credential = fields.Boolean(
        string='Primary Credential',
        default=True,
        help='Can be selected as primary credential'
    )

    # ==========================================
    # REQUIREMENTS & VALIDATION
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        default=False,
        help='Members must provide proof of this credential'
    )
    
    verification_document_required = fields.Boolean(
        string='Document Required',
        default=False,
        help='Require upload of credential document'
    )
    
    requires_expiration_date = fields.Boolean(
        string='Has Expiration Date',
        default=False,
        help='This credential expires and requires renewal'
    )
    
    typical_validity_period = fields.Integer(
        string='Typical Validity (Years)',
        default=0,
        help='Typical validity period in years (0 = no expiration)'
    )
    
    requires_continuing_education = fields.Boolean(
        string='Requires CE',
        default=False,
        help='Requires continuing education for maintenance'
    )
    
    ce_hours_required = fields.Float(
        string='CE Hours Required',
        help='Continuing education hours required per renewal period'
    )

    # ==========================================
    # ISSUING AUTHORITY
    # ==========================================
    
    issuing_organization = fields.Char(
        string='Issuing Organization',
        help='Organization that issues this credential'
    )
    
    issuing_country_id = fields.Many2one(
        'res.country',
        string='Issuing Country',
        help='Primary country where this credential is issued'
    )
    
    website = fields.Char(
        string='Website',
        help='Website of issuing organization'
    )

    # ==========================================
    # MEMBERSHIP CATEGORY ASSOCIATIONS
    # ==========================================
    
    category_ids = fields.Many2many(
        'membership.category',
        'credential_category_rel',
        'credential_id',
        'category_id',
        string='Required for Categories',
        help='Member categories that require this credential'
    )
    
    partner_count = fields.Integer(
        string='Member Count',
        compute='_compute_partner_count',
        help='Number of members with this credential'
    )

    @api.depends('code')  # Dummy dependency
    def _compute_partner_count(self):
        """Count members with this credential"""
        for credential in self:
            credential.partner_count = self.env['res.partner'].search_count([
                ('professional_credentials', 'in', [credential.id])
            ])

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_view_members(self):
        """View members with this credential"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('professional_credentials', 'in', [self.id])],
            'context': {'default_professional_credentials': [(6, 0, [self.id])]},
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            if record.code:
                name = f"{record.code} - {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure credential code is unique"""
        for credential in self:
            if self.search_count([
                ('code', '=', credential.code),
                ('id', '!=', credential.id)
            ]) > 0:
                raise ValidationError(
                    _("Credential code must be unique. '%s' is already used.") % credential.code
                )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Credential code must be unique!'),
    ]


class MembershipCredentialHistory(models.Model):
    """
    Track credential history for members
    """
    _name = 'membership.credential.history'
    _description = 'Credential History'
    _order = 'date_obtained desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    credential_id = fields.Many2one(
        'membership.credential',
        string='Credential',
        required=True,
        ondelete='restrict'
    )
    
    date_obtained = fields.Date(
        string='Date Obtained',
        required=True,
        help='Date when credential was obtained'
    )
    
    date_expires = fields.Date(
        string='Expiration Date',
        help='Date when credential expires'
    )
    
    credential_number = fields.Char(
        string='Credential Number',
        help='Official credential/license number'
    )
    
    issuing_authority = fields.Char(
        string='Issuing Authority',
        help='Specific issuing authority (e.g., State Medical Board)'
    )
    
    issuing_state_id = fields.Many2one(
        'res.country.state',
        string='Issuing State/Province',
        help='State or province that issued this credential'
    )
    
    status = fields.Selection([
        ('current', 'Current'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
    ], string='Status',
       default='current',
       required=True)
    
    verification_status = fields.Selection([
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], string='Verification Status',
       default='pending')
    
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help='User who verified this credential'
    )
    
    verified_date = fields.Date(
        string='Verification Date'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Documents',
        help='Supporting documents (certificates, licenses, etc.)'
    )

    @api.onchange('credential_id', 'date_obtained')
    def _onchange_set_expiration(self):
        """Auto-set expiration date based on credential validity period"""
        if self.credential_id and self.date_obtained:
            if self.credential_id.requires_expiration_date and self.credential_id.typical_validity_period > 0:
                from dateutil.relativedelta import relativedelta
                self.date_expires = self.date_obtained + relativedelta(
                    years=self.credential_id.typical_validity_period
                )