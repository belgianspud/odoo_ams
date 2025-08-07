# -*- coding: utf-8 -*-
from . import models
from . import wizard

def post_init_hook(cr, registry):
    """Post-installation hook to set up AMS accounting"""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Enable AMS accounting for existing subscription products
    ams_products = env['product.template'].search([
        ('is_subscription_product', '=', True),
        ('use_ams_accounting', '=', False)
    ])
    
    if ams_products:
        ams_products.write({'use_ams_accounting': True})
        
        # Auto-configure accounts for these products
        for product in ams_products:
            product._set_default_ams_accounts()