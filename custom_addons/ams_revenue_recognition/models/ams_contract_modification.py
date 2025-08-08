# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSContractModification(models.Model):
    """Contract Modifications affecting Revenue Recognition"""
    _name = 'ams.contract.modification'
    _description = 'AMS Contract Modification'
    _order = 'modification_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Modification Name',
        required=True,
        tracking=True,
        help='Name of the contract modification'
    )
    
    schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Revenue schedule being modified'
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        related='schedule_id.subscription_id',
        store=True,
        help='Related subscription'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='schedule_id.partner_id',
        store=True,
        help='Customer from schedule'
    )
    
    # Modification Details
    modification_type = fields.Selection([
        ('upgrade', 'Subscription Upgrade'),
        ('downgrade', 'Subscription Downgrade'),
        ('cancellation', 'Early Cancellation'),
        ('extension', 'Contract Extension'),
        ('price_change', 'Price Change'),
        ('quantity_change', 'Quantity Change'),
        ('pause', 'Service Pause'),
        ('resume', 'Service Resume'),
        ('termination', 'Early Termination'),
        ('other', 'Other Modification'),
    ], string='Modification Type', required=True, tracking=True,
       help='Type of contract modification')
    
    modification_date = fields.Date(
        string='Modification Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Date when modification takes effect'
    )
    
    effective_date = fields.Date(
        string='Effective Date',
        help='Date when modification becomes effective (may differ from modification date)'
    )
    
    reason = fields.Text(
        string='Modification Reason',
        required=True,
        tracking=True,
        help='Detailed reason for the modification'
    )
    
    # Original Contract Values
    original_contract_value = fields.Float(
        string='Original Contract Value',
        readonly=True,
        help='Original total contract value before modification'
    )
    
    original_start_date = fields.Date(
        string='Original Start Date',
        readonly=True,
        help='Original contract start date'
    )
    
    original_end_date = fields.Date(
        string='Original End Date',
        readonly=True,
        help='Original contract end date'
    )
    
    # New Contract Values
    new_contract_value = fields.Float(
        string='New Contract Value',
        tracking=True,
        help='New total contract value after modification'
    )
    
    new_start_date = fields.Date(
        string='New Start Date',
        help='New contract start date (if changed)'
    )
    
    new_end_date = fields.Date(
        string='New End Date',
        help='New contract end date (if changed)'
    )
    
    # Financial Impact
    value_change = fields.Float(
        string='Value Change',
        compute='_compute_financial_impact',
        store=True,
        help='Change in total contract value'
    )
    
    recognized_to_date = fields.Float(
        string='Revenue Recognized to Date',
        help='Revenue already recognized before modification'
    )
    
    unrecognized_amount = fields.Float(
        string='Unrecognized Amount',
        compute='_compute_financial_impact',
        store=True,
        help='Revenue not yet recognized at modification date'
    )
    
    adjustment_amount = fields.Float(
        string='Revenue Adjustment',
        compute='_compute_financial_impact',
        store=True,
        help='Required revenue adjustment due to modification'
    )
    
    # New Schedule Information
    new_schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='New Revenue Schedule',
        readonly=True,
        help='New revenue schedule created from modification'
    )
    
    # Processing Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True,
       help='Processing status of the modification')
    
    processing_method = fields.Selection([
        ('prospective', 'Prospective (Forward-looking)'),
        ('retrospective', 'Retrospective (Catch-up)'),
        ('cumulative', 'Cumulative Catch-up'),
    ], string='Processing Method', default='prospective',
       help='How to handle the contract modification')
    
    # Journal Entries
    adjustment_move_id = fields.Many2one(
        'account.move',
        string='Adjustment Journal Entry',
        readonly=True,
        help='Journal entry for revenue adjustment'
    )
    
    # Supporting Documentation
    supporting_document = fields.Binary(
        string='Supporting Document',
        help='Contract amendment or supporting documentation'
    )
    
    supporting_document_name = fields.Char(
        string='Document Name',
        help='Name of supporting document'
    )
    
    # User Tracking
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True,
        help='User who processed the modification'
    )
    
    processed_date = fields.Datetime(
        string='Processed Date',
        readonly=True,
        help='When the modification was processed'
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help='User who approved the modification'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date',
        help='When the modification was approved'
    )
    
    # ASC 606 Compliance Fields
    is_contract_modification = fields.Boolean(
        string='Is Contract Modification',
        default=True,
        help='This change qualifies as a contract modification under ASC 606'
    )
    
    modification_accounting = fields.Selection([
        ('separate_contract', 'Treat as Separate Contract'),
        ('modify_existing', 'Modify Existing Contract'),
        ('terminate_new', 'Terminate and Create New'),
    ], string='Modification Accounting', default='modify_existing',
       help='ASC 606 accounting treatment for this modification')
    
    performance_obligation_impact = fields.Text(
        string='Performance Obligation Impact',
        help='Description of how this modification affects performance obligations'
    )
    
    # Computed Fields
    @api.depends('new_contract_value', 'original_contract_value', 'recognized_to_date')
    def _compute_financial_impact(self):
        """Compute financial impact of modification"""
        for modification in self:
            modification.value_change = (modification.new_contract_value or 0) - (modification.original_contract_value or 0)
            modification.unrecognized_amount = (modification.original_contract_value or 0) - (modification.recognized_to_date or 0)
            
            # Calculate adjustment needed
            if modification.processing_method == 'prospective':
                # Prospective: adjust future recognition only
                modification.adjustment_amount = 0
            elif modification.processing_method == 'retrospective':
                # Retrospective: adjust as if change was always in effect
                if modification.original_contract_value and modification.new_contract_value:
                    recognition_ratio = modification.recognized_to_date / modification.original_contract_value
                    should_have_recognized = modification.new_contract_value * recognition_ratio
                    modification.adjustment_amount = should_have_recognized - modification.recognized_to_date
                else:
                    modification.adjustment_amount = 0
            else:
                # Cumulative: catch-up adjustment
                modification.adjustment_amount = modification.value_change
    
    # Constraints and Validations
    @api.constrains('modification_date', 'effective_date')
    def _check_dates(self):
        """Validate modification dates"""
        for modification in self:
            if modification.effective_date and modification.effective_date < modification.modification_date:
                raise ValidationError("Effective date cannot be before modification date.")
    
    @api.constrains('new_contract_value')
    def _check_new_contract_value(self):
        """Validate new contract value"""
        for modification in self:
            if modification.new_contract_value is not None and modification.new_contract_value < 0:
                raise ValidationError("New contract value cannot be negative.")
    
    # CRUD Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create method"""
        for vals in vals_list:
            # Auto-generate name if not provided
            if not vals.get('name'):
                schedule = self.env['ams.revenue.schedule'].browse(vals.get('schedule_id'))
                mod_type = vals.get('modification_type', 'modification')
                vals['name'] = f"{mod_type.title()} - {schedule.name}"
            
            # Set effective date to modification date if not provided
            if not vals.get('effective_date'):
                vals['effective_date'] = vals.get('modification_date')
        
        modifications = super().create(vals_list)
        
        for modification in modifications:
            modification._capture_original_values()
        
        return modifications
    
    def write(self, vals):
        """Enhanced write method"""
        # Prevent changes to processed modifications
        if any(mod.state == 'processed' for mod in self):
            allowed_fields = {'reason', 'supporting_document', 'supporting_document_name'}
            if not set(vals.keys()).issubset(allowed_fields):
                raise UserError("Cannot modify processed contract modifications.")
        
        return super().write(vals)
    
    # Business Logic Methods
    def action_validate(self):
        """Validate the contract modification"""
        for modification in self:
            if modification.state != 'draft':
                raise UserError(f"Cannot validate modification in {modification.state} state.")
            
            modification._validate_modification()
            modification.state = 'validated'
            modification.message_post(body="Contract modification validated.")
    
    def action_process(self):
        """Process the contract modification"""
        for modification in self:
            if modification.state != 'validated':
                raise UserError(f"Modification must be validated before processing.")
            
            try:
                modification._process_modification()
                modification._mark_as_processed()
                modification.message_post(body="Contract modification processed successfully.")
                
            except Exception as e:
                modification.message_post(body=f"Processing failed: {str(e)}")
                raise
    
    def action_cancel(self):
        """Cancel the contract modification"""
        for modification in self:
            if modification.state == 'processed':
                raise UserError("Cannot cancel processed modifications. Create a reversal instead.")
            
            modification.state = 'cancelled'
            modification.message_post(body="Contract modification cancelled.")
    
    def action_approve(self):
        """Approve the contract modification"""
        for modification in self:
            if modification.state not in ['draft', 'validated']:
                raise UserError(f"Cannot approve modification in {modification.state} state.")
            
            modification.write({
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            
            if modification.state == 'draft':
                modification.action_validate()
            
            modification.message_post(body=f"Contract modification approved by {self.env.user.name}.")
    
    def _capture_original_values(self):
        """Capture original contract values"""
        self.ensure_one()
        
        schedule = self.schedule_id
        
        self.write({
            'original_contract_value': schedule.total_contract_value,
            'original_start_date': schedule.start_date,
            'original_end_date': schedule.end_date,
            'recognized_to_date': schedule.recognized_revenue,
        })
    
    def _validate_modification(self):
        """Validate modification can be processed"""
        self.ensure_one()
        
        if not self.schedule_id:
            raise UserError("Modification must be linked to a revenue schedule.")
        
        if self.schedule_id.state not in ['active']:
            raise UserError("Can only modify active revenue schedules.")
        
        if not self.new_contract_value and self.modification_type not in ['cancellation', 'termination']:
            raise UserError("New contract value is required for this modification type.")
        
        if self.modification_date < self.schedule_id.start_date:
            raise UserError("Modification date cannot be before schedule start date.")
        
        # Validate modification makes sense
        if self.modification_type == 'upgrade' and self.new_contract_value <= self.original_contract_value:
            raise UserError("Upgrade must increase contract value.")
        
        if self.modification_type == 'downgrade' and self.new_contract_value >= self.original_contract_value:
            raise UserError("Downgrade must decrease contract value.")
    
    def _process_modification(self):
        """Process the contract modification"""
        self.ensure_one()
        
        if self.modification_type in ['cancellation', 'termination']:
            self._process_termination()
        elif self.modification_type in ['upgrade', 'downgrade', 'price_change']:
            self._process_value_change()
        elif self.modification_type == 'extension':
            self._process_extension()
        elif self.modification_type in ['pause', 'resume']:
            self._process_pause_resume()
        else:
            self._process_general_modification()
    
    def _process_value_change(self):
        """Process modifications that change contract value"""
        self.ensure_one()
        
        # Create revenue adjustment if needed
        if self.adjustment_amount and abs(self.adjustment_amount) > 0.01:
            self._create_revenue_adjustment()
        
        # Update the original schedule or create new one
        if self.modification_accounting == 'modify_existing':
            self._modify_existing_schedule()
        elif self.modification_accounting == 'terminate_new':
            self._terminate_and_create_new_schedule()
        
        # Update future recognition entries
        self._update_future_recognitions()
    
    def _process_termination(self):
        """Process early termination or cancellation"""
        self.ensure_one()
        
        # Calculate termination adjustment
        termination_date = self.effective_date or self.modification_date
        
        # Handle unrecognized revenue
        if self.unrecognized_amount > 0:
            if self.modification_type == 'cancellation':
                # For cancellations, typically recognize remaining revenue immediately
                self._create_catch_up_recognition(termination_date)
            else:
                # For terminations, may need to reverse unrecognized revenue
                self._create_termination_adjustment(termination_date)
        
        # Update schedule end date
        self.schedule_id.write({
            'end_date': termination_date,
            'state': 'completed' if self.modification_type == 'cancellation' else 'cancelled'
        })
        
        # Cancel future recognition entries
        future_recognitions = self.schedule_id.recognition_ids.filtered(
            lambda r: r.state == 'draft' and r.recognition_date > termination_date
        )
        future_recognitions.action_cancel()
    
    def _process_extension(self):
        """Process contract extension"""
        self.ensure_one()
        
        # Update schedule end date
        if self.new_end_date:
            self.schedule_id.end_date = self.new_end_date
        
        # Update contract value if changed
        if self.new_contract_value and self.new_contract_value != self.original_contract_value:
            self.schedule_id.total_contract_value = self.new_contract_value
        
        # Generate additional recognition entries
        self.schedule_id._generate_recognition_entries()
    
    def _process_pause_resume(self):
        """Process service pause or resume"""
        self.ensure_one()
        
        if self.modification_type == 'pause':
            self.schedule_id.action_pause()
        else:  # resume
            self.schedule_id.action_resume()
    
    def _process_general_modification(self):
        """Process other types of modifications"""
        self.ensure_one()
        
        # Update schedule values as needed
        updates = {}
        
        if self.new_contract_value:
            updates['total_contract_value'] = self.new_contract_value
        
        if self.new_start_date:
            updates['start_date'] = self.new_start_date
        
        if self.new_end_date:
            updates['end_date'] = self.new_end_date
        
        if updates:
            self.schedule_id.write(updates)
            
        # Create adjustment if needed
        if self.adjustment_amount and abs(self.adjustment_amount) > 0.01:
            self._create_revenue_adjustment()
    
    def _modify_existing_schedule(self):
        """Modify the existing revenue schedule"""
        self.ensure_one()
        
        updates = {}
        
        if self.new_contract_value:
            updates['total_contract_value'] = self.new_contract_value
        
        if self.new_end_date:
            updates['end_date'] = self.new_end_date
        
        if updates:
            self.schedule_id.write(updates)
    
    def _terminate_and_create_new_schedule(self):
        """Terminate existing schedule and create new one"""
        self.ensure_one()
        
        termination_date = self.effective_date or self.modification_date
        
        # Terminate existing schedule
        self.schedule_id.write({
            'end_date': termination_date,
            'state': 'completed'
        })
        
        # Create new schedule for remaining period
        if self.new_contract_value and self.new_end_date:
            new_schedule_vals = {
                'subscription_id': self.subscription_id.id,
                'total_contract_value': self.new_contract_value,
                'start_date': termination_date + timedelta(days=1),
                'end_date': self.new_end_date,
                'original_schedule_id': self.schedule_id.id,
                'state': 'active',
            }
            
            new_schedule = self.env['ams.revenue.schedule'].create(new_schedule_vals)
            self.new_schedule_id = new_schedule.id
            new_schedule.action_activate()
    
    def _update_future_recognitions(self):
        """Update future recognition entries based on modification"""
        self.ensure_one()
        
        # Get future recognition entries
        future_recognitions = self.schedule_id.recognition_ids.filtered(
            lambda r: r.state == 'draft' and r.recognition_date >= self.modification_date
        )
        
        if not future_recognitions:
            return
        
        # Recalculate recognition amounts based on new contract value
        if self.new_contract_value and self.new_contract_value != self.original_contract_value:
            new_daily_amount = self.schedule_id.daily_recognition_amount
            
            for recognition in future_recognitions:
                recognition.write({
                    'planned_amount': new_daily_amount,
                    'recognized_amount': new_daily_amount,
                    'modification_id': self.id,
                })
    
    def _create_revenue_adjustment(self):
        """Create journal entry for revenue adjustment"""
        self.ensure_one()
        
        if abs(self.adjustment_amount) < 0.01:
            return
        
        journal = self._get_adjustment_journal()
        
        # Determine accounts
        revenue_account = self.schedule_id.revenue_account_id
        deferred_account = self.schedule_id.deferred_account_id
        
        if not revenue_account or not deferred_account:
            raise UserError("Revenue and deferred revenue accounts must be configured.")
        
        # Create journal entry
        move_vals = {
            'move_type': 'entry',
            'date': self.modification_date,
            'journal_id': journal.id,
            'ref': f'Contract Modification Adjustment - {self.name}',
            'line_ids': [],
        }
        
        if self.adjustment_amount > 0:
            # Need to recognize more revenue
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Contract Modification - Additional Revenue',
                    'account_id': deferred_account.id,
                    'debit': self.adjustment_amount,
                    'credit': 0,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'name': f'Contract Modification - Additional Revenue',
                    'account_id': revenue_account.id,
                    'debit': 0,
                    'credit': self.adjustment_amount,
                    'partner_id': self.partner_id.id,
                }),
            ]
        else:
            # Need to reverse some revenue
            move_vals['line_ids'] = [
                (0, 0, {
                    'name': f'Contract Modification - Revenue Reversal',
                    'account_id': revenue_account.id,
                    'debit': abs(self.adjustment_amount),
                    'credit': 0,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'name': f'Contract Modification - Revenue Reversal',
                    'account_id': deferred_account.id,
                    'debit': 0,
                    'credit': abs(self.adjustment_amount),
                    'partner_id': self.partner_id.id,
                }),
            ]
        
        adjustment_move = self.env['account.move'].create(move_vals)
        adjustment_move.action_post()
        
        self.adjustment_move_id = adjustment_move.id
        
        _logger.info(f"Created adjustment entry {adjustment_move.name} for modification {self.id}")
    
    def _create_catch_up_recognition(self, termination_date):
        """Create catch-up recognition entry for early termination"""
        self.ensure_one()
        
        if self.unrecognized_amount <= 0:
            return
        
        # Create special recognition entry for remaining amount
        catch_up_recognition = self.env['ams.revenue.recognition'].create({
            'schedule_id': self.schedule_id.id,
            'recognition_date': termination_date,
            'planned_amount': self.unrecognized_amount,
            'recognized_amount': self.unrecognized_amount,
            'modification_id': self.id,
            'is_adjustment': True,
            'adjustment_reason': f'Catch-up recognition due to {self.modification_type}',
            'state': 'draft',
        })
        
        catch_up_recognition.action_recognize()
    
    def _create_termination_adjustment(self, termination_date):
        """Create adjustment for early termination with revenue reversal"""
        self.ensure_one()
        
        # This is for cases where unrecognized revenue should be reversed
        # rather than recognized (e.g., service termination for cause)
        
        journal = self._get_adjustment_journal()
        revenue_account = self.schedule_id.revenue_account_id
        deferred_account = self.schedule_id.deferred_account_id
        
        move_vals = {
            'move_type': 'entry',
            'date': termination_date,
            'journal_id': journal.id,
            'ref': f'Early Termination Adjustment - {self.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'Early Termination - Deferred Revenue Reversal',
                    'account_id': deferred_account.id,
                    'debit': self.unrecognized_amount,
                    'credit': 0,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'name': f'Early Termination - Customer Credit/Refund',
                    'account_id': self.schedule_id.subscription_id.product_id.product_tmpl_id.ams_receivable_account_id.id,
                    'debit': 0,
                    'credit': self.unrecognized_amount,
                    'partner_id': self.partner_id.id,
                }),
            ],
        }
        
        termination_move = self.env['account.move'].create(move_vals)
        termination_move.action_post()
        
        self.adjustment_move_id = termination_move.id
    
    def _get_adjustment_journal(self):
        """Get journal for adjustment entries"""
        # Try to find AMS journal first
        ams_journal = self.env['account.journal'].search([
            ('code', '=', 'AMS'),
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if ams_journal:
            return ams_journal
        
        # Fallback to default general journal
        general_journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not general_journal:
            raise UserError("No suitable journal found for adjustment entries.")
        
        return general_journal
    
    def _mark_as_processed(self):
        """Mark modification as processed"""
        self.ensure_one()
        
        self.write({
            'state': 'processed',
            'processed_by': self.env.user.id,
            'processed_date': fields.Datetime.now(),
        })
    
    # Reporting Methods
    def get_modification_summary(self):
        """Get summary for reporting"""
        self.ensure_one()
        
        return {
            'modification_id': self.id,
            'name': self.name,
            'type': self.modification_type,
            'date': self.modification_date,
            'customer': self.partner_id.name,
            'subscription': self.subscription_id.name,
            'original_value': self.original_contract_value,
            'new_value': self.new_contract_value,
            'value_change': self.value_change,
            'adjustment_amount': self.adjustment_amount,
            'state': self.state,
            'processed_by': self.processed_by.name if self.processed_by else None,
            'processed_date': self.processed_date,
        }
    
    @api.model
    def get_modification_statistics(self, date_from=None, date_to=None):
        """Get modification statistics for dashboard"""
        domain = []
        
        if date_from:
            domain.append(('modification_date', '>=', date_from))
        if date_to:
            domain.append(('modification_date', '<=', date_to))
        
        modifications = self.search(domain)
        
        return {
            'total_count': len(modifications),
            'by_type': self._group_by_type(modifications),
            'total_value_impact': sum(modifications.mapped('value_change')),
            'total_adjustments': sum(modifications.mapped('adjustment_amount')),
            'pending_count': len(modifications.filtered(lambda m: m.state in ['draft', 'validated'])),
        }
    
    def _group_by_type(self, modifications):
        """Group modifications by type for reporting"""
        type_data = {}
        for modification in modifications:
            mod_type = modification.modification_type
            if mod_type not in type_data:
                type_data[mod_type] = {
                    'type': mod_type,
                    'count': 0,
                    'value_impact': 0,
                }
            type_data[mod_type]['count'] += 1
            type_data[mod_type]['value_impact'] += modification.value_change
        
        return list(type_data.values())