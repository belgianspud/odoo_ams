# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import controllers

import logging
from datetime import timedelta
from odoo import fields

_logger = logging.getLogger(__name__)


def _pre_init_hook(env):
    """Pre-installation hook for data migration and preparation"""
    _logger.info("AMS Membership Core: Running pre-init hook...")
    
    # In Odoo 18, pre_init_hook receives an Environment object
    cr = env.cr
    
    # Check if foundation module is installed
    cr.execute("""
        SELECT state FROM ir_module_module 
        WHERE name = 'ams_foundation' AND state = 'installed'
    """)
    
    if not cr.fetchone():
        raise Exception(
            "AMS Foundation module must be installed before AMS Membership Core. "
            "Please install ams_foundation first."
        )
    
    _logger.info("AMS Membership Core: Pre-init completed successfully")


def _post_init_hook(env):
    """Post-installation hook for final setup and integration"""
    _logger.info("AMS Membership Core: Running post-init hook...")
    
    # Handle the environment properly
    cr = env.cr
    
    try:
        # 1. Ensure AMS settings exist and are configured
        _setup_ams_settings(env)
        
        # 2. Create default product categories if not exist
        _setup_product_categories(env)
        
        # 3. Set up default benefits
        _setup_default_benefits(env)
        
        # 4. Setup portal group integration
        _setup_portal_group_integration(env)
        
        # 5. Sync any existing foundation members with membership core
        _sync_foundation_members(env)
        
        # 6. Configure portal access for existing members
        _configure_portal_access(env)
        
        _logger.info("AMS Membership Core: Post-init completed successfully")
        
    except Exception as e:
        _logger.error(f"AMS Membership Core: Post-init failed: {str(e)}")
        raise


def _setup_ams_settings(env):
    """Ensure AMS settings exist and are properly configured"""
    settings = env['ams.settings'].search([('active', '=', True)], limit=1)
    
    if not settings:
        _logger.info("Creating default AMS settings...")
        settings = env['ams.settings'].create({
            'name': 'Default AMS Settings',
            'active': True,
            'member_number_prefix': 'M',
            'member_number_padding': 6,
            'auto_status_transitions': True,
            'grace_period_days': 30,
            'suspend_period_days': 60,
            'terminate_period_days': 90,
            'auto_create_portal_users': True,
            'welcome_email_enabled': True,
            'renewal_reminder_enabled': True,
            'renewal_reminder_days': 30,
            'engagement_scoring_enabled': True,
        })
        _logger.info(f"Created AMS settings: {settings.name}")


def _setup_product_categories(env):
    """Create default product categories"""
    categories = [
        ('Membership Products', 'ams_membership_core.categ_membership_products'),
        ('Subscription Products', 'ams_membership_core.categ_subscription_products'),
        ('Publication Subscriptions', 'ams_membership_core.categ_publication_subscriptions'),
        ('Chapter Memberships', 'ams_membership_core.categ_chapter_memberships'),
    ]
    
    for cat_name, cat_ref in categories:
        try:
            category = env.ref(cat_ref, raise_if_not_found=False)
            if not category:
                parent_cat = env['product.category'].search([('name', '=', 'All')], limit=1)
                if not parent_cat:
                    parent_cat = env.ref('product.product_category_all')
                
                env['product.category'].create({
                    'name': cat_name,
                    'parent_id': parent_cat.id,
                })
                _logger.info(f"Created product category: {cat_name}")
        except Exception as e:
            _logger.warning(f"Could not create category {cat_name}: {str(e)}")


def _setup_default_benefits(env):
    """Ensure default benefits exist"""
    default_benefits = [
        {
            'name': 'Member Portal Access',
            'code': 'PORTAL',
            'benefit_type': 'access',
            'applies_to': 'both',
            'auto_apply': True,
        },
        {
            'name': 'Member Directory Access',
            'code': 'DIRECTORY',
            'benefit_type': 'networking',
            'applies_to': 'membership',
            'auto_apply': True,
        },
        {
            'name': 'Member Event Pricing',
            'code': 'EVENT_DISC',
            'benefit_type': 'discount',
            'applies_to': 'both',
            'discount_type': 'percentage',
            'discount_percentage': 15.0,
            'auto_apply': True,
        },
    ]
    
    for benefit_data in default_benefits:
        existing = env['ams.benefit'].search([('code', '=', benefit_data['code'])], limit=1)
        if not existing:
            env['ams.benefit'].create(benefit_data)
            _logger.info(f"Created default benefit: {benefit_data['name']}")


def _sync_foundation_members(env):
    """Sync existing foundation members with membership core"""
    # Find members from foundation who don't have membership records
    members_without_memberships = env['res.partner'].search([
        ('is_member', '=', True),
        ('member_status', '=', 'active'),
        ('membership_ids', '=', False),
    ])
    
    if not members_without_memberships:
        return
    
    _logger.info(f"Syncing {len(members_without_memberships)} foundation members...")
    
    # Get default membership product
    default_product = env['product.product'].search([
        ('is_subscription_product', '=', True),
        ('subscription_product_type', '=', 'membership'),
    ], limit=1)
    
    if not default_product:
        _logger.warning("No default membership product found for sync")
        return
    
    for member in members_without_memberships:
        try:
            # Create membership record for existing foundation member
            membership_vals = {
                'partner_id': member.id,
                'product_id': default_product.id,
                'start_date': member.membership_start_date or fields.Date.today(),
                'end_date': member.membership_end_date or (fields.Date.today() + timedelta(days=365)),
                'membership_fee': default_product.list_price,
                'state': 'active',
                'auto_renew': True,
                'payment_status': 'paid',  # Assume existing members are paid
            }
            
            membership = env['ams.membership'].create(membership_vals)
            _logger.info(f"Created membership for existing member: {member.name}")
            
        except Exception as e:
            _logger.error(f"Failed to create membership for {member.name}: {str(e)}")


def _configure_portal_access(env):
    """Configure portal access for existing members"""
    settings = env['ams.settings'].search([('active', '=', True)], limit=1)
    
    if not settings or not settings.auto_create_portal_users:
        return
    
    # Find active members without portal users
    members_without_portal = env['res.partner'].search([
        ('is_member', '=', True),
        ('member_status', 'in', ['active', 'grace']),
        ('portal_user_id', '=', False),
        ('email', '!=', False),
    ])
    
    if not members_without_portal:
        return
    
    _logger.info(f"Creating portal access for {len(members_without_portal)} members...")
    
    for member in members_without_portal:
        try:
            member.action_create_portal_user()
            _logger.info(f"Created portal access for: {member.name}")
        except Exception as e:
            _logger.warning(f"Failed to create portal user for {member.name}: {str(e)}")