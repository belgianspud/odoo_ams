# -*- coding: utf-8 -*-
from . import models
from . import wizard
from odoo import fields

def post_init_hook(env):
    """Post-installation hook to set up AMS accounting"""
    
    try:
        # Step 1: Fix any existing duplicate account issues
        AccountAccount = env['account.account']
        fixed_accounts = AccountAccount.fix_duplicate_account_issue()
        
        if fixed_accounts:
            env['ir.logging'].create({
                'name': 'ams_base_accounting.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'Fixed {len(fixed_accounts)} existing accounts with AMS categories',
                'path': 'ams_base_accounting',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 2: Ensure AMS accounts are configured
        updated_count = AccountAccount.ensure_ams_accounts_configured()
        
        if updated_count > 0:
            env['ir.logging'].create({
                'name': 'ams_base_accounting.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'Updated {updated_count} accounts with AMS categories',
                'path': 'ams_base_accounting',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 3: Create any missing AMS accounts
        result = AccountAccount.create_ams_account_structure()
        
        if result['created']:
            env['ir.logging'].create({
                'name': 'ams_base_accounting.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'Created {len(result["created"])} new AMS accounts',
                'path': 'ams_base_accounting',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 4: Enable AMS accounting for existing subscription products
        ams_products = env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('use_ams_accounting', '=', False)
        ])
        
        if ams_products:
            ams_products.write({'use_ams_accounting': True})
            
            # Auto-configure accounts for these products
            configured_count = 0
            for product in ams_products:
                try:
                    product._set_default_ams_accounts()
                    configured_count += 1
                except Exception as e:
                    # Log error but continue with other products
                    env['ir.logging'].create({
                        'name': 'ams_base_accounting.post_init',
                        'type': 'server',
                        'level': 'WARNING',
                        'message': f'Error configuring product {product.name}: {str(e)}',
                        'path': 'ams_base_accounting',
                        'func': 'post_init_hook',
                        'line': '0',
                    })
            
            if configured_count > 0:
                env['ir.logging'].create({
                    'name': 'ams_base_accounting.post_init',
                    'type': 'server',
                    'level': 'INFO',
                    'message': f'Enabled AMS accounting for {len(ams_products)} products, configured {configured_count} products',
                    'path': 'ams_base_accounting',
                    'func': 'post_init_hook',
                    'line': '0',
                })
        
        # Step 5: Validate the final setup
        validation = AccountAccount.validate_ams_account_setup()
        
        if validation['valid']:
            env['ir.logging'].create({
                'name': 'ams_base_accounting.post_init',
                'type': 'server',
                'level': 'INFO',
                'message': f'AMS accounting setup completed successfully. Validated {validation["accounts_checked"]} accounts.',
                'path': 'ams_base_accounting',
                'func': 'post_init_hook',
                'line': '0',
            })
        else:
            env['ir.logging'].create({
                'name': 'ams_base_accounting.post_init',
                'type': 'server',
                'level': 'WARNING',
                'message': f'AMS accounting setup completed with issues: {", ".join(validation["issues"])}',
                'path': 'ams_base_accounting',
                'func': 'post_init_hook',
                'line': '0',
            })
        
        # Step 6: Mark setup as completed
        env['ir.config_parameter'].sudo().set_param('ams.setup.accounts_creation_needed', 'false')
        env['ir.config_parameter'].sudo().set_param('ams.setup.completed_date', fields.Datetime.now().isoformat())
        
    except Exception as e:
        # Log any critical errors during setup
        env['ir.logging'].create({
            'name': 'ams_base_accounting.post_init',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Critical error during AMS accounting setup: {str(e)}',
            'path': 'ams_base_accounting',
            'func': 'post_init_hook',
            'line': '0',
        })
        
        # Don't raise the exception to prevent installation failure
        # The setup wizard can be used to fix any issues


def uninstall_hook(env):
    """Cleanup when module is uninstalled"""
    
    try:
        # Disable AMS accounting on products
        ams_products = env['product.template'].search([
            ('use_ams_accounting', '=', True)
        ])
        
        if ams_products:
            ams_products.write({'use_ams_accounting': False})
        
        # Remove AMS categories from accounts (but keep the accounts)
        ams_accounts = env['account.account'].search([
            ('ams_account_category', '!=', False)
        ])
        
        if ams_accounts:
            ams_accounts.write({'ams_account_category': False})
        
        # Clean up configuration parameters
        config_params = env['ir.config_parameter'].search([
            ('key', 'like', 'ams.%')
        ])
        
        if config_params:
            config_params.unlink()
        
        env['ir.logging'].create({
            'name': 'ams_base_accounting.uninstall',
            'type': 'server',
            'level': 'INFO',
            'message': f'AMS Base Accounting uninstalled. Cleaned up {len(ams_products)} products and {len(ams_accounts)} accounts.',
            'path': 'ams_base_accounting',
            'func': 'uninstall_hook',
            'line': '0',
        })
        
    except Exception as e:
        # Log error but don't fail uninstall
        env['ir.logging'].create({
            'name': 'ams_base_accounting.uninstall',
            'type': 'server',
            'level': 'ERROR',
            'message': f'Error during uninstall: {str(e)}',
            'path': 'ams_base_accounting',
            'func': 'uninstall_hook',
            'line': '0',
        })