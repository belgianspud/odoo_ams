from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Enhanced account move model with AMS-specific features and integrations
    """
    _inherit = 'account.move'
    
    # AMS Integration Fields
    ams_subscription_id = fields.Many2one('ams.subscription', 'Related AMS Subscription', readonly=True)
    ams_member_id = fields.Many2one('res.partner', 'AMS Member', readonly=True)
    ams_chapter_id = fields.Many2one('ams.chapter', 'AMS Chapter', readonly=True)
    
    # Invoice Classification
    is_ams_subscription_invoice = fields.Boolean('Is AMS Subscription Invoice', default=False)
    is_ams_renewal_invoice = fields.Boolean('Is AMS Renewal Invoice', default=False)
    is_ams_donation = fields.Boolean('Is AMS Donation', default=False)
    is_ams_chapter_fee = fields.Boolean('Is AMS Chapter Fee', default=False)
    
    # Subscription-specific fields
    subscription_period_start = fields.Date('Subscription Period Start')
    subscription_period_end = fields.Date('Subscription Period End')
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type')
    
    # Chapter-specific fields
    chapter_allocation_percentage = fields.Float('Chapter Allocation %', default=0.0)
    chapter_allocation_amount = fields.Float('Chapter Allocation Amount', compute='_compute_chapter_allocation')
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Revenue'),
        ('proportional', 'Proportional Over Period')
    ], string='Revenue Recognition Method', default='immediate')
    
    deferred_revenue_created = fields.Boolean('Deferred Revenue Created', default=False)
    deferred_revenue_move_ids = fields.One2many('account.move', 'source_move_id', 'Deferred Revenue Entries')
    source_move_id = fields.Many2one('account.move', 'Source Move')
    
    # Payment Tracking
    ams_payment_method = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('online', 'Online Payment'),
        ('autopay', 'Auto Payment')
    ], string='AMS Payment Method')
    
    payment_reference = fields.Char('Payment Reference')
    payment_processor = fields.Char('Payment Processor')
    
    # Member Communication
    member_notification_sent = fields.Boolean('Member Notification Sent', default=False)
    member_notification_date = fields.Datetime('Member Notification Date')
    member_portal_access = fields.Boolean('Member Portal Access', default=True)
    
    # Financial Analytics
    member_lifetime_invoice_number = fields.Integer('Member Invoice #', compute='_compute_member_analytics')
    member_total_paid_to_date = fields.Float('Member Total Paid', compute='_compute_member_analytics')
    is_first_invoice = fields.Boolean('First Invoice for Member', compute='_compute_member_analytics')
    
    # Approval Workflow
    requires_approval = fields.Boolean('Requires Approval', compute='_compute_approval_requirements')
    approval_user_id = fields.Many2one('res.users', 'Approved By')
    approval_date = fields.Datetime('Approval Date')
    approval_notes = fields.Text('Approval Notes')
    
    # Collections
    collection_status = fields.Selection([
        ('current', 'Current'),
        ('reminder_sent', 'Reminder Sent'),
        ('follow_up', 'Follow-up Required'),
        ('collection_agency', 'Collection Agency'),
        ('write_off', 'Write-off')
    ], string='Collection Status', default='current')
    
    days_overdue = fields.Integer('Days Overdue', compute='_compute_overdue_info')
    follow_up_level = fields.Integer('Follow-up Level', default=0)
    last_follow_up_date = fields.Date('Last Follow-up Date')
    
    @api.depends('amount_total', 'chapter_allocation_percentage')
    def _compute_chapter_allocation(self):
        for move in self:
            if move.chapter_allocation_percentage > 0:
                move.chapter_allocation_amount = (move.amount_total * move.chapter_allocation_percentage) / 100
            else:
                move.chapter_allocation_amount = 0.0
    
    @api.depends('partner_id')
    def _compute_member_analytics(self):
        for move in self:
            if move.partner_id and move.move_type == 'out_invoice':
                # Count member's invoices
                member_invoices = self.search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('date', '<=', move.date)
                ]).sorted('date')
                
                move.member_lifetime_invoice_number = len(member_invoices)
                move.is_first_invoice = (move.member_lifetime_invoice_number == 1)
                
                # Calculate total paid to date
                paid_invoices = member_invoices.filtered(lambda inv: inv.payment_state == 'paid')
                move.member_total_paid_to_date = sum(paid_invoices.mapped('amount_total'))
            else:
                move.member_lifetime_invoice_number = 0
                move.member_total_paid_to_date = 0.0
                move.is_first_invoice = False
    
    @api.depends('journal_id', 'amount_total')
    def _compute_approval_requirements(self):
        for move in self:
            if move.journal_id.require_approval and move.amount_total > move.journal_id.approval_amount_limit:
                move.requires_approval = True
            else:
                move.requires_approval = False
    
    @api.depends('invoice_date_due', 'payment_state')
    def _compute_overdue_info(self):
        today = fields.Date.today()
        for move in self:
            if move.invoice_date_due and move.payment_state in ['not_paid', 'partial']:
                days_diff = (today - move.invoice_date_due).days
                move.days_overdue = max(0, days_diff)
            else:
                move.days_overdue = 0
    
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        
        for move in moves:
            # Auto-populate AMS fields based on subscription
            if move.ams_subscription_id:
                move._populate_ams_fields_from_subscription()
            
            # Auto-detect AMS invoice types
            move._detect_ams_invoice_type()
            
            # Set revenue recognition method
            move._set_revenue_recognition_method()
        
        return moves
    
    def _populate_ams_fields_from_subscription(self):
        """Populate AMS fields from related subscription"""
        if not self.ams_subscription_id:
            return
        
        subscription = self.ams_subscription_id
        
        # Basic AMS fields
        self.ams_member_id = subscription.partner_id.id
        self.ams_chapter_id = subscription.chapter_id.id if subscription.chapter_id else False
        self.subscription_type_id = subscription.subscription_type_id.id
        
        # Subscription period
        self.subscription_period_start = subscription.start_date
        self.subscription_period_end = subscription.end_date
        
        # Chapter allocation
        if subscription.chapter_id and hasattr(subscription.chapter_id, 'parent_organization_allocation'):
            self.chapter_allocation_percentage = subscription.chapter_id.parent_organization_allocation
    
    def _detect_ams_invoice_type(self):
        """Auto-detect AMS invoice type based on content"""
        if self.move_type != 'out_invoice':
            return
        
        # Check for subscription products
        subscription_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id and l.product_id.is_subscription_product
        )
        
        if subscription_lines:
            self.is_ams_subscription_invoice = True
            
            # Check if it's a renewal
            if any('renewal' in line.name.lower() for line in subscription_lines):
                self.is_ams_renewal_invoice = True
            
            # Check subscription types
            for line in subscription_lines:
                if line.product_id.subscription_type_id:
                    if line.product_id.subscription_type_id.code == 'chapter':
                        self.is_ams_chapter_fee = True
        
        # Check for donation products
        donation_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id and 'donation' in l.product_id.name.lower()
        )
        
        if donation_lines:
            self.is_ams_donation = True
    
    def _set_revenue_recognition_method(self):
        """Set revenue recognition method based on invoice type and subscription"""
        if not self.is_ams_subscription_invoice:
            return
        
        if self.ams_subscription_id:
            self.revenue_recognition_method = self.ams_subscription_id.revenue_recognition_method
        elif self.subscription_period_start and self.subscription_period_end:
            # If we have subscription periods, use proportional recognition
            self.revenue_recognition_method = 'proportional'
    
    def action_post(self):
        """Override post action to add AMS-specific logic"""
        # Validate journal entry if it's an AMS journal
        for move in self:
            if move.journal_id.is_ams_journal:
                move.journal_id.validate_journal_entry(move)
        
        # Standard posting
        result = super().action_post()
        
        # AMS-specific post-processing
        for move in self:
            move._process_ams_post_actions()
        
        return result
    
    def _process_ams_post_actions(self):
        """Process AMS-specific actions after posting"""
        # Create deferred revenue entries
        if self.revenue_recognition_method == 'deferred' and not self.deferred_revenue_created:
            self._create_deferred_revenue_entries()
        
        # Create chapter allocation entry
        if self.chapter_allocation_amount > 0:
            self._create_chapter_allocation_entry()
        
        # Send member notification
        if self.is_ams_subscription_invoice and not self.member_notification_sent:
            self._send_member_notification()
        
        # Update subscription status
        if self.ams_subscription_id:
            self._update_subscription_status()
    
    def _create_deferred_revenue_entries(self):
        """Create deferred revenue recognition entries"""
        if not self.subscription_period_start or not self.subscription_period_end:
            return
        
        # Calculate number of months for recognition
        months = (self.subscription_period_end.year - self.subscription_period_start.year) * 12 + \
                (self.subscription_period_end.month - self.subscription_period_start.month) + 1
        
        if months <= 0:
            return
        
        monthly_amount = self.amount_total / months
        
        # Find deferred revenue account
        deferred_account = self.env['account.account'].search([
            ('code', '=', 'DEFERRED_REV'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not deferred_account:
            deferred_account = self.company_id.deferred_revenue_account_id
        
        if not deferred_account:
            _logger.warning(f"No deferred revenue account found for {self.name}")
            return
        
        # Create monthly recognition entries
        current_date = self.subscription_period_start.replace(day=1)
        
        for month in range(months):
            recognition_date = current_date + relativedelta(months=month)
            
            move_vals = {
                'journal_id': self.journal_id.id,
                'date': recognition_date,
                'ref': f'Revenue Recognition - {self.name}',
                'source_move_id': self.id,
                'line_ids': [
                    (0, 0, {
                        'name': f'Revenue Recognition - {self.name}',
                        'account_id': deferred_account.id,
                        'debit': monthly_amount,
                        'credit': 0.0,
                        'analytic_account_id': self.ams_subscription_id.account_analytic_id.id if self.ams_subscription_id and self.ams_subscription_id.account_analytic_id else False,
                    }),
                    (0, 0, {
                        'name': f'Revenue Recognition - {self.name}',
                        'account_id': self.invoice_line_ids[0].account_id.id,
                        'debit': 0.0,
                        'credit': monthly_amount,
                        'analytic_account_id': self.ams_subscription_id.account_analytic_id.id if self.ams_subscription_id and self.ams_subscription_id.account_analytic_id else False,
                    })
                ]
            }
            
            recognition_move = self.env['account.move'].create(move_vals)
            recognition_move.action_post()
        
        self.deferred_revenue_created = True
    
    def _create_chapter_allocation_entry(self):
        """Create chapter allocation entry"""
        if not self.ams_chapter_id or self.chapter_allocation_amount <= 0:
            return
        
        # Find or create allocation account
        allocation_account = self.env['account.account'].search([
            ('code', '=', 'CHAPTER_ALLOC'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not allocation_account:
            _logger.warning(f"No chapter allocation account found for {self.name}")
            return
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': f'Chapter Allocation - {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Allocation to {self.ams_chapter_id.name}',
                    'account_id': self.invoice_line_ids[0].account_id.id,
                    'debit': self.chapter_allocation_amount,
                    'credit': 0.0,
                    'analytic_account_id': self.ams_chapter_id.analytic_account_id.id if self.ams_chapter_id.analytic_account_id else False,
                }),
                (0, 0, {
                    'name': f'Allocation to {self.ams_chapter_id.name}',
                    'account_id': allocation_account.id,
                    'debit': 0.0,
                    'credit': self.chapter_allocation_amount,
                })
            ]
        }
        
        allocation_move = self.env['account.move'].create(move_vals)
        allocation_move.action_post()
    
    def _send_member_notification(self):
        """Send notification to member about new invoice"""
        if not self.partner_id.email or self.partner_id.suppress_financial_emails:
            return
        
        template = self.env.ref('ams_accounting.email_template_subscription_invoice', False)
        if template:
            try:
                template.send_mail(self.id, force_send=False)
                self.member_notification_sent = True
                self.member_notification_date = fields.Datetime.now()
            except Exception as e:
                _logger.error(f"Failed to send member notification for {self.name}: {str(e)}")
    
    def _update_subscription_status(self):
        """Update related subscription status"""
        if not self.ams_subscription_id:
            return
        
        subscription = self.ams_subscription_id
        
        # If this is a renewal invoice, update subscription state
        if self.is_ams_renewal_invoice:
            if self.payment_state == 'paid':
                subscription.action_confirm_renewal()
            else:
                subscription.state = 'pending_renewal'
    
    def action_send_member_portal_access(self):
        """Send member portal access for this invoice"""
        if not self.partner_id:
            raise UserError(_('No member associated with this invoice.'))
        
        template = self.env.ref('portal.mail_template_data_portal_welcome', False)
        if template:
            template.send_mail(self.partner_id.id, force_send=True)
        
        self.member_portal_access = True
        self.message_post(body=_('Portal access sent to member.'))
    
    def action_create_payment_plan(self):
        """Create payment plan for this invoice"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Payment Plan',
            'res_model': 'ams.payment.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_total_amount': self.amount_residual,
                'default_source_invoice_id': self.id,
            }
        }
    
    def action_follow_up_reminder(self):
        """Send follow-up reminder for overdue invoice"""
        if self.days_overdue <= 0:
            raise UserError(_('Invoice is not overdue.'))
        
        # Determine follow-up level
        if self.days_overdue <= 30:
            level = 1
        elif self.days_overdue <= 60:
            level = 2
        elif self.days_overdue <= 90:
            level = 3
        else:
            level = 4
        
        self.follow_up_level = level
        self.last_follow_up_date = fields.Date.today()
        
        # Update collection status
        if level == 1:
            self.collection_status = 'reminder_sent'
        elif level <= 3:
            self.collection_status = 'follow_up'
        else:
            self.collection_status = 'collection_agency'
        
        # Send follow-up email
        template_name = f'ams_accounting.email_template_follow_up_level_{level}'
        template = self.env.ref(template_name, False)
        
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_(f'Follow-up reminder (Level {level}) sent to member.'))
        
        return True
    
    def action_view_subscription_details(self):
        """View related subscription details"""
        if not self.ams_subscription_id:
            raise UserError(_('No subscription associated with this invoice.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscription Details',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.ams_subscription_id.id,
        }
    
    def action_view_member_financial_summary(self):
        """View member's financial summary"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Financial Summary - {self.partner_id.name}',
            'res_model': 'ams.member.financial.summary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
            }
        }
    
    @api.model
    def _cron_process_overdue_invoices(self):
        """Cron job to process overdue invoices"""
        today = fields.Date.today()
        
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),
            ('is_ams_subscription_invoice', '=', True)
        ])
        
        processed_count = 0
        
        for invoice in overdue_invoices:
            try:
                # Auto-send follow-up based on days overdue
                if invoice.days_overdue in [7, 30, 60, 90] and invoice.last_follow_up_date != today:
                    invoice.action_follow_up_reminder()
                    processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to process overdue invoice {invoice.name}: {str(e)}")
        
        _logger.info(f"Processed {processed_count} overdue invoices")
        return processed_count
    
    @api.model
    def get_ams_invoice_analytics(self, date_from=None, date_to=None):
        """Get AMS invoice analytics for dashboard"""
        if not date_from:
            date_from = fields.Date.today().replace(month=1, day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('is_ams_subscription_invoice', '=', True)
        ]
        
        invoices = self.search(domain)
        
        analytics = {
            'total_invoices': len(invoices),
            'total_amount': sum(invoices.mapped('amount_total')),
            'paid_invoices': len(invoices.filtered(lambda i: i.payment_state == 'paid')),
            'overdue_invoices': len(invoices.filtered(lambda i: i.days_overdue > 0)),
            'renewal_invoices': len(invoices.filtered('is_ams_renewal_invoice')),
            'chapter_fee_invoices': len(invoices.filtered('is_ams_chapter_fee')),
            'first_time_invoices': len(invoices.filtered('is_first_invoice')),
            'average_invoice_amount': sum(invoices.mapped('amount_total')) / len(invoices) if invoices else 0,
            'collection_efficiency': len(invoices.filtered(lambda i: i.payment_state == 'paid')) / len(invoices) * 100 if invoices else 0,
        }
        
        return analytics