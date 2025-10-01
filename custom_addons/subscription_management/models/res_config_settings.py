# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Grace Period Settings
    subscription_grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        config_parameter='subscription.grace_period_days',
        help='Number of days after expiry before suspension. '
             'Subscription retains full access during grace period.'
    )
    
    subscription_suspend_period_days = fields.Integer(
        string='Suspension Period (Days)',
        default=60,
        config_parameter='subscription.suspend_period_days',
        help='Number of days in suspended state before termination. '
             'Subscription has limited access during suspension.'
    )
    
    subscription_terminate_period_days = fields.Integer(
        string='Termination Period (Days)',
        default=90,
        config_parameter='subscription.terminate_period_days',
        help='Number of days before final termination. '
             'After this period, subscription is permanently terminated.'
    )
    
    # Grace Period Actions
    subscription_grace_send_email = fields.Boolean(
        string='Send Grace Period Emails',
        default=True,
        config_parameter='subscription.grace_send_email',
        help='Automatically send email notifications during grace period'
    )
    
    subscription_grace_email_frequency = fields.Selection([
        ('once', 'Once at Start'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
    ], string='Grace Email Frequency',
       default='weekly',
       config_parameter='subscription.grace_email_frequency',
       help='How often to send grace period reminders')
    
    # Suspension Actions
    subscription_suspend_restrict_portal = fields.Boolean(
        string='Restrict Portal During Suspension',
        default=True,
        config_parameter='subscription.suspend_restrict_portal',
        help='Limit portal access for suspended subscriptions'
    )
    
    subscription_suspend_send_email = fields.Boolean(
        string='Send Suspension Emails',
        default=True,
        config_parameter='subscription.suspend_send_email',
        help='Automatically send email when subscription is suspended'
    )