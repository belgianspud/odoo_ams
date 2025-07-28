from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionRenewal(models.Model):
    _name = 'ams.subscription.renewal'
    _description = 'AMS Subscription Renewal Management'
    _order = 'renewal_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        'Subscription',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    renewal_date = fields.Date(
        'Renewal Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Date when the renewal was processed"
    )
    
    previous_end_date = fields.Date(
        'Previous End Date',
        required=True,
        help="End date before renewal"
    )
    
    new_end_date = fields.Date(
        'New End Date',
        required=True,
        help="End date after renewal"
    )
    
    renewal_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semiannual', 'Semi-Annual'),
        ('yearly', 'Yearly')
    ], string='Renewal Period', required=True)
    
    amount = fields.Monetary(
        'Renewal Amount',
        currency_field='currency_id',
        required=True,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    method = fields.Selection([
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('batch', 'Batch Processing')
    ], string='Renewal Method', default='manual', required=True)
    
    # Invoice and payment tracking
    invoice_id = fields.Many2one(
        'account.move',
        'Renewal Invoice',
        readonly=True,
        tracking=True
    )
    
    payment_status = fields.Selection(
        related='invoice_id.payment_state',
        string='Payment Status',
        readonly=True
    )
    
    payment_date = fields.Date(
        'Payment Date',
        compute='_compute_payment_info',
        store=True
    )
    
    # Related fields for easier access
    partner_id = fields.Many2one(
        related='subscription_id.partner_id',
        string='Member',
        store=True,
        readonly=True
    )
    
    subscription_type_id = fields.Many2one(
        related='subscription_id.subscription_type_id',
        string='Subscription Type',
        store=True,
        readonly=True
    )
    
    chapter_id = fields.Many2one(
        related='subscription_id.chapter_id',
        string='Chapter',
        store=True,
        readonly=True
    )
    
    # Computed fields
    display_name = fields.Char(
        'Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    renewal_duration_days = fields.Integer(
        'Renewal Duration (Days)',
        compute='_compute_renewal_duration',
        store=True
    )
    
    days_extended = fields.Integer(
        'Days Extended',
        compute='_compute_renewal_duration',
        store=True
    )
    
    # Tracking and audit
    created_by_rule = fields.Boolean(
        'Created by Rule',
        default=False,
        help="Whether this renewal was created automatically by a rule"
    )
    
    rule_id = fields.Many2one(
        'ams.subscription.rule',
        'Applied Rule',
        help="Rule that created this renewal (if automatic)"
    )
    
    notes = fields.Text('Notes')
    
    @api.depends('subscription_id', 'renewal_date', 'renewal_period')
    def _compute_display_name(self):
        for record in self:
            if record.subscription_id:
                record.display_name = f"{record.subscription_id.name} - {record.renewal_period.title()} Renewal ({record.renewal_date})"
            else:
                record.display_name = f"Renewal - {record.renewal_date}"
    
    @api.depends('previous_end_date', 'new_end_date')
    def _compute_renewal_duration(self):
        for record in self:
            if record.previous_end_date and record.new_end_date:
                delta = record.new_end_date - record.previous_end_date
                record.days_extended = delta.days
                
                # Calculate standard renewal duration
                if record.renewal_period == 'monthly':
                    record.renewal_duration_days = 30
                elif record.renewal_period == 'quarterly':
                    record.renewal_duration_days = 90
                elif record.renewal_period == 'semiannual':
                    record.renewal_duration_days = 180
                elif record.renewal_period == 'yearly':
                    record.renewal_duration_days = 365
                else:
                    record.renewal_duration_days = delta.days
            else:
                record.days_extended = 0
                record.renewal_duration_days = 0
    
    @api.depends('invoice_id', 'invoice_id.payment_state', 'invoice_id.invoice_payments_widget')
    def _compute_payment_info(self):
        for record in self:
            if record.invoice_id and record.invoice_id.payment_state == 'paid':
                # Try to get the payment date from the invoice
                payments = record.invoice_id.line_ids.mapped('matched_credit_ids').mapped('credit_move_id').mapped('move_id')
                if payments:
                    record.payment_date = max(payments.mapped('date'))
                else:
                    record.payment_date = record.invoice_id.invoice_date
            else:
                record.payment_date = False
    
    @api.model
    def create_renewal(self, subscription, renewal_period=None, amount=None):
        """Create a renewal for a subscription"""
        if not subscription.is_recurring:
            raise UserError(_("Cannot create renewal for non-recurring subscription"))
        
        # Use subscription's default period if not specified
        period = renewal_period or subscription.recurring_period
        
        # Calculate new end date
        current_end = subscription.end_date
        if period == 'monthly':
            new_end = current_end + relativedelta(months=1)
        elif period == 'quarterly':
            new_end = current_end + relativedelta(months=3)
        elif period == 'semiannual':
            new_end = current_end + relativedelta(months=6)
        else:  # yearly
            new_end = current_end + relativedelta(years=1)
        
        # Use subscription amount if not specified
        renewal_amount = amount or subscription.amount
        
        vals = {
            'subscription_id': subscription.id,
            'previous_end_date': current_end,
            'new_end_date': new_end,
            'renewal_period': period,
            'amount': renewal_amount,
            'state': 'draft',
            'method': 'manual'
        }
        
        return self.create(vals)
    
    def action_generate_invoice(self):
        """Generate renewal invoice"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_("Invoice already exists for this renewal"))
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.subscription_id.product_id.id if self.subscription_id.product_id else False,
                'name': f"Renewal: {self.subscription_id.name} ({self.previous_end_date} to {self.new_end_date})",
                'quantity': 1,
                'price_unit': self.amount,
                'account_id': self._get_income_account().id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Link invoice to renewal and subscription
        self.write({
            'invoice_id': invoice.id,
            'state': 'pending'
        })
        
        self.subscription_id.write({
            'renewal_invoice_id': invoice.id,
            'state': 'pending_renewal'
        })
        
        self.message_post(body=f"Renewal invoice {invoice.name} created")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }
    
    def action_confirm_renewal(self):
        """Confirm the renewal and update subscription"""
        self.ensure_one()
        
        if self.state != 'pending':
            raise UserError(_("Only pending renewals can be confirmed"))
        
        if self.invoice_id and self.invoice_id.payment_state != 'paid':
            raise UserError(_("Invoice must be paid before confirming renewal"))
        
        # Update subscription
        self.subscription_id.write({
            'end_date': self.new_end_date,
            'paid_through_date': self.new_end_date,
            'next_renewal_date': self._calculate_next_renewal_date(),
            'state': 'active',
            'renewal_invoice_id': False,
            'last_renewal_date': self.renewal_date,
        })
        
        # Update renewal status
        self.write({'state': 'paid'})
        
        # Create status history entry
        self.env['ams.subscription.status.history'].create_status_change(
            self.subscription_id,
            'pending_renewal',
            'active',
            f"Renewed until {self.new_end_date}",
            automatic=False
        )
        
        self.message_post(body=f"Renewal confirmed. Subscription extended until {self.new_end_date}")
        
        return True
    
    def action_cancel_renewal(self):
        """Cancel the renewal"""
        self.ensure_one()
        
        if self.state in ('paid', 'cancelled'):
            raise UserError(_("Cannot cancel a paid or already cancelled renewal"))
        
        # Cancel associated invoice if exists
        if self.invoice_id and self.invoice_id.state == 'draft':
            self.invoice_id.button_cancel()
        
        # Update renewal and subscription status
        self.write({'state': 'cancelled'})
        
        if self.subscription_id.state == 'pending_renewal':
            self.subscription_id.write({
                'state': 'active',
                'renewal_invoice_id': False
            })
        
        self.message_post(body="Renewal cancelled")
        
        return True
    
    def _calculate_next_renewal_date(self):
        """Calculate the next renewal date after this renewal"""
        if self.renewal_period == 'monthly':
            return self.new_end_date + relativedelta(months=1)
        elif self.renewal_period == 'quarterly':
            return self.new_end_date + relativedelta(months=3)
        elif self.renewal_period == 'semiannual':
            return self.new_end_date + relativedelta(months=6)
        else:  # yearly
            return self.new_end_date + relativedelta(years=1)
    
    def _get_income_account(self):
        """Get the income account for the renewal invoice"""
        if self.subscription_id.product_id:
            return self.subscription_id.product_id.product_tmpl_id.get_product_accounts()['income']
        else:
            # Fallback to default income account
            return self.env['account.account'].search([
                ('user_type_id.name', '=', 'Income'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
    
    @api.model
    def process_automatic_renewals(self):
        """Process automatic renewals for eligible subscriptions"""
        today = fields.Date.today()
        
        # Find subscriptions eligible for automatic renewal
        eligible_subscriptions = self.env['ams.subscription'].search([
            ('is_recurring', '=', True),
            ('auto_renewal', '=', True),
            ('state', '=', 'active'),
            ('next_renewal_date', '<=', today)
        ])
        
        renewals_processed = 0
        
        for subscription in eligible_subscriptions:
            try:
                # Create renewal
                renewal = self.create_renewal(subscription)
                renewal.write({
                    'method': 'automatic',
                    'created_by_rule': True
                })
                
                # Generate invoice
                renewal.action_generate_invoice()
                
                # For auto-renewal, we might want to automatically confirm if payment method is on file
                # This would depend on your payment processing integration
                
                renewals_processed += 1
                _logger.info(f"Automatic renewal processed for subscription {subscription.name}")
                
            except Exception as e:
                _logger.error(f"Failed to process automatic renewal for {subscription.name}: {str(e)}")
        
        return renewals_processed
    
    @api.model
    def get_renewal_statistics(self, date_from=None, date_to=None):
        """Get renewal statistics for reporting"""
        domain = []
        
        if date_from:
            domain.append(('renewal_date', '>=', date_from))
        if date_to:
            domain.append(('renewal_date', '<=', date_to))
        
        renewals = self.search(domain)
        
        total_renewals = len(renewals)
        successful_renewals = len(renewals.filtered(lambda r: r.state == 'paid'))
        failed_renewals = len(renewals.filtered(lambda r: r.state == 'failed'))
        pending_renewals = len(renewals.filtered(lambda r: r.state == 'pending'))
        
        total_revenue = sum(renewals.filtered(lambda r: r.state == 'paid').mapped('amount'))
        
        # Success rate
        success_rate = (successful_renewals / total_renewals * 100) if total_renewals > 0 else 0
        
        # Average renewal amount
        avg_amount = total_revenue / successful_renewals if successful_renewals > 0 else 0
        
        # Renewal by period
        by_period = {}
        for period in ['monthly', 'quarterly', 'semiannual', 'yearly']:
            count = len(renewals.filtered(lambda r: r.renewal_period == period))
            by_period[period] = count
        
        return {
            'total_renewals': total_renewals,
            'successful_renewals': successful_renewals,
            'failed_renewals': failed_renewals,
            'pending_renewals': pending_renewals,
            'success_rate': success_rate,
            'total_revenue': total_revenue,
            'average_amount': avg_amount,
            'by_period': by_period
        }
    
    # Actions for views
    def action_view_subscription(self):
        """View the related subscription"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription'),
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
        }
    
    def action_view_invoice(self):
        """View the renewal invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this renewal"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }
    
    @api.constrains('previous_end_date', 'new_end_date')
    def _check_dates(self):
        for record in self:
            if record.previous_end_date >= record.new_end_date:
                raise ValidationError(_("New end date must be after previous end date"))
    
    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Renewal amount must be positive"))