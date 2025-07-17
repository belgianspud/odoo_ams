from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import AccessError, MissingError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class WebsiteSubscription(http.Controller):
    
    @http.route(['/subscriptions', '/subscriptions/page/<int:page>'], 
                type='http', auth="public", website=True)
    def subscription_plans(self, page=1, search='', category=None, **kwargs):
        """Display subscription plans on website"""
        domain = [('website_published', '=', True), ('active', '=', True)]
        
        if search:
            domain += [('name', 'ilike', search)]
        
        if category:
            domain += [('plan_type', '=', category)]
        
        # Get plans
        Plan = request.env['ams.subscription.plan'].sudo()
        plans = Plan.search(domain, order='sequence, name')
        
        # Get plan types for filter
        plan_types = Plan.search([('website_published', '=', True)]).mapped('plan_type')
        plan_types = list(set(plan_types))
        
        values = {
            'plans': plans,
            'plan_types': plan_types,
            'search': search,
            'category': category,
        }
        
        return request.render('ams_subscriptions.subscription_plans_page', values)
    
    @http.route(['/subscription/plan/<model("ams.subscription.plan"):plan>'], 
                type='http', auth="public", website=True)
    def subscription_plan_detail(self, plan, **kwargs):
        """Display subscription plan details"""
        if not plan.website_published or not plan.active:
            raise MissingError(_("This subscription plan is not available."))
        
        values = {
            'plan': plan,
            'user': request.env.user,
        }
        
        return request.render('ams_subscriptions.subscription_plan_detail', values)
    
    @http.route(['/subscription/subscribe/<model("ams.subscription.plan"):plan>'], 
                type='http', auth="user", website=True, methods=['POST'])
    def subscribe_to_plan(self, plan, **kwargs):
        """Subscribe user to a plan"""
        try:
            # Check if user already has active subscription for this plan
            existing = request.env['ams.subscription'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('plan_id', '=', plan.id),
                ('state', 'in', ['active', 'trial'])
            ])
            
            if existing:
                return request.redirect('/my/subscriptions?error=already_subscribed')
            
            # Check plan limits
            if plan.max_subscriptions > 0 and plan.subscription_count >= plan.max_subscriptions:
                return request.redirect('/my/subscriptions?error=plan_full')
            
            # Create subscription
            subscription_vals = {
                'partner_id': request.env.user.partner_id.id,
                'plan_id': plan.id,
                'price': plan.price,
                'start_date': fields.Date.today(),
                'auto_renew': plan.auto_renew,
            }
            
            # Handle trial period
            if plan.trial_period_days > 0:
                subscription_vals.update({
                    'is_trial': True,
                    'state': 'trial',
                })
            
            subscription = request.env['ams.subscription'].sudo().create(subscription_vals)
            
            # If not trial, create sale order for payment
            if not subscription.is_trial:
                sale_order = self._create_sale_order_for_subscription(subscription)
                subscription.sale_order_id = sale_order.id
                
                # Redirect to payment
                return request.redirect(f'/shop/payment?order_id={sale_order.id}')
            else:
                # Activate trial subscription
                subscription.action_activate()
                return request.redirect('/my/subscriptions?success=trial_activated')
                
        except Exception as e:
            _logger.error(f"Error subscribing to plan {plan.id}: {str(e)}")
            return request.redirect('/my/subscriptions?error=subscription_failed')
    
    def _create_sale_order_for_subscription(self, subscription):
        """Create sale order for subscription payment"""
        SaleOrder = request.env['sale.order'].sudo()
        
        order_vals = {
            'partner_id': subscription.partner_id.id,
            'origin': subscription.name,
            'order_line': [(0, 0, {
                'product_id': subscription.plan_id.product_id.id,
                'name': f"{subscription.plan_id.name} Subscription",
                'product_uom_qty': 1,
                'price_unit': subscription.price,
            })],
        }
        
        order = SaleOrder.create(order_vals)
        order.action_confirm()
        
        return order


class SubscriptionPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        """Add subscription count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'subscription_count' in counters:
            subscription_count = request.env['ams.subscription'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id)
            ]) if request.env.user != request.website.user_id else 0
            values['subscription_count'] = subscription_count
            
        return values
    
    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_subscriptions(self, page=1, date_begin=None, date_end=None, 
                           sortby=None, search=None, search_in='content', **kw):
        """Display user's subscriptions in portal"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        domain = [('partner_id', '=', partner.id)]
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'start_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'plan': {'label': _('Plan'), 'order': 'plan_id'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Search
        if search and search_in:
            if search_in == 'content':
                domain += ['|', ('name', 'ilike', search), ('plan_id.name', 'ilike', search)]
        
        # Date filter
        if date_begin and date_end:
            domain += [('start_date', '>=', date_begin), ('start_date', '<=', date_end)]
        
        # Count subscriptions
        subscription_count = request.env['ams.subscription'].search_count(domain)
        
        # Pager
        pager = request.website.pager(
            url="/my/subscriptions",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=subscription_count,
            page=page,
            step=self._items_per_page
        )
        
        # Get subscriptions
        subscriptions = request.env['ams.subscription'].search(
            domain, order=order, limit=self._items_per_page, offset=pager['offset']
        )
        
        values.update({
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'pager': pager,
            'default_url': '/my/subscriptions',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
        })
        
        return request.render("ams_subscriptions.portal_my_subscriptions", values)
    
    @http.route(['/my/subscription/<int:subscription_id>'], type='http', auth="user", website=True)
    def portal_subscription_detail(self, subscription_id, access_token=None, **kw):
        """Display subscription details in portal"""
        try:
            subscription_sudo = self._document_check_access('ams.subscription', 
                                                          subscription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = {
            'subscription': subscription_sudo,
            'page_name': 'subscription',
        }
        
        return request.render("ams_subscriptions.portal_subscription_detail", values)
    
    @http.route(['/my/subscription/<int:subscription_id>/renew'], 
                type='http', auth="user", website=True, methods=['POST'])
    def portal_subscription_renew(self, subscription_id, **kw):
        """Renew subscription from portal"""
        try:
            subscription = request.env['ams.subscription'].browse(subscription_id)
            
            # Check access
            if subscription.partner_id != request.env.user.partner_id:
                raise AccessError(_("Access denied"))
            
            if not subscription.can_renew:
                return request.redirect(f'/my/subscription/{subscription_id}?error=cannot_renew')
            
            # Create sale order for renewal
            sale_order = self._create_renewal_order(subscription)
            
            # Redirect to payment
            return request.redirect(f'/shop/payment?order_id={sale_order.id}')
            
        except Exception as e:
            _logger.error(f"Error renewing subscription {subscription_id}: {str(e)}")
            return request.redirect(f'/my/subscription/{subscription_id}?error=renewal_failed')
    
    def _create_renewal_order(self, subscription):
        """Create sale order for subscription renewal"""
        SaleOrder = request.env['sale.order'].sudo()
        
        order_vals = {
            'partner_id': subscription.partner_id.id,
            'origin': f"{subscription.name} - Renewal",
            'order_line': [(0, 0, {
                'product_id': subscription.plan_id.product_id.id,
                'name': f"{subscription.plan_id.name} Subscription Renewal",
                'product_uom_qty': 1,
                'price_unit': subscription.price,
            })],
        }
        
        order = SaleOrder.create(order_vals)
        order.action_confirm()
        
        return order
    
    @http.route(['/my/subscription/<int:subscription_id>/cancel'], 
                type='http', auth="user", website=True, methods=['POST'])
    def portal_subscription_cancel(self, subscription_id, **kw):
        """Cancel subscription from portal"""
        try:
            subscription = request.env['ams.subscription'].browse(subscription_id)
            
            # Check access
            if subscription.partner_id != request.env.user.partner_id:
                raise AccessError(_("Access denied"))
            
            subscription.action_cancel()
            
            return request.redirect(f'/my/subscription/{subscription_id}?success=cancelled')
            
        except Exception as e:
            _logger.error(f"Error cancelling subscription {subscription_id}: {str(e)}")
            return request.redirect(f'/my/subscription/{subscription_id}?error=cancel_failed')


class WebsiteSaleSubscription(WebsiteSale):
    """Extend website sale for subscription handling"""
    
    @http.route()
    def payment_confirmation(self, **post):
        """Handle subscription activation after payment"""
        result = super().payment_confirmation(**post)
        
        # Check if this was a subscription order
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            
            # Find related subscription
            subscription = request.env['ams.subscription'].sudo().search([
                ('sale_order_id', '=', order.id)
            ], limit=1)
            
            if subscription and order.state in ['sale', 'done']:
                # Activate subscription after successful payment
                if subscription.state == 'draft':
                    subscription.action_activate()
                elif subscription.state in ['expired', 'cancelled']:
                    subscription.action_renew()
        
        return result