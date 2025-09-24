from . import models
from . import wizards

def _post_init_hook(cr, registry):
    """Post-installation hook to set up integration with ams_foundation"""
    from odoo import api, SUPERUSER_ID
    
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Ensure all existing members are properly flagged
        partners = env['res.partner'].search([('is_member', '=', True)])
        for partner in partners:
            if not partner.member_status:
                partner.member_status = 'active'
        
        # Set up default member types for existing memberships
        memberships = env['ams.membership'].search([('member_type_id', '=', False)])
        default_member_type = env['ams.member.type'].search([('sequence', '=', 1)], limit=1)
        if default_member_type and memberships:
            memberships.write({'partner_id.member_type_id': default_member_type.id})
