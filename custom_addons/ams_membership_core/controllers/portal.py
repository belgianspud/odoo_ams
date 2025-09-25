# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv import expression
from odoo.tools import groupby as groupbyelem

import logging
_logger = logging.getLogger(__name__)


class MembershipPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        """Add membership and subscription counts to portal home - FIXED VERSION"""
        # CRITICAL: First call parent to get base values
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        
        # CRITICAL: Only add ACTUAL COUNTERS to the values dict
        # These are the only values that should be numeric counters
        try:
            if partner and getattr(partner, 'is_member', False):
                # Only add counters if they're specifically requested
                if 'membership_count' in counters:
                    try:
                        membership_count = request.env['ams.membership'].search_count([
                            ('partner_id', '=', partner.id)
                        ]) if request.env['ams.membership'].check_access_rights('read', raise_exception=False) else 0
                        values['membership_count'] = membership_count
                    except Exception as e:
                        _logger.error(f"Error getting membership count: {e}")
                        values['membership_count'] = 0

                if 'subscription_count' in counters:
                    try:
                        subscription_count = request.env['ams.subscription'].search_count([
                            ('partner_id', '=', partner.id)
                        ]) if request.env['ams.subscription'].check_access_rights('read', raise_exception=False) else 0
                        values['subscription_count'] = subscription_count
                    except Exception as e:
                        _logger.error(f"Error getting subscription count: {e}")
                        values['subscription_count'] = 0
        except Exception as e:
            _logger.error(f"Error in counter processing: {e}")
        
        return values

    def _prepare_portal_layout_values(self):
        """Prepare portal layout values with member context - SAFE VERSION"""
        values = super()._prepare_portal_layout_values()
        
        partner = request.env.user.partner_id
        
        # CRITICAL: Add member data as TEMPLATE CONTEXT, not as counters
        # These go into template context and are NOT processed as counters
        try:
            if partner:
                # Safe foundation field access with fallbacks
                is_member = getattr(partner, 'is_member', False)
                member_number = getattr(partner, 'member_number', None) or 'Not Assigned'
                member_status = getattr(partner, 'member_status', None) or 'unknown'
                
                # Safe member_type access
                member_type_name = 'Not Set'
                if hasattr(partner, 'member_type_id') and partner.member_type_id:
                    member_type_name = partner.member_type_id.name or 'Not Set'
                
                # Safe date access
                membership_start_date = getattr(partner, 'membership_start_date', None)
                membership_end_date = getattr(partner, 'membership_end_date', None)
                next_renewal_date = getattr(partner, 'next_renewal_date', None)
                
                # TEMPLATE CONTEXT ONLY - these are for display, not counters
                values.update({
                    'is_member': is_member,
                    'member_number': member_number,
                    'member_type': member_type_name,
                    'member_status': member_status,
                    'membership_start_date': membership_start_date,
                    'membership_end_date': membership_end_date,
                    'next_renewal_date': next_renewal_date,
                })
                
                # Only add additional member data if they are a member
                if is_member:
                    try:
                        current_membership = getattr(partner, 'current_membership_id', None)
                        active_benefits = getattr(partner, 'active_benefit_ids', partner.env['ams.benefit'])
                        pending_renewals_count = getattr(partner, 'pending_renewals_count', 0)
                        total_subscription_count = getattr(partner, 'subscription_count', 0)
                        
                        values.update({
                            'current_membership': current_membership,
                            'active_benefits': active_benefits,
                            'pending_renewals_count': pending_renewals_count,
                            'total_subscription_count': total_subscription_count,  # Different name to avoid conflicts
                        })
                    except Exception as e:
                        _logger.error(f"Error getting member data: {e}")
            else:
                # Safe defaults for non-members
                values.update({
                    'is_member': False,
                    'member_number': 'Not Available',
                    'member_type': 'Not Available',
                    'member_status': 'unknown',
                    'membership_start_date': None,
                    'membership_end_date': None,
                    'next_renewal_date': None,
                    'current_membership': None,
                    'active_benefits': request.env['ams.benefit'],
                    'pending_renewals_count': 0,
                    'total_subscription_count': 0,
                })
        except Exception as e:
            _logger.error(f"Error in portal layout values: {e}")
            # Safe fallback values
            values.update({
                'is_member': False,
                'member_number': 'Not Available',
                'member_type': 'Not Available',
                'member_status': 'unknown',
                'membership_start_date': None,
                'membership_end_date': None,
                'next_renewal_date': None,
                'current_membership': None,
                'active_benefits': request.env['ams.benefit'],
                'pending_renewals_count': 0,
                'total_subscription_count': 0,
            })
            
        return values

    def _prepare_memberships_domain(self, partner):
        """Prepare domain for membership search"""
        return [('partner_id', '=', partner.id)]

    def _prepare_subscriptions_domain(self, partner):
        """Prepare domain for subscription search"""
        return [('partner_id', '=', partner.id)]

    @http.route(['/my/memberships', '/my/memberships/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_memberships(self, page=1, date_begin=None, date_end=None, 
                             sortby=None, search=None, search_in='name', **kw):
        """Display member's memberships - SAFE VERSION"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        # Check if partner exists and is a member
        if not partner or not getattr(partner, 'is_member', False):
            return request.render("ams_membership_core.portal_no_membership_access", values)

        try:
            Membership = request.env['ams.membership']
            domain = self._prepare_memberships_domain(partner)

            searchbar_sortings = {
                'date': {'label': _('Start Date'), 'order': 'start_date desc'},
                'end_date': {'label': _('End Date'), 'order': 'end_date desc'},
                'name': {'label': _('Name'), 'order': 'name'},
                'state': {'label': _('Status'), 'order': 'state'},
            }
            
            searchbar_inputs = {
                'name': {'input': 'name', 'label': _('Search in Name')},
                'product': {'input': 'product', 'label': _('Search in Product')},
            }

            # Default sort
            if not sortby:
                sortby = 'date'
            order = searchbar_sortings[sortby]['order']

            # Search
            if search and search_in:
                search_domain = []
                if search_in == 'name':
                    search_domain = ['|', ('name', 'ilike', search), 
                                   ('product_id.name', 'ilike', search)]
                elif search_in == 'product':
                    search_domain = [('product_id.name', 'ilike', search)]
                domain = expression.AND([domain, search_domain])

            # Date filtering
            if date_begin and date_end:
                domain = expression.AND([domain, [
                    ('start_date', '>=', date_begin),
                    ('start_date', '<=', date_end)
                ]])

            # Count for pager
            membership_count = Membership.search_count(domain)

            # Pager
            pager = portal_pager(
                url="/my/memberships",
                url_args={'date_begin': date_begin, 'date_end': date_end,
                         'sortby': sortby, 'search_in': search_in, 'search': search},
                total=membership_count,
                page=page,
                step=self._items_per_page
            )

            # Get memberships
            memberships = Membership.search(domain, order=order, 
                                           limit=self._items_per_page, 
                                           offset=pager['offset'])

            # Add page-specific data
            values.update({
                'date': date_begin,
                'memberships': memberships,
                'page_name': 'membership',
                'pager': pager,
                'default_url': '/my/memberships',
                'searchbar_sortings': searchbar_sortings,
                'searchbar_inputs': searchbar_inputs,
                'search_in': search_in,
                'search': search,
                'sortby': sortby,
            })
            
        except Exception as e:
            _logger.error(f"Error in portal_my_memberships: {e}")
            values.update({
                'memberships': [],
                'page_name': 'membership',
            })
            
        return request.render("ams_membership_core.portal_my_memberships", values)

    @http.route(['/my/member/profile'], type='http', auth="user", website=True)
    def portal_member_profile(self, **kw):
        """Member profile dashboard - SAFE VERSION"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        if not partner or not getattr(partner, 'is_member', False):
            return request.render("ams_membership_core.portal_no_membership_access", values)

        # Add profile-specific data
        values.update({
            'partner': partner,
            'page_name': 'member_profile',
        })

        return request.render("ams_membership_core.portal_member_profile", values)

    @http.route(['/my/memberships/<int:membership_id>'], 
                type='http', auth="user", website=True)
    def portal_membership_detail(self, membership_id, **kw):
        """Display membership details - SAFE VERSION"""
        try:
            membership_sudo = self._document_check_access('ams.membership', membership_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'membership': membership_sudo,
            'partner': membership_sudo.partner_id,
            'member_number': getattr(membership_sudo.partner_id, 'member_number', None) or 'Not Assigned',
            'page_name': 'membership',
        }
        return request.render("ams_membership_core.portal_membership_detail", values)

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_subscriptions(self, page=1, date_begin=None, date_end=None, 
                               sortby=None, search=None, search_in='name', **kw):
        """Display member's subscriptions - SAFE VERSION"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        try:
            Subscription = request.env['ams.subscription']
            domain = self._prepare_subscriptions_domain(partner)

            searchbar_sortings = {
                'date': {'label': _('Start Date'), 'order': 'start_date desc'},
                'end_date': {'label': _('End Date'), 'order': 'end_date desc'},
                'name': {'label': _('Name'), 'order': 'name'},
                'state': {'label': _('Status'), 'order': 'state'},
                'type': {'label': _('Type'), 'order': 'subscription_type'},
            }
            
            searchbar_inputs = {
                'name': {'input': 'name', 'label': _('Search in Name')},
                'product': {'input': 'product', 'label': _('Search in Product')},
                'type': {'input': 'type', 'label': _('Search in Type')},
            }

            # Default sort
            if not sortby:
                sortby = 'date'
            order = searchbar_sortings[sortby]['order']

            # Search
            if search and search_in:
                search_domain = []
                if search_in == 'name':
                    search_domain = ['|', ('name', 'ilike', search), 
                                   ('product_id.name', 'ilike', search)]
                elif search_in == 'product':
                    search_domain = [('product_id.name', 'ilike', search)]
                elif search_in == 'type':
                    search_domain = [('subscription_type', 'ilike', search)]
                domain = expression.AND([domain, search_domain])

            # Date filtering
            if date_begin and date_end:
                domain = expression.AND([domain, [
                    ('start_date', '>=', date_begin),
                    ('start_date', '<=', date_end)
                ]])

            # Count for pager
            subscription_count = Subscription.search_count(domain)

            # Pager
            pager = portal_pager(
                url="/my/subscriptions",
                url_args={'date_begin': date_begin, 'date_end': date_end,
                         'sortby': sortby, 'search_in': search_in, 'search': search},
                total=subscription_count,
                page=page,
                step=self._items_per_page
            )

            # Get subscriptions
            subscriptions = Subscription.search(domain, order=order, 
                                              limit=self._items_per_page, 
                                              offset=pager['offset'])

            values.update({
                'date': date_begin,
                'subscriptions': subscriptions,
                'page_name': 'subscription',
                'pager': pager,
                'default_url': '/my/subscriptions',
                'searchbar_sortings': searchbar_sortings,
                'searchbar_inputs': searchbar_inputs,
                'search_in': search_in,
                'search': search,
                'sortby': sortby,
            })
            
        except Exception as e:
            _logger.error(f"Error in portal_my_subscriptions: {e}")
            values.update({
                'subscriptions': [],
                'page_name': 'subscription',
            })
            
        return request.render("ams_membership_core.portal_my_subscriptions", values)

    @http.route(['/my/subscriptions/<int:subscription_id>'], 
                type='http', auth="user", website=True)
    def portal_subscription_detail(self, subscription_id, **kw):
        """Display subscription details"""
        try:
            subscription_sudo = self._document_check_access('ams.subscription', subscription_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'subscription': subscription_sudo,
            'page_name': 'subscription',
        }
        return request.render("ams_membership_core.portal_subscription_detail", values)

    @http.route(['/my/memberships/<int:membership_id>/renew'], 
                type='http', auth="user", website=True)
    def portal_membership_renew(self, membership_id, **kw):
        """Initiate membership renewal"""
        try:
            membership_sudo = self._document_check_access('ams.membership', membership_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if membership_sudo.state != 'active' or membership_sudo.auto_renew:
            return request.redirect(f'/my/memberships/{membership_id}')

        # Create renewal record
        try:
            renewal = request.env['ams.renewal'].sudo().create({
                'membership_id': membership_id,
                'renewal_date': fields.Date.today(),
                'new_end_date': membership_sudo._calculate_renewal_end_date(),
                'amount': membership_sudo.membership_fee,
                'renewal_type': 'manual',
                'state': 'draft',
            })
            
            # Create invoice for the renewal
            renewal.action_create_invoice()
            
            # Redirect to invoice payment if available
            if renewal.invoice_id:
                return request.redirect(f'/my/invoices/{renewal.invoice_id.id}')
            else:
                request.session['renewal_success'] = True
                return request.redirect(f'/my/memberships/{membership_id}')
                
        except Exception as e:
            _logger.error(f"Renewal creation failed: {str(e)}")
            return request.redirect(f'/my/memberships/{membership_id}?error=renewal_failed')

    @http.route(['/my/subscriptions/<int:subscription_id>/pause'], 
                type='http', auth="user", website=True, methods=['POST'])
    def portal_subscription_pause(self, subscription_id, **kw):
        """Pause subscription"""
        try:
            subscription_sudo = self._document_check_access('ams.subscription', subscription_id)
            if subscription_sudo.state == 'active':
                subscription_sudo.action_pause()
        except (AccessError, MissingError):
            pass
        
        return request.redirect(f'/my/subscriptions/{subscription_id}')

    @http.route(['/my/subscriptions/<int:subscription_id>/resume'], 
                type='http', auth="user", website=True, methods=['POST'])
    def portal_subscription_resume(self, subscription_id, **kw):
        """Resume subscription"""
        try:
            subscription_sudo = self._document_check_access('ams.subscription', subscription_id)
            if subscription_sudo.state == 'paused':
                subscription_sudo.action_resume()
        except (AccessError, MissingError):
            pass
        
        return request.redirect(f'/my/subscriptions/{subscription_id}')

    def _document_check_access(self, model_name, document_id, access_token=None):
        """Check access to membership/subscription documents"""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(request.env.ref('base.user_root').id)
        
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            raise AccessError(_("Access Denied"))

        # Additional check for partner ownership
        if document_sudo.partner_id != request.env.user.partner_id:
            raise AccessError(_("Access Denied"))
            
        return document_sudo