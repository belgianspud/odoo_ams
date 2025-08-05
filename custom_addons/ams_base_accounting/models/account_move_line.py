# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AccountMoveLine(models.Model):
    _name = 'ams.account.move.line'
    _description = 'AMS Journal Entry Line'
    _order = 'move_id, sequence, id'
    
    # Basic fields
    name = fields.Char(
        string='Label',
        required=True,
        help='Description of the journal item'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering lines within a journal entry'
    )
    
    move_id = fields.Many2one(
        'ams.account.move',
        string='Journal Entry',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    account_id = fields.Many2one(
        'ams.account.account',
        string='Account',
        required=True,
        index=True,
        ondelete='restrict'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        ondelete='restrict'
    )
    
    # Amounts
    debit = fields.Float(
        string='Debit',
        default=0.0,
        digits='Account',
        help='Debit amount for this line'
    )
    
    credit = fields.Float(
        string='Credit',
        default=0.0,
        digits='Account',
        help='Credit amount for this line'
    )
    
    balance = fields.Float(
        string='Balance',
        compute='_compute_balance',
        store=True,
        help='Debit - Credit'
    )
    
    # Currency handling
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Currency of this line'
    )
    
    amount_currency = fields.Float(
        string='Amount in Currency',
        help='Amount in the specified currency'
    )
    
    # Related fields from move
    date = fields.Date(
        related='move_id.date',
        string='Date',
        store=True,
        index=True
    )
    
    journal_id = fields.Many2one(
        related='move_id.journal_id',
        string='Journal',
        store=True,
        index=True
    )
    
    company_id = fields.Many2one(
        related='move_id.company_id',
        string='Company',
        store=True,
        index=True
    )
    
    move_state = fields.Selection(
        related='move_id.state',
        string='Status',
        store=True
    )
    
    move_name = fields.Char(
        related='move_id.name',
        string='Journal Entry Number',
        store=True
    )
    
    # Account related fields
    account_type = fields.Selection(
        related='account_id.account_type',
        string='Account Type',
        store=True
    )
    
    account_code = fields.Char(
        related='account_id.code',
        string='Account Code',
        store=True
    )
    
    # AMS-specific fields
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        help='Related subscription for this journal item'
    )
    
    revenue_recognition_id = fields.Many2one(
        'ams.revenue.recognition',
        string='Revenue Recognition',
        help='Revenue recognition record that generated this line'
    )
    
    ams_category = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('event', 'Event'),
        ('general', 'General'),
    ], string='AMS Category', help='Categorizes line by AMS function')
    
    # Reconciliation
    reconciled = fields.Boolean(
        string='Reconciled',
        default=False,
        help='This line has been reconciled'
    )
    
    full_reconcile_id = fields.Many2one(
        'ams.account.full.reconcile',
        string='Matching Number',
        copy=False
    )
    
    matched_debit_ids = fields.One2many(
        'ams.account.partial.reconcile',
        'credit_move_id',
        string='Matched Debits',
        help='Debit journal items matched with this credit journal item'
    )
    
    matched_credit_ids = fields.One2many(
        'ams.account.partial.reconcile',
        'debit_move_id',
        string='Matched Credits',
        help='Credit journal items matched with this debit journal item'
    )
    
    # Analytic accounting (for cost centers, projects, etc.)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account for cost tracking'
    )
    
    # Product information
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Product related to this journal item'
    )
    
    quantity = fields.Float(
        string='Quantity',
        help='Quantity of product/service'
    )
    
    # Tax information
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help='Taxes applied to this line'
    )
    
    tax_line_id = fields.Many2one(
        'account.tax',
        string='Originator Tax',
        help='Tax that generated this tax line'
    )
    
    tax_base_amount = fields.Float(
        string='Tax Base Amount',
        help='Base amount for tax calculation'
    )
    
    @api.depends('debit', 'credit')
    def _compute_balance(self):
        """Compute balance (debit - credit)"""
        for line in self:
            line.balance = line.debit - line.credit
    
    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        """Ensure debit and credit are not both non-zero"""
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError('Debit and credit amounts must be positive')
            
            if line.debit > 0 and line.credit > 0:
                raise ValidationError('A journal item cannot have both debit and credit amounts')
    
    @api.onchange('account_id')
    def _onchange_account_id(self):
        """Update currency when account changes"""
        if self.account_id and self.account_id.currency_id:
            self.currency_id = self.account_id.currency_id
    
    @api.onchange('debit', 'credit', 'currency_id', 'amount_currency')
    def _onchange_amount_currency(self):
        """Handle currency conversions"""
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            if self.amount_currency:
                # Convert amount_currency to company currency
                company_currency = self.company_id.currency_id
                if self.debit:
                    self.debit = self.currency_id._convert(
                        self.amount_currency, company_currency, 
                        self.company_id, self.date or fields.Date.today()
                    )
                elif self.credit:
                    self.credit = self.currency_id._convert(
                        self.amount_currency, company_currency,
                        self.company_id, self.date or fields.Date.today()
                    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults and validate"""
        for vals in vals_list:
            # Set AMS category from move if not provided
            if not vals.get('ams_category') and vals.get('move_id'):
                move = self.env['ams.account.move'].browse(vals['move_id'])
                if move.ams_category:
                    vals['ams_category'] = move.ams_category
            
            # Set subscription from move if not provided
            if not vals.get('subscription_id') and vals.get('move_id'):
                move = self.env['ams.account.move'].browse(vals['move_id'])
                if move.subscription_id:
                    vals['subscription_id'] = move.subscription_id.id
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to prevent modification of posted entries"""
        for line in self:
            if line.move_state == 'posted':
                allowed_fields = ['reconciled', 'full_reconcile_id', 'analytic_account_id']
                if any(field not in allowed_fields for field in vals.keys()):
                    raise UserError(f'Cannot modify posted journal entry {line.move_name}')
        
        return super().write(vals)
    
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        """Reconcile journal items"""
        if not self:
            return True
        
        # Group by account and partner
        lines_by_account = {}
        for line in self:
            if not line.account_id.reconcile:
                raise UserError(f'Account {line.account_id.name} does not allow reconciliation')
            
            key = (line.account_id.id, line.partner_id.id)
            if key not in lines_by_account:
                lines_by_account[key] = self.env['ams.account.move.line']
            lines_by_account[key] |= line
        
        # Reconcile each group
        for lines in lines_by_account.values():
            total_balance = sum(lines.mapped('balance'))
            
            if abs(total_balance) < 0.01:  # Fully reconciled
                reconcile_vals = {
                    'name': f'Reconcile {lines[0].account_id.code}',
                    'create_date': fields.Datetime.now(),
                }
                full_reconcile = self.env['ams.account.full.reconcile'].create(reconcile_vals)
                lines.write({
                    'reconciled': True,
                    'full_reconcile_id': full_reconcile.id,
                })
            else:
                # Partial reconciliation
                # This would create partial reconcile records
                # Implementation simplified for brevity
                pass
        
        return True
    
    def remove_move_reconcile(self):
        """Remove reconciliation"""
        for line in self:
            line.write({
                'reconciled': False,
                'full_reconcile_id': False,
            })
        
        return True
    
    def action_view_subscription(self):
        """View related subscription"""
        self.ensure_one()
        if not self.subscription_id:
            raise UserError('No subscription linked to this journal item')
        
        return {
            'name': 'Related Subscription',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override to add computed fields to search results"""
        result = super().search_read(domain, fields, offset, limit, order)
        
        # Add computed display names if needed
        for record in result:
            if 'display_name' in record and not record.get('display_name'):
                account_name = record.get('account_id', ['', ''])[1] if record.get('account_id') else ''
                partner_name = record.get('partner_id', ['', ''])[1] if record.get('partner_id') else ''
                
                display_parts = [record.get('name', '')]
                if account_name:
                    display_parts.append(account_name)
                if partner_name:
                    display_parts.append(partner_name)
                
                record['display_name'] = ' - '.join(filter(None, display_parts))
        
        return result
    
    def name_get(self):
        """Display format for journal lines"""
        result = []
        for line in self:
            name_parts = [line.name]
            if line.account_id:
                name_parts.append(f'[{line.account_id.code}]')
            if line.partner_id:
                name_parts.append(line.partner_id.name)
            
            name = ' - '.join(name_parts)
            result.append((line.id, name))
        
        return result


class AccountFullReconcile(models.Model):
    """Full reconciliation model"""
    _name = 'ams.account.full.reconcile'
    _description = 'Full Reconciliation'
    
    name = fields.Char(
        string='Number',
        required=True,
        default='New'
    )
    
    reconciled_line_ids = fields.One2many(
        'ams.account.move.line',
        'full_reconcile_id',
        string='Reconciled Lines'
    )
    
    create_date = fields.Datetime(
        string='Created On',
        default=fields.Datetime.now
    )


class AccountPartialReconcile(models.Model):
    """Partial reconciliation model"""
    _name = 'ams.account.partial.reconcile'
    _description = 'Partial Reconciliation'
    
    debit_move_id = fields.Many2one(
        'ams.account.move.line',
        string='Debit Move',
        required=True,
        ondelete='cascade'
    )
    
    credit_move_id = fields.Many2one(
        'ams.account.move.line',
        string='Credit Move',
        required=True,
        ondelete='cascade'
    )
    
    amount = fields.Float(
        string='Amount',
        required=True,
        help='Amount reconciled'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )
    
    create_date = fields.Datetime(
        string='Created On',
        default=fields.Datetime.now
    )