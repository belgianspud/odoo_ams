# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import UserError, AccessError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import json

try:
    from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
except ImportError:
    # Fallback for different Odoo versions
    from odoo.addons.website.controllers.main import Website as CustomerPortal
    from odoo.addons.website.controllers.main import pager as portal_pager

class AMSPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        """Add subscription count to portal home - compatible with Community"""
        try:
            values = super()._prepare_portal_layout_values()
        except:
            values = {}
        
        partner = request.env.user.partner_id
        
        # Add subscription count
        subscription_count = request.env['ams.subscription'].search_count([
            '|',
            ('partner_id', '=', partner.id),
            ('account_id', '=', partner.id),
            ('state', '!=', 'terminated')
        ])
        values['subscription_count'] = subscription_count
        
        return values

    def _prepare_home_portal_values(self, counters):
        """Add subscription count to portal home counters"""
        try:
            values = super()._prepare_home_portal_values(counters)
        except:
            values = {}
        
        partner = request.env.user.partner_id
        if 'subscription_count' in counters:
            subscription_count = request.env['ams.subscription'].search_count([
                '|',
                ('partner_id', '=', partner.id),
                ('account_id', '=', partner.id),
                ('state', '!=', 'terminated')
            ])
            values['subscription_count'] = subscription_count
        
        return values

    @http.route(['/my/subscriptions', '/my/subscriptions/page/<int:page>'], type='http', auth='user', website=True)
    def my_subscriptions(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """Enhanced subscriptions page with filtering and management"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        
        domain = [
            '|',
            ('partner_id', '=', partner.id),
            ('account_id', '=', partner.id)
        ]
        
        # Searchbar filters
        searchbar_filters = {
            'all': {'label': 'All', 'domain': []},
            'active': {'label': 'Active', 'domain': [('state', '=', 'active')]},
            'paused': {'label': 'Paused', 'domain': [('state', '=', 'paused')]},
            'grace': {'label': 'Grace Period', 'domain': [('state', '=', 'grace')]},
            'suspended': {'label': 'Suspended', 'domain': [('state', '=', 'suspended')]},
        }
        
        # Searchbar sorting
        searchbar_sortings = {
            'date': {'label': 'Start Date', 'order': 'start_date desc'},
            'name': {'label': 'Name', 'order': 'name'},
            'state': {'label': 'Status', 'order': 'state'},
        }
        
        # Apply filters
        if filterby and filterby in searchbar_filters:
            domain += searchbar_filters[filterby]['domain']
        else:
            filterby = 'all'
        
        # Apply sorting
        if sortby and sortby in searchbar_sortings:
            order = searchbar_sortings[sortby]['order']
        else:
            sortby = 'date'
            order = 'start_date desc'
        
        # Count subscriptions
        subscription_count = request.env['ams.subscription'].search_count(domain)
        
        # Items per page
        items_per_page = 10
        
        # Prepare pager
        pager = portal_pager(
            url="/my/subscriptions",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=subscription_count,
            page=page,
            step=items_per_page
        )
        
        # Get subscriptions
        subscriptions = request.env['ams.subscription'].search(
            domain, order=order, limit=items_per_page, offset=pager['offset']
        )
        
        # Handle flash messages
        message = request.session.pop('message', None)
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'subscriptions': subscriptions,
            'page_name': 'subscription',
            'default_url': '/my/subscriptions',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
            'message': message,
        })
        
        return request.render('ams_subscriptions.portal_my_subscriptions', values)

    @http.route(['/my/subscription/<int:subscription_id>'], type='http', auth='user', website=True)
    def my_subscription_detail(self, subscription_id, **kw):
        """Detailed view of a single subscription with management options"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.render('website.404')
        
        # Get available tiers for upgrades/downgrades
        available_tiers = request.env['ams.subscription.tier'].search([
            ('subscription_type', '=', subscription.subscription_type),
            ('id', '!=', subscription.tier_id.id)
        ])
        
        # Get modification history
        modifications = subscription.modification_ids.sorted('modification_date', reverse=True)
        
        # Get payment history
        payment_history = request.env['ams.payment.history'].search([
            ('subscription_id', '=', subscription.id)
        ], order='payment_date desc', limit=10)
        
        # Handle flash messages
        message = request.session.pop('message', None)
        
        values = {
            'subscription': subscription,
            'available_tiers': available_tiers,
            'modifications': modifications,
            'payment_history': payment_history,
            'page_name': 'subscription_detail',
            'message': message,
        }
        
        return request.render('ams_subscriptions.portal_subscription_detail', values)

    @http.route(['/my/subscription/<int:subscription_id>/pause'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def pause_subscription(self, subscription_id, **post):
        """Pause a subscription"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.redirect('/my/subscriptions')
        
        try:
            subscription.sudo().action_pause_subscription()
            request.session['message'] = {'type': 'success', 'text': 'Subscription paused successfully!'}
        except UserError as e:
            request.session['message'] = {'type': 'danger', 'text': str(e)}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'An error occurred: {str(e)}'}
        
        return request.redirect(f'/my/subscription/{subscription_id}')

    @http.route(['/my/subscription/<int:subscription_id>/resume'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def resume_subscription(self, subscription_id, **post):
        """Resume a paused subscription"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.redirect('/my/subscriptions')
        
        try:
            subscription.sudo().action_resume_subscription()
            request.session['message'] = {'type': 'success', 'text': 'Subscription resumed successfully!'}
        except UserError as e:
            request.session['message'] = {'type': 'danger', 'text': str(e)}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'An error occurred: {str(e)}'}
        
        return request.redirect(f'/my/subscription/{subscription_id}')

    @http.route(['/my/subscription/<int:subscription_id>/modify'], type='http', auth='user', website=True)
    def subscription_modify_form(self, subscription_id, **kw):
        """Form to modify subscription (upgrade/downgrade)"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.render('website.404')
        
        if not subscription.allow_modifications:
            request.session['message'] = {'type': 'warning', 'text': 'This subscription cannot be modified.'}
            return request.redirect(f'/my/subscription/{subscription_id}')
        
        # Get available tiers
        available_tiers = request.env['ams.subscription.tier'].search([
            ('subscription_type', '=', subscription.subscription_type),
            ('id', '!=', subscription.tier_id.id)
        ])
        
        # Handle flash messages
        message = request.session.pop('message', None)
        
        values = {
            'subscription': subscription,
            'available_tiers': available_tiers,
            'page_name': 'subscription_modify',
            'message': message,
        }
        
        return request.render('ams_subscriptions.portal_subscription_modify', values)

    @http.route(['/my/subscription/<int:subscription_id>/modify'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def subscription_modify_submit(self, subscription_id, **post):
        """Process subscription modification"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.redirect('/my/subscriptions')
        
        new_tier_id = int(post.get('new_tier_id', 0))
        reason = post.get('reason', '')
        
        if not new_tier_id:
            request.session['message'] = {'type': 'danger', 'text': 'Please select a new tier.'}
            return request.redirect(f'/my/subscription/{subscription_id}/modify')
        
        try:
            # Create and execute modification wizard
            wizard = request.env['ams.subscription.modification.wizard'].sudo().create({
                'subscription_id': subscription_id,
                'current_tier_id': subscription.tier_id.id,
                'new_tier_id': new_tier_id,
                'reason': reason or 'Customer requested modification via portal',
                'modification_type': 'upgrade' if new_tier_id > subscription.tier_id.id else 'downgrade',
            })
            
            result = wizard.action_confirm_modification()
            
            # Extract message from wizard result
            if isinstance(result, dict) and result.get('params', {}).get('message'):
                request.session['message'] = {
                    'type': 'success', 
                    'text': result['params']['message']
                }
            else:
                request.session['message'] = {
                    'type': 'success', 
                    'text': 'Subscription modification completed successfully!'
                }
                
        except UserError as e:
            request.session['message'] = {'type': 'danger', 'text': str(e)}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'An error occurred: {str(e)}'}
        
        return request.redirect(f'/my/subscription/{subscription_id}')

    @http.route(['/my/subscription/<int:subscription_id>/cancel'], type='http', auth='user', website=True)
    def subscription_cancel_form(self, subscription_id, **kw):
        """Form to cancel subscription"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.render('website.404')
        
        cancellation_reasons = [
            ('too_expensive', 'Too Expensive'),
            ('not_using', 'Not Using Enough'),
            ('missing_features', 'Missing Features'),
            ('poor_service', 'Poor Customer Service'),
            ('competitor', 'Found Better Alternative'),
            ('business_closed', 'Business Closed/Changed'),
            ('technical_issues', 'Technical Issues'),
            ('other', 'Other'),
        ]
        
        # Handle flash messages
        message = request.session.pop('message', None)
        
        values = {
            'subscription': subscription,
            'cancellation_reasons': cancellation_reasons,
            'page_name': 'subscription_cancel',
            'message': message,
        }
        
        return request.render('ams_subscriptions.portal_subscription_cancel', values)

    @http.route(['/my/subscription/<int:subscription_id>/cancel'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def subscription_cancel_submit(self, subscription_id, **post):
        """Process subscription cancellation"""
        subscription = request.env['ams.subscription'].browse(subscription_id)
        partner = request.env.user.partner_id
        
        # Security check
        if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
            return request.redirect('/my/subscriptions')
        
        cancellation_reason = post.get('cancellation_reason')
        detailed_feedback = post.get('detailed_feedback', '')
        effective_date = post.get('effective_date', 'period_end')
        request_refund = bool(post.get('request_refund'))
        
        if not cancellation_reason:
            request.session['message'] = {'type': 'danger', 'text': 'Please select a cancellation reason.'}
            return request.redirect(f'/my/subscription/{subscription_id}/cancel')
        
        try:
            # Create and execute cancellation wizard
            wizard = request.env['ams.subscription.cancellation.wizard'].sudo().create({
                'subscription_id': subscription_id,
                'cancellation_reason': cancellation_reason,
                'detailed_feedback': detailed_feedback,
                'effective_date': effective_date,
                'request_refund': request_refund,
                'confirm_understanding': True,
                'confirm_no_reversal': True,
            })
            
            result = wizard.action_confirm_cancellation()
            
            # Extract message from wizard result
            if isinstance(result, dict) and result.get('params', {}).get('message'):
                request.session['message'] = {
                    'type': 'success', 
                    'text': result['params']['message']
                }
            else:
                request.session['message'] = {
                    'type': 'success', 
                    'text': 'Cancellation request submitted successfully.'
                }
                
        except UserError as e:
            request.session['message'] = {'type': 'danger', 'text': str(e)}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'An error occurred: {str(e)}'}
        
        return request.redirect('/my/subscriptions')

    @http.route(['/my/enterprise-seats'], type='http', auth='user', website=True)
    def my_enterprise_seats(self, **kw):
        """Manage enterprise seat assignments"""
        partner = request.env.user.partner_id
        
        # Get enterprise subscriptions where user is the account holder
        enterprise_subscriptions = request.env['ams.subscription'].search([
            ('account_id', '=', partner.id),
            ('subscription_type', '=', 'enterprise'),
            ('state', 'in', ['active', 'grace'])
        ])
        
        if not enterprise_subscriptions:
            return request.render('ams_subscriptions.portal_no_enterprise_subscriptions')
        
        # Get seat assignments for these subscriptions
        seat_assignments = request.env['ams.subscription.seat'].search([
            ('subscription_id', 'in', enterprise_subscriptions.ids)
        ])
        
        # Get available contacts (employees under this company)
        available_contacts = request.env['res.partner'].search([
            ('parent_id', '=', partner.id),
            ('is_company', '=', False)
        ])
        
        # Handle flash messages
        message = request.session.pop('message', None)
        
        values = {
            'enterprise_subscriptions': enterprise_subscriptions,
            'seat_assignments': seat_assignments,
            'available_contacts': available_contacts,
            'page_name': 'enterprise_seats',
            'message': message,
        }
        
        return request.render('ams_subscriptions.portal_enterprise_seats', values)

    @http.route(['/my/enterprise-seats/assign'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def assign_enterprise_seat(self, **post):
        """Assign an enterprise seat to a contact"""
        partner = request.env.user.partner_id
        subscription_id = int(post.get('subscription_id', 0))
        contact_id = int(post.get('contact_id', 0))
        
        if not subscription_id or not contact_id:
            request.session['message'] = {'type': 'danger', 'text': 'Invalid subscription or contact selected.'}
            return request.redirect('/my/enterprise-seats')
        
        subscription = request.env['ams.subscription'].browse(subscription_id)
        
        # Security check
        if subscription.account_id != partner:
            request.session['message'] = {'type': 'danger', 'text': 'Access denied.'}
            return request.redirect('/my/enterprise-seats')
        
        # Check if seats are available
        active_seats = len(subscription.seat_ids.filtered('active'))
        if active_seats >= subscription.total_seats:
            request.session['message'] = {'type': 'danger', 'text': 'No available seats in this subscription.'}
            return request.redirect('/my/enterprise-seats')
        
        # Check if contact is already assigned
        existing_seat = request.env['ams.subscription.seat'].search([
            ('subscription_id', '=', subscription_id),
            ('contact_id', '=', contact_id),
            ('active', '=', True)
        ])
        
        if existing_seat:
            request.session['message'] = {'type': 'warning', 'text': 'This contact is already assigned to this subscription.'}
            return request.redirect('/my/enterprise-seats')
        
        try:
            # Create seat assignment
            request.env['ams.subscription.seat'].sudo().create({
                'subscription_id': subscription_id,
                'contact_id': contact_id,
                'assigned_date': fields.Date.today(),
                'active': True,
            })
            
            request.session['message'] = {'type': 'success', 'text': 'Seat assigned successfully!'}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'Error assigning seat: {str(e)}'}
        
        return request.redirect('/my/enterprise-seats')

    @http.route(['/my/enterprise-seats/<int:seat_id>/unassign'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def unassign_enterprise_seat(self, seat_id, **post):
        """Unassign an enterprise seat"""
        partner = request.env.user.partner_id
        seat = request.env['ams.subscription.seat'].browse(seat_id)
        
        # Security check
        if not seat.exists() or seat.subscription_id.account_id != partner:
            request.session['message'] = {'type': 'danger', 'text': 'Access denied.'}
            return request.redirect('/my/enterprise-seats')
        
        try:
            seat.sudo().write({'active': False})
            request.session['message'] = {'type': 'success', 'text': 'Seat unassigned successfully!'}
        except Exception as e:
            request.session['message'] = {'type': 'danger', 'text': f'Error unassigning seat: {str(e)}'}
        
        return request.redirect('/my/enterprise-seats')

    @http.route(['/my/subscription/calculate-proration'], type='json', auth='user')
    def calculate_proration(self, subscription_id, new_tier_id):
        """AJAX endpoint to calculate proration for subscription changes"""
        try:
            subscription = request.env['ams.subscription'].browse(subscription_id)
            new_tier = request.env['ams.subscription.tier'].browse(new_tier_id)
            partner = request.env.user.partner_id
            
            # Security check
            if not subscription.exists() or (subscription.partner_id != partner and subscription.account_id != partner):
                return {'error': 'Unauthorized'}
            
            if not new_tier.exists():
                return {'error': 'Invalid tier selected'}
            
            # Determine modification type
            modification_type = 'upgrade' if new_tier_id > subscription.tier_id.id else 'downgrade'
            
            proration_amount = subscription._calculate_proration(
                subscription.tier_id, new_tier, modification_type
            )
            
            return {
                'proration_amount': proration_amount,
                'formatted_amount': f"${abs(proration_amount):.2f}",
                'is_charge': proration_amount > 0,
                'is_credit': proration_amount < 0,
            }
        except Exception as e:
            return {'error': str(e)}