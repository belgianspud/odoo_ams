# -*- coding: utf-8 -*-

from . import models
from . import wizard

def _post_init_subscription_integration(cr, registry):
    """
    Post-initialization hook to set up subscription integration with AMS Products Base.
    
    This hook runs after module installation to:
    - Validate integration with ams_products_base
    - Set up default subscription billing periods
    - Configure subscription-specific email templates
    - Initialize subscription analytics data
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Validate that required dependencies are properly installed
    try:
        # Check AMS Products Base integration
        ProductTemplate = env['product.template']
        if not hasattr(ProductTemplate, 'is_ams_product'):
            raise ImportError("AMS Products Base integration not found")
            
        # Check AMS Billing Periods integration
        BillingPeriod = env['ams.billing.period']
        if not BillingPeriod.search_count([]):
            # Create basic billing periods if none exist
            _create_basic_billing_periods(env)
            
        # Initialize subscription-specific configurations
        _setup_subscription_configurations(env)
        
        # Set up default email templates for subscription workflows
        _setup_subscription_email_templates(env)
        
        # Initialize subscription analytics and reporting
        _setup_subscription_analytics(env)
        
        cr.execute("""
            INSERT INTO ir_logging (name, level, dbname, line, func, path, message, create_date)
            VALUES ('ams.subscriptions.products', 'INFO', %s, 0, '_post_init_subscription_integration', 
                   'ams_subscriptions_products/__init__.py', 
                   'AMS Subscriptions Products module initialized successfully', NOW())
        """, (cr.dbname,))
        
    except Exception as e:
        cr.execute("""
            INSERT INTO ir_logging (name, level, dbname, line, func, path, message, create_date)
            VALUES ('ams.subscriptions.products', 'ERROR', %s, 0, '_post_init_subscription_integration',
                   'ams_subscriptions_products/__init__.py',
                   'Failed to initialize AMS Subscriptions Products: %s', NOW())
        """, (cr.dbname, str(e)))
        raise

def _create_basic_billing_periods(env):
    """Create basic billing periods if none exist."""
    BillingPeriod = env['ams.billing.period']
    
    basic_periods = [
        {
            'name': 'Monthly',
            'code': 'MONTHLY',
            'duration_value': 1,
            'duration_unit': 'months',
            'sequence': 10,
            'is_default': False,
            'description': 'Monthly subscription billing cycle',
        },
        {
            'name': 'Quarterly',
            'code': 'QUARTERLY', 
            'duration_value': 3,
            'duration_unit': 'months',
            'sequence': 20,
            'is_default': False,
            'description': 'Quarterly subscription billing cycle',
        },
        {
            'name': 'Annual',
            'code': 'ANNUAL',
            'duration_value': 12,
            'duration_unit': 'months',
            'sequence': 30,
            'is_default': True,
            'description': 'Annual subscription billing cycle',
        },
    ]
    
    for period_data in basic_periods:
        existing = BillingPeriod.search([('code', '=', period_data['code'])], limit=1)
        if not existing:
            BillingPeriod.create(period_data)

def _setup_subscription_configurations(env):
    """Set up subscription-specific system configurations."""
    IrConfigParameter = env['ir.config_parameter']
    
    # Default subscription configurations
    default_configs = {
        'ams.subscription.default_grace_period': '30',  # days
        'ams.subscription.renewal_reminder_days': '30,15,7',  # comma-separated
        'ams.subscription.auto_renewal_enabled': 'True',
        'ams.subscription.prorated_billing_enabled': 'True',
        'ams.subscription.member_portal_enabled': 'True',
        'ams.subscription.analytics_enabled': 'True',
    }
    
    for key, value in default_configs.items():
        existing = IrConfigParameter.search([('key', '=', key)], limit=1)
        if not existing:
            IrConfigParameter.create({
                'key': key,
                'value': value,
            })

def _setup_subscription_email_templates(env):
    """Set up default email templates for subscription workflows."""
    MailTemplate = env['mail.template']
    
    # Check if subscription templates already exist
    existing_templates = MailTemplate.search([
        ('name', 'ilike', 'subscription'),
        ('model', '=', 'sale.subscription')
    ])
    
    if existing_templates:
        return  # Templates already exist
        
    # Create basic subscription email templates
    template_data = [
        {
            'name': 'Subscription Renewal Reminder',
            'model_id': env.ref('sale_subscription.model_sale_subscription').id,
            'subject': 'Your ${object.name} subscription expires soon',
            'body_html': '''
                <p>Dear ${object.partner_id.name},</p>
                <p>Your subscription "${object.name}" will expire on ${object.date}.</p>
                <p>Please renew to continue your access.</p>
                <p>Best regards,<br/>${user.company_id.name}</p>
            ''',
            'auto_delete': False,
        },
        {
            'name': 'Subscription Activated',
            'model_id': env.ref('sale_subscription.model_sale_subscription').id,
            'subject': 'Welcome to ${object.name}',
            'body_html': '''
                <p>Dear ${object.partner_id.name},</p>
                <p>Your subscription "${object.name}" has been activated!</p>
                <p>You can access your benefits through the member portal.</p>
                <p>Best regards,<br/>${user.company_id.name}</p>
            ''',
            'auto_delete': False,
        }
    ]
    
    for template in template_data:
        MailTemplate.create(template)

def _setup_subscription_analytics(env):
    """Initialize subscription analytics and reporting data structures."""
    # This could set up initial analytics views, KPIs, or dashboard configurations
    # For now, we'll just ensure the necessary database structures are in place
    
    # Create or update subscription analytics views if needed
    cr = env.cr
    
    # Create subscription revenue view for analytics
    cr.execute("""
        CREATE OR REPLACE VIEW subscription_revenue_analysis AS
        SELECT 
            ss.id as subscription_id,
            ss.partner_id,
            ss.name as subscription_name,
            ss.date_start,
            ss.date as date_end,
            ss.recurring_total as monthly_recurring_revenue,
            ss.recurring_total * 12 as annual_recurring_revenue,
            CASE 
                WHEN ss.stage_category = 'progress' THEN 'active'
                WHEN ss.stage_category = 'closed' THEN 'cancelled'
                ELSE 'other'
            END as subscription_status,
            pt.ams_product_behavior,
            pt.name as product_name
        FROM sale_subscription ss
        LEFT JOIN sale_subscription_line ssl ON ssl.analytic_account_id = ss.id
        LEFT JOIN product_template pt ON pt.id = ssl.product_id
        WHERE pt.is_ams_product = true
        AND pt.ams_product_behavior = 'subscription'
    """)

def _uninstall_cleanup_subscriptions(cr, registry):
    """
    Cleanup hook when module is uninstalled.
    
    This hook:
    - Removes subscription behavior from existing products
    - Cleans up subscription-specific configurations
    - Preserves data but removes functionality
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Update products to remove subscription behavior
        subscription_products = env['product.template'].search([
            ('ams_product_behavior', '=', 'subscription')
        ])
        
        if subscription_products:
            # Convert subscription products back to generic AMS products
            subscription_products.write({
                'ams_product_behavior': False,
                # Keep is_subscription_product for data preservation
                # but remove subscription-specific enhancements
            })
        
        # Remove subscription-specific configurations
        IrConfigParameter = env['ir.config_parameter']
        subscription_configs = IrConfigParameter.search([
            ('key', 'like', 'ams.subscription.%')
        ])
        subscription_configs.unlink()
        
        # Log cleanup completion
        cr.execute("""
            INSERT INTO ir_logging (name, level, dbname, line, func, path, message, create_date)
            VALUES ('ams.subscriptions.products', 'INFO', %s, 0, '_uninstall_cleanup_subscriptions',
                   'ams_subscriptions_products/__init__.py',
                   'AMS Subscriptions Products cleanup completed', NOW())
        """, (cr.dbname,))
        
    except Exception as e:
        cr.execute("""
            INSERT INTO ir_logging (name, level, dbname, line, func, path, message, create_date)
            VALUES ('ams.subscriptions.products', 'ERROR', %s, 0, '_uninstall_cleanup_subscriptions',
                   'ams_subscriptions_products/__init__.py', 
                   'Failed to cleanup AMS Subscriptions Products: %s', NOW())
        """, (cr.dbname, str(e)))