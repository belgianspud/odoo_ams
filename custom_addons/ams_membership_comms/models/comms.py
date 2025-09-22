from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipComms(models.Model):
    _name = 'membership.comms'
    _description = 'Membership Communications'
    _order = 'sent_date desc'
    _rec_name = 'subject'

    # Basic Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        help="The member who received this communication"
    )
    membership_id = fields.Many2one(
        'membership.membership',
        string='Related Membership',
        help="The membership this communication relates to"
    )
    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Related Subscription',
        help="The subscription this communication relates to"
    )
    event_id = fields.Many2one(
        'event.event',
        string='Related Event',
        help="The event this communication relates to"
    )
    
    # Communication Details
    comm_type = fields.Selection([
        ('welcome', 'Welcome Message'),
        ('renewal_reminder', 'Renewal Reminder'),
        ('payment_reminder', 'Payment Reminder'),
        ('lapsed_notice', 'Lapsed Notice'),
        ('event_confirmation', 'Event Confirmation'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('general', 'General Communication'),
    ], string='Communication Type', required=True)
    
    subject = fields.Char(
        string='Subject',
        required=True,
        help="Email subject line"
    )
    body = fields.Html(
        string='Body',
        help="Email body content"
    )
    
    # Status and Tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        help="When this communication should be sent"
    )
    sent_date = fields.Datetime(
        string='Sent Date',
        help="When this communication was actually sent"
    )
    
    # Technical
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help="Template used for this communication"
    )
    mail_message_id = fields.Many2one(
        'mail.message',
        string='Mail Message',
        help="The actual sent email message"
    )
    
    # Auto-generated
    days_before_expiry = fields.Integer(
        string='Days Before Expiry',
        help="For renewal reminders, days before membership expires"
    )

    @api.model_create_multi
    def create(self, vals_list):
        comms = super().create(vals_list)
        for comm in comms:
            if comm.state == 'scheduled' and comm.scheduled_date:
                comm._schedule_sending()
        return comms

    def action_send_now(self):
        """Send communication immediately"""
        for comm in self:
            if comm.state in ['draft', 'scheduled']:
                comm._send_communication()

    def action_schedule(self):
        """Schedule communication for later sending"""
        for comm in self:
            if comm.state == 'draft' and comm.scheduled_date:
                comm.state = 'scheduled'
                comm._schedule_sending()

    def action_cancel(self):
        """Cancel scheduled communication"""
        self.write({'state': 'cancelled'})

    def _send_communication(self):
        """Actually send the communication"""
        self.ensure_one()
        
        if not self.partner_id.email:
            self.state = 'failed'
            _logger.warning(f"No email address for partner {self.partner_id.name}")
            return
        
        try:
            if self.template_id:
                # Use template
                self.template_id.send_mail(self.id, force_send=True)
            else:
                # Send custom email
                mail_values = {
                    'subject': self.subject,
                    'body_html': self.body,
                    'email_to': self.partner_id.email,
                    'email_from': self.env.company.email or 'noreply@example.com',
                    'auto_delete': False,
                }
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
                self.mail_message_id = mail.mail_message_id
            
            self.write({
                'state': 'sent',
                'sent_date': fields.Datetime.now()
            })
            
            _logger.info(f"Sent {self.comm_type} communication to {self.partner_id.name}")
            
        except Exception as e:
            self.state = 'failed'
            _logger.error(f"Failed to send communication to {self.partner_id.name}: {str(e)}")

    def _schedule_sending(self):
        """Schedule communication using ir.cron"""
        self.ensure_one()
        # This would integrate with a more sophisticated scheduling system
        # For now, we'll rely on the cron job to check scheduled communications

    @api.model
    def send_scheduled_communications(self):
        """Cron job method to send scheduled communications"""
        now = fields.Datetime.now()
        
        scheduled_comms = self.search([
            ('state', '=', 'scheduled'),
            ('scheduled_date', '<=', now)
        ])
        
        sent_count = 0
        for comm in scheduled_comms:
            comm._send_communication()
            if comm.state == 'sent':
                sent_count += 1
        
        _logger.info(f"Sent {sent_count} scheduled communications")

    @api.model
    def generate_renewal_reminders(self):
        """Generate renewal reminder communications"""
        today = fields.Date.today()
        reminder_days = [30, 15, 7, 1]  # Days before expiry to send reminders
        
        for days in reminder_days:
            target_date = today + timedelta(days=days)
            
            # Find memberships expiring on target date
            memberships = self.env['membership.membership'].search([
                ('state', '=', 'active'),
                ('end_date', '=', target_date)
            ])
            
            for membership in memberships:
                # Check if reminder already sent
                existing = self.search([
                    ('membership_id', '=', membership.id),
                    ('comm_type', '=', 'renewal_reminder'),
                    ('days_before_expiry', '=', days),
                    ('state', 'in', ['sent', 'scheduled'])
                ])
                
                if not existing:
                    self._create_renewal_reminder(membership, days)

    def _create_renewal_reminder(self, membership, days_before):
        """Create a renewal reminder communication"""
        template = self.env.ref('membership_comms.email_template_renewal_reminder', False)
        
        subject = f"Membership Renewal Reminder - {days_before} days"
        if days_before == 1:
            subject = "Urgent: Membership Expires Tomorrow"
        elif days_before == 0:
            subject = "Membership Expires Today"
        
        self.create({
            'partner_id': membership.partner_id.id,
            'membership_id': membership.id,
            'comm_type': 'renewal_reminder',
            'subject': subject,
            'days_before_expiry': days_before,
            'template_id': template.id if template else False,
            'scheduled_date': fields.Datetime.now(),
            'state': 'scheduled'
        })

    @api.model
    def generate_lapsed_notices(self):
        """Generate lapsed member notices"""
        today = fields.Date.today()
        grace_period = 30  # Days after expiry
        
        # Find memberships that lapsed exactly 'grace_period' days ago
        lapsed_date = today - timedelta(days=grace_period)
        
        memberships = self.env['membership.membership'].search([
            ('state', '=', 'lapsed'),
            ('end_date', '=', lapsed_date)
        ])
        
        template = self.env.ref('membership_comms.email_template_lapsed_notice', False)
        
        for membership in memberships:
            # Check if notice already sent
            existing = self.search([
                ('membership_id', '=', membership.id),
                ('comm_type', '=', 'lapsed_notice'),
                ('state', 'in', ['sent', 'scheduled'])
            ])
            
            if not existing:
                self.create({
                    'partner_id': membership.partner_id.id,
                    'membership_id': membership.id,
                    'comm_type': 'lapsed_notice',
                    'subject': 'We Miss You - Membership Lapsed',
                    'template_id': template.id if template else False,
                    'scheduled_date': fields.Datetime.now(),
                    'state': 'scheduled'
                })

    @api.model
    def generate_welcome_messages(self):
        """Generate welcome messages for new members"""
        # Find new memberships created in the last day
        yesterday = fields.Date.today() - timedelta(days=1)
        
        new_memberships = self.env['membership.membership'].search([
            ('create_date', '>=', yesterday),
            ('state', '=', 'active')
        ])
        
        template = self.env.ref('membership_comms.email_template_welcome', False)
        
        for membership in new_memberships:
            # Check if welcome already sent
            existing = self.search([
                ('membership_id', '=', membership.id),
                ('comm_type', '=', 'welcome'),
                ('state', 'in', ['sent', 'scheduled'])
            ])
            
            if not existing:
                self.create({
                    'partner_id': membership.partner_id.id,
                    'membership_id': membership.id,
                    'comm_type': 'welcome',
                    'subject': 'Welcome to Our Organization!',
                    'template_id': template.id if template else False,
                    'scheduled_date': fields.Datetime.now(),
                    'state': 'scheduled'
                })


class ResPartner(models.Model):
    _inherit = 'res.partner'

    communication_ids = fields.One2many(
        'membership.comms',
        'partner_id',
        string='Communications'
    )
    last_communication_date = fields.Datetime(
        string='Last Communication',
        compute='_compute_last_communication'
    )
    communication_count = fields.Integer(
        string='Communication Count',
        compute='_compute_communication_count'
    )

    @api.depends('communication_ids.sent_date')
    def _compute_last_communication(self):
        for partner in self:
            sent_comms = partner.communication_ids.filtered(lambda c: c.state == 'sent')
            if sent_comms:
                partner.last_communication_date = max(sent_comms.mapped('sent_date'))
            else:
                partner.last_communication_date = False

    @api.depends('communication_ids')
    def _compute_communication_count(self):
        for partner in self:
            partner.communication_count = len(partner.communication_ids)

    def action_view_communications(self):
        """View communications for this partner"""
        self.ensure_one()
        return {
            'name': f"Communications - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'membership.comms',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }


class Membership(models.Model):
    _inherit = 'membership.membership'

    communication_ids = fields.One2many(
        'membership.comms',
        'membership_id',
        string='Communications'
    )


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)
        
        # Send event confirmation emails
        for registration in registrations:
            registration._send_event_confirmation()
        
        return registrations

    def _send_event_confirmation(self):
        """Send event confirmation email"""
        template = self.env.ref('membership_comms.email_template_event_confirmation', False)
        
        if template and self.partner_id.email:
            self.env['membership.comms'].create({
                'partner_id': self.partner_id.id,
                'event_id': self.event_id.id,
                'comm_type': 'event_confirmation',
                'subject': f'Event Registration Confirmation - {self.event_id.name}',
                'template_id': template.id,
                'scheduled_date': fields.Datetime.now(),
                'state': 'scheduled'
            })


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to send payment confirmations"""
        result = super().action_post()
        
        for move in self:
            if move.move_type == 'out_invoice' and move.membership_id:
                move._send_payment_confirmation()
        
        return result

    def _send_payment_confirmation(self):
        """Send payment confirmation email"""
        template = self.env.ref('membership_comms.email_template_payment_confirmation', False)
        
        if template and self.partner_id.email:
            self.env['membership.comms'].create({
                'partner_id': self.partner_id.id,
                'membership_id': self.membership_id.id,
                'comm_type': 'payment_confirmation',
                'subject': f'Payment Confirmation - Invoice {self.name}',
                'template_id': template.id,
                'scheduled_date': fields.Datetime.now(),
                'state': 'scheduled'
            })