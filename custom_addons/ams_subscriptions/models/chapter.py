from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AMSChapter(models.Model):
    _name = 'ams.chapter'
    _description = 'AMS Chapter'
    _order = 'name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Chapter Name',
        required=True,
        tracking=True,
        help="Name of the chapter (e.g., 'New York Chapter', 'California Chapter')"
    )
    
    code = fields.Char(
        string='Chapter Code',
        required=True,
        tracking=True,
        help="Short code for this chapter (e.g., 'NY', 'CA')"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="Uncheck to archive this chapter"
    )
    
    description = fields.Html(
        string='Description',
        help="Detailed description of this chapter"
    )
    
    # Geographic Information
    street = fields.Char(
        string='Street'
    )
    
    street2 = fields.Char(
        string='Street 2'
    )
    
    city = fields.Char(
        string='City',
        tracking=True
    )
    
    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        tracking=True
    )
    
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        tracking=True
    )
    
    zip = fields.Char(
        string='ZIP Code'
    )
    
    region = fields.Char(
        string='Region',
        help="Geographic region or area served by this chapter"
    )
    
    timezone = fields.Selection(
        '_get_timezones',
        string='Timezone',
        default='UTC',
        help="Timezone for this chapter"
    )
    
    # Contact Information
    phone = fields.Char(
        string='Phone'
    )
    
    mobile = fields.Char(
        string='Mobile'
    )
    
    email = fields.Char(
        string='Email'
    )
    
    website = fields.Char(
        string='Website'
    )
    
    # Leadership
    president_id = fields.Many2one(
        'res.partner',
        string='Chapter President',
        domain=[('is_company', '=', False)],
        tracking=True
    )
    
    vice_president_id = fields.Many2one(
        'res.partner',
        string='Vice President',
        domain=[('is_company', '=', False)]
    )
    
    secretary_id = fields.Many2one(
        'res.partner',
        string='Secretary',
        domain=[('is_company', '=', False)]
    )
    
    treasurer_id = fields.Many2one(
        'res.partner',
        string='Treasurer',
        domain=[('is_company', '=', False)]
    )
    
    # Board and Officers
    board_member_ids = fields.Many2many(
        'res.partner',
        'chapter_board_member_rel',
        'chapter_id',
        'partner_id',
        string='Board Members',
        domain=[('is_company', '=', False)]
    )
    
    officer_ids = fields.Many2many(
        'res.partner',
        'chapter_officer_rel',
        'chapter_id',
        'partner_id',
        string='Officers',
        domain=[('is_company', '=', False)]
    )
    
    # Status and Settings
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('provisional', 'Provisional'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed')
    ], string='Chapter Status', default='active', required=True, tracking=True)
    
    founded_date = fields.Date(
        string='Founded Date',
        tracking=True
    )
    
    charter_number = fields.Char(
        string='Charter Number',
        help="Official charter number if applicable"
    )
    
    # Membership Settings
    auto_approve_memberships = fields.Boolean(
        string='Auto-Approve Memberships',
        default=False,
        help="Automatically approve membership applications for this chapter"
    )
    
    membership_fee_override = fields.Float(
        string='Membership Fee Override',
        digits='Product Price',
        help="Override standard membership fees for this chapter (0 = use standard rates)"
    )
    
    max_members = fields.Integer(
        string='Maximum Members',
        help="Maximum number of members allowed in this chapter (0 = unlimited)"
    )
    
    # Meeting Information
    meeting_day = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Regular Meeting Day')
    
    meeting_time = fields.Float(
        string='Meeting Time',
        help="Regular meeting time (24-hour format)"
    )
    
    meeting_location = fields.Text(
        string='Meeting Location',
        help="Regular meeting location or address"
    )
    
    meeting_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('other', 'Other')
    ], string='Meeting Frequency')
    
    # Financial Information
    bank_account = fields.Char(
        string='Bank Account',
        help="Chapter bank account information"
    )
    
    tax_id = fields.Char(
        string='Tax ID',
        help="Chapter tax identification number"
    )
    
    budget_amount = fields.Float(
        string='Annual Budget',
        digits='Product Price',
        help="Annual budget amount"
    )
    
    # Statistics and Counts
    member_count = fields.Integer(
        string='Current Members',
        compute='_compute_member_statistics',
        store=True,
        help="Number of current active members"
    )
    
    total_members = fields.Integer(
        string='Total Members',
        compute='_compute_member_statistics',
        store=True,
        help="Total number of members (including inactive)"
    )
    
    subscription_ids = fields.One2many(
        'ams.member.subscription',
        'chapter_id',
        string='Subscriptions'
    )
    
    # Events and Activities
    event_ids = fields.One2many(
        'event.event',
        'chapter_id',
        string='Chapter Events'
    )
    
    event_count = fields.Integer(
        string='Event Count',
        compute='_compute_event_count'
    )
    
    # Communication
    newsletter_template_id = fields.Many2one(
        'mail.template',
        string='Newsletter Template',
        help="Default newsletter template for this chapter"
    )
    
    communication_language = fields.Many2one(
        'res.lang',
        string='Communication Language',
        default=lambda self: self.env.ref('base.lang_en')
    )
    
    # Social Media
    facebook_url = fields.Char(
        string='Facebook URL'
    )
    
    twitter_handle = fields.Char(
        string='Twitter Handle'
    )
    
    linkedin_url = fields.Char(
        string='LinkedIn URL'
    )
    
    instagram_handle = fields.Char(
        string='Instagram Handle'
    )
    
    # Notes
    notes = fields.Html(
        string='Internal Notes'
    )
    
    public_notes = fields.Html(
        string='Public Notes',
        help="Notes visible to chapter members"
    )

    @api.depends('subscription_ids.state')
    def _compute_member_statistics(self):
        """Compute member statistics"""
        for chapter in self:
            active_subscriptions = chapter.subscription_ids.filtered(
                lambda s: s.state in ['active', 'pending_renewal']
            )
            chapter.member_count = len(active_subscriptions)
            chapter.total_members = len(chapter.subscription_ids)

    @api.depends('event_ids')
    def _compute_event_count(self):
        """Compute number of events"""
        for chapter in self:
            chapter.event_count = len(chapter.event_ids)

    @api.model
    def _get_timezones(self):
        """Get list of timezones"""
        # Basic timezone list - can be extended
        return [
            ('UTC', 'UTC'),
            ('US/Eastern', 'US/Eastern'),
            ('US/Central', 'US/Central'),
            ('US/Mountain', 'US/Mountain'),
            ('US/Pacific', 'US/Pacific'),
            ('Europe/London', 'Europe/London'),
            ('Europe/Paris', 'Europe/Paris'),
            ('Asia/Tokyo', 'Asia/Tokyo'),
            ('Australia/Sydney', 'Australia/Sydney'),
        ]

    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure chapter code is unique"""
        for chapter in self:
            if self.search_count([
                ('code', '=', chapter.code),
                ('id', '!=', chapter.id)
            ]) > 0:
                raise ValidationError(_("Chapter code must be unique!"))

    @api.constrains('max_members')
    def _check_max_members(self):
        """Check max members constraint"""
        for chapter in self:
            if chapter.max_members > 0:
                if chapter.member_count > chapter.max_members:
                    raise ValidationError(
                        _("Cannot set maximum members below current member count (%s)") 
                        % chapter.member_count
                    )

    @api.constrains('meeting_time')
    def _check_meeting_time(self):
        """Validate meeting time format"""
        for chapter in self:
            if chapter.meeting_time and (chapter.meeting_time < 0 or chapter.meeting_time >= 24):
                raise ValidationError(_("Meeting time must be between 0 and 24 hours."))

    @api.onchange('country_id')
    def _onchange_country_id(self):
        """Clear state when country changes"""
        # Get the state record safely
        state_record = self.state_id
    
        # Only proceed if we have both country and state
        if self.country_id and state_record:
            # Get the state's country safely
            state_country = getattr(state_record, 'country_id', False)
            if state_country and state_country != self.country_id:
                self.state_id = False

    def name_get(self):
        """Customize display name"""
        result = []
        for chapter in self:
            name = chapter.name
            if chapter.code:
                name = f"[{chapter.code}] {name}"
            if chapter.member_count > 0:
                name += f" ({chapter.member_count} members)"
            result.append((chapter.id, name))
        return result

    def action_view_members(self):
        """View members of this chapter"""
        self.ensure_one()
        
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ams_subscriptions.action_member_subscription"
        )
        action['domain'] = [('chapter_id', '=', self.id)]
        action['context'] = {
            'default_chapter_id': self.id,
            'search_default_chapter_id': self.id,
        }
        
        return action

    def action_view_events(self):
        """View events for this chapter"""
        self.ensure_one()
        
        # Check if event module is installed
        if not self.env['ir.module.module'].search([
            ('name', '=', 'event'),
            ('state', '=', 'installed')
        ]):
            raise ValidationError(_("Event module is not installed."))
        
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_event_view")
        action['domain'] = [('chapter_id', '=', self.id)]
        action['context'] = {
            'default_chapter_id': self.id,
        }
        
        return action

    def action_send_newsletter(self):
        """Send newsletter to chapter members"""
        self.ensure_one()
        
        if not self.newsletter_template_id:
            raise ValidationError(_("No newsletter template configured for this chapter."))
        
        # Get active members
        active_members = self.subscription_ids.filtered(
            lambda s: s.state in ['active', 'pending_renewal']
        ).mapped('partner_id')
        
        if not active_members:
            raise ValidationError(_("No active members found for this chapter."))
        
        # Send newsletter
        for member in active_members:
            if member.email:
                self.newsletter_template_id.send_mail(
                    member.id, 
                    force_send=True,
                    email_values={'subject': f"Chapter Newsletter - {self.name}"}
                )
        
        self.message_post(
            body=_("Newsletter sent to %d chapter members.") % len(active_members)
        )

    def action_create_membership(self):
        """Create a new membership for this chapter"""
        self.ensure_one()
        
        return {
            'name': _('New Chapter Membership'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.member.subscription',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_chapter_id': self.id,
            }
        }

    def get_available_membership_types(self):
        """Get membership types available for this chapter"""
        self.ensure_one()
        
        # Get all membership types that are either not chapter-based or allow this chapter
        return self.env['ams.membership.type'].search([
            '|',
            ('chapter_based', '=', False),
            ('allowed_chapter_ids', 'in', [self.id])
        ])

    def get_chapter_statistics(self):
        """Get comprehensive chapter statistics"""
        self.ensure_one()
        
        # Member statistics by type
        member_by_type = {}
        for subscription in self.subscription_ids.filtered(lambda s: s.state == 'active'):
            member_type = subscription.membership_type_id.member_category
            member_by_type[member_type] = member_by_type.get(member_type, 0) + 1
        
        # Revenue statistics
        total_revenue = sum(self.subscription_ids.mapped('total_amount'))
        active_revenue = sum(
            self.subscription_ids.filtered(
                lambda s: s.state == 'active'
            ).mapped('total_amount')
        )
        
        return {
            'total_members': self.total_members,
            'active_members': self.member_count,
            'member_by_type': member_by_type,
            'total_revenue': total_revenue,
            'active_revenue': active_revenue,
            'events_count': self.event_count,
            'status': self.status,
        }

    def check_membership_eligibility(self, partner_id, membership_type_id):
        """Check if a person is eligible for membership in this chapter"""
        self.ensure_one()
        
        partner = self.env['res.partner'].browse(partner_id)
        membership_type = self.env['ams.membership.type'].browse(membership_type_id)
        
        # Check if membership type is available for this chapter
        if not membership_type.is_available_for_chapter(self.id):
            return False, _("Membership type '%s' is not available for this chapter.") % membership_type.name
        
        # Check chapter capacity
        if self.max_members > 0 and self.member_count >= self.max_members:
            return False, _("Chapter has reached maximum member capacity (%s).") % self.max_members
        
        # Check if already a member
        existing_subscription = self.subscription_ids.filtered(
            lambda s: s.partner_id.id == partner_id and s.state in ['active', 'pending_renewal']
        )
        if existing_subscription:
            return False, _("Person is already an active member of this chapter.")
        
        return True, _("Eligible for membership in this chapter.")

    @api.model
    def get_chapter_dashboard_data(self):
        """Get dashboard data for all chapters"""
        chapters = self.search([('active', '=', True)])
        
        dashboard_data = []
        for chapter in chapters:
            stats = chapter.get_chapter_statistics()
            dashboard_data.append({
                'chapter_id': chapter.id,
                'chapter_name': chapter.name,
                'chapter_code': chapter.code,
                'city': chapter.city,
                'state': chapter.state_id.name if chapter.state_id else '',
                'statistics': stats
            })
        
        return dashboard_data

    def toggle_active(self):
        """Toggle active status with additional checks"""
        for chapter in self:
            if chapter.active and chapter.member_count > 0:
                raise ValidationError(
                    _("Cannot deactivate chapter '%s' because it has active members. "
                      "Please transfer or cancel member subscriptions first.") % chapter.name
                )
        
        return super().toggle_active()

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        chapter = super().create(vals)
        
        # Log chapter creation
        _logger.info(f"New chapter created: {chapter.name} [{chapter.code}]")
        
        return chapter

    def write(self, vals):
        """Override write to track important changes"""
        result = super().write(vals)
        
        # Log status changes
        if 'status' in vals:
            for chapter in self:
                _logger.info(f"Chapter {chapter.name} status changed to: {chapter.status}")
        
        return result