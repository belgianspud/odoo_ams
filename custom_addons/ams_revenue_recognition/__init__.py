# -*- coding: utf-8 -*-
from . import models
from . import wizard

def post_init_hook(env):
    """Post-installation hook to configure revenue recognition"""
    
    try:
        # Enable revenue recognition for existing subscription products
        subscription_products = env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('use_ams_accounting', '=', True)
        ])
        
        if subscription_products:
            # Configure revenue recognition settings
            for product in subscription_products:
                # The revenue recognition method is computed automatically
                # but we can ensure auto-create is enabled
                if hasattr(product, 'auto_create_recognition'):
                    product.write({
                        'auto_create_recognition': True,
                        'auto_process_recognition': True,
                    })
            
            env['ir.logging'].create({
                'name': 'ams_revenue_recognition.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'Configured revenue recognition for {len(subscription_products)} subscription products',
                'path': 'ams_revenue_recognition',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Create revenue recognition schedules for existing posted invoices with subscription products
        created_schedules_count = _create_missing_revenue_schedules(env)
        
        # Activate any draft schedules that should be active
        activated_count = _activate_draft_schedules(env)
        
        # Final summary log
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'INFO',
            'message': f'AMS Revenue Recognition installed successfully. Created {created_schedules_count} schedules, activated {activated_count} schedules.',
            'path': 'ams_revenue_recognition',
            'func': 'post_init_hook',
            'line': '0',
        })
        
    except Exception as e:
        # Log error but don't fail installation
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error in post_init_hook: {str(e)}',
            'path': 'ams_revenue_recognition',
            'func': 'post_init_hook',
            'line': '0',
        })


def _create_missing_revenue_schedules(env):
    """Create revenue recognition schedules for existing invoices"""
    
    created_count = 0
    
    try:
        # Find posted invoices with AMS subscription products that don't have schedules
        posted_invoices = env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('has_ams_products', '=', True)
        ])
        
        for invoice in posted_invoices:
            try:
                # Process each line that needs revenue recognition
                for line in invoice.invoice_line_ids:
                    if not line.product_id:
                        continue
                    
                    product_template = line.product_id.product_tmpl_id
                    
                    # Check if this line needs a revenue schedule
                    if (product_template.is_subscription_product and 
                        product_template.use_ams_accounting and
                        getattr(product_template, 'revenue_recognition_method', 'immediate') != 'immediate'):
                        
                        # Check if schedule already exists
                        existing = env['ams.revenue.schedule'].search([
                            ('invoice_line_id', '=', line.id)
                        ], limit=1)
                        
                        if not existing:
                            # Create schedule
                            try:
                                schedule = product_template.create_recognition_schedule(line)
                                if schedule:
                                    created_count += 1
                            except Exception as line_error:
                                # Log individual line error but continue
                                env['ir.logging'].create({
                                    'name': 'ams_revenue_recognition.post_init',
                                    'type': 'server',
                                    'level': 'WARNING',
                                    'message': f'Error creating schedule for invoice line {line.id}: {str(line_error)}',
                                    'path': 'ams_revenue_recognition',
                                    'func': '_create_missing_revenue_schedules',
                                    'line': '0',
                                })
                                
            except Exception as invoice_error:
                # Log error but continue with other invoices
                env['ir.logging'].create({
                    'name': 'ams_revenue_recognition.post_init',
                    'type': 'server', 
                    'level': 'WARNING',
                    'message': f'Error processing invoice {invoice.name}: {str(invoice_error)}',
                    'path': 'ams_revenue_recognition',
                    'func': '_create_missing_revenue_schedules',
                    'line': '0',
                })
        
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error in _create_missing_revenue_schedules: {str(e)}',
            'path': 'ams_revenue_recognition',
            'func': '_create_missing_revenue_schedules',
            'line': '0',
        })
    
    return created_count


def _activate_draft_schedules(env):
    """Activate draft revenue schedules that should be active"""
    
    activated_count = 0
    
    try:
        draft_schedules = env['ams.revenue.schedule'].search([
            ('state', '=', 'draft')
        ])
        
        for schedule in draft_schedules:
            try:
                # Check if schedule is properly configured
                if (schedule.revenue_account_id and 
                    schedule.total_amount > 0 and
                    schedule.start_date and 
                    schedule.end_date):
                    
                    # Generate recognition lines if not already done
                    if not schedule.recognition_line_ids:
                        schedule._generate_recognition_lines()
                    
                    # Activate the schedule
                    schedule.action_activate()
                    activated_count += 1
                    
            except Exception as schedule_error:
                # Log error but continue
                env['ir.logging'].create({
                    'name': 'ams_revenue_recognition.post_init',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': f'Error activating schedule {schedule.id}: {str(schedule_error)}',
                    'path': 'ams_revenue_recognition', 
                    'func': '_activate_draft_schedules',
                    'line': '0',
                })
    
    except Exception as e:
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error in _activate_draft_schedules: {str(e)}',
            'path': 'ams_revenue_recognition',
            'func': '_activate_draft_schedules',
            'line': '0',
        })
    
    return activated_count


def uninstall_hook(env):
    """Clean up when module is uninstalled"""
    
    try:
        # Cancel all active revenue recognition schedules
        active_schedules = env['ams.revenue.schedule'].search([
            ('state', '=', 'active')
        ])
        
        cancelled_count = 0
        for schedule in active_schedules:
            try:
                # Only cancel if no revenue has been recognized
                if schedule.recognized_amount == 0:
                    schedule.action_cancel()
                    cancelled_count += 1
            except Exception:
                # Ignore errors during uninstall
                pass
        
        # Disable auto-create revenue recognition on products
        subscription_products = env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('auto_create_recognition', '=', True)
        ])
        
        if subscription_products:
            subscription_products.write({
                'auto_create_recognition': False,
                'auto_process_recognition': False,
            })
        
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.uninstall',
            'type': 'server',
            'level': 'INFO',
            'message': f'AMS Revenue Recognition uninstalled successfully. Cancelled {cancelled_count} schedules, disabled recognition on {len(subscription_products)} products.',
            'path': 'ams_revenue_recognition',
            'func': 'uninstall_hook',
            'line': '0',
        })
        
    except Exception as e:
        # Log error but don't fail uninstall
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.uninstall',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error in uninstall_hook: {str(e)}',
            'path': 'ams_revenue_recognition',
            'func': 'uninstall_hook',
            'line': '0',
        })