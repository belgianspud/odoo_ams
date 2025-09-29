# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SubscriptionWebsiteController(http.Controller):
    """Public website controller for subscription features"""

    @http.route(['/subscription/usage/<int:subscription_id>'], 
                type='json', auth='user', website=True)
    def subscription_add_usage(self, subscription_id, usage_type, quantity, description=None, **kw):
        """API endpoint to add usage to subscription"""
        try:
            subscription = request.env['subscription.subscription'].browse(subscription_id)
            
            # Check access
            if subscription.partner_id != request.env.user.partner_id:
                return {'error': 'Access denied'}
            
            usage = subscription.add_usage(usage_type, quantity, description)
            
            return {
                'success': True,
                'usage_id': usage.id,
                'current_usage': subscription.current_usage,
                'usage_overage': subscription.usage_overage,
            }
        except Exception as e:
            _logger.error(f"Error adding usage: {e}")
            return {'error': str(e)}

    @http.route(['/subscription/webhook/usage'], 
                type='json', auth='none', csrf=False, website=True)
    def subscription_usage_webhook(self, **kw):
        """Webhook endpoint for external usage tracking"""
        # This endpoint can be used by external systems to report usage
        # Implement proper authentication and validation as needed
        
        try:
            subscription_ref = kw.get('subscription_ref')
            usage_type = kw.get('usage_type')
            quantity = float(kw.get('quantity', 0))
            description = kw.get('description')
            
            if not all([subscription_ref, usage_type, quantity]):
                return {'error': 'Missing required parameters'}
            
            subscription = request.env['subscription.subscription'].sudo().search([
                ('name', '=', subscription_ref)
            ], limit=1)
            
            if not subscription:
                return {'error': 'Subscription not found'}
            
            usage = subscription.add_usage(usage_type, quantity, description)
            
            return {
                'success': True,
                'usage_id': usage.id,
            }
            
        except Exception as e:
            _logger.error(f"Webhook error: {e}")
            return {'error': 'Internal server error'}