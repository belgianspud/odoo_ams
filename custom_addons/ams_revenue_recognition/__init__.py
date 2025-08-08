# -*- coding: utf-8 -*-
from . import models
from . import wizard

def post_init_hook(env):
    """Post-installation hook to configure revenue recognition"""
    
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
            if not hasattr(product, 'auto_create_recognition'):
                continue
                
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
    _create_missing_revenue_schedules(env)
    
    # Activate any draft schedules that should be active
    _activate_draft_schedules(env)


def _create_missing_revenue_schedules(env):
    """Create revenue recognition schedules for existing invoices"""
    
    # Find posted invoices with AMS subscription products that don't have schedules
    posted_invoices = env['account.move'].search([
        ('state', '=', 'posted'),
        ('move_type', '=', 'out_invoice'),
        ('has_ams_products', '=', True)
    ])
    
    created_schedules = env['ams.revenue.schedule']
    
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
                    product_template.revenue_recognition_method != 'immediate'):
                    
                    # Check if schedule already exists
                    existing = env['ams.revenue.schedule'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    
                    if not existing:
                        # Create schedule
                        schedule = product_template.create_recognition_schedule(line)
                        if schedule:
                            created_schedules |= schedule
                            
        except Exception as e:
            # Log error but continue with other invoices
            env['ir.logging'].create({
                'name': 'ams_revenue_recognition.post_init',
                'type': 'server', 
                'level': 'WARNING',
                'message': f'Error creating schedule for invoice {invoice.name}: {str(e)}',
                'path': 'ams_revenue_recognition',
                'func': '_create_missing_revenue_schedules',
                'line': '0',
            })
    
    if created_schedules:
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'INFO', 
            'message': f'Created {len(created_schedules)} revenue recognition schedules for existing invoices',
            'path': 'ams_revenue_recognition',
            'func': '_create_missing_revenue_schedules',
            'line': '0',
        })


def _activate_draft_schedules(env):
    """Activate draft revenue schedules that should be active"""
    
    draft_schedules = env['ams.revenue.schedule'].search([
        ('state', '=', 'draft')
    ])
    
    activated_count = 0
    
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
                
        except Exception as e:
            # Log error but continue
            env['ir.logging'].create({
                'name': 'ams_revenue_recognition.post_init',
                'type': 'server',
                'level': 'WARNING',
                'message': f'Error activating schedule {schedule.id}: {str(e)}',
                'path': 'ams_revenue_recognition', 
                'func': '_activate_draft_schedules',
                'line': '0',
            })
    
    if activated_count > 0:
        env['ir.logging'].create({
            'name': 'ams_revenue_recognition.post_init',
            'type': 'server',
            'level': 'INFO',
            'message': f'Activated {activated_count} revenue recognition schedules',
            'path': 'ams_revenue_recognition',
            'func': '_activate_draft_schedules', 
            'line': '0',
        })


def uninstall_hook(env):
    """Clean up when module is uninstalled"""
    
    # Cancel all active revenue recognition schedules
    active_schedules = env['ams.revenue.schedule'].search([
        ('state', '=', 'active')
    ])
    
    for schedule in active_schedules:
        try:
            # Only cancel if no revenue has been recognized
            if schedule.recognized_amount == 0:
                schedule.action_cancel()
        except Exception:
            # Ignore errors during uninstall
            pass
    
    # Disable auto-create revenue recognition on products
    subscription_products = env['product.template'].search([
        ('is_subscription_product', '=', True),
        ('auto_create_recognition', '=', True)
    ])
    
    subscription_products.write({
        'auto_create_recognition': False,
        'auto_process_recognition': False,
    })
    
    env['ir.logging'].create({
        'name': 'ams_revenue_recognition.uninstall',
        'type': 'server',
        'level': 'INFO',
        'message': 'AMS Revenue Recognition module uninstalled successfully',
        'path': 'ams_revenue_recognition',
        'func': 'uninstall_hook',
        'line': '0',
    })