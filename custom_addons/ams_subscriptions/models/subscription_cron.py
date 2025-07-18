# Add the methods needed for the cron jobs to work

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionCron(models.Model):
    _inherit = 'ams.subscription'
    
    @api.model
    def _cron_check_expiries(self):
        """Cron job to check for expired subscriptions and update their status"""
        today = fields.Date.today()
        
        # Find subscriptions that have expired
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('end_date', '!=', False)
        ])
        
        for subscription in expired_subscriptions:
            # Don't expire if there's a pending renewal
            if subscription.renewal_invoice_id and subscription.renewal_invoice_id.state != 'cancel':
                continue
                
            subscription.state = 'expired'
            _logger.info(f"Subscription {subscription.name} has been marked as expired")
        
        _logger.info(f"Processed {len(expired_subscriptions)} expired subscriptions")
    
    @api.model
    def _cron_send_weekly_reminders(self):
        """Cron job to send weekly renewal reminders"""
        today = fields.Date.today()
        
        # Find subscriptions expiring in the next 7, 14, 21, 30 days
        reminder_dates = [
            today + relativedelta(days=7),
            today + relativedelta(days=14),
            today + relativedelta(days=21),
            today + relativedelta(days=30)
        ]
        
        for reminder_date in reminder_dates:
            subscriptions_to_remind = self.search([
                ('state', '=', 'active'),
                ('is_recurring', '=', True),
                ('next_renewal_date', '=', reminder_date),
                ('renewal_reminder_sent', '=', False)
            ])
            
            for subscription in subscriptions_to_remind:
                subscription._send_renewal_reminder()
                _logger.info(f"Renewal reminder sent for subscription {subscription.name}")
        
        _logger.info(f"Weekly renewal reminders processed")
    
    @api.model
    def _cron_monthly_cleanup(self):
        """Cron job for monthly cleanup tasks"""
        today = fields.Date.today()
        
        # Reset renewal reminder flags for subscriptions that were renewed
        renewed_subscriptions = self.search([
            ('renewal_reminder_sent', '=', True),
            ('state', '=', 'active'),
            ('next_renewal_date', '>', today + relativedelta(days=45))  # Renewed for more than 45 days
        ])
        
        renewed_subscriptions.write({'renewal_reminder_sent': False})
        _logger.info(f"Reset renewal reminder flags for {len(renewed_subscriptions)} subscriptions")
        
        # Clean up old draft invoices for cancelled subscriptions
        cancelled_subscriptions = self.search([
            ('state', '=', 'cancelled'),
            ('renewal_invoice_id', '!=', False),
            ('renewal_invoice_id.state', '=', 'draft')
        ])
        
        for subscription in cancelled_subscriptions:
            if subscription.renewal_invoice_id:
                subscription.renewal_invoice_id.button_cancel()
                subscription.renewal_invoice_id = False
                _logger.info(f"Cleaned up draft renewal invoice for cancelled subscription {subscription.name}")
        
        # Auto-cancel subscriptions that have been expired for more than 90 days
        old_expired_subscriptions = self.search([
            ('state', '=', 'expired'),
            ('end_date', '<', today - relativedelta(days=90))
        ])
        
        old_expired_subscriptions.write({'state': 'cancelled'})
        _logger.info(f"Auto-cancelled {len(old_expired_subscriptions)} old expired subscriptions")
        
        _logger.info("Monthly cleanup completed")
    
    @api.model
    def _cron_auto_confirm_paid_renewals(self):
        """Cron job to auto-confirm renewals when invoices are paid"""
        paid_renewal_invoices = self.env['account.move'].search([
            ('is_renewal_invoice', '=', True),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'paid')
        ])
        
        for invoice in paid_renewal_invoices:
            subscription = invoice.subscription_id
            if subscription and subscription.state == 'pending_renewal':
                subscription.action_confirm_renewal()
                _logger.info(f"Auto-confirmed renewal for subscription {subscription.name} after payment")
        
        _logger.info(f"Auto-confirmed {len(paid_renewal_invoices)} paid renewals")
    
    def _send_renewal_reminder_email(self):
        """Send renewal reminder email using Odoo's email system"""
        # Get email template
        template = self.env.ref('ams_subscriptions.email_template_renewal_reminder', False)
        if template:
            try:
                template.send_mail(self.id, force_send=True)
                self.renewal_reminder_sent = True
                _logger.info(f"Renewal reminder email sent for subscription {self.name}")
            except Exception as e:
                _logger.error(f"Failed to send renewal reminder email for {self.name}: {str(e)}")
        else:
            _logger.warning("Renewal reminder email template not found")
    
    def _get_renewal_summary_data(self):
        """Get summary data for renewal dashboard"""
        today = fields.Date.today()
        
        return {
            'due_today': self.search_count([
                ('is_recurring', '=', True),
                ('state', '=', 'active'),
                ('next_renewal_date', '=', today)
            ]),
            'due_this_week': self.search_count([
                ('is_recurring', '=', True),
                ('state', '=', 'active'),
                ('next_renewal_date', '>=', today),
                ('next_renewal_date', '<=', today + relativedelta(days=7))
            ]),
            'due_this_month': self.search_count([
                ('is_recurring', '=', True),
                ('state', '=', 'active'),
                ('next_renewal_date', '>=', today),
                ('next_renewal_date', '<=', today + relativedelta(months=1))
            ]),
            'pending_payment': self.search_count([
                ('state', '=', 'pending_renewal'),
                ('renewal_invoice_id', '!=', False)
            ]),
            'overdue': self.search_count([
                ('is_recurring', '=', True),
                ('state', '=', 'active'),
                ('next_renewal_date', '<', today)
            ])
        }