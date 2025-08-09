# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

class AMSRevenueRecognition(models.Model):
    """Individual Revenue Recognition Entries"""
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition Entry'
    _order = 'recognition_date desc, id desc'
    _rec_name = 'description'

    # Basic Information
    description = fields.Char(
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
        related='schedule_id.subscription_id',
        string='Subscription',
        store=True,
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        related='schedule_id.product_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        related='schedule_id.partner_id', 
        string='Customer',
        store=True,
        readonly=True
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        related='schedule_id.invoice_id',
        string='Source Invoice',
        store=True,
        readonly=True
    )

    # Recognition Details
    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        index=True,
        help='Date when revenue should be recognized'
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
        help='Amount actually recognized (may differ due to adjustments)'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='schedule_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Journal Entry Information
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Recognition Journal Entry',
        readonly=True,
        help='Journal entry created for this recognition'
    )
    
    # State and Processing
    state = fields.Selection([
        ('pending', 'Pending'),
        ('recognized', 'Recognized'),
        ('reversed', 'Reversed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True)
    
    processed_date = fields.Datetime(
        string='Processed Date',
        readonly=True,
        help='When this recognition was processed'
    )
    
    processed_by = fields.Many2one(
        'res.users',
        string='Processed By',
        readonly=True,
        help='User who processed this recognition'
    )
    
    # Accounts (from schedule/product)
    revenue_account_id = fields.Many2one(
        'account.account',
        related='schedule_id.revenue_account_id',
        string='Revenue Account',
        store=True,
        readonly=True
    )
    
    deferred_account_id = fields.Many2one(
        'account.account',
        related='schedule_id.deferred_account_id',
        string='Deferred Account',
        store=True,
        readonly=True
    )

    # Constraints and Validation
    @api.constrains('scheduled_amount')
    def _check_scheduled_amount(self):
        """Validate scheduled amount"""
        for recognition in self:
            if recognition.scheduled_amount <= 0:
                raise ValidationError(_('Scheduled amount must be greater than zero'))
    
    @api.constrains('recognition_date')
    def _check_recognition_date(self):
        """Validate recognition date"""
        for recognition in self:
            if recognition.recognition_date and recognition.schedule_id:
                schedule = recognition.schedule_id
                if recognition.recognition_date < schedule.start_date:
                    raise ValidationError(_('Recognition date cannot be before schedule start date'))
                if recognition.recognition_date > schedule.end_date:
                    raise ValidationError(_('Recognition date cannot be after schedule end date'))
    
    # Main Actions
    def action_recognize_revenue(self):
        """Process this revenue recognition entry"""
        for recognition in self:
            if recognition.state != 'pending':
                raise UserError(_('Only pending recognitions can be processed'))
            
            # Validate accounts are configured
            if not recognition.revenue_account_id:
                raise UserError(_('Revenue account not configured for product %s') % recognition.product_id.name)
            
            if recognition.schedule_id.recognition_method == 'straight_line' and not recognition.deferred_account_id:
                raise UserError(_('Deferred revenue account not configured for product %s') % recognition.product_id.name)
            
            # Set recognized amount (default to scheduled amount)
            if not recognition.recognized_amount:
                recognition.recognized_amount = recognition.scheduled_amount
            
            # Create journal entry
            recognition._create_journal_entry()
            
            # Update status
            recognition.write({
                'state': 'recognized',
                'processed_date': fields.Datetime.now(),
                'processed_by': self.env.user.id,
            })
    
    def action_reverse_recognition(self):
        """Reverse this revenue recognition"""
        for recognition in self:
            if recognition.state != 'recognized':
                raise UserError(_('Only recognized entries can be reversed'))
            
            # Create reversal entry
            reversal = recognition.copy({
                'description': f'Reversal of: {recognition.description}',
                'scheduled_amount': -recognition.recognized_amount,
                'recognized_amount': -recognition.recognized_amount,
                'state': 'pending',
                'journal_entry_id': False,
                'processed_date': False,
                'processed_by': False,
            })
            
            # Process the reversal immediately
            reversal.action_recognize_revenue()
            
            # Update original entry state
            recognition.state = 'reversed'
            
            return reversal
    
    def _create_journal_entry(self):
        """Create journal entry for revenue recognition"""
        self.ensure_one()
        
        if self.journal_entry_id:
            # Already has journal entry
            return self.journal_entry_id
        
        # Get company and journal
        company = self.env.company
        journal = self._get_recognition_journal()
        
        # Prepare journal entry values
        move_vals = {
            'journal_id': journal.id,
            'date': self.recognition_date,
            'ref': f'Revenue Recognition - {self.description}',
            'move_type': 'entry',
            'line_ids': self._prepare_journal_entry_lines(),
        }
        
        # Create journal entry
        move = self.env['account.move'].create(move_vals)
        
        # Post the entry
        move.action_post()
        
        # Link to recognition
        self.journal_entry_id = move.id
        
        return move
    
    def _prepare_journal_entry_lines(self):
        """Prepare journal entry lines for revenue recognition"""
        self.ensure_one()
        
        lines = []
        amount = abs(self.recognized_amount)
        
        if self.schedule_id.recognition_method == 'straight_line':
            # Transfer from deferred to earned revenue
            # DR: Deferred Revenue (liability decrease)
            lines.append((0, 0, {
                'account_id': self.deferred_account_id.id,
                'name': f'Deferred Revenue Recognition - {self.description}',
                'debit': amount if self.recognized_amount > 0 else 0,
                'credit': amount if self.recognized_amount < 0 else 0,
                'partner_id': self.partner_id.id,
            }))
            
            # CR: Revenue (income increase)
            lines.append((0, 0, {
                'account_id': self.revenue_account_id.id,
                'name': f'Revenue Recognition - {self.description}',
                'credit': amount if self.recognized_amount > 0 else 0,
                'debit': amount if self.recognized_amount < 0 else 0,
                'partner_id': self.partner_id.id,
            }))
        
        return lines
    
    def _get_recognition_journal(self):
        """Get the journal to use for recognition entries"""
        # Try to find AMS journal first
        ams_journal = self.env['account.journal'].search([
            ('code', '=', 'AMS'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if ams_journal:
            return ams_journal
        
        # Fall back to general journal
        general_journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not general_journal:
            raise UserError(_('No general journal found for revenue recognition'))
        
        return general_journal
    
    def action_view_journal_entry(self):
        """View the journal entry for this recognition"""
        self.ensure_one()
        
        if not self.journal_entry_id:
            raise UserError(_('No journal entry created for this recognition'))
        
        return {
            'name': 'Revenue Recognition Journal Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def process_due_recognitions(self, cutoff_date=None):
        """Process all pending recognitions due by cutoff date"""
        if not cutoff_date:
            cutoff_date = fields.Date.today()
        
        due_recognitions = self.search([
            ('state', '=', 'pending'),
            ('recognition_date', '<=', cutoff_date)
        ])
        
        processed_count = 0
        errors = []
        
        for recognition in due_recognitions:
            try:
                recognition.action_recognize_revenue()
                processed_count += 1
            except Exception as e:
                errors.append(f'Recognition {recognition.id}: {str(e)}')
        
        return {
            'processed_count': processed_count,
            'total_due': len(due_recognitions),
            'errors': errors
        }