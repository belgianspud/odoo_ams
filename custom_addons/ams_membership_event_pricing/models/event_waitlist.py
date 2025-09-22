from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class EventWaitlist(models.Model):
    _name = 'event.waitlist'
    _description = 'Event Waitlist'
    _order = 'priority desc, join_date asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    event_id = fields.Many2one(
        'event.event',
        string='Event',
        required=True,
        ondelete='cascade',
        help="Event this waitlist entry is for"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        help="Person on the waitlist"
    )
    
    # Waitlist Details
    join_date = fields.Datetime(
        string='Join Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
        help="When this person joined the waitlist"
    )
    priority = fields.Integer(
        string='Priority',
        compute='_compute_priority',
        store=True,
        help="Priority based on membership level and join date"
    )
    position = fields.Integer(
        string='Waitlist Position',
        compute='_compute_position',
        help="Current position in the waitlist"
    )
    
    # Member Information
    membership_level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        compute='_compute_member_info',
        store=True,
        help="Member's current membership level"
    )
    is_member = fields.Boolean(
        string='Is Member',
        related='partner_id.is_member',
        readonly=True
    )
    
    # Status and Processing
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('notified', 'Notified'),
        ('registered', 'Registered'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='waiting', required=True, tracking=True)
    
    notification_date = fields.Datetime(
        string='Notification Date',
        help="When notification was sent about available spot"
    )
    notification_expires = fields.Datetime(
        string='Notification Expires',
        help="When the notification expires"
    )
    response_hours = fields.Integer(
        string='Response Time (Hours)',
        related='event_id.waitlist_response_hours',
        help="Hours given to respond to notification"
    )
    
    # Registration Information
    registration_id = fields.Many2one(
        'event.registration',
        string='Registration',
        help="Created registration when promoted from waitlist"
    )
    promoted_date = fields.Datetime(
        string='Promoted Date',
        help="When promoted from waitlist to registered"
    )
    
    # Contact Preferences
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        readonly=True
    )
    phone = fields.Char(
        string='Phone',
        related='partner_id.phone',
        readonly=True
    )
    preferred_contact_method = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('both', 'Email and Phone')
    ], string='Preferred Contact Method', default='email')
    
    # Notes
    notes = fields.Text(
        string='Notes',
        help="Additional notes about this waitlist entry"
    )

    @api.depends('partner_id.current_membership_id.level_id')
    def _compute_member_info(self):
        for waitlist in self:
            if waitlist.partner_id.current_membership_id:
                waitlist.membership_level_id = waitlist.partner_id.current_membership_id.level_id
            else:
                waitlist.membership_level_id = False

    @api.depends('membership_level_id.priority', 'join_date', 'is_member')
    def _compute_priority(self):
        for waitlist in self:
            # Base priority on membership level
            if waitlist.membership_level_id:
                base_priority = waitlist.membership_level_id.priority or 10
            elif waitlist.is_member:
                base_priority = 50  # Default member priority
            else:
                base_priority = 100  # Non-member priority
            
            # Add time component (earlier = higher priority)
            # Subtract minutes from join date to create time-based priority
            time_component = int((fields.Datetime.now() - waitlist.join_date).total_seconds() / 60)
            waitlist.priority = base_priority + time_component

    @api.depends('event_id', 'state')
    def _compute_position(self):
        for waitlist in self:
            if waitlist.state == 'waiting':
                higher_priority = self.search([
                    ('event_id', '=', waitlist.event_id.id),
                    ('state', '=', 'waiting'),
                    ('priority', '>', waitlist.priority)
                ])
                same_priority_earlier = self.search([
                    ('event_id', '=', waitlist.event_id.id),
                    ('state', '=', 'waiting'),
                    ('priority', '=', waitlist.priority),
                    ('join_date', '<', waitlist.join_date)
                ])
                waitlist.position = len(higher_priority) + len(same_priority_earlier) + 1
            else:
                waitlist.position = 0

    @api.constrains('event_id', 'partner_id')
    def _check_duplicate_waitlist(self):
        for waitlist in self:
            existing = self.search([
                ('event_id', '=', waitlist.event_id.id),
                ('partner_id', '=', waitlist.partner_id.id),
                ('state', 'in', ['waiting', 'notified']),
                ('id', '!=', waitlist.id)
            ])
            if existing:
                raise ValidationError(_("This person is already on the waitlist for this event."))

    def action_notify_available_spot(self):
        """Notify person about available spot"""
        self.ensure_one()
        
        if self.state != 'waiting':
            raise UserError(_("Only waiting entries can be notified."))
        
        # Set notification expiry
        response_hours = self.event_id.waitlist_response_hours or 24
        notification_expires = fields.Datetime.now() + timedelta(hours=response_hours)
        
        self.write({
            'state': 'notified',
            'notification_date': fields.Datetime.now(),
            'notification_expires': notification_expires
        })
        
        # Send notification email
        self._send_spot_available_notification()
        
        self.message_post(body=_("Spot available notification sent. Expires: %s") % notification_expires)

    def action_register_from_waitlist(self):
        """Register person from waitlist"""
        self.ensure_one()
        
        if self.state != 'notified':
            raise UserError(_("Only notified entries can be registered."))
        
        # Check if event still has spots
        if not self.event_id._has_available_spots():
            raise UserError(_("Event is now full. Cannot register from waitlist."))
        
        # Create registration
        registration_vals = {
            'event_id': self.event_id.id,
            'partner_id': self.partner_id.id,
            'email': self.partner_id.email,
            'phone': self.partner_id.phone,
            'state': 'open',
            'is_paid': False,
            'date_open': fields.Datetime.now(),
        }
        
        registration = self.env['event.registration'].create(registration_vals)
        
        self.write({
            'state': 'registered',
            'registration_id': registration.id,
            'promoted_date': fields.Datetime.now()
        })
        
        self.message_post(body=_("Successfully registered from waitlist."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Event Registration'),
            'res_model': 'event.registration',
            'res_id': registration.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel_waitlist(self):
        """Cancel waitlist entry"""
        self.ensure_one()
        
        if self.state in ['registered']:
            raise UserError(_("Cannot cancel registered entries."))
        
        self.state = 'cancelled'
        self.message_post(body=_("Waitlist entry cancelled."))

    def action_expire_notification(self):
        """Expire notification and move back to waiting"""
        self.ensure_one()
        
        self.state = 'expired'
        self.message_post(body=_("Notification expired. Entry moved to expired status."))

    def _send_spot_available_notification(self):
        """Send email notification about available spot"""
        template = self.env.ref('membership_event_pricing.email_template_waitlist_spot_available', False)
        if template and self.email:
            template.send_mail(self.id, force_send=True)

    @api.model
    def process_expired_notifications(self):
        """Cron job to process expired notifications"""
        expired_notifications = self.search([
            ('state', '=', 'notified'),
            ('notification_expires', '<', fields.Datetime.now())
        ])
        
        for notification in expired_notifications:
            notification.action_expire_notification()
        
        _logger.info(f"Processed {len(expired_notifications)} expired waitlist notifications")

    @api.model
    def auto_promote_from_waitlist(self):
        """Auto-promote people from waitlist when spots become available"""
        # Find events with waitlists and available spots
        events_with_waitlist = self.search([('state', '=', 'waiting')]).mapped('event_id')
        
        for event in events_with_waitlist:
            if event._has_available_spots():
                # Get next person in line
                next_in_line = self.search([
                    ('event_id', '=', event.id),
                    ('state', '=', 'waiting')
                ], order='priority desc, join_date asc', limit=1)
                
                if next_in_line:
                    next_in_line.action_notify_available_spot()


class EventWaitlistSettings(models.Model):
    _name = 'event.waitlist.settings'
    _description = 'Event Waitlist Settings'

    event_id = fields.Many2one(
        'event.event',
        string='Event',
        required=True,
        ondelete='cascade'
    )
    enable_waitlist = fields.Boolean(
        string='Enable Waitlist',
        default=True,
        help="Allow people to join waitlist when event is full"
    )
    max_waitlist_size = fields.Integer(
        string='Maximum Waitlist Size',
        default=0,
        help="Maximum number of people on waitlist (0 = unlimited)"
    )
    response_hours = fields.Integer(
        string='Response Time (Hours)',
        default=24,
        help="Hours given to respond to spot notification"
    )
    member_priority = fields.Boolean(
        string='Member Priority',
        default=True,
        help="Give members priority on waitlist"
    )
    auto_promote = fields.Boolean(
        string='Auto-promote from Waitlist',
        default=True,
        help="Automatically notify next person when spot becomes available"
    )


# Enhanced Event model with waitlist functionality
class Event(models.Model):
    _inherit = 'event.event'

    # Waitlist Configuration
    enable_waitlist = fields.Boolean(
        string='Enable Waitlist',
        default=True,
        help="Allow registrations to waitlist when event is full"
    )
    max_waitlist_size = fields.Integer(
        string='Maximum Waitlist Size',
        default=0,
        help="Maximum number of people on waitlist (0 = unlimited)"
    )
    waitlist_response_hours = fields.Integer(
        string='Waitlist Response Time (Hours)',
        default=24,
        help="Hours given to respond to waitlist notifications"
    )
    member_waitlist_priority = fields.Boolean(
        string='Member Priority on Waitlist',
        default=True,
        help="Give members higher priority on waitlist"
    )
    auto_promote_waitlist = fields.Boolean(
        string='Auto-promote from Waitlist',
        default=True,
        help="Automatically notify next person when spots become available"
    )

    # Waitlist Statistics
    waitlist_ids = fields.One2many(
        'event.waitlist',
        'event_id',
        string='Waitlist'
    )
    waitlist_count = fields.Integer(
        string='Waitlist Count',
        compute='_compute_waitlist_stats'
    )
    waiting_count = fields.Integer(
        string='Currently Waiting',
        compute='_compute_waitlist_stats'
    )
    notified_count = fields.Integer(
        string='Notified Count',
        compute='_compute_waitlist_stats'
    )

    @api.depends('waitlist_ids.state')
    def _compute_waitlist_stats(self):
        for event in self:
            waitlist = event.waitlist_ids
            event.waitlist_count = len(waitlist)
            event.waiting_count = len(waitlist.filtered(lambda w: w.state == 'waiting'))
            event.notified_count = len(waitlist.filtered(lambda w: w.state == 'notified'))

    def _has_available_spots(self):
        """Check if event has available spots"""
        self.ensure_one()
        if self.seats_max == 0:  # Unlimited seats
            return True
        return self.seats_available > 0

    def action_view_waitlist(self):
        """View event waitlist"""
        self.ensure_one()
        return {
            'name': f"Waitlist - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'event.waitlist',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }

    def action_process_waitlist(self):
        """Process waitlist (notify next person if spots available)"""
        self.ensure_one()
        
        if not self._has_available_spots():
            raise UserError(_("Event is full. No spots available."))
        
        next_in_line = self.waitlist_ids.filtered(
            lambda w: w.state == 'waiting'
        ).sorted(lambda w: (-w.priority, w.join_date))
        
        if not next_in_line:
            raise UserError(_("No one is waiting on the waitlist."))
        
        next_in_line[0].action_notify_available_spot()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Next person in waitlist has been notified.'),
                'type': 'success',
            }
        }

    def add_to_waitlist(self, partner_id, preferred_contact='email'):
        """Add person to event waitlist"""
        self.ensure_one()
        
        # Check if waitlist is enabled
        if not self.enable_waitlist:
            raise UserError(_("Waitlist is not enabled for this event."))
        
        # Check waitlist size limit
        if self.max_waitlist_size > 0 and self.waiting_count >= self.max_waitlist_size:
            raise UserError(_("Waitlist is full."))
        
        # Check for existing waitlist entry
        existing = self.waitlist_ids.filtered(
            lambda w: w.partner_id.id == partner_id and w.state in ['waiting', 'notified']
        )
        if existing:
            raise UserError(_("This person is already on the waitlist."))
        
        # Create waitlist entry
        waitlist_entry = self.env['event.waitlist'].create({
            'event_id': self.id,
            'partner_id': partner_id,
            'preferred_contact_method': preferred_contact,
        })
        
        # Send confirmation email
        template = self.env.ref('membership_event_pricing.email_template_waitlist_confirmation', False)
        if template:
            template.send_mail(waitlist_entry.id, force_send=True)
        
        return waitlist_entry


# Enhanced Registration model with waitlist integration
class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # Waitlist Information
    waitlist_entry_id = fields.Many2one(
        'event.waitlist',
        string='Waitlist Entry',
        help="Original waitlist entry if registered from waitlist"
    )
    registered_from_waitlist = fields.Boolean(
        string='From Waitlist',
        compute='_compute_from_waitlist'
    )

    @api.depends('waitlist_entry_id')
    def _compute_from_waitlist(self):
        for registration in self:
            registration.registered_from_waitlist = bool(registration.waitlist_entry_id)

    def action_cancel(self):
        """Override to handle waitlist when registration is cancelled"""
        result = super().action_cancel()
        
        # Auto-promote from waitlist if enabled
        for registration in self:
            if registration.event_id.auto_promote_waitlist:
                # Find next person on waitlist
                next_waitlist = registration.event_id.waitlist_ids.filtered(
                    lambda w: w.state == 'waiting'
                ).sorted(lambda w: (-w.priority, w.join_date))
                
                if next_waitlist:
                    next_waitlist[0].action_notify_available_spot()
        
        return result