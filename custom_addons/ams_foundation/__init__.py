# -*- coding: utf-8 -*-

from . import models
from . import wizards

def post_init_hook(env):
    """
    Post-installation hook to set up initial data and configurations.
    """
    # Set up default member numbering sequence if not exists
    sequence = env['ir.sequence'].search([('code', '=', 'ams.member.number')], limit=1)
    if not sequence:
        env['ir.sequence'].create({
            'name': 'Member Number Sequence',
            'code': 'ams.member.number',
            'prefix': 'M',
            'padding': 6,
            'number_increment': 1,
            'number_next_actual': 1,
        })
    
    # Initialize default AMS settings if not exists
    settings = env['ams.settings'].search([], limit=1)
    if not settings:
        env['ams.settings'].create({
            'name': 'Default AMS Settings',
            'member_number_prefix': 'M',
            'grace_period_days': 30,
            'suspend_period_days': 60,
            'terminate_period_days': 90,
            'auto_create_portal_users': True,
        })