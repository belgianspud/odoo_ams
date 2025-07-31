from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.tools import consteq
import logging

_logger = logging.getLogger(__name__)

class AMSMemberPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        """Add AMS-specific portal counters"""
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        
        if 'subscription_count' in counters:
            subscription_count = request.env['ams.member.subscription'].search_count([
                ('partner_id', '=', partner.id)
            ])
            values['subscription_count'] = subscription_count
        
        if 'benefit_count' in counters:
            # Count available benefits
            current_subscription = partner.current_subscription_id
            if current_subscription:
                benefit_count = len(current_subscription.membership_type_id.benefit_ids)
                values['benefit_count'] = benefit_count
            else:
                values['benefit_count'] = 0
        
        return values

    @http.route(['/my/membership'], type='http', auth="user", website=True)
    def portal_my_membership(self, **kw):
        """Member portal dashboard"""
        partner = request.env.user.partner_id
        
        # Get current subscription
        current_subscription = partner.current_subscription_id
        
        # Get subscription history
        subscription_history = request.env['ams.member.subscription'].search([
            ('partner_id', '=', partner.id)
        ], order='start_date desc')
        
        # Get available benefits
        benefits = []
        if current_subscription:
            benefits = current_subscription.membership_type_id.benefit_ids.filtered('active')
        
        # Get recent invoices
        recent_invoices = request.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted')
        ], order='invoice_date desc', limit=5)
        
        # Get payment methods
        payment_tokens = request.env['payment.token'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ])
        
        values = {
            'partner': partner,
            'current_subscription': current_subscription,
            'subscription_history': subscription_history,
            'benefits': benefits,
            'recent_invoices': recent_invoices,
            'payment_tokens': payment_tokens,
            'page_name': 'membership'
        }
        
        return request.render("ams_subscriptions.portal_my_membership", values)

    @http.route(['/my/membership/renew'], type='http', auth="user", website=True)
    def portal_membership_renew(self, **kw):
        """Member portal renewal page"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        if not current_subscription:
            return request.redirect('/my/membership?error=no_subscription')
            
        if current_subscription.state not in ['active', 'pending_renewal', 'expired']:
            return request.redirect('/my/membership?error=cannot_renew')
        
        # Get renewal options
        membership_types = request.env['ams.membership.type'].search([
            ('active', '=', True)
        ])
        
        # Filter by chapter if applicable
        if current_subscription.chapter_id:
            membership_types = membership_types.filtered(
                lambda mt: not mt.chapter_based or 
                current_subscription.chapter_id in mt.allowed_chapter_ids
            )
        
        values = {
            'partner': partner,
            'current_subscription': current_subscription,
            'membership_types': membership_types,
            'page_name': 'renewal'
        }
        
        return request.render("ams_subscriptions.portal_membership_renew", values)

    @http.route(['/my/membership/renew/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_membership_renew_submit(self, **post):
        """Process membership renewal"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        if not current_subscription:
            return request.redirect('/my/membership?error=no_subscription')
        
        try:
            membership_type_id = int(post.get('membership_type_id'))
            auto_renew = post.get('auto_renew') == 'on'
            payment_token_id = int(post.get('payment_token_id', 0)) or False
            
            # Create renewal subscription
            renewal_vals = {
                'partner_id': partner.id,
                'membership_type_id': membership_type_id,
                'chapter_id': current_subscription.chapter_id.id if current_subscription.chapter_id else False,
                'start_date': current_subscription.end_date + fields.timedelta(days=1) if current_subscription.end_date else fields.Date.today(),
                'parent_subscription_id': current_subscription.id,
                'auto_renew': auto_renew,
                'payment_token_id': payment_token_id,
            }
            
            renewal = request.env['ams.member.subscription'].sudo().create(renewal_vals)
            
            # Auto-approve if membership type doesn't require approval
            if not renewal.membership_type_id.requires_approval:
                renewal.action_approve()
            
            return request.redirect(f'/my/membership/confirmation/{renewal.id}')
            
        except Exception as e:
            _logger.error(f"Membership renewal failed: {e}")
            return request.redirect('/my/membership/renew?error=renewal_failed')

    @http.route(['/my/membership/confirmation/<int:subscription_id>'], type='http', auth="user", website=True)
    def portal_membership_confirmation(self, subscription_id, **kw):
        """Membership renewal confirmation page"""
        subscription = request.env['ams.member.subscription'].browse(subscription_id)
        
        # Security check
        if subscription.partner_id != request.env.user.partner_id:
            raise AccessError(_("Access denied"))
        
        values = {
            'subscription': subscription,
            'page_name': 'confirmation'
        }
        
        return request.render("ams_subscriptions.portal_membership_confirmation", values)

    @http.route(['/my/membership/upgrade'], type='http', auth="user", website=True)
    def portal_membership_upgrade(self, **kw):
        """Member portal upgrade page"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        if not current_subscription or current_subscription.state != 'active':
            return request.redirect('/my/membership?error=no_active_subscription')
        
        # Get available upgrade options
        current_price = current_subscription.membership_type_id.price
        upgrade_types = request.env['ams.membership.type'].search([
            ('active', '=', True),
            ('price', '>', current_price),
            ('id', '!=', current_subscription.membership_type_id.id)
        ])
        
        # Calculate prorated costs
        upgrade_options = []
        for upgrade_type in upgrade_types:
            prorated_cost = current_subscription.calculate_proration(
                upgrade_type.price - current_price
            )
            
            upgrade_options.append({
                'membership_type': upgrade_type,
                'prorated_cost': prorated_cost,
                'benefits': upgrade_type.benefit_ids.filtered('active')
            })
        
        values = {
            'partner': partner,
            'current_subscription': current_subscription,
            'upgrade_options': upgrade_options,
            'page_name': 'upgrade'
        }
        
        return request.render("ams_subscriptions.portal_membership_upgrade", values)

    @http.route(['/my/membership/upgrade/submit'], type='http', auth="user", website=True, methods=['POST'])
    def portal_membership_upgrade_submit(self, **post):
        """Process membership upgrade"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        try:
            new_membership_type_id = int(post.get('membership_type_id'))
            effective_date = post.get('effective_date', 'immediate')
            
            new_membership_type = request.env['ams.membership.type'].browse(new_membership_type_id)
            
            if effective_date == 'immediate':
                # Create backup of current subscription
                backup = request.env['ams.subscription.backup'].sudo().create_backup(
                    current_subscription,
                    backup_type='upgrade',
                    reason=f'Upgrade to {new_membership_type.name}'
                )
                
                # Update current subscription
                current_subscription.sudo().write({
                    'membership_type_id': new_membership_type_id,
                    'unit_price': new_membership_type.price,
                })
                
                # Calculate and create proration invoice
                prorated_amount = current_subscription.calculate_proration(
                    new_membership_type.price - current_subscription.membership_type_id.price
                )
                
                if prorated_amount > 0:
                    invoice_vals = {
                        'partner_id': partner.id,
                        'move_type': 'out_invoice',
                        'subscription_id': current_subscription.id,
                        'invoice_line_ids': [(0, 0, {
                            'name': f'Membership Upgrade: {current_subscription.membership_type_id.name} → {new_membership_type.name}',
                            'quantity': 1,
                            'price_unit': prorated_amount,
                        })]
                    }
                    
                    invoice = request.env['account.move'].sudo().create(invoice_vals)
                    invoice.action_post()
                
                return request.redirect('/my/membership?success=upgrade_complete')
            
            else:
                # Schedule future upgrade
                scheduled_change_vals = {
                    'subscription_id': current_subscription.id,
                    'target_membership_type_id': new_membership_type_id,
                    'effective_date': fields.Date.from_string(effective_date),
                    'change_type': 'upgrade',
                    'financial_adjustment': new_membership_type.price - current_subscription.membership_type_id.price
                }
                
                request.env['ams.subscription.scheduled.change'].sudo().create(scheduled_change_vals)
                
                return request.redirect('/my/membership?success=upgrade_scheduled')
                
        except Exception as e:
            _logger.error(f"Membership upgrade failed: {e}")
            return request.redirect('/my/membership/upgrade?error=upgrade_failed')

    @http.route(['/my/membership/benefits'], type='http', auth="user", website=True)
    def portal_membership_benefits(self, **kw):
        """Member portal benefits page"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        if not current_subscription:
            return request.redirect('/my/membership?error=no_subscription')
        
        # Get benefits with usage tracking
        benefits = current_subscription.membership_type_id.benefit_ids.filtered('active')
        
        benefit_data = []
        for benefit in benefits:
            usage_count = benefit.get_member_usage_count(partner)
            is_available, message = benefit.is_available_for_member(partner)
            
            benefit_data.append({
                'benefit': benefit,
                'usage_count': usage_count,
                'is_available': is_available,
                'availability_message': message,
                'usage_logs': request.env['ams.benefit.usage'].search([
                    ('benefit_id', '=', benefit.id),
                    ('member_id', '=', partner.id)
                ], order='usage_date desc', limit=5)
            })
        
        values = {
            'partner': partner,
            'current_subscription': current_subscription,
            'benefit_data': benefit_data,
            'page_name': 'benefits'
        }
        
        return request.render("ams_subscriptions.portal_membership_benefits", values)

    @http.route(['/my/membership/benefits/use/<int:benefit_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_use_benefit(self, benefit_id, **post):
        """Record benefit usage from portal"""
        partner = request.env.user.partner_id
        benefit = request.env['ams.subscription.benefit'].browse(benefit_id)
        
        try:
            usage_notes = post.get('usage_notes', '')
            benefit.sudo().record_usage(partner, notes=usage_notes)
            
            return request.redirect('/my/membership/benefits?success=benefit_used')
            
        except Exception as e:
            _logger.error(f"Benefit usage failed: {e}")
            return request.redirect('/my/membership/benefits?error=usage_failed')

    @http.route(['/my/membership/payment-methods'], type='http', auth="user", website=True)
    def portal_payment_methods(self, **kw):
        """Member portal payment methods management"""
        partner = request.env.user.partner_id
        
        payment_tokens = request.env['payment.token'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ])
        
        values = {
            'partner': partner,
            'payment_tokens': payment_tokens,
            'page_name': 'payment_methods'
        }
        
        return request.render("ams_subscriptions.portal_payment_methods", values)

    @http.route(['/my/membership/invoices'], type='http', auth="user", website=True)
    def portal_membership_invoices(self, **kw):
        """Member portal invoices page"""
        partner = request.env.user.partner_id
        
        invoices = request.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted')
        ], order='invoice_date desc')
        
        values = {
            'partner': partner,
            'invoices': invoices,
            'page_name': 'invoices'
        }
        
        return request.render("ams_subscriptions.portal_membership_invoices", values)

    @http.route(['/my/membership/settings'], type='http', auth="user", website=True)
    def portal_membership_settings(self, **kw):
        """Member portal settings page"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        values = {
            'partner': partner,
            'current_subscription': current_subscription,
            'page_name': 'settings'
        }
        
        return request.render("ams_subscriptions.portal_membership_settings", values)

    @http.route(['/my/membership/settings/update'], type='http', auth="user", website=True, methods=['POST'])
    def portal_membership_settings_update(self, **post):
        """Update membership settings from portal"""
        partner = request.env.user.partner_id
        current_subscription = partner.current_subscription_id
        
        try:
            # Update communication preferences
            partner.sudo().write({
                'newsletter_subscription': post.get('newsletter_subscription') == 'on',
                'event_notifications': post.get('event_notifications') == 'on',
                'communication_preference': post.get('communication_preference', 'email')
            })
            
            # Update subscription settings
            if current_subscription:
                current_subscription.sudo().write({
                    'auto_renew': post.get('auto_renew') == 'on',
                    'payment_token_id': int(post.get('payment_token_id', 0)) or False
                })
            
            return request.redirect('/my/membership/settings?success=settings_updated')
            
        except Exception as e:
            _logger.error(f"Settings update failed: {e}")
            return request.redirect('/my/membership/settings?error=update_failed')
