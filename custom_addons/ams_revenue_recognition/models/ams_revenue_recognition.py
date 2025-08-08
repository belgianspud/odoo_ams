# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSRevenueRecognition(models.Model):
    """Individual Revenue Recognition Entries"""
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition Entry'
    _order = 'recognition_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Recognition Entry',
        compute='_compute_name',
        store=True,
        help='Name of the revenue recognition entry'
    )
    
    schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Recognition Schedule',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Related revenue recognition schedule'
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
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='schedule_id.product_id',
        store=True,
        help='Product from schedule'
    )
    
    # Recognition Details
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        tracking=True,
        help='Date when revenue should be recognized'
    )
    
    planned_amount = fields.Float(
        string='Planned Amount',
        required=True,
        tracking=True,
        help='Originally planned recognition amount'
    )
    
    recognized_amount = fields.Float(
        string='Recognized Amount',
        tracking=True,
        help='Actual amount recognized (may differ from planned due to adjustments)'
    )
    
    adjustment_amount = fields.Float(
        string='Adjustment Amount',
        compute='_compute_adjustment_amount',
        store=True,
        help='Difference between recognized and planned amounts'
    )
    
    # Recognition Method Details
    recognition_method = fields.Selection(
        related='schedule_id.recognition_method',
        string='Recognition Method',
        store=True,
        help='Method used for this recognition'
    )
    
    # Accounting References
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        help='Generated journal entry for this recognition'
    )
    
    deferred_move_line_id = fields.Many2one(
        'account.move.line',
        string='Deferred Revenue Line',
        readonly=True,
        help='Journal line debiting deferred revenue'
    )
    
    revenue_move_line_id = fields.Many2one(
        'account.move.line',
        string='Revenue Line',
        readonly=True,
        help='Journal line crediting revenue'
    )
    
    deferred_account_id = fields.Many2one(
        'account.account',
        string='Deferred Revenue Account',
        related='schedule_id.deferred_account_id',
        store=True,
        help='Account holding deferred revenue'
    )
    
    revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        related='schedule_id.revenue_account_id',
        store=True,
        help='Account for recognized revenue'
    )
    
    # Status and Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True,
       help='Current status of the recognition entry')
    
    is_adjustment = fields.Boolean(
        string='Is Adjustment',
        default=False,
        help='This entry is an adjustment to correct previous recognition'
    )
    
    original_recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Original Recognition',
        help='Reference to original recognition if this is an adjustment'
    )
    
    adjustment_reason = fields.Text(
        string='Adjustment Reason',
        help='Reason for adjustment if applicable'
    )
    
    # Processing Information
    processed_date = fields.Datetime(
        string='Processed Date',
        readonly=True,
        help='Date and time when recognition was processed'
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True,
        help='User who processed this recognition'
    )
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Error message if processing failed'
    )
    
    # Period Information
    period_number = fields.Integer(
        string='Period Number',
        help='Sequential period number within the schedule'
    )
    
    is_final_period = fields.Boolean(
        string='Final Period',
        compute='_compute_period_info',
        store=True,
        help='This is the final recognition period for the schedule'
    )
    
    # Contract Modification References
    modification_id = fields.Many2one(
        'ams.contract.modification',
        string='Related Modification',
        help='Contract modification that created this recognition'
    )
    
    # Proration and Partial Recognition
    is_prorated = fields.Boolean(
        string='Prorated Recognition',
        default=False,
        help='This recognition was prorated due to partial period'
    )
    
    proration_factor = fields.Float(
        string='Proration Factor',
        default=1.0,
        help='Factor applied for partial period recognition'
    )
    
    days_in_period = fields.Integer(
        string='Days in Period',
        help='Number of days in this recognition period'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='schedule_id.company_id',
        store=True,
        help='Company from revenue schedule'
    )
    
    # Computed Fields
    @api.depends('schedule_id.name', 'recognition_date', 'period_number')
    def _compute_name(self):
        """Compute recognition entry name"""
        for recognition in self:
            if recognition.schedule_id and recognition.recognition_date:
                date_str = recognition.recognition_date.strftime('%Y-%m-%d')
                if recognition.period_number:
                    recognition.name = f"{recognition.schedule_id.name} - Period {recognition.period_number} ({date_str})"
                else:
                    recognition.name = f"{recognition.schedule_id.name} - {date_str}"
            else:
                recognition.name = "New Recognition Entry"
    
    @api.depends('recognized_amount', 'planned_amount')
    def _compute_adjustment_amount(self):
        """Compute adjustment amount"""
        for recognition in self:
            recognition.adjustment_amount = recognition.recognized_amount - recognition.planned_amount
    
    @api.depends('schedule_id.recognition_ids', 'recognition_date')
    def _compute_period_info(self):
        """Compute period information"""
        for recognition in self:
            if recognition.schedule_id:
                # Find all recognitions for this schedule, ordered by date
                all_recognitions = recognition.schedule_id.recognition_ids.sorted('recognition_date')
                
                # Set period number
                if recognition in all_recognitions:
                    recognition.period_number = all_recognitions.ids.index(recognition.id) + 1
                else:
                    recognition.period_number = 0
                
                # Check if this is the final period
                if all_recognitions:
                    recognition.is_final_period = (recognition == all_recognitions[-1])
                else:
                    recognition.is_final_period = False
            else:
                recognition.period_number = 0
                recognition.is_final_period = False
    
    # Constraints and Validations
    @api.constrains('planned_amount', 'recognized_amount')
    def _check_amounts(self):
        """Validate recognition amounts"""
        for recognition in self:
            if recognition.planned_amount < 0:
                raise ValidationError("Planned amount cannot be negative.")
            
            if recognition.state == 'posted' and recognition.recognized_amount < 0:
                raise ValidationError("Recognized amount cannot be negative.")
    
    @api.constrains('recognition_date')
    def _check_recognition_date(self):
        """Validate recognition date"""
        for recognition in self:
            if recognition.schedule_id:
                if recognition.recognition_date < recognition.schedule_id.start_date:
                    raise ValidationError("Recognition date cannot be before schedule start date.")
                
                if recognition.recognition_date > recognition.schedule_id.end_date:
                    raise ValidationError("Recognition date cannot be after schedule end date.")
    
    @api.constrains('proration_factor')
    def _check_proration_factor(self):
        """Validate proration factor"""
        for recognition in self:
            if not (0.0 <= recognition.proration_factor <= 1.0):
                raise ValidationError("Proration factor must be between 0.0 and 1.0.")
    
    # CRUD Methods
    @api.model_create_multi
    def create(self, vals_list):
        """Enhanced create method"""
        for vals in vals_list:
            # Set recognized amount to planned amount if not specified
            if 'recognized_amount' not in vals and 'planned_amount' in vals:
                vals['recognized_amount'] = vals['planned_amount']
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Enhanced write method with state change validation"""
        # Prevent changes to posted entries except for specific fields
        if any(rec.state == 'posted' for rec in self):
            allowed_fields = {'adjustment_reason', 'error_message'}
            changed_fields = set(vals.keys())
            if not changed_fields.issubset(allowed_fields):
                raise UserError("Cannot modify posted revenue recognition entries.")
        
        return super().write(vals)
    
    def unlink(self):
        """Prevent deletion of posted entries"""
        if any(rec.state == 'posted' for rec in self):
            raise UserError("Cannot delete posted revenue recognition entries.")
        
        return super().unlink()
    
    # Business Logic Methods
    def action_recognize(self):
        """Process the revenue recognition"""
        for recognition in self:
            if recognition.state != 'draft':
                raise UserError(f"Cannot process recognition in {recognition.state} state.")
            
            try:
                recognition._validate_for_recognition()
                recognition._create_journal_entry()
                recognition._update_recognition_status()
                
                recognition.message_post(body=f"Revenue recognized: {recognition.recognized_amount}")
                
            except Exception as e:
                recognition._handle_recognition_error(str(e))
                raise
    
    def action_cancel(self):
        """Cancel the revenue recognition"""
        for recognition in self:
            if recognition.state == 'posted':
                raise UserError("Cannot cancel posted revenue recognition. Create a reversal instead.")
            
            recognition.state = 'cancelled'
            recognition.message_post(body="Revenue recognition cancelled.")
    
    def action_reset_to_draft(self):
        """Reset recognition to draft (admin only)"""
        for recognition in self:
            if recognition.state == 'posted' and recognition.journal_entry_id:
                raise UserError("Cannot reset posted recognition with journal entry. Reverse the entry first.")
            
            recognition.write({
                'state': 'draft',
                'error_message': False,
                'processed_date': False,
                'processed_by': False,
            })
            
            recognition.message_post(body="Revenue recognition reset to draft.")
    
    def action_create_reversal(self):
        """Create reversal entry for posted recognition"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError("Can only reverse posted recognitions.")
        
        if not self.journal_entry_id:
            raise UserError("No journal entry found to reverse.")
        
        # Create reversal journal entry
        reversal_entry = self.journal_entry_id._reverse_moves(
            default_values_list=[{
                'ref': f'Reversal of {self.journal_entry_id.name}',
                'date': date.today(),
            }]
        )
        
        # Create reversal recognition entry
        reversal_recognition = self.copy({
            'recognized_amount': -self.recognized_amount,
            'is_adjustment': True,
            'original_recognition_id': self.id,
            'adjustment_reason': 'Reversal of original recognition',
            'journal_entry_id': reversal_entry.id,
            'state': 'posted',
            'processed_date': fields.Datetime.now(),
            'processed_by': self.env.user.id,
        })
        
        self.message_post(body=f"Recognition reversed. Reversal entry: {reversal_recognition.name}")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reversal Recognition',
            'res_model': 'ams.revenue.recognition',
            'res_id': reversal_recognition.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _validate_for_recognition(self):
        """Validate recognition can be processed"""
        self.ensure_one()
        
        if not self.schedule_id:
            raise UserError("Recognition must be linked to a schedule.")
        
        if self.schedule_id.state != 'active':
            raise UserError("Cannot process recognition for inactive schedule.")
        
        if not self.recognized_amount or self.recognized_amount <= 0:
            raise UserError("Recognition amount must be positive.")
        
        if not self.deferred_account_id or not self.revenue_account_id:
            raise UserError("Deferred revenue and revenue accounts must be configured.")
        
        # Check if recognition date is appropriate
        if self.recognition_date > date.today():
            raise UserError("Cannot recognize future revenue.")
    
    def _create_journal_entry(self):
        """Create journal entry for revenue recognition"""
        self.ensure_one()
        
        # Prepare journal entry values
        company = self.env.company
        journal = self._get_recognition_journal()
        
        move_vals = {
            'move_type': 'entry',
            'date': self.recognition_date,
            'journal_id': journal.id,
            'ref': f'Revenue Recognition - {self.name}',
            'line_ids': [
                # Debit Deferred Revenue (decrease liability)
                (0, 0, {
                    'name': f'Deferred Revenue Recognition - {self.subscription_id.name}',
                    'account_id': self.deferred_account_id.id,
                    'debit': self.recognized_amount,
                    'credit': 0,
                    'partner_id': self.partner_id.id,
                    'product_id': self.product_id.id,
                }),
                # Credit Revenue (increase income)
                (0, 0, {
                    'name': f'Revenue Recognition - {self.subscription_id.name}',
                    'account_id': self.revenue_account_id.id,
                    'debit': 0,
                    'credit': self.recognized_amount,
                    'partner_id': self.partner_id.id,
                    'product_id': self.product_id.id,
                }),
            ],
        }
        
        # Create and post the journal entry
        journal_entry = self.env['account.move'].create(move_vals)
        journal_entry.action_post()
        
        # Store references to journal entry and lines
        self.journal_entry_id = journal_entry.id
        self.deferred_move_line_id = journal_entry.line_ids.filtered(
            lambda l: l.account_id == self.deferred_account_id
        )[0].id
        self.revenue_move_line_id = journal_entry.line_ids.filtered(
            lambda l: l.account_id == self.revenue_account_id
        )[0].id
        
        _logger.info(f"Created journal entry {journal_entry.name} for recognition {self.id}")
    
    def _get_recognition_journal(self):
        """Get appropriate journal for revenue recognition"""
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
            raise UserError("No suitable journal found for revenue recognition.")
        
        return general_journal
    
    def _update_recognition_status(self):
        """Update recognition status after successful processing"""
        self.ensure_one()
        
        self.write({
            'state': 'posted',
            'processed_date': fields.Datetime.now(),
            'processed_by': self.env.user.id,
            'error_message': False,
        })
        
        # Check if schedule should be marked as completed
        self.schedule_id._check_completion_status()
    
    def _handle_recognition_error(self, error_message):
        """Handle recognition processing error"""
        self.ensure_one()
        
        self.write({
            'state': 'error',
            'error_message': error_message,
        })
        
        # Create activity for manual review
        self.activity_schedule(
            'mail.mail_activity_data_warning',
            summary='Revenue Recognition Error',
            note=f'Revenue recognition failed: {error_message}',
            user_id=self.env.user.id
        )
        
        _logger.error(f"Revenue recognition error for {self.id}: {error_message}")
    
    # Reporting and Analysis Methods
    def get_recognition_summary(self):
        """Get summary of recognition for reporting"""
        self.ensure_one()
        
        return {
            'recognition_id': self.id,
            'name': self.name,
            'date': self.recognition_date,
            'planned_amount': self.planned_amount,
            'recognized_amount': self.recognized_amount,
            'adjustment_amount': self.adjustment_amount,
            'state': self.state,
            'subscription_name': self.subscription_id.name,
            'customer_name': self.partner_id.name,
            'product_name': self.product_id.name,
            'period_number': self.period_number,
            'is_final': self.is_final_period,
        }
    
    @api.model
    def get_recognition_statistics(self, date_from=None, date_to=None):
        """Get recognition statistics for dashboard"""
        domain = [('state', '=', 'posted')]
        
        if date_from:
            domain.append(('recognition_date', '>=', date_from))
        if date_to:
            domain.append(('recognition_date', '<=', date_to))
        
        recognitions = self.search(domain)
        
        return {
            'total_recognized': sum(recognitions.mapped('recognized_amount')),
            'total_count': len(recognitions),
            'by_month': self._group_by_month(recognitions),
            'by_product': self._group_by_product(recognitions),
            'average_amount': sum(recognitions.mapped('recognized_amount')) / len(recognitions) if recognitions else 0,
        }
    
    def _group_by_month(self, recognitions):
        """Group recognitions by month for reporting"""
        monthly_data = {}
        for recognition in recognitions:
            month_key = recognition.recognition_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_key,
                    'count': 0,
                    'amount': 0,
                }
            monthly_data[month_key]['count'] += 1
            monthly_data[month_key]['amount'] += recognition.recognized_amount
        
        return list(monthly_data.values())
    
    def _group_by_product(self, recognitions):
        """Group recognitions by product for reporting"""
        product_data = {}
        for recognition in recognitions:
            product_name = recognition.product_id.name or 'Unknown'
            if product_name not in product_data:
                product_data[product_name] = {
                    'product': product_name,
                    'count': 0,
                    'amount': 0,
                }
            product_data[product_name]['count'] += 1
            product_data[product_name]['amount'] += recognition.recognized_amount
        
        return list(product_data.values())
    
    # Batch Processing Methods
    @api.model
    def process_batch_recognition(self, recognition_ids=None, date_limit=None):
        """Process multiple recognitions in batch"""
        if recognition_ids:
            recognitions = self.browse(recognition_ids)
        else:
            domain = [
                ('state', '=', 'draft'),
                ('recognition_date', '<=', date_limit or date.today())
            ]
            recognitions = self.search(domain)
        
        processed_count = 0
        error_count = 0
        errors = []
        
        for recognition in recognitions:
            try:
                recognition.action_recognize()
                processed_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'recognition_id': recognition.id,
                    'error': str(e)
                })
                _logger.error(f"Batch processing error for recognition {recognition.id}: {str(e)}")
        
        return {
            'processed': processed_count,
            'errors': error_count,
            'error_details': errors
        }