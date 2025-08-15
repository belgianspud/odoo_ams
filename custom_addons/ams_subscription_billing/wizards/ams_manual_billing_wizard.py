# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSManualBillingWizard(models.TransientModel):
    """Simple wizard for manual billing of subscriptions"""
    _name = 'ams.manual.billing.wizard'
    _description = 'AMS Manual Billing Wizard'

    # Basic Configuration
    billing_date = fields.Date(
        string='Billing Date',
        required=True,
        default=fields.Date.today,
        help='Date to use for billing (invoice date)'
    )
    
    subscription_ids = fields.Many2many(
        'ams.subscription',
        string='Subscriptions to Bill',
        domain=[('state', '=', 'active'), ('enable_auto_billing', '=', True)],
        help='Select subscriptions to bill manually'
    )
    
    # Processing Options
    force_billing = fields.Boolean(
        string='Force Billing',
        default=False,
        help='Bill even if not due according to schedule'
    )
    
    auto_send_invoices = fields.Boolean(
        string='Auto Send Invoices',
        default=True,
        help='Automatically send generated invoices to customers'
    )
    
    # Processing Results (populated after execution)
    result_message = fields.Html(
        string='Processing Results',
        readonly=True
    )
    
    # Statistics
    selected_count = fields.Integer(
        string='Selected Subscriptions',
        compute='_compute_statistics'
    )
    
    eligible_count = fields.Integer(
        string='Eligible for Billing',
        compute='_compute_statistics'
    )
    
    @api.depends('subscription_ids', 'billing_date', 'force_billing')
    def _compute_statistics(self):
        """Compute billing statistics"""
        for wizard in self:
            wizard.selected_count = len(wizard.subscription_ids)
            
            if wizard.subscription_ids and wizard.billing_date:
                eligible = 0
                for subscription in wizard.subscription_ids:
                    if wizard._is_eligible_for_billing(subscription):
                        eligible += 1
                wizard.eligible_count = eligible
            else:
                wizard.eligible_count = 0
    
    def _is_eligible_for_billing(self, subscription):
        """Check if subscription is eligible for billing"""
        # Always eligible if forcing
        if self.force_billing:
            return True
        
        # Check if billing schedule is due
        if subscription.billing_schedule_ids:
            for schedule in subscription.billing_schedule_ids.filtered(lambda s: s.state == 'active'):
                if schedule.is_due_for_billing(self.billing_date):
                    return True
        
        # Check if next billing date is due
        if subscription.next_billing_date and subscription.next_billing_date <= self.billing_date:
            return True
        
        return False
    
    @api.onchange('subscription_ids', 'billing_date')
    def _onchange_billing_selection(self):
        """Update statistics when selection changes"""
        self._compute_statistics()
        
        # Show warning if no subscriptions are eligible
        if self.subscription_ids and self.eligible_count == 0:
            return {
                'warning': {
                    'title': _('No Eligible Subscriptions'),
                    'message': _('None of the selected subscriptions are due for billing on %s. Enable "Force Billing" to bill anyway.') % self.billing_date
                }
            }
    
    def action_process_billing(self):
        """Process manual billing for selected subscriptions"""
        if not self.subscription_ids:
            raise UserError(_('Please select at least one subscription to bill'))
        
        if not self.billing_date:
            raise UserError(_('Please specify a billing date'))
        
        # Get eligible subscriptions
        eligible_subscriptions = self.subscription_ids.filtered(
            lambda s: self._is_eligible_for_billing(s)
        )
        
        if not eligible_subscriptions and not self.force_billing:
            raise UserError(_('No subscriptions are eligible for billing on %s') % self.billing_date)
        
        # Use force_billing logic if needed
        subscriptions_to_bill = eligible_subscriptions if not self.force_billing else self.subscription_ids
        
        # Process billing
        results = self._process_subscriptions(subscriptions_to_bill)
        
        # Update wizard with results
        self.result_message = self._format_results(results)
        
        # Return action to show results
        return {
            'name': _('Manual Billing Results'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.manual.billing.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }
    
    def _process_subscriptions(self, subscriptions):
        """Process billing for subscriptions"""
        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'invoices_created': [],
            'total_amount': 0.0,
        }
        
        for subscription in subscriptions:
            try:
                # Get or create billing schedule
                schedule = subscription._get_or_create_billing_schedule()
                
                if not schedule:
                    results['skipped'].append({
                        'subscription': subscription,
                        'reason': 'No billing schedule available'
                    })
                    continue
                
                # Process billing
                billing_result = schedule.process_billing(self.billing_date)
                
                if billing_result.get('success'):
                    results['successful'].append(subscription)
                    
                    # Track created invoice
                    if billing_result.get('invoice'):
                        invoice = billing_result['invoice']
                        results['invoices_created'].append(invoice)
                        results['total_amount'] += invoice.amount_total
                        
                        # Send invoice if configured
                        if self.auto_send_invoices:
                            try:
                                invoice.action_invoice_sent()
                                _logger.info(f'Manual billing: Invoice {invoice.name} sent to {invoice.partner_id.name}')
                            except Exception as e:
                                _logger.warning(f'Manual billing: Failed to send invoice {invoice.name}: {str(e)}')
                else:
                    results['failed'].append({
                        'subscription': subscription,
                        'error': billing_result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'subscription': subscription,
                    'error': str(e)
                })
                _logger.error(f'Manual billing error for subscription {subscription.name}: {str(e)}')
        
        return results
    
    def _format_results(self, results):
        """Format results for display"""
        html = "<div class='container-fluid'>"
        
        # Summary
        html += f"<div class='alert alert-info'>"
        html += f"<h4><i class='fa fa-info-circle'></i> Billing Summary</h4>"
        html += f"<p><strong>Billing Date:</strong> {self.billing_date}</p>"
        html += f"<p><strong>Successful:</strong> {len(results['successful'])}</p>"
        html += f"<p><strong>Failed:</strong> {len(results['failed'])}</p>"
        html += f"<p><strong>Skipped:</strong> {len(results['skipped'])}</p>"
        html += f"<p><strong>Invoices Created:</strong> {len(results['invoices_created'])}</p>"
        html += f"<p><strong>Total Amount:</strong> ${results['total_amount']:,.2f}</p>"
        html += f"</div>"
        
        # Successful billings
        if results['successful']:
            html += "<div class='alert alert-success'>"
            html += f"<h5><i class='fa fa-check-circle'></i> Successfully Billed ({len(results['successful'])})</h5>"
            html += "<ul>"
            for subscription in results['successful']:
                html += f"<li>{subscription.name} - {subscription.partner_id.name}</li>"
            html += "</ul>"
            html += "</div>"
        
        # Failed billings
        if results['failed']:
            html += "<div class='alert alert-danger'>"
            html += f"<h5><i class='fa fa-exclamation-circle'></i> Failed Billings ({len(results['failed'])})</h5>"
            html += "<ul>"
            for failed in results['failed']:
                subscription = failed['subscription']
                error = failed['error']
                html += f"<li>{subscription.name} - {subscription.partner_id.name}: {error}</li>"
            html += "</ul>"
            html += "</div>"
        
        # Skipped billings
        if results['skipped']:
            html += "<div class='alert alert-warning'>"
            html += f"<h5><i class='fa fa-exclamation-triangle'></i> Skipped ({len(results['skipped'])})</h5>"
            html += "<ul>"
            for skipped in results['skipped']:
                subscription = skipped['subscription']
                reason = skipped['reason']
                html += f"<li>{subscription.name} - {subscription.partner_id.name}: {reason}</li>"
            html += "</ul>"
            html += "</div>"
        
        # Created invoices
        if results['invoices_created']:
            html += "<div class='alert alert-info'>"
            html += f"<h5><i class='fa fa-file-text-o'></i> Created Invoices ({len(results['invoices_created'])})</h5>"
            html += "<ul>"
            for invoice in results['invoices_created']:
                html += f"<li><a href='/web#id={invoice.id}&view_type=form&model=account.move' target='_blank'>{invoice.name}</a> - {invoice.partner_id.name} - ${invoice.amount_total:,.2f}</li>"
            html += "</ul>"
            html += "</div>"
        
        html += "</div>"
        return html
    
    def action_view_created_invoices(self):
        """View invoices created during this billing run"""
        # This would need to track created invoices - simplified for now
        return {
            'name': _('Created Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('subscription_id', 'in', self.subscription_ids.ids),
                ('invoice_date', '=', self.billing_date),
                ('billing_type', '=', 'manual')
            ],
            'context': {'search_default_group_by_partner': 1}
        }
    
    def action_close(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        defaults = super().default_get(fields_list)
        
        # If called from subscription view, pre-select those subscriptions
        if self.env.context.get('active_model') == 'ams.subscription':
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                # Filter to only active subscriptions with billing enabled
                eligible_subscriptions = self.env['ams.subscription'].browse(active_ids).filtered(
                    lambda s: s.state == 'active' and s.enable_auto_billing
                )
                defaults['subscription_ids'] = [(6, 0, eligible_subscriptions.ids)]
        
        return defaults