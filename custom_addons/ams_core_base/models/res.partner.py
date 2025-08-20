# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ===== MEMBER IDENTITY =====
    member_id = fields.Char(
        string='Member ID',
        copy=False,
        readonly=True,
        index=True,
        help="Unique member identifier assigned automatically"
    )
    is_member = fields.Boolean(
        string='Is Member',
        default=False,
        help="Check if this contact is an association member"
    )
    member_since = fields.Date(
        string='Member Since',
        help="Date when this contact first became a member"
    )
    member_status = fields.Selection([
        ('active', 'Active'),
        ('lapsed', 'Lapsed'),
        ('prospect', 'Prospect'),
        ('emeritus', 'Emeritus'),
        ('honorary', 'Honorary'),
        ('student', 'Student'),
        ('suspended', 'Suspended'),
        ('deceased', 'Deceased'),
    ], string='Member Status', default='prospect')
    
    emeritus_flag = fields.Boolean(
        string='Emeritus',
        default=False,
        help="Former member with emeritus status"
    )
    
    # ===== PROFESSIONAL INFORMATION =====
    profession_discipline = fields.Char(
        string='Profession/Discipline',
        help="Primary profession or discipline"
    )
    
    professional_designation_ids = fields.Many2many(
        'ams.professional.designation',
        string='Professional Designations',
        help="Professional titles, certifications, degrees"
    )
    
    specialty_ids = fields.Many2many(
        'ams.member.specialty',
        string='Specialties/Practice Areas',
        help="Areas of specialization or practice"
    )
    
    license_certification_number = fields.Char(
        string='License/Certification Number',
        help="Professional license or certification number"
    )
    
    career_stage = fields.Selection([
        ('student', 'Student'),
        ('early_career', 'Early Career'),
        ('mid_career', 'Mid-Career'),
        ('senior', 'Senior'),
        ('retired', 'Retired/Emeritus'),
    ], string='Career Stage')
    
    employer_id = fields.Many2one(
        'res.partner',
        string='Employer',
        domain="[('is_company', '=', True)]",
        help="Current employer organization"
    )
    
    job_title_role = fields.Char(
        string='Job Title/Role',
        help="Current job title or role"
    )
    
    mentorship_role = fields.Selection([
        ('none', 'None'),
        ('mentor', 'Mentor'),
        ('mentee', 'Mentee'),
        ('both', 'Both'),
    ], string='Mentorship Role', default='none')

    # ===== PERSONAL DEMOGRAPHICS =====
    preferred_name = fields.Char(
        string='Preferred Name/Nickname',
        help="How the member prefers to be addressed"
    )
    
    date_of_birth = fields.Date(
        string='Date of Birth',
        help="Member's date of birth (privacy controlled)"
    )
    
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ], string='Gender')
    
    nationality = fields.Char(
        string='Nationality/Citizenship',
        help="Member's nationality or citizenship"
    )

    # ===== ORGANIZATION-SPECIFIC FIELDS =====
    organization_type = fields.Selection([
        ('company', 'Company'),
        ('university', 'University'),
        ('hospital', 'Hospital'),
        ('nonprofit', 'Nonprofit'),
        ('government', 'Government Agency'),
        ('sponsor', 'Sponsor'),
        ('vendor', 'Vendor'),
    ], string='Organization Type')
    
    industry_sector = fields.Char(
        string='Industry/Sector',
        help="Industry or sector for organizations"
    )
    
    employee_count_bracket = fields.Selection([
        ('1_10', '1-10 employees'),
        ('11_50', '11-50 employees'),
        ('51_200', '51-200 employees'),
        ('201_1000', '201-1,000 employees'),
        ('1000_plus', '1,000+ employees'),
    ], string='Employee Count')
    
    tax_id_registration = fields.Char(
        string='Tax ID/Registration Number',
        help="Tax identification or business registration number"
    )

    # ===== CONTACT PREFERENCES =====
    alternate_emails = fields.Text(
        string='Alternate Emails',
        help="Additional email addresses (one per line)"
    )
    
    preferred_contact_method = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('mail', 'Mail'),
        ('sms', 'SMS'),
    ], string='Preferred Contact Method', default='email')

    # ===== MEMBER CATEGORIES =====
    member_category_ids = fields.Many2many(
        'res.partner.category',
        string='Member Categories',
        help="Association-specific member categories"
    )

    # ===== COMPUTED FIELDS =====
    full_member_name = fields.Char(
        string='Full Member Name',
        compute='_compute_full_member_name',
        store=True,
        help="Computed full name including preferred name"
    )
    
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        help="Computed age from date of birth"
    )
    
    # ===== MEMBER PROFILE LINK =====
    member_profile_id = fields.One2many(
        'ams.member.profile',
        'partner_id',
        string='Member Profile',
        help="Extended member profile information"
    )

    @api.depends('name', 'preferred_name')
    def _compute_full_member_name(self):
        for partner in self:
            if partner.preferred_name:
                partner.full_member_name = f"{partner.name} ({partner.preferred_name})"
            else:
                partner.full_member_name = partner.name or ''

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for partner in self:
            if partner.date_of_birth:
                partner.age = today.year - partner.date_of_birth.year - (
                    (today.month, today.day) < 
                    (partner.date_of_birth.month, partner.date_of_birth.day)
                )
            else:
                partner.age = 0

    @api.model
    def create(self, vals):
        # Auto-assign member ID if is_member is True or if creating with member data
        if vals.get('is_member') or vals.get('member_since') or vals.get('member_status') != 'prospect':
            if not vals.get('member_id'):
                vals['member_id'] = self._generate_member_id()
                vals['is_member'] = True
                if not vals.get('member_since'):
                    vals['member_since'] = fields.Date.today()
        
        partner = super(ResPartner, self).create(vals)
        
        # Log creation in audit log
        self._log_audit_trail(partner, 'create', 'Partner created', vals)
        
        return partner

    def write(self, vals):
        # Capture old values for audit logging
        old_values = {}
        for partner in self:
            old_values[partner.id] = {
                field: getattr(partner, field) for field in vals.keys()
                if hasattr(partner, field)
            }
        
        # Auto-assign member ID if becoming a member
        if vals.get('is_member') and not any(partner.member_id for partner in self):
            for partner in self:
                if not partner.member_id:
                    vals['member_id'] = self._generate_member_id()
                    if not vals.get('member_since') and not partner.member_since:
                        vals['member_since'] = fields.Date.today()
        
        result = super(ResPartner, self).write(vals)
        
        # Log changes in audit log
        for partner in self:
            if partner.id in old_values:
                changes = {}
                for field, new_value in vals.items():
                    if hasattr(partner, field):
                        old_value = old_values[partner.id].get(field)
                        if old_value != new_value:
                            changes[field] = {'old': old_value, 'new': new_value}
                
                if changes:
                    self._log_audit_trail(partner, 'write', 'Partner updated', changes)
        
        return result

    def _generate_member_id(self):
        """Generate next member ID using configured sequence"""
        sequence = self.env['ir.sequence'].next_by_code('ams.member.id')
        if not sequence:
            # Fallback if sequence doesn't exist
            sequence = self.env['ir.sequence'].create({
                'name': 'AMS Member ID',
                'code': 'ams.member.id',
                'prefix': 'MEM-',
                'padding': 6,
                'number_increment': 1,
            }).next_by_code('ams.member.id')
        return sequence

    def _log_audit_trail(self, record, operation, description, data):
        """Log changes to audit trail"""
        try:
            self.env['ams.audit.log'].sudo().create({
                'model_name': record._name,
                'record_id': record.id,
                'operation': operation,
                'description': description,
                'user_id': self.env.user.id,
                'data': str(data),
                'timestamp': fields.Datetime.now(),
            })
        except Exception as e:
            _logger.warning(f"Failed to log audit trail: {e}")

    @api.constrains('member_id')
    def _check_member_id_unique(self):
        for partner in self:
            if partner.member_id:
                existing = self.search([
                    ('member_id', '=', partner.member_id),
                    ('id', '!=', partner.id)
                ])
                if existing:
                    raise ValidationError(_("Member ID %s already exists for %s") % 
                                        (partner.member_id, existing.name))

    @api.constrains('email')
    def _check_email_unique_for_members(self):
        """Ensure email addresses are unique among active members"""
        for partner in self:
            if partner.is_member and partner.email:
                existing = self.search([
                    ('email', '=', partner.email),
                    ('is_member', '=', True),
                    ('member_status', 'in', ['active', 'student', 'emeritus']),
                    ('id', '!=', partner.id)
                ])
                if existing:
                    raise ValidationError(_("Email %s is already used by member %s") % 
                                        (partner.email, existing.name))

    def action_make_member(self):
        """Convert contact to member"""
        for partner in self:
            if not partner.is_member:
                partner.write({
                    'is_member': True,
                    'member_status': 'active',
                    'member_since': partner.member_since or fields.Date.today(),
                })

    def action_remove_member_status(self):
        """Remove member status (keep as contact)"""
        for partner in self:
            if partner.is_member:
                partner.write({
                    'is_member': False,
                    'member_status': 'prospect',
                })

    def name_get(self):
        """Override name_get to include member ID and preferred name"""
        result = []
        for partner in self:
            name = partner.name or ''
            
            # Add member ID if exists
            if partner.member_id:
                name = f"[{partner.member_id}] {name}"
            
            # Add preferred name if different
            if partner.preferred_name and partner.preferred_name != partner.name:
                name = f"{name} ({partner.preferred_name})"
            
            result.append((partner.id, name))
        
        return result