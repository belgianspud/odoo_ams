from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Subscription Management Settings
    default_subscription_grace_period = fields.Integer(
        'Default Grace Period (Days)',
        default=30,
        config_parameter='ams_subscriptions.default_grace_period',
        help="Default number of days for grace period after subscription expiry"
    )
    
    default_subscription_suspension_period = fields.Integer(
        'Default Suspension Period (Days)',
        default=60,
        config_parameter='ams_subscriptions.default_suspension_period',
        help="Default number of days before suspension after grace period"
    )
    
    default_subscription_termination_period = fields.Integer(
        'Default Termination Period (Days)',
        default=90,
        config_parameter='ams_subscriptions.default_termination_period',
        help="Default number of days before termination after suspension"
    )
    
    # Renewal Settings
    enable_auto_renewal = fields.Boolean(
        'Enable Auto-Renewal',
        default=True,
        config_parameter='ams_subscriptions.enable_auto_renewal',
        help="Allow subscriptions to be set for automatic renewal"
    )
    
    default_renewal_reminder_days = fields.Integer(
        'Default Renewal Reminder (Days)',
        default=30,
        config_parameter='ams_subscriptions.default_renewal_reminder_days',
        help="Default number of days before expiry to send renewal reminders"
    )
    
    auto_confirm_paid_renewals = fields.Boolean(
        'Auto-Confirm Paid Renewals',
        default=True,
        config_parameter='ams_subscriptions.auto_confirm_paid_renewals',
        help="Automatically confirm renewals when payment is received"
    )
    
    # Email Settings
    subscription_activation_template_id = fields.Many2one(
        'mail.template',
        'Subscription Activation Email',
        domain="[('model', '=', 'ams.subscription')]",
        config_parameter='ams_subscriptions.activation_template_id',
        help="Email template sent when subscription is activated"
    )
    
    renewal_reminder_template_id = fields.Many2one(
        'mail.template',
        'Renewal Reminder Email',
        domain="[('model', '=', 'ams.subscription')]",
        config_parameter='ams_subscriptions.renewal_reminder_template_id',
        help="Email template sent for renewal reminders"
    )
    
    suspension_notification_template_id = fields.Many2one(
        'mail.template',
        'Suspension Notification Email',
        domain="[('model', '=', 'ams.subscription')]",
        config_parameter='ams_subscriptions.suspension_template_id',
        help="Email template sent when subscription is suspended"
    )
    
    termination_notification_template_id = fields.Many2one(
        'mail.template',
        'Termination Notification Email',
        domain="[('model', '=', 'ams.subscription')]",
        config_parameter='ams_subscriptions.termination_template_id',
        help="Email template sent when subscription is terminated"
    )
    
    # Chapter Settings
    require_membership_for_chapters = fields.Boolean(
        'Require Membership for Chapters',
        default=True,
        config_parameter='ams_subscriptions.require_membership_for_chapters',
        help="Require an active membership to join chapters"
    )
    
    auto_create_chapter_products = fields.Boolean(
        'Auto-Create Chapter Products',
        default=True,
        config_parameter='ams_subscriptions.auto_create_chapter_products',
        help="Automatically create products for chapters with fees"
    )
    
    # Financial Settings
    subscription_income_account_id = fields.Many2one(
        'account.account',
        'Subscription Income Account',
        domain="[('user_type_id.name', '=', 'Income'), ('company_id', '=', company_id)]",
        config_parameter='ams_subscriptions.income_account_id',
        help="Default income account for subscription revenue"
    )
    
    track_financial_transactions = fields.Boolean(
        'Track Financial Transactions',
        default=True,
        config_parameter='ams_subscriptions.track_financial_transactions',
        help="Create financial transaction records for subscription payments"
    )
    
    # Integration Settings
    website_integration_enabled = fields.Boolean(
        'Website Integration',
        default=True,
        config_parameter='ams_subscriptions.website_integration_enabled',
        help="Enable subscription products on website"
    )
    
    pos_integration_enabled = fields.Boolean(
        'POS Integration',
        default=True,
        config_parameter='ams_subscriptions.pos_integration_enabled',
        help="Enable subscription products in Point of Sale"
    )
    
    portal_integration_enabled = fields.Boolean(
        'Portal Integration',
        default=True,
        config_parameter='ams_subscriptions.portal_integration_enabled',
        help="Enable subscription management in customer portal"
    )
    
    # Analytics Settings
    enable_subscription_analytics = fields.Boolean(
        'Enable Analytics',
        default=True,
        config_parameter='ams_subscriptions.enable_analytics',
        help="Enable advanced subscription analytics and reporting"
    )
    
    analytics_retention_months = fields.Integer(
        'Analytics Retention (Months)',
        default=24,
        config_parameter='ams_subscriptions.analytics_retention_months',
        help="Number of months to retain detailed analytics data"
    )
    
    # Automation Settings
    enable_cron_jobs = fields.Boolean(
        'Enable Automated Jobs',
        default=True,
        config_parameter='ams_subscriptions.enable_cron_jobs',
        help="Enable automated subscription processing jobs"
    )
    
    cron_execution_time = fields.Selection([
        ('01:00', '1:00 AM'),
        ('02:00', '2:00 AM'),
        ('03:00', '3:00 AM'),
        ('04:00', '4:00 AM'),
        ('05:00', '5:00 AM'),
        ('06:00', '6:00 AM'),
    ], string='Cron Execution Time',
       default='02:00',
       config_parameter='ams_subscriptions.cron_execution_time',
       help="Preferred time for running automated jobs"
    )
    
    # Notification Settings
    notify_admins_on_failures = fields.Boolean(
        'Notify Admins on Failures',
        default=True,
        config_parameter='ams_subscriptions.notify_admins_on_failures',
        help="Send notifications to administrators when automated processes fail"
    )
    
    admin_notification_emails = fields.Char(
        'Admin Notification Emails',
        config_parameter='ams_subscriptions.admin_notification_emails',
        help="Comma-separated list of email addresses for admin notifications"
    )
    
    # Member Portal Settings
    allow_member_renewal = fields.Boolean(
        'Allow Member Self-Renewal',
        default=True,
        config_parameter='ams_subscriptions.allow_member_renewal',
        help="Allow members to renew their own subscriptions through portal"
    )
    
    allow_member_chapter_selection = fields.Boolean(
        'Allow Chapter Selection',
        default=True,
        config_parameter='ams_subscriptions.allow_member_chapter_selection',
        help="Allow members to join/leave chapters through portal"
    )
    
    show_member_directory = fields.Boolean(
        'Show Member Directory',
        default=False,
        config_parameter='ams_subscriptions.show_member_directory',
        help="Show member directory in portal (privacy considerations)"
    )
    
    # Data Management
    archive_old_subscriptions_days = fields.Integer(
        'Archive Old Subscriptions (Days)',
        default=1095,  # 3 years
        config_parameter='ams_subscriptions.archive_old_subscriptions_days',
        help="Number of days after termination to archive subscription records"
    )
    
    purge_draft_subscriptions_days = fields.Integer(
        'Purge Draft Subscriptions (Days)',
        default=90,
        config_parameter='ams_subscriptions.purge_draft_subscriptions_days',
        help="Number of days to keep draft subscriptions before purging"
    )
    
    @api.model
    def get_values(self):
        """Override to add custom parameter retrieval"""
        res = super().get_values()
        
        # Get template IDs as integers
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        template_fields = [
            'subscription_activation_template_id',
            'renewal_reminder_template_id', 
            'suspension_notification_template_id',
            'termination_notification_template_id',
            'subscription_income_account_id'
        ]
        
        for field in template_fields:
            param_name = f'ams_subscriptions.{field.replace("_id", "")}'
            value = ICPSudo.get_param(param_name, False)
            if value and value.isdigit():
                res[field] = int(value)
        
        return res
    
    def set_values(self):
        """Override to add custom parameter setting"""
        super().set_values()
        
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        # Set template IDs
        template_fields = [
            'subscription_activation_template_id',
            'renewal_reminder_template_id',
            'suspension_notification_template_id', 
            'termination_notification_template_id',
            'subscription_income_account_id'
        ]
        
        for field in template_fields:
            param_name = f'ams_subscriptions.{field.replace("_id", "")}'
            value = getattr(self, field)
            ICPSudo.set_param(param_name, value.id if value else False)
    
    def action_create_default_email_templates(self):
        """Create default email templates for subscription management"""
        template_data = [
            {
                'name': 'AMS: Subscription Activated',
                'subject': 'Welcome! Your {{ object.subscription_type_id.name }} is now active',
                'body_html': '''
                <p>Dear {{ object.partner_id.name }},</p>
                <p>Your subscription to <strong>{{ object.subscription_type_id.name }}</strong> has been activated!</p>
                <p><strong>Subscription Details:</strong></p>
                <ul>
                    <li>Start Date: {{ object.start_date }}</li>
                    <li>End Date: {{ object.end_date }}</li>
                    <li>Amount: {{ object.amount }} {{ object.currency_id.symbol }}</li>
                </ul>
                <p>Thank you for being a valued member of our association.</p>
                <p>Best regards,<br/>The Association Team</p>
                ''',
                'model_id': self.env.ref('ams_subscriptions.model_ams_subscription').id,
            },
            {
                'name': 'AMS: Renewal Reminder',
                'subject': 'Renewal Reminder: {{ object.subscription_type_id.name }}',
                'body_html': '''
                <p>Dear {{ object.partner_id.name }},</p>
                <p>This is a friendly reminder that your <strong>{{ object.subscription_type_id.name }}</strong> 
                   subscription will expire on {{ object.end_date }}.</p>
                <p>To ensure uninterrupted access to member benefits, please renew your subscription.</p>
                <p>If you have auto-renewal enabled, we'll process your renewal automatically.</p>
                <p>Questions? Contact us at support@example.com</p>
                <p>Best regards,<br/>The Association Team</p>
                ''',
                'model_id': self.env.ref('ams_subscriptions.model_ams_subscription').id,
            }
        ]
        
        created_count = 0
        for template in template_data:
            existing = self.env['mail.template'].search([
                ('name', '=', template['name']),
                ('model_id', '=', template['model_id'])
            ])
            
            if not existing:
                self.env['mail.template'].create(template)
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Email Templates Created'),
                'message': _('%d email templates were created successfully.') % created_count,
                'type': 'success',
            }
        }
    
    def action_test_cron_jobs(self):
        """Test cron job execution"""
        try:
            # Test subscription expiry check
            subscription_model = self.env['ams.subscription']
            expired_count = subscription_model._cron_check_expiries()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cron Test Successful'),
                    'message': _('Processed %d expired subscriptions.') % expired_count,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cron Test Failed'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                }
            }