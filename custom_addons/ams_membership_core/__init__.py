# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """
    Post-install hook for Odoo 18 - CORRECT SIGNATURE
    Args:
        env: Odoo environment object (replaces the old cr, registry pattern)
    """
    
    _logger.info("Starting AMS Membership Core post-init setup (Odoo 18)...")
    
    try:
        # Create default product categories if they don't exist
        categories_to_create = [
            ('Membership Products', None),  # Will use default parent
            ('Subscription Products', None),
            ('Chapter Memberships', 'Membership Products'),
            ('Publication Subscriptions', 'Subscription Products'),
        ]
        
        for cat_name, parent_name in categories_to_create:
            try:
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
            except Exception as e:
                _logger.warning(f"Could not create category {cat_name}: {e}")
        
        # Set up default sequences if they don't exist
        sequences_to_create = [
            ('ams.membership', 'AMS Membership Sequence', 'MEM'),
            ('ams.subscription', 'AMS Subscription Sequence', 'SUB'),
            ('ams.renewal', 'AMS Renewal Sequence', 'REN'),
            ('ams.benefit', 'AMS Benefit Sequence', 'BEN'),
        ]
        
        for seq_code, seq_name, seq_prefix in sequences_to_create:
            try:
                existing_seq = env['ir.sequence'].search([('code', '=', seq_code)], limit=1)
                if not existing_seq:
                    env['ir.sequence'].create({
                        'name': seq_name,
                        'code': seq_code,
                        'prefix': f'{seq_prefix}%(year)s',
                        'padding': 6,
                        'number_next': 1,
                        'number_increment': 1,
                    })
                    _logger.info(f"Created sequence: {seq_name}")
            except Exception as e:
                _logger.warning(f"Could not create sequence {seq_name}: {e}")
        
        # Process existing members to ensure computed fields are correct
        try:
            # Get members in smaller batches for Odoo 18 performance
            member_count = env['res.partner'].search_count([('is_member', '=', True)])
            if member_count > 0:
                _logger.info(f"Processing {member_count} existing members...")
                
                batch_size = 50  # Smaller batches for Odoo 18
                offset = 0
                processed = 0
                
                while offset < member_count:
                    batch = env['res.partner'].search([
                        ('is_member', '=', True)
                    ], limit=batch_size, offset=offset)
                    
                    if not batch:
                        break
                    
                    for member in batch:
                        try:
                            # Force recomputation by accessing computed fields
                            # This triggers the @api.depends decorators
                            _ = member.current_membership_id
                            _ = member.membership_count
                            _ = member.active_chapter_count
                            _ = member.subscription_count
                            _ = member.active_benefit_ids
                            processed += 1
                        except Exception as e:
                            _logger.warning(f"Could not process member {member.name}: {e}")
                    
                    offset += batch_size
                    
                    # Commit periodically for large datasets
                    if processed % 100 == 0:
                        env.cr.commit()
                        _logger.info(f"Processed {processed}/{member_count} members...")
                
                _logger.info(f"Completed processing {processed} existing members")
                
        except Exception as e:
            _logger.warning(f"Could not process existing members: {e}")
        
        # Sync existing paid invoices to create memberships/subscriptions
        try:
            # Look for paid invoices with subscription products
            domain = [
                ('move_id.state', '=', 'posted'),
                ('move_id.payment_state', 'in', ['paid', 'in_payment']),
                ('product_id.is_subscription_product', '=', True),
            ]
            
            invoice_lines = env['account.move.line'].search(domain, limit=50)
            
            created_memberships = 0
            created_subscriptions = 0
            
            for line in invoice_lines:
                try:
                    product = line.product_id.product_tmpl_id
                    
                    if hasattr(product, 'subscription_product_type'):
                        if product.subscription_product_type in ['membership', 'chapter']:
                            # Check if membership already exists
                            existing = env['ams.membership'].search([
                                ('invoice_line_id', '=', line.id)
                            ], limit=1)
                            
                            if not existing:
                                membership = env['ams.membership'].create_from_invoice_payment(line)
                                if membership:
                                    created_memberships += 1
                                    
                        elif product.subscription_product_type in ['publication', 'subscription']:
                            # Check if subscription already exists
                            existing = env['ams.subscription'].search([
                                ('invoice_line_id', '=', line.id)
                            ], limit=1)
                            
                            if not existing:
                                subscription = env['ams.subscription'].create_from_invoice_payment(line)
                                if subscription:
                                    created_subscriptions += 1
                                    
                except Exception as e:
                    _logger.warning(f"Could not process invoice line {line.id}: {e}")
            
            if created_memberships > 0:
                _logger.info(f"Created {created_memberships} memberships from existing invoices")
            if created_subscriptions > 0:
                _logger.info(f"Created {created_subscriptions} subscriptions from existing invoices")
                
        except Exception as e:
            _logger.warning(f"Could not sync existing invoices: {e}")
        
        # Odoo 18 specific: Check for portal integration
        try:
            portal_group = env.ref('base.group_portal', raise_if_not_found=False)
            if portal_group:
                _logger.info("Portal group found and ready for integration")
                
                # Check if portal templates are properly configured
                portal_menu = env.ref('portal.portal_my_home', raise_if_not_found=False)
                if portal_menu:
                    _logger.info("Portal home template found - member portal ready")
            else:
                _logger.info("Portal module not installed - portal features will be unavailable")
                
        except Exception as e:
            _logger.warning(f"Portal integration check failed: {e}")
        
        # Final commit for all changes
        env.cr.commit()
        _logger.info("AMS Membership Core post-init setup completed successfully for Odoo 18!")
        
    except Exception as e:
        _logger.error(f"Critical error in post-init setup: {e}", exc_info=True)
        # Roll back on critical errors
        env.cr.rollback()
        raise


def uninstall_hook(env):
    """
    Pre-uninstall hook for Odoo 18 - CORRECT SIGNATURE
    Args:
        env: Odoo environment object
    """
    
    _logger.info("Starting AMS Membership Core uninstall cleanup (Odoo 18)...")
    
    try:
        # Archive rather than delete to maintain data integrity
        models_to_archive = [
            ('product.template', [('is_subscription_product', '=', True)]),
            ('ams.membership', []),
            ('ams.subscription', []),
            ('ams.renewal', []),
        ]
        
        for model_name, domain in models_to_archive:
            try:
                records = env[model_name].search(domain)
                if records:
                    # Use write instead of unlink to preserve data
                    records.write({'active': False})
                    _logger.info(f"Archived {len(records)} records from {model_name}")
            except Exception as e:
                _logger.warning(f"Could not archive {model_name} records: {e}")
        
        # Reset partner fields to defaults (don't delete member status)
        try:
            members = env['res.partner'].search([('is_member', '=', True)])
            for member in members:
                # Reset computed field caches but keep is_member status
                member.invalidate_cache([
                    'current_membership_id',
                    'membership_count', 
                    'active_chapter_count',
                    'subscription_count',
                    'active_benefit_ids'
                ])
            _logger.info(f"Reset computed fields for {len(members)} members")
        except Exception as e:
            _logger.warning(f"Could not reset member fields: {e}")
        
        _logger.info("AMS Membership Core uninstall cleanup completed")
        
    except Exception as e:
        _logger.error(f"Error in uninstall cleanup: {e}", exc_info=True)