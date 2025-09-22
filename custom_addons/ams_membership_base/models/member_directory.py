from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MemberDirectory(models.Model):
    _name = 'membership.directory'
    _description = 'Member Directory Entry'
    _order = 'partner_id'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        tracking=True,
        help="Include this member in the public directory"
    )
    allow_contact = fields.Boolean(
        string='Allow Contact',
        default=True,
        tracking=True,
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
    bio = fields.Html(
        string='Professional Bio',
        help="Professional background and biography"
    )
    skills = fields.Text(
        string='Skills/Expertise',
        help="Areas of expertise and skills (one per line or comma-separated)"
    )
    industries = fields.Text(
        string='Industries',
        help="Industries of experience (one per line or comma-separated)"
    )
    linkedin_url = fields.Char(
        string='LinkedIn Profile',
        help="LinkedIn profile URL"
    )
    website_url = fields.Char(
        string='Website',
        help="Personal or company website"
    )
    twitter_handle = fields.Char(
        string='Twitter Handle',
        help="Twitter username (without @)"
    )
    
    # Membership Information (for display)
    membership_level = fields.Char(
        string='Membership Level',
        compute='_compute_membership_info',
        store=True,
        help="Current membership level"
    )
    chapter_name = fields.Char(
        string='Chapter',
        compute='_compute_membership_info',
        store=True,
        help="Current chapter name"
    )
    member_since = fields.Date(
        string='Member Since',
        compute='_compute_membership_info',
        store=True,
        help="Date when member first joined"
    )
    membership_status = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled')
    ], string='Membership Status', compute='_compute_membership_info', store=True)
    
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
    
    # Contact Tracking
    contact_count = fields.Integer(
        string='Times Contacted',
        default=0,
        help="Number of times other members have contacted this member"
    )
    
    @api.depends('partner_id.current_membership_id', 'partner_id.membership_ids')
    def _compute_membership_info(self):
        for record in self:
            if record.partner_id:
                current_membership = record.partner_id.current_membership_id
                if current_membership:
                    record.membership_level = getattr(current_membership, 'level_id', False) and current_membership.level_id.name or ''
                    record.chapter_name = getattr(current_membership, 'chapter_id', False) and current_membership.chapter_id.name or ''
                    record.membership_status = current_membership.state
                else:
                    record.membership_level = ''
                    record.chapter_name = ''
                    record.membership_status = False
                
                # Get earliest membership start date
                all_memberships = record.partner_id.membership_ids
                if all_memberships:
                    earliest_membership = min(all_memberships, key=lambda m: m.start_date)
                    record.member_since = earliest_membership.start_date
                else:
                    record.member_since = False
            else:
                record.membership_level = ''
                record.chapter_name = ''
                record.member_since = False
                record.membership_status = False
    
    @api.constrains('partner_id')
    def _check_partner_unique(self):
        for record in self:
            existing = self.search([
                ('partner_id', '=', record.partner_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_("Directory entry already exists for member %s.") % record.partner_id.name)
    
    @api.constrains('linkedin_url', 'website_url')
    def _check_urls(self):
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        for record in self:
            if record.linkedin_url and not url_pattern.match(record.linkedin_url):
                raise ValidationError(_("Please enter a valid LinkedIn URL (starting with http:// or https://)"))
            if record.website_url and not url_pattern.match(record.website_url):
                raise ValidationError(_("Please enter a valid website URL (starting with http:// or https://)"))
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.last_updated = fields.Datetime.now()
        return records
    
    def write(self, vals):
        # Track when important fields are updated
        important_fields = ['bio', 'skills', 'industries', 'show_email', 'show_phone', 
                           'linkedin_url', 'website_url', 'twitter_handle', 'category_ids']
        if any(field in vals for field in important_fields):
            vals['last_updated'] = fields.Datetime.now()
        return super().write(vals)
    
    def action_increment_view_count(self):
        """Increment view count when profile is viewed"""
        self.ensure_one()
        self.sudo().write({'view_count': self.view_count + 1})
        # Don't trigger tracking for view count updates
    
    def action_increment_contact_count(self):
        """Increment contact count when member is contacted"""
        self.ensure_one()
        self.sudo().write({'contact_count': self.contact_count + 1})
    
    def action_update_from_partner(self):
        """Update directory entry from partner information"""
        for record in self:
            # Force recomputation of membership info
            record._compute_membership_info()
            record.last_updated = fields.Datetime.now()
    
    def toggle_public_status(self):
        """Toggle public visibility status"""
        self.ensure_one()
        self.is_public = not self.is_public
        self.message_post(
            body=_("Directory visibility changed to %s") % (_("Public") if self.is_public else _("Private"))
        )


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
    description = fields.Html(
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
    
    # Category Management
    parent_id = fields.Many2one(
        'membership.directory.category',
        string='Parent Category',
        help="Parent category for hierarchical organization"
    )
    child_ids = fields.One2many(
        'membership.directory.category',
        'parent_id',
        string='Subcategories'
    )
    
    # Statistics
    member_count = fields.Integer(
        string='Members',
        compute='_compute_member_count',
        help="Number of members in this category"
    )
    public_member_count = fields.Integer(
        string='Public Members',
        compute='_compute_member_count',
        help="Number of public members in this category"
    )
    
    @api.depends('member_ids.is_public')
    def _compute_member_count(self):
        for category in self:
            all_entries = self.env['membership.directory'].search([
                ('category_ids', 'in', category.id)
            ])
            category.member_count = len(all_entries)
            category.public_member_count = len(all_entries.filtered('is_public'))
    
    # Reverse relation for easier querying
    member_ids = fields.Many2many(
        'membership.directory',
        string='Directory Entries'
    )
    
    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_("Category code must be unique among active categories."))
    
    @api.constrains('parent_id')
    def _check_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create recursive categories."))
    
    def name_get(self):
        """Return name with parent hierarchy"""
        result = []
        for category in self:
            if category.parent_id:
                name = f"{category.parent_id.name} / {category.name}"
            else:
                name = category.name
            result.append((category.id, name))
        return result


class ResPartner(models.Model):
    _inherit = 'res.partner'

    directory_entry_id = fields.One2many(
        'membership.directory',
        'partner_id',
        string='Directory Entry'
    )
    in_directory = fields.Boolean(
        string='In Member Directory',
        compute='_compute_directory_status',
        store=True
    )
    directory_public = fields.Boolean(
        string='Directory Public',
        compute='_compute_directory_status',
        store=True
    )
    directory_views = fields.Integer(
        string='Directory Views',
        compute='_compute_directory_status',
        help="Number of directory profile views"
    )
    
    @api.depends('directory_entry_id.is_public', 'directory_entry_id.view_count')
    def _compute_directory_status(self):
        for partner in self:
            if partner.directory_entry_id:
                entry = partner.directory_entry_id[0]  # Should only be one
                partner.in_directory = True
                partner.directory_public = entry.is_public
                partner.directory_views = entry.view_count
            else:
                partner.in_directory = False
                partner.directory_public = False
                partner.directory_views = 0
    
    def action_create_directory_entry(self):
        """Create directory entry for this member"""
        self.ensure_one()
        
        if self.directory_entry_id:
            # Entry already exists, open it
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'membership.directory',
                'res_id': self.directory_entry_id[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Create new entry
        directory_entry = self.env['membership.directory'].create({
            'partner_id': self.id,
            'is_public': True,
            'allow_contact': True,
            'show_company': True,
            'show_email': False,  # Default to private for privacy
            'show_phone': False,  # Default to private for privacy
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'membership.directory',
            'res_id': directory_entry.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_update_directory(self):
        """Update directory entry from partner data"""
        self.ensure_one()
        if self.directory_entry_id:
            self.directory_entry_id[0].action_update_from_partner()