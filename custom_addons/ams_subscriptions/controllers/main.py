from odoo import http
from odoo.http import request

class SubscriptionController(http.Controller):
    
    @http.route('/shop/subscriptions', type='http', auth="public", website=True)
    def subscription_shop(self, **kwargs):
        """Display subscription products in shop"""
        subscription_products = request.env['product.template'].sudo().search([
            ('is_subscription_product', '=', True),
            ('website_published', '=', True)
        ])
        
        values = {
            'subscription_products': subscription_products,
            'subscription_types': request.env['ams.subscription.type'].sudo().search([
                ('website_published', '=', True)
            ])
        }
        
        return request.render('ams_subscriptions.subscription_shop', values)
    
    @http.route('/my/subscriptions', type='http', auth="user", website=True)
    def my_subscriptions(self, **kwargs):
        """Customer portal for subscriptions"""
        partner = request.env.user.partner_id
        subscriptions = request.env['ams.subscription'].sudo().search([
            ('partner_id', '=', partner.id)
        ])
        
        values = {
            'subscriptions': subscriptions,
            'page_name': 'subscription',
        }
        
        return request.render('ams_subscriptions.my_subscriptions', values)