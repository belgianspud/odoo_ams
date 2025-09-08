# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSCommunicationLog(models.Model):
    """Track all communications sent to members across all channels."""
    _name = 'ams.communication.log'
    _description = 'Communication Log'
    _order = 'sent_date desc, id desc'
    _rec_name = 'display_name'

    # ==========================================
    # CORE IDENTIFICATION FIELDS
    # ==========================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        ondelete='cascade',
        index=True,
        help='Member or contact who received the communication'
    )

    communication_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('mail', 'Mail'),
        ('phone', 'Phone')
    ], string='Communication Type', required=True, help='Method of communication')

    category = fields.Selection([
        ('marketing', 'Marketing'),
        ('membership', 'Membership'),
        ('events', 'Events'),
        ('education', 'Education'),
        ('committee', 'Committee'),
        ('fundraising', 'Fundraising'),
        ('emergency', 'Emergency')
    ], string='Category', required=True, help='Purpose of communication')

    subject = fields.Char(
        string='Subject/Title',
        help='Communication subject line or title'
    )

    # ==========================================
    # DELIVERY TRACKING
    # ==========================================

    sent_date = fields.Datetime(
        string='Sent Date',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help='When the communication was sent'
    )

    delivery_status = fields.Selection([
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('unsubscribed', 'Unsubscribed'),
        ('complained', 'Spam Complaint')
    ], string='Delivery Status', required=True, default='sent', help='Current delivery status')

    delivery_date = fields.Datetime(
        string='Delivery Date',
        help='When the communication was delivered (if different from sent)'
    )

    opened_date = fields.Datetime(
        string='Opened Date',
        help='When the recipient opened the communication (email tracking)'
    )

    clicked_date = fields.Datetime(
        string='Clicked Date',
        help='When the recipient clicked a link in the communication'
    )

    bounce_reason = fields.Char(
        string='Bounce Reason',
        help='Reason for delivery failure or bounce'
    )

    # ==========================================
    # TEMPLATE & CAMPAIGN INTEGRATION
    # ==========================================

    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help='Email template used for this communication'
    )

    campaign_id = fields.Char(
        string='Campaign ID',
        index=True,
        help='External campaign identifier for tracking'
    )

    automation_rule_id = fields.Many2one(
        'ams.automation.rule',
        string='Automation Rule',
        help='Automation rule that triggered this communication'
    )

    # ==========================================
    # RESPONSE & ENGAGEMENT TRACKING
    # ==========================================

    response_tracked = fields.Boolean(
        string='Response Tracking Enabled',
        default=False,
        help='Whether engagement tracking (opens, clicks) is enabled'
    )

    click_count = fields.Integer(
        string='Click Count',
        default=0,
        help='Number of times links were clicked'
    )

    open_count = fields.Integer(
        string='Open Count',
        default=0,
        help='Number of times the communication was opened'
    )

    # ==========================================
    # EXTERNAL SYSTEM INTEGRATION
    # ==========================================

    external_message_id = fields.Char(
        string='External Message ID',
        help='Message ID from external email service or SMS provider'
    )

    external_provider = fields.Char(
        string='External Provider',
        help='Name of external service provider (SendGrid, Twilio, etc.)'
    )

    # ==========================================
    # COMMUNICATION CONTENT & METADATA
    # ==========================================

    body_plain = fields.Text(
        string='Plain Text Body',
        help='Plain text version of the communication content'
    )

    body_html = fields.Html(
        string='HTML Body',
        help='HTML version of the communication content'
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'communication_log_attachment_rel',
        'log_id',
        'attachment_id',
        string='Attachments',
        help='Files attached to this communication'
    )

    # ==========================================
    # COMPUTED & HELPER FIELDS
    # ==========================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    partner_name = fields.Char(
        related='partner_id.name',
        string='Recipient Name',
        readonly=True,
        store=True
    )

    partner_email = fields.Char(
        related='partner_id.email',
        string='Recipient Email',
        readonly=True
    )

    is_member = fields.Boolean(
        related='partner_id.is_member',
        string='Is Member',
        readonly=True
    )

    delivery_successful = fields.Boolean(
        string='Delivery Successful',
        compute='_compute_delivery_successful',
        store=True,
        help='Whether the communication was successfully delivered'
    )

    engagement_score = fields.Float(
        string='Engagement Score',
        compute='_compute_engagement_score',
        store=True,
        help='Calculated engagement score based on opens, clicks, etc.'
    )

    days_since_sent = fields.Integer(
        string='Days Since Sent',
        compute='_compute_days_since_sent',
        help='Number of days since communication was sent'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('partner_id', 'communication_type', 'category', 'subject', 'sent_date')
    def _compute_display_name(self):
        """Compute display name for communication log records."""
        for record in self:
            partner_name = record.partner_id.name or 'Unknown'
            comm_type = dict(record._fields['communication_type'].selection).get(
                record.communication_type, record.communication_type
            )
            category = dict(record._fields['category'].selection).get(
                record.category, record.category
            )
            
            date_str = record.sent_date.strftime('%Y-%m-%d %H:%M') if record.sent_date else 'No Date'
            subject = record.subject[:30] + '...' if record.subject and len(record.subject) > 30 else (record.subject or 'No Subject')
            
            record.display_name = f"{partner_name} - {comm_type} - {category} - {subject} ({date_str})"

    @api.depends('delivery_status')
    def _compute_delivery_successful(self):
        """Compute whether delivery was successful."""
        successful_statuses = ['delivered', 'opened', 'clicked']
        for record in self:
            record.delivery_successful = record.delivery_status in successful_statuses

    @api.depends('delivery_status', 'open_count', 'click_count', 'response_tracked')
    def _compute_engagement_score(self):
        """Compute engagement score based on delivery status and interactions."""
        for record in self:
            score = 0.0
            
            # Base score for delivery
            if record.delivery_status == 'delivered':
                score += 1.0
            elif record.delivery_status in ['opened', 'clicked']:
                score += 2.0
            elif record.delivery_status in ['bounced', 'failed']:
                score = 0.0
            elif record.delivery_status == 'complained':
                score = -1.0
            
            # Bonus for engagement
            if record.open_count > 0:
                score += min(record.open_count * 0.5, 2.0)  # Cap at +2.0
            
            if record.click_count > 0:
                score += min(record.click_count * 1.0, 3.0)  # Cap at +3.0
                
            record.engagement_score = score

    @api.depends('sent_date')
    def _compute_days_since_sent(self):
        """Compute days since communication was sent."""
        today = fields.Date.context_today(self)
        for record in self:
            if record.sent_date:
                sent_date = record.sent_date.date()
                record.days_since_sent = (today - sent_date).days
            else:
                record.days_since_sent = 0

    # ==========================================
    # VALIDATION
    # ==========================================

    @api.constrains('sent_date', 'delivery_date')
    def _validate_dates(self):
        """Validate that delivery date is not before sent date."""
        for record in self:
            if record.delivery_date and record.sent_date:
                if record.delivery_date < record.sent_date:
                    raise ValidationError(
                        "Delivery date cannot be earlier than sent date."
                    )

    @api.constrains('communication_type', 'partner_id')
    def _validate_contact_info(self):
        """Validate that partner has necessary contact info for communication type."""
        for record in self:
            partner = record.partner_id
            
            if record.communication_type == 'email' and not partner.email:
                raise ValidationError(
                    f"Cannot log email communication for {partner.name} - no email address on file."
                )
            elif record.communication_type == 'sms' and not partner.mobile:
                raise ValidationError(
                    f"Cannot log SMS communication for {partner.name} - no mobile phone on file."
                )
            elif record.communication_type == 'phone' and not (partner.phone or partner.mobile):
                raise ValidationError(
                    f"Cannot log phone communication for {partner.name} - no phone number on file."
                )
            elif record.communication_type == 'mail' and not partner.street:
                raise ValidationError(
                    f"Cannot log mail communication for {partner.name} - no address on file."
                )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    @api.model
    def log_communication(self, partner_id, communication_type, category, subject=None, template_id=None, 
                         campaign_id=None, body_plain=None, body_html=None, external_message_id=None):
        """Create a communication log entry."""
        vals = {
            'partner_id': partner_id,
            'communication_type': communication_type,
            'category': category,
            'sent_date': fields.Datetime.now(),
            'delivery_status': 'sent'
        }
        
        if subject:
            vals['subject'] = subject
        if template_id:
            vals['template_id'] = template_id
        if campaign_id:
            vals['campaign_id'] = campaign_id
        if body_plain:
            vals['body_plain'] = body_plain
        if body_html:
            vals['body_html'] = body_html
        if external_message_id:
            vals['external_message_id'] = external_message_id
            
        return self.create(vals)

    def update_delivery_status(self, new_status, bounce_reason=None, delivery_date=None):
        """Update the delivery status of this communication."""
        self.ensure_one()
        
        vals = {'delivery_status': new_status}
        
        if delivery_date:
            vals['delivery_date'] = delivery_date
        elif new_status in ['delivered', 'bounced', 'failed']:
            vals['delivery_date'] = fields.Datetime.now()
            
        if bounce_reason:
            vals['bounce_reason'] = bounce_reason
            
        self.write(vals)
        
        # Update partner communication statistics if needed
        if new_status == 'bounced' and self.communication_type == 'email':
            self._update_partner_bounce_count()
            
        return True

    def track_open(self):
        """Track that this communication was opened."""
        self.ensure_one()
        
        vals = {
            'open_count': self.open_count + 1,
            'opened_date': fields.Datetime.now()
        }
        
        # Update delivery status if not already opened/clicked
        if self.delivery_status not in ['opened', 'clicked']:
            vals['delivery_status'] = 'opened'
            
        self.write(vals)
        return True

    def track_click(self):
        """Track that links in this communication were clicked."""
        self.ensure_one()
        
        vals = {
            'click_count': self.click_count + 1,
            'clicked_date': fields.Datetime.now(),
            'delivery_status': 'clicked'  # Clicking implies opening
        }
        
        # Also track as opened if not already
        if not self.opened_date:
            vals['opened_date'] = fields.Datetime.now()
            vals['open_count'] = max(self.open_count, 1)
            
        self.write(vals)
        return True

    def _update_partner_bounce_count(self):
        """Update partner's bounce count statistics."""
        # This would integrate with partner bounce tracking
        # Implementation depends on partner extension fields
        pass

    # ==========================================
    # REPORTING & ANALYTICS METHODS
    # ==========================================

    @api.model
    def get_delivery_stats(self, date_from=None, date_to=None, campaign_id=None):
        """Get delivery statistics for a date range or campaign."""
        domain = []
        
        if date_from:
            domain.append(('sent_date', '>=', date_from))
        if date_to:
            domain.append(('sent_date', '<=', date_to))
        if campaign_id:
            domain.append(('campaign_id', '=', campaign_id))
            
        communications = self.search(domain)
        
        stats = {
            'total_sent': len(communications),
            'delivered': len(communications.filtered(lambda c: c.delivery_status == 'delivered')),
            'failed': len(communications.filtered(lambda c: c.delivery_status in ['failed', 'bounced'])),
            'opened': len(communications.filtered(lambda c: c.delivery_status in ['opened', 'clicked'])),
            'clicked': len(communications.filtered(lambda c: c.delivery_status == 'clicked')),
            'bounced': len(communications.filtered(lambda c: c.delivery_status == 'bounced')),
        }
        
        # Calculate rates
        if stats['total_sent'] > 0:
            stats['delivery_rate'] = (stats['delivered'] / stats['total_sent']) * 100
            stats['open_rate'] = (stats['opened'] / stats['total_sent']) * 100
            stats['click_rate'] = (stats['clicked'] / stats['total_sent']) * 100
            stats['bounce_rate'] = (stats['bounced'] / stats['total_sent']) * 100
        else:
            stats['delivery_rate'] = 0
            stats['open_rate'] = 0
            stats['click_rate'] = 0
            stats['bounce_rate'] = 0
            
        return stats

    @api.model
    def get_campaign_performance(self, campaign_id):
        """Get detailed performance metrics for a specific campaign."""
        communications = self.search([('campaign_id', '=', campaign_id)])
        
        if not communications:
            return {'error': 'No communications found for this campaign'}
            
        stats = self.get_delivery_stats(campaign_id=campaign_id)
        
        # Add additional campaign-specific metrics
        stats.update({
            'unique_recipients': len(communications.mapped('partner_id')),
            'member_recipients': len(communications.filtered('is_member')),
            'non_member_recipients': len(communications.filtered(lambda c: not c.is_member)),
            'avg_engagement_score': sum(communications.mapped('engagement_score')) / len(communications),
            'communication_types': communications.read_group(
                [('campaign_id', '=', campaign_id)],
                ['communication_type'],
                ['communication_type']
            )
        })
        
        return stats

    # ==========================================
    # INTEGRATION METHODS
    # ==========================================

    @api.model
    def process_webhook_update(self, external_message_id, status_data):
        """Process webhook updates from external email/SMS providers."""
        communication = self.search([
            ('external_message_id', '=', external_message_id)
        ], limit=1)
        
        if not communication:
            return {'error': 'Communication not found'}
            
        # Map external status to internal status
        status_mapping = {
            'delivered': 'delivered',
            'opened': 'opened',
            'clicked': 'clicked',
            'bounced': 'bounced',
            'failed': 'failed',
            'complained': 'complained',
            'unsubscribed': 'unsubscribed'
        }
        
        new_status = status_mapping.get(status_data.get('event'))
        if new_status:
            communication.update_delivery_status(
                new_status,
                bounce_reason=status_data.get('reason'),
                delivery_date=status_data.get('timestamp')
            )
            
        return {'success': True, 'communication_id': communication.id}