# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionUpgradeWizard(models.TransientModel):
    """Wizard for Upgrading/Downgrading Subscriptions with Proration"""
    _name = 'ams.subscription.upgrade.wizard'
    _description = 'AMS Subscription Upgrade/Downgrade Wizard'
    
    # =============================================================================
    # BASIC INFORMATION
    # =============================================================================
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Current Subscription',
        required=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='subscription_id.partner_id',
        string='Customer',
        readonly=True
    )
    
    change_type = fields.Selection([
        ('upgrade', 'Upgrade Product'),
        ('downgrade', 'Downgrade Product'),
        ('add_seats', 'Add Seats'),
        ('remove_seats', 'Remove Seats'),
        ('change_plan', 'Change Billing Plan'),
        ('modify_features', 'Modify Features'),
    ], string='Change Type', required=True, default='upgrade')
    
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        help='Date when the change takes effect'
    )
    
    # =============================================================================
    # CURRENT SUBSCRIPTION DETAILS
    # =============================================================================
    
    current_product_id = fields.Many2one(
        'product.product',
        related='subscription_id.product_id',
        string='Current Product',
        readonly=True
    )
    
    current_price = fields.Monetary(
        string='Current Price',
        related='subscription_id.price',
        currency_field='currency_id',
        readonly=True
    )
    
    current_quantity = fields.Float(
        string='Current Quantity/Seats',
        related='subscription_id.quantity',
        readonly=True
    )
    
    current_billing_frequency = fields.Selection(
        related='subscription_id.subscription_period',
        string='Current Billing Frequency',
        readonly=True
    )
    
    # =============================================================================
    # NEW SUBSCRIPTION DETAILS
    # =============================================================================
    
    new_product_id = fields.Many2one(
        'product.product',
        string='New Product',
        help='New product for upgrade/downgrade'
    )
    
    new_price = fields.Monetary(
        string='New Price',
        currency_field='currency_id',
        help='New price (auto-filled from product)'
    )
    
    new_quantity = fields.Float(
        string='New Quantity/Seats',
        default=1.0,
        help='New quantity/number of seats'
    )
    
    new_billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='New Billing Frequency',
    help='New billing frequency (if changing plan)')
    
    # Additional Features/Add-ons
    feature_change_ids = fields.One2many(
        'ams.subscription.feature.change',
        'upgrade_wizard_id',
        string='Feature Changes'
    )
    
    # =============================================================================
    # PRICING AND CALCULATION
    # =============================================================================
    
    price_difference = fields.Monetary(
        string='Price Difference',
        currency_field='currency_id',
        compute='_compute_pricing_info',
        store=True,
        help='Difference between new and current price'
    )
    
    is_upgrade = fields.Boolean(
        string='Is Upgrade',
        compute='_compute_pricing_info',
        store=True,
        help='True if new price is higher than current'
    )
    
    quantity_difference = fields.Float(
        string='Quantity Difference',
        compute='_compute_pricing_info',
        store=True,
        help='Difference in quantity/seats'
    )
    
    # =============================================================================
    # PRORATION CONFIGURATION
    # =============================================================================
    
    enable_proration = fields.Boolean(
        string='Enable Proration',
        default=True,
        help='Calculate proration for mid-cycle changes'
    )
    
    proration_method = fields.Selection([
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('percentage', 'Percentage Based'),
        ('none', 'No Proration'),
    ], string='Proration Method', default='daily')
    
    # Current Billing Period
    current_billing_period_start = fields.Date(
        string='Current Period Start',
        compute='_compute_billing_period',
        store=True
    )
    
    current_billing_period_end = fields.Date(
        string='Current Period End',
        compute='_compute_billing_period',
        store=True
    )
    
    # Proration Calculation Results
    proration_preview_generated = fields.Boolean(
        string='Proration Preview Generated',
        default=False
    )
    
    proration_credit_amount = fields.Monetary(
        string='Proration Credit',
        currency_field='currency_id',
        readonly=True,
        help='Credit amount for unused portion'
    )
    
    proration_charge_amount = fields.Monetary(
        string='Proration Charge',
        currency_field='currency_id',
        readonly=True,
        help='Additional charge for upgrade'
    )
    
    net_proration_amount = fields.Monetary(
        string='Net Proration Amount',
        currency_field='currency_id',
        readonly=True,
        help='Net amount (positive = charge, negative = credit)'
    )
    
    # =============================================================================
    # PAYMENT AND BILLING
    # =============================================================================
    
    immediate_billing = fields.Boolean(
        string='Bill Immediately',
        default=True,
        help='Create invoice immediately for proration'
    )
    
    payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Payment Method',
        help='Payment method for immediate billing'
    )
    
    auto_payment = fields.Boolean(
        string='Process Payment Automatically',
        default=False,
        help='Automatically process payment for proration'
    )
    
    # =============================================================================
    # CUSTOMER COMMUNICATION
    # =============================================================================
    
    send_notification = fields.Boolean(
        string='Send Customer Notification',
        default=True,
        help='Send email notification to customer'
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Notification Template',
        domain="[('model', '=', 'ams.subscription')]"
    )
    
    custom_message = fields.Text(
        string='Custom Message',
        help='Additional message to include in notification'
    )
    
    # =============================================================================
    # PREVIEW AND CONFIRMATION
    # =============================================================================
    
    preview_summary = fields.Text(
        string='Change Summary',
        readonly=True,
        help='Summary of all changes'
    )
    
    confirmation_required = fields.Boolean(
        string='Requires Confirmation',
        default=True,
        help='Change requires customer confirmation'
    )
    
    customer_confirmed = fields.Boolean(
        string='Customer Confirmed',
        help='Customer has confirmed the change'
    )
    
    terms_accepted = fields.Boolean(
        string='Terms Accepted',
        help='Customer has accepted new terms'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='subscription_id.currency_id',
        readonly=True
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    @api.depends('current_price', 'new_price', 'current_quantity', 'new_quantity', 'change_type')
    def _compute_pricing_info(self):
        """Compute pricing information"""
        for wizard in self:
            if wizard.change_type in ['upgrade', 'downgrade']:
                wizard.price_difference = (wizard.new_price or 0) - wizard.current_price
                wizard.is_upgrade = wizard.price_difference > 0
                wizard.quantity_difference = 0
            elif wizard.change_type in ['add_seats', 'remove_seats']:
                wizard.quantity_difference = wizard.new_quantity - (wizard.current_quantity or 1)
                wizard.price_difference = wizard.current_price * wizard.quantity_difference
                wizard.is_upgrade = wizard.quantity_difference > 0
            else:
                wizard.price_difference = 0
                wizard.quantity_difference = 0
                wizard.is_upgrade = False
    
    @api.depends('subscription_id', 'effective_date')
    def _compute_billing_period(self):
        """Compute current billing period"""
        for wizard in self:
            if wizard.subscription_id:
                period = wizard._calculate_current_billing_period()
                wizard.current_billing_period_start = period['start']
                wizard.current_billing_period_end = period['end']
            else:
                wizard.current_billing_period_start = False
                wizard.current_billing_period_end = False
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('new_product_id')
    def _onchange_new_product_id(self):
        """Update price when product changes"""
        if self.new_product_id:
            self.new_price = self.new_product_id.list_price
            
            # Set default quantity based on product type
            if hasattr(self.new_product_id.product_tmpl_id, 'ams_product_type'):
                product_type = self.new_product_id.product_tmpl_id.ams_product_type
                if product_type == 'enterprise':
                    self.new_quantity = max(1, self.current_quantity or 1)
                else:
                    self.new_quantity = 1
    
    @api.onchange('change_type')
    def _onchange_change_type(self):
        """Adjust fields based on change type"""
        if self.change_type in ['add_seats', 'remove_seats']:
            self.new_product_id = self.current_product_id
            self.new_price = self.current_price
            if self.change_type == 'add_seats':
                self.new_quantity = (self.current_quantity or 1) + 1
            else:
                self.new_quantity = max(1, (self.current_quantity or 1) - 1)
        elif self.change_type == 'change_plan':
            self.new_product_id = self.current_product_id
            self.new_price = self.current_price
            self.new_quantity = self.current_quantity
        
        # Clear proration preview
        self.proration_preview_generated = False
        self._clear_proration_amounts()
    
    @api.onchange('enable_proration', 'proration_method', 'effective_date')
    def _onchange_proration_settings(self):
        """Clear proration preview when settings change"""
        self.proration_preview_generated = False
        self._clear_proration_amounts()
    
    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Load payment method from subscription"""
        if self.subscription_id:
            self.payment_method_id = self.subscription_id.payment_method_id
            self.auto_payment = self.subscription_id.enable_auto_payment
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('new_quantity')
    def _check_new_quantity(self):
        """Validate new quantity"""
        for wizard in self:
            if wizard.new_quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero'))
    
    @api.constrains('effective_date')
    def _check_effective_date(self):
        """Validate effective date"""
        for wizard in self:
            if wizard.effective_date < fields.Date.today():
                raise ValidationError(_('Effective date cannot be in the past'))
    
    @api.constrains('change_type', 'new_product_id')
    def _check_product_change(self):
        """Validate product changes"""
        for wizard in self:
            if wizard.change_type in ['upgrade', 'downgrade'] and not wizard.new_product_id:
                raise ValidationError(_('New product is required for product changes'))
            
            if (wizard.change_type == 'upgrade' and 
                wizard.new_product_id and 
                wizard.new_price <= wizard.current_price):
                raise ValidationError(_('Upgrade must result in higher price'))
            
            if (wizard.change_type == 'downgrade' and 
                wizard.new_product_id and 
                wizard.new_price >= wizard.current_price):
                raise ValidationError(_('Downgrade must result in lower price'))
    
    # =============================================================================
    # PRORATION CALCULATION
    # =============================================================================
    
    def action_calculate_proration(self):
        """Calculate proration amounts"""
        self.ensure_one()
        
        if not self.enable_proration:
            self._clear_proration_amounts()
            self.proration_preview_generated = True
            return
        
        # Calculate proration
        proration_result = self._calculate_proration_amounts()
        
        # Update fields
        self.proration_credit_amount = proration_result.get('credit_amount', 0)
        self.proration_charge_amount = proration_result.get('charge_amount', 0)
        self.net_proration_amount = self.proration_charge_amount - self.proration_credit_amount
        self.proration_preview_generated = True
        
        # Generate summary
        self._generate_preview_summary()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Proration calculated successfully'),
                'type': 'success',
            }
        }
    
    def _calculate_proration_amounts(self):
        """Calculate proration amounts based on change type"""
        result = {'credit_amount': 0, 'charge_amount': 0}
        
        if not self.enable_proration:
            return result
        
        # Get billing period info
        period_info = self._get_proration_period_info()
        if not period_info:
            return result
        
        proration_percentage = period_info['proration_percentage']
        
        if self.change_type in ['upgrade', 'downgrade']:
            result = self._calculate_product_change_proration(proration_percentage)
        elif self.change_type in ['add_seats', 'remove_seats']:
            result = self._calculate_quantity_change_proration(proration_percentage)
        elif self.change_type == 'change_plan':
            result = self._calculate_plan_change_proration(proration_percentage)
        
        return result
    
    def _calculate_product_change_proration(self, proration_percentage):
        """Calculate proration for product upgrade/downgrade"""
        price_diff = self.price_difference
        quantity = self.current_quantity or 1
        
        if self.change_type == 'upgrade' and price_diff > 0:
            # Charge prorated difference for upgrade
            charge_amount = price_diff * quantity * proration_percentage
            return {'credit_amount': 0, 'charge_amount': charge_amount}
        elif self.change_type == 'downgrade' and price_diff < 0:
            # Credit prorated difference for downgrade
            credit_amount = abs(price_diff) * quantity * proration_percentage
            return {'credit_amount': credit_amount, 'charge_amount': 0}
        
        return {'credit_amount': 0, 'charge_amount': 0}
    
    def _calculate_quantity_change_proration(self, proration_percentage):
        """Calculate proration for quantity/seat changes"""
        quantity_diff = self.quantity_difference
        price = self.current_price
        
        if self.change_type == 'add_seats' and quantity_diff > 0:
            # Charge prorated amount for additional seats
            charge_amount = price * quantity_diff * proration_percentage
            return {'credit_amount': 0, 'charge_amount': charge_amount}
        elif self.change_type == 'remove_seats' and quantity_diff < 0:
            # Credit prorated amount for removed seats
            credit_amount = price * abs(quantity_diff) * proration_percentage
            return {'credit_amount': credit_amount, 'charge_amount': 0}
        
        return {'credit_amount': 0, 'charge_amount': 0}
    
    def _calculate_plan_change_proration(self, proration_percentage):
        """Calculate proration for billing plan changes"""
        # This would handle changes in billing frequency
        # Complex calculation based on new vs old billing cycles
        # For now, return no proration
        return {'credit_amount': 0, 'charge_amount': 0}
    
    def _get_proration_period_info(self):
        """Get proration period information"""
        if not self.current_billing_period_start or not self.current_billing_period_end:
            return None
        
        total_days = (self.current_billing_period_end - self.current_billing_period_start).days + 1
        remaining_days = (self.current_billing_period_end - self.effective_date).days + 1
        
        if remaining_days <= 0:
            proration_percentage = 0
        else:
            if self.proration_method == 'daily':
                proration_percentage = remaining_days / total_days
            elif self.proration_method == 'monthly':
                # Calculate based on months remaining
                proration_percentage = self._calculate_monthly_proration()
            else:
                proration_percentage = remaining_days / total_days
        
        return {
            'total_days': total_days,
            'remaining_days': remaining_days,
            'proration_percentage': max(0, proration_percentage)
        }
    
    def _calculate_monthly_proration(self):
        """Calculate monthly-based proration percentage"""
        # This would implement monthly proration logic
        # For now, fall back to daily
        total_days = (self.current_billing_period_end - self.current_billing_period_start).days + 1
        remaining_days = (self.current_billing_period_end - self.effective_date).days + 1
        return remaining_days / total_days if total_days > 0 else 0
    
    def _calculate_current_billing_period(self):
        """Calculate current billing period dates"""
        subscription = self.subscription_id
        today = self.effective_date or fields.Date.today()
        
        if subscription.subscription_period == 'monthly':
            start = today.replace(day=1)
            end = start + timedelta(days=32)
            end = end.replace(day=1) - timedelta(days=1)
        elif subscription.subscription_period == 'quarterly':
            quarter = ((today.month - 1) // 3) + 1
            start = today.replace(month=(quarter - 1) * 3 + 1, day=1)
            end = start + timedelta(days=93)
            end = end.replace(day=1) - timedelta(days=1)
        elif subscription.subscription_period == 'annual':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        else:
            # Default to monthly
            start = today.replace(day=1)
            end = start + timedelta(days=32)
            end = end.replace(day=1) - timedelta(days=1)
        
        return {'start': start, 'end': end}
    
    # =============================================================================
    # PREVIEW AND SUMMARY
    # =============================================================================
    
    def _generate_preview_summary(self):
        """Generate preview summary of changes"""
        summary_lines = []
        
        # Header
        summary_lines.append(f"=== SUBSCRIPTION CHANGE SUMMARY ===")
        summary_lines.append(f"Customer: {self.partner_id.name}")
        summary_lines.append(f"Subscription: {self.subscription_id.name}")
        summary_lines.append(f"Change Type: {self.change_type.replace('_', ' ').title()}")
        summary_lines.append(f"Effective Date: {self.effective_date}")
        summary_lines.append("")
        
        # Current vs New
        summary_lines.append("CURRENT → NEW:")
        if self.change_type in ['upgrade', 'downgrade']:
            summary_lines.append(f"Product: {self.current_product_id.name} → {self.new_product_id.name}")
            summary_lines.append(f"Price: {self.current_price:.2f} → {self.new_price:.2f}")
        elif self.change_type in ['add_seats', 'remove_seats']:
            summary_lines.append(f"Seats: {self.current_quantity:.0f} → {self.new_quantity:.0f}")
            summary_lines.append(f"Total Price: {self.current_price * (self.current_quantity or 1):.2f} → {self.new_price * self.new_quantity:.2f}")
        
        # Proration details
        if self.enable_proration and self.proration_preview_generated:
            summary_lines.append("")
            summary_lines.append("PRORATION DETAILS:")
            summary_lines.append(f"Billing Period: {self.current_billing_period_start} to {self.current_billing_period_end}")
            
            if self.proration_credit_amount > 0:
                summary_lines.append(f"Credit Amount: {self.proration_credit_amount:.2f}")
            if self.proration_charge_amount > 0:
                summary_lines.append(f"Charge Amount: {self.proration_charge_amount:.2f}")
            
            if self.net_proration_amount != 0:
                if self.net_proration_amount > 0:
                    summary_lines.append(f"Net Amount Due: {self.net_proration_amount:.2f}")
                else:
                    summary_lines.append(f"Net Credit: {abs(self.net_proration_amount):.2f}")
        
        # Billing information
        summary_lines.append("")
        summary_lines.append("BILLING:")
        if self.immediate_billing:
            summary_lines.append("✓ Bill immediately")
            if self.auto_payment and self.payment_method_id:
                summary_lines.append(f"✓ Auto-payment with {self.payment_method_id.name}")
        else:
            summary_lines.append("• Bill in next regular cycle")
        
        # Notifications
        if self.send_notification:
            summary_lines.append("✓ Send customer notification")
        
        self.preview_summary = "\n".join(summary_lines)
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _clear_proration_amounts(self):
        """Clear proration amounts"""
        self.proration_credit_amount = 0
        self.proration_charge_amount = 0
        self.net_proration_amount = 0
        self.preview_summary = ""
    
    # =============================================================================
    # MAIN ACTIONS
    # =============================================================================
    
    def action_apply_changes(self):
        """Apply subscription changes"""
        self.ensure_one()
        
        # Validate before applying
        self._validate_before_apply()
        
        # Calculate proration if not done
        if self.enable_proration and not self.proration_preview_generated:
            self.action_calculate_proration()
        
        # Create proration calculation record
        proration_calc = None
        if self.enable_proration and (self.proration_charge_amount > 0 or self.proration_credit_amount > 0):
            proration_calc = self._create_proration_calculation()
        
        # Apply subscription changes
        self._apply_subscription_changes()
        
        # Process proration
        if proration_calc:
            proration_calc.action_approve()
            if self.immediate_billing:
                proration_calc.action_apply()
        
        # Send notifications
        if self.send_notification:
            self._send_customer_notification()
        
        # Log the change
        self._log_subscription_change()
        
        return {
            'name': _('Updated Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _validate_before_apply(self):
        """Validate before applying changes"""
        if self.subscription_id.state != 'active':
            raise UserError(_('Only active subscriptions can be modified'))
        
        if self.confirmation_required and not self.customer_confirmed:
            raise UserError(_('Customer confirmation is required for this change'))
        
        if not self.terms_accepted:
            raise UserError(_('Terms must be accepted before applying changes'))
        
        if self.auto_payment and not self.payment_method_id:
            raise UserError(_('Payment method is required for auto-payment'))
    
    def _create_proration_calculation(self):
        """Create proration calculation record"""
        vals = {
            'subscription_id': self.subscription_id.id,
            'original_product_id': self.current_product_id.id,
            'proration_type': self.change_type,
            'effective_date': self.effective_date,
            'billing_period_start': self.current_billing_period_start,
            'billing_period_end': self.current_billing_period_end,
            'proration_method': self.proration_method,
            'original_price': self.current_price,
            'original_quantity': self.current_quantity or 1,
        }
        
        if self.change_type in ['upgrade', 'downgrade']:
            vals.update({
                'new_product_id': self.new_product_id.id,
                'new_price': self.new_price,
                'new_quantity': self.new_quantity,
            })
        elif self.change_type in ['add_seats', 'remove_seats']:
            vals['new_quantity'] = self.new_quantity
        
        # Set manual amounts if calculated
        if self.proration_preview_generated:
            vals.update({
                'manual_override': True,
                'manual_credit_amount': self.proration_credit_amount,
                'manual_charge_amount': self.proration_charge_amount,
                'override_reason': f'Applied via upgrade wizard: {self.change_type}',
            })
        
        return self.env['ams.proration.calculation'].create(vals)
    
    def _apply_subscription_changes(self):
        """Apply changes to subscription"""
        subscription = self.subscription_id
        
        if self.change_type in ['upgrade', 'downgrade']:
            # Update product and price
            subscription.write({
                'product_id': self.new_product_id.id,
                'price': self.new_price,
                'quantity': self.new_quantity,
            })
        elif self.change_type in ['add_seats', 'remove_seats']:
            # Update quantity
            subscription.quantity = self.new_quantity
        elif self.change_type == 'change_plan':
            # Update billing frequency
            if self.new_billing_frequency:
                subscription.subscription_period = self.new_billing_frequency
        
        # Update billing schedule if exists
        billing_schedules = subscription.billing_schedule_ids.filtered(lambda s: s.state == 'active')
        for schedule in billing_schedules:
            if self.new_billing_frequency:
                schedule.billing_frequency = self.new_billing_frequency
            schedule._calculate_next_billing_date()
    
    def _send_customer_notification(self):
        """Send notification to customer"""
        if self.notification_template_id:
            template = self.notification_template_id
        else:
            # Use default template
            template = self.env.ref('ams_subscription_billing.email_template_subscription_change', False)
        
        if template:
            # Add custom message to context
            ctx = {
                'custom_message': self.custom_message,
                'change_type': self.change_type,
                'effective_date': self.effective_date,
                'proration_amount': self.net_proration_amount,
            }
            
            template.with_context(ctx).send_mail(self.subscription_id.id, force_send=True)
    
    def _log_subscription_change(self):
        """Log the subscription change"""
        change_description = self._generate_change_description()
        
        self.subscription_id.message_post(
            body=change_description,
            subject=f'Subscription {self.change_type.replace("_", " ").title()}'
        )
    
    def _generate_change_description(self):
        """Generate description of changes made"""
        lines = []
        
        if self.change_type in ['upgrade', 'downgrade']:
            lines.append(f"Product changed from {self.current_product_id.name} to {self.new_product_id.name}")
            lines.append(f"Price changed from {self.current_price:.2f} to {self.new_price:.2f}")
        elif self.change_type in ['add_seats', 'remove_seats']:
            lines.append(f"Seats changed from {self.current_quantity:.0f} to {self.new_quantity:.0f}")
        
        lines.append(f"Effective date: {self.effective_date}")
        
        if self.enable_proration and self.net_proration_amount != 0:
            if self.net_proration_amount > 0:
                lines.append(f"Proration charge: {self.net_proration_amount:.2f}")
            else:
                lines.append(f"Proration credit: {abs(self.net_proration_amount):.2f}")
        
        return "\n".join(lines)
    
    # =============================================================================
    # UTILITY ACTIONS
    # =============================================================================
    
    def action_preview_invoice(self):
        """Preview the proration invoice"""
        self.ensure_one()
        
        if not self.proration_preview_generated:
            raise UserError(_('Please calculate proration first'))
        
        if self.net_proration_amount <= 0:
            raise UserError(_('No invoice needed for this change'))
        
        # Create temporary invoice preview
        preview_vals = self._prepare_preview_invoice_values()
        
        return {
            'name': _('Invoice Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.invoice.preview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_vals': preview_vals,
                'default_subscription_id': self.subscription_id.id,
            }
        }
    
    def _prepare_preview_invoice_values(self):
        """Prepare invoice values for preview"""
        return {
            'partner_id': self.partner_id.id,
            'amount_total': self.net_proration_amount,
            'description': f'{self.change_type.replace("_", " ").title()} - {self.subscription_id.name}',
            'effective_date': self.effective_date,
        }
    
    def action_request_customer_approval(self):
        """Request customer approval for changes"""
        self.ensure_one()
        
        # Send approval request email
        template = self.env.ref('ams_subscription_billing.email_template_change_approval_request', False)
        if template:
            template.send_mail(self.subscription_id.id, force_send=True)
        
        # Create approval activity
        self.subscription_id.activity_schedule(
            'mail.mail_activity_data_call',
            summary=f'Customer approval pending for {self.change_type}',
            note=f'Waiting for customer approval for subscription change. Effective date: {self.effective_date}'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Approval request sent to customer'),
                'type': 'success',
            }
        }


class AMSSubscriptionFeatureChange(models.TransientModel):
    """Feature Changes for Subscription Upgrades"""
    _name = 'ams.subscription.feature.change'
    _description = 'AMS Subscription Feature Change'
    
    upgrade_wizard_id = fields.Many2one(
        'ams.subscription.upgrade.wizard',
        string='Upgrade Wizard',
        required=True,
        ondelete='cascade'
    )
    
    feature_name = fields.Char(
        string='Feature Name',
        required=True
    )
    
    change_type = fields.Selection([
        ('add', 'Add Feature'),
        ('remove', 'Remove Feature'),
        ('modify', 'Modify Feature'),
    ], string='Change Type', required=True)
    
    current_value = fields.Char(
        string='Current Value'
    )
    
    new_value = fields.Char(
        string='New Value'
    )
    
    price_impact = fields.Monetary(
        string='Price Impact',
        currency_field='currency_id',
        help='Additional cost for this feature change'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='upgrade_wizard_id.currency_id'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the feature change'
    )