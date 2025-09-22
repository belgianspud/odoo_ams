from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MemberDirectory(models.Model):
    _name = 'membership.directory'
    _description = 'Member Directory Entry'
    _order = 'partner_id'
    _rec_name = 'partner_id'

    # Basic Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        help="The member this directory entry represents"
    )
    
    # Privacy Settings
    is_public = fields.Boolean(
        string='Include in Directory',
        default=True,
        help="Include this member in the public directory"
    )
    allow_contact = fields.Boolean(
        string='Allow Contact',
        default=True,
        help="Allow other members to contact this member"
    )
    
    # Contact Display Options
    show_email = fields.Boolean(
        string='Show Email',
        default=False,
        help="Display email address in directory"
    )
    show_phone = fields.Boolean(
        string='Show Phone',
        default=False,
        help="Display phone number in directory"
    )
    show_company = fields.Boolean(
        string='Show Company',
        default=True,
        help="Display company/organization in directory"
    )
    show_address = fields.Boolean(
        string='Show Address',
        default=False,
        help="Display address in directory"
    )
    
    # Professional Information
    bio = fields.Text(
        string='Professional Bio',
        help="Professional background and biography"
    )
    skills = fields.Char(
        string='Skills/Expertise',
        help="Areas of expertise and skills"
    )
    industries = fields.Char(
        string='Industries',
        help="Industries of experience"
    )
    linkedin_url = fields.Char(
        string='LinkedIn Profile',
        help="LinkedIn profile URL"
    )
    website_url = fields.Char(
        string='Website',
        help="Personal or company website"
    )
    
    # Membership Information (for display)
    membership_level = fields.Char(
        string='Membership Level',
        related='partner_id.current_membership_id.level_id.name',
        readonly=True
    )
    chapter_name = fields.Char(
        string='Chapter',
        related='partner_id.chapter_id.name',
        readonly=True
    )
    member_since = fields.Date(
        string='Member Since',
        related='partner_id.current_membership_id.start_date',
        readonly=True
    )
    
    # Directory Categories
    category_ids = fields.Many2many(
        'membership.directory.category',
        string='Directory Categories',
        help="Categories this member appears under"
    )
    
    # Activity Tracking
    last_updated = fields.Datetime(
        string='Last Updated',
        default=fields.Datetime.now,
        help="When directory entry was last updated"
    )
    view_count = fields.Integer(
        string='Profile Views',
        default=0,
        help="Number of times this profile has been viewed"
    )
    
    @api.constrains('partner_id')
    def _check_partner_unique(self):
        for record in self:
            existing = self.search([
                ('partner_id', '=', record.partner_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_("Directory entry already exists for this member."))
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.last_updated = fields.Datetime.now()
        return records
    
    def write(self, vals):
        if any(field in vals for field in ['bio', 'skills', 'industries', 'show_email', 'show_phone']):
            vals['last_updated'] = fields.Datetime.now()
        return super().write(vals)
    
    def action_increment_view_count(self):
        """Increment view count when profile is viewed"""
        self.view_count += 1
    
    def action_update_from_partner(self):
        """Update directory entry from partner information"""
        for record in self:
            # Auto-update fields that might have changed on partner
            record.last_updated = fields.Datetime.now()


class MemberDirectoryCategory(models.Model):
    _name = 'membership.directory.category'
    _description = 'Directory Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help="Name of the directory category"
    )
    code = fields.Char(
        string='Code',
        help="Short code for the category"
    )
    description = fields.Text(
        string='Description',
        help="Description of this category"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to disable this category"
    )
    color = fields.Integer(
        string='Color',
        help="Color for category display"
    )
    
    member_count = fields.Integer(
        string='Members',
        compute='_compute_member_count',
        help="Number of members in this category"
    )
    
    @api.depends()  # Will be computed when needed
    def _compute_member_count(self):
        for category in self:
            category.member_count = self.env['membership.directory'].search_count([
                ('category_ids', 'in', category.id),
                ('is_public', '=', True)
            ])


class ResPartner(models.Model):
    _inherit = 'res.partner'

    directory_entry_id = fields.One2many(
        'membership.directory',
        'partner_id',
        string='Directory Entry'
    )
    in_directory = fields.Boolean(
        string='In Member Directory',
        compute='_compute_directory_status'
    )
    directory_public = fields.Boolean(
        string='Directory Public',
        compute='_compute_directory_status'
    )
    
    @api.depends('directory_entry_id.is_public')
    def _compute_directory_status(self):
        for partner in self:
            if partner.directory_entry_id:
                partner.in_directory = True
                partner.directory_public = partner.directory_entry_id[0].is_public
            else:
                partner.in_directory = False
                partner.directory_public = False
    
    def action_create_directory_entry(self):
        """Create directory entry for this member"""
        self.ensure_one()
        if not self.directory_entry_id:
            self.env['membership.directory'].create({
                'partner_id': self.id,
                'is_public': True,
                'allow_contact': True,
                'show_company': True
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'membership.directory',
            'res_id': self.directory_entry_id[0].id,
            'view_mode': 'form',
            'target': 'current',
        }