# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


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
    
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        membership_count = request.env['membership.membership'].search_count([
            ('partner_id', '=', partner.id)
        ])
        
        values['membership_count'] = membership_count
        return values
    
    @http.route(['/my/memberships', '/my/memberships/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_memberships(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Membership = request.env['membership.membership']
        
        domain = [('partner_id', '=', partner.id)]
        
        # Searchbar filters
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'expired': {'label': _('Expired'), 'domain': [('state', '=', 'expired')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
            'suspended': {'label': _('Suspended'), 'domain': [('state', '=', 'suspended')]},
        }
        
        # Searchbar sorting
        searchbar_sortings = {
            'date': {'label': _('Newest First'), 'order': 'start_date desc'},
            'date_asc': {'label': _('Oldest First'), 'order': 'start_date asc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        # Default filter and sort
        if not filterby:
            filterby = 'all'
        if not sortby:
            sortby = 'date'
        
        # Apply domain filters
        domain += searchbar_filters[filterby]['domain']
        order = searchbar_sortings[sortby]['order']
        
        # Count for pager
        membership_count = Membership.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/memberships",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=membership_count,
            page=page,
            step=10
        )
        
        # Get memberships
        memberships = Membership.search(domain, order=order, limit=10, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'memberships': memberships,
            'page_name': 'membership',
            'default_url': '/my/memberships',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        
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