from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MembershipChapter(models.Model):
    _name = 'membership.chapter'
    _description = 'Membership Chapter'
    _order = 'sequence, name'
    _parent_store = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Chapter Name',
        required=True,
        tracking=True,
        help="Name of the chapter"
    )
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help="Short code for the chapter"
    )
    description = fields.Text(
        string='Description',
        help="Description of the chapter and its purpose"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of display"
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="Uncheck to disable this chapter"
    )
    
    # Hierarchy
    parent_id = fields.Many2one(
        'membership.chapter',
        string='Parent Chapter',
        index=True,
        ondelete='cascade',
        help="Parent chapter for hierarchical organization"
    )
    child_ids = fields.One2many(
        'membership.chapter',
        'parent_id',
        string='Sub-Chapters'
    )
    parent_path = fields.Char(index=True)
    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        store=True,
        help="Hierarchy level (0 = top level)"
    )
    
    # Chapter Type and Location
    chapter_type = fields.Selection([
        ('regional', 'Regional'),
        ('special_interest', 'Special Interest'),
        ('professional', 'Professional'),
        ('student', 'Student'),
        ('other', 'Other'),
    ], string='Chapter Type', default='regional', required=True, tracking=True)
    
    # Location Information
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        ondelete='restrict',
        domain="[('country_id', '=?', country_id)]"
    )
    zip = fields.Char(string='Zip')
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        ondelete='restrict'
    )
    
    # Contact Information
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    website = fields.Char(string='Website')
    
    # Management
    manager_id = fields.Many2one(
        'res.partner',
        string='Chapter Manager',
        tracking=True,
        domain=[('is_company', '=', False)],
        help="Primary manager/president of the chapter"
    )
    officer_ids = fields.Many2many(
        'res.partner',
        'chapter_officer_rel',
        'chapter_id',
        'partner_id',
        string='Officers',
        domain=[('is_company', '=', False)],
        help="Chapter officers and board members"
    )
    
    # Membership
    member_ids = fields.One2many(
        'res.partner',
        'chapter_id',
        string='Members'
    )
    membership_ids = fields.One2many(
        'membership.membership',
        'chapter_id',
        string='Memberships'
    )
    
    # Statistics
    member_count = fields.Integer(
        string='Total Members',
        compute='_compute_member_statistics',
        help="Total number of members in this chapter"
    )
    active_member_count = fields.Integer(
        string='Active Members',
        compute='_compute_member_statistics',
        help="Number of members with active memberships"
    )
    total_member_count = fields.Integer(
        string='Total (including sub-chapters)',
        compute='_compute_total_statistics',
        help="Total members including sub-chapters"
    )
    
    # Financial
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    @api.depends('parent_path')
    def _compute_level(self):
        for chapter in self:
            if chapter.parent_path:
                chapter.level = len(chapter.parent_path.split('/')) - 2
            else:
                chapter.level = 0

    @api.depends('member_ids', 'membership_ids.state')
    def _compute_member_statistics(self):
        for chapter in self:
            chapter.member_count = len(chapter.member_ids)
            # Check if memberships exist and have state field
            active_memberships = chapter.membership_ids.filtered(
                lambda m: hasattr(m, 'state') and m.state in ['active', 'grace']
            )
            chapter.active_member_count = len(active_memberships)

    @api.depends('member_count', 'child_ids.total_member_count', 'child_ids.member_count')
    def _compute_total_statistics(self):
        for chapter in self:
            total = chapter.member_count
            for child in chapter.child_ids:
                total += child.total_member_count
            chapter.total_member_count = total

    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive chapters.'))

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Code must be unique. Another chapter already uses this code."))

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    def name_get(self):
        """Return name with hierarchy path"""
        result = []
        for chapter in self:
            if chapter.parent_id:
                name = f"{chapter.parent_id.name} / {chapter.name}"
            else:
                name = chapter.name
            result.append((chapter.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Search by name or code"""
        args = args or []
        if name:
            chapters = self.search(['|', ('name', operator, name), ('code', operator, name)] + args, limit=limit)
            return chapters.name_get()
        return super()._name_search(name, args, operator, limit, name_get_uid)

    def action_view_members(self):
        """View members of this chapter"""
        self.ensure_one()
        return {
            'name': f"Members - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id)],
            'context': {'default_chapter_id': self.id},
        }

    def action_view_memberships(self):
        """View memberships of this chapter"""
        self.ensure_one()
        return {
            'name': f"Memberships - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id)],
            'context': {'default_chapter_id': self.id},
        }

    def action_view_sub_chapters(self):
        """View sub-chapters"""
        self.ensure_one()
        return {
            'name': f"Sub-Chapters - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }

    def get_chapter_hierarchy(self):
        """Get full chapter hierarchy as string"""
        self.ensure_one()
        hierarchy = []
        chapter = self
        while chapter:
            hierarchy.insert(0, chapter.name)
            chapter = chapter.parent_id
        return ' / '.join(hierarchy)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        help="Chapter this member belongs to"
    )
    chapter_role = fields.Selection([
        ('member', 'Member'),
        ('officer', 'Officer'),
        ('manager', 'Manager/President'),
    ], string='Chapter Role', default='member', help="Role in the chapter")
    
    managed_chapter_ids = fields.One2many(
        'membership.chapter',
        'manager_id',
        string='Managed Chapters'
    )
    officer_chapter_ids = fields.Many2many(
        'membership.chapter',
        'chapter_officer_rel',
        'partner_id',
        'chapter_id',
        string='Officer in Chapters'
    )


class Membership(models.Model):
    _inherit = 'membership.membership'

    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        help="Chapter this membership belongs to"
    )
    
    @api.onchange('partner_id')
    def _onchange_partner_chapter(self):
        """Auto-set chapter from partner"""
        if self.partner_id and self.partner_id.chapter_id:
            self.chapter_id = self.partner_id.chapter_id