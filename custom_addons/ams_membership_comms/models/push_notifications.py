from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import json
import logging
import requests

_logger = logging.getLogger(__name__)


class MobileDevice(models.Model):
    _name = 'mobile.device'
    _description = 'Mobile Device Registration'
    _order = 'last_seen desc'

    # Device Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        help="Device owner"
    )
    device_token = fields.Char(
        string='Device Token',
        required=True,
        index=True,
        help="Unique device token for push notifications"
    )
    device_id = fields.Char(
        string='Device ID',
        help="Unique device identifier"
    )
    
    # Device Details
    platform = fields.Selection([
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
        ('other', 'Other')
    ], string='Platform', required=True, default='android')
    
    app_version = fields.Char(
        string='App Version',
        help="Version of the mobile app"
    )
    os_version = fields.Char(
        string='OS Version',
        help="Operating system version"
    )
    device_model = fields.Char(
        string='Device Model',
        help="Device model (iPhone 12, Samsung Galaxy, etc.)"
    )
    
    # Registration and Activity
    registration_date = fields.Datetime(
        string='Registration Date',
        default=fields.Datetime.now,
        required=True
    )
    last_seen = fields.Datetime(
        string='Last Seen',
        help="Last time device was active"
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="Device is active and can receive notifications"
    )
    
    # Push Notification Settings
    notifications_enabled = fields.Boolean(
        string='Notifications Enabled',
        default=True,
        help="User has enabled push notifications"
    )
    notification_preferences = fields.Text(
        string='Notification Preferences',
        help="JSON string of notification preferences"
    )
    
    # Statistics
    total_notifications_sent = fields.Integer(
        string='Notifications Sent',
        default=0,
        help="Total push notifications sent to this device"
    )
    total_notifications_opened = fields.Integer(
        string='Notifications Opened',
        default=0,
        help="Total notifications opened by user"
    )
    open_rate = fields.Float(
        string='Open Rate %',
        compute='_compute_open_rate',
        help="Percentage of notifications opened"
    )

    @api.depends('total_notifications_sent', 'total_notifications_opened')
    def _compute_open_rate(self):
        for device in self:
            if device.total_notifications_sent > 0:
                device.open_rate = (device.total_notifications_opened / device.total_notifications_sent) * 100
            else:
                device.open_rate = 0

    @api.constrains('device_token')
    def _check_unique_device_token(self):
        for device in self:
            existing = self.search([
                ('device_token', '=', device.device_token),
                ('id', '!=', device.id)
            ])
            if existing:
                # Update existing device instead of creating duplicate
                existing.write({
                    'partner_id': device.partner_id.id,
                    'last_seen': fields.Datetime.now(),
                    'is_active': True
                })
                device.unlink()

    def update_last_seen(self):
        """Update last seen timestamp"""
        self.ensure_one()
        self.last_seen = fields.Datetime.now()

    def deactivate_device(self):
        """Deactivate device (user uninstalled app, etc.)"""
        self.ensure_one()
        self.is_active = False

    def update_notification_preferences(self, preferences):
        """Update notification preferences"""
        self.ensure_one()
        self.notification_preferences = json.dumps(preferences)

    def get_notification_preferences(self):
        """Get notification preferences as dict"""
        self.ensure_one()
        if self.notification_preferences:
            try:
                return json.loads(self.notification_preferences)
            except:
                return {}
        return {}


class PushNotificationCampaign(models.Model):
    _name = 'push.notification.campaign'
    _description = 'Push Notification Campaign'
    _order = 'send_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campaign Information
    name = fields.Char(
        string='Campaign Name',
        required=True,
        tracking=True,
        help="Name of the push notification campaign"
    )
    message_title = fields.Char(
        string='Notification Title',
        required=True,
        help="Title shown in push notification"
    )
    message_body = fields.Text(
        string='Message Body',
        required=True,
        help="Body text of the notification"
    )
    
    # Campaign Settings
    campaign_type = fields.Selection([
        ('immediate', 'Send Immediately'),
        ('scheduled', 'Scheduled'),
        ('triggered', 'Triggered')
    ], string='Campaign Type', default='immediate', required=True)
    
    send_date = fields.Datetime(
        string='Send Date',
        help="When to send the campaign (for scheduled campaigns)"
    )
    
    # Targeting
    target_type = fields.Selection([
        ('all_members', 'All Members'),
        ('membership_level', 'By Membership Level'),
        ('chapter', 'By Chapter'),
        ('custom_segment', 'Custom Segment'),
        ('individual', 'Individual Members')
    ], string='Target Audience', required=True, default='all_members')
    
    membership_level_ids = fields.Many2many(
        'membership.level',
        string='Target Membership Levels'
    )
    chapter_ids = fields.Many2many(
        'membership.chapter',
        string='Target Chapters'
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Target Members'
    )
    
    # Platform Targeting
    target_platforms = fields.Selection([
        ('all', 'All Platforms'),
        ('ios', 'iOS Only'),
        ('android', 'Android Only'),
        ('web', 'Web Only')
    ], string='Platform Target', default='all')
    
    # Advanced Options
    action_type = fields.Selection([
        ('open_app', 'Open App'),
        ('open_url', 'Open URL'),
        ('open_event', 'Open Event'),
        ('custom', 'Custom Action')
    ], string='Action Type', default='open_app')
    
    action_url = fields.Char(
        string='Action URL',
        help="URL to open when notification is tapped"
    )
    action_data = fields.Text(
        string='Action Data',
        help="JSON data for custom actions"
    )
    
    # Campaign Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Statistics
    total_recipients = fields.Integer(
        string='Total Recipients',
        compute='_compute_campaign_stats'
    )
    notifications_sent = fields.Integer(
        string='Notifications Sent',
        default=0
    )
    notifications_delivered = fields.Integer(
        string='Notifications Delivered',
        default=0
    )
    notifications_opened = fields.Integer(
        string='Notifications Opened',
        default=0
    )
    delivery_rate = fields.Float(
        string='Delivery Rate %',
        compute='_compute_rates'
    )
    open_rate = fields.Float(
        string='Open Rate %',
        compute='_compute_rates'
    )
    
    # Related Records
    notification_ids = fields.One2many(
        'push.notification.log',
        'campaign_id',
        string='Notification Logs'
    )

    @api.depends('target_type', 'membership_level_ids', 'chapter_ids', 'partner_ids')
    def _compute_campaign_stats(self):
        for campaign in self:
            recipients = campaign._get_target_devices()
            campaign.total_recipients = len(recipients)

    @api.depends('notifications_sent', 'notifications_delivered', 'notifications_opened')
    def _compute_rates(self):
        for campaign in self:
            if campaign.notifications_sent > 0:
                campaign.delivery_rate = (campaign.notifications_delivered / campaign.notifications_sent) * 100
                campaign.open_rate = (campaign.notifications_opened / campaign.notifications_sent) * 100
            else:
                campaign.delivery_rate = 0
                campaign.open_rate = 0

    def _get_target_devices(self):
        """Get target devices based on campaign settings"""
        self.ensure_one()
        
        # Base domain for active devices
        domain = [('is_active', '=', True), ('notifications_enabled', '=', True)]
        
        # Add platform filter
        if self.target_platforms != 'all':
            domain.append(('platform', '=', self.target_platforms))
        
        # Get target partners
        if self.target_type == 'all_members':
            partners = self.env['res.partner'].search([('is_member', '=', True)])
        elif self.target_type == 'membership_level':
            memberships = self.env['membership.membership'].search([
                ('level_id', 'in', self.membership_level_ids.ids),
                ('state', '=', 'active')
            ])
            partners = memberships.mapped('partner_id')
        elif self.target_type == 'chapter':
            partners = self.chapter_ids.mapped('member_ids')
        elif self.target_type == 'individual':
            partners = self.partner_ids
        else:
            partners = self.env['res.partner'].browse()
        
        # Add partner filter to domain
        if partners:
            domain.append(('partner_id', 'in', partners.ids))
        
        return self.env['mobile.device'].search(domain)

    def action_send_campaign(self):
        """Send push notification campaign"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_("Only draft campaigns can be sent."))
        
        if self.campaign_type == 'scheduled' and not self.send_date:
            raise UserError(_("Scheduled campaigns must have a send date."))
        
        if self.campaign_type == 'scheduled' and self.send_date > fields.Datetime.now():
            self.state = 'scheduled'
            self.message_post(body=_("Campaign scheduled for %s") % self.send_date)
            return
        
        # Send immediately
        self._send_notifications()

    def _send_notifications(self):
        """Send notifications to target devices"""
        self.ensure_one()
        
        self.state = 'sending'
        target_devices = self._get_target_devices()
        
        if not target_devices:
            raise UserError(_("No target devices found for this campaign."))
        
        sent_count = 0
        delivered_count = 0
        
        for device in target_devices:
            try:
                # Create notification log
                notification_log = self.env['push.notification.log'].create({
                    'campaign_id': self.id,
                    'device_id': device.id,
                    'partner_id': device.partner_id.id,
                    'title': self.message_title,
                    'body': self.message_body,
                    'action_type': self.action_type,
                    'action_url': self.action_url,
                    'action_data': self.action_data,
                })
                
                # Send push notification
                success = self._send_push_notification(device, notification_log)
                
                if success:
                    delivered_count += 1
                    notification_log.status = 'delivered'
                    device.total_notifications_sent += 1
                else:
                    notification_log.status = 'failed'
                
                sent_count += 1
                
            except Exception as e:
                _logger.error(f"Failed to send push notification to device {device.id}: {str(e)}")
        
        # Update campaign statistics
        self.write({
            'state': 'sent',
            'notifications_sent': sent_count,
            'notifications_delivered': delivered_count
        })
        
        self.message_post(body=_("Campaign sent to %d devices (%d delivered)") % (sent_count, delivered_count))

    def _send_push_notification(self, device, notification_log):
        """Send push notification to specific device"""
        # This is a placeholder implementation
        # In a real implementation, this would integrate with:
        # - Firebase Cloud Messaging (FCM) for Android
        # - Apple Push Notification Service (APNS) for iOS
        # - Web Push API for web notifications
        
        try:
            if device.platform == 'android':
                return self._send_fcm_notification(device, notification_log)
            elif device.platform == 'ios':
                return self._send_apns_notification(device, notification_log)
            elif device.platform == 'web':
                return self._send_web_push_notification(device, notification_log)
            else:
                return False
        except Exception as e:
            _logger.error(f"Push notification send failed: {str(e)}")
            return False

    def _send_fcm_notification(self, device, notification_log):
        """Send FCM notification (placeholder)"""
        # Placeholder implementation
        # Real implementation would use FCM API
        _logger.info(f"Sending FCM notification to {device.device_token}")
        return True

    def _send_apns_notification(self, device, notification_log):
        """Send APNS notification (placeholder)"""
        # Placeholder implementation  
        # Real implementation would use APNS API
        _logger.info(f"Sending APNS notification to {device.device_token}")
        return True

    def _send_web_push_notification(self, device, notification_log):
        """Send web push notification (placeholder)"""
        # Placeholder implementation
        # Real implementation would use Web Push API
        _logger.info(f"Sending web push notification to {device.device_token}")
        return True

    def action_cancel_campaign(self):
        """Cancel scheduled campaign"""
        self.ensure_one()
        
        if self.state not in ['draft', 'scheduled']:
            raise UserError(_("Only draft or scheduled campaigns can be cancelled."))
        
        self.state = 'cancelled'
        self.message_post(body=_("Campaign cancelled."))

    @api.model
    def process_scheduled_campaigns(self):
        """Cron job to process scheduled campaigns"""
        now = fields.Datetime.now()
        scheduled_campaigns = self.search([
            ('state', '=', 'scheduled'),
            ('send_date', '<=', now)
        ])
        
        for campaign in scheduled_campaigns:
            try:
                campaign._send_notifications()
                _logger.info(f"Processed scheduled campaign: {campaign.name}")
            except Exception as e:
                _logger.error(f"Failed to process scheduled campaign {campaign.name}: {str(e)}")


class PushNotificationLog(models.Model):
    _name = 'push.notification.log'
    _description = 'Push Notification Log'
    _order = 'send_date desc'

    # Basic Information
    campaign_id = fields.Many2one(
        'push.notification.campaign',
        string='Campaign',
        ondelete='cascade',
        help="Related campaign"
    )
    device_id = fields.Many2one(
        'mobile.device',
        string='Device',
        required=True,
        help="Target device"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        help="Notification recipient"
    )
    
    # Notification Content
    title = fields.Char(
        string='Title',
        required=True
    )
    body = fields.Text(
        string='Body',
        required=True
    )
    action_type = fields.Char(string='Action Type')
    action_url = fields.Char(string='Action URL')
    action_data = fields.Text(string='Action Data')
    
    # Status and Timestamps
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('opened', 'Opened')
    ], string='Status', default='pending', required=True)
    
    send_date = fields.Datetime(
        string='Send Date',
        default=fields.Datetime.now,
        required=True
    )
    delivered_date = fields.Datetime(string='Delivered Date')
    opened_date = fields.Datetime(string='Opened Date')
    
    # Error Information
    error_message = fields.Text(string='Error Message')

    def action_mark_opened(self):
        """Mark notification as opened"""
        self.ensure_one()
        
        if self.status != 'opened':
            self.write({
                'status': 'opened',
                'opened_date': fields.Datetime.now()
            })
            
            # Update campaign statistics
            if self.campaign_id:
                self.campaign_id.notifications_opened += 1
            
            # Update device statistics
            self.device_id.total_notifications_opened += 1


class PushNotificationTemplate(models.Model):
    _name = 'push.notification.template'
    _description = 'Push Notification Template'
    _order = 'name'

    # Template Information
    name = fields.Char(
        string='Template Name',
        required=True,
        help="Name of the notification template"
    )
    description = fields.Text(
        string='Description',
        help="Description of when to use this template"
    )
    
    # Template Content
    title_template = fields.Char(
        string='Title Template',
        required=True,
        help="Template for notification title (can use variables)"
    )
    body_template = fields.Text(
        string='Body Template',
        required=True,
        help="Template for notification body (can use variables)"
    )
    
    # Default Action
    default_action_type = fields.Selection([
        ('open_app', 'Open App'),
        ('open_url', 'Open URL'),
        ('open_event', 'Open Event'),
        ('custom', 'Custom Action')
    ], string='Default Action', default='open_app')
    
    default_action_url = fields.Char(
        string='Default Action URL'
    )
    
    # Template Settings
    category = fields.Selection([
        ('general', 'General'),
        ('events', 'Events'),
        ('membership', 'Membership'),
        ('payments', 'Payments'),
        ('announcements', 'Announcements'),
        ('reminders', 'Reminders')
    ], string='Category', default='general')
    
    active = fields.Boolean(
        string='Active',
        default=True
    )

    def create_campaign_from_template(self, values=None):
        """Create campaign from this template"""
        self.ensure_one()
        
        if not values:
            values = {}
        
        # Render templates with values
        title = self._render_template(self.title_template, values)
        body = self._render_template(self.body_template, values)
        
        campaign_vals = {
            'name': f"Campaign from {self.name}",
            'message_title': title,
            'message_body': body,
            'action_type': self.default_action_type,
            'action_url': self.default_action_url,
        }
        
        return self.env['push.notification.campaign'].create(campaign_vals)

    def _render_template(self, template, values):
        """Render template with values"""
        if not template or not values:
            return template
        
        try:
            # Simple template rendering (in production, use proper templating)
            result = template
            for key, value in values.items():
                placeholder = f"{{{{{key}}}}}"
                result = result.replace(placeholder, str(value))
            return result
        except Exception:
            return template


# Enhanced Partner model with mobile device tracking
class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Mobile Device Information
    mobile_device_ids = fields.One2many(
        'mobile.device',
        'partner_id',
        string='Mobile Devices'
    )
    active_devices_count = fields.Integer(
        string='Active Devices',
        compute='_compute_device_stats'
    )
    push_notifications_enabled = fields.Boolean(
        string='Push Notifications Enabled',
        compute='_compute_device_stats'
    )
    
    # Push Notification Statistics
    total_push_notifications = fields.Integer(
        string='Push Notifications Received',
        compute='_compute_push_stats'
    )
    push_notification_open_rate = fields.Float(
        string='Push Open Rate %',
        compute='_compute_push_stats'
    )

    @api.depends('mobile_device_ids.is_active')
    def _compute_device_stats(self):
        for partner in self:
            active_devices = partner.mobile_device_ids.filtered('is_active')
            partner.active_devices_count = len(active_devices)
            partner.push_notifications_enabled = any(d.notifications_enabled for d in active_devices)

    @api.depends('mobile_device_ids.total_notifications_sent', 'mobile_device_ids.total_notifications_opened')
    def _compute_push_stats(self):
        for partner in self:
            devices = partner.mobile_device_ids
            partner.total_push_notifications = sum(devices.mapped('total_notifications_sent'))
            
            total_sent = sum(devices.mapped('total_notifications_sent'))
            total_opened = sum(devices.mapped('total_notifications_opened'))
            
            if total_sent > 0:
                partner.push_notification_open_rate = (total_opened / total_sent) * 100
            else:
                partner.push_notification_open_rate = 0

    def action_view_mobile_devices(self):
        """View mobile devices for this partner"""
        self.ensure_one()
        return {
            'name': f"Mobile Devices - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'mobile.device',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }