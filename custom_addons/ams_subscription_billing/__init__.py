# -*- coding: utf-8 -*-
from . import models
from . import wizard
from odoo import fields

def post_init_hook(env):
    """Simplified post-installation hook to set up basic AMS subscription billing"""
    
    try:
        # Step 1: Enable billing on existing active subscriptions
        active_subscriptions = env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('enable_auto_billing', '=', False)
        ])
        
        if active_subscriptions:
            # Enable auto-billing for active subscriptions
            active_subscriptions.write({'enable_auto_billing': True})
            
            env['ir.logging'].create({
                'name': 'ams_subscription_billing.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'Enabled auto-billing for {len(active_subscriptions)} existing subscriptions',
                'path': 'ams_subscription_billing',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 2: Create billing schedules for subscriptions without them
        created_schedules_count = _create_missing_billing_schedules(env)
        
        # Step 3: Set up basic billing configuration
        _setup_basic_billing_configuration(env)
        
        # Step 4: Validate basic setup
        validation = _validate_basic_billing_setup(env)
        
        if validation['valid']:
            env['ir.logging'].create({
                'name': 'ams_subscription_billing.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'AMS Subscription Billing setup completed successfully. Created {created_schedules_count} billing schedules.',
                'path': 'ams_subscription_billing',
                'func': 'post_init_hook',
                'line': '0',
            })
        else:
            env['ir.logging'].create({
                'name': 'ams_subscription_billing.post_init',
                'type': 'server',
                'level': 'WARNING',
                'message': f'AMS Subscription Billing setup completed with issues: {", ".join(validation["issues"])}',
                'path': 'ams_subscription_billing',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 5: Mark setup as completed
        env['ir.config_parameter'].sudo().set_param('ams_billing.setup.completed', 'true')
        env['ir.config_parameter'].sudo().set_param('ams_billing.setup.completed_date', fields.Datetime.now().isoformat())
        
    except Exception as e:
        # Log any critical errors during setup
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Critical error during AMS billing setup: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': 'post_init_hook',
            'line': '0',
        })


def _create_missing_billing_schedules(env):
    """Create basic billing schedules for existing subscriptions"""
    
    created_count = 0
    
    try:
        # Find active subscriptions without billing schedules
        subscriptions_without_schedules = env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('enable_auto_billing', '=', True),
            ('billing_schedule_ids', '=', False)
        ])
        
        for subscription in subscriptions_without_schedules:
            try:
                # Create basic billing schedule for this subscription
                schedule = env['ams.billing.schedule'].create({
                    'subscription_id': subscription.id,
                    'billing_frequency': subscription.subscription_period,
                    'next_billing_date': subscription.next_billing_date or fields.Date.today(),
                    'auto_generate_invoice': True,
                    'auto_send_invoice': subscription.auto_send_invoices,
                    'state': 'active',
                })
                
                if schedule:
                    created_count += 1
                    
            except Exception as e:
                # Log individual subscription error but continue
                env['ir.logging'].create({
                    'name': 'ams_subscription_billing.post_init',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': f'Error creating billing schedule for subscription {subscription.name}: {str(e)}',
                    'path': 'ams_subscription_billing',
                    'func': '_create_missing_billing_schedules',
                    'line': '0',
                })
        
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error in _create_missing_billing_schedules: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': '_create_missing_billing_schedules',
            'line': '0',
        })
    
    return created_count


def _setup_basic_billing_configuration(env):
    """Set up basic billing configuration parameters"""
    
    try:
        # Basic billing settings
        default_configs = {
            'ams_billing.auto_send_invoices': 'true',
            'ams_billing.payment_reminder_enabled': 'true',
            'ams_billing.reminder_days': '1,7,14',  # Days after due date to send reminders
            'ams_billing.batch_size': '100',
            'ams_billing.weekend_billing_adjustment': 'next_business_day',
        }
        
        for key, value in default_configs.items():
            existing = env['ir.config_parameter'].sudo().get_param(key)
            if not existing:
                env['ir.config_parameter'].sudo().set_param(key, value)
        
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error setting up billing configuration: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': '_setup_basic_billing_configuration',
            'line': '0',
        })


def _validate_basic_billing_setup(env):
    """Validate that basic billing is properly set up"""
    
    issues = []
    
    try:
        # Check if sequences exist
        required_sequences = [
            'ams.billing.schedule',
            'ams.billing.event',
        ]
        
        for seq_code in required_sequences:
            sequence = env['ir.sequence'].search([('code', '=', seq_code)], limit=1)
            if not sequence:
                issues.append(f'Missing sequence: {seq_code}')
        
        # Check if basic email template exists
        template = env.ref('ams_subscription_billing.email_template_payment_reminder', False)
        if not template:
            issues.append('Missing payment reminder email template')
        
        # Check for active subscriptions with billing enabled
        active_billing_count = env['ams.subscription'].search_count([
            ('state', '=', 'active'),
            ('enable_auto_billing', '=', True)
        ])
        
        if active_billing_count == 0:
            issues.append('No active subscriptions with billing enabled')
        
    except Exception as e:
        issues.append(f'Validation error: {str(e)}')
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
    }


def uninstall_hook(env):
    """Simplified cleanup when module is uninstalled"""
    
    try:
        # Disable auto-billing on all subscriptions
        subscriptions_with_billing = env['ams.subscription'].search([
            ('enable_auto_billing', '=', True)
        ])
        
        if subscriptions_with_billing:
            subscriptions_with_billing.write({'enable_auto_billing': False})
        
        # Cancel all active billing schedules
        active_schedules = env['ams.billing.schedule'].search([
            ('state', '=', 'active')
        ])
        
        if active_schedules:
            active_schedules.write({'state': 'cancelled'})
        
        # Clean up configuration parameters
        config_params = env['ir.config_parameter'].search([
            ('key', 'like', 'ams_billing.%')
        ])
        
        if config_params:
            config_params.unlink()
        
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.uninstall',
            'type': 'server',
            'level': 'INFO',
            'message': f'AMS Subscription Billing uninstalled. Disabled billing on {len(subscriptions_with_billing)} subscriptions, cancelled {len(active_schedules)} schedules.',
            'path': 'ams_subscription_billing',
            'func': 'uninstall_hook',
            'line': '0',
        })
        
    except Exception as e:
        # Log error but don't fail uninstall
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.uninstall',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error during uninstall: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': 'uninstall_hook',
            'line': '0',
        })