# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionRenewalWizard(models.TransientModel):
    """
    Wizard for processing AMS subscription renewals with comprehensive options.
    Handles single and bulk renewal processing, pricing updates, and communication.
    """
    _name = 'ams.subscription.renewal.wizard'
    _description = 'Subscription Renewal Processing Wizard'

    # ========================================================================
    # RENEWAL SELECTION AND MODE
    # ========================================================================

    renewal_mode = fields.Selection([
        ('single', 'Single Renewal'),
        ('bulk', 'Bulk Renewals'),
        ('customer', 'Customer Renewals'),
    ], string="Renewal Mode",
       default='single',
       required=True,
       help="Type of renewal processing")

    renewal_id = fields.Many2one(
        'ams.subscription.renewal',
        string="Renewal",
        help="Single renewal to process"
    )

    renewal_ids = fields.Many2many(
        'ams.subscription.renewal',
        string="Renewals",
        help="Multiple renewals to process"
    )

    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        help="Customer for renewal processing"
    )

    # ========================================================================
    # RENEWAL CONFIGURATION
    # ========================================================================

    renewal_date = fields.Date(
        string="Renewal Date",
        default=fields.Date.today,
        required=True,
        help="Date to process renewals"
    )

    new_billing_period_id = fields.Many2one(
        'ams.billing.period',
        string="New Billing Period",
        help="Change billing period for renewals (optional)"
    )

    apply_price_updates = fields.Boolean(
        string="Apply Price Updates",
        default=True,
        help="Apply current product pricing to renewals"
    )

    price_adjustment_percent = fields.Float(
        string="Price Adjustment %",
        default=0.0,
        help="Additional price adjustment percentage"
    )

    extend_grace_period = fields.Boolean(
        string="Extend Grace Period",
        default=False,
        help="Extend grace period for overdue renewals"
    )

    grace_extension_days = fields.Integer(
        string="Grace Extension Days",
        default=7,
        help="Additional grace period days"
    )

    # ========================================================================
    # RENEWAL PROCESSING OPTIONS
    # ========================================================================

    renewal_method = fields.Selection([
        ('automatic', 'Automatic Processing'),
        ('manual', 'Manual Processing'),
        ('bulk_automatic', 'Bulk Automatic'),
    ], string="Processing Method",
       default='automatic',
       required=True,
       help="How to process the renewals")

    create_invoices = fields.Boolean(
        string="Create Invoices",
        default=True,
        help="Automatically create invoices for renewals"
    )

    send_confirmations = fields.Boolean(
        string="Send Confirmation Emails",
        default=True,
        help="Send renewal confirmation emails to customers"
    )

    update_subscription_dates = fields.Boolean(
        string="Update Subscription Dates",
        default=True,
        help="Update subscription end dates after renewal"
    )

    # ========================================================================
    # COMMUNICATION AND NOTIFICATIONS
    # ========================================================================

    email_template_id = fields.Many2one(
        'mail.template',
        string="Email Template",
        domain=[('model', '=', 'ams.subscription.renewal')],
        help="Custom email template for renewal confirmations"
    )

    custom_message = fields.Text(
        string="Custom Message",
        help="Additional message to include in communications"
    )

    notify_internal_users = fields.Boolean(
        string="Notify Internal Users",
        default=True,
        help="Send notifications to internal users about renewals"
    )

    internal_user_ids = fields.Many2many(
        'res.users',
        string="Users to Notify",
        help="Internal users to notify about renewal processing"
    )

    # ========================================================================
    # RENEWAL SUMMARY AND PREVIEW
    # ========================================================================

    renewals_to_process_count = fields.Integer(
        string="Renewals Count",
        compute='_compute_renewal_summary',
        help="Number of renewals to process"
    )

    total_renewal_value = fields.Monetary(
        string="Total Renewal Value",
        compute='_compute_renewal_summary',
        help="Total value of renewals to process"
    )

    member_renewals_count = fields.Integer(
        string="Member Renewals",
        compute='_compute_renewal_summary',
        help="Number of member renewals"
    )

    overdue_renewals_count = fields.Integer(
        string="Overdue Renewals",
        compute='_compute_renewal_summary',
        help="Number of overdue renewals"
    )

    price_increase_renewals = fields.Integer(
        string="Price Increases",
        compute='_compute_renewal_summary',
        help="Number of renewals with price increases"
    )

    average_price_increase = fields.Float(
        string="Average Price Increase %",
        compute='_compute_renewal_summary',
        help="Average price increase percentage"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ========================================================================
    # VALIDATION AND STATUS
    # ========================================================================

    can_process_renewals = fields.Boolean(
        string="Can Process",
        compute='_compute_validation_status',
        help="Whether renewals can be processed"
    )

    validation_messages = fields.Text(
        string="Validation Messages",
        compute='_compute_validation_status',
        help="Validation issues or information"
    )

    processing_warnings = fields.Text(
        string="Processing Warnings",
        compute='_compute_processing_warnings',
        help="Warnings about renewal processing"
    )

    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================

    @api.depends('renewal_mode', 'renewal_id', 'renewal_ids', 'partner_id')
    def _compute_renewal_summary(self):
        """Compute renewal processing summary."""
        for wizard in self:
            renewals = wizard._get_renewals_to_process()
            
            wizard.renewals_to_process_count = len(renewals)
            wizard.total_renewal_value = sum(renewals.mapped('renewal_price'))
            wizard.member_renewals_count = len(renewals.filtered('is_member_renewal'))
            wizard.overdue_renewals_count = len(renewals.filtered('is_overdue'))
            
            # Price increase analysis
            price_increase_renewals = renewals.filtered(lambda r: r.price_increase_percent > 0)
            wizard.price_increase_renewals = len(price_increase_renewals)
            
            if price_increase_renewals:
                wizard.average_price_increase = sum(
                    price_increase_renewals.mapped('price_increase_percent')
                ) / len(price_increase_renewals)
            else:
                wizard.average_price_increase = 0.0

    @api.depends('renewal_mode', 'renewal_id', 'renewal_ids', 'partner_id', 'renewal_date')
    def _compute_validation_status(self):
        """Validate renewal processing requirements."""
        for wizard in self:
            messages = []
            can_process = True

            # Mode-specific validations
            if wizard.renewal_mode == 'single':
                if not wizard.renewal_id:
                    messages.append("Select a renewal to process")
                    can_process = False
                elif wizard.renewal_id.state not in ['pending', 'reminded', 'grace_period']:
                    messages.append("Selected renewal cannot be processed (invalid state)")
                    can_process = False

            elif wizard.renewal_mode == 'bulk':
                if not wizard.renewal_ids:
                    messages.append("Select renewals to process")
                    can_process = False
                else:
                    invalid_renewals = wizard.renewal_ids.filtered(
                        lambda r: r.state not in ['pending', 'reminded', 'grace_period']
                    )
                    if invalid_renewals:
                        messages.append(f"{len(invalid_renewals)} renewals have invalid states")
                        can_process = False

            elif wizard.renewal_mode == 'customer':
                if not wizard.partner_id:
                    messages.append("Select a customer")
                    can_process = False
                else:
                    customer_renewals = wizard._get_customer_renewals()
                    if not customer_renewals:
                        messages.append("No processable renewals found for customer")
                        can_process = False

            # General validations
            if wizard.renewal_date < fields.Date.today():
                messages.append("Renewal date cannot be in the past")
                can_process = False

            if wizard.price_adjustment_percent < -100:
                messages.append("Price adjustment cannot be less than -100%")
                can_process = False

            wizard.can_process_renewals = can_process
            wizard.validation_messages = "\n".join(messages) if messages else "Ready to process renewals"

    @api.depends('renewal_mode', 'renewal_id', 'renewal_ids', 'partner_id', 'apply_price_updates')
    def _compute_processing_warnings(self):
        """Generate processing warnings."""
        for wizard in self:
            warnings = []
            
            renewals = wizard._get_renewals_to_process()
            
            if not renewals:
                warnings.append("No renewals to process")
            else:
                # Check for price increases
                if wizard.apply_price_updates:
                    price_increases = renewals.filtered(lambda r: r.price_increase_amount > 0)
                    if price_increases:
                        total_increase = sum(price_increases.mapped('price_increase_amount'))
                        warnings.append(f"Price increases detected: ${total_increase:.2f} total impact")

                # Check for overdue renewals
                overdue = renewals.filtered('is_overdue')
                if overdue:
                    warnings.append(f"{len(overdue)} overdue renewals will be processed")

                # Check for failed customers
                failed_customers = renewals.mapped('partner_id').filtered(
                    lambda p: p.outstanding_subscription_amount > 0
                )
                if failed_customers:
                    warnings.append(f"{len(failed_customers)} customers have outstanding payments")

                # Check for auto-renewal disabled
                no_auto_renewal = renewals.filtered(lambda r: not r.auto_renewal_enabled)
                if no_auto_renewal:
                    warnings.append(f"{len(no_auto_renewal)} renewals have auto-renewal disabled")

            wizard.processing_warnings = "\n".join(warnings) if warnings else ""

    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================

    @api.onchange('renewal_mode')
    def _onchange_renewal_mode(self):
        """Update fields when renewal mode changes."""
        if self.renewal_mode == 'single':
            self.renewal_ids = [(5, 0, 0)]  # Clear many2many
            self.partner_id = False
        elif self.renewal_mode == 'bulk':
            self.renewal_id = False
            self.partner_id = False
        elif self.renewal_mode == 'customer':
            self.renewal_id = False
            self.renewal_ids = [(5, 0, 0)]

    @api.onchange('renewal_id')
    def _onchange_renewal_id(self):
        """Update fields when single renewal changes."""
        if self.renewal_id:
            # Set defaults from renewal
            if self.renewal_id.billing_period_id:
                self.new_billing_period_id = self.renewal_id.billing_period_id
            
            # Set renewal date to due date if not overdue
            if not self.renewal_id.is_overdue:
                self.renewal_date = self.renewal_id.renewal_due_date

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update renewal processing when customer changes."""
        if self.partner_id and self.renewal_mode == 'customer':
            # This will trigger recomputation of summary fields
            pass

    @api.onchange('extend_grace_period')
    def _onchange_extend_grace_period(self):
        """Set default grace extension."""
        if self.extend_grace_period and not self.grace_extension_days:
            self.grace_extension_days = 7

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _get_renewals_to_process(self):
        """Get renewals to process based on wizard configuration."""
        if self.renewal_mode == 'single' and self.renewal_id:
            return self.renewal_id
        elif self.renewal_mode == 'bulk' and self.renewal_ids:
            return self.renewal_ids
        elif self.renewal_mode == 'customer' and self.partner_id:
            return self._get_customer_renewals()
        else:
            return self.env['ams.subscription.renewal'].browse()

    def _get_customer_renewals(self):
        """Get processable renewals for selected customer."""
        if not self.partner_id:
            return self.env['ams.subscription.renewal'].browse()
        
        return self.env['ams.subscription.renewal'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['pending', 'reminded', 'grace_period']),
        ])

    # ========================================================================
    # RENEWAL PROCESSING METHODS
    # ========================================================================

    def action_process_renewals(self):
        """Process renewals with configured settings."""
        self.ensure_one()
        
        if not self.can_process_renewals:
            raise UserError(_("Cannot process renewals. Please resolve validation issues."))
        
        renewals = self._get_renewals_to_process()
        
        if not renewals:
            raise UserError(_("No renewals to process"))
        
        # Process renewals
        results = self._process_renewals(renewals)
        
        # Show results
        return self._show_processing_results(results)

    def _process_renewals(self, renewals):
        """Process the specified renewals."""
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'processed_renewals': [],
            'total_value': 0.0,
        }
        
        for renewal in renewals:
            try:
                # Apply pricing updates if requested
                if self.apply_price_updates:
                    self._apply_pricing_updates(renewal)
                
                # Apply price adjustments
                if self.price_adjustment_percent != 0:
                    self._apply_price_adjustment(renewal)
                
                # Extend grace period if requested
                if self.extend_grace_period and renewal.is_overdue:
                    self._extend_grace_period(renewal)
                
                # Update billing period if requested
                if self.new_billing_period_id:
                    renewal.billing_period_id = self.new_billing_period_id
                
                # Process the renewal
                success = renewal.process_renewal(self.renewal_method)
                
                if success:
                    results['success_count'] += 1
                    results['processed_renewals'].append(renewal.id)
                    results['total_value'] += renewal.renewal_price
                    
                    # Post-processing actions
                    if self.create_invoices:
                        self._create_renewal_invoice(renewal)
                    
                    if self.send_confirmations:
                        self._send_renewal_confirmation(renewal)
                        
                else:
                    results['error_count'] += 1
                    results['errors'].append(f"Failed to process {renewal.name}")
                
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Error processing {renewal.name}: {str(e)}")
                _logger.error(f"Renewal processing error for {renewal.name}: {e}")
        
        # Send internal notifications
        if self.notify_internal_users and results['success_count'] > 0:
            self._send_internal_notifications(results)
        
        return results

    def _apply_pricing_updates(self, renewal):
        """Apply current product pricing to renewal."""
        if renewal.product_id and renewal.partner_id:
            pricing = renewal.product_id.calculate_subscription_pricing_for_partner(
                renewal.partner_id
            )
            
            # Update renewal pricing (this might need to be stored in a different field)
            # The actual implementation depends on how pricing updates are tracked
            renewal.message_post(
                body=_("Pricing updated: Current price ${:.2f}, New price ${:.2f}").format(
                    renewal.current_price,
                    pricing.get('base_price', 0.0)
                )
            )

    def _apply_price_adjustment(self, renewal):
        """Apply additional price adjustment."""
        if self.price_adjustment_percent != 0:
            adjustment_amount = renewal.renewal_price * (self.price_adjustment_percent / 100)
            renewal.message_post(
                body=_("Price adjustment applied: {:.1f}% (${:.2f})").format(
                    self.price_adjustment_percent,
                    adjustment_amount
                )
            )

    def _extend_grace_period(self, renewal):
        """Extend grace period for renewal."""
        if self.grace_extension_days > 0:
            new_grace_end = renewal.grace_period_end + timedelta(days=self.grace_extension_days)
            renewal.message_post(
                body=_("Grace period extended by {} days until {}").format(
                    self.grace_extension_days,
                    new_grace_end.strftime('%Y-%m-%d')
                )
            )

    def _create_renewal_invoice(self, renewal):
        """Create invoice for processed renewal."""
        try:
            # Find the billing record created during renewal processing
            billing = self.env['ams.subscription.billing'].search([
                ('subscription_id', '=', renewal.subscription_id.id),
                ('billing_date', '>=', self.renewal_date),
                ('state', '=', 'scheduled')
            ], limit=1)
            
            if billing:
                billing.process_billing()
        except Exception as e:
            _logger.error(f"Failed to create invoice for renewal {renewal.name}: {e}")

    def _send_renewal_confirmation(self, renewal):
        """Send renewal confirmation email."""
        try:
            if self.email_template_id:
                template = self.email_template_id
            else:
                template = renewal._get_renewal_confirmation_template()
            
            if template:
                # Add custom message if provided
                if self.custom_message:
                    template = template.copy()
                    template.body_html += f"\n\n<p>{self.custom_message}</p>"
                
                template.send_mail(renewal.id, force_send=True)
                
        except Exception as e:
            _logger.error(f"Failed to send confirmation for renewal {renewal.name}: {e}")

    def _send_internal_notifications(self, results):
        """Send internal notifications about renewal processing."""
        if not self.internal_user_ids and not self.notify_internal_users:
            return
        
        users_to_notify = self.internal_user_ids if self.internal_user_ids else self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('sales_team.group_sale_manager').id])
        ])
        
        subject = f"Renewal Processing Complete: {results['success_count']} processed"
        body = f"""
        Renewal processing completed:
        
        • Successful: {results['success_count']}
        • Failed: {results['error_count']}
        • Total Value: ${results['total_value']:.2f}
        
        Processing Method: {dict(self._fields['renewal_method'].selection)[self.renewal_method]}
        Processing Date: {self.renewal_date}
        """
        
        if results['errors']:
            body += f"\n\nErrors:\n" + "\n".join(results['errors'][:5])
            if len(results['errors']) > 5:
                body += f"\n... and {len(results['errors']) - 5} more errors"
        
        for user in users_to_notify:
            user.partner_id.message_post(
                subject=subject,
                body=body,
                message_type='notification'
            )

    # ========================================================================
    # RESULT PRESENTATION
    # ========================================================================

    def _show_processing_results(self, results):
        """Show processing results to user."""
        if results['success_count'] == 0:
            message_type = 'danger'
            title = "Renewal Processing Failed"
            message = f"Failed to process {results['error_count']} renewals."
        elif results['error_count'] == 0:
            message_type = 'success'
            title = "Renewal Processing Complete"
            message = f"Successfully processed {results['success_count']} renewals (${results['total_value']:.2f} total value)."
        else:
            message_type = 'warning'
            title = "Renewal Processing Partial"
            message = f"Processed {results['success_count']} renewals successfully, {results['error_count']} failed."
        
        if results['errors']:
            message += f"\n\nErrors:\n" + "\n".join(results['errors'][:3])
            if len(results['errors']) > 3:
                message += f"\n... and {len(results['errors']) - 3} more"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'title': title,
                'type': message_type,
                'sticky': True,
            }
        }

    # ========================================================================
    # PREVIEW AND VALIDATION ACTIONS
    # ========================================================================

    def action_preview_renewals(self):
        """Preview renewals that will be processed."""
        self.ensure_one()
        
        renewals = self._get_renewals_to_process()
        
        if not renewals:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No renewals to preview',
                    'title': 'Preview Results',
                    'type': 'warning',
                }
            }
        
        preview_lines = []
        for renewal in renewals:
            line = f"• {renewal.partner_id.name} - {renewal.product_id.name} (${renewal.renewal_price:.2f})"
            if renewal.is_overdue:
                line += " [OVERDUE]"
            if renewal.price_increase_amount > 0:
                line += f" [+{renewal.price_increase_percent:.1f}%]"
            preview_lines.append(line)
        
        message = f"Renewals to Process ({len(renewals)}):\n\n" + "\n".join(preview_lines[:10])
        if len(renewals) > 10:
            message += f"\n... and {len(renewals) - 10} more renewals"
        
        message += f"\n\nTotal Value: ${sum(renewals.mapped('renewal_price')):.2f}"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'title': 'Renewal Preview',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_validate_renewals(self):
        """Validate renewals and show detailed validation results."""
        self.ensure_one()
        
        renewals = self._get_renewals_to_process()
        
        validation_results = []
        error_count = 0
        warning_count = 0
        
        for renewal in renewals:
            issues = []
            
            # Check renewal state
            if renewal.state not in ['pending', 'reminded', 'grace_period']:
                issues.append(f"Invalid state: {renewal.state}")
                error_count += 1
            
            # Check customer eligibility
            if renewal.product_id and renewal.partner_id:
                variant = renewal.product_id.product_variant_ids[0] if renewal.product_id.product_variant_ids else None
                if variant:
                    eligibility = variant.can_create_subscription_for_partner(renewal.partner_id)
                    if not eligibility.get('can_create'):
                        issues.append(f"Eligibility issue: {eligibility.get('reason')}")
                        error_count += 1
            
            # Check for outstanding payments
            if renewal.partner_id.outstanding_subscription_amount > 0:
                issues.append(f"Outstanding payments: ${renewal.partner_id.outstanding_subscription_amount:.2f}")
                warning_count += 1
            
            # Check for price increases
            if renewal.price_increase_percent > 20:
                issues.append(f"Large price increase: {renewal.price_increase_percent:.1f}%")
                warning_count += 1
            
            if issues:
                validation_results.append(f"{renewal.name}: {', '.join(issues)}")
        
        if error_count == 0 and warning_count == 0:
            message = f"✅ All {len(renewals)} renewals validated successfully"
            message_type = 'success'
        elif error_count == 0:
            message = f"⚠️ {len(renewals)} renewals validated with {warning_count} warnings:\n\n"
            message += "\n".join(validation_results[:5])
            message_type = 'warning'
        else:
            message = f"❌ Validation failed: {error_count} errors, {warning_count} warnings:\n\n"
            message += "\n".join(validation_results[:5])
            message_type = 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'title': 'Renewal Validation',
                'type': message_type,
                'sticky': True,
            }
        }

    # ========================================================================
    # BULK ACTION HELPERS
    # ========================================================================

    def action_load_due_renewals(self):
        """Load renewals due for processing."""
        self.ensure_one()
        
        due_renewals = self.env['ams.subscription.renewal'].search([
            ('state', 'in', ['pending', 'reminded']),
            ('renewal_due_date', '<=', fields.Date.today() + timedelta(days=7)),
        ])
        
        if self.renewal_mode == 'bulk':
            self.renewal_ids = [(6, 0, due_renewals.ids)]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Loaded {len(due_renewals)} renewals due within 7 days",
                'title': 'Due Renewals Loaded',
                'type': 'success',
            }
        }

    def action_load_overdue_renewals(self):
        """Load overdue renewals."""
        self.ensure_one()
        
        overdue_renewals = self.env['ams.subscription.renewal'].search([
            ('state', 'in', ['grace_period', 'expired']),
        ])
        
        if self.renewal_mode == 'bulk':
            self.renewal_ids = [(6, 0, overdue_renewals.ids)]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Loaded {len(overdue_renewals)} overdue renewals",
                'title': 'Overdue Renewals Loaded',
                'type': 'warning',
            }
        }

    def action_load_member_renewals(self):
        """Load renewals for members only."""
        self.ensure_one()
        
        member_renewals = self.env['ams.subscription.renewal'].search([
            ('state', 'in', ['pending', 'reminded', 'grace_period']),
            ('is_member_renewal', '=', True),
        ])
        
        if self.renewal_mode == 'bulk':
            self.renewal_ids = [(6, 0, member_renewals.ids)]
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Loaded {len(member_renewals)} member renewals",
                'title': 'Member Renewals Loaded',
                'type': 'info',
            }
        }

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @api.constrains('price_adjustment_percent')
    def _check_price_adjustment(self):
        """Validate price adjustment percentage."""
        for wizard in self:
            if wizard.price_adjustment_percent < -100:
                raise ValidationError(_("Price adjustment cannot be less than -100%"))
            if wizard.price_adjustment_percent > 1000:
                raise ValidationError(_("Price adjustment cannot exceed 1000%"))

    @api.constrains('grace_extension_days')
    def _check_grace_extension(self):
        """Validate grace extension days."""
        for wizard in self:
            if wizard.extend_grace_period and wizard.grace_extension_days <= 0:
                raise ValidationError(_("Grace extension days must be positive"))

    @api.constrains('renewal_date')
    def _check_renewal_date(self):
        """Validate renewal date."""
        for wizard in self:
            if wizard.renewal_date < fields.Date.today():
                raise ValidationError(_("Renewal date cannot be in the past"))

    # ========================================================================
    # DEFAULT VALUES
    # ========================================================================

    @api.model
    def default_get(self, fields):
        """Set default values based on context."""
        result = super().default_get(fields)
        
        # Set renewal from context
        if 'renewal_id' not in result and self.env.context.get('active_model') == 'ams.subscription.renewal':
            if self.env.context.get('active_id'):
                result['renewal_id'] = self.env.context['active_id']
                result['renewal_mode'] = 'single'
            elif self.env.context.get('active_ids'):
                result['renewal_ids'] = [(6, 0, self.env.context['active_ids'])]
                result['renewal_mode'] = 'bulk'
        
        # Set customer from context
        if 'partner_id' not in result and self.env.context.get('default_partner_id'):
            result['partner_id'] = self.env.context['default_partner_id']
            result['renewal_mode'] = 'customer'
        
        # Set default internal users
        if 'internal_user_ids' not in result:
            manager_group = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
            if manager_group:
                result['internal_user_ids'] = [(6, 0, manager_group.users.ids)]
        
        return result