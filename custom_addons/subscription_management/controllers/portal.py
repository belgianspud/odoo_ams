# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from collections import OrderedDict
import logging

_logger = logging.getLogger(__name__)


class SubscriptionPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add subscription count to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'subscription_count' in counters:
            subscription_count = request.env['subscription.subscription'].search_count([
                ('partner_id', 'child_of', request.env.user.partner_id.id)
            ]) if request.env.user.partner_id else 0
            values['subscription_count'] = subscription_count
            
        return values

    def _prepare_subscriptions_domain(self, partner):
        """Prepare domain for subscription search"""
        return [('partner_id', 'child_of', partner.id)]

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_subscriptions(self, page=1, date_begin=None, date_end=None, 
                               sortby=None, search=None, search_in='content', 
                               filterby=None, **kw):
        """Display user's subscriptions"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SubscriptionSudo = request.env['subscription.subscription'].sudo()

        domain = self._prepare_subscriptions_domain(partner)

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'date_start desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'plan': {'label': _('Plan'), 'order': 'plan_id'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'trial': {'label': _('Trial'), 'domain': [('state', '=', 'trial')]},
            'suspended': {'label': _('Suspended'), 'domain': [('state', '=', 'suspended')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
            'expired': {'label': _('Expired'), 'domain': [('state', '=', 'expired')]},
        }
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'name': {'input': 'name', 'label': _('Search in Name')},
            'plan': {'input': 'plan', 'label': _('Search in Plan')},
        }

        # Default sort order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Default filter
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'name'):
                search_domain = ['|', ('name', 'ilike', search), ('plan_id.name', 'ilike', search)]
            elif search_in == 'plan':
                search_domain = [('plan_id.name', 'ilike', search)]
            domain += search_domain

        # Count for pager
        subscription_count = SubscriptionSudo.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/subscriptions",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 
                     'filterby': filterby, 'search_in': search_in, 'search': search},
            total=subscription_count,
            page=page,
            step=self._items_per_page
        )

        # Content - Get all subscriptions and separate by status
        all_subscriptions = SubscriptionSudo.search(domain, order=order)
        
        # Separate active and inactive subscriptions
        active_subscriptions = all_subscriptions.filtered(
            lambda s: s.state in ('active', 'trial')
        )
        inactive_subscriptions = all_subscriptions.filtered(
            lambda s: s.state not in ('active', 'trial')
        )
        
        # Apply pagination to combined results
        start = pager['offset']
        end = start + self._items_per_page
        subscriptions = all_subscriptions[start:end]
        
        request.session['my_subscriptions_history'] = subscriptions.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'subscriptions': subscriptions,
            'active_subscriptions': active_subscriptions,
            'inactive_subscriptions': inactive_subscriptions,
            'page_name': 'subscription',
            'archive_groups': [],
            'default_url': '/my/subscriptions',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("subscription_management.portal_my_subscriptions", values)

    @http.route(['/my/subscriptions/<int:subscription_id>'], 
                type='http', auth="public", website=True)
    def portal_subscription_detail(self, subscription_id, access_token=None, **kw):
        """Display subscription detail page"""
        try:
            subscription_sudo = self._document_check_access('subscription.subscription', 
                                                          subscription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Get recent usage records
        usage_records = request.env['subscription.usage'].sudo().search([
            ('subscription_id', '=', subscription_id)
        ], order='date desc', limit=10)

        values = {
            'subscription': subscription_sudo,
            'usage_records': usage_records,
            'page_name': 'subscription',
        }
        return request.render("subscription_management.portal_subscription_detail", values)

    @http.route(['/my/subscriptions/<int:subscription_id>/suspend'], 
                type='http', auth="user", website=True, methods=['GET'])
    def portal_subscription_suspend(self, subscription_id, **kw):
        """Suspend subscription"""
        try:
            subscription_sudo = self._document_check_access('subscription.subscription', 
                                                          subscription_id)
            if subscription_sudo.state in ('active', 'trial'):
                subscription_sudo.action_suspend()
                request.env['mail.message'].sudo().create({
                    'model': 'subscription.subscription',
                    'res_id': subscription_id,
                    'message_type': 'notification',
                    'body': _('Subscription suspended by customer'),
                })
            return request.redirect(f'/my/subscriptions/{subscription_id}')
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/subscriptions/<int:subscription_id>/cancel'], 
                type='http', auth="user", website=True, methods=['GET'])
    def portal_subscription_cancel(self, subscription_id, **kw):
        """Cancel subscription"""
        try:
            subscription_sudo = self._document_check_access('subscription.subscription', 
                                                          subscription_id)
            if subscription_sudo.state not in ('cancelled', 'expired'):
                subscription_sudo.action_cancel()
                
                # Send cancellation email
                template = request.env.ref('subscription_management.email_template_subscription_cancelled', 
                                         raise_if_not_found=False)
                if template:
                    template.sudo().send_mail(subscription_id, force_send=True)
                
                request.env['mail.message'].sudo().create({
                    'model': 'subscription.subscription',
                    'res_id': subscription_id,
                    'message_type': 'notification',
                    'body': _('Subscription cancelled by customer'),
                })
            return request.redirect(f'/my/subscriptions/{subscription_id}')
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/subscriptions/<int:subscription_id>/reactivate'], 
                type='http', auth="user", website=True, methods=['GET'])
    def portal_subscription_reactivate(self, subscription_id, **kw):
        """Reactivate subscription"""
        try:
            subscription_sudo = self._document_check_access('subscription.subscription', 
                                                          subscription_id)
            if subscription_sudo.state == 'suspended':
                subscription_sudo.action_activate()
                request.env['mail.message'].sudo().create({
                    'model': 'subscription.subscription',
                    'res_id': subscription_id,
                    'message_type': 'notification',
                    'body': _('Subscription reactivated by customer'),
                })
            return request.redirect(f'/my/subscriptions/{subscription_id}')
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/subscription/plans'], type='http', auth="public", website=True)
    def subscription_plans(self, **kw):
        """Display available subscription plans"""
        plans = request.env['subscription.plan'].sudo().search([
            ('active', '=', True)
        ], order='sequence, price')
        
        values = {
            'plans': plans,
            'page_name': 'subscription_plans',
        }
        return request.render("subscription_management.portal_subscription_plans", values)

    @http.route(['/my/subscriptions/subscribe/<int:plan_id>'], 
                type='http', auth="user", website=True)
    def subscription_subscribe(self, plan_id, **kw):
        """Subscribe to a plan"""
        plan = request.env['subscription.plan'].sudo().browse(plan_id)
        if not plan.exists() or not plan.active:
            return request.redirect('/subscription/plans')

        partner = request.env.user.partner_id
        
        # Check if customer already has active subscription for this plan
        existing = request.env['subscription.subscription'].sudo().search([
            ('partner_id', '=', partner.id),
            ('plan_id', '=', plan.id),
            ('state', 'in', ['active', 'trial'])
        ], limit=1)
        
        if existing:
            # Redirect to existing subscription with a message
            return request.redirect(f'/my/subscriptions/{existing.id}?already_subscribed=1')
        
        # Create subscription
        subscription_vals = {
            'partner_id': partner.id,
            'plan_id': plan.id,
            'state': 'draft',
        }
        
        subscription = request.env['subscription.subscription'].sudo().create(subscription_vals)
        
        # Start trial or activate
        if plan.trial_period > 0:
            subscription.action_start_trial()
        else:
            subscription.action_activate()
        
        # Send welcome email
        template = request.env.ref('subscription_management.email_template_subscription_welcome', 
                                 raise_if_not_found=False)
        if template:
            template.sudo().send_mail(subscription.id, force_send=True)
        
        return request.redirect(f'/my/subscriptions/{subscription.id}')

    def _document_check_access(self, model_name, document_id, access_token=None):
        """Check access to subscription document"""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo().exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))
        
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if not access_token or not document_sudo.access_token or \
               not document_sudo.access_token == access_token:
                raise
        
        return document_sudo