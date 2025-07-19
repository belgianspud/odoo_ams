from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSSubscriptionModification(models.Model):
    """
    Model to track subscription modifications and their accounting impact
    """
    _name = 'ams.subscription.modification'
    _description = 'AMS Subscription Modification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'modification_number'

    # ========================
    # BASIC INFORMATION
    # ========================
    
    modification_number = fields.Char('Modification Number', required=True, 
        copy=False, readonly=True, default=lambda self: _('New'))
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', 
        required=True, ondelete='cascade', tracking=True)
    partner_id = fields.Many2one('res.partner', related='subscription_id.partner_id', 
        store=True, readonly=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', 
        readonly=True)
    
    # ========================
    # MODIFICATION DETAILS
    # ========================
    
    # Modification Type
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('addon', 'Add-on Service'),
        ('removal', 'Service Removal'),
        ('discount', 'Discount Applied'),
        ('penalty', 'Penalty/Fee'),
        ('proration', 'Proration Adjustment'),
        ('suspension', 'Temporary Suspension'),
        ('reactivation', 'Reactivation'),
        ('term_change', 'Term Length Change'),
        ('billing_change', 'Billing Frequency Change'),
        ('product_change', 'Product Change'),
        ('chapter_change', 'Chapter Change'),
        ('other', 'Other Modification')
    ], string='Modification Type', required=True, tracking=True)
    
    # Amount Changes
    original_amount = fields.Float('Original Amount', required=True, tracking=True)
    new_amount = fields.Float('New Amount', required=True, tracking=True)
    amount_change = fields.Float('Amount Change', compute='_compute_amount_change', 
        store=True, tracking=True)
    amount_change_percentage = fields.Float('Change %', compute='_compute_amount_change', 
        store=True)
    
    # Effective Dates
    effective_date = fields.Date('Effective Date', required=True, 
        default=fields.Date.today, tracking=True)
    end_date = fields.Date('End Date', 
        help="End date for temporary modifications (suspensions, discounts, etc.)")
    
    # Product/Service Changes
    original_product_id = fields.Many2one('product.product', 'Original Product')
    new_product_id = fields.Many2one('product.product', 'New Product')
    
    # Subscription Term Changes
    original_term_months = fields.Integer('Original Term (Months)')
    new_term_months = fields.Integer('New Term (Months)')
    
    # Billing Frequency Changes
    original_billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Original Billing Frequency')
    new_billing_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='New Billing Frequency')
    
    # Chapter Changes
    original_chapter_id = fields.Many2one('ams.chapter', 'Original Chapter')
    new_chapter_id = fields.Many2one('ams.chapter', 'New Chapter')
    
    # ========================
    # PRORATION AND BILLING
    # ========================
    
    # Proration Settings
    proration_method = fields.Selection([
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('none', 'No Proration')
    ], string='Proration Method', default='daily')
    
    proration_amount = fields.Float('Proration Amount', 
        compute='_compute_proration_amount', store=True)
    proration_days = fields.Integer('Proration Days', 
        compute='_compute_proration_amount', store=True)
    
    # Credit/Charge Management
    credit_amount = fields.Float('Credit Amount', default=0.0,
        help="Amount to credit for downgrades or service removals")
    charge_amount = fields.Float('Charge Amount', default=0.0,
        help="Amount to charge for upgrades or add-ons")
    net_amount = fields.Float('Net Amount', compute='_compute_net_amount', store=True)
    
    # Invoice Integration
    create_credit_note = fields.Boolean('Create Credit Note', default=False)
    create_invoice = fields.Boolean('Create Invoice', default=False)
    immediate_billing = fields.Boolean('Immediate Billing', default=True,
        help="Bill the modification immediately vs. next billing cycle")
    
    # ========================
    # APPROVAL WORKFLOW
    # ========================
    
    # Approval Requirements
    requires_approval = fields.Boolean('Requires Approval', 
        compute='_compute_approval_requirements', store=True)
    approval_threshold = fields.Float('Approval Threshold', 
        default=lambda self: self.env.company.modification_approval_limit or 100.0)
    
    # Approval Tracking
    approved_by = fields.Many2one('res.users', 'Approved By', tracking=True)
    approval_date = fields.Datetime('Approval Date', tracking=True)
    approval_notes = fields.Text('Approval Notes')
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    
    # ========================
    # REASON AND DOCUMENTATION
    # ========================
    
    # Reason Tracking
    reason_category = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('system_upgrade', 'System Upgrade'),
        ('pricing_change', 'Pricing Change'),
        ('service_discontinuation', 'Service Discontinuation'),
        ('compliance', 'Compliance Requirement'),
        ('technical_issue', 'Technical Issue'),
        ('billing_correction', 'Billing Correction'),
        ('customer_service', 'Customer Service'),
        ('retention', 'Customer Retention'),
        ('other', 'Other')
    ], string='Reason Category', required=True, tracking=True)
    
    description = fields.Text('Modification Description', required=True, tracking=True)
    internal_notes = fields.Text('Internal Notes')
    customer_communication = fields.Text('Customer Communication')
    
    # Supporting Documentation
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    
    # ========================
    # ACCOUNTING INTEGRATION
    # ========================
    
    # Generated Accounting Entries
    move_ids = fields.One2many('account.move', 'subscription_modification_id', 
        'Accounting Entries', readonly=True)
    credit_note_id = fields.Many2one('account.move', 'Credit Note', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    
    # Revenue Recognition Impact
    revenue_recognition_impact = fields.Selection([
        ('none', 'No Impact'),
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Recognition'),
        ('reversal', 'Revenue Reversal')
    ], string='Revenue Recognition Impact', default='none')
    
    # Journal Configuration
    journal_id = fields.Many2one('account.journal', 'Journal', 
        domain="[('type', '=', 'sale')]")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    
    # ========================
    # PROCESSING TRACKING
    # ========================
    
    processed = fields.Boolean('Processed', default=False, readonly=True, tracking=True)
    processed_date = fields.Datetime('Processed Date', readonly=True)
    processed_by = fields.Many2one('res.users', 'Processed By', readonly=True)
    
    # Rollback Information
    can_rollback = fields.Boolean('Can Rollback', compute='_compute_can_rollback')
    rollback_deadline = fields.Datetime('Rollback Deadline', 
        compute='_compute_rollback_deadline', store=True)
    
    # Impact Tracking
    related_modifications = fields.One2many('ams.subscription.modification', 
        'original_modification_id', 'Related Modifications')
    original_modification_id = fields.Many2one('ams.subscription.modification', 
        'Original Modification', help="For rollback modifications")
    
    # ========================
    # COMPUTED FIELDS
    # ========================
    
    @api.depends('original_amount', 'new_amount')
    def _compute_amount_change(self):
        for modification in self:
            modification.amount_change = modification.new_amount - modification.original_amount
            
            if modification.original_amount != 0:
                modification.amount_change_percentage = (
                    modification.amount_change / modification.original_amount) * 100
            else:
                modification.amount_change_percentage = 0.0
    
    @api.depends('credit_amount', 'charge_amount')
    def _compute_net_amount(self):
        for modification in self:
            modification.net_amount = modification.charge_amount - modification.credit_amount
    
    @api.depends('amount_change', 'modification_type')
    def _compute_approval_requirements(self):
        for modification in self:
            # Require approval for significant changes or certain types
            significant_change = abs(modification.amount_change) > modification.approval_threshold
            special_types = modification.modification_type in ['downgrade', 'penalty', 'suspension']
            
            modification.requires_approval = significant_change or special_types
    
    @api.depends('effective_date', 'subscription_id', 'proration_method')
    def _compute_proration_amount(self):
        for modification in self:
            if modification.proration_method == 'none' or not modification.subscription_id:
                modification.proration_amount = 0.0
                modification.proration_days = 0
                continue
            
            # Calculate proration based on remaining subscription period
            subscription = modification.subscription_id
            
            if not subscription.end_date:
                modification.proration_amount = 0.0
                modification.proration_days = 0
                continue
            
            # Calculate remaining days
            remaining_days = (subscription.end_date - modification.effective_date).days
            
            if remaining_days <= 0:
                modification.proration_amount = 0.0
                modification.proration_days = 0
                continue
            
            modification.proration_days = remaining_days
            
            # Calculate total period days
            if subscription.recurring_period == 'monthly':
                total_days = 30  # Simplified
            elif subscription.recurring_period == 'quarterly':
                total_days = 90
            elif subscription.recurring_period == 'yearly':
                total_days = 365
            else:
                total_days = 30
            
            # Calculate proration amount
            daily_rate = modification.amount_change / total_days
            modification.proration_amount = daily_rate * remaining_days
    
    @api.depends('processed', 'processed_date')
    def _compute_can_rollback(self):
        for modification in self:
            if not modification.processed:
                modification.can_rollback = False
                continue
            
            # Allow rollback within 30 days of processing
            rollback_window = timedelta(days=30)
            can_rollback = (
                modification.processed_date and 
                fields.Datetime.now() - modification.processed_date <= rollback_window
            )
            
            modification.can_rollback = can_rollback
    
    @api.depends('processed_date')
    def _compute_rollback_deadline(self):
        for modification in self:
            if modification.processed_date:
                modification.rollback_deadline = modification.processed_date + timedelta(days=30)
            else:
                modification.rollback_deadline = False
    
    # ========================
    # CRUD OPERATIONS
    # ========================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('modification_number', _('New')) == _('New'):
                vals['modification_number'] = self.env['ir.sequence'].next_by_code(
                    'ams.subscription.modification') or _('New')
        
        modifications = super().create(vals_list)
        
        for modification in modifications:
            # Auto-populate original values from subscription
            modification._populate_original_values()
            
            # Set approval requirements
            modification._check_approval_requirements()
        
        return modifications
    
    def _populate_original_values(self):
        """Populate original values from subscription"""
        if not self.subscription_id:
            return
        
        subscription = self.subscription_id
        
        if not self.original_amount:
            self.original_amount = subscription.amount
        
        if not self.original_product_id:
            self.original_product_id = subscription.product_id
        
        if not self.original_chapter_id:
            self.original_chapter_id = subscription.chapter_id
        
        if not self.original_billing_frequency:
            self.original_billing_frequency = subscription.recurring_period
        
        # Set journal and analytic account from subscription
        if not self.journal_id and hasattr(subscription, 'journal_id'):
            self.journal_id = subscription.journal_id
        
        if not self.analytic_account_id:
            self.analytic_account_id = subscription.account_analytic_id
    
    def _check_approval_requirements(self):
        """Check if modification requires approval and update state"""
        if self.requires_approval and self.state == 'draft':
            self.state = 'pending_approval'
            
            # Create approval activity
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Subscription Modification Approval: {self.modification_number}',
                note=f'Modification requires approval: {self.modification_type} - {self.amount_change}',
                user_id=self._get_approver_user().id
            )
    
    def _get_approver_user(self):
        """Get the user who should approve this modification"""
        # Default to account manager
        manager_group = self.env.ref('account.group_account_manager', False)
        if manager_group and manager_group.users:
            return manager_group.users[0]
        return self.env.user
    
    # ========================
    # WORKFLOW ACTIONS
    # ========================
    
    def action_submit_for_approval(self):
        """Submit modification for approval"""
        for modification in self:
            if modification.state != 'draft':
                raise UserError(_('Only draft modifications can be submitted for approval.'))
            
            modification.state = 'pending_approval'
            modification.message_post(body=_('Modification submitted for approval.'))
    
    def action_approve(self):
        """Approve the modification"""
        for modification in self:
            if modification.state != 'pending_approval':
                raise UserError(_('Only pending modifications can be approved.'))
            
            modification.approved_by = self.env.user.id
            modification.approval_date = fields.Datetime.now()
            modification.state = 'approved'
            
            modification.message_post(body=_('Modification approved by %s.') % self.env.user.name)
            
            # Auto-process if configured
            if modification.immediate_billing:
                modification.action_process()
    
    def action_reject(self):
        """Reject the modification"""
        for modification in self:
            if modification.state != 'pending_approval':
                raise UserError(_('Only pending modifications can be rejected.'))
            
            modification.state = 'rejected'
            modification.message_post(body=_('Modification rejected by %s.') % self.env.user.name)
    
    def action_process(self):
        """Process the approved modification"""
        for modification in self:
            if modification.state not in ['approved', 'draft']:
                raise UserError(_('Only approved modifications can be processed.'))
            
            if modification.requires_approval and not modification.approved_by:
                raise UserError(_('Modification requires approval before processing.'))
            
            try:
                # Apply modification to subscription
                modification._apply_to_subscription()
                
                # Create accounting entries
                modification._create_accounting_entries()
                
                # Update status
                modification.processed = True
                modification.processed_date = fields.Datetime.now()
                modification.processed_by = self.env.user.id
                modification.state = 'processed'
                
                modification.message_post(
                    body=_('Modification processed successfully.'),
                    subject=_('Subscription Modification Processed')
                )
                
            except Exception as e:
                _logger.error(f"Failed to process modification {modification.modification_number}: {str(e)}")
                raise UserError(_('Failed to process modification: %s') % str(e))
    
    def action_cancel(self):
        """Cancel the modification"""
        for modification in self:
            if modification.state == 'processed':
                raise UserError(_('Cannot cancel processed modifications. Use rollback instead.'))
            
            modification.state = 'cancelled'
            modification.message_post(body=_('Modification cancelled.'))
    
    def action_rollback(self):
        """Rollback a processed modification"""
        for modification in self:
            if not modification.can_rollback:
                raise UserError(_('This modification cannot be rolled back.'))
            
            # Create rollback modification
            rollback_vals = {
                'subscription_id': modification.subscription_id.id,
                'modification_type': 'other',
                'description': f'Rollback of {modification.modification_number}: {modification.description}',
                'original_amount': modification.new_amount,
                'new_amount': modification.original_amount,
                'effective_date': fields.Date.today(),
                'original_modification_id': modification.id,
                'reason_category': 'billing_correction',
                'immediate_billing': True,
            }
            
            rollback_modification = self.create(rollback_vals)
            rollback_modification.action_process()
            
            modification.message_post(
                body=_('Modification rolled back via %s.') % rollback_modification.modification_number)
    
    # ========================
    # BUSINESS LOGIC
    # ========================
    
    def _apply_to_subscription(self):
        """Apply the modification to the subscription"""
        subscription = self.subscription_id
        
        # Update subscription based on modification type
        if self.modification_type in ['upgrade', 'downgrade', 'proration']:
            subscription.amount = self.new_amount
        
        elif self.modification_type == 'product_change':
            if self.new_product_id:
                subscription.product_id = self.new_product_id
                subscription.amount = self.new_amount
        
        elif self.modification_type == 'chapter_change':
            if self.new_chapter_id:
                subscription.chapter_id = self.new_chapter_id
        
        elif self.modification_type == 'billing_change':
            if self.new_billing_frequency:
                subscription.recurring_period = self.new_billing_frequency
                subscription.amount = self.new_amount
        
        elif self.modification_type == 'term_change':
            if self.new_term_months:
                # Recalculate end date
                subscription.end_date = subscription.start_date + relativedelta(
                    months=self.new_term_months)
        
        elif self.modification_type == 'suspension':
            subscription.state = 'suspended'
            subscription.suspension_date = self.effective_date
        
        elif self.modification_type == 'reactivation':
            subscription.state = 'active'
            subscription.suspension_date = False
        
        # Log the change
        subscription.message_post(
            body=_('Subscription modified via %s: %s') % (
                self.modification_number, self.description),
            subject=_('Subscription Modification Applied')
        )
    
    def _create_accounting_entries(self):
        """Create necessary accounting entries for the modification"""
        if not self.journal_id:
            # Get default subscription journal
            self.journal_id = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('is_ams_journal', '=', True),
                ('ams_journal_type', '=', 'subscription')
            ], limit=1)
        
        if not self.journal_id:
            raise UserError(_('No suitable journal found for subscription modifications.'))
        
        # Create credit note for downgrades/removals
        if self.credit_amount > 0 and self.create_credit_note:
            self._create_credit_note()
        
        # Create invoice for upgrades/add-ons
        if self.charge_amount > 0 and self.create_invoice:
            self._create_modification_invoice()
        
        # Create adjustment entry for amount changes
        if self.net_amount != 0:
            self._create_adjustment_entry()
    
    def _create_credit_note(self):
        """Create credit note for downgrades or service removals"""
        credit_note_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_refund',
            'journal_id': self.journal_id.id,
            'invoice_date': self.effective_date,
            'ref': f'Credit Note - {self.modification_number}',
            'subscription_modification_id': self.id,
            'line_ids': [(0, 0, {
                'name': f'Credit for {self.modification_type}: {self.description}',
                'quantity': 1,
                'price_unit': self.credit_amount,
                'account_id': self._get_revenue_account().id,
                'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
            })]
        }
        
        credit_note = self.env['account.move'].create(credit_note_vals)
        credit_note.action_post()
        
        self.credit_note_id = credit_note.id
        return credit_note
    
    def _create_modification_invoice(self):
        """Create invoice for upgrades or add-ons"""
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'journal_id': self.journal_id.id,
            'invoice_date': self.effective_date,
            'ref': f'Modification Invoice - {self.modification_number}',
            'subscription_modification_id': self.id,
            'line_ids': [(0, 0, {
                'name': f'Charge for {self.modification_type}: {self.description}',
                'quantity': 1,
                'price_unit': self.charge_amount,
                'account_id': self._get_revenue_account().id,
                'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        self.invoice_id = invoice.id
        return invoice
    
    def _create_adjustment_entry(self):
        """Create general adjustment entry for amount changes"""
        if abs(self.net_amount) < 0.01:  # Skip negligible amounts
            return
        
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.effective_date,
            'ref': f'Subscription Modification - {self.modification_number}',
            'subscription_modification_id': self.id,
            'line_ids': []
        }
        
        revenue_account = self._get_revenue_account()
        receivable_account = self.partner_id.property_account_receivable_id
        
        if self.net_amount > 0:
            # Charge: Debit Receivable, Credit Revenue
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Subscription Modification: {self.description}',
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.net_amount,
                    'credit': 0.0,
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                }),
                (0, 0, {
                    'name': f'Subscription Modification: {self.description}',
                    'account_id': revenue_account.id,
                    'debit': 0.0,
                    'credit': self.net_amount,
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                })
            ]
        else:
            # Credit: Debit Revenue, Credit Receivable
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Subscription Modification: {self.description}',
                    'account_id': revenue_account.id,
                    'debit': abs(self.net_amount),
                    'credit': 0.0,
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                }),
                (0, 0, {
                    'name': f'Subscription Modification: {self.description}',
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': abs(self.net_amount),
                    'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id else False,
                })
            ]
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        return move
    
    def _get_revenue_account(self):
        """Get appropriate revenue account for the modification"""
        # Try to get from subscription type
        if self.subscription_id.subscription_type_id and hasattr(self.subscription_id.subscription_type_id, 'revenue_account_id'):
            return self.subscription_id.subscription_type_id.revenue_account_id
        
        # Try to get from company AMS settings
        if self.company_id.ams_subscription_revenue_account_id:
            return self.company_id.ams_subscription_revenue_account_id
        
        # Fallback to income account
        return self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
    
    # ========================
    # UTILITY METHODS
    # ========================
    
    def action_view_accounting_entries(self):
        """View related accounting entries"""
        move_ids = self.move_ids.ids
        if self.credit_note_id:
            move_ids.append(self.credit_note_id.id)
        if self.invoice_id:
            move_ids.append(self.invoice_id.id)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Accounting Entries - {self.modification_number}',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'create': False}
        }
    
    def action_preview_impact(self):
        """Preview the financial impact of the modification"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modification Impact Preview',
            'res_model': 'ams.subscription.modification.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_modification_id': self.id,
            }
        }
    
    @api.model
    def get_modification_statistics(self, date_from=None, date_to=None):
        """Get modification statistics for reporting"""
        if not date_from:
            date_from = fields.Date.today().replace(month=1, day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        domain = [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('state', '=', 'processed')
        ]
        
        modifications = self.search(domain)
        
        stats = {
            'total_modifications': len(modifications),
            'total_value_impact': sum(modifications.mapped('net_amount')),
            'by_type': {},
            'by_reason': {},
            'approval_rate': 0.0,
            'average_processing_time': 0.0,
        }
        
        # Group by type
        for mod_type in modifications.mapped('modification_type'):
            type_mods = modifications.filtered(lambda m: m.modification_type == mod_type)
            stats['by_type'][mod_type] = {
                'count': len(type_mods),
                'value_impact': sum(type_mods.mapped('net_amount'))
            }
        
        # Group by reason
        for reason in modifications.mapped('reason_category'):
            reason_mods = modifications.filtered(lambda m: m.reason_category == reason)
            stats['by_reason'][reason] = len(reason_mods)
        
        # Calculate approval rate
        total_requiring_approval = len(modifications.filtered('requires_approval'))
        if total_requiring_approval > 0:
            approved = len(modifications.filtered(lambda m: m.requires_approval and m.approved_by))
            stats['approval_rate'] = (approved / total_requiring_approval) * 100
        
        return stats
    
    # ========================
    # CONSTRAINTS AND VALIDATION
    # ========================
    
    @api.constrains('original_amount', 'new_amount')
    def _check_amounts(self):
        for modification in self:
            if modification.original_amount < 0:
                raise ValidationError(_('Original amount cannot be negative.'))
            if modification.new_amount < 0:
                raise ValidationError(_('New amount cannot be negative.'))
    
    @api.constrains('effective_date', 'end_date')
    def _check_dates(self):
        for modification in self:
            if modification.end_date and modification.end_date < modification.effective_date:
                raise ValidationError(_('End date cannot be before effective date.'))
    
    @api.constrains('credit_amount', 'charge_amount')
    def _check_credit_charge_amounts(self):
        for modification in self:
            if modification.credit_amount < 0:
                raise ValidationError(_('Credit amount cannot be negative.'))
            if modification.charge_amount < 0:
                raise ValidationError(_('Charge amount cannot be negative.'))
    
    @api.constrains('proration_days')
    def _check_proration_days(self):
        for modification in self:
            if modification.proration_days < 0:
                raise ValidationError(_('Proration days cannot be negative.'))


# Add subscription_modification_id field to account.move
class AccountMove(models.Model):
    """
    Enhanced account move to track subscription modifications
    """
    _inherit = 'account.move'
    
    subscription_modification_id = fields.Many2one('ams.subscription.modification', 
        'Subscription Modification', readonly=True,
        help="The subscription modification that generated this accounting entry")


# Integration with subscription model
class AMSSubscription(models.Model):
    """
    Enhanced subscription with modification tracking
    """
    _inherit = 'ams.subscription'
    
    modification_ids = fields.One2many('ams.subscription.modification', 'subscription_id', 
        'Modifications', help="All modifications made to this subscription")
    modification_count = fields.Integer('Modification Count', 
        compute='_compute_modification_count', store=True)
    last_modification_date = fields.Date('Last Modification Date', 
        compute='_compute_last_modification', store=True)
    
    @api.depends('modification_ids')
    def _compute_modification_count(self):
        for subscription in self:
            subscription.modification_count = len(subscription.modification_ids.filtered(
                lambda m: m.state == 'processed'))
    
    @api.depends('modification_ids', 'modification_ids.processed_date')
    def _compute_last_modification(self):
        for subscription in self:
            processed_mods = subscription.modification_ids.filtered(
                lambda m: m.state == 'processed' and m.processed_date)
            
            if processed_mods:
                latest_mod = processed_mods.sorted('processed_date', reverse=True)[0]
                subscription.last_modification_date = latest_mod.processed_date.date()
            else:
                subscription.last_modification_date = False
    
    def action_create_modification(self):
        """Create a new modification for this subscription"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Subscription Modification',
            'res_model': 'ams.subscription.modification',
            'view_mode': 'form',
            'context': {
                'default_subscription_id': self.id,
                'default_original_amount': self.amount,
                'default_new_amount': self.amount,
                'default_original_product_id': self.product_id.id if self.product_id else False,
                'default_original_chapter_id': self.chapter_id.id if self.chapter_id else False,
                'default_original_billing_frequency': self.recurring_period,
            }
        }
    
    def action_view_modifications(self):
        """View all modifications for this subscription"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Modifications - {self.name}',
            'res_model': 'ams.subscription.modification',
            'view_mode': 'tree,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id}
        }


# Sequence for modification numbers - this would typically go in data files
# but including here for completeness
class IrSequence(models.Model):
    """
    Ensure sequence exists for subscription modifications
    """
    _inherit = 'ir.sequence'
    
    @api.model
    def _get_ams_modification_sequence(self):
        """Get or create sequence for subscription modifications"""
        sequence = self.search([('code', '=', 'ams.subscription.modification')], limit=1)
        if not sequence:
            sequence = self.create({
                'name': 'AMS Subscription Modification',
                'code': 'ams.subscription.modification',
                'prefix': 'MOD-%(year)s-',
                'suffix': '',
                'padding': 5,
                'number_increment': 1,
                'company_id': False,  # Global sequence
            })
        return sequence