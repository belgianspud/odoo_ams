# -*- coding: utf-8 -*-
{
    'name': 'AMS Subscriptions',
    'version': '2.0.0',
    'summary': 'Enhanced subscription management with billing periods integration',
    'description': """
AMS Subscriptions - Enhanced Version 2.0
========================================
Advanced subscription lifecycle management for associations, now with:

- Billing Periods Integration - Uses ams_billing_periods for flexible billing cycles
- Product Behavior Integration - Inherits from ams_products_base for consistent UX
- Individual and Enterprise Memberships with seat management
- Chapter and Publication subscription management
- Complete lifecycle automation (Active → Grace → Suspended → Terminated)
- Member portal with self-service capabilities
- Payment failure tracking and NSF management
- Modification and cancellation workflows

Key Enhancements in V2.0:
- Removed duplication with ams_products_base
- Integrated with ams_billing_periods for flexible billing
- Enhanced member pricing through base module
- Cleaner architecture with proper inheritance
- Better integration with product behavior system

Technical Architecture:
- Layer 2 module that extends ams_products_base (Layer 1)
- Uses ams_billing_periods for all date calculations
- Focuses on subscription lifecycle, not product configuration
- Clean separation of concerns for maintainability
    """,
    'author': 'Your Organization',
    'website': 'https://yourwebsite.com',
    'category': 'Association Management',
    'license': 'LGPL-3',
    
    # Enhanced dependencies for V2.0 architecture
    'depends': [
        # Core Odoo modules
        'base',
        'contacts',
        'sale_management',
        'account',
        'website_sale',
        'point_of_sale',
        'mail',
        'portal',
        'event',            # For event template integration
        
        # AMS Foundation modules (Layer 1)
        'ams_products_base',    # NEW! Product behavior and basic subscription config
        'ams_billing_periods',  # NEW! Flexible billing period management
        'ams_member_data',      # Member status and pricing integration
    ],
    
    'data': [
        # Security - Load in proper order
        'security/ams_subscription_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/ams_subscription_cron.xml',
        
        # Core Models Views - Enhanced to inherit from base modules
        'views/product_template_subscription_views.xml',  # Enhanced inheritance
        'views/ams_subscription_views.xml',
        'views/ams_subscription_seat_views.xml',
        'views/ams_subscription_tier_views.xml',
        'views/ams_subscription_modification_views.xml',   # New wizard views
        'views/res_partner_views.xml',
        
        # Portal integration
        'views/portal_templates.xml',                      # Enhanced portal
        'views/portal_subscription_templates.xml',
        
        # Enhanced management views
        'views/ams_subscription_dashboard_views.xml',     # New dashboard
        'views/ams_subscription_reports_views.xml',       # Enhanced reporting
        
        # Actions and menus
        'views/ams_subscription_actions.xml',
        'views/ams_subscription_menu.xml',
    ],
    
    # Assets for enhanced UX
    'assets': {
        'web.assets_backend': [
            'ams_subscriptions/static/src/css/subscription_dashboard.css',
            'ams_subscriptions/static/src/js/subscription_widgets.js',
        ],
        'web.assets_frontend': [
            'ams_subscriptions/static/src/css/portal_subscriptions.css',
        ],
    },
    
    # Installation and compatibility
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,  # After base modules but before specialized ones
    
    # Version and upgrade handling
    'pre_init_hook': None,
    'post_init_hook': 'post_init_hook',    # For data migration from V1.0
    'post_load': None,
    'uninstall_hook': None,
    
    # Development info
    'development_status': 'Production/Stable',
    'maintainers': ['your-organization'],
    'support': 'https://your-support-url.com',
    
    # Module relationships for clean architecture
    'conflicts': [],                        # No conflicts - designed for coexistence
    'excludes': [],
    
    # External dependencies
    'external_dependencies': {
        'python': ['dateutil'],            # For advanced date calculations
        'bin': [],
    },
    
    # Localization and UI
    'translations': [
        # Future: Add translation support
    ],
    
    # Demo and test data
    'demo': [],
    'test': [],
    
    # Commercial info
    'price': 0,
    'currency': 'USD',
    'live_test_url': None,
    
    # Technical metadata
    'bootstrap': False,
    'cloc_exclude': ['./**/*'],
}

def post_init_hook(cr, registry):
    """
    Post-installation hook to migrate existing subscription data
    and ensure compatibility with ams_products_base
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Migrate existing subscription products to use ams_product_behavior
    _migrate_subscription_products(env)
    
    # Update existing subscriptions to use billing periods
    _migrate_subscription_billing_periods(env)
    
    # Log successful migration
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("AMS Subscriptions V2.0 migration completed successfully")


def _migrate_subscription_products(env):
    """Migrate existing subscription products to use ams_products_base"""
    
    # Find products with old ams_product_type field
    products = env['product.template'].search([
        ('ams_product_type', '!=', 'none'),
    ])
    
    for product in products:
        # Map old types to new behavior system
        type_mapping = {
            'individual': 'subscription',
            'enterprise': 'subscription', 
            'chapter': 'subscription',
            'publication': 'subscription',
        }
        
        new_behavior = type_mapping.get(product.ams_product_type, 'subscription')
        
        # Update to use ams_products_base system
        product.write({
            'is_ams_product': True,
            'ams_product_behavior': new_behavior,
            'is_subscription_product': True,
        })


def _migrate_subscription_billing_periods(env):
    """Update subscriptions to use ams_billing_periods"""
    
    # Get or create default billing periods from ams_billing_periods
    annual_period = env['ams.billing.period'].search([
        ('name', '=', 'Annual')
    ], limit=1)
    
    if annual_period:
        # Update products without billing periods
        subscription_products = env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('default_billing_period_id', '=', False),
        ])
        
        subscription_products.write({
            'default_billing_period_id': annual_period.id
        })