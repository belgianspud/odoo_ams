# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipChapter(models.Model):
    _name = 'ams.membership.chapter'
    _description = 'Chapter Memberships (Placeholder for ams_chapters module)'
    _inherit = 'ams.membership.base'
    _rec_name = 'name'

    # Chapter-specific fields (placeholder structure)
    chapter_id = fields.Many2one('ams.chapter', 'Chapter', 
                                help="Will be implemented in ams_chapters module")
    chapter_code = fields.Char('Chapter Code', help="Temporary field until ams_chapters module")
    chapter_name = fields.Char('Chapter Name', help="Temporary field until ams_chapters module")
    chapter_location = fields.Char('Chapter Location', help="Geographic area served by chapter")
    
    # Relationship to Primary Membership
    primary_membership_id = fields.Many2one('ams.membership.membership', 'Primary Membership',
                                          help="Primary association membership required for chapter membership")
    
    # Chapter-specific features
    local_voting_rights = fields.Boolean('Local Voting Rights', default=True)
    committee_access = fields.Boolean('Committee Access', default=True)
    local_event_access = fields.Boolean('Local Event Access', default=True)
    newsletter_subscription = fields.Boolean('Chapter Newsletter', default=True)
    
    # Leadership and Involvement
    leadership_role = fields.Selection([
        ('member', 'Member'),
        ('committee', 'Committee Member'),
        ('board', 'Board Member'),
        ('officer', 'Officer'),
        ('president', 'President'),
        ('past_president', 'Past President')
    ], string='Leadership Role', default='member')
    
    committee_memberships = fields.Text('Committee Memberships')
    volunteer_hours = fields.Float('Volunteer Hours')
    
    # Meeting and Participation
    meeting_attendance_rate = fields.Float('Meeting Attendance Rate (%)', default=0.0)
    last_meeting_attended = fields.Date('Last Meeting Attended')
    total_meetings_attended = fields.Integer('Total Meetings Attended', default=0)
    
    # Chapter-specific dues (if different from primary)
    chapter_dues = fields.Float('Chapter Dues', default=0.0)
    dues_paid_separately = fields.Boolean('Dues Paid Separately', default=False,
                                        help="Chapter dues are separate from primary membership")

    @api.onchange('primary_membership_id')
    def _onchange_primary_membership(self):
        """Set partner based on primary membership"""
        if self.primary_membership_id:
            self.partner_id = self.primary_membership_id.partner_id

    def write(self, vals):
        """Override to ensure partner consistency"""
        if 'primary_membership_id' in vals:
            primary_membership = self.env['ams.membership.membership'].browse(vals['primary_membership_id'])
            vals['partner_id'] = primary_membership.partner_id.id
        
        return super().write(vals)

    # Action Methods
    def action_view_primary_membership(self):
        """View the primary membership"""
        self.ensure_one()
        
        if not self.primary_membership_id:
            raise UserError(_("No primary membership linked."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Primary Membership'),
            'res_model': 'ams.membership.membership',
            'res_id': self.primary_membership_id.id,
            'view_mode': 'form',
        }

    def action_record_meeting_attendance(self):
        """Record meeting attendance"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Meeting Attendance'),
            'res_model': 'ams.chapter.meeting.attendance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_chapter_membership_id': self.id,
            }
        }

    def action_update_leadership_role(self):
        """Update leadership role"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Leadership Role'),
            'res_model': 'ams.chapter.leadership.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_chapter_membership_id': self.id,
                'default_current_role': self.leadership_role,
            }
        }

    def action_view_chapter_activities(self):
        """View chapter activities and events"""
        self.ensure_one()
        
        # Placeholder - will be implemented in ams_chapters module
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Chapter Activities'),
                'message': _('Chapter activities and events will be available in the ams_chapters module.'),
                'type': 'info'
            }
        }

    # Chapter-specific Methods
    def record_meeting_attendance(self, meeting_date, attended=True):
        """Record meeting attendance"""
        self.ensure_one()
        
        if attended:
            self.total_meetings_attended += 1
            self.last_meeting_attended = meeting_date
            
            # Recalculate attendance rate (placeholder calculation)
            # In full implementation, this would be based on total meetings held
            total_meetings_held = 12  # Placeholder - monthly meetings
            self.meeting_attendance_rate = (self.total_meetings_attended / total_meetings_held) * 100
        
        # Log the attendance
        self.message_post(
            body=_("Meeting attendance recorded: %s on %s") % (
                "Present" if attended else "Absent", 
                meeting_date
            ),
            message_type='notification'
        )

    def update_volunteer_hours(self, hours, description="Volunteer work"):
        """Update volunteer hours"""
        self.ensure_one()
        
        if hours < 0:
            raise UserError(_("Volunteer hours cannot be negative."))
        
        self.volunteer_hours += hours
        
        # Log volunteer hours
        self.message_post(
            body=_("Volunteer hours recorded: %.1f hours - %s") % (hours, description),
            message_type='notification'
        )

    def get_chapter_benefits(self):
        """Get list of chapter-specific benefits"""
        self.ensure_one()
        benefits = []
        
        if self.local_voting_rights:
            benefits.append(_("Local Chapter Voting Rights"))
        if self.committee_access:
            benefits.append(_("Committee Participation"))
        if self.local_event_access:
            benefits.append(_("Local Event Access"))
        if self.newsletter_subscription:
            benefits.append(_("Chapter Newsletter"))
        
        # Leadership benefits
        if self.leadership_role != 'member':
            benefits.append(_("Leadership Role: %s") % dict(self._fields['leadership_role'].selection)[self.leadership_role])
        
        return benefits

    def check_primary_membership_requirement(self):
        """Check if primary membership requirements are met"""
        self.ensure_one()
        
        if not self.primary_membership_id:
            return {
                'valid': False,
                'message': _("Chapter membership requires an active primary association membership.")
            }
        
        if self.primary_membership_id.state not in ['active', 'grace']:
            return {
                'valid': False,
                'message': _("Primary membership must be active or in grace period.")
            }
        
        return {
            'valid': True,
            'message': _("Primary membership requirements satisfied.")
        }

    # Constraints
    @api.constrains('primary_membership_id')
    def _check_primary_membership_required(self):
        """Ensure primary membership is required"""
        for chapter_membership in self:
            if not chapter_membership.primary_membership_id:
                raise ValidationError(_("Chapter membership requires a primary association membership."))

    @api.constrains('primary_membership_id', 'partner_id')
    def _check_partner_consistency(self):
        """Ensure partner matches primary membership"""
        for chapter_membership in self:
            if chapter_membership.primary_membership_id and chapter_membership.partner_id:
                if chapter_membership.partner_id != chapter_membership.primary_membership_id.partner_id:
                    raise ValidationError(_("Chapter membership partner must match primary membership partner."))

    @api.constrains('product_id')
    def _check_product_class(self):
        """Ensure product is a chapter membership product"""
        for membership in self:
            if membership.product_id.product_tmpl_id.product_class != 'chapter':
                raise ValidationError(_("Product must be a chapter membership product class."))

    @api.constrains('meeting_attendance_rate')
    def _check_attendance_rate(self):
        """Validate attendance rate"""
        for membership in self:
            if membership.meeting_attendance_rate < 0 or membership.meeting_attendance_rate > 100:
                raise ValidationError(_("Meeting attendance rate must be between 0 and 100 percent."))

    @api.constrains('volunteer_hours')
    def _check_volunteer_hours(self):
        """Validate volunteer hours"""
        for membership in self:
            if membership.volunteer_hours < 0:
                raise ValidationError(_("Volunteer hours cannot be negative."))

    @api.constrains('chapter_dues')
    def _check_chapter_dues(self):
        """Validate chapter dues"""
        for membership in self:
            if membership.chapter_dues < 0:
                raise ValidationError(_("Chapter dues cannot be negative."))

    # Placeholder methods for future ams_chapters module integration
    def _get_chapter_meetings(self):
        """Get chapter meetings - placeholder for ams_chapters module"""
        # This will be implemented in the ams_chapters module
        return []

    def _get_chapter_events(self):
        """Get chapter events - placeholder for ams_chapters module"""
        # This will be implemented in the ams_chapters module
        return []

    def _get_chapter_committees(self):
        """Get chapter committees - placeholder for ams_chapters module"""
        # This will be implemented in the ams_chapters module
        return []