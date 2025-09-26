# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipSubscription(models.Model):
    _name = 'ams.membership.subscription'
    _description = 'Publications, Newsletters, and Subscription Services'
    _inherit = 'ams.membership.base'
    _rec_name = 'name'

    # Subscription Type Classification
    subscription_type = fields.Selection([
        ('newsletter', 'Newsletter'),
        ('publication', 'Publication'),
        ('journal', 'Journal'),
        ('magazine', 'Magazine'),
        ('digital_content', 'Digital Content'),
        ('resource_access', 'Resource Access'),
        ('exhibits', 'Exhibits Access'),
        ('advertising', 'Advertising Service'),
        ('sponsorship', 'Sponsorship Package'),
        ('event_booth', 'Event Booth Rental'),
        ('services', 'Professional Services')
    ], string='Subscription Type', compute='_compute_subscription_type', store=True)
    
    # Delivery Preferences
    delivery_method = fields.Selection([
        ('email', 'Email'),
        ('physical_mail', 'Physical Mail'),
        ('digital_download', 'Digital Download'),
        ('online_access', 'Online Access'),
        ('both', 'Email and Physical Mail'),
        ('pickup', 'Pickup'),
        ('courier', 'Courier Delivery')
    ], string='Delivery Method', default='email', required=True)
    
    delivery_address_id = fields.Many2one('res.partner', 'Delivery Address',
                                        help="Specific delivery address if different from member address")
    
    # Content and Format
    content_format = fields.Selection([
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('print', 'Print'),
        ('digital_magazine', 'Digital Magazine'),
        ('video', 'Video Content'),
        ('audio', 'Audio Content'),
        ('interactive', 'Interactive Content'),
        ('archive_access', 'Archive Access')
    ], string='Content Format', default='pdf')
    
    language_preference = fields.Many2one('res.lang', 'Language Preference',
                                        default=lambda self: self.env.lang)
    
    # Publication Schedule
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('on_demand', 'On Demand'),
        ('continuous', 'Continuous Access')
    ], string='Publication Frequency', related='product_id.product_tmpl_id.recurrence_period', readonly=True)
    
    # Issue Tracking
    issues_remaining = fields.Integer('Issues Remaining', default=0)
    total_issues_purchased = fields.Integer('Total Issues Purchased', default=0)
    current_issue_number = fields.Char('Current Issue Number')
    last_issue_sent = fields.Date('Last Issue Sent')
    next_issue_due = fields.Date('Next Issue Due', compute='_compute_next_issue_due')
    
    # Digital Access
    digital_access_granted = fields.Boolean('Digital Access Granted', default=False)
    access_credentials = fields.Char('Access Credentials', groups="ams_foundation.group_ams_staff")
    login_url = fields.Url('Access URL')
    digital_library_access = fields.Boolean('Digital Library Access', default=False)
    
    # Member Benefits Integration
    member_discount_applied = fields.Boolean('Member Discount Applied', default=False)
    member_discount_amount = fields.Float('Member Discount Amount', default=0.0)
    guest_access_allowed = fields.Boolean('Guest Access Allowed', 
                                        related='product_id.product_tmpl_id.guest_purchase_allowed', readonly=True)
    
    # Content Preferences
    topics_of_interest = fields.Text('Topics of Interest')
    content_level = fields.Selection([
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
        ('all_levels', 'All Levels')
    ], string='Content Level', default='all_levels')
    
    # Communication Preferences
    email_notifications = fields.Boolean('Email Notifications', default=True)
    sms_notifications = fields.Boolean('SMS Notifications', default=False)
    marketing_emails = fields.Boolean('Marketing Emails', default=True)
    
    # Archive Access
    archive_access_years = fields.Integer('Archive Access (Years)', default=0,
                                        help="Years of back issues accessible")
    archive_download_limit = fields.Integer('Archive Download Limit', default=0,
                                          help="0 = unlimited")
    downloads_used = fields.Integer('Downloads Used', default=0)
    
    # Subscription Statistics
    open_rate = fields.Float('Email Open Rate (%)', default=0.0, readonly=True)
    click_rate = fields.Float('Click Rate (%)', default=0.0, readonly=True)
    engagement_score = fields.Float('Engagement Score', compute='_compute_engagement_score', store=True)
    last_access_date = fields.Datetime('Last Access Date', readonly=True)
    total_access_count = fields.Integer('Total Access Count', default=0, readonly=True)

    @api.depends('product_id')
    def _compute_subscription_type(self):
        """Determine subscription type based on product class"""
        type_mapping = {
            'newsletter': 'newsletter',
            'publication': 'publication',
            'subscription': 'publication',
            'exhibits': 'exhibits',
            'advertising': 'advertising',
            'sponsorship': 'sponsorship',
            'event_booth': 'event_booth',
            'services': 'services'
        }
        
        for subscription in self:
            if subscription.product_id and subscription.product_id.product_tmpl_id.product_class:
                product_class = subscription.product_id.product_tmpl_id.product_class
                subscription.subscription_type = type_mapping.get(product_class, 'publication')
            else:
                subscription.subscription_type = 'publication'

    def _compute_next_issue_due(self):
        """Compute when next issue is due"""
        for subscription in self:
            if subscription.frequency and subscription.last_issue_sent:
                from datetime import timedelta
                
                if subscription.frequency == 'weekly':
                    delta = timedelta(weeks=1)
                elif subscription.frequency == 'bi_weekly':
                    delta = timedelta(weeks=2)
                elif subscription.frequency == 'monthly':
                    delta = timedelta(days=30)
                elif subscription.frequency == 'quarterly':
                    delta = timedelta(days=90)
                elif subscription.frequency == 'semi_annual':
                    delta = timedelta(days=180)
                elif subscription.frequency == 'annual':
                    delta = timedelta(days=365)
                else:
                    delta = timedelta(days=30)  # Default to monthly
                
                subscription.next_issue_due = subscription.last_issue_sent + delta
            else:
                subscription.next_issue_due = False

    @api.depends('open_rate', 'click_rate', 'total_access_count')
    def _compute_engagement_score(self):
        """Compute overall engagement score"""
        for subscription in self:
            # Simple engagement calculation
            score = 0
            
            if subscription.open_rate > 0:
                score += subscription.open_rate * 0.3
            
            if subscription.click_rate > 0:
                score += subscription.click_rate * 0.5
            
            if subscription.total_access_count > 0:
                # Normalize access count (cap at 100 for scoring)
                access_score = min(subscription.total_access_count, 100)
                score += access_score * 0.2
            
            subscription.engagement_score = min(score, 100)  # Cap at 100

    @api.onchange('delivery_method')
    def _onchange_delivery_method(self):
        """Set defaults based on delivery method"""
        if self.delivery_method in ['email', 'digital_download', 'online_access']:
            self.content_format = 'pdf' if self.delivery_method == 'email' else 'digital_magazine'
            self.digital_access_granted = True
        elif self.delivery_method in ['physical_mail', 'pickup', 'courier']:
            self.content_format = 'print'
            self.digital_access_granted = False

    @api.onchange('subscription_type')
    def _onchange_subscription_type(self):
        """Set defaults based on subscription type"""
        if self.subscription_type == 'newsletter':
            self.delivery_method = 'email'
            self.content_format = 'html'
            self.frequency = 'monthly'
        elif self.subscription_type in ['journal', 'magazine', 'publication']:
            self.delivery_method = 'both'
            self.content_format = 'pdf'
            self.archive_access_years = 2
        elif self.subscription_type == 'digital_content':
            self.delivery_method = 'online_access'
            self.content_format = 'interactive'
            self.digital_library_access = True

    # Action Methods
    def action_send_test_issue(self):
        """Send test issue to subscriber"""
        self.ensure_one()
        
        if not self.partner_id.email:
            raise UserError(_("Member must have an email address to send test issue."))
        
        # This would integrate with email system to send actual content
        self.message_post(
            body=_("Test issue sent to %s") % self.partner_id.email,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test Issue Sent'),
                'message': _('Test issue has been sent to %s') % self.partner_id.email,
                'type': 'success'
            }
        }

    def action_grant_digital_access(self):
        """Grant digital access and generate credentials"""
        self.ensure_one()
        
        if self.digital_access_granted:
            raise UserError(_("Digital access is already granted."))
        
        # Generate access credentials (simplified)
        import secrets
        access_code = secrets.token_urlsafe(8)
        
        self.write({
            'digital_access_granted': True,
            'access_credentials': access_code,
            'login_url': f"https://portal.association.com/login?code={access_code}"
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Digital Access Granted'),
                'message': _('Digital access credentials have been generated and sent to member.'),
                'type': 'success'
            }
        }

    def action_revoke_digital_access(self):
        """Revoke digital access"""
        self.ensure_one()
        
        self.write({
            'digital_access_granted': False,
            'access_credentials': False,
            'login_url': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Digital Access Revoked'),
                'message': _('Digital access has been revoked for this subscription.'),
                'type': 'info'
            }
        }

    def action_update_delivery_preferences(self):
        """Update delivery preferences"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Delivery Preferences'),
            'res_model': 'ams.subscription.delivery.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
            }
        }

    def action_view_archive(self):
        """View available archive issues"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Archive Issues'),
            'res_model': 'ams.subscription.archive',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {
                'default_subscription_id': self.id,
            }
        }

    def action_record_access(self):
        """Record that subscriber accessed content"""
        self.ensure_one()
        
        self.write({
            'last_access_date': fields.Datetime.now(),
            'total_access_count': self.total_access_count + 1
        })
        
        # Update engagement score
        self._compute_engagement_score()

    def action_change_delivery_address(self):
        """Change delivery address"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Delivery Address'),
            'res_model': 'ams.delivery.address.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_subscription_id': self.id,
                'default_current_address_id': self.delivery_address_id.id if self.delivery_address_id else self.partner_id.id,
            }
        }

    # Subscription Management Methods
    def send_issue(self, issue_data=None):
        """Send issue to subscriber"""
        self.ensure_one()
        
        if self.state not in ['active', 'grace']:
            _logger.warning(f"Cannot send issue to inactive subscription {self.name}")
            return False
        
        # Update tracking
        self.write({
            'last_issue_sent': fields.Date.today(),
            'issues_remaining': max(0, self.issues_remaining - 1),
            'current_issue_number': issue_data.get('issue_number', '') if issue_data else ''
        })
        
        # Log issue delivery
        self.message_post(
            body=_("Issue sent via %s") % dict(self._fields['delivery_method'].selection)[self.delivery_method],
            message_type='notification'
        )
        
        return True

    def update_engagement_metrics(self, opened=False, clicked=False):
        """Update engagement metrics from email tracking"""
        self.ensure_one()
        
        # This would be called from email tracking systems
        if opened:
            # Update open rate (simplified calculation)
            total_sent = self.total_issues_purchased or 1
            opens = (self.open_rate * total_sent / 100) + 1
            self.open_rate = (opens / total_sent) * 100
        
        if clicked:
            # Update click rate
            total_sent = self.total_issues_purchased or 1
            clicks = (self.click_rate * total_sent / 100) + 1
            self.click_rate = (clicks / total_sent) * 100

    def check_delivery_eligibility(self):
        """Check if subscription is eligible for delivery"""
        self.ensure_one()
        
        issues = []
        
        if self.state not in ['active', 'grace']:
            issues.append(_("Subscription must be active"))
        
        if self.delivery_method in ['physical_mail', 'courier'] and not self._get_delivery_address():
            issues.append(_("Valid delivery address required"))
        
        if self.delivery_method in ['email', 'digital_download'] and not self.partner_id.email:
            issues.append(_("Email address required for digital delivery"))
        
        if self.issues_remaining <= 0 and self.frequency != 'continuous':
            issues.append(_("No issues remaining in subscription"))
        
        return {
            'eligible': len(issues) == 0,
            'issues': issues
        }

    def _get_delivery_address(self):
        """Get effective delivery address"""
        self.ensure_one()
        return self.delivery_address_id or self.partner_id

    def get_subscription_summary(self):
        """Get subscription summary for portal"""
        self.ensure_one()
        return {
            'type': dict(self._fields['subscription_type'].selection)[self.subscription_type],
            'frequency': dict(self._fields['frequency'].selection)[self.frequency],
            'delivery': dict(self._fields['delivery_method'].selection)[self.delivery_method],
            'format': dict(self._fields['content_format'].selection)[self.content_format],
            'issues_remaining': self.issues_remaining,
            'next_issue': self.next_issue_due,
            'digital_access': self.digital_access_granted,
            'engagement_score': self.engagement_score,
        }

    # Constraints
    @api.constrains('product_id')
    def _check_product_class(self):
        """Ensure product is a subscription-related product"""
        valid_classes = ['subscription', 'newsletter', 'publication', 'exhibits', 
                        'advertising', 'sponsorship', 'event_booth', 'services']
        
        for subscription in self:
            if subscription.product_id.product_tmpl_id.product_class not in valid_classes:
                raise ValidationError(_("Product must be a subscription-related product class."))

    @api.constrains('issues_remaining', 'total_issues_purchased')
    def _check_issue_counts(self):
        """Validate issue counts"""
        for subscription in self:
            if subscription.issues_remaining < 0:
                raise ValidationError(_("Issues remaining cannot be negative."))
            if subscription.total_issues_purchased < 0:
                raise ValidationError(_("Total issues purchased cannot be negative."))

    @api.constrains('open_rate', 'click_rate')
    def _check_engagement_rates(self):
        """Validate engagement rates"""
        for subscription in self:
            if subscription.open_rate < 0 or subscription.open_rate > 100:
                raise ValidationError(_("Open rate must be between 0 and 100 percent."))
            if subscription.click_rate < 0 or subscription.click_rate > 100:
                raise ValidationError(_("Click rate must be between 0 and 100 percent."))

    @api.constrains('archive_access_years', 'archive_download_limit')
    def _check_archive_settings(self):
        """Validate archive settings"""
        for subscription in self:
            if subscription.archive_access_years < 0:
                raise ValidationError(_("Archive access years cannot be negative."))
            if subscription.archive_download_limit < 0:
                raise ValidationError(_("Archive download limit cannot be negative."))

    @api.constrains('downloads_used')
    def _check_download_usage(self):
        """Validate download usage"""
        for subscription in self:
            if subscription.downloads_used < 0:
                raise ValidationError(_("Downloads used cannot be negative."))
            if (subscription.archive_download_limit > 0 and 
                subscription.downloads_used > subscription.archive_download_limit):
                raise ValidationError(_("Downloads used cannot exceed download limit."))

    @api.constrains('delivery_method', 'content_format')
    def _check_delivery_format_compatibility(self):
        """Ensure delivery method and content format are compatible"""
        for subscription in self:
            if subscription.delivery_method in ['physical_mail', 'pickup', 'courier']:
                if subscription.content_format not in ['print']:
                    raise ValidationError(_("Physical delivery requires print format."))
            elif subscription.delivery_method in ['email', 'digital_download']:
                if subscription.content_format in ['print']:
                    raise ValidationError(_("Digital delivery cannot use print format."))