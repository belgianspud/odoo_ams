from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionChange(models.Model):
    _name = 'subscription.change'
    _description = 'Subscription Change Request'
    _order = 'change_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Change Reference',
        compute='_compute_name',
        store=True,
        help="Reference for this subscription change"
    )
    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Subscription',
        required=True,
        help="The subscription being changed"
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Subscriber',
        readonly=True
    )
    
    # Change Details
    change_type = fields.Selection([
        ('plan_change', 'Plan Change'),
        ('payment_plan_change', 'Payment Plan Change'),
        ('pause', 'Pause Subscription'),
        ('resume', 'Resume Subscription'),
        ('early_termination', 'Early Termination'),
        ('extension', 'Extension'),
        ('other', 'Other')
    ], string='Change Type', required=True, tracking=True)
    
    change_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Date when the change becomes effective"
    )
    
    # Plan Changes
    old_plan_id = fields.Many2one(
        'subscription.plan',
        string='From Plan',
        help="Current subscription plan"
    )
    new_plan_id = fields.Many2one(
        'subscription.plan',
        string='To Plan',
        help="New subscription plan"
    )
    
    # Payment Plan Changes
    old_payment_plan_id = fields.Many2one(
        'subscription.payment.plan',
        string='From Payment Plan',
        help="Current payment plan"
    )
    new_payment_plan_id = fields.Many2one(
        'subscription.payment.plan',
        string='To Payment Plan',
        help="New payment plan"
    )
    
    # Reason and Details
    reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('upgrade', 'Plan Upgrade'),
        ('downgrade', 'Plan Downgrade'),
        ('financial_hardship', 'Financial Hardship'),
        ('service_issue', 'Service Issue'),
        ('competitive_offer', 'Competitive Offer'),
        ('administrative', 'Administrative'),
        ('other', 'Other')
    ], string='Reason', required=True, tracking=True)
    
    reason_notes = fields.Text(
        string='Reason Notes',
        help="Additional details about the reason for change"
    )
    
    # Financial Impact
    old_plan_price = fields.Monetary(
        string='Old Plan Price',
        related='old_plan_id.price',
        currency_field='currency_id',
        readonly=True
    )
    new_plan_price = fields.Monetary(
        string='New Plan Price',
        related='new_plan_id.price',
        currency_field='currency_id',
        readonly=True
    )
    price_difference = fields.Monetary(
        string='Price Difference',
        compute='_compute_price_difference',
        currency_field='currency_id',
        help="Difference in pricing (positive = increase, negative = decrease)"
    )
    
    # Proration Calculations
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_proration',
        help="Days remaining on current subscription period"
    )
    proration_credit = fields.Monetary(
        string='Proration Credit',
        compute='_compute_proration',
        store=True,
        currency_field='currency_id',
        help="Credit for unused portion of old plan"
    )
    proration_charge = fields.Monetary(
        string='Proration Charge',
        compute='_compute_proration',
        store=True,
        currency_field='currency_id',
        help="Charge for new plan from change date"
    )
    net_adjustment = fields.Monetary(
        string='Net Adjustment',
        compute='_compute_net_adjustment',
        currency_field='currency_id',
        help="Net amount to charge/credit (positive = charge, negative = credit)"
    )
    
    # Processing Information
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    processed_date = fields.Datetime(
        string='Processed Date',
        help="When the change was processed"
    )
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        help="User who processed the change"
    )
    
    # Related Records
    adjustment_invoice_id = fields.Many2one(
        'account.move',
        string='Adjustment Invoice',
        help="Invoice created for subscription change adjustment"
    )
    
    # Pause/Resume specific fields
    pause_start_date = fields.Date(
        string='Pause Start Date',
        help="When subscription pause begins"
    )
    pause_end_date = fields.Date(
        string='Pause End Date',
        help="When subscription resumes (optional for indefinite pause)"
    )
    pause_reason = fields.Text(
        string='Pause Reason',
        help="Reason for pausing subscription"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('partner_id.name', 'change_type', 'change_date')
    def _compute_name(self):
        for record in self:
            if record.partner_id and record.change_type:
                change_type_name = dict(record._fields['change_type'].selection).get(record.change_type)
                record.name = f"{record.partner_id.name}: {change_type_name}"
            else:
                record.name = "New Subscription Change"

    @api.depends('old_plan_price', 'new_plan_price')
    def _compute_price_difference(self):
        for record in self:
            if record.old_plan_id and record.new_plan_id:
                record.price_difference = record.new_plan_price - record.old_plan_price
            else:
                record.price_difference = 0

    @api.depends('subscription_id.end_date', 'change_date', 'old_plan_id', 'new_plan_id')
    def _compute_proration(self):
        for record in self:
            if (record.subscription_id.end_date and record.change_date and 
                record.old_plan_id and record.new_plan_id):
                
                # Calculate days remaining
                remaining_days = (record.subscription_id.end_date - record.change_date).days
                record.days_remaining = max(0, remaining_days)
                
                if record.days_remaining > 0:
                    # Calculate total days in subscription period
                    total_days = (record.subscription_id.end_date - record.subscription_id.start_date).days
                    
                    if total_days > 0:
                        # Calculate proration factor
                        proration_factor = record.days_remaining / total_days
                        
                        # Calculate credit for unused portion of old plan
                        record.proration_credit = record.old_plan_price * proration_factor
                        
                        # Calculate charge for new plan for remaining period
                        record.proration_charge = record.new_plan_price * proration_factor
                    else:
                        record.proration_credit = 0
                        record.proration_charge = 0
                else:
                    record.proration_credit = 0
                    record.proration_charge = 0
            else:
                record.days_remaining = 0
                record.proration_credit = 0
                record.proration_charge = 0

    @api.depends('proration_charge', 'proration_credit')
    def _compute_net_adjustment(self):
        for record in self:
            record.net_adjustment = record.proration_charge - record.proration_credit

    @api.constrains('change_date', 'subscription_id')
    def _check_change_date(self):
        for record in self:
            if record.change_date and record.subscription_id:
                if record.change_date < record.subscription_id.start_date:
                    raise ValidationError(_("Change date cannot be before subscription start date."))
                if record.change_date > record.subscription_id.end_date:
                    raise ValidationError(_("Change date cannot be after subscription end date."))

    @api.constrains('pause_start_date', 'pause_end_date')
    def _check_pause_dates(self):
        for record in self:
            if record.pause_start_date and record.pause_end_date:
                if record.pause_start_date >= record.pause_end_date:
                    raise ValidationError(_("Pause start date must be before pause end date."))

    @api.onchange('subscription_id', 'change_type')
    def _onchange_subscription_change_type(self):
        if self.subscription_id:
            self.old_plan_id = self.subscription_id.plan_id
            self.old_payment_plan_id = self.subscription_id.payment_plan_id

    def action_submit(self):
        """Submit change request for approval"""
        for record in self:
            if record.state == 'draft':
                record.state = 'submitted'
                record.message_post(body=_("Subscription change submitted for approval."))

    def action_approve(self):
        """Approve the change request"""
        for record in self:
            if record.state == 'submitted':
                record.state = 'approved'
                record.message_post(body=_("Subscription change approved."))

    def action_reject(self):
        """Reject the change request"""
        for record in self:
            if record.state == 'submitted':
                record.state = 'rejected'
                record.message_post(body=_("Subscription change rejected."))

    def action_process(self):
        """Process the approved change"""
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Only approved changes can be processed."))
            
            # Process based on change type
            if record.change_type == 'plan_change':
                record._process_plan_change()
            elif record.change_type == 'payment_plan_change':
                record._process_payment_plan_change()
            elif record.change_type == 'pause':
                record._process_pause()
            elif record.change_type == 'resume':
                record._process_resume()
            elif record.change_type == 'early_termination':
                record._process_early_termination()
            elif record.change_type == 'extension':
                record._process_extension()
            
            # Update status
            record.write({
                'state': 'processed',
                'processed_date': fields.Datetime.now(),
                'processed_by': self.env.user.id
            })
            
            record.message_post(body=_("Subscription change processed successfully."))

    def _process_plan_change(self):
        """Process plan change with proration"""
        self.ensure_one()
        
        # Create adjustment invoice if needed
        if abs(self.net_adjustment) > 0.01:  # Account for rounding
            self._create_adjustment_invoice()
        
        # Update subscription
        self.subscription_id.write({
            'plan_id': self.new_plan_id.id
        })
        
        # Log the change
        self.subscription_id.message_post(
            body=_("Plan changed from %s to %s. Net adjustment: %s %s") % (
                self.old_plan_id.name,
                self.new_plan_id.name,
                self.net_adjustment,
                self.currency_id.symbol
            )
        )

    def _process_payment_plan_change(self):
        """Process payment plan change"""
        self.ensure_one()
        
        # Cancel existing installments
        pending_installments = self.subscription_id.installment_ids.filtered(
            lambda i: i.status == 'pending'
        )
        pending_installments.write({'status': 'cancelled'})
        
        # Update subscription payment plan
        self.subscription_id.write({
            'payment_plan_id': self.new_payment_plan_id.id
        })
        
        # Set up new payment plan
        self.subscription_id.action_setup_payment_plan()

    def _process_pause(self):
        """Process subscription pause"""
        self.ensure_one()
        
        # Update subscription
        self.subscription_id.write({
            'state': 'paused' if 'paused' in dict(self.subscription_id._fields['state'].selection) else 'grace'
        })
        
        # If there's an end date, extend subscription
        if self.pause_end_date and self.pause_start_date:
            pause_days = (self.pause_end_date - self.pause_start_date).days
            new_end_date = self.subscription_id.end_date + timedelta(days=pause_days)
            self.subscription_id.end_date = new_end_date

    def _process_resume(self):
        """Process subscription resume"""
        self.ensure_one()
        
        # Update subscription
        self.subscription_id.write({
            'state': 'active'
        })

    def _process_early_termination(self):
        """Process early termination"""
        self.ensure_one()
        
        # Update subscription end date and status
        self.subscription_id.write({
            'end_date': self.change_date,
            'state': 'cancelled'
        })
        
        # Calculate refund if applicable
        if self.proration_credit > 0:
            self._create_adjustment_invoice()

    def _process_extension(self):
        """Process subscription extension"""
        self.ensure_one()
        
        if self.new_plan_id:
            # Extend by plan duration
            extension_months = self.new_plan_id.duration_months
            new_end_date = self.subscription_id.end_date + relativedelta(months=extension_months)
            self.subscription_id.end_date = new_end_date

    def _create_adjustment_invoice(self):
        """Create adjustment invoice for subscription change"""
        self.ensure_one()
        
        if abs(self.net_adjustment) < 0.01:  # Skip if amount is negligible
            return
        
        # Determine invoice type and amount
        if self.net_adjustment > 0:
            # Charge customer
            invoice_type = 'out_invoice'
            amount = self.net_adjustment
            description = f"Subscription change charge: {self.old_plan_id.name} to {self.new_plan_id.name}"
        else:
            # Credit customer
            invoice_type = 'out_refund'
            amount = abs(self.net_adjustment)
            description = f"Subscription change credit: {self.old_plan_id.name} to {self.new_plan_id.name}"
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': invoice_type,
            'invoice_date': self.change_date,
            'ref': self.name,
            'subscription_id': self.subscription_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': amount,
                'account_id': self.new_plan_id.product_id.categ_id.property_account_income_categ_id.id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.adjustment_invoice_id = invoice.id
        
        return invoice

    def action_cancel(self):
        """Cancel change request"""
        for record in self:
            if record.state in ['draft', 'submitted', 'approved']:
                record.state = 'cancelled'
                record.message_post(body=_("Subscription change cancelled."))


class SubscriptionChangeWizard(models.TransientModel):
    _name = 'subscription.change.wizard'
    _description = 'Subscription Change Wizard'

    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Subscription',
        required=True
    )
    change_type = fields.Selection([
        ('plan_change', 'Change Plan'),
        ('payment_plan_change', 'Change Payment Plan'),
        ('pause', 'Pause Subscription'),
        ('early_termination', 'Early Termination'),
        ('extension', 'Extend Subscription')
    ], string='Change Type', required=True)
    
    # Plan change fields
    new_plan_id = fields.Many2one(
        'subscription.plan',
        string='New Plan'
    )
    new_payment_plan_id = fields.Many2one(
        'subscription.payment.plan',
        string='New Payment Plan'
    )
    
    change_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today
    )
    reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('upgrade', 'Plan Upgrade'),
        ('downgrade', 'Plan Downgrade'),
        ('financial_hardship', 'Financial Hardship'),
        ('service_issue', 'Service Issue'),
        ('other', 'Other')
    ], string='Reason', required=True)
    
    reason_notes = fields.Text(string='Notes')
    
    # Preview calculations
    net_adjustment = fields.Monetary(
        string='Net Adjustment',
        compute='_compute_preview',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('subscription_id', 'new_plan_id', 'change_date')
    def _compute_preview(self):
        for wizard in self:
            if wizard.subscription_id and wizard.new_plan_id and wizard.change_date:
                # Simplified calculation for preview
                old_price = wizard.subscription_id.plan_id.price
                new_price = wizard.new_plan_id.price
                
                # Calculate remaining days
                if wizard.subscription_id.end_date:
                    remaining_days = (wizard.subscription_id.end_date - wizard.change_date).days
                    total_days = (wizard.subscription_id.end_date - wizard.subscription_id.start_date).days
                    
                    if total_days > 0 and remaining_days > 0:
                        proration_factor = remaining_days / total_days
                        proration_credit = old_price * proration_factor
                        proration_charge = new_price * proration_factor
                        wizard.net_adjustment = proration_charge - proration_credit
                    else:
                        wizard.net_adjustment = 0
                else:
                    wizard.net_adjustment = 0
            else:
                wizard.net_adjustment = 0

    def action_create_change_request(self):
        """Create subscription change request"""
        self.ensure_one()
        
        vals = {
            'subscription_id': self.subscription_id.id,
            'change_type': self.change_type,
            'change_date': self.change_date,
            'reason': self.reason,
            'reason_notes': self.reason_notes,
        }
        
        if self.change_type == 'plan_change':
            vals.update({
                'old_plan_id': self.subscription_id.plan_id.id,
                'new_plan_id': self.new_plan_id.id,
            })
        elif self.change_type == 'payment_plan_change':
            vals.update({
                'old_payment_plan_id': self.subscription_id.payment_plan_id.id,
                'new_payment_plan_id': self.new_payment_plan_id.id,
            })
        
        change = self.env['subscription.change'].create(vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Change Request'),
            'res_model': 'subscription.change',
            'res_id': change.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_process_immediately(self):
        """Create and immediately process the change"""
        change_action = self.action_create_change_request()
        
        # Get the created change record
        change = self.env['subscription.change'].browse(change_action['res_id'])
        change.state = 'approved'
        change.action_process()
        
        return change_action


# Add change tracking to Subscription model
class Subscription(models.Model):
    _inherit = 'subscription.subscription'

    change_ids = fields.One2many(
        'subscription.change',
        'subscription_id',
        string='Change History'
    )
    change_count = fields.Integer(
        string='Changes',
        compute='_compute_change_count'
    )

    @api.depends('change_ids')
    def _compute_change_count(self):
        for subscription in self:
            subscription.change_count = len(subscription.change_ids)

    def action_change_subscription(self):
        """Open subscription change wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Subscription'),
            'res_model': 'subscription.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id}
        }

    def action_view_changes(self):
        """View subscription change history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change History'),
            'res_model': 'subscription.change',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id}
        }