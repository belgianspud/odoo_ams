# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Membership fields
    is_member = fields.Boolean(string='Is Member', compute='_compute_membership_info', store=True)
    membership_ids = fields.One2many('membership.membership', 'partner_id', string='Memberships')
    current_membership_id = fields.Many2one('membership.membership', string='Current Membership',
                                            compute='_compute_membership_info', store=True)
    membership_state = fields.Selection(related='current_membership_id.state', string='Membership Status')
    membership_type = fields.Char(related='current_membership_id.membership_type_id.name', 
                                  string='Membership Type')
    membership_start_date = fields.Date(related='current_membership_id.start_date', 
                                        string='Membership Start')
    membership_end_date = fields.Date(related='current_membership_id.end_date', 
                                      string='Membership End')
    
    @api.depends('membership_ids', 'membership_ids.state', 'membership_ids.start_date')
    def _compute_membership_info(self):
        for partner in self:
            active_memberships = partner.membership_ids.filtered(
                lambda m: m.state == 'active'
            ).sorted('start_date', reverse=True)
            
            if active_memberships:
                partner.is_member = True
                partner.current_membership_id = active_memberships[0]
            else:
                partner.is_member = False
                partner.current_membership_id = False