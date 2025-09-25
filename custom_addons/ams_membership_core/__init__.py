# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards


def post_init_hook(cr, registry):
    """Post-install hook to set up initial data and configurations"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    
    def _setup_initial_data():
        """Set up initial configuration data"""
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        try:
            # Create default product categories if they don't exist
            categories_to_create = [
                ('Membership Products', 'product.product_category_all'),
                ('Subscription Products', 'product.product_category_all'),
                ('Chapter Memberships', 'Subscription Products'),
                ('Publication Subscriptions', 'Subscription Products'),
            ]
            
            for cat_name, parent_ref in categories_to_create:
                existing_cat = env['product.category'].search([('name', '=', cat_name)], limit=1)
                if not existing_cat:
                    parent_cat = env.ref(parent_ref, raise_if_not_found=False)
                    if not parent_cat and parent_ref != 'product.product_category_all':
                        # Create parent category first
                        parent_cat = env['product.category'].search([('name', '=', parent_ref)], limit=1)
                    
                    if parent_cat or parent_ref == 'product.product_category_all':
                        parent_id = parent_cat.id if parent_cat else env.ref('product.product_category_all').id
                        env['product.category'].create({
                            'name': cat_name,
                            'parent_id': parent_id,
                        })
                        _logger.info(f"Created product category: {cat_name}")
            
            # Ensure portal group integration
            try:
                portal_group = env.ref('base.group_portal', raise_if_not_found=False)
                membership_portal_group = env.ref('ams_membership_core.group_membership_portal', raise_if_not_found=False)
                
                if portal_group and membership_portal_group:
                    # Add membership portal as implied group of portal
                    if membership_portal_group.id not in portal_group.implied_ids.ids:
                        portal_group.implied_ids = [(4, membership_portal_group.id)]
                        _logger.info("Added membership portal group to portal group")
            except Exception as e:
                _logger.warning(f"Could not set up portal group integration: {e}")
            
            # Set up default benefit types if benefits exist
            try:
                benefits = env['ams.benefit'].search([])
                if benefits:
                    _logger.info(f"Found {len(benefits)} existing benefits")
            except Exception as e:
                _logger.warning(f"Benefits not available during post-init: {e}")
            
            _logger.info("AMS Membership Core post-init setup completed successfully")
            
        except Exception as e:
            _logger.error(f"Error in post-init setup: {e}")
    
    _setup_initial_data()


def uninstall_hook(cr, registry):
    """Pre-uninstall hook to clean up data"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    
    def _cleanup_data():
        """Clean up module-specific data"""
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        try:
            # Clean up portal group relationships
            try:
                portal_group = env.ref('base.group_portal', raise_if_not_found=False)
                membership_portal_group = env.ref('ams_membership_core.group_membership_portal', raise_if_not_found=False)
                
                if portal_group and membership_portal_group:
                    portal_group.implied_ids = [(3, membership_portal_group.id)]
                    _logger.info("Removed membership portal group from portal group")
            except Exception as e:
                _logger.warning(f"Could not clean up portal group integration: {e}")
            
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
            _logger.error(f"Error in uninstall cleanup: {e}")
    
    _cleanup_data()