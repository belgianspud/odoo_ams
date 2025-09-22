from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ChapterMeeting(models.Model):
    _name = 'membership.chapter.meeting'
    _description = 'Chapter Meeting'
    _order = 'meeting_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Meeting Title',
        required=True,
        tracking=True,
        help="Title of the meeting"
    )
    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        required=True,
        help="Chapter organizing this meeting"
    )
    meeting_date = fields.Datetime(
        string='Meeting Date',
        required=True,
        tracking=True,
        help="Date and time of the meeting"
    )
    duration = fields.Float(
        string='Duration (Hours)',
        default=2.0,
        help="Expected duration of the meeting in hours"
    )
    
    # Meeting Type and Status
    meeting_type = fields.Selection([
        ('board', 'Board Meeting'),
        ('general', 'General Meeting'),
        ('special', 'Special Meeting'),
        ('committee', 'Committee Meeting'),
        ('social', 'Social Event'),
        ('education', 'Educational Session'),
        ('networking', 'Networking Event')
    ], string='Meeting Type', required=True, default='general', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Location and Format
    location = fields.Char(
        string='Location',
        help="Physical location of the meeting"
    )
    address = fields.Text(
        string='Full Address',
        help="Complete address with directions"
    )
    is_virtual = fields.Boolean(
        string='Virtual Meeting',
        default=False,
        help="Meeting conducted online"
    )
    meeting_url = fields.Char(
        string='Meeting URL',
        help="Online meeting link (Zoom, Teams, etc.)"
    )
    access_code = fields.Char(
        string='Access Code',
        help="Password or access code for virtual meeting"
    )
    
    # Agenda and Content
    agenda = fields.Html(
        string='Agenda',
        help="Meeting agenda and topics to be discussed"
    )
    presentation_materials = fields.Binary(
        string='Presentation Materials',
        help="Presentation files or materials"
    )
    materials_filename = fields.Char(
        string='Materials Filename'
    )
    
    # Post-Meeting Information
    minutes = fields.Html(
        string='Meeting Minutes',
        help="Minutes and notes from the meeting"
    )
    action_items = fields.Html(
        string='Action Items',
        help="Action items and follow-ups from the meeting"
    )
    next_meeting_date = fields.Datetime(
        string='Next Meeting Date',
        help="Scheduled date for next meeting"
    )
    
    # Attendance Management
    attendee_ids = fields.Many2many(
        'res.partner',
        'meeting_attendee_rel',
        'meeting_id',
        'partner_id',
        string='Attendees',
        help="Members who attended the meeting"
    )
    invited_ids = fields.Many2many(
        'res.partner',
        'meeting_invited_rel',
        'meeting_id',
        'partner_id',
        string='Invited Members',
        help="Members invited to the meeting"
    )
    rsvp_ids = fields.One2many(
        'membership.chapter.meeting.rsvp',
        'meeting_id',
        string='RSVPs'
    )
    
    # Statistics
    invited_count = fields.Integer(
        string='Invited Count',
        compute='_compute_attendance_stats'
    )
    rsvp_yes_count = fields.Integer(
        string='RSVP Yes',
        compute='_compute_attendance_stats'
    )
    rsvp_no_count = fields.Integer(
        string='RSVP No',
        compute='_compute_attendance_stats'
    )
    rsvp_maybe_count = fields.Integer(
        string='RSVP Maybe',
        compute='_compute_attendance_stats'
    )
    attended_count = fields.Integer(
        string='Attended Count',
        compute='_compute_attendance_stats'
    )
    attendance_rate = fields.Float(
        string='Attendance Rate %',
        compute='_compute_attendance_stats',
        help="Percentage of invited members who attended"
    )
    
    # Meeting Organization
    organizer_id = fields.Many2one(
        'res.partner',
        string='Organizer',
        help="Person organizing the meeting"
    )
    secretary_id = fields.Many2one(
        'res.partner',
        string='Secretary',
        help="Person taking minutes"
    )
    facilitator_id = fields.Many2one(
        'res.partner',
        string='Facilitator',
        help="Person facilitating the meeting"
    )
    
    # Budget and Costs
    estimated_cost = fields.Monetary(
        string='Estimated Cost',
        currency_field='currency_id',
        help="Estimated cost for the meeting"
    )
    actual_cost = fields.Monetary(
        string='Actual Cost',
        currency_field='currency_id',
        help="Actual cost incurred"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('invited_ids', 'attendee_ids', 'rsvp_ids.response')
    def _compute_attendance_stats(self):
        for meeting in self:
            meeting.invited_count = len(meeting.invited_ids)
            meeting.attended_count = len(meeting.attendee_ids)
            
            # RSVP counts
            rsvps = meeting.rsvp_ids
            meeting.rsvp_yes_count = len(rsvps.filtered(lambda r: r.response == 'yes'))
            meeting.rsvp_no_count = len(rsvps.filtered(lambda r: r.response == 'no'))
            meeting.rsvp_maybe_count = len(rsvps.filtered(lambda r: r.response == 'maybe'))
            
            # Attendance rate
            if meeting.invited_count > 0:
                meeting.attendance_rate = (meeting.attended_count / meeting.invited_count) * 100
            else:
                meeting.attendance_rate = 0

    @api.constrains('meeting_date')
    def _check_meeting_date(self):
        for meeting in self:
            if meeting.meeting_date and meeting.meeting_date < fields.Datetime.now():
                if meeting.state == 'draft':
                    raise ValidationError(_("Cannot schedule meeting in the past."))

    def action_publish(self):
        """Publish meeting and send invitations"""
        for meeting in self:
            if meeting.state == 'draft':
                meeting.state = 'published'
                meeting._send_meeting_invitations()
                meeting.message_post(body=_("Meeting published and invitations sent."))

    def action_confirm(self):
        """Confirm meeting"""
        for meeting in self:
            if meeting.state == 'published':
                meeting.state = 'confirmed'
                meeting.message_post(body=_("Meeting confirmed."))

    def action_complete(self):
        """Mark meeting as completed"""
        for meeting in self:
            if meeting.state == 'confirmed':
                meeting.state = 'completed'
                meeting.message_post(body=_("Meeting completed."))

    def action_cancel(self):
        """Cancel meeting"""
        for meeting in self:
            if meeting.state in ['draft', 'published', 'confirmed']:
                meeting.state = 'cancelled'
                meeting._send_cancellation_notice()
                meeting.message_post(body=_("Meeting cancelled."))

    def _send_meeting_invitations(self):
        """Send meeting invitations to invited members"""
        template = self.env.ref('ams_membership_chapter.email_template_meeting_invitation', False)
        if template:
            for member in self.invited_ids:
                if member.email:
                    # Create RSVP record
                    rsvp = self.env['membership.chapter.meeting.rsvp'].create({
                        'meeting_id': self.id,
                        'partner_id': member.id,
                        'response': 'pending'
                    })
                    # Send invitation with RSVP link
                    try:
                        template.with_context(rsvp_id=rsvp.id).send_mail(self.id, force_send=True)
                    except Exception as e:
                        _logger.warning(f"Failed to send meeting invitation to {member.email}: {e}")

    def _send_cancellation_notice(self):
        """Send cancellation notice to invited members"""
        template = self.env.ref('ams_membership_chapter.email_template_meeting_cancellation', False)
        if template:
            for member in self.invited_ids:
                if member.email:
                    try:
                        template.send_mail(self.id, force_send=True)
                    except Exception as e:
                        _logger.warning(f"Failed to send cancellation notice to {member.email}: {e}")

    def action_send_reminder(self):
        """Send meeting reminder"""
        template = self.env.ref('ams_membership_chapter.email_template_meeting_reminder', False)
        if template:
            for member in self.invited_ids:
                if member.email:
                    try:
                        template.send_mail(self.id, force_send=True)
                    except Exception as e:
                        _logger.warning(f"Failed to send reminder to {member.email}: {e}")
        self.message_post(body=_("Meeting reminders sent."))

    def action_view_rsvps(self):
        """View RSVPs for this meeting"""
        self.ensure_one()
        return {
            'name': f"RSVPs - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.meeting.rsvp',
            'view_mode': 'tree,form',
            'domain': [('meeting_id', '=', self.id)],
            'context': {'default_meeting_id': self.id},
        }

    def action_auto_invite_chapter_members(self):
        """Auto-invite all active chapter members"""
        self.ensure_one()
        # Get chapter members, filter safely
        chapter_members = self.chapter_id.member_ids
        if chapter_members:
            self.invited_ids = [(6, 0, chapter_members.ids)]
            self.message_post(body=_("All chapter members have been invited."))
        else:
            self.message_post(body=_("No chapter members found to invite."))

    @api.model
    def send_meeting_reminders(self):
        """Cron job to send meeting reminders 24 hours before"""
        tomorrow = fields.Datetime.now() + timedelta(hours=24)
        start_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        meetings = self.search([
            ('meeting_date', '>=', start_time),
            ('meeting_date', '<=', end_time),
            ('state', '=', 'confirmed')
        ])
        
        for meeting in meetings:
            try:
                meeting.action_send_reminder()
            except Exception as e:
                _logger.error(f"Failed to send reminder for meeting {meeting.id}: {e}")
        
        _logger.info(f"Sent reminders for {len(meetings)} meetings")


class ChapterMeetingRSVP(models.Model):
    _name = 'membership.chapter.meeting.rsvp'
    _description = 'Meeting RSVP'
    _rec_name = 'partner_id'

    meeting_id = fields.Many2one(
        'membership.chapter.meeting',
        string='Meeting',
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        help="Member responding to invitation"
    )
    response = fields.Selection([
        ('pending', 'Pending'),
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe')
    ], string='Response', default='pending', required=True)
    
    response_date = fields.Datetime(
        string='Response Date',
        help="When the response was recorded"
    )
    notes = fields.Text(
        string='Notes',
        help="Additional notes from the member"
    )
    
    # RSVP Token for email links
    rsvp_token = fields.Char(
        string='RSVP Token',
        default=lambda self: self._generate_rsvp_token(),
        help="Unique token for RSVP links"
    )

    def _generate_rsvp_token(self):
        """Generate unique RSVP token"""
        import uuid
        return str(uuid.uuid4())

    def action_rsvp_yes(self):
        """RSVP Yes"""
        self.write({
            'response': 'yes',
            'response_date': fields.Datetime.now()
        })

    def action_rsvp_no(self):
        """RSVP No"""
        self.write({
            'response': 'no',
            'response_date': fields.Datetime.now()
        })

    def action_rsvp_maybe(self):
        """RSVP Maybe"""
        self.write({
            'response': 'maybe',
            'response_date': fields.Datetime.now()
        })


class MembershipChapter(models.Model):
    _inherit = 'membership.chapter'

    # Meeting Management
    meeting_ids = fields.One2many(
        'membership.chapter.meeting',
        'chapter_id',
        string='Meetings'
    )
    meeting_count = fields.Integer(
        string='Meetings Count',
        compute='_compute_meeting_count'
    )
    next_meeting_date = fields.Datetime(
        string='Next Meeting',
        compute='_compute_next_meeting'
    )
    last_meeting_date = fields.Datetime(
        string='Last Meeting',
        compute='_compute_last_meeting'
    )
    
    # Meeting Settings
    default_meeting_duration = fields.Float(
        string='Default Meeting Duration (Hours)',
        default=2.0,
        help="Default duration for chapter meetings"
    )
    meeting_day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Regular Meeting Day', help="Regular day of week for meetings")
    
    meeting_time = fields.Float(
        string='Regular Meeting Time',
        help="Regular time for meetings (24-hour format)"
    )
    
    # Meeting Statistics
    total_meetings_held = fields.Integer(
        string='Total Meetings Held',
        compute='_compute_meeting_statistics'
    )
    average_attendance = fields.Float(
        string='Average Attendance Rate',
        compute='_compute_meeting_statistics'
    )

    @api.depends('meeting_ids')
    def _compute_meeting_count(self):
        for chapter in self:
            chapter.meeting_count = len(chapter.meeting_ids)

    @api.depends('meeting_ids.meeting_date', 'meeting_ids.state')
    def _compute_next_meeting(self):
        for chapter in self:
            next_meetings = chapter.meeting_ids.filtered(
                lambda m: m.meeting_date > fields.Datetime.now() and m.state in ['published', 'confirmed']
            ).sorted('meeting_date')
            chapter.next_meeting_date = next_meetings[0].meeting_date if next_meetings else False

    @api.depends('meeting_ids.meeting_date', 'meeting_ids.state')
    def _compute_last_meeting(self):
        for chapter in self:
            past_meetings = chapter.meeting_ids.filtered(
                lambda m: m.meeting_date < fields.Datetime.now() and m.state == 'completed'
            ).sorted('meeting_date', reverse=True)
            chapter.last_meeting_date = past_meetings[0].meeting_date if past_meetings else False

    @api.depends('meeting_ids.state', 'meeting_ids.attendance_rate')
    def _compute_meeting_statistics(self):
        for chapter in self:
            completed_meetings = chapter.meeting_ids.filtered(lambda m: m.state == 'completed')
            chapter.total_meetings_held = len(completed_meetings)
            
            if completed_meetings:
                chapter.average_attendance = sum(completed_meetings.mapped('attendance_rate')) / len(completed_meetings)
            else:
                chapter.average_attendance = 0

    def action_view_meetings(self):
        """View chapter meetings"""
        self.ensure_one()
        return {
            'name': f"Meetings - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.meeting',
            'view_mode': 'tree,form,calendar',
            'domain': [('chapter_id', '=', self.id)],
            'context': {'default_chapter_id': self.id},
        }

    def action_schedule_meeting(self):
        """Schedule a new meeting"""
        self.ensure_one()
        return {
            'name': f"Schedule Meeting - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.chapter.meeting',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_chapter_id': self.id,
                'default_organizer_id': self.manager_id.id if self.manager_id else False,
                'default_duration': self.default_meeting_duration,
            },
        }