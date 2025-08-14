# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
import calendar
import logging

_logger = logging.getLogger(__name__)

class AMSProrationCalculation(models.Model):
    """Proration Calculation for Mid-Cycle Subscription Changes"""
    _name = 'ams.proration.calculation'
    _description = 'AMS Proration Calculation'
    _order = 'calculation_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Calculation Name',
        required=True,
        index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('ams.proration.calculation') or 'New'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the proration calculation'
    )
    
    # Related Records
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Customer',
        store=True,
        readonly=True
    )
    
    original_product_id = fields.Many2one(
        'product.product',
        string='Original Product',
        required=True
    )
    
    new_product_id = fields.Many2one(
        'product.product',
        string='New Product',
        help='New product (for upgrades/downgrades). Leave empty for quantity changes.'
    )
    
    billing_event_id = fields.Many2one(
        'ams.billing.event',
        string='Related Billing Event',
        ondelete='set null'
    )
    
    # Calculation Information
    calculation_date = fields.Date(
        string='Calculation Date',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True
    )
    
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        help='Date when the change takes effect',
        tracking=True
    )
    
    proration_type = fields.Selection([
        ('upgrade', 'Product Upgrade'),
        ('downgrade', 'Product Downgrade'),
        ('quantity_increase', 'Quantity Increase'),
        ('quantity_decrease', 'Quantity Decrease'),
        ('add_seats', 'Add Enterprise Seats'),
        ('remove_seats', 'Remove Enterprise Seats'),
        ('plan_change', 'Billing Plan Change'),
        ('mid_cycle_start', 'Mid-Cycle Start'),
        ('early_termination', 'Early Termination'),
        ('suspension_credit', 'Suspension Credit'),
        ('reactivation_charge', 'Reactivation Charge'),
    ], string='Proration Type', required=True, tracking=True)
    
    # Billing Period Information
    billing_period_start = fields.Date(
        string='Billing Period Start',
        required=True,
        help='Start of the current billing period'
    )
    
    billing_period_end = fields.Date(
        string='Billing Period End',
        required=True,
        help='End of the current billing period'
    )
    
    billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Billing Frequency', required=True)
    
    # Pricing Information
    original_price = fields.Monetary(
        string='Original Price',
        currency_field='currency_id',
        required=True
    )
    
    new_price = fields.Monetary(
        string='New Price',
        currency_field='currency_id',
        help='New price (for upgrades/downgrades)'
    )
    
    original_quantity = fields.Float(
        string='Original Quantity',
        default=1.0,
        help='Original quantity/seats'
    )
    
    new_quantity = fields.Float(
        string='New Quantity',
        default=1.0,
        help='New quantity/seats'
    )
    
    # Calculation Method
    proration_method = fields.Selection([
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('percentage', 'Percentage Based'),
        ('fixed_amount', 'Fixed Amount'),
    ], string='Proration Method', required=True, default='daily')
    
    # Calculation Results
    total_period_days = fields.Integer(
        string='Total Period Days',
        compute='_compute_period_calculations',
        store=True,
        help='Total days in the billing period'
    )
    
    remaining_days = fields.Integer(
        string='Remaining Days',
        compute='_compute_period_calculations',
        store=True,
        help='Days remaining from effective date to period end'
    )
    
    proration_percentage = fields.Float(
        string='Proration Percentage',
        compute='_compute_proration_amounts',
        store=True,
        help='Percentage of period remaining'
    )
    
    credit_amount = fields.Monetary(
        string='Credit Amount',
        currency_field='currency_id',
        compute='_compute_proration_amounts',
        store=True,
        help='Amount to credit (for downgrades, early termination)'
    )
    
    charge_amount = fields.Monetary(
        string='Charge Amount',
        currency_field='currency_id',
        compute='_compute_proration_amounts',
        store=True,
        help='Amount to charge (for upgrades, additional seats)'
    )
    
    net_amount = fields.Monetary(
        string='Net Amount',
        currency_field='currency_id',
        compute='_compute_proration_amounts',
        store=True,
        help='Net amount (positive = charge, negative = credit)'
    )
    
    # Manual Adjustments
    manual_override = fields.Boolean(
        string='Manual Override',
        default=False,
        help='Manually override calculated amounts'
    )
    
    manual_credit_amount = fields.Monetary(
        string='Manual Credit Amount',
        currency_field='currency_id',
        help='Manually set credit amount'
    )
    
    manual_charge_amount = fields.Monetary(
        string='Manual Charge Amount',
        currency_field='currency_id',
        help='Manually set charge amount'
    )
    
    override_reason = fields.Text(
        string='Override Reason',
        help='Reason for manual override'
    )
    
    # Final Amounts (considering overrides)
    final_credit_amount = fields.Monetary(
        string='Final Credit Amount',
        currency_field='currency_id',
        compute='_compute_final_amounts',
        store=True
    )
    
    final_charge_amount = fields.Monetary(
        string='Final Charge Amount',
        currency_field='currency_id',
        compute='_compute_final_amounts',
        store=True
    )
    
    final_net_amount = fields.Monetary(
        string='Final Net Amount',
        currency_field='currency_id',
        compute='_compute_final_amounts',
        store=True
    )
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    applied_date = fields.Date(
        string='Applied Date',
        readonly=True
    )
    
    applied_by = fields.Many2one(
        'res.users',
        string='Applied By',
        readonly=True
    )
    
    # Related Records
    invoice_id = fields.Many2one(
        'account.move',
        string='Proration Invoice',
        ondelete='set null',
        help='Invoice created for this proration'
    )
    
    credit_note_id = fields.Many2one(
        'account.move',
        string='Credit Note',
        ondelete='set null',
        help='Credit note created for this proration'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Additional Configuration
    include_taxes = fields.Boolean(
        string='Include Taxes',
        default=True,
        help='Include taxes in proration calculations'
    )
    
    round_to_cents = fields.Boolean(
        string='Round to Cents',
        default=True,
        help='Round final amounts to nearest cent'
    )
    
    minimum_charge = fields.Monetary(
        string='Minimum Charge',
        currency_field='currency_id',
        help='Minimum charge amount (if applicable)'
    )
    
    notes = fields.Text(
        string='Calculation Notes',
        help='Additional notes about the calculation'
    )
    
    # Computed Fields
    @api.depends('subscription_id', 'proration_type', 'effective_date')
    def _compute_display_name(self):
        """Compute display name"""
        for calc in self:
            if calc.subscription_id:
                calc.display_name = f"{calc.subscription_id.name} - {calc.proration_type.replace('_', ' ').title()} ({calc.effective_date})"
            else:
                calc.display_name = calc.name or 'New Proration Calculation'
    
    @api.depends('billing_period_start', 'billing_period_end', 'effective_date')
    def _compute_period_calculations(self):
        """Compute period-related calculations"""
        for calc in self:
            if calc.billing_period_start and calc.billing_period_end:
                # Total days in billing period
                total_delta = calc.billing_period_end - calc.billing_period_start
                calc.total_period_days = total_delta.days + 1  # Include both start and end days
                
                # Remaining days from effective date
                if calc.effective_date:
                    if calc.effective_date <= calc.billing_period_end:
                        remaining_delta = calc.billing_period_end - calc.effective_date
                        calc.remaining_days = max(0, remaining_delta.days + 1)
                    else:
                        calc.remaining_days = 0
                else:
                    calc.remaining_days = 0
            else:
                calc.total_period_days = 0
                calc.remaining_days = 0
    
    @api.depends('proration_method', 'total_period_days', 'remaining_days', 
                 'original_price', 'new_price', 'original_quantity', 'new_quantity', 'proration_type')
    def _compute_proration_amounts(self):
        """Compute proration amounts"""
        for calc in self:
            calc._calculate_proration()
    
    @api.depends('manual_override', 'credit_amount', 'charge_amount', 
                 'manual_credit_amount', 'manual_charge_amount')
    def _compute_final_amounts(self):
        """Compute final amounts considering manual overrides"""
        for calc in self:
            if calc.manual_override:
                calc.final_credit_amount = calc.manual_credit_amount or 0
                calc.final_charge_amount = calc.manual_charge_amount or 0
            else:
                calc.final_credit_amount = calc.credit_amount
                calc.final_charge_amount = calc.charge_amount
            
            calc.final_net_amount = calc.final_charge_amount - calc.final_credit_amount
    
    # Validation
    @api.constrains('billing_period_start', 'billing_period_end')
    def _check_billing_period(self):
        """Validate billing period"""
        for calc in self:
            if calc.billing_period_start and calc.billing_period_end:
                if calc.billing_period_end <= calc.billing_period_start:
                    raise ValidationError(_('Billing period end must be after start'))
    
    @api.constrains('effective_date', 'billing_period_start', 'billing_period_end')
    def _check_effective_date(self):
        """Validate effective date"""
        for calc in self:
            if calc.effective_date and calc.billing_period_start and calc.billing_period_end:
                if calc.effective_date < calc.billing_period_start:
                    raise ValidationError(_('Effective date cannot be before billing period start'))
    
    @api.constrains('original_quantity', 'new_quantity')
    def _check_quantities(self):
        """Validate quantities"""
        for calc in self:
            if calc.original_quantity < 0 or calc.new_quantity < 0:
                raise ValidationError(_('Quantities cannot be negative'))
    
    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create to auto-calculate proration"""
        for vals in vals_list:
            # Set billing period if not provided
            if 'subscription_id' in vals and not vals.get('billing_period_start'):
                subscription = self.env['ams.subscription'].browse(vals['subscription_id'])
                period = self._get_current_billing_period(subscription)
                vals.setdefault('billing_period_start', period['start'])
                vals.setdefault('billing_period_end', period['end'])
                vals.setdefault('billing_frequency', subscription.subscription_period)
        
        calcs = super().create(vals_list)
        
        # Auto-calculate on creation
        for calc in calcs:
            calc.action_calculate()
        
        return calcs
    
    def _get_current_billing_period(self, subscription):
        """Get current billing period for subscription"""
        today = fields.Date.today()
        
        if subscription.subscription_period == 'monthly':
            start = today.replace(day=1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        elif subscription.subscription_period == 'quarterly':
            quarter = ((today.month - 1) // 3) + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end = start + relativedelta(months=3) - timedelta(days=1)
        elif subscription.subscription_period == 'annual':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        else:
            # Default to monthly
            start = today.replace(day=1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        
        return {'start': start, 'end': end}
    
    # Actions
    def action_calculate(self):
        """Calculate proration amounts"""
        for calc in self:
            calc._calculate_proration()
            calc.state = 'calculated'
            calc.message_post(body=_('Proration calculated'))
    
    def action_approve(self):
        """Approve the proration calculation"""
        for calc in self:
            if calc.state != 'calculated':
                raise UserError(_('Only calculated prorations can be approved'))
            
            calc.state = 'approved'
            calc.message_post(body=_('Proration approved'))
    
    def action_apply(self):
        """Apply the proration (create invoices/credits)"""
        for calc in self:
            if calc.state != 'approved':
                raise UserError(_('Only approved prorations can be applied'))
            
            calc._apply_proration()
            calc.state = 'applied'
            calc.applied_date = fields.Date.today()
            calc.applied_by = self.env.user.id
            calc.message_post(body=_('Proration applied'))
    
    def action_cancel(self):
        """Cancel the proration calculation"""
        for calc in self:
            if calc.state == 'applied':
                raise UserError(_('Applied prorations cannot be cancelled'))
            
            calc.state = 'cancelled'
            calc.message_post(body=_('Proration cancelled'))
    
    def action_reset_to_draft(self):
        """Reset to draft for recalculation"""
        for calc in self:
            if calc.state == 'applied':
                raise UserError(_('Applied prorations cannot be reset'))
            
            calc.state = 'draft'
            calc.message_post(body=_('Proration reset to draft'))
    
    # Core Calculation Logic
    def _calculate_proration(self):
        """Main proration calculation logic"""
        self.ensure_one()
        
        if self.total_period_days == 0:
            self.proration_percentage = 0
            self.credit_amount = 0
            self.charge_amount = 0
            self.net_amount = 0
            return
        
        # Calculate proration percentage
        if self.proration_method == 'daily':
            self.proration_percentage = self.remaining_days / self.total_period_days
        elif self.proration_method == 'monthly':
            self.proration_percentage = self._calculate_monthly_proration()
        elif self.proration_method == 'percentage':
            # Use a fixed percentage (would be set manually)
            pass
        else:
            self.proration_percentage = self.remaining_days / self.total_period_days
        
        # Calculate amounts based on proration type
        if self.proration_type in ['upgrade', 'downgrade']:
            self._calculate_product_change_proration()
        elif self.proration_type in ['quantity_increase', 'quantity_decrease']:
            self._calculate_quantity_change_proration()
        elif self.proration_type in ['add_seats', 'remove_seats']:
            self._calculate_seat_change_proration()
        elif self.proration_type == 'mid_cycle_start':
            self._calculate_mid_cycle_start_proration()
        elif self.proration_type == 'early_termination':
            self._calculate_early_termination_proration()
        elif self.proration_type in ['suspension_credit', 'reactivation_charge']:
            self._calculate_suspension_proration()
        
        # Apply rounding if configured
        if self.round_to_cents:
            self.credit_amount = round(self.credit_amount, 2)
            self.charge_amount = round(self.charge_amount, 2)
        
        # Calculate net amount
        self.net_amount = self.charge_amount - self.credit_amount
        
        _logger.info(f'Proration calculated for {self.name}: Credit={self.credit_amount}, Charge={self.charge_amount}, Net={self.net_amount}')
    
    def _calculate_monthly_proration(self):
        """Calculate proration percentage for monthly method"""
        # This method prorates based on full months rather than days
        effective_month = self.effective_date.month
        period_end_month = self.billing_period_end.month
        
        if effective_month == period_end_month:
            # Same month - use daily proration
            return self.remaining_days / self.total_period_days
        else:
            # Different months - calculate month fractions
            months_remaining = period_end_month - effective_month + 1
            total_months = self._get_total_months_in_period()
            return months_remaining / total_months if total_months > 0 else 0
    
    def _get_total_months_in_period(self):
        """Get total months in billing period"""
        if self.billing_frequency == 'monthly':
            return 1
        elif self.billing_frequency == 'quarterly':
            return 3
        elif self.billing_frequency == 'semi_annual':
            return 6
        elif self.billing_frequency == 'annual':
            return 12
        else:
            return 1
    
    def _calculate_product_change_proration(self):
        """Calculate proration for product upgrades/downgrades"""
        price_difference = (self.new_price or 0) - self.original_price
        
        if self.proration_type == 'upgrade' and price_difference > 0:
            # Charge prorated difference for upgrade
            self.charge_amount = price_difference * self.proration_percentage * self.original_quantity
            self.credit_amount = 0
        elif self.proration_type == 'downgrade' and price_difference < 0:
            # Credit prorated difference for downgrade
            self.credit_amount = abs(price_difference) * self.proration_percentage * self.original_quantity
            self.charge_amount = 0
        else:
            # No price difference or wrong type
            self.charge_amount = 0
            self.credit_amount = 0
    
    def _calculate_quantity_change_proration(self):
        """Calculate proration for quantity changes"""
        quantity_difference = self.new_quantity - self.original_quantity
        
        if self.proration_type == 'quantity_increase' and quantity_difference > 0:
            # Charge prorated amount for additional quantity
            self.charge_amount = self.original_price * quantity_difference * self.proration_percentage
            self.credit_amount = 0
        elif self.proration_type == 'quantity_decrease' and quantity_difference < 0:
            # Credit prorated amount for reduced quantity
            self.credit_amount = self.original_price * abs(quantity_difference) * self.proration_percentage
            self.charge_amount = 0
        else:
            self.charge_amount = 0
            self.credit_amount = 0
    
    def _calculate_seat_change_proration(self):
        """Calculate proration for enterprise seat changes"""
        # Similar to quantity change but may have different pricing logic
        self._calculate_quantity_change_proration()
    
    def _calculate_mid_cycle_start_proration(self):
        """Calculate proration for mid-cycle subscription start"""
        # Charge prorated amount for remaining period
        self.charge_amount = self.original_price * self.proration_percentage * self.original_quantity
        self.credit_amount = 0
    
    def _calculate_early_termination_proration(self):
        """Calculate proration for early termination"""
        # Credit remaining amount for early termination
        self.credit_amount = self.original_price * self.proration_percentage * self.original_quantity
        self.charge_amount = 0
    
    def _calculate_suspension_proration(self):
        """Calculate proration for suspension/reactivation"""
        if self.proration_type == 'suspension_credit':
            # Credit for suspension period
            self.credit_amount = self.original_price * self.proration_percentage * self.original_quantity
            self.charge_amount = 0
        elif self.proration_type == 'reactivation_charge':
            # Charge for reactivation (if applicable)
            self.charge_amount = self.original_price * self.proration_percentage * self.original_quantity
            self.credit_amount = 0
    
    # Application Logic
    def _apply_proration(self):
        """Apply the proration by creating invoices/credits"""
        self.ensure_one()
        
        # Create invoice for charges
        if self.final_charge_amount > 0:
            self._create_proration_invoice()
        
        # Create credit note for credits
        if self.final_credit_amount > 0:
            self._create_proration_credit()
    
    def _create_proration_invoice(self):
        """Create invoice for proration charges"""
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.calculation_date,
            'ref': f'Proration: {self.display_name}',
            'narration': self.description or f'Proration charge for {self.proration_type}',
            'invoice_line_ids': [(0, 0, {
                'name': f'Proration Charge - {self.proration_type.replace("_", " ").title()}',
                'quantity': 1,
                'price_unit': self.final_charge_amount,
                'product_id': self.new_product_id.id if self.new_product_id else self.original_product_id.id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        self.invoice_id = invoice.id
        return invoice
    
    def _create_proration_credit(self):
        """Create credit note for proration credits"""
        credit_vals = {
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'invoice_date': self.calculation_date,
            'ref': f'Proration Credit: {self.display_name}',
            'narration': self.description or f'Proration credit for {self.proration_type}',
            'invoice_line_ids': [(0, 0, {
                'name': f'Proration Credit - {self.proration_type.replace("_", " ").title()}',
                'quantity': 1,
                'price_unit': self.final_credit_amount,
                'product_id': self.original_product_id.id,
            })]
        }
        
        credit = self.env['account.move'].create(credit_vals)
        credit.action_post()
        
        self.credit_note_id = credit.id
        return credit
    
    # Utility Methods
    def action_view_invoice(self):
        """View proration invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No invoice created for this proration'))
        
        return {
            'name': _('Proration Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_credit_note(self):
        """View proration credit note"""
        self.ensure_one()
        
        if not self.credit_note_id:
            raise UserError(_('No credit note created for this proration'))
        
        return {
            'name': _('Proration Credit Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.credit_note_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def get_proration_summary(self):
        """Get summary of proration calculation"""
        self.ensure_one()
        
        return {
            'calculation_id': self.id,
            'calculation_name': self.display_name,
            'subscription_name': self.subscription_id.name,
            'customer_name': self.partner_id.name,
            'proration_type': self.proration_type,
            'effective_date': self.effective_date,
            'proration_percentage': self.proration_percentage,
            'final_credit_amount': self.final_credit_amount,
            'final_charge_amount': self.final_charge_amount,
            'final_net_amount': self.final_net_amount,
            'state': self.state,
            'applied_date': self.applied_date,
        }
    
    # Class Methods for Common Calculations
    @api.model
    def calculate_upgrade_proration(self, subscription, new_product, effective_date=None):
        """Helper method to calculate upgrade proration"""
        if not effective_date:
            effective_date = fields.Date.today()
        
        return self.create({
            'subscription_id': subscription.id,
            'original_product_id': subscription.product_id.id,
            'new_product_id': new_product.id,
            'proration_type': 'upgrade',
            'effective_date': effective_date,
            'original_price': subscription.price,
            'new_price': new_product.list_price,
            'original_quantity': 1,
            'new_quantity': 1,
        })
    
    @api.model
    def calculate_seat_addition_proration(self, subscription, additional_seats, effective_date=None):
        """Helper method to calculate seat addition proration"""
        if not effective_date:
            effective_date = fields.Date.today()
        
        return self.create({
            'subscription_id': subscription.id,
            'original_product_id': subscription.product_id.id,
            'proration_type': 'add_seats',
            'effective_date': effective_date,
            'original_price': subscription.price,
            'original_quantity': subscription.quantity or 1,
            'new_quantity': (subscription.quantity or 1) + additional_seats,
        })