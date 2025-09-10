# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ResConfigSettings(models.TransientModel):
    """Extend settings to include AMS billing configuration"""
    _inherit = 'res.config.settings'

    # =============================================================================
    # BILLING AUTOMATION SETTINGS
    # =============================================================================
    
    ams_auto_send_invoices = fields.Boolean(
        string='Auto Send Invoices',
        config_parameter='ams_billing.auto_send_invoices',
        default=True,
        help='Automatically send invoices to customers when generated'
    )
    
    ams_payment_reminder_enabled = fields.Boolean(
        string='Enable Payment Reminders',
        config_parameter='ams_billing.payment_reminder_enabled',
        default=True,
        help='Automatically send payment reminders for overdue invoices'
    )
    
    ams_reminder_days = fields.Char(
        string='Reminder Days',
        config_parameter='ams_billing.reminder_days',
        default='1,7,14',
        help='Days after due date to send reminders (comma-separated)'
    )
    
    # =============================================================================
    # BILLING SCHEDULE SETTINGS
    # =============================================================================
    
    ams_weekend_billing_adjustment = fields.Selection([
        ('none', 'No Adjustment'),
        ('next_business_day', 'Next Business Day'),
        ('previous_business_day', 'Previous Business Day'),
    ], string='Weekend Billing Adjustment',
    config_parameter='ams_billing.weekend_billing_adjustment',
    default='next_business_day',
    help='How to handle billing dates that fall on weekends')
    
    ams_batch_size = fields.Integer(
        string='Billing Batch Size',
        config_parameter='ams_billing.batch_size',
        default=100,
        help='Number of billing schedules to process in each batch'
    )
    
    ams_billing_lead_days = fields.Integer(
        string='Billing Lead Days',
        config_parameter='ams_billing.billing_lead_days',
        default=0,
        help='Number of days before due date to generate invoices'
    )
    
    # =============================================================================
    # DEFAULT BILLING SETTINGS
    # =============================================================================
    
    ams_default_payment_terms = fields.Many2one(
        'account.payment.term',
        string='Default Payment Terms',
        config_parameter='ams_billing.default_payment_terms',
        help='Default payment terms for subscription invoices'
    )
    
    ams_default_billing_journal = fields.Many2one(
        'account.journal',
        string='Default Billing Journal',
        domain=[('type', '=', 'sale')],
        config_parameter='ams_billing.default_billing_journal',
        help='Default journal for subscription billing'
    )
    
    # =============================================================================
    # EMAIL TEMPLATE SETTINGS
    # =============================================================================
    
    ams_invoice_template_id = fields.Many2one(
        'mail.template',
        string='Invoice Email Template',
        domain=[('model', '=', 'account.move')],
        config_parameter='ams_billing.invoice_template_id',
        help='Email template for sending invoices'
    )
    
    ams_payment_reminder_template_id = fields.Many2one(
        'mail.template',
        string='Payment Reminder Template',
        domain=[('model', '=', 'account.move')],
        config_parameter='ams_billing.payment_reminder_template_id',
        help='Email template for payment reminders'
    )
    
    # =============================================================================
    # STATISTICS (READ-ONLY)
    # =============================================================================
    
    ams_active_billing_schedules = fields.Integer(
        string='Active Billing Schedules',
        compute='_compute_billing_statistics',
        readonly=True
    )
    
    ams_overdue_invoices_count = fields.Integer(
        string='Overdue Invoices',
        compute='_compute_billing_statistics',
        readonly=True
    )
    
    ams_pending_billing_events = fields.Integer(
        string='Pending Billing Events',
        compute='_compute_billing_statistics',
        readonly=True
    )
    
    def _compute_billing_statistics(self):
        """Compute billing statistics for display"""
        for settings in self:
            # Active billing schedules
            settings.ams_active_billing_schedules = self.env['ams.billing.schedule'].search_count([
                ('state', '=', 'active')
            ])
            
            # Overdue invoices
            settings.ams_overdue_invoices_count = self.env['account.move'].search_count([
                ('is_subscription_invoice', '=', True),
                ('is_overdue', '=', True),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ])
            
            # Pending billing events
            settings.ams_pending_billing_events = self.env['ams.billing.event'].search_count([
                ('state', '=', 'pending'),
                ('event_date', '<=', fields.Date.today())
            ])
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('ams_reminder_days')
    def _check_reminder_days(self):
        """Validate reminder days format"""
        for settings in self:
            if settings.ams_reminder_days:
                try:
                    days = [int(day.strip()) for day in settings.ams_reminder_days.split(',')]
                    if any(day < 0 for day in days):
                        raise ValueError("Negative days not allowed")
                except ValueError:
                    raise ValidationError(_('Reminder days must be a comma-separated list of positive numbers (e.g., "1,7,14")'))
    
    @api.constrains('ams_batch_size')
    def _check_batch_size(self):
        """Validate batch size"""
        for settings in self:
            if settings.ams_batch_size and settings.ams_batch_size < 1:
                raise ValidationError(_('Batch size must be at least 1'))
    
    @api.constrains('ams_billing_lead_days')
    def _check_billing_lead_days(self):
        """Validate billing lead days"""
        for settings in self:
            if settings.ams_billing_lead_days and settings.ams_billing_lead_days < 0:
                raise ValidationError(_('Billing lead days cannot be negative'))
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def action_test_billing_configuration(self):
        """Test billing configuration"""
        self.ensure_one()
        
        issues = []
        warnings = []
        
        # Check required settings
        if not self.ams_default_billing_journal:
            issues.append(_('Default billing journal is not configured'))
        
        # Check email templates
        if self.ams_auto_send_invoices and not self.ams_invoice_template_id:
            warnings.append(_('Auto-send invoices is enabled but no invoice template is configured'))
        
        if self.ams_payment_reminder_enabled and not self.ams_payment_reminder_template_id:
            warnings.append(_('Payment reminders are enabled but no reminder template is configured'))
        
        # Check cron jobs
        billing_cron = self.env.ref('ams_subscription_billing.cron_ams_process_billing_schedules', False)
        if not billing_cron or not billing_cron.active:
            warnings.append(_('Billing processing cron job is not active'))
        
        reminder_cron = self.env.ref('ams_subscription_billing.cron_ams_send_payment_reminders', False)
        if not reminder_cron or not reminder_cron.active:
            warnings.append(_('Payment reminder cron job is not active'))
        
        # Prepare result message
        if not issues and not warnings:
            message = _('✅ Billing configuration is properly set up!')
            message_type = 'success'
        else:
            message = _('⚠️ Billing Configuration Issues Found:\n\n')
            if issues:
                message += _('🔴 Issues:\n%s\n\n') % '\n'.join(f'• {issue}' for issue in issues)
            if warnings:
                message += _('🟡 Warnings:\n%s') % '\n'.join(f'• {warning}' for warning in warnings)
            message_type = 'danger' if issues else 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Billing Configuration Test'),
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }
    
    def action_setup_default_templates(self):
        """Set up default email templates if not configured"""
        self.ensure_one()
        
        # Set default invoice template
        if not self.ams_invoice_template_id:
            invoice_template = self.env.ref('ams_subscription_billing.email_template_invoice_notification', False)
            if invoice_template:
                self.ams_invoice_template_id = invoice_template.id
        
        # Set default payment reminder template
        if not self.ams_payment_reminder_template_id:
            reminder_template = self.env.ref('ams_subscription_billing.email_template_payment_reminder', False)
            if reminder_template:
                self.ams_payment_reminder_template_id = reminder_template.id
        
        # Set default billing journal
        if not self.ams_default_billing_journal:
            sales_journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            if sales_journal:
                self.ams_default_billing_journal = sales_journal.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Default templates and settings configured'),
                'type': 'success',
            }
        }
    
    def action_view_billing_dashboard(self):
        """View billing dashboard"""
        return {
            'name': _('Billing Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'kanban,tree,form',
            'domain': [('enable_auto_billing', '=', True)],
            'context': {'search_default_group_by_payment_status': 1}
        }
    
    def action_view_overdue_invoices(self):
        """View overdue invoices"""
        return {
            'name': _('Overdue Subscription Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('is_subscription_invoice', '=', True),
                ('is_overdue', '=', True),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ]
        }
    
    def action_view_pending_events(self):
        """View pending billing events"""
        return {
            'name': _('Pending Billing Events'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.billing.event',
            'view_mode': 'list,form',
            'domain': [
                ('state', '=', 'pending'),
                ('event_date', '<=', fields.Date.today())
            ]
        }