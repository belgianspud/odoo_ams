# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    """Simplified extension of Account Move (Invoice) for basic subscription billing tracking"""
    _inherit = 'account.move'

    # =============================================================================
    # BASIC BILLING TRACKING FIELDS
    # =============================================================================
    
    # AMS Billing References
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='AMS Subscription',
        ondelete='set null',
        index=True,
        help='Related AMS subscription for this invoice'
    )
    
    billing_schedule_id = fields.Many2one(
        'ams.billing.schedule',
        string='Billing Schedule',
        ondelete='set null',
        help='Billing schedule that generated this invoice'
    )
    
    billing_event_id = fields.Many2one(
        'ams.billing.event',
        string='Billing Event',
        ondelete='set null',
        help='Billing event that generated this invoice'
    )
    
    # Billing Type Classification
    billing_type = fields.Selection([
        ('regular', 'Regular Billing'),
        ('manual', 'Manual Invoice'),
        ('adjustment', 'Adjustment'),
    ], string='Billing Type', default='regular',
    help='Type of billing this invoice represents')
    
    is_subscription_invoice = fields.Boolean(
        string='Is Subscription Invoice',
        compute='_compute_subscription_invoice',
        store=True,
        help='This invoice is related to subscription billing'
    )
    
    # Billing Period Information
    billing_period_start = fields.Date(
        string='Billing Period Start',
        help='Start date of the billing period covered by this invoice'
    )
    
    billing_period_end = fields.Date(
        string='Billing Period End',
        help='End date of the billing period covered by this invoice'
    )
    
    billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Frequency',
    help='Billing frequency for this subscription invoice')
    
    # Basic Customer Communication
    auto_sent = fields.Boolean(
        string='Automatically Sent',
        default=False,
        help='Invoice was automatically sent to customer'
    )
    
    auto_send_date = fields.Datetime(
        string='Auto Send Date',
        readonly=True
    )
    
    # Basic Overdue Information
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue_info',
        store=True
    )
    
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_overdue_info',
        store=True
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('subscription_id', 'billing_schedule_id', 'billing_event_id')
    def _compute_subscription_invoice(self):
        """Determine if this is a subscription invoice"""
        for invoice in self:
            invoice.is_subscription_invoice = bool(
                invoice.subscription_id or 
                invoice.billing_schedule_id or 
                invoice.billing_event_id
            )
    
    @api.depends('invoice_date_due', 'payment_state')
    def _compute_overdue_info(self):
        """Compute basic overdue information"""
        today = fields.Date.today()
        
        for invoice in self:
            if (invoice.invoice_date_due and 
                invoice.payment_state in ['not_paid', 'partial'] and
                invoice.invoice_date_due < today):
                invoice.is_overdue = True
                invoice.days_overdue = (today - invoice.invoice_date_due).days
            else:
                invoice.is_overdue = False
                invoice.days_overdue = 0
    
    # =============================================================================
    # VALIDATION AND CONSTRAINTS
    # =============================================================================
    
    @api.constrains('billing_period_start', 'billing_period_end')
    def _check_billing_period(self):
        """Validate billing period dates"""
        for invoice in self:
            if invoice.billing_period_start and invoice.billing_period_end:
                if invoice.billing_period_end <= invoice.billing_period_start:
                    raise ValidationError(_('Billing period end must be after start date'))
    
    @api.constrains('subscription_id', 'move_type')
    def _check_subscription_invoice_type(self):
        """Validate subscription invoice type"""
        for invoice in self:
            if invoice.subscription_id and invoice.move_type not in ['out_invoice', 'out_refund']:
                raise ValidationError(_('Subscription invoices must be customer invoices or refunds'))
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Update fields when subscription changes"""
        if self.subscription_id:
            # Set partner
            self.partner_id = self.subscription_id.partner_id
            
            # Set billing type
            if not self.billing_type or self.billing_type == 'regular':
                self.billing_type = 'regular'
    
    # =============================================================================
    # SIMPLIFIED BILLING LIFECYCLE
    # =============================================================================
    
    def action_post(self):
        """Override posting to handle basic subscription billing workflows"""
        result = super().action_post()
        
        for invoice in self:
            if invoice.is_subscription_invoice:
                invoice._handle_subscription_invoice_posted()
        
        return result
    
    def _handle_subscription_invoice_posted(self):
        """Handle basic subscription invoice posting"""
        self.ensure_one()
        
        # Auto-send invoice if configured
        if (self.subscription_id and 
            self.subscription_id.auto_send_invoices and 
            not self.auto_sent):
            self._auto_send_invoice()
        
        # Update subscription billing dates
        if self.subscription_id and self.billing_type == 'regular':
            self.subscription_id.last_billing_date = self.invoice_date
    
    def _auto_send_invoice(self):
        """Automatically send invoice to customer"""
        try:
            self.action_invoice_sent()
            self.auto_sent = True
            self.auto_send_date = fields.Datetime.now()
            
            _logger.info(f'Auto-sent invoice {self.name} to {self.partner_id.name}')
            
        except Exception as e:
            _logger.error(f'Failed to auto-send invoice {self.name}: {str(e)}')
            
            # Create activity for manual follow-up
            self.activity_schedule(
                'mail.mail_activity_data_email',
                summary=_('Failed to auto-send invoice'),
                note=_('Automatic invoice sending failed: %s') % str(e)
            )
    
    # =============================================================================
    # BASIC PAYMENT ACTIONS
    # =============================================================================
    
    def action_send_payment_reminder(self):
        """Send basic payment reminder email"""
        self.ensure_one()
        
        if self.payment_state == 'paid':
            raise UserError(_('Invoice is already paid'))
        
        if not self.is_overdue:
            raise UserError(_('Invoice is not overdue'))
        
        # Find payment reminder template
        template = self.env.ref('ams_subscription_billing.email_template_payment_reminder', False)
        if not template:
            raise UserError(_('Payment reminder email template not found'))
        
        # Send email
        template.send_mail(self.id, force_send=True)
        
        self.message_post(body=_('Payment reminder sent to customer'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment reminder sent successfully'),
                'type': 'success',
            }
        }
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def action_view_subscription(self):
        """View related subscription"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_('No subscription linked to this invoice'))
        
        return {
            'name': _('Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_billing_schedule(self):
        """View related billing schedule"""
        self.ensure_one()
        
        if not self.billing_schedule_id:
            raise UserError(_('No billing schedule linked to this invoice'))
        
        return {
            'name': _('Billing Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.schedule',
            'res_id': self.billing_schedule_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def get_payment_portal_url(self):
        """Get basic payment portal URL for customer"""
        self.ensure_one()
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/invoices/{self.id}"
    
    # =============================================================================
    # BASIC REPORTING
    # =============================================================================
    
    def get_billing_summary(self):
        """Get basic billing summary for this invoice"""
        self.ensure_one()
        
        return {
            'invoice_id': self.id,
            'invoice_number': self.name,
            'subscription_name': self.subscription_id.name if self.subscription_id else None,
            'customer_name': self.partner_id.name,
            'billing_type': self.billing_type,
            'amount_total': self.amount_total,
            'amount_residual': self.amount_residual,
            'payment_state': self.payment_state,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'billing_period_start': self.billing_period_start,
            'billing_period_end': self.billing_period_end,
            'auto_sent': self.auto_sent,
        }
    
    # =============================================================================
    # BASIC BATCH OPERATIONS
    # =============================================================================
    
    @api.model
    def cron_send_payment_reminders(self):
        """Basic cron job to send payment reminders for overdue subscription invoices"""
        today = fields.Date.today()
        
        # Find overdue subscription invoices that haven't had reminders sent recently
        overdue_invoices = self.search([
            ('is_subscription_invoice', '=', True),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('is_overdue', '=', True),
        ])
        
        _logger.info(f'Found {len(overdue_invoices)} overdue subscription invoices')
        
        sent_count = 0
        error_count = 0
        
        # Only send reminders for invoices that are 1, 7, or 14 days overdue
        reminder_days = [1, 7, 14]
        
        for invoice in overdue_invoices:
            try:
                if invoice.days_overdue in reminder_days:
                    invoice.action_send_payment_reminder()
                    sent_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f'Error sending payment reminder for invoice {invoice.name}: {str(e)}')
        
        _logger.info(f'Payment reminder sending completed: {sent_count} sent, {error_count} errors')
        
        return {
            'sent_count': sent_count,
            'error_count': error_count,
            'total_overdue': len(overdue_invoices),
        }
    
    @api.model
    def cron_mark_overdue_invoices(self):
        """Basic cron job to mark invoices as overdue"""
        today = fields.Date.today()
        
        # Find invoices that should be marked as overdue
        invoices_to_mark = self.search([
            ('is_subscription_invoice', '=', True),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('is_overdue', '=', False),
        ])
        
        _logger.info(f'Found {len(invoices_to_mark)} invoices to mark as overdue')
        
        # Force recomputation of overdue status
        if invoices_to_mark:
            invoices_to_mark._compute_overdue_info()
        
        # Update subscription payment status
        subscriptions_to_update = invoices_to_mark.mapped('subscription_id')
        if subscriptions_to_update:
            subscriptions_to_update._compute_payment_status()
        
        return {
            'marked_overdue': len(invoices_to_mark),
            'subscriptions_updated': len(subscriptions_to_update),
        }