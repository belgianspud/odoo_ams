# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards

import logging
from odoo import api, SUPERUSER_ID
_logger = logging.getLogger(__name__)

def post_init_hook(cr, registry):
    """Post-install hook to set up initial data and configurations"""
    
    _logger = logging.getLogger(__name__)
    _logger.info("Starting AMS Membership Core post-init setup...")
    
    def _setup_initial_data():
        """Set up initial configuration data"""
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        try:
            # Create default product categories if they don't exist
            categories_to_create = [
                ('Membership Products', None),  # Will use default parent
                ('Subscription Products', None),
                ('Chapter Memberships', 'Membership Products'),
                ('Publication Subscriptions', 'Subscription Products'),
            ]
            
            for cat_name, parent_name in categories_to_create:
                existing_cat = env['product.category'].search([('name', '=', cat_name)], limit=1)
                if not existing_cat:
                    parent_cat = None
                    if parent_name:
                        parent_cat = env['product.category'].search([('name', '=', parent_name)], limit=1)
                    
                    # Create the category
                    cat_vals = {'name': cat_name}
                    if parent_cat:
                        cat_vals['parent_id'] = parent_cat.id
                    
                    env['product.category'].create(cat_vals)
                    _logger.info(f"Created product category: {cat_name}")
            
            # Set up default sequences if they don't exist
            try:
                # Check if membership sequence exists
                membership_seq = env['ir.sequence'].search([('code', '=', 'ams.membership')], limit=1)
                if not membership_seq:
                    env['ir.sequence'].create({
                        'name': 'AMS Membership Sequence',
                        'code': 'ams.membership',
                        'prefix': 'MEM',
                        'padding': 6,
                        'number_next': 1,
                    })
                    _logger.info("Created membership sequence")
                
                # Check if subscription sequence exists
                subscription_seq = env['ir.sequence'].search([('code', '=', 'ams.subscription')], limit=1)
                if not subscription_seq:
                    env['ir.sequence'].create({
                        'name': 'AMS Subscription Sequence',
                        'code': 'ams.subscription',
                        'prefix': 'SUB',
                        'padding': 6,
                        'number_next': 1,
                    })
                    _logger.info("Created subscription sequence")
                    
            except Exception as e:
                _logger.warning(f"Could not create sequences: {e}")
            
            # Ensure portal group integration (optional)
            try:
                portal_group = env.ref('base.group_portal', raise_if_not_found=False)
                if portal_group:
                    _logger.info("Portal group found and ready for integration")
            except Exception as e:
                _logger.warning(f"Portal group not available: {e}")
            
            _logger.info("AMS Membership Core post-init setup completed successfully")
            
        except Exception as e:
            _logger.error(f"Error in post-init setup: {e}", exc_info=True)
    
    _setup_initial_data()


def uninstall_hook(cr, registry):
    """Pre-uninstall hook to clean up data"""
    
    _logger = logging.getLogger(__name__)
    _logger.info("Starting AMS Membership Core uninstall cleanup...")
    
    def _cleanup_data():
        """Clean up module-specific data"""
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        try:
            # Archive rather than delete subscription products to maintain data integrity
            try:
                subscription_products = env['product.template'].search([
                    ('is_subscription_product', '=', True)
                ])
                if subscription_products:
                    subscription_products.write({'active': False})
                    _logger.info(f"Archived {len(subscription_products)} subscription products")
            except Exception as e:
                _logger.warning(f"Could not archive subscription products: {e}")
            
            _logger.info("AMS Membership Core uninstall cleanup completed")
            
        except Exception as e:
            _logger.error(f"Error in uninstall cleanup: {e}", exc_info=True)
    
    _cleanup_data()