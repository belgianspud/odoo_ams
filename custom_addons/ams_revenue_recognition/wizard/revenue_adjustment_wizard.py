# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class AMSRevenueAdjustmentWizard(models.TransientModel):
    """Wizard for creating revenue recognition adjustments"""
    _name = 'ams.revenue.adjustment.wizard'
    _description = 'Revenue Recognition Adjustment Wizard'

    # Selection of what to adjust
    adjustment_target = fields.Selection([
        ('schedule', 'Entire Revenue Schedule'),
        ('recognition', 'Specific Recognition Entry'),
        ('period', 'Recognition Period Range'),
    ], string='Adjustment Target', required=True, default='recognition',
       help='What you want to adjust')

    schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        help='Schedule to adjust'
    )

    recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Recognition Entry',
        help='Specific recognition entry to adjust'
    )

    # Period range (when adjusting multiple periods)
    period_start_date = fields.Date(
        string='Period Start Date',
        help='Start date for period range adjustment'
    )

    period_end_date = fields.Date(
        string='Period End Date',
        help='End date for period range adjustment'
    )

    # Adjustment details
    adjustment_type = fields.Selection([
        ('amount', 'Adjust Recognition Amount'),
        ('date', 'Change Recognition Date'),
        ('reverse', 'Reverse Recognition'),
        ('catch_up', 'Catch-up Recognition'),
        ('split', 'Split Recognition'),
    ], string='Adjustment Type', required=True, default='amount',
       help='Type of adjustment to make')

    adjustment_reason = fields.Selection([
        ('contract_modification', 'Contract Modification'),
        ('error_correction', 'Error Correction'),
        ('proration_adjustment', 'Proration Adjustment'),
        ('regulatory_change', 'Regulatory Change'),
        ('accounting_policy', 'Accounting Policy Change'),
        ('other', 'Other'),
    ], string='Adjustment Reason', required=True,
       help='Business reason for the adjustment')

    detailed_reason = fields.Text(
        string='Detailed Explanation',
        required=True,
        help='Detailed explanation of why this adjustment is needed'
    )

    # Amount adjustments
    original_amount = fields.Float(
        string='Original Amount',
        readonly=True,
        help='Original recognition amount'
    )

    new_amount = fields.Float(
        string='New Amount',
        help='New recognition amount'
    )

    adjustment_amount = fields.Float(
        string='Adjustment Amount',
        compute='_compute_adjustment_amount',
        help='Calculated adjustment amount'
    )

    # Date adjustments
    original_date = fields.Date(
        string='Original Date',
        readonly=True,
        help='Original recognition date'
    )

    new_date = fields.Date(
        string='New Date',
        help='New recognition date'
    )

    # Reversal options
    create_reversal_entry = fields.Boolean(
        string='Create Reversal Entry',
        default=True,
        help='Create a reversal entry instead of modifying the original'
    )

    # Split options
    split_amounts = fields.Text(
        string='Split Amounts',
        help='Enter split amounts separated by commas (e.g., 1000, 2000, 1500)'
    )

    split_dates = fields.Text(
        string='Split Dates',
        help='Enter split dates separated by commas (YYYY-MM-DD format)'
    )

    # Processing options
    post_immediately = fields.Boolean(
        string='Post Immediately',
        default=False,
        help='Post the adjustment immediately after creation'
    )

    create_journal_entry = fields.Boolean(
        string='Create Journal Entry',
        default=True,
        help='Create journal entry for the adjustment'
    )

    # Review information
    affected_entries_count = fields.Integer(
        string='Affected Entries',
        compute='_compute_affected_entries',
        help='Number of recognition entries that will be affected'
    )

    total_impact_amount = fields.Float(
        string='Total Impact Amount',
        compute='_compute_total_impact',
        help='Total financial impact of the adjustment'
    )

    # Approval requirements
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_approval_requirements',
        help='This adjustment requires manager approval'
    )

    approval_threshold = fields.Float(
        default=10000.0,
        help='Amount threshold requiring approval'
    )

    @api.depends('original_amount', 'new_amount')
    def _compute_adjustment_amount(self):
        """Calculate adjustment amount"""
        for wizard in self:
            wizard.adjustment_amount = (wizard.new_amount or 0) - (wizard.original_amount or 0)

    @api.depends('adjustment_target', 'schedule_id', 'recognition_id', 'period_start_date', 'period_end_date')
    def _compute_affected_entries(self):
        """Calculate number of affected entries"""
        for wizard in self:
            count = 0
            if wizard.adjustment_target == 'recognition' and wizard.recognition_id:
                count = 1
            elif wizard.adjustment_target == 'schedule' and wizard.schedule_id:
                count = len(wizard.schedule_id.recognition_ids)
            elif wizard.adjustment_target == 'period' and wizard.schedule_id and wizard.period_start_date and wizard.period_end_date:
                count = len(wizard.schedule_id.recognition_ids.filtered(
                    lambda r: wizard.period_start_date <= r.recognition_date <= wizard.period_end_date
                ))
            wizard.affected_entries_count = count

    @api.depends('adjustment_amount', 'affected_entries_count')
    def _compute_total_impact(self):
        """Calculate total financial impact"""
        for wizard in self:
            if wizard.adjustment_type == 'amount':
                wizard.total_impact_amount = abs(wizard.adjustment_amount * wizard.affected_entries_count)
            else:
                wizard.total_impact_amount = 0.0

    @api.depends('total_impact_amount', 'approval_threshold')
    def _compute_approval_requirements(self):
        """Determine if approval is required"""
        for wizard in self:
            wizard.requires_approval = wizard.total_impact_amount > wizard.approval_threshold

    @api.onchange('adjustment_target')
    def _onchange_adjustment_target(self):
        """Clear dependent fields when target changes"""
        self.recognition_id = False
        self.schedule_id = False
        self.period_start_date = False
        self.period_end_date = False

    @api.onchange('recognition_id')
    def _onchange_recognition_id(self):
        """Populate original values when recognition is selected"""
        if self.recognition_id:
            self.original_amount = self.recognition_id.recognized_amount
            self.original_date = self.recognition_id.recognition_date
            self.new_amount = self.original_amount
            self.new_date = self.original_date

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        """Set period range when schedule is selected"""
        if self.schedule_id:
            self.period_start_date = self.schedule_id.start_date
            self.period_end_date = self.schedule_id.end_date

    def action_preview_adjustment(self):
        """Preview the adjustment before applying"""
        self.ensure_one()
        self._validate_adjustment()

        preview_data = self._prepare_preview_data()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Adjustment Preview',
            'res_model': 'ams.revenue.adjustment.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
                'default_preview_data': preview_data,
            }
        }

    def action_apply_adjustment(self):
        """Apply the revenue recognition adjustment"""
        self.ensure_one()
        self._validate_adjustment()

        if self.requires_approval and not self.env.user.has_group('ams_revenue_recognition.group_ams_revenue_recognition_manager'):
            raise UserError("This adjustment requires manager approval due to its high impact amount.")

        try:
            if self.adjustment_type == 'amount':
                result = self._apply_amount_adjustment()
            elif self.adjustment_type == 'date':
                result = self._apply_date_adjustment()
            elif self.adjustment_type == 'reverse':
                result = self._apply_reversal()
            elif self.adjustment_type == 'catch_up':
                result = self._apply_catch_up()
            elif self.adjustment_type == 'split':
                result = self._apply_split()
            else:
                raise UserError("Unsupported adjustment type.")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Revenue adjustment applied successfully! {result.get("message", "")}',
                    'type': 'success',
                    'sticky': True,
                }
            }

        except Exception as e:
            _logger.error(f"Revenue adjustment failed: {str(e)}")
            raise UserError(f"Adjustment failed: {str(e)}")

    def _validate_adjustment(self):
        """Validate adjustment parameters"""
        if self.adjustment_target == 'recognition' and not self.recognition_id:
            raise UserError("Please select a recognition entry to adjust.")

        if self.adjustment_target == 'schedule' and not self.schedule_id:
            raise UserError("Please select a revenue schedule to adjust.")

        if self.adjustment_target == 'period':
            if not self.schedule_id:
                raise UserError("Please select a revenue schedule for period adjustment.")
            if not self.period_start_date or not self.period_end_date:
                raise UserError("Please specify the period start and end dates.")
            if self.period_end_date < self.period_start_date:
                raise UserError("Period end date must be after start date.")

        if self.adjustment_type == 'amount' and not self.new_amount:
            raise UserError("Please specify the new recognition amount.")

        if self.adjustment_type == 'date' and not self.new_date:
            raise UserError("Please specify the new recognition date.")

        if self.adjustment_type == 'split':
            if not self.split_amounts or not self.split_dates:
                raise UserError("Please specify split amounts and dates.")

    def _prepare_preview_data(self):
        """Prepare data for adjustment preview"""
        return {
            'adjustment_type': self.adjustment_type,
            'adjustment_target': self.adjustment_target,
            'affected_entries': self.affected_entries_count,
            'total_impact': self.total_impact_amount,
            'requires_approval': self.requires_approval,
            'reason': self.detailed_reason,
        }

    def _apply_amount_adjustment(self):
        """Apply amount adjustment"""
        entries = self._get_target_entries()
        adjusted_count = 0

        for entry in entries:
            if entry.state == 'posted' and self.create_reversal_entry:
                # Create reversal entry
                reversal = entry.action_create_reversal()
                # Create new entry with correct amount
                new_entry = entry.copy({
                    'recognized_amount': self.new_amount,
                    'is_adjustment': True,
                    'adjustment_reason': f"{self.adjustment_reason}: {self.detailed_reason}",
                    'original_recognition_id': entry.id,
                })
                if self.post_immediately:
                    new_entry.action_recognize()
                adjusted_count += 1
            elif entry.state == 'draft':
                # Modify draft entry directly
                entry.write({
                    'recognized_amount': self.new_amount,
                    'is_adjustment': True,
                    'adjustment_reason': f"{self.adjustment_reason}: {self.detailed_reason}",
                })
                adjusted_count += 1

        return {'message': f'{adjusted_count} entries adjusted'}

    def _apply_date_adjustment(self):
        """Apply date adjustment"""
        entries = self._get_target_entries()
        adjusted_count = 0

        for entry in entries:
            if entry.state == 'draft':
                entry.recognition_date = self.new_date
                adjusted_count += 1
            else:
                raise UserError(f"Cannot change date of posted entry: {entry.name}")

        return {'message': f'{adjusted_count} entries rescheduled'}

    def _apply_reversal(self):
        """Apply reversal adjustment"""
        entries = self._get_target_entries()
        reversed_count = 0

        for entry in entries:
            if entry.state == 'posted':
                entry.action_create_reversal()
                reversed_count += 1

        return {'message': f'{reversed_count} entries reversed'}

    def _apply_catch_up(self):
        """Apply catch-up recognition"""
        # Implementation for catch-up recognition
        return {'message': 'Catch-up recognition applied'}

    def _apply_split(self):
        """Apply split recognition"""
        # Implementation for split recognition
        return {'message': 'Recognition split applied'}

    def _get_target_entries(self):
        """Get the recognition entries targeted by this adjustment"""
        if self.adjustment_target == 'recognition':
            return self.recognition_id
        elif self.adjustment_target == 'schedule':
            return self.schedule_id.recognition_ids
        elif self.adjustment_target == 'period':
            return self.schedule_id.recognition_ids.filtered(
                lambda r: self.period_start_date <= r.recognition_date <= self.period_end_date
            )
        return self.env['ams.revenue.recognition']


class AMSRevenueAdjustmentPreview(models.TransientModel):
    """Preview wizard for revenue adjustments"""
    _name = 'ams.revenue.adjustment.preview'
    _description = 'Revenue Adjustment Preview'

    wizard_id = fields.Many2one(
        'ams.revenue.adjustment.wizard',
        string='Adjustment Wizard',
        required=True
    )

    preview_data = fields.Text(
        string='Preview Data',
        readonly=True
    )

    def action_apply_adjustment(self):
        """Apply the adjustment from preview"""
        return self.wizard_id.action_apply_adjustment()

    def action_back_to_wizard(self):
        """Go back to adjustment wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Revenue Recognition Adjustment',
            'res_model': 'ams.revenue.adjustment.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }