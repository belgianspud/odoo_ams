# -*- coding: utf-8 -*-

from . import models
from . import wizard

def post_init_hook(cr, registry):
    """
    Post-installation hook to set up initial AMS accounting configuration
    """
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Ensure AMS account categories are configured
        _logger.info('Setting up AMS account categories...')
        accounts = env['account.account'].search([])
        if accounts:
            accounts.ensure_ams_accounts_configured()
            _logger.info('AMS account categories configured successfully')
        
        # Set up default AMS products if they don't exist
        _logger.info('Configuring AMS subscription products...')
        products = env['product.template'].search([
            ('is_subscription_product', '=', True),
            ('use_ams_accounting', '=', True)
        ])
        
        for product in products:
            if not product.ams_accounts_configured:
                try:
                    product._set_default_ams_accounts()
                    _logger.info(f'Configured accounts for product: {product.name}')
                except Exception as e:
                    _logger.warning(f'Could not configure accounts for product {product.name}: {str(e)}')
        
        _logger.info('AMS Base Accounting module installed successfully')
        
    except Exception as e:
        _logger.error(f'Error during AMS Base Accounting post-installation: {str(e)}')

def uninstall_hook(cr, registry):
    """
    Uninstallation hook to clean up AMS-specific configurations
    """
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Note: We don't remove account configurations or data during uninstall
        # to preserve financial integrity. Only remove AMS-specific flags.
        
        _logger.info('AMS Base Accounting module uninstalled successfully')
        _logger.warning('Financial data and account configurations have been preserved for data integrity')
        
    except Exception as e:
        _logger.error(f'Error during AMS Base Accounting uninstallation: {str(e)}')