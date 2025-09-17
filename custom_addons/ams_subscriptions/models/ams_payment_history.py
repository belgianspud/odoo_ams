# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta

class AMSPaymentHistory(models.Model):
    _name = 'ams.payment.history'
    _description = 'AMS Payment History'
    _order = 'payment_date desc'
    _inherit = ['mail.thread']

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='subscription_id.partner_id',
        store=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True
    )
    
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Invoice Line'
    )
    
    payment_date = fields.Datetime(
        string='Payment Date',
        default=fields.Datetime.now,
        tracking=True
    )
    
    amount = fields.Float(
        string='Payment Amount',
        required=True
    )
    
    payment_status = fields.Selection([
        ('success', 'Successful'),
        ('failed', 'Failed'),
        ('nsf', 'NSF (Non-Sufficient Funds)'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ], string='Payment Status', required=True, default='pending', tracking=True)
    
    payment_method = fields.Selection([
        ('invoice', 'Manual Invoice Payment'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ], string='Payment Method', default='invoice')
    
    failure_reason = fields.Text(
        string='Failure Reason',
        help='Details about why the payment failed'
    )
    
    failure_date = fields.Datetime(
        string='Failure Date',
        help='When the payment failure was detected'
    )
    
    retry_count = fields.Integer(
        string='Retry Attempts',
        default=0,
        help='Number of times payment was retried'
    )
    
    next_retry_date = fields.Datetime(
        string='Next Retry Date',
        help='When to attempt payment again'
    )
    
    # References to actual payment records
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment Record'
    )
    
    # Flags for easy filtering
    is_nsf = fields.Boolean(
        string='Is NSF',
        compute='_compute_flags',
        store=True
    )
    
    is_recent_failure = fields.Boolean(
        string='Recent Failure',
        compute='_compute_flags',
        store=True,
        help='Failed in the last 30 days'
    )

    @api.depends('payment_status', 'failure_date')
    def _compute_flags(self):
        for record in self:
            record.is_nsf = record.payment_status == 'nsf'
            
            if record.failure_date:
                thirty_days_ago = datetime.now() - timedelta(days=30)
                record.is_recent_failure = record.failure_date >= thirty_days_ago and record.payment_status == 'failed'
            else:
                record.is_recent_failure = False

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle payment failure logic"""
        records = super().create(vals_list)
        
        for record in records:
            if record.payment_status in ['failed', 'nsf']:
                record._handle_payment_failure()
            elif record.payment_status == 'success':
                record._handle_payment_success()
        
        return records

    def write(self, vals):
        """Override write to handle status changes"""
        result = super().write(vals)
        
        if 'payment_status' in vals:
            for record in self:
                if record.payment_status in ['failed', 'nsf']:
                    record._handle_payment_failure()
                elif record.payment_status == 'success':
                    record._handle_payment_success()
                    
        return result

    def _handle_payment_failure(self):
        """Handle payment failure - update partner, subscription, etc."""
        self.ensure_one()
        
        # Set failure date if not set
        if not self.failure_date:
            self.failure_date = fields.Datetime.now()
        
        # Update partner NSF flag
        partner = self.partner_id
        partner.has_nsf_history = True
        partner.last_nsf_date = self.failure_date
        partner.nsf_count += 1
        
        # Update subscription status if needed
        subscription = self.subscription_id
        if subscription.state == 'active':
            # Don't immediately suspend - but flag for attention
            subscription.payment_issues = True
            subscription.last_payment_failure = self.failure_date
        
        # Log the failure
        self.subscription_id.message_post(
            body=f"Payment failure recorded: {self.payment_status.upper()} - {self.failure_reason or 'No reason provided'}",
            message_type='notification'
        )
        
        # Schedule retry if appropriate
        if self.payment_status == 'failed' and self.retry_count < 3:
            self._schedule_payment_retry()

    def _handle_payment_success(self):
        """Handle successful payment - clear flags, extend subscription, etc."""
        self.ensure_one()
        
        # Clear payment issues on subscription
        subscription = self.subscription_id
        subscription.payment_issues = False
        subscription.last_successful_payment = self.payment_date
        
        # Update partner flags if this clears recent failures
        partner = self.partner_id
        recent_failures = self.search([
            ('partner_id', '=', partner.id),
            ('payment_status', 'in', ['failed', 'nsf']),
            ('failure_date', '>=', fields.Datetime.now() - timedelta(days=30))
        ])
        
        if not recent_failures:
            partner.has_recent_nsf = False
        
        # Log success
        self.subscription_id.message_post(
            body=f"Payment successful: ${self.amount:.2f} via {self.payment_method}",
            message_type='notification'
        )

    def _schedule_payment_retry(self):
        """Schedule the next payment retry"""
        self.ensure_one()
        
        # Exponential backoff: 1 day, 3 days, 7 days
        retry_delays = {0: 1, 1: 3, 2: 7}
        delay_days = retry_delays.get(self.retry_count, 7)
        
        self.next_retry_date = fields.Datetime.now() + timedelta(days=delay_days)
        self.retry_count += 1

    def action_retry_payment(self):
        """Action to retry a failed payment"""
        self.ensure_one()
        
        if self.payment_status not in ['failed', 'nsf']:
            raise UserError("Can only retry failed payments")
        
        # This would integrate with your payment processor
        # For now, just reset to pending and let user handle manually
        self.write({
            'payment_status': 'pending',
            'failure_reason': f"Retry attempt #{self.retry_count}",
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Payment retry initiated for {self.subscription_id.name}',
                'type': 'info',
                'sticky': False,
            }
        }

    def action_mark_paid(self):
        """Manual action to mark payment as successful"""
        self.ensure_one()
        
        self.write({
            'payment_status': 'success',
            'payment_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Payment marked as successful for {self.subscription_id.name}',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def create_from_invoice_payment(self, invoice, payment_status='success', payment_method='invoice'):
        """Create payment history records from invoice payments"""
        records = []
        
        for line in invoice.invoice_line_ids:
            # Find related subscription
            subscription = self.env['ams.subscription'].search([
                ('invoice_line_id', '=', line.id)
            ], limit=1)
            
            if subscription:
                vals = {
                    'subscription_id': subscription.id,
                    'invoice_id': invoice.id,
                    'invoice_line_id': line.id,
                    'amount': line.price_subtotal,
                    'payment_status': payment_status,
                    'payment_method': payment_method,
                }
                
                if payment_status in ['failed', 'nsf']:
                    vals['failure_date'] = fields.Datetime.now()
                    vals['failure_reason'] = f"Payment failed for invoice {invoice.name}"
                
                records.append(self.create(vals))
        
        return records

    @api.model
    def get_nsf_customers(self):
        """Get list of customers with recent NSF issues"""
        thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
        
        return self.search([
            ('payment_status', 'in', ['failed', 'nsf']),
            ('failure_date', '>=', thirty_days_ago)
        ]).mapped('partner_id')


# Enhance the Partner model to track payment history
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Payment failure tracking
    has_nsf_history = fields.Boolean(
        string='Has NSF History',
        default=False,
        help='This customer has had payment failures'
    )
    
    has_recent_nsf = fields.Boolean(
        string='Recent NSF',
        compute='_compute_nsf_flags',
        store=True,
        help='Has had payment failures in the last 30 days'
    )
    
    last_nsf_date = fields.Datetime(
        string='Last NSF Date',
        help='Date of most recent payment failure'
    )
    
    nsf_count = fields.Integer(
        string='Total NSF Count',
        default=0,
        help='Total number of payment failures'
    )
    
    # Active subscription tracking
    current_individual_subscription_id = fields.Many2one(
        'ams.subscription',
        string='Current Individual Subscription',
        help='Current active individual membership'
    )
    
    current_enterprise_subscription_id = fields.Many2one(
        'ams.subscription',
        string='Current Enterprise Subscription', 
        help='Current active enterprise membership'
    )
    
    # Payment history
    payment_history_ids = fields.One2many(
        'ams.payment.history',
        'partner_id',
        string='Payment History'
    )

    @api.depends('payment_history_ids.payment_status', 'payment_history_ids.failure_date')
    def _compute_nsf_flags(self):
        thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
        
        for partner in self:
            recent_failures = partner.payment_history_ids.filtered(
                lambda p: p.payment_status in ['failed', 'nsf'] and 
                         p.failure_date and p.failure_date >= thirty_days_ago
            )
            partner.has_recent_nsf = bool(recent_failures)

    def action_view_payment_history(self):
        """Action to view payment history for this partner"""
        self.ensure_one()
        
        return {
            'name': f'Payment History - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.payment.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }

    def action_clear_nsf_flag(self):
        """Manual action to clear NSF flags (after verification)"""
        self.ensure_one()
        
        self.write({
            'has_recent_nsf': False,
            'has_nsf_history': False,  # Optional - or keep history but clear recent flag
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'NSF flags cleared for {self.name}',
                'type': 'success',
                'sticky': False,
            }
        }