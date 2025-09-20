# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class MembershipRenewalWizard(models.TransientModel):
    _name = 'membership.renewal.wizard'
    _description = 'Membership Renewal Wizard'

    # Membership being renewed
    membership_id = fields.Many2one(
        'membership.membership',
        string='Membership',
        required=True,
        readonly=True,
        help='Membership to renew'
    )
    
    partner_id = fields.Many2one(
        related='membership_id.partner_id',
        string='Member',
        readonly=True
    )
    
    membership_type_id = fields.Many2one(
        related='membership_id.membership_type_id',
        string='Membership Type',
        readonly=True
    )
    
    current_state = fields.Selection(
        related='membership_id.state',
        string='Current Status',
        readonly=True
    )
    
    current_end_date = fields.Date(
        related='membership_id.end_date',
        string='Current End Date',
        readonly=True
    )
    
    # Renewal configuration
    renewal_type = fields.Selection([
        ('standard', 'Standard Renewal'),
        ('custom_period', 'Custom Period'),
        ('custom_date', 'Custom End Date'),
        ('lifetime', 'Convert to Lifetime')
    ], string='Renewal Type',
       default='standard',
       required=True,
       help='Type of renewal to perform')
    
    renewal_months = fields.Integer(
        string='Renewal Period (Months)',
        default=12,
        help='Number of months to extend the membership'
    )
    
    new_end_date = fields.Date(
        string='New End Date',
        compute='_compute_new_end_date',
        store=True,
        readonly=False,
        help='Calculated new end date for the membership'
    )
    
    custom_end_date = fields.Date(
        string='Custom End Date',
        help='Custom end date when using custom date renewal'
    )
    
    # Pricing information
    base_price = fields.Float(
        related='membership_type_id.price',
        string='Base Price',
        readonly=True
    )
    
    renewal_price = fields.Float(
        string='Renewal Price',
        compute='_compute_renewal_price',
        store=True,
        readonly=False,
        help='Price for this renewal'
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        default=0.0,
        help='Discount to apply to renewal price'
    )
    
    final_price = fields.Float(
        string='Final Price',
        compute='_compute_final_price',
        store=True,
        help='Final price after discounts'
    )
    
    currency_id = fields.Many2one(
        related='membership_type_id.currency_id',
        readonly=True
    )
    
    # Payment information
    payment_received = fields.Boolean(
        string='Payment Received',
        default=False,
        help='Check if payment has been received'
    )
    
    amount_paid = fields.Float(
        string='Amount Paid',
        default=0.0,
        help='Amount actually paid for this renewal'
    )
    
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('online', 'Online Payment'),
        ('other', 'Other')
    ], string='Payment Method',
       help='Method used for payment')
    
    payment_reference = fields.Char(
        string='Payment Reference',
        help='Reference number for payment (check number, transaction ID, etc.)'
    )
    
    # Renewal options
    send_confirmation_email = fields.Boolean(
        string='Send Confirmation Email',
        default=True,
        help='Send email confirmation after renewal'
    )
    
    reset_grace_period = fields.Boolean(
        string='Reset Grace Period Settings',
        default=True,
        help='Reset grace period flags for renewed membership'
    )
    
    notes = fields.Text(
        string='Renewal Notes',
        help='Additional notes about this renewal'
    )
    
    # Validation and information
    days_since_expiry = fields.Integer(
        string='Days Since Expiry',
        compute='_compute_expiry_info',
        help='Number of days since membership expired (negative if not expired)'
    )
    
    is_early_renewal = fields.Boolean(
        string='Early Renewal',
        compute='_compute_expiry_info',
        help='True if renewing before expiry date'
    )
    
    renewal_warning = fields.Text(
        string='Renewal Warning',
        compute='_compute_renewal_warning',
        help='Warning messages about this renewal'
    )
    
    can_renew = fields.Boolean(
        string='Can Renew',
        compute='_compute_can_renew',
        help='True if membership can be renewed'
    )
    
    @api.depends('renewal_type', 'renewal_months', 'custom_end_date', 'current_end_date')
    def _compute_new_end_date(self):
        for wizard in self:
            if wizard.renewal_type == 'lifetime':
                wizard.new_end_date = False
            elif wizard.renewal_type == 'custom_date':
                wizard.new_end_date = wizard.custom_end_date
            elif wizard.renewal_type in ['standard', 'custom_period']:
                months = wizard.renewal_months if wizard.renewal_type == 'custom_period' else wizard.membership_type_id.duration
                if wizard.current_end_date and wizard.current_end_date >= fields.Date.today():
                    # Extend from current end date if not expired
                    wizard.new_end_date = wizard.current_end_date + relativedelta(months=months)
                else:
                    # Start from today if expired
                    wizard.new_end_date = fields.Date.today() + relativedelta(months=months)
            else:
                wizard.new_end_date = False
    
    @api.depends('renewal_type', 'base_price', 'renewal_months')
    def _compute_renewal_price(self):
        for wizard in self:
            if wizard.renewal_type == 'lifetime':
                # Lifetime conversion price could be different
                wizard.renewal_price = wizard.base_price * 10  # Example: 10x regular price
            elif wizard.renewal_type == 'custom_period':
                # Prorate based on months
                standard_months = wizard.membership_type_id.duration or 12
                wizard.renewal_price = wizard.base_price * (wizard.renewal_months / standard_months)
            else:
                wizard.renewal_price = wizard.base_price
    
    @api.depends('renewal_price', 'discount_amount')
    def _compute_final_price(self):
        for wizard in self:
            wizard.final_price = max(0, wizard.renewal_price - wizard.discount_amount)
    
    @api.depends('current_end_date')
    def _compute_expiry_info(self):
        for wizard in self:
            if wizard.current_end_date:
                today = fields.Date.today()
                delta = (today - wizard.current_end_date).days
                wizard.days_since_expiry = delta
                wizard.is_early_renewal = delta < 0
            else:
                wizard.days_since_expiry = 0
                wizard.is_early_renewal = False
    
    @api.depends('current_state', 'days_since_expiry', 'renewal_type', 'new_end_date')
    def _compute_renewal_warning(self):
        for wizard in self:
            warnings = []
            
            if wizard.current_state == 'cancelled':
                warnings.append("This membership is cancelled. Renewal will reactivate it.")
            
            if wizard.current_state == 'terminated':
                warnings.append("This membership is terminated. Consider creating a new membership instead.")
            
            if wizard.is_early_renewal and wizard.days_since_expiry < -30:
                warnings.append(f"Early renewal: membership doesn't expire for {abs(wizard.days_since_expiry)} days.")
            
            if wizard.days_since_expiry > 365:
                warnings.append("Membership expired over a year ago. Consider creating a new membership.")
            
            if wizard.renewal_type == 'custom_date' and wizard.new_end_date:
                if wizard.new_end_date <= fields.Date.today():
                    warnings.append("Custom end date is in the past or today.")
            
            wizard.renewal_warning = "\n".join(warnings) if warnings else ""
    
    @api.depends('current_state')
    def _compute_can_renew(self):
        for wizard in self:
            # Allow renewal for most states except terminated (with warning)
            wizard.can_renew = wizard.current_state in ['active', 'grace', 'suspended', 'cancelled', 'terminated']
    
    @api.onchange('renewal_type')
    def _onchange_renewal_type(self):
        """Reset dependent fields when renewal type changes"""
        if self.renewal_type == 'standard':
            self.renewal_months = self.membership_type_id.duration or 12
        elif self.renewal_type == 'custom_period':
            self.renewal_months = 12
        elif self.renewal_type == 'custom_date':
            self.custom_end_date = False
    
    @api.onchange('payment_received')
    def _onchange_payment_received(self):
        """Auto-fill amount paid when payment received is checked"""
        if self.payment_received and not self.amount_paid:
            self.amount_paid = self.final_price
    
    def action_preview_renewal(self):
        """Preview the renewal without executing it"""
        self.ensure_one()
        
        preview_info = {
            'current_end_date': self.current_end_date,
            'new_end_date': self.new_end_date,
            'renewal_price': self.renewal_price,
            'final_price': self.final_price,
            'extension_days': (self.new_end_date - (self.current_end_date or fields.Date.today())).days if self.new_end_date else 0
        }
        
        message = f"""
Renewal Preview:
- Current End Date: {self.current_end_date or 'N/A'}
- New End Date: {self.new_end_date or 'Lifetime'}
- Extension: {preview_info['extension_days']} days
- Price: {self.final_price} {self.currency_id.symbol}
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Renewal Preview',
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_renew_membership(self):
        """Execute the membership renewal"""
        self.ensure_one()
        
        if not self.can_renew:
            raise ValidationError(_("This membership cannot be renewed in its current state."))
        
        # Validate payment if required
        if self.final_price > 0 and not self.payment_received:
            raise ValidationError(_("Payment must be received before processing renewal."))
        
        if self.payment_received and self.amount_paid < self.final_price:
            if not self.env.user.has_group('membership_core.group_membership_manager'):
                raise ValidationError(_("Payment amount is less than the renewal price. Only managers can approve partial payments."))
        
        # Perform the renewal
        membership = self.membership_id
        
        # Prepare renewal data
        renewal_data = {
            'new_end_date': self.new_end_date,
            'amount_paid': self.amount_paid
        }
        
        # Handle different renewal types
        if self.renewal_type == 'lifetime':
            # Convert to lifetime by clearing end date
            membership.write({
                'end_date': False,
                'state': 'active',
                'amount_paid': membership.amount_paid + self.amount_paid,
                'grace_end_date': False,
                'suspension_end_date': False,
                'renewal_reminder_sent': False
            })
        else:
            # Standard renewal
            membership.action_renew(
                new_end_date=self.new_end_date,
                amount_paid=self.amount_paid
            )
        
        # Add renewal notes
        if self.notes:
            membership.message_post(
                body=_("Renewal processed: %s") % self.notes,
                message_type='comment'
            )
        
        # Record payment information
        if self.payment_received:
            payment_note = f"Payment received: {self.amount_paid} {self.currency_id.symbol}"
            if self.payment_method:
                payment_note += f" via {dict(self._fields['payment_method'].selection)[self.payment_method]}"
            if self.payment_reference:
                payment_note += f" (Ref: {self.payment_reference})"
            
            membership.message_post(
                body=payment_note,
                message_type='comment'
            )
        
        # Send confirmation email
        if (self.send_confirmation_email and 
            membership.membership_type_id.welcome_template_id):
            try:
                membership.membership_type_id.welcome_template_id.send_mail(membership.id)
            except Exception as e:
                # Log warning but don't fail
                _logger.warning(f"Failed to send renewal confirmation email: {str(e)}")
        
        # Return to membership form
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Renewed'),
            'res_model': 'membership.membership',
            'res_id': membership.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def action_create_invoice(self):
        """Create an invoice for the renewal"""
        self.ensure_one()
        
        if not self.final_price:
            raise ValidationError(_("Cannot create invoice with zero amount."))
        
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f'Membership Renewal - {self.membership_type_id.name}',
                'quantity': 1.0,
                'price_unit': self.final_price,
                'membership_type_id': self.membership_type_id.id,
                'membership_id': self.membership_id.id,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Link invoice to membership
        self.membership_id.invoice_ids = [(4, invoice.id)]
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current'
        }


class MembershipBulkRenewalWizard(models.TransientModel):
    _name = 'membership.bulk.renewal.wizard'
    _description = 'Bulk Membership Renewal Wizard'
    
    # Selection criteria
    membership_type_ids = fields.Many2many(
        'membership.type',
        string='Membership Types',
        help='Limit to specific membership types'
    )
    
    expiry_date_from = fields.Date(
        string='Expiry Date From',
        help='Include memberships expiring from this date'
    )
    
    expiry_date_to = fields.Date(
        string='Expiry Date To',
        help='Include memberships expiring until this date'
    )
    
    include_states = fields.Selection([
        ('active_grace', 'Active and Grace Period'),
        ('all_renewable', 'All Renewable States'),
        ('custom', 'Custom Selection')
    ], string='Include States',
       default='active_grace',
       required=True)
    
    custom_states = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended')
    ], string='Custom States')
    
    # Renewal settings
    renewal_months = fields.Integer(
        string='Renewal Period (Months)',
        default=12,
        required=True
    )
    
    auto_process = fields.Boolean(
        string='Auto-Process Renewals',
        default=False,
        help='Automatically process renewals without confirmation'
    )
    
    # Results
    membership_count = fields.Integer(
        string='Matching Memberships',
        compute='_compute_membership_count'
    )
    
    selected_membership_ids = fields.Many2many(
        'membership.membership',
        string='Selected Memberships',
        compute='_compute_selected_memberships'
    )
    
    @api.depends('membership_type_ids', 'expiry_date_from', 'expiry_date_to', 'include_states', 'custom_states')
    def _compute_selected_memberships(self):
        for wizard in self:
            domain = []
            
            if wizard.membership_type_ids:
                domain.append(('membership_type_id', 'in', wizard.membership_type_ids.ids))
            
            if wizard.expiry_date_from:
                domain.append(('end_date', '>=', wizard.expiry_date_from))
            
            if wizard.expiry_date_to:
                domain.append(('end_date', '<=', wizard.expiry_date_to))
            
            if wizard.include_states == 'active_grace':
                domain.append(('state', 'in', ['active', 'grace']))
            elif wizard.include_states == 'all_renewable':
                domain.append(('state', 'in', ['active', 'grace', 'suspended']))
            elif wizard.include_states == 'custom' and wizard.custom_states:
                domain.append(('state', '=', wizard.custom_states))
            
            wizard.selected_membership_ids = self.env['membership.membership'].search(domain)
    
    @api.depends('selected_membership_ids')
    def _compute_membership_count(self):
        for wizard in self:
            wizard.membership_count = len(wizard.selected_membership_ids)
    
    def action_preview_bulk_renewal(self):
        """Preview memberships that would be renewed"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships to Renew'),
            'res_model': 'membership.membership',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.selected_membership_ids.ids)],
            'target': 'new'
        }
    
    def action_process_bulk_renewal(self):
        """Process bulk renewals"""
        self.ensure_one()
        
        if not self.selected_membership_ids:
            raise ValidationError(_("No memberships selected for renewal."))
        
        success_count = 0
        error_count = 0
        errors = []
        
        for membership in self.selected_membership_ids:
            try:
                new_end_date = membership.end_date + relativedelta(months=self.renewal_months) if membership.end_date else fields.Date.today() + relativedelta(months=self.renewal_months)
                membership.action_renew(new_end_date=new_end_date)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"{membership.name}: {str(e)}")
        
        # Show results
        message = f"Bulk renewal completed:\n- Successful: {success_count}\n- Errors: {error_count}"
        if errors:
            message += f"\n\nErrors:\n" + "\n".join(errors[:10])  # Show first 10 errors
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Renewal Results',
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            }
        }