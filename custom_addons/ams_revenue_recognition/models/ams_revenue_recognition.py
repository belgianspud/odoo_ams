# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime

class AMSRevenueRecognition(models.Model):
    """Individual Revenue Recognition Entry"""
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition Entry'
    _order = 'recognition_date asc, id asc'
    _rec_name = 'display_name'

    # Basic Information
    display_name = fields.Char(
        string='Recognition Entry',
        compute='_compute_display_name',
        store=True
    )
    
    description = fields.Text(
        string='Description',
        required=True,
        help='Description of this recognition entry'
    )

    # Related Records
    schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='AMS Subscription',
        related='schedule_id.subscription_id',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='schedule_id.product_id',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='schedule_id.partner_id',
        store=True,
        readonly=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Source Invoice',
        related='schedule_id.invoice_id',
        store=True,
        readonly=True
    )

    # Recognition Details
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        index=True,
        help='Date when this revenue should be recognized'
    )
    
    scheduled_amount = fields.Monetary(
        string='Scheduled Amount',
        required=True,
        currency_field='currency_id',
        help='Amount scheduled to be recognized'
    )
    
    recognized_amount = fields.Monetary(
        string='Recognized Amount',
        currency_field='currency_id',
        default=0.0,
        help='Amount actually recognized (may differ from scheduled due to adjustments)'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='schedule_id.currency_id',
        store=True,
        readonly=True
    )

    # Status and Processing
    state = fields.Selection([
        ('pending', 'Pending'),
        ('recognized', 'Recognized'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    processed_date = fields.Datetime(
        string='Processed Date',
        readonly=True,
        help='When this recognition was actually processed'
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True,
        help='User who processed this recognition'
    )

    # Journal Entry Information
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        help='Journal entry created for this recognition'
    )
    
    journal_entry_line_ids = fields.One2many(
        'account.move.line',
        related='journal_entry_id.line_ids',
        string='Journal Entry Lines',
        readonly=True
    )

    # Account Information (from schedule)
    revenue_account_id = fields.Many2one(
        'account.account',
        string='Revenue Account',
        related='schedule_id.revenue_account_id',
        store=True,
        readonly=True
    )
    
    deferred_account_id = fields.Many2one(
        'account.account',
        string='Deferred Account',
        related='schedule_id.deferred_account_id',
        store=True,
        readonly=True
    )

    # Computed Fields
    @api.depends('schedule_id', 'recognition_date', 'scheduled_amount')
    def _compute_display_name(self):
        """Compute display name for recognition entry"""
        for recognition in self:
            if recognition.schedule_id and recognition.recognition_date:
                schedule_name = recognition.schedule_id.display_name or 'Schedule'
                date_str = recognition.recognition_date.strftime('%Y-%m-%d') if recognition.recognition_date else 'No Date'
                recognition.display_name = f"{schedule_name} - {date_str}"
            else:
                recognition.display_name = f"Recognition #{recognition.id or 'New'}"

    # Constraints and Validation
    @api.constrains('scheduled_amount', 'recognized_amount')
    def _check_amounts(self):
        """Validate amounts"""
        for recognition in self:
            if recognition.scheduled_amount <= 0:
                raise UserError(_('Scheduled amount must be greater than zero'))
            
            if recognition.state == 'recognized' and recognition.recognized_amount <= 0:
                raise UserError(_('Recognized amount must be greater than zero when recognized'))

    @api.constrains('recognition_date')
    def _check_recognition_date(self):
        """Validate recognition date"""
        for recognition in self:
            if recognition.recognition_date and recognition.schedule_id:
                if (recognition.recognition_date < recognition.schedule_id.start_date or 
                    recognition.recognition_date > recognition.schedule_id.end_date):
                    raise UserError(_('Recognition date must be within the schedule period'))

    # Actions and Processing
    def action_recognize_revenue(self):
        """Process this revenue recognition entry"""
        for recognition in self:
            if recognition.state != 'pending':
                raise UserError(_('Only pending recognitions can be processed'))
            
            if not recognition.revenue_account_id:
                raise UserError(_('Revenue account is required for recognition'))
            
            # Create journal entry
            journal_entry = recognition._create_recognition_journal_entry()
            
            if journal_entry:
                # Update recognition record
                recognition.write({
                    'state': 'recognized',
                    'recognized_amount': recognition.scheduled_amount,  # Default to scheduled
                    'processed_date': fields.Datetime.now(),
                    'processed_by': recognition.env.user.id,
                    'journal_entry_id': journal_entry.id,
                })
                
                # Post the journal entry
                if journal_entry.state == 'draft':
                    journal_entry.action_post()
                
                recognition.message_post(
                    body=f"Revenue recognized: {recognition.currency_id.symbol}{recognition.recognized_amount:.2f}"
                )
                
                # Update schedule's last processed date
                recognition.schedule_id.last_processed_date = recognition.recognition_date
            
            return journal_entry

    def action_cancel_recognition(self):
        """Cancel this revenue recognition"""
        for recognition in self:
            if recognition.state == 'recognized':
                raise UserError(_('Cannot cancel recognized revenue. Create reversing entry instead.'))
            
            recognition.state = 'cancelled'
            recognition.message_post(body=_('Revenue recognition cancelled'))

    def _create_recognition_journal_entry(self):
        """Create journal entry for revenue recognition"""
        self.ensure_one()
        
        if not self.deferred_account_id and not self.revenue_account_id:
            raise UserError(_('Either deferred or revenue account is required'))
        
        # Determine journal to use
        journal = self._get_recognition_journal()
        
        # Prepare journal entry values
        entry_vals = {
            'ref': f"Revenue Recognition - {self.schedule_id.display_name}",
            'journal_id': journal.id,
            'date': self.recognition_date,
            'move_type': 'entry',
            'line_ids': [],
        }
        
        # Create journal entry lines
        lines = self._prepare_journal_entry_lines()
        entry_vals['line_ids'] = [(0, 0, line) for line in lines]
        
        # Create the journal entry
        journal_entry = self.env['account.move'].create(entry_vals)
        
        return journal_entry

    def _prepare_journal_entry_lines(self):
        """Prepare journal entry lines for revenue recognition"""
        lines = []
        amount = self.scheduled_amount
        
        if self.schedule_id.recognition_method == 'immediate':
            # Immediate recognition: DR Revenue, CR A/R (usually already done by invoice)
            # This might not create lines if revenue was already recognized in invoice
            pass
        else:
            # Deferred recognition: DR Deferred Revenue, CR Revenue
            if self.deferred_account_id and self.revenue_account_id:
                # Debit Deferred Revenue (reduces liability)
                lines.append({
                    'name': f"Revenue Recognition - {self.description}",
                    'account_id': self.deferred_account_id.id,
                    'debit': amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id,
                })
                
                # Credit Revenue (increases income)
                lines.append({
                    'name': f"Revenue Recognition - {self.description}",
                    'account_id': self.revenue_account_id.id,
                    'debit': 0.0,
                    'credit': amount,
                    'partner_id': self.partner_id.id,
                })
        
        return lines

    def _get_recognition_journal(self):
        """Get the appropriate journal for revenue recognition"""
        # Try to find AMS journal first
        ams_journal = self.env['account.journal'].search([
            ('code', '=', 'AMS'),
            ('type', 'in', ['sale', 'general'])
        ], limit=1)
        
        if ams_journal:
            return ams_journal
        
        # Fall back to default general journal
        general_journal = self.env['account.journal'].search([
            ('type', '=', 'general')
        ], limit=1)
        
        if not general_journal:
            raise UserError(_('No suitable journal found for revenue recognition'))
        
        return general_journal

    def action_view_journal_entry(self):
        """View the journal entry for this recognition"""
        self.ensure_one()
        
        if not self.journal_entry_id:
            raise UserError(_('No journal entry exists for this recognition'))
        
        return {
            'name': 'Revenue Recognition Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reverse_recognition(self):
        """Create reversing entry for this recognition"""
        self.ensure_one()
        
        if self.state != 'recognized':
            raise UserError(_('Only recognized revenue can be reversed'))
        
        if not self.journal_entry_id:
            raise UserError(_('No journal entry to reverse'))
        
        # Create reversal of the journal entry
        reversal_wizard = self.env['account.move.reversal'].with_context({
            'active_model': 'account.move',
            'active_ids': [self.journal_entry_id.id],
        }).create({
            'reason': f"Reversal of revenue recognition - {self.description}",
            'refund_method': 'cancel',  # Creates counterpart move
        })
        
        reversal_result = reversal_wizard.reverse_moves()
        
        if reversal_result.get('res_id'):
            # Update recognition status
            self.write({
                'state': 'cancelled',
                'recognized_amount': 0.0,
            })
            
            self.message_post(
                body=f"Revenue recognition reversed. Reversal entry: {reversal_result.get('res_id')}"
            )
        
        return reversal_result

    @api.model
    def process_batch_recognitions(self, cutoff_date=None):
        """Process multiple revenue recognitions in batch"""
        if not cutoff_date:
            cutoff_date = fields.Date.today()
        
        # Find all pending recognitions due by cutoff date
        pending_recognitions = self.search([
            ('state', '=', 'pending'),
            ('recognition_date', '<=', cutoff_date),
            ('schedule_id.state', '=', 'active'),
        ])
        
        processed_count = 0
        error_count = 0
        
        for recognition in pending_recognitions:
            try:
                recognition.action_recognize_revenue()
                processed_count += 1
            except Exception as e:
                error_count += 1
                recognition.message_post(
                    body=f"Error processing revenue recognition: {str(e)}",
                    message_type='comment'
                )
        
        return {
            'processed': processed_count,
            'errors': error_count,
            'total': len(pending_recognitions),
        }