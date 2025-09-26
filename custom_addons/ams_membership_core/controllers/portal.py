# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR
import logging

_logger = logging.getLogger(__name__)


class MembershipPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add membership counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'membership_count' in counters:
            membership_count = request.env['ams.membership.membership'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', 'in', ['active', 'grace'])
            ]) if request.env.user.partner_id.is_member else 0
            values['membership_count'] = membership_count

        if 'subscription_count' in counters:
            subscription_count = request.env['ams.membership.subscription'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', 'in', ['active', 'grace'])
            ])
            values['subscription_count'] = subscription_count

        if 'course_count' in counters:
            course_count = request.env['ams.membership.course'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id),
                ('state', 'in', ['active', 'grace'])
            ])
            values['course_count'] = course_count

        return values

    def _prepare_portal_layout_values(self):
        """Add membership menu items to portal layout"""
        values = super()._prepare_portal_layout_values()
        
        if request.env.user.partner_id.is_member:
            values['page_name'] = 'membership'
            
        return values

    # Membership Dashboard
    @http.route(['/my/membership', '/my/membership/dashboard'], type='http', auth="user", website=True)
    def portal_membership_dashboard(self, **kw):
        """Member dashboard showing overview of all memberships and subscriptions"""
        partner = request.env.user.partner_id
        
        if not partner.is_member:
            return request.redirect('/my')
        
        # Get membership summary
        membership_summary = partner.get_active_memberships_summary()
        
        # Get renewal eligibility
        renewal_eligible = partner.check_renewal_eligibility()
        
        # Get member benefits
        benefits = partner.get_member_benefits()
        
        # Calculate engagement score
        engagement_score = partner.calculate_member_engagement_score()
        
        values = {
            'page_name': 'membership_dashboard',
            'partner': partner,
            'membership_summary': membership_summary,
            'renewal_eligible': renewal_eligible,
            'benefits': benefits,
            'engagement_score': engagement_score,
        }
        
        return request.render("ams_membership_core.portal_membership_dashboard", values)

    # Memberships
    @http.route(['/my/memberships', '/my/memberships/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_memberships(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """List all memberships for the current user"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Membership = request.env['ams.membership.membership']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'start_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'status': {'label': _('Status'), 'order': 'state'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'grace': {'label': _('Grace Period'), 'domain': [('state', '=', 'grace')]},
            'expired': {'label': _('Expired'), 'domain': [('state', 'in', ['lapsed', 'expired'])]},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('start_date', '>', date_begin), ('start_date', '<=', date_end)]

        # Count
        membership_count = Membership.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/memberships",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=membership_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        memberships = Membership.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_memberships_history'] = memberships.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'memberships': memberships,
            'page_name': 'membership',
            'archive_groups': [],
            'default_url': '/my/memberships',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("ams_membership_core.portal_my_memberships", values)

    @http.route(['/my/membership/<int:membership_id>'], type='http', auth="user", website=True)
    def portal_membership_detail(self, membership_id, access_token=None, **kw):
        """Show membership details"""
        try:
            membership_sudo = self._document_check_access('ams.membership.membership', membership_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'page_name': 'membership',
            'membership': membership_sudo,
            'benefits': membership_sudo.get_membership_benefits(),
        }
        return request.render("ams_membership_core.portal_membership_detail", values)

    # Subscriptions
    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_subscriptions(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """List all subscriptions for the current user"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Subscription = request.env['ams.membership.subscription']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'start_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'type': {'label': _('Type'), 'order': 'subscription_type'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'newsletter': {'label': _('Newsletters'), 'domain': [('subscription_type', '=', 'newsletter')]},
            'publication': {'label': _('Publications'), 'domain': [('subscription_type', '=', 'publication')]},
            'digital': {'label': _('Digital Access'), 'domain': [('digital_access_granted', '=', True)]},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Count
        subscription_count = Subscription.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/subscriptions",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=subscription_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        subscriptions = Subscription.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'default_url': '/my/subscriptions',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("ams_membership_core.portal_my_subscriptions", values)

    @http.route(['/my/subscription/<int:subscription_id>'], type='http', auth="user", website=True)
    def portal_subscription_detail(self, subscription_id, access_token=None, **kw):
        """Show subscription details"""
        try:
            subscription_sudo = self._document_check_access('ams.membership.subscription', subscription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'page_name': 'subscription',
            'subscription': subscription_sudo,
            'summary': subscription_sudo.get_subscription_summary(),
        }
        return request.render("ams_membership_core.portal_subscription_detail", values)

    @http.route(['/my/subscription/<int:subscription_id>/access'], type='http', auth="user", website=True)
    def portal_subscription_access(self, subscription_id, access_token=None, **kw):
        """Access subscription content"""
        try:
            subscription_sudo = self._document_check_access('ams.membership.subscription', subscription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Record access
        subscription_sudo.action_record_access()

        # Redirect to content or show access page
        if subscription_sudo.login_url:
            return request.redirect(subscription_sudo.login_url)
        else:
            values = {
                'page_name': 'subscription',
                'subscription': subscription_sudo,
            }
            return request.render("ams_membership_core.portal_subscription_access", values)

    # Courses
    @http.route(['/my/courses', '/my/courses/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_courses(self, page=1, sortby=None, filterby=None, **kw):
        """List all courses for the current user"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Course = request.env['ams.membership.course']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'enrollment_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'progress': {'label': _('Progress'), 'order': 'progress_percentage desc'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('completion_status', '=', 'in_progress')]},
            'completed': {'label': _('Completed'), 'domain': [('completion_status', '=', 'completed')]},
            'not_started': {'label': _('Not Started'), 'domain': [('completion_status', '=', 'not_started')]},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Count
        course_count = Course.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/courses",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=course_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        courses = Course.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'courses': courses,
            'page_name': 'course',
            'default_url': '/my/courses',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("ams_membership_core.portal_my_courses", values)

    @http.route(['/my/course/<int:course_id>'], type='http', auth="user", website=True)
    def portal_course_detail(self, course_id, access_token=None, **kw):
        """Show course details"""
        try:
            course_sudo = self._document_check_access('ams.membership.course', course_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'page_name': 'course',
            'course': course_sudo,
            'summary': course_sudo.get_course_summary(),
            'access_check': course_sudo.check_access_eligibility(),
        }
        return request.render("ams_membership_core.portal_course_detail", values)

    @http.route(['/my/course/<int:course_id>/access'], type='http', auth="user", website=True)
    def portal_course_access(self, course_id, access_token=None, **kw):
        """Access course content"""
        try:
            course_sudo = self._document_check_access('ams.membership.course', course_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check access eligibility
        access_check = course_sudo.check_access_eligibility()
        if not access_check['eligible']:
            values = {
                'page_name': 'course',
                'course': course_sudo,
                'access_denied': True,
                'access_issues': access_check['issues'],
            }
            return request.render("ams_membership_core.portal_course_access", values)

        # Access course
        course_sudo.action_access_course()

        # Redirect to course platform or show access page
        if course_sudo.access_url:
            return request.redirect(course_sudo.access_url)
        else:
            values = {
                'page_name': 'course',
                'course': course_sudo,
                'access_granted': True,
            }
            return request.render("ams_membership_core.portal_course_access", values)

    # Donations
    @http.route(['/my/donations', '/my/donations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_donations(self, page=1, sortby=None, filterby=None, **kw):
        """List all donations for the current user"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Donation = request.env['ams.membership.donation']

        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'start_date desc'},
            'amount': {'label': _('Amount'), 'order': 'total_donated desc'},
            'type': {'label': _('Type'), 'order': 'donation_type'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'general': {'label': _('General Fund'), 'domain': [('donation_type', '=', 'general')]},
            'scholarship': {'label': _('Scholarship'), 'domain': [('donation_type', '=', 'scholarship')]},
            'memorial': {'label': _('Memorial'), 'domain': [('is_memorial_gift', '=', True)]},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Count
        donation_count = Donation.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/donations",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=donation_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        donations = Donation.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'donations': donations,
            'page_name': 'donation',
            'default_url': '/my/donations',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        return request.render("ams_membership_core.portal_my_donations", values)

    @http.route(['/my/donation/<int:donation_id>'], type='http', auth="user", website=True)
    def portal_donation_detail(self, donation_id, access_token=None, **kw):
        """Show donation details"""
        try:
            donation_sudo = self._document_check_access('ams.membership.donation', donation_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'page_name': 'donation',
            'donation': donation_sudo,
            'benefits': donation_sudo.get_donor_benefits(),
            'impact': donation_sudo.get_impact_summary(),
        }
        return request.render("ams_membership_core.portal_donation_detail", values)

    # Renewal and Upgrade Actions
    @http.route(['/my/membership/<int:membership_id>/renew'], type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_membership_renew(self, membership_id, access_token=None, **kw):
        """Membership renewal page"""
        try:
            membership_sudo = self._document_check_access('ams.membership.membership', membership_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not membership_sudo.can_be_renewed:
            return request.redirect(f'/my/membership/{membership_id}')

        if request.httprequest.method == 'POST':
            # Create renewal order
            try:
                membership_sudo.action_create_renewal_invoice()
                return request.redirect('/my/orders')
            except Exception as e:
                _logger.error(f"Renewal failed: {str(e)}")
                return request.redirect(f'/my/membership/{membership_id}')

        values = {
            'page_name': 'membership',
            'membership': membership_sudo,
            'renewal_check': membership_sudo.check_renewal_eligibility(),
        }
        return request.render("ams_membership_core.portal_membership_renew", values)

    # Utility methods
    def _document_check_access(self, model_name, document_id, access_token=None):
        """Check access to membership documents"""
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo()
        
        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if access_token and document_sudo.access_token and access_token == document_sudo.access_token:
                return document_sudo
            else:
                raise
        
        # Check if user owns the document
        if document_sudo.partner_id.id != request.env.user.partner_id.id:
            raise AccessError(_("You do not have access to this document."))
        
        return document_sudo