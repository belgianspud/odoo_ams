# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class AccountMove(models.Model):
    _name = 'ams.account.move'
    _description = 'AMS Journal Entry'
    _order = 'date desc, name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Number',
        required=True,
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default='New'
    )
    
    ref = fields.Char(
        string='Reference',
        copy=False,
        tracking=True,
        help='External reference or description'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
        tracking=True
    )
    
    journal_id = fields.Many2one(
        'ams.account.journal',
        string='Journal',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.company.currency_id
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, tracking=True, default='draft')
    
    move_type = fields.Selection([
        ('entry', 'Journal Entry'),
        ('subscription', 'Subscription Entry'),
        ('revenue_recognition', 'Revenue Recognition'),
        ('payment', 'Payment Entry'),
        ('adjustment', 'Adjustment Entry'),
    ], string='Type', required=True, default='entry',
       readonly=True, states={'draft': [('readonly', False)]})
    
    # Journal entry lines
    line_ids = fields.One2many(
        'ams.account.move.line',
        'move_id',
        string='Journal Items',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    # Totals
    amount_total = fields.Float(
        string='Total Amount',
        compute='_compute_amount',
        store=True,
        tracking=True
    )
    
    amount_total_signed = fields.Float(
        string='Total Signed',
        compute='_compute_amount',
        store=True,
        help='Total amount in the direction of the journal'
    )
    
    # Subscription integration
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Related Subscription',
        help='Subscription that generated this journal entry'
    )
    
    revenue_recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Revenue Recognition',
        help='Revenue recognition record that generated this entry'
    )
    
    # AMS-specific fields
    is_ams_entry = fields.Boolean(
        string='AMS Entry',
        default=True,
        help='This entry was created by AMS accounting'
    )
    
    ams_category = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('event', 'Event'),
        ('general', 'General'),
    ], string='AMS Category', help='Categorizes entry by AMS function')
    
    # Partner information
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )
    
    # Posting information
    posted_by = fields.Many2one(
        'res.users',
        string='Posted By',
        readonly=True,
        copy=False
    )
    
    posted_date = fields.Datetime(
        string='Posted Date',
        readonly=True,
        copy=False
    )
    
    # Auto-posting
    auto_post = fields.Boolean(
        string='Auto Post',
        help='Automatically post this entry when created'
    )
    
    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_amount(self):
        """Compute total amounts"""
        for move in self:
            total_debit = sum(move.line_ids.mapped('debit'))
            total_credit = sum(move.line_ids.mapped('credit'))
            
            move.amount_total = max(total_debit, total_credit)
            move.amount_total_signed = total_debit - total_credit
    
    @api.constrains('line_ids')
    def _check_balanced(self):
        """Ensure journal entry is balanced"""
        for move in self:
            if move.state == 'posted':
                total_debit = sum(move.line_ids.mapped('debit'))
                total_credit = sum(move.line_ids.mapped('credit'))
                
                if abs(total_debit - total_credit) > 0.01:  # Allow for rounding
                    raise ValidationError(
                        f'Journal Entry {move.name} is not balanced. '
                        f'Debits: {total_debit}, Credits: {total_credit}'
                    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle numbering and auto-posting"""
        for vals in vals_list:
            # Set sequence number if not provided
            if vals.get('name', 'New') == 'New':
                journal = self.env['ams.account.journal'].browse(vals.get('journal_id'))
                if journal and journal.sequence_id:
                    vals['name'] = journal.sequence_id.next_by_id()
                else:
                    vals['name'] = 'MISC/001'  # Fallback
            
            # Set AMS category based on journal type
            if not vals.get('ams_category') and vals.get('journal_id'):
                journal = self.env['ams.account.journal'].browse(vals.get('journal_id'))
                if journal.type in ['membership', 'chapter', 'publication']:
                    vals['ams_category'] = journal.type
        
        moves = super().create(vals_list)
        
        # Auto-post if requested
        for move in moves:
            if move.auto_post or (move.journal_id and move.journal_id.auto_post):
                try:
                    move.action_post()
                except Exception as e:
                    # Log error but don't fail creation
                    move.message_post(body=f'Auto-post failed: {str(e)}')
        
        return moves
    
    def action_post(self):
        """Post the journal entry"""
        for move in self:
            if move.state != 'draft':
                raise UserError(f'Only draft entries can be posted. Entry {move.name} is {move.state}')
            
            # Validate entry is balanced
            total_debit = sum(move.line_ids.mapped('debit'))
            total_credit = sum(move.line_ids.mapped('credit'))
            
            if abs(total_debit - total_credit) > 0.01:
                raise UserError(
                    f'Entry {move.name} is not balanced. '
                    f'Debits: {total_debit:.2f}, Credits: {total_credit:.2f}'
                )
            
            # Validate at least one line exists
            if not move.line_ids:
                raise UserError(f'Entry {move.name} has no journal items')
            
            # Post the entry
            move.write({
                'state': 'posted',
                'posted_by': self.env.user.id,
                'posted_date': fields.Datetime.now(),
            })
            
            move.message_post(body=f'Journal entry posted by {self.env.user.name}')
    
    def action_cancel(self):
        """Cancel the journal entry"""
        for move in self:
            if move.state == 'cancelled':
                raise UserError(f'Entry {move.name} is already cancelled')
            
            move.write({'state': 'cancelled'})
            move.message_post(body=f'Journal entry cancelled by {self.env.user.name}')
    
    def action_draft(self):
        """Reset entry to draft"""
        for move in self:
            if move.state not in ['posted', 'cancelled']:
                raise UserError(f'Cannot reset entry {move.name} to draft from state {move.state}')
            
            move.write({
                'state': 'draft',
                'posted_by': False,
                'posted_date': False,
            })
            
            move.message_post(body=f'Journal entry reset to draft by {self.env.user.name}')
    
    def unlink(self):
        """Prevent deletion of posted entries"""
        for move in self:
            if move.state == 'posted':
                raise UserError(f'Cannot delete posted journal entry {move.name}')
        return super().unlink()
    
    @api.model
    def create_subscription_entry(self, subscription, invoice_amount, description=None):
        """Create journal entry for subscription payment"""
        if not description:
            description = f'Subscription payment - {subscription.name}'
        
        # Get accounts
        product = subscription.product_id.product_tmpl_id
        cash_account = self._get_cash_account()
        deferred_revenue_account = product.deferred_revenue_account_id
        
        if not deferred_revenue_account:
            raise UserError(f'No deferred revenue account configured for product {product.name}')
        
        # Get subscription journal
        journal = self.env['ams.account.journal'].get_subscription_journal()
        if not journal:
            raise UserError('No subscription journal configured')
        
        # Create journal entry
        entry_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': description,
            'move_type': 'subscription',
            'subscription_id': subscription.id,
            'partner_id': subscription.partner_id.id,
            'ams_category': subscription.subscription_type if subscription.subscription_type in ['membership', 'chapter', 'publication'] else 'general',
            'line_ids': [
                # Debit Cash
                (0, 0, {
                    'account_id': cash_account.id,
                    'partner_id': subscription.partner_id.id,
                    'debit': invoice_amount,
                    'credit': 0.0,
                    'name': description,
                }),
                # Credit Deferred Revenue
                (0, 0, {
                    'account_id': deferred_revenue_account.id,
                    'partner_id': subscription.partner_id.id,
                    'debit': 0.0,
                    'credit': invoice_amount,
                    'name': description,
                }),
            ]
        }
        
        return self.create(entry_vals)
    
    def _get_cash_account(self):
        """Get default cash account"""
        cash_account = self.env['ams.account.account'].search([
            ('account_type', '=', 'asset_cash'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not cash_account:
            raise UserError('No cash account found. Please create a cash account first.')
        
        return cash_account
    
    @api.model
    def create_revenue_recognition_entry(self, subscription, recognition_amount, period_start, period_end):
        """Create journal entry for revenue recognition"""
        description = f'Revenue recognition - {subscription.name} ({period_start} to {period_end})'
        
        # Get accounts
        product = subscription.product_id.product_tmpl_id
        deferred_revenue_account = product.deferred_revenue_account_id
        revenue_account = product.revenue_account_id
        
        if not deferred_revenue_account or not revenue_account:
            raise UserError(f'Revenue accounts not configured for product {product.name}')
        
        # Get revenue recognition journal
        journal = self.env['ams.account.journal'].get_revenue_recognition_journal()
        if not journal:
            raise UserError('No revenue recognition journal configured')
        
        # Create journal entry
        entry_vals = {
            'journal_id': journal.id,
            'date': period_end,  # Recognize revenue at end of period
            'ref': description,
            'move_type': 'revenue_recognition',
            'subscription_id': subscription.id,
            'partner_id': subscription.partner_id.id,
            'ams_category': subscription.subscription_type if subscription.subscription_type in ['membership', 'chapter', 'publication'] else 'general',
            'auto_post': True,  # Auto-post revenue recognition entries
            'line_ids': [
                # Debit Deferred Revenue
                (0, 0, {
                    'account_id': deferred_revenue_account.id,
                    'partner_id': subscription.partner_id.id,
                    'debit': recognition_amount,
                    'credit': 0.0,
                    'name': description,
                }),
                # Credit Revenue
                (0, 0, {
                    'account_id': revenue_account.id,
                    'partner_id': subscription.partner_id.id,
                    'debit': 0.0,
                    'credit': recognition_amount,
                    'name': description,
                }),
            ]
        }
        
        return self.create(entry_vals)
    
    def name_get(self):
        """Display format"""
        result = []
        for move in self:
            name = f'{move.name}'
            if move.ref:
                name += f' - {move.ref}'
            result.append((move.id, name))
        return result