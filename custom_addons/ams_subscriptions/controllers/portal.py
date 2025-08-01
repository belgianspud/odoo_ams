# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class AMSPortal(CustomerPortal):

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], type='http', auth='user', website=True)
    def my_subscriptions(self, page=1, **kw):
        # Fetch subscriptions for logged-in user
        subscriptions = request.env['ams.subscription'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', '!=', 'terminated')
        ], order='create_date desc')

        values = {
            'page_name': 'subscription',
            'subscriptions': subscriptions,
        }
        return request.render('ams_subscriptions.portal_my_subscriptions', values)
