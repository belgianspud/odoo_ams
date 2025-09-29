# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class WebsiteCourseSale(WebsiteSale):
    """Website controller for course sales and catalog"""

    @http.route(['/shop/courses'], type='http', auth="public", website=True, sitemap=True)
    def course_catalog(self, page=0, category=None, search='', ppg=False, **post):
        """Course catalog page with filtering and search"""
        
        # Get course products
        domain = [
            ('is_subscription_product', '=', True),
            ('product_class', '=', 'courses'),
            ('website_published', '=', True),
            ('sale_ok', '=', True)
        ]
        
        # Add search filter
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('course_id.name', 'ilike', search),
                ('course_id.description', 'ilike', search)
            ]
        
        # Add category filter
        if category:
            domain.append(('course_id.course_category', '=', category))
        
        # Get products
        Product = request.env['product.template']
        products = Product.search(domain, order='name')
        
        # Get course categories for filter
        categories = request.env['product.template'].search([
            ('product_class', '=', 'courses'),
            ('website_published', '=', True),
            ('course_id.course_category', '!=', False)
        ]).mapped('course_id.course_category')
        
        category_options = []
        if categories:
            category_selection = dict(request.env['slide.channel']._fields['course_category'].selection)
            category_options = [(cat, category_selection.get(cat, cat)) for cat in set(categories)]
            category_options.sort(key=lambda x: x[1])
        
        # Build course data with enhanced information
        course_data = []
        current_user = request.env.user
        is_member = current_user.partner_id.is_member if current_user != request.env.ref('base.public_user') else False
        
        for product in products:
            course_info = product._get_course_info_for_website()
            
            # Get appropriate pricing
            member_price = product.member_price if product.member_price > 0 else product.list_price
            non_member_price = product.list_price
            display_price = member_price if is_member else non_member_price
            
            # Check enrollment eligibility
            eligibility = product.check_course_enrollment_eligibility(current_user.partner_id)
            
            # Check if already enrolled
            already_enrolled = False
            if current_user != request.env.ref('base.public_user') and product.course_id:
                existing_enrollment = request.env['slide.channel.partner'].sudo().search([
                    ('channel_id', '=', product.course_id.id),
                    ('partner_id', '=', current_user.partner_id.id)
                ], limit=1)
                already_enrolled = bool(existing_enrollment)
            
            course_data.append({
                'product': product,
                'course_info': course_info,
                'member_price': member_price,
                'non_member_price': non_member_price,
                'display_price': display_price,
                'show_member_discount': is_member and product.member_price > 0 and product.member_price < product.list_price,
                'discount_amount': non_member_price - member_price if member_price < non_member_price else 0,
                'eligibility': eligibility,
                'already_enrolled': already_enrolled,
                'can_purchase': eligibility['eligible'] and not already_enrolled,
            })
        
        # Pagination
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20
        
        pager = request.website.pager(
            url='/shop/courses',
            url_args={'search': search, 'category': category},
            total=len(course_data),
            page=page,
            step=ppg
        )
        
        # Apply pagination
        offset = pager['offset']
        course_data = course_data[offset:offset + ppg]
        
        values = {
            'courses': course_data,
            'search': search,
            'category': category,
            'categories': category_options,
            'is_member': is_member,
            'pager': pager,
            'course_count': len(products),
        }
        
        return request.render("ams_membership_core.course_catalog", values)

    @http.route(['/shop/course/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=True)
    def course_detail(self, product, **kwargs):
        """Individual course detail page"""
        
        # Verify this is a course product
        if product.product_class != 'courses' or not product.website_published:
            return request.redirect('/shop/courses')
        
        current_user = request.env.user
        is_member = current_user.partner_id.is_member if current_user != request.env.ref('base.public_user') else False
        
        # Check if already enrolled
        already_enrolled = False
        enrollment = None
        if current_user != request.env.ref('base.public_user') and product.course_id:
            enrollment = request.env['slide.channel.partner'].sudo().search([
                ('channel_id', '=', product.course_id.id),
                ('partner_id', '=', current_user.partner_id.id)
            ], limit=1)
            already_enrolled = bool(enrollment)
        
        # Get course information
        course_info = product._get_course_info_for_website()
        
        # Get pricing
        member_price = product.member_price if product.member_price > 0 else product.list_price
        non_member_price = product.list_price
        display_price = member_price if is_member else non_member_price
        
        # Check enrollment eligibility
        eligibility = product.check_course_enrollment_eligibility(current_user.partner_id)
        
        # Get course reviews/ratings (if available)
        reviews = []
        if product.course_id:
            # Get completed enrollments with ratings
            completed_enrollments = request.env['slide.channel.partner'].sudo().search([
                ('channel_id', '=', product.course_id.id),
                ('completed', '=', True),
                ('rating', '>', 0)
            ], limit=10, order='write_date desc')
            
            for enroll in completed_enrollments:
                if enroll.partner_id.name:  # Only show if partner name is available
                    reviews.append({
                        'partner_name': enroll.partner_id.name,
                        'rating': enroll.rating,
                        'date': enroll.write_date,
                        'comment': getattr(enroll, 'review_comment', '')  # If review comments exist
                    })
        
        # Get related/similar courses
        related_courses = []
        if product.course_id and product.course_id.course_category:
            related_products = request.env['product.template'].search([
                ('product_class', '=', 'courses'),
                ('website_published', '=', True),
                ('course_id.course_category', '=', product.course_id.course_category),
                ('id', '!=', product.id)
            ], limit=4)
            
            for related in related_products:
                related_info = related._get_course_info_for_website()
                related_courses.append({
                    'product': related,
                    'course_info': related_info,
                    'price': related.member_price if is_member and related.member_price > 0 else related.list_price
                })
        
        values = {
            'product': product,
            'course_info': course_info,
            'member_price': member_price,
            'non_member_price': non_member_price,
            'display_price': display_price,
            'show_member_discount': is_member and product.member_price > 0 and product.member_price < product.list_price,
            'discount_amount': non_member_price - member_price if member_price < non_member_price else 0,
            'is_member': is_member,
            'already_enrolled': already_enrolled,
            'enrollment': enrollment,
            'eligibility': eligibility,
            'can_purchase': eligibility['eligible'] and not already_enrolled,
            'reviews': reviews,
            'related_courses': related_courses,
            'course_slides': product.course_id.slide_ids[:3] if product.course_id else [],  # Preview slides
        }
        
        return request.render("ams_membership_core.course_detail", values)

    @http.route(['/shop/course/<model("product.template"):product>/enroll'], type='http', auth="user", website=True)
    def course_enroll_direct(self, product, **kwargs):
        """Direct enrollment in course (for free courses or members)"""
        
        if product.product_class != 'courses':
            return request.redirect('/shop/courses')
        
        current_user = request.env.user
        
        # Check eligibility
        eligibility = product.check_course_enrollment_eligibility(current_user.partner_id)
        if not eligibility['eligible']:
            return request.redirect(f'/shop/course/{product.id}?error=not_eligible')
        
        # Check if free for members or completely free
        price = product.get_course_price(current_user.partner_id)
        if price > 0:
            # Redirect to purchase
            return request.redirect(f'/shop/product/{product.product_variant_ids[0].id}')
        
        # Direct enrollment for free courses
        try:
            if product.course_id:
                # Check if already enrolled
                existing = request.env['slide.channel.partner'].search([
                    ('channel_id', '=', product.course_id.id),
                    ('partner_id', '=', current_user.partner_id.id)
                ])
                
                if existing:
                    return request.redirect(f'/slides/{product.course_id.id}')
                
                # Create enrollment
                enrollment = request.env['slide.channel.partner'].sudo().create({
                    'channel_id': product.course_id.id,
                    'partner_id': current_user.partner_id.id,
                    'enrollment_date': fields.Date.today(),
                })
                
                return request.redirect(f'/slides/{product.course_id.id}')
            else:
                return request.redirect(f'/shop/course/{product.id}?error=no_course')
                
        except Exception as e:
            _logger.error(f"Error in direct course enrollment: {str(e)}")
            return request.redirect(f'/shop/course/{product.id}?error=enrollment_failed')

    @http.route(['/shop/courses/category/<string:category>'], type='http', auth="public", website=True)
    def course_category(self, category, **kwargs):
        """Course category page"""
        return self.course_catalog(category=category, **kwargs)

    @http.route(['/shop/courses/search'], type='http', auth="public", website=True)
    def course_search(self, search='', **kwargs):
        """Course search results"""
        return self.course_catalog(search=search, **kwargs)

    # Override WebsiteSale methods for course-specific pricing
    def _get_search_domain(self, search, category, attrib_values, search_in_description=True, search_in_name=True, search_in_attributes=True):
        """Override to handle course search"""
        domain = super()._get_search_domain(search, category, attrib_values, search_in_description, search_in_name, search_in_attributes)
        
        # If we're in course context, add course-specific search
        if request.httprequest.path.startswith('/shop/courses'):
            if search:
                course_domain = [
                    '|', '|',
                    ('course_id.name', 'ilike', search),
                    ('course_id.description', 'ilike', search),
                    ('course_id.course_category', 'ilike', search)
                ]
                domain = ['|'] + domain + course_domain
        
        return domain

    def _prepare_product_values(self, product, category, search, **kwargs):
        """Override to add course-specific data"""
        values = super()._prepare_product_values(product, category, search, **kwargs)
        
        if product.product_class == 'courses':
            current_user = request.env.user
            is_member = current_user.partner_id.is_member if current_user != request.env.ref('base.public_user') else False
            
            values.update({
                'course_info': product._get_course_info_for_website(),
                'is_member': is_member,
                'member_price': product.member_price,
                'display_price': product.get_course_price(current_user.partner_id),
                'show_member_discount': is_member and product.member_price > 0 and product.member_price < product.list_price,
            })
        
        return values


class CoursePortalController(CustomerPortal):
    """Portal controller for course management"""

    def _prepare_home_portal_values(self, counters):
        """Add course counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'course_count' in counters:
            partner = request.env.user.partner_id
            enrollments = request.env['slide.channel.partner'].search([
                ('partner_id', '=', partner.id),
                ('channel_id.is_ams_course', '=', True)
            ])
            values['course_count'] = len(enrollments)
        
        return values

    @http.route(['/my/courses', '/my/courses/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_courses(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """List enrolled courses in portal"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        # Get course enrollments
        domain = [
            ('partner_id', '=', partner.id),
            ('channel_id.is_ams_course', '=', True)
        ]
        
        searchbar_sortings = {
            'date': {'label': _('Enrollment Date'), 'order': 'enrollment_date desc'},
            'name': {'label': _('Course Name'), 'order': 'channel_id.name'},
            'progress': {'label': _('Progress'), 'order': 'completion desc'},
        }
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'in_progress': {'label': _('In Progress'), 'domain': [('completed', '=', False), ('completion', '>', 0)]},
            'completed': {'label': _('Completed'), 'domain': [('completed', '=', True)]},
            'not_started': {'label': _('Not Started'), 'domain': [('completion', '=', 0)]},
        }
        
        # Apply filters
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        if date_begin and date_end:
            domain += [('enrollment_date', '>', date_begin), ('enrollment_date', '<=', date_end)]
        
        # Get enrollments
        CoursePartner = request.env['slide.channel.partner']
        course_count = CoursePartner.search_count(domain)
        
        # Pagination
        pager = request.website.pager(
            url="/my/courses",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=course_count,
            page=page,
            step=self._items_per_page
        )
        
        courses = CoursePartner.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        
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

    @http.route(['/my/course/<int:enrollment_id>'], type='http', auth="user", website=True)
    def portal_course_detail(self, enrollment_id, **kw):
        """Course enrollment detail in portal"""
        try:
            enrollment = request.env['slide.channel.partner'].browse(enrollment_id)
            
            # Security check
            if enrollment.partner_id != request.env.user.partner_id:
                return request.redirect('/my/courses')
            
            values = {
                'page_name': 'course',
                'enrollment': enrollment,
                'course': enrollment.channel_id,
                'progress_summary': enrollment.get_progress_summary(),
                'can_access': enrollment.check_access_validity(),
            }
            
            return request.render("ams_membership_core.portal_course_detail", values)
            
        except Exception:
            return request.redirect('/my/courses')

    @http.route(['/my/course/<int:enrollment_id>/certificate'], type='http', auth="user", website=True)
    def portal_course_certificate(self, enrollment_id, **kw):
        """Download course certificate"""
        try:
            enrollment = request.env['slide.channel.partner'].browse(enrollment_id)
            
            # Security check
            if enrollment.partner_id != request.env.user.partner_id:
                return request.redirect('/my/courses')
            
            if not enrollment.ams_certificate_issued:
                return request.redirect(f'/my/course/{enrollment_id}?error=no_certificate')
            
            # Generate certificate PDF or redirect to certificate URL
            if enrollment.ams_certificate_url:
                return request.redirect(enrollment.ams_certificate_url)
            else:
                # Generate certificate on the fly
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'ams_membership_core.course_certificate_report',
                    'report_type': 'qweb-pdf',
                    'data': {'enrollment_id': enrollment_id},
                    'context': {'active_id': enrollment_id},
                }
                
        except Exception:
            return request.redirect('/my/courses')

    @http.route(['/my/course/<int:enrollment_id>/access'], type='http', auth="user", website=True)
    def portal_course_access(self, enrollment_id, **kw):
        """Access course content from portal"""
        try:
            enrollment = request.env['slide.channel.partner'].browse(enrollment_id)
            
            # Security check
            if enrollment.partner_id != request.env.user.partner_id:
                return request.redirect('/my/courses')
            
            # Check access validity
            if not enrollment.check_access_validity():
                return request.redirect(f'/my/course/{enrollment_id}?error=access_expired')
            
            # Update last access
            enrollment.sudo().write({
                'last_activity_date': fields.Datetime.now()
            })
            
            # Redirect to course
            return request.redirect(f'/slides/{enrollment.channel_id.id}')
            
        except Exception:
            return request.redirect('/my/courses')


class CourseApiController(http.Controller):
    """API endpoints for course functionality"""

    @http.route(['/course/api/pricing'], type='json', auth="public", methods=['POST'])
    def get_course_pricing(self, product_id):
        """Get course pricing for current user"""
        try:
            product = request.env['product.template'].browse(product_id)
            current_user = request.env.user
            
            if product.product_class != 'courses':
                return {'error': 'Not a course product'}
            
            is_member = current_user.partner_id.is_member if current_user != request.env.ref('base.public_user') else False
            price = product.get_course_price(current_user.partner_id)
            eligibility = product.check_course_enrollment_eligibility(current_user.partner_id)
            
            return {
                'price': price,
                'member_price': product.member_price,
                'non_member_price': product.list_price,
                'is_member': is_member,
                'eligible': eligibility['eligible'],
                'issues': eligibility['issues'],
            }
            
        except Exception as e:
            return {'error': str(e)}

    @http.route(['/course/api/enrollment_check'], type='json', auth="user", methods=['POST'])
    def check_enrollment_status(self, course_id):
        """Check if user is enrolled in course"""
        try:
            partner = request.env.user.partner_id
            enrollment = request.env['slide.channel.partner'].search([
                ('channel_id', '=', course_id),
                ('partner_id', '=', partner.id)
            ], limit=1)
            
            return {
                'enrolled': bool(enrollment),
                'enrollment_id': enrollment.id if enrollment else None,
                'completed': enrollment.completed if enrollment else False,
                'progress': enrollment.completion if enrollment else 0,
            }
            
        except Exception as e:
            return {'error': str(e)}