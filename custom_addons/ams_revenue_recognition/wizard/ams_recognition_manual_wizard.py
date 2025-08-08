# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSRecognitionManualWizard(models.TransientModel):
    """Wizard for manual revenue recognition creation"""
    _name = 'ams.recognition.manual.wizard'
    _description = 'Manual Revenue Recognition Wizard'

    # Recognition Type
    recognition_mode = fields.Selection([
        ('single', 'Single Recognition Entry'),
        ('batch', 'Batch Recognition'),
        ('catch_up', 'Catch-up Recognition'),
        ('milestone', 'Milestone Recognition'),
    ], string='Recognition Mode', required=True, default='single',
       help='Type of manual recognition to create')

    # Schedule Selection
    schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        required=True,
        domain="[('state', 'in', ['active', 'paused'])]",
        help='Revenue schedule to create recognition for'
    )

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        related='schedule_id.subscription_id',
        readonly=True,
        help='Related subscription'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='schedule_id.partner_id',
        readonly=True,
        help='Customer'
    )

    # Single Recognition Fields
    recognition_date = fields.Date(
        string='Recognition Date',
        default=fields.Date.context_today,
        required=True,
        help='Date for revenue recognition'
    )

    recognition_amount = fields.Float(
        string='Recognition Amount',
        help='Amount to recognize'
    )

    # Batch Recognition Fields
    batch_start_date = fields.Date(
        string='Batch Start Date',
        help='Start date for batch recognition'
    )

    batch_end_date = fields.Date(
        string='Batch End Date',
        help='End date for batch recognition'
    )

    batch_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Batch Frequency', default='monthly',
       help='Frequency for batch recognition entries')

    batch_amount_per_period = fields.Float(
        string='Amount per Period',
        help='Amount to recognize per period in batch'
    )

    # Catch-up Recognition Fields
    catch_up_through_date = fields.Date(
        string='Catch-up Through Date',
        help='Recognize revenue through this date'
    )

    catch_up_method = fields.Selection([
        ('equal_periods', 'Equal Amounts per Period'),
        ('prorated', 'Prorated by Days'),
        ('lump_sum', 'Lump Sum Recognition'),
    ], string='Catch-up Method', default='equal_periods',
       help='Method for catch-up recognition calculation')

    # Milestone Recognition Fields
    milestone_description = fields.Char(
        string='Milestone Description',
        help='Description of the milestone achieved'
    )

    milestone_percentage = fields.Float(
        string='Milestone Percentage',
        help='Percentage of contract completed with this milestone'
    )

    milestone_amount = fields.Float(
        string='Milestone Amount',
        compute='_compute_milestone_amount',
        help='Amount to recognize for this milestone'
    )

    # Configuration Options
    create_journal_entry = fields.Boolean(
        string='Create Journal Entry',
        default=True,
        help='Automatically create journal entry'
    )

    post_immediately = fields.Boolean(
        string='Post Immediately',
        default=False,
        help='Post recognition entries immediately'
    )

    override_validation = fields.Boolean(
        string='Override Validation',
        default=False,
        help='Override standard validation checks'
    )

    # Reason and Notes
    recognition_reason = fields.Selection([
        ('manual_adjustment', 'Manual Adjustment'),
        ('milestone_completion', 'Milestone Completion'),
        ('catch_up_processing', 'Catch-up Processing'),
        ('contract_modification', 'Contract Modification'),
        ('period_end_adjustment', 'Period End Adjustment'),
        ('other', 'Other'),
    ], string='Recognition Reason', required=True,
       help='Reason for manual recognition')

    detailed_notes = fields.Text(
        string='Detailed Notes',
        required=True,
        help='Detailed explanation for this manual recognition'
    )

    # Preview Information
    total_amount_to_recognize = fields.Float(
        string='Total Amount to Recognize',
        compute='_compute_total_recognition',
        help='Total amount that will be recognized'
    )

    entries_to_create = fields.Integer(
        string='Entries to Create',
        compute='_compute_total_recognition',
        help='Number of recognition entries to create'
    )

    remaining_contract_value = fields.Float(
        string='Remaining Contract Value',
        related='schedule_id.remaining_revenue',
        readonly=True,
        help='Remaining unrecognized revenue'
    )

    # Validation flags
    exceeds_remaining = fields.Boolean(
        string='Exceeds Remaining',
        compute='_compute_validation_flags',
        help='Recognition exceeds remaining contract value'
    )

    future_dated = fields.Boolean(
        string='Future Dated',
        compute='_compute_validation_flags',
        help='Recognition is dated in the future'
    )

    @api.depends('milestone_percentage', 'schedule_id.total_contract_value')
    def _compute_milestone_amount(self):
        """Compute milestone recognition amount"""
        for wizard in self:
            if wizard.milestone_percentage and wizard.schedule_id:
                wizard.milestone_amount = (
                    wizard.schedule_id.total_contract_value * 
                    wizard.milestone_percentage / 100
                )
            else:
                wizard.milestone_amount = 0.0

    @api.depends('recognition_mode', 'recognition_amount', 'batch_amount_per_period', 
                 'milestone_amount', 'batch_start_date', 'batch_end_date', 'batch_frequency')
    def _compute_total_recognition(self):
        """Compute total recognition amount and entry count"""
        for wizard in self:
            if wizard.recognition_mode == 'single':
                wizard.total_amount_to_recognize = wizard.recognition_amount
                wizard.entries_to_create = 1
            elif wizard.recognition_mode == 'milestone':
                wizard.total_amount_to_recognize = wizard.milestone_amount
                wizard.entries_to_create = 1
            elif wizard.recognition_mode == 'batch':
                if wizard.batch_start_date and wizard.batch_end_date and wizard.batch_frequency:
                    periods = wizard._calculate_batch_periods()
                    wizard.total_amount_to_recognize = wizard.batch_amount_per_period * periods
                    wizard.entries_to_create = periods
                else:
                    wizard.total_amount_to_recognize = 0.0
                    wizard.entries_to_create = 0
            elif wizard.recognition_mode == 'catch_up':
                if wizard.catch_up_through_date and wizard.schedule_id:
                    # Calculate catch-up amount
                    wizard.total_amount_to_recognize = wizard._calculate_catch_up_amount()
                    wizard.entries_to_create = 1  # Simplified for now
                else:
                    wizard.total_amount_to_recognize = 0.0
                    wizard.entries_to_create = 0
            else:
                wizard.total_amount_to_recognize = 0.0
                wizard.entries_to_create = 0

    @api.depends('total_amount_to_recognize', 'remaining_contract_value', 'recognition_date')
    def _compute_validation_flags(self):
        """Compute validation flags"""
        for wizard in self:
            wizard.exceeds_remaining = (
                wizard.total_amount_to_recognize > wizard.remaining_contract_value
            )
            wizard.future_dated = wizard.recognition_date > date.today()

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        """Update fields when schedule changes"""
        if self.schedule_id:
            # Set default recognition amount to daily amount
            self.recognition_amount = self.schedule_id.daily_recognition_amount
            self.batch_amount_per_period = self.schedule_id.monthly_recognition_amount
            
            # Set default dates
            if not self.batch_start_date:
                self.batch_start_date = self.schedule_id.start_date
            if not self.batch_end_date:
                self.batch_end_date = self.schedule_id.end_date
            if not self.catch_up_through_date:
                self.catch_up_through_date = date.today()

    @api.onchange('recognition_mode')
    def _onchange_recognition_mode(self):
        """Clear fields when mode changes"""
        # Clear amounts
        self.recognition_amount = 0.0
        self.batch_amount_per_period = 0.0
        self.milestone_percentage = 0.0
        
        # Set defaults based on mode
        if self.recognition_mode == 'single' and self.schedule_id:
            self.recognition_amount = self.schedule_id.daily_recognition_amount
        elif self.recognition_mode == 'batch' and self.schedule_id:
            self.batch_amount_per_period = self.schedule_id.monthly_recognition_amount

    def _calculate_batch_periods(self):
        """Calculate number of periods in batch"""
        if not (self.batch_start_date and self.batch_end_date and self.batch_frequency):
            return 0

        if self.batch_frequency == 'daily':
            return (self.batch_end_date - self.batch_start_date).days + 1
        elif self.batch_frequency == 'weekly':
            return ((self.batch_end_date - self.batch_start_date).days // 7) + 1
        elif self.batch_frequency == 'monthly':
            months = (self.batch_end_date.year - self.batch_start_date.year) * 12
            months += self.batch_end_date.month - self.batch_start_date.month
            return months + 1
        
        return 0

    def _calculate_catch_up_amount(self):
        """Calculate catch-up recognition amount"""
        if not (self.schedule_id and self.catch_up_through_date):
            return 0.0

        # Calculate what should have been recognized by the catch-up date
        total_days = (self.schedule_id.end_date - self.schedule_id.start_date).days + 1
        days_elapsed = (self.catch_up_through_date - self.schedule_id.start_date).days + 1
        
        if total_days <= 0:
            return 0.0

        should_have_recognized = (
            self.schedule_id.total_contract_value * 
            days_elapsed / total_days
        )
        
        already_recognized = self.schedule_id.recognized_revenue
        
        return max(0, should_have_recognized - already_recognized)

    def action_validate_and_preview(self):
        """Validate inputs and show preview"""
        self.ensure_one()
        self._validate_recognition()

        preview_data = self._prepare_preview_data()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Recognition Preview',
            'res_model': 'ams.recognition.manual.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
                'default_preview_data': preview_data,
            }
        }

    def action_create_recognition(self):
        """Create manual revenue recognition entries"""
        self.ensure_one()
        self._validate_recognition()

        try:
            if self.recognition_mode == 'single':
                result = self._create_single_recognition()
            elif self.recognition_mode == 'batch':
                result = self._create_batch_recognition()
            elif self.recognition_mode == 'catch_up':
                result = self._create_catch_up_recognition()
            elif self.recognition_mode == 'milestone':
                result = self._create_milestone_recognition()
            else:
                raise UserError("Unsupported recognition mode")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Manual revenue recognition created successfully! {result.get("message", "")}',
                    'type': 'success',
                    'sticky': True,
                }
            }

        except Exception as e:
            _logger.error(f"Manual revenue recognition failed: {str(e)}")
            raise UserError(f"Recognition creation failed: {str(e)}")

    def _validate_recognition(self):
        """Validate recognition parameters"""
        if not self.schedule_id:
            raise UserError("Please select a revenue schedule.")

        if self.schedule_id.state not in ['active', 'paused']:
            raise UserError("Can only create recognition for active or paused schedules.")

        if not self.override_validation:
            if self.exceeds_remaining:
                raise UserError(
                    f"Recognition amount ${self.total_amount_to_recognize:,.2f} "
                    f"exceeds remaining contract value ${self.remaining_contract_value:,.2f}"
                )

            if self.future_dated and not self.env.user.has_group('ams_revenue_recognition.group_ams_revenue_recognition_manager'):
                raise UserError("Only managers can create future-dated recognition entries.")

        # Mode-specific validation
        if self.recognition_mode == 'single':
            if self.recognition_amount <= 0:
                raise UserError("Recognition amount must be positive.")

        elif self.recognition_mode == 'batch':
            if not (self.batch_start_date and self.batch_end_date):
                raise UserError("Batch start and end dates are required.")
            if self.batch_end_date < self.batch_start_date:
                raise UserError("Batch end date must be after start date.")
            if self.batch_amount_per_period <= 0:
                raise UserError("Batch amount per period must be positive.")

        elif self.recognition_mode == 'milestone':
            if not self.milestone_description:
                raise UserError("Milestone description is required.")
            if not (0 < self.milestone_percentage <= 100):
                raise UserError("Milestone percentage must be between 0 and 100.")

    def _prepare_preview_data(self):
        """Prepare preview data"""
        return {
            'mode': self.recognition_mode,
            'schedule_name': self.schedule_id.name,
            'total_amount': self.total_amount_to_recognize,
            'entries_count': self.entries_to_create,
            'exceeds_remaining': self.exceeds_remaining,
            'future_dated': self.future_dated,
            'reason': self.recognition_reason,
            'notes': self.detailed_notes,
        }

    def _create_single_recognition(self):
        """Create single recognition entry"""
        recognition_vals = {
            'schedule_id': self.schedule_id.id,
            'recognition_date': self.recognition_date,
            'planned_amount': self.recognition_amount,
            'recognized_amount': self.recognition_amount,
            'is_adjustment': True,
            'adjustment_reason': f"{self.recognition_reason}: {self.detailed_notes}",
            'state': 'draft',
        }

        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)

        if self.post_immediately:
            recognition.action_recognize()

        return {'message': f'Created recognition entry: {recognition.name}'}

    def _create_batch_recognition(self):
        """Create batch recognition entries"""
        entries_created = []
        current_date = self.batch_start_date

        while current_date <= self.batch_end_date:
            recognition_vals = {
                'schedule_id': self.schedule_id.id,
                'recognition_date': current_date,
                'planned_amount': self.batch_amount_per_period,
                'recognized_amount': self.batch_amount_per_period,
                'is_adjustment': True,
                'adjustment_reason': f"Batch {self.recognition_reason}: {self.detailed_notes}",
                'state': 'draft',
            }

            recognition = self.env['ams.revenue.recognition'].create(recognition_vals)
            entries_created.append(recognition)

            if self.post_immediately:
                recognition.action_recognize()

            # Advance to next period
            if self.batch_frequency == 'daily':
                current_date += timedelta(days=1)
            elif self.batch_frequency == 'weekly':
                current_date += timedelta(weeks=1)
            elif self.batch_frequency == 'monthly':
                current_date += relativedelta(months=1)

        return {'message': f'Created {len(entries_created)} batch recognition entries'}

    def _create_catch_up_recognition(self):
        """Create catch-up recognition entry"""
        catch_up_amount = self._calculate_catch_up_amount()

        if catch_up_amount <= 0:
            return {'message': 'No catch-up recognition needed'}

        recognition_vals = {
            'schedule_id': self.schedule_id.id,
            'recognition_date': self.catch_up_through_date,
            'planned_amount': catch_up_amount,
            'recognized_amount': catch_up_amount,
            'is_adjustment': True,
            'adjustment_reason': f"Catch-up {self.recognition_reason}: {self.detailed_notes}",
            'state': 'draft',
        }

        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)

        if self.post_immediately:
            recognition.action_recognize()

        return {'message': f'Created catch-up recognition: ${catch_up_amount:,.2f}'}

    def _create_milestone_recognition(self):
        """Create milestone recognition entry"""
        recognition_vals = {
            'schedule_id': self.schedule_id.id,
            'recognition_date': self.recognition_date,
            'planned_amount': self.milestone_amount,
            'recognized_amount': self.milestone_amount,
            'is_adjustment': True,
            'adjustment_reason': f"Milestone {self.milestone_description}: {self.detailed_notes}",
            'state': 'draft',
        }

        recognition = self.env['ams.revenue.recognition'].create(recognition_vals)

        if self.post_immediately:
            recognition.action_recognize()

        return {'message': f'Created milestone recognition: {self.milestone_description}'}


class AMSRecognitionManualPreview(models.TransientModel):
    """Preview wizard for manual revenue recognition"""
    _name = 'ams.recognition.manual.preview'
    _description = 'Manual Revenue Recognition Preview'

    wizard_id = fields.Many2one(
        'ams.recognition.manual.wizard',
        string='Manual Recognition Wizard',
        required=True
    )

    preview_data = fields.Text(
        string='Preview Data',
        readonly=True
    )

    def action_create_recognition(self):
        """Create recognition from preview"""
        return self.wizard_id.action_create_recognition()

    def action_back_to_wizard(self):
        """Go back to manual recognition wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manual Revenue Recognition',
            'res_model': 'ams.recognition.manual.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }