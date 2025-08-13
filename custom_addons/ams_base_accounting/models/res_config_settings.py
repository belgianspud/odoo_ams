# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # AMS Default Accounts
    ams_default_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default AMS Revenue Account',
        config_parameter='ams_base_accounting.default_revenue_account_id',
        domain=[('account_type', '=', 'income')],
        help='Default revenue account for AMS products'
    )
    
    ams_default_receivable_account_id = fields.Many2one(
        'account.account',
        string='Default AMS Receivable Account',
        config_parameter='ams_base_accounting.default_receivable_account_id',
        domain=[('account_type', '=', 'asset_receivable')],
        help='Default receivable account for AMS members'
    )
    
    # AMS Configuration Options
    ams_auto_configure_products = fields.Boolean(
        string='Auto-Configure Product Accounts',
        config_parameter='ams_base_accounting.auto_configure_products',
        default=True,
        help='Automatically configure accounts for new AMS products'
    )
    
    ams_member_numbering_prefix = fields.Char(
        string='Member ID Prefix',
        config_parameter='ams_base_accounting.member_numbering_prefix',
        default='MEM',
        help='Prefix for automatic member ID generation'
    )