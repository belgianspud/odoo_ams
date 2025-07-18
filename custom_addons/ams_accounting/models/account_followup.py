# -*- coding: utf-8 -*-
#############################################################################
#
#    AMS Accounting - Follow-up Management Model
#    Enhanced follow-up system for AMS member collections
#
#############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AccountFollowup(models.Model):
    """Follow-up configuration with AMS-specific features"""
    _name = 'account.followup'
    _description = 'Account Follow-up'
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company, required=True)
    description = fields.Text('Description', translate=True)
    
    # Follow-up Lines
    followup_line_ids = fields.One2many('account.followup.line', 'followup_id', 'Follow-up Lines')
    
    # AMS Integration
    is_ams_followup = fields.Boolean('AMS Follow-up Configuration', default=False,
        help="Enable AMS-specific follow-up features")
    ams_member_focused = fields.Boolean('Member-Focused Approach', default=False,
        help="Use gentler, relationship-focused follow-up for AMS members")
    ams_chapter_specific = fields.Boolean('Chapter-Specific Follow-up', default=False,
        help="Allow chapter-specific follow-up procedures")
    
    # Configuration
    active = fields.Boolean('Active', default=True)
    automatic_followup = fields.Boolean('Automatic Follow-up', default=False,
        help="Automatically send follow-up emails based on schedule")
    
    # Statistics
    partner_count = fields.Integer('Partners', compute='_compute_partner_count')
    
    @api.depends('name')
    def _compute_partner_count(self):
        for followup in self:
            followup.partner_count = self.env['res.partner'].search_count([
                ('followup_id', '=', followup.id)
            ])
    
    def action_view_partners(self):
        """View partners using this follow-up configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Partners',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('followup_id', '=', self.id)],
            'context': {'default_followup_id': self.id}
        }
    
    @api.model
    def _cron_send_followup_emails(self):
        """Cron job to send automated follow-up emails"""
        today = fields.Date.today()
        
        # Find all active follow-up configurations with automatic follow-up enabled
        followup_configs = self.search([
            ('active', '=', True),
            ('automatic_followup', '=', True)
        ])
        
        total_sent = 0
        for config in followup_configs:
            sent_count = config._process_automatic_followups(today)
            total_sent += sent_count
        
        _logger.info(f"Sent {total_sent} automatic follow-up emails")
        return total_sent
    
    def _process_automatic_followups(self, today):
        """Process automatic follow-ups for this configuration"""
        sent_count = 0
        
        # Get partners using this follow-up configuration
        partners = self.env['res.partner'].search([
            ('followup_id', '=', self.id),
            ('active', '=', True)
        ])
        
        for partner in partners:
            try:
                if partner._should_send_followup(today):
                    partner._send_followup_email()
                    sent_count += 1
            except Exception as e:
                _logger.error(f"Failed to send follow-up for partner {partner.name}: {str(e)}")
        
        return sent_count


class AccountFollowupLine(models.Model):
    """Follow-up line configuration with AMS enhancements"""
    _name = 'account.followup.line'
    _description = 'Follow-up Line'
    _order = 'followup_id, delay'

    name = fields.Char('Name', required=True, translate=True)
    followup_id = fields.Many2one('account.followup', 'Follow-up', required=True, ondelete='cascade')
    delay = fields.Integer('Days', required=True,
        help="Number of days after the invoice due date to trigger this follow-up level")
    sequence = fields.Integer('Sequence', default=10)
    
    # Communication Settings
    send_email = fields.Boolean('Send Email', default=True)
    send_letter = fields.Boolean('Send Letter', default=False)
    manual_action = fields.Boolean('Manual Action Required', default=False)
    manual_action_note = fields.Text('Manual Action Note')
    
    # Email Configuration
    email_template_id = fields.Many2one('mail.template', 'Email Template',
        domain="[('model', '=', 'res.partner')]")
    email_subject = fields.Char('Email Subject')
    
    # Actions
    action_type = fields.Selection([
        ('none', 'No Action'),
        ('reminder', 'Send Reminder'),
        ('warning', 'Send Warning'),
        ('final_notice', 'Send Final Notice'),
        ('suspend', 'Suspend Account'),
        ('collection', 'Forward to Collection')
    ], string='Action Type', default='reminder')
    
    # AMS Integration
    ams_gentle_approach = fields.Boolean('AMS Gentle Approach', default=False,
        help="Use gentler language appropriate for member relationships")
    ams_chapter_notification = fields.Boolean('Notify Chapter', default=False,
        help="Notify the member's chapter about this follow-up")
    ams_suspend_benefits = fields.Boolean('Suspend Member Benefits', default=False,
        help="Suspend membership benefits at this level")
    
    # Additional Fields
    description = fields.Text('Description', translate=True)
    company_id = fields.Many2one('res.company', related='followup_id.company_id', store=True)
    
    def get_email_subject(self, partner):
        """Get email subject for this follow-up level"""
        if self.email_subject:
            return self.email_subject
        
        level_names = {
            'reminder': 'Payment Reminder',
            'warning': 'Payment Warning',
            'final_notice': 'Final Payment Notice',
            'suspend': 'Account Suspension Notice',
            'collection': 'Collection Notice'
        }
        
        base_subject = level_names.get(self.action_type, 'Payment Notice')
        
        if self.ams_gentle_approach:
            return f"{base_subject} - {partner.name}"
        else:
            return f"{base_subject.upper()} - {partner.name}"
    
    def get_followup_context(self, partner):
        """Get context for follow-up email template"""
        return {
            'partner': partner,
            'followup_line': self,
            'company': self.company_id,
            'today': fields.Date.today(),
            'overdue_amount': partner.total_due,
            'days_overdue': self.delay,
            'is_ams_member': partner.total_subscription_count > 0,
            'ams_gentle': self.ams_gentle_approach,
        }


class ResPartnerFollowup(models.Model):
    """Enhanced partner model with AMS follow-up integration"""
    _inherit = 'res.partner'
    
    # Follow-up Configuration
    followup_id = fields.Many2one('account.followup', 'Follow-up Configuration',
        help="Follow-up procedure to use for this partner")
    followup_level = fields.Integer('Current Follow-up Level', default=0,
        help="Current follow-up level for this partner")
    last_followup_date = fields.Date('Last Follow-up Date',
        help="Date of the last follow-up sent")
    next_followup_date = fields.Date('Next Follow-up Date', compute='_compute_next_followup_date',
        help="Date when next follow-up should be sent")
    
    # Follow-up Status
    followup_status = fields.Selection([
        ('none', 'No Follow-up Needed'),
        ('reminder', 'Reminder Sent'),
        ('warning', 'Warning Sent'),
        ('final', 'Final Notice Sent'),
        ('suspended', 'Account Suspended'),
        ('collection', 'In Collection')
    ], string='Follow-up Status', default='none', compute='_compute_followup_status', store=True)
    
    # AMS Follow-up Integration
    ams_suspend_benefits = fields.Boolean('AMS Benefits Suspended', default=False,
        help="Member benefits have been suspended due to non-payment")
    ams_collection_exempt = fields.Boolean('Exempt from Collection', default=False,
        help="Exempt this member from aggressive collection procedures")
    ams_preferred_communication = fields.Selection([
        ('email', 'Email'),
        ('letter', 'Letter'),
        ('phone', 'Phone'),
        ('in_person', 'In Person')
    ], string='Preferred Communication', default='email')
    
    # Overdue Analysis
    total_due = fields.Float('Total Due', compute='_compute_overdue_amounts', store=True)
    overdue_30 = fields.Float('0-30 Days', compute='_compute_overdue_amounts', store=True)
    overdue_60 = fields.Float('31-60 Days', compute='_compute_overdue_amounts', store=True)
    overdue_90 = fields.Float('61-90 Days', compute='_compute_overdue_amounts', store=True)
    overdue_120 = fields.Float('90+ Days', compute='_compute_overdue_amounts', store=True)
    
    @api.depends('last_followup_date', 'followup_id', 'followup_level')
    def _compute_next_followup_date(self):
        """Compute when next follow-up should be sent"""
        for partner in self:
            if not partner.followup_id or not partner.last_followup_date:
                partner.next_followup_date = False
                continue
            
            # Find next follow-up line
            next_lines = partner.followup_id.followup_line_ids.filtered(
                lambda l: l.sequence > partner.followup_level
            ).sorted('sequence')
            
            if next_lines:
                next_line = next_lines[0]
                partner.next_followup_date = partner.last_followup_date + timedelta(days=next_line.delay)
            else:
                partner.next_followup_date = False
    
    @api.depends('followup_level', 'followup_id')
    def _compute_followup_status(self):
        """Compute current follow-up status"""
        for partner in self:
            if not partner.followup_id or partner.followup_level == 0:
                partner.followup_status = 'none'
                continue
            
            current_line = partner.followup_id.followup_line_ids.filtered(
                lambda l: l.sequence == partner.followup_level
            )
            
            if current_line:
                partner.followup_status = current_line.action_type
            else:
                partner.followup_status = 'none'
    
    @api.depends('invoice_ids', 'invoice_ids.amount_residual', 'invoice_ids.invoice_date_due')
    def _compute_overdue_amounts(self):
        """Compute overdue amounts by aging buckets"""
        for partner in self:
            today = fields.Date.today()
            
            overdue_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and 
                           inv.state == 'posted' and 
                           inv.amount_residual > 0 and
                           inv.invoice_date_due and
                           inv.invoice_date_due < today
            )
            
            partner.total_due = sum(overdue_invoices.mapped('amount_residual'))
            
            # Age buckets
            partner.overdue_30 = sum(
                inv.amount_residual for inv in overdue_invoices 
                if (today - inv.invoice_date_due).days <= 30
            )
            partner.overdue_60 = sum(
                inv.amount_residual for inv in overdue_invoices 
                if 30 < (today - inv.invoice_date_due).days <= 60
            )
            partner.overdue_90 = sum(
                inv.amount_residual for inv in overdue_invoices 
                if 60 < (today - inv.invoice_date_due).days <= 90
            )
            partner.overdue_120 = sum(
                inv.amount_residual for inv in overdue_invoices 
                if (today - inv.invoice_date_due).days > 90
            )
    
    def _should_send_followup(self, today):
        """Determine if follow-up should be sent today"""
        if not self.followup_id or not self.total_due or self.total_due <= 0:
            return False
        
        if not self.next_followup_date or self.next_followup_date > today:
            return False
        
        # Check if member is exempt from collection
        if self.ams_collection_exempt and self.followup_status in ('collection', 'suspended'):
            return False
        
        return True
    
    def _send_followup_email(self):
        """Send follow-up email to partner"""
        if not self.followup_id:
            return False
        
        # Get next follow-up line
        next_lines = self.followup_id.followup_line_ids.filtered(
            lambda l: l.sequence > self.followup_level
        ).sorted('sequence')
        
        if not next_lines:
            return False
        
        followup_line = next_lines[0]
        
        # Send email if configured
        if followup_line.send_email and followup_line.email_template_id:
            try:
                # Get template context
                ctx = followup_line.get_followup_context(self)
                
                # Send email
                followup_line.email_template_id.with_context(ctx).send_mail(
                    self.id, force_send=True
                )
                
                # Update follow-up tracking
                self.write({
                    'followup_level': followup_line.sequence,
                    'last_followup_date': fields.Date.today(),
                })
                
                # Create activity for manual action
                if followup_line.manual_action:
                    self.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=f"Follow-up Manual Action: {followup_line.name}",
                        note=followup_line.manual_action_note or "Manual follow-up action required",
                        user_id=self.env.user.id,
                        date_deadline=fields.Date.today() + timedelta(days=1)
                    )
                
                # AMS-specific actions
                if followup_line.ams_suspend_benefits:
                    self.ams_suspend_benefits = True
                
                if followup_line.ams_chapter_notification and hasattr(self, 'chapter_ids'):
                    self._notify_chapters_of_followup(followup_line)
                
                _logger.info(f"Follow-up email sent to {self.name} - Level: {followup_line.name}")
                return True
                
            except Exception as e:
                _logger.error(f"Failed to send follow-up email to {self.name}: {str(e)}")
                return False
        
        return False
    
    def _notify_chapters_of_followup(self, followup_line):
        """Notify member's chapters about follow-up action"""
        # This method can be extended to notify chapter administrators
        # about member follow-up actions
        pass
    
    def action_manual_followup(self):
        """Manual follow-up action"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Manual Follow-up - {self.name}',
            'res_model': 'account.followup.manual.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_followup_id': self.followup_id.id,
            }
        }
    
    def action_reset_followup(self):
        """Reset follow-up status"""
        self.write({
            'followup_level': 0,
            'last_followup_date': False,
            'ams_suspend_benefits': False,
        })
        
        # Cancel related activities
        self.activity_ids.filtered(
            lambda a: 'follow-up' in a.summary.lower()
        ).action_done()
    
    def action_view_overdue_invoices(self):
        """View overdue invoices for this partner"""
        today = fields.Date.today()
        
        domain = [
            ('partner_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('amount_residual', '>', 0),
            ('invoice_date_due', '<', today)
        ]
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Overdue Invoices - {self.name}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_group_by_date': 1,
            }
        }
    
    @api.model
    def _cron_update_followup_status(self):
        """Cron job to update follow-up status for all partners"""
        partners = self.search([
            ('active', '=', True),
            ('followup_id', '!=', False),
            ('is_company', '=', False)
        ])
        
        updated_count = 0
        for partner in partners:
            try:
                # Trigger recomputation of overdue amounts
                partner._compute_overdue_amounts()
                partner._compute_followup_status()
                partner._compute_next_followup_date()
                updated_count += 1
            except Exception as e:
                _logger.error(f"Failed to update follow-up status for {partner.name}: {str(e)}")
        
        _logger.info(f"Updated follow-up status for {updated_count} partners")
        return updated_count