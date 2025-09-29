# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards


def post_init_hook(env):
    """Post-installation hook for subscription management module"""
    
    # Create default subscription sequence if it doesn't exist
    sequence = env['ir.sequence'].search([('code', '=', 'subscription.subscription')])
    if not sequence:
        env['ir.sequence'].create({
            'name': 'Subscription',
            'code': 'subscription.subscription',
            'prefix': 'SUB',
            'padding': 5,
            'number_next': 1,
            'number_increment': 1,
        })
    
    # Set up default configuration
    config_params = [
        ('subscription.default_trial_period', '14'),
        ('subscription.billing_reminder_days', '3'),
        ('subscription.auto_post_invoices', 'True'),
        ('subscription.send_welcome_email', 'True'),
        ('subscription.settings.grace_period_days', '7'),
        ('subscription.settings.max_billing_retries', '3'),
    ]
    
    for key, value in config_params:
        if not env['ir.config_parameter'].get_param(key):
            env['ir.config_parameter'].set_param(key, value)
    
    # Create default product category for subscription services
    try:
        category = env['product.category'].search([('name', '=', 'Subscription Services')])
        if not category:
            parent = env.ref('product.product_category_all', raise_if_not_found=False)
            if parent:
                env['product.category'].create({
                    'name': 'Subscription Services',
                    'parent_id': parent.id,
                })
    except Exception as e:
        # Category creation is optional, log and continue
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"Could not create Subscription Services category: {e}")


def uninstall_hook(env):
    """Pre-uninstallation hook for subscription management module"""
    
    # Clean up configuration parameters
    config_params = [
        'subscription.default_trial_period',
        'subscription.billing_reminder_days',
        'subscription.auto_post_invoices',
        'subscription.send_welcome_email',
        'subscription.settings.grace_period_days',
        'subscription.settings.max_billing_retries',
    ]
    
    for key in config_params:
        param = env['ir.config_parameter'].search([('key', '=', key)])
        if param:
            param.unlink()
    
    # Disable cron jobs
    cron_jobs = [
        'subscription_management.cron_subscription_billing',
        'subscription_management.cron_subscription_trial_expiry',
        'subscription_management.cron_subscription_expiry',
        'subscription_management.cron_subscription_auto_renew',
        'subscription_management.cron_subscription_billing_reminders',
        'subscription_management.cron_subscription_usage_update',
    ]
    
    for cron_ref in cron_jobs:
        try:
            cron = env.ref(cron_ref, raise_if_not_found=False)
            if cron:
                cron.write({'active': False})
        except:
            pass  # Cron job may not exist