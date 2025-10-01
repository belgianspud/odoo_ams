# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Grace Period Settings
    membership_grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        config_parameter='membership.grace_period_days',
        help='Number of days after expiry before suspension. '
             'Member retains full access during grace period.'
    )
    
    membership_suspend_period_days = fields.Integer(
        string='Suspension Period (Days)',
        default=60,
        config_parameter='membership.suspend_period_days',
        help='Number of days in suspended state before termination. '
             'Member has limited access during suspension.'
    )
    
    membership_terminate_period_days = fields.Integer(
        string='Termination Period (Days)',
        default=90,
        config_parameter='membership.terminate_period_days',
        help='Number of days before final termination. '
             'After this period, membership is permanently terminated.'
    )
    
    # Grace Period Actions
    membership_grace_send_email = fields.Boolean(
        string='Send Grace Period Emails',
        default=True,
        config_parameter='membership.grace_send_email',
        help='Automatically send email notifications during grace period'
    )
    
    membership_grace_email_frequency = fields.Selection([
        ('once', 'Once at Start'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
    ], string='Grace Email Frequency',
       default='weekly',
       config_parameter='membership.grace_email_frequency',
       help='How often to send grace period reminders')
    
    # Suspension Actions
    membership_suspend_restrict_portal = fields.Boolean(
        string='Restrict Portal During Suspension',
        default=True,
        config_parameter='membership.suspend_restrict_portal',
        help='Limit portal access for suspended members'
    )
    
    membership_suspend_send_email = fields.Boolean(
        string='Send Suspension Emails',
        default=True,
        config_parameter='membership.suspend_send_email',
        help='Automatically send email when member is suspended'
    )