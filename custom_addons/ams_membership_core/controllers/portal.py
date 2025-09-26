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
        """ENHANCED: Prepare portal layout values with complete member context"""
        values = super()._prepare_portal_layout_values()
        
        partner = request.env.user.partner_id
        
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
                
                # ENHANCED: Get chapter memberships for portal home
                chapter_memberships = request.env['ams.membership']
                chapter_membership_count = 0
                total_subscription_count = 0
                
                try:
                    if is_member:
                        # Get all active memberships
                        all_memberships = request.env['ams.membership'].search([
                            ('partner_id', '=', partner.id),
                            ('state', '=', 'active')
                        ])
                        
                        # Filter chapter memberships
                        chapter_memberships = all_memberships.filtered(
                            lambda m: getattr(m, 'is_chapter_membership', False)
                        )
                        chapter_membership_count = len(chapter_memberships)
                        
                        # Get subscription count
                        total_subscription_count = request.env['ams.subscription'].search_count([
                            ('partner_id', '=', partner.id),
                            ('state', '=', 'active')
                        ])
                        
                except Exception as e:
                    _logger.warning(f"Error getting member data: {e}")
                
                # TEMPLATE CONTEXT ONLY - these are for display, not counters
                values.update({
                    'is_member': is_member,
                    'member_number': member_number,
                    'member_type': member_type_name,
                    'member_status': member_status,
                    'membership_start_date': membership_start_date,
                    'membership_end_date': membership_end_date,
                    'next_renewal_date': next_renewal_date,
                    
                    # CHAPTER CONTEXT - FIXED
                    'chapter_memberships': chapter_memberships,
                    'chapter_membership_count': chapter_membership_count,
                })
                
                # Only add additional member data if they are a member
                if is_member:
                    try:
                        current_membership = getattr(partner, 'current_membership_id', None)
                        active_benefits = getattr(partner, 'active_benefit_ids', partner.env['ams.benefit'])
                        pending_renewals_count = getattr(partner, 'pending_renewals_count', 0)
                        
                        values.update({
                            'current_membership': current_membership,
                            'active_benefits': active_benefits,
                            'pending_renewals_count': pending_renewals_count,
                            'total_subscription_count': total_subscription_count,
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
                    'chapter_memberships': request.env['ams.membership'],
                    'chapter_membership_count': 0,
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
                'chapter_memberships': request.env['ams.membership'],
                'chapter_membership_count': 0,
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
        """FIXED: Display member's memberships with proper data separation"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        _logger.info(f"Portal memberships accessed by user {request.env.user.login} for partner {partner.id}")

        # Check if partner exists and is a member
        if not partner or not getattr(partner, 'is_member', False):
            _logger.warning(f"Access denied - partner: {partner}, is_member: {getattr(partner, 'is_member', False)}")
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

            _logger.info(f"Searching memberships with domain: {domain}")

            # Count for pager
            membership_count = Membership.search_count(domain)
            _logger.info(f"Found {membership_count} memberships for partner {partner.id}")

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

            _logger.info(f"Retrieved {len(memberships)} memberships")

            # CRITICAL FIX: Properly separate memberships for templates
            regular_memberships = []
            chapter_memberships = []
            
            for membership in memberships:
                try:
                    if getattr(membership, 'is_chapter_membership', False):
                        chapter_memberships.append(membership)
                    else:
                        regular_memberships.append(membership)
                except Exception as e:
                    _logger.warning(f"Error checking membership type for {membership.id}: {e}")
                    regular_memberships.append(membership)  # Default to regular

            # Convert to recordsets for template compatibility
            regular_memberships = Membership.browse([m.id for m in regular_memberships])
            chapter_memberships = Membership.browse([m.id for m in chapter_memberships])

            _logger.info(f"Separated: {len(regular_memberships)} regular, {len(chapter_memberships)} chapter")

            # Add page-specific data with ALL required template variables
            values.update({
                'date': date_begin,
                'memberships': memberships,                    # All memberships (for compatibility)
                'regular_memberships': regular_memberships,    # Regular only
                'chapter_memberships': chapter_memberships,    # Chapter only - CRITICAL FIX
                'page_name': 'membership',
                'pager': pager,
                'default_url': '/my/memberships',
                'searchbar_sortings': searchbar_sortings,
                'searchbar_inputs': searchbar_inputs,
                'search_in': search_in,
                'search': search,
                'sortby': sortby,
                
                # Ensure member context is available
                'partner': partner,
            })
            
        except Exception as e:
            _logger.error(f"Error in portal_my_memberships: {e}", exc_info=True)
            values.update({
                'memberships': Membership,
                'regular_memberships': Membership,
                'chapter_memberships': Membership,
                'page_name': 'membership',
                'error_message': str(e),
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
        """Display membership details - SAFE VERSION WITH CURRENCY FIX"""
        try:
            membership_sudo = self._document_check_access('ams.membership', membership_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Get currency for monetary widget - this fixes the KeyError
        currency = membership_sudo.currency_id or request.env.company.currency_id
        
        values = {
            'membership': membership_sudo,
            'partner': membership_sudo.partner_id,
            'member_number': getattr(membership_sudo.partner_id, 'member_number', None) or 'Not Assigned',
            'page_name': 'membership',
            
            # Currency context required for monetary widget
            'display_currency': currency,
            'currency': currency,
            
            # Additional portal context that might be needed
            'company': request.env.company,
            'user': request.env.user,
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

    @http.route(['/my/chapters'], type='http', auth="user", website=True)
    def portal_my_chapters(self, **kw):
        """Display member's chapter memberships - NEW METHOD"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        if not partner or not getattr(partner, 'is_member', False):
            return request.render("ams_membership_core.portal_no_membership_access", values)

        try:
            # Get all chapter memberships
            chapter_memberships = request.env['ams.membership'].search([
                ('partner_id', '=', partner.id),
                ('is_chapter_membership', '=', True)
            ])

            # Calculate analytics
            total_events_attended = sum(m.chapter_events_attended or 0 for m in chapter_memberships)
            total_volunteer_hours = sum(m.chapter_volunteer_hours or 0 for m in chapter_memberships)
            
            active_chapters = chapter_memberships.filtered(lambda m: m.state == 'active')
            if active_chapters:
                scores = [m.chapter_engagement_score for m in active_chapters if m.chapter_engagement_score > 0]
                average_engagement_score = sum(scores) / len(scores) if scores else 0
            else:
                average_engagement_score = 0

            values.update({
                'chapter_memberships': chapter_memberships,
                'total_events_attended': total_events_attended,
                'total_volunteer_hours': total_volunteer_hours,
                'average_engagement_score': average_engagement_score,
                'page_name': 'chapters',
            })

        except Exception as e:
            _logger.error(f"Error in portal_my_chapters: {e}")
            values.update({
                'chapter_memberships': request.env['ams.membership'],
                'page_name': 'chapters',
            })

        return request.render("ams_membership_core.portal_my_chapters", values)

    @http.route(['/my/chapters/<int:membership_id>'], 
                type='http', auth="user", website=True)
    def portal_chapter_detail(self, membership_id, **kw):
        """Display chapter membership details"""
        try:
            membership_sudo = self._document_check_access('ams.membership', membership_id)
            
            # Verify it's a chapter membership
            if not getattr(membership_sudo, 'is_chapter_membership', False):
                return request.redirect('/my/memberships')
                
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'membership': membership_sudo,
            'chapter': membership_sudo,  # Alias for template compatibility
            'page_name': 'chapters',
        }
        return request.render("ams_membership_core.portal_membership_detail", values)

    # CRITICAL: Custom invoice handler for membership/subscription invoices
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="user", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        """Custom invoice detail handler for membership/subscription invoices"""
        try:
            # Use enhanced document access check
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
            
            # Check if this is a membership/subscription invoice
            if hasattr(invoice_sudo, 'has_subscription_lines') and invoice_sudo.has_subscription_lines:
                # Find related membership/subscription for context
                membership_line = invoice_sudo.invoice_line_ids.filtered(lambda l: hasattr(l, 'related_membership_id') and l.related_membership_id)
                subscription_line = invoice_sudo.invoice_line_ids.filtered(lambda l: hasattr(l, 'related_subscription_id') and l.related_subscription_id)
                
                values = {
                    'invoice': invoice_sudo,
                    'related_membership': membership_line.related_membership_id if membership_line else None,
                    'related_subscription': subscription_line.related_subscription_id if subscription_line else None,
                    'report_type': report_type,
                    'download': download,
                    'page_name': 'invoice',
                    'token': access_token,
                }
                
                # Use standard invoice template
                return request.render("account.portal_invoice_page", values)
            else:
                # Let the standard account portal handle non-subscription invoices
                return super()._document_check_access('account.move', invoice_id, access_token)
                
        except (AccessError, MissingError):
            # Redirect to portal home if access denied
            return request.redirect('/my')

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
                # Use access token for invoice redirect
                redirect_url = f'/my/invoices/{renewal.invoice_id.id}'
                if renewal.invoice_id.access_token:
                    redirect_url += f'?access_token={renewal.invoice_id.access_token}'
                return request.redirect(redirect_url)
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

    # DEBUG ROUTES FOR TROUBLESHOOTING
    @http.route(['/my/debug'], type='http', auth="user", website=True)
    def debug_portal(self, **kw):
        """Debug route to check portal access"""
        partner = request.env.user.partner_id
        user = request.env.user
        
        debug_info = f"""
        <html><head><title>Portal Debug</title></head><body>
        <h2>Portal Debug Information</h2>
        <h3>User Info</h3>
        <p><strong>User ID:</strong> {user.id}</p>
        <p><strong>User Login:</strong> {user.login}</p>
        <p><strong>User Groups:</strong> {', '.join(user.groups_id.mapped('name'))}</p>
        
        <h3>Partner Info</h3>
        <p><strong>Partner ID:</strong> {partner.id}</p>
        <p><strong>Partner Name:</strong> {partner.name}</p>
        <p><strong>Partner Email:</strong> {partner.email}</p>
        <p><strong>Is Member:</strong> {getattr(partner, 'is_member', 'FIELD_NOT_FOUND')}</p>
        <p><strong>Member Status:</strong> {getattr(partner, 'member_status', 'FIELD_NOT_FOUND')}</p>
        <p><strong>Member Number:</strong> {getattr(partner, 'member_number', 'FIELD_NOT_FOUND')}</p>
        
        <h3>Access Tests</h3>
        """
        
        try:
            # Test membership model access
            membership_count = request.env['ams.membership'].search_count([])
            debug_info += f"<p><strong>Total Memberships (no domain):</strong> {membership_count}</p>"
        except Exception as e:
            debug_info += f"<p><strong>Membership Access Error:</strong> {str(e)}</p>"
        
        try:
            # Test partner membership access
            partner_memberships = request.env['ams.membership'].search([('partner_id', '=', partner.id)])
            debug_info += f"<p><strong>Partner Memberships Found:</strong> {len(partner_memberships)}</p>"
            for membership in partner_memberships:
                debug_info += f"<p>  - {membership.name}: {membership.state} ({membership.product_id.name})</p>"
        except Exception as e:
            debug_info += f"<p><strong>Partner Membership Error:</strong> {str(e)}</p>"
        
        try:
            # Test direct SQL query
            request.env.cr.execute("""
                SELECT id, name, state, partner_id 
                FROM ams_membership 
                WHERE partner_id = %s
            """, (partner.id,))
            sql_results = request.env.cr.fetchall()
            debug_info += f"<p><strong>Direct SQL Results:</strong> {len(sql_results)} records</p>"
            for row in sql_results:
                debug_info += f"<p>  - ID {row[0]}: {row[1]} ({row[2]})</p>"
        except Exception as e:
            debug_info += f"<p><strong>SQL Query Error:</strong> {str(e)}</p>"
        
        debug_info += """
        <h3>Test Links</h3>
        <a href="/my" style="margin-right: 10px;">Portal Home</a>
        <a href="/my/memberships" style="margin-right: 10px;">Memberships</a>
        <a href="/my/chapters" style="margin-right: 10px;">Chapters</a>
        </body></html>
        """
        return debug_info

    @http.route(['/my/membership/debug'], type='http', auth="user", website=True)
    def portal_membership_debug(self, **kw):
        """Detailed membership debug with template context"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        try:
            memberships = request.env['ams.membership'].search([('partner_id', '=', partner.id)])
            regular_memberships = memberships.filtered(lambda m: not getattr(m, 'is_chapter_membership', False))
            chapter_memberships = memberships.filtered(lambda m: getattr(m, 'is_chapter_membership', False))
            
            values.update({
                'memberships': memberships,
                'regular_memberships': regular_memberships, 
                'chapter_memberships': chapter_memberships,
                'debug_partner_id': partner.id,
                'debug_membership_count': len(memberships),
                'debug_regular_count': len(regular_memberships),
                'debug_chapter_count': len(chapter_memberships),
            })
        except Exception as e:
            values.update({
                'debug_error': str(e),
                'memberships': request.env['ams.membership'],
            })
        
        return request.render("ams_membership_core.portal_membership_debug", values)

    def _document_check_access(self, model_name, document_id, access_token=None):
        """ENHANCED: Check access to membership/subscription documents AND invoices"""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.with_user(request.env.ref('base.user_root').id)
        
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            # ENHANCED: Special handling for subscription invoices
            if model_name == 'account.move':
                partner = request.env.user.partner_id
                
                # Check if invoice belongs to the current user
                if document_sudo.partner_id == partner:
                    # Additional check for subscription invoices
                    if getattr(document_sudo, 'has_subscription_lines', False):
                        _logger.info(f"Granting access to subscription invoice {document_id} for partner {partner.id}")
                        return document_sudo
                    
                    # Check if they have general invoice access (fallback)
                    try:
                        # Try to access with token if provided
                        if access_token and hasattr(document_sudo, 'access_token'):
                            if document_sudo.access_token == access_token:
                                return document_sudo
                    except Exception as e:
                        _logger.warning(f"Token validation failed: {e}")
                
                # If it's an invoice and user should have access, grant it
                if document_sudo.partner_id == partner and document_sudo.state == 'posted':
                    return document_sudo
                    
            raise AccessError(_("Access Denied"))

        # Additional check for partner ownership for membership/subscription documents
        if hasattr(document_sudo, 'partner_id') and document_sudo.partner_id != request.env.user.partner_id:
            raise AccessError(_("Access Denied"))
            
        return document_sudo


    