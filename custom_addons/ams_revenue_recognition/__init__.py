# -*- coding: utf-8 -*-
from . import models
from . import wizard
from . import reports

def post_init_hook(env):
    """Post-installation hook to set up AMS revenue recognition"""
    
    # Enable revenue recognition for existing subscription products
    subscription_products = env['product.template'].search([
        ('is_subscription_product', '=', True),
        ('use_ams_accounting', '=', True)
    ])
    
    if subscription_products:
        # Auto-configure revenue recognition for existing products
        for product in subscription_products:
            product._setup_revenue_recognition()
        
    # Create recognition schedules for existing active subscriptions
    active_subscriptions = env['ams.subscription'].search([
        ('state', '=', 'active'),
        ('paid_through_date', '!=', False)
    ])
    
    recognition_schedules_created = 0
    for subscription in active_subscriptions:
        # Check if recognition schedule already exists
        existing_schedule = env['ams.revenue.schedule'].search([
            ('subscription_id', '=', subscription.id),
            ('state', '!=', 'cancelled')
        ], limit=1)
        
        if not existing_schedule and subscription.product_id.product_tmpl_id.use_ams_accounting:
            try:
                # Create recognition schedule for existing subscription
                schedule = env['ams.revenue.schedule'].create_from_subscription(subscription)
                if schedule:
                    recognition_schedules_created += 1
            except Exception as e:
                # Log error but don't fail installation
                env['ir.logging'].create({
                    'name': 'ams_revenue_recognition.post_init',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': f'Failed to create recognition schedule for subscription {subscription.id}: {str(e)}',
                    'path': 'ams_revenue_recognition',
                    'line': '0',
                    'func': 'post_init_hook'
                })
    
    # Log installation summary
    env['ir.logging'].create({
        'name': 'ams_revenue_recognition.post_init',
        'type': 'server', 
        'level': 'INFO',
        'message': f'AMS Revenue Recognition installed successfully. '
                  f'Configured {len(subscription_products)} products, '
                  f'created {recognition_schedules_created} recognition schedules.',
        'path': 'ams_revenue_recognition',
        'line': '0',
        'func': 'post_init_hook'
    })