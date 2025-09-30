# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class MembershipPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        
        if 'membership_count' in counters:
            partner = request.env.user.partner_id
            membership_count = request.env['membership.membership'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['membership_count'] = membership_count
            
        return values
    
    @http.route(['/my/memberships'], type='http', auth="user", website=True)
    def portal_my_memberships(self, **kw):
        partner = request.env.user.partner_id
        memberships = request.env['membership.membership'].search([
            ('partner_id', '=', partner.id)
        ], order='start_date desc')
        
        values = {
            'memberships': memberships,
            'page_name': 'membership',
        }
        
        return request.render("membership_community.portal_my_memberships", values)
    
    @http.route(['/my/membership/<int:membership_id>'], type='http', auth="user", website=True)
    def portal_my_membership_detail(self, membership_id, **kw):
        partner = request.env.user.partner_id
        membership = request.env['membership.membership'].browse(membership_id)
        
        if not membership.exists() or membership.partner_id != partner:
            return request.redirect('/my')
            
        values = {
            'membership': membership,
            'page_name': 'membership',
        }
        
        return request.render("membership_community.portal_my_membership_detail", values)