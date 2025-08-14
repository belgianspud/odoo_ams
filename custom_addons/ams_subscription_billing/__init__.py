# -*- coding: utf-8 -*-
from . import models
from . import wizard
from odoo import fields

def post_init_hook(env):
    """Post-installation hook to set up AMS subscription billing"""
    
    try:
        # Step 1: Enable billing automation on existing active subscriptions
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
        
        # Step 3: Set up default billing configuration
        _setup_default_billing_configuration(env)
        
        # Step 4: Set up default dunning sequences
        _setup_default_dunning_sequences(env)
        
        # Step 5: Configure payment retry settings
        _setup_payment_retry_configuration(env)
        
        # Step 6: Validate billing setup
        validation = _validate_billing_setup(env)
        
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
        
        # Step 7: Mark setup as completed
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
    """Create billing schedules for existing subscriptions"""
    
    created_count = 0
    
    try:
        # Find active subscriptions without billing schedules
        subscriptions_without_schedules = env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('billing_schedule_ids', '=', False)
        ])
        
        for subscription in subscriptions_without_schedules:
            try:
                # Create billing schedule for this subscription
                schedule = env['ams.billing.schedule'].create({
                    'subscription_id': subscription.id,
                    'billing_frequency': subscription.subscription_period,
                    'next_billing_date': subscription.next_billing_date or fields.Date.today(),
                    'auto_invoice': True,
                    'auto_payment': subscription.enable_auto_payment,
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


def _setup_default_billing_configuration(env):
    """Set up default billing configuration parameters"""
    
    try:
        # Default billing settings
        default_configs = {
            'ams_billing.default_invoice_terms': 'Due immediately for individual memberships, Net 30 for enterprise',
            'ams_billing.grace_period_days': '7',
            'ams_billing.auto_suspend_after_grace': 'true',
            'ams_billing.allow_partial_payments': 'false',
            'ams_billing.proration_enabled': 'true',
            'ams_billing.weekend_billing_adjustment': 'next_business_day',
            'ams_billing.batch_size': '100',
            'ams_billing.email_notifications': 'true',
            'ams_billing.invoice_auto_send': 'true',
            'ams_billing.payment_retry_enabled': 'true',
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
            'func': '_setup_default_billing_configuration',
            'line': '0',
        })


def _setup_default_dunning_sequences(env):
    """Set up default dunning sequences"""
    
    try:
        # Check if default dunning sequence exists
        existing_sequence = env['ams.dunning.sequence'].search([
            ('name', '=', 'Default Dunning Sequence')
        ], limit=1)
        
        if not existing_sequence:
            # Create default dunning sequence
            sequence = env['ams.dunning.sequence'].create({
                'name': 'Default Dunning Sequence',
                'description': 'Standard 3-step dunning process for all memberships',
                'is_default': True,
                'active': True,
            })
            
            # Create dunning steps
            steps_data = [
                {
                    'sequence': 10,
                    'name': 'Friendly Reminder',
                    'days_after_due': 3,
                    'email_template_id': env.ref('ams_subscription_billing.email_template_dunning_reminder', False).id if env.ref('ams_subscription_billing.email_template_dunning_reminder', False) else False,
                    'action_type': 'email',
                    'description': 'Friendly reminder about overdue payment',
                },
                {
                    'sequence': 20,
                    'name': 'Warning Notice',
                    'days_after_due': 10,
                    'email_template_id': env.ref('ams_subscription_billing.email_template_dunning_warning', False).id if env.ref('ams_subscription_billing.email_template_dunning_warning', False) else False,
                    'action_type': 'email',
                    'description': 'Warning notice with suspension threat',
                },
                {
                    'sequence': 30,
                    'name': 'Final Notice',
                    'days_after_due': 20,
                    'email_template_id': env.ref('ams_subscription_billing.email_template_dunning_final', False).id if env.ref('ams_subscription_billing.email_template_dunning_final', False) else False,
                    'action_type': 'email_and_suspend',
                    'description': 'Final notice before suspension',
                },
            ]
            
            for step_data in steps_data:
                step_data['dunning_sequence_id'] = sequence.id
                env['ams.dunning.step'].create(step_data)
        
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error setting up dunning sequences: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': '_setup_default_dunning_sequences',
            'line': '0',
        })


def _setup_payment_retry_configuration(env):
    """Set up payment retry configuration"""
    
    try:
        # Payment retry settings
        retry_configs = {
            'ams_billing.payment_retry_max_attempts': '3',
            'ams_billing.payment_retry_initial_delay': '24',  # hours
            'ams_billing.payment_retry_exponential_backoff': 'true',
            'ams_billing.payment_retry_backoff_multiplier': '2',
            'ams_billing.payment_retry_max_delay': '168',  # 7 days in hours
            'ams_billing.payment_retry_notify_customer': 'true',
            'ams_billing.payment_retry_notify_admin': 'true',
        }
        
        for key, value in retry_configs.items():
            existing = env['ir.config_parameter'].sudo().get_param(key)
            if not existing:
                env['ir.config_parameter'].sudo().set_param(key, value)
        
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_subscription_billing.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error setting up payment retry configuration: {str(e)}',
            'path': 'ams_subscription_billing',
            'func': '_setup_payment_retry_configuration',
            'line': '0',
        })


def _validate_billing_setup(env):
    """Validate that billing is properly set up"""
    
    issues = []
    
    try:
        # Check if sequences exist
        required_sequences = [
            'ams.billing.schedule',
            'ams.billing.event',
            'ams.payment.retry',
            'ams.dunning.process',
        ]
        
        for seq_code in required_sequences:
            sequence = env['ir.sequence'].search([('code', '=', seq_code)], limit=1)
            if not sequence:
                issues.append(f'Missing sequence: {seq_code}')
        
        # Check if dunning templates exist
        required_templates = [
            'email_template_dunning_reminder',
            'email_template_dunning_warning', 
            'email_template_dunning_final',
        ]
        
        for template_name in required_templates:
            template = env.ref(f'ams_subscription_billing.{template_name}', False)
            if not template:
                issues.append(f'Missing email template: {template_name}')
        
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
    """Cleanup when module is uninstalled"""
    
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
        
        # Cancel all pending payment retries
        pending_retries = env['ams.payment.retry'].search([
            ('state', '=', 'pending')
        ])
        
        if pending_retries:
            pending_retries.write({'state': 'cancelled'})
        
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