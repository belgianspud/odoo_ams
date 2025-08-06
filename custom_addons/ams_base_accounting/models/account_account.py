# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AccountAccount(models.Model):
    _name = 'ams.account.account'
    _description = 'AMS Chart of Accounts'
    _order = 'code, name'
    _parent_store = True
    _parent_name = 'parent_id'
    
    name = fields.Char(
        string='Account Name',
        required=True,
        index=True,
        translate=True
    )
    
    code = fields.Char(
        string='Account Code',
        size=64,
        required=True,
        index=True,
        help='Account code must be unique'
    )
    
    account_type = fields.Selection([
        # Assets
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        
        # Liabilities  
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        ('liability_deferred_revenue', 'Deferred Revenue'),
        
        # Equity
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        
        # Revenue
        ('income', 'Income'),
        ('income_membership', 'Membership Revenue'),
        ('income_chapter', 'Chapter Revenue'),
        ('income_publication', 'Publication Revenue'),
        ('income_other', 'Other Revenue'),
        
        # Expenses
        ('expense', 'Expenses'),
        ('expense_direct_cost', 'Cost of Revenue'),
        ('expense_depreciation', 'Depreciation'),
        
        # Off Balance Sheet
        ('off_balance', 'Off-Balance Sheet'),
    ], string='Account Type', required=True, 
       help='The account type determines where this account appears in financial reports')
    
    parent_id = fields.Many2one(
        'ams.account.account',
        string='Parent Account',
        index=True,
        ondelete='cascade',
        help='The parent account for creating account hierarchies'
    )
    
    parent_path = fields.Char(index=True)
    
    child_ids = fields.One2many(
        'ams.account.account',
        'parent_id',
        string='Child Accounts'
    )
    
    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        store=True,
        help='Account hierarchy level (0 = top level)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Account Currency',
        help='Forces all journal entries on this account to have this currency'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive accounts are hidden from selection lists'
    )
    
    reconcile = fields.Boolean(
        string='Allow Reconciliation',
        default=False,
        help='Allow journal entries on this account to be reconciled'
    )
    
    note = fields.Text(string='Internal Notes')
    
    # AMS-specific fields
    is_ams_account = fields.Boolean(
        string='AMS Account',
        default=True,
        help='This account is managed by AMS accounting'
    )
    
    ams_category = fields.Selection([
        ('membership', 'Membership Related'),
        ('chapter', 'Chapter Related'),
        ('publication', 'Publication Related'),
        ('event', 'Event Related'),
        ('general', 'General Operations'),
    ], string='AMS Category', help='Categorizes accounts by AMS function')
    
    # Balance and totals
    balance = fields.Float(
        string='Current Balance',
        compute='_compute_balance',
        help='Current account balance'
    )
    
    debit_total = fields.Float(
        string='Total Debit',
        compute='_compute_balance',
        help='Total debits for this account'
    )
    
    credit_total = fields.Float(
        string='Total Credit', 
        compute='_compute_balance',
        help='Total credits for this account'
    )
    
    # Usage tracking
    move_line_ids = fields.One2many(
        'ams.account.move.line',
        'account_id',
        string='Journal Items',
        readonly=True
    )
    
    @api.depends('parent_id')
    def _compute_level(self):
        """Compute account hierarchy level"""
        for account in self:
            level = 0
            parent = account.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            account.level = level
    
    def _compute_balance(self):
        """Compute account balances from journal entries"""
        for account in self:
            # This would normally query journal entries
            # For now, set defaults - will be enhanced when journal entries are implemented
            account.balance = 0.0
            account.debit_total = 0.0
            account.credit_total = 0.0
    
    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Ensure no circular references in account hierarchy"""
        if not self._check_recursion():
            raise ValidationError('Error! You cannot create recursive account hierarchies.')
    
    @api.constrains('code', 'company_id')
    def _check_code_company_unique(self):
        """Ensure account codes are unique per company"""
        for account in self:
            if self.search_count([
                ('code', '=', account.code),
                ('company_id', '=', account.company_id.id),
                ('id', '!=', account.id)
            ]) > 0:
                raise ValidationError(f'Account code "{account.code}" already exists for company "{account.company_id.name}"')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to validate account creation"""
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code'):
                vals['code'] = self._generate_account_code(vals.get('account_type'))
        
        return super().create(vals_list)
    
    def _generate_account_code(self, account_type):
        """Generate account code based on type"""
        code_prefixes = {
            'asset_receivable': '1200',
            'asset_cash': '1000',
            'asset_current': '1300',
            'asset_non_current': '1500',
            'asset_fixed': '1600',
            'liability_payable': '2000',
            'liability_current': '2100',
            'liability_deferred_revenue': '2400',
            'equity': '3000',
            'income_membership': '4100',
            'income_chapter': '4200', 
            'income_publication': '4300',
            'income': '4000',
            'expense': '5000',
            'expense_direct_cost': '5100',
        }
        
        prefix = code_prefixes.get(account_type, '9000')
        
        # Find next available number
        existing_codes = self.search([
            ('code', 'like', f'{prefix}%'),
            ('company_id', '=', self.env.company.id)
        ]).mapped('code')
        
        for i in range(1, 100):
            new_code = f'{prefix}{i:02d}'
            if new_code not in existing_codes:
                return new_code
        
        return f'{prefix}99'
    
    def name_get(self):
        """Display format: [CODE] Account Name"""
        result = []
        for account in self:
            name = f'[{account.code}] {account.name}'
            result.append((account.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Allow searching by code or name"""
        args = args or []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            account_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
            return self.browse(account_ids).name_get()
        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
    
    def action_view_journal_entries(self):
        """Action to view journal entries for this account"""
        self.ensure_one()
        
        return {
            'name': f'Journal Entries - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.account.move.line',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {
                'default_account_id': self.id,
                'search_default_account_id': self.id,
            }
        }
    
    def toggle_reconcile(self):
        """Toggle reconciliation setting"""
        for account in self:
            account.reconcile = not account.reconcile
        return True
    
    @api.model
    def create_default_accounts(self, company_id=None):
        """Create default chart of accounts for AMS"""
        if not company_id:
            company_id = self.env.company.id
        
        # Define default accounts structure
        default_accounts = [
            # Assets
            {'code': '1000', 'name': 'Cash and Bank', 'account_type': 'asset_cash', 'ams_category': 'general'},
            {'code': '1200', 'name': 'Accounts Receivable', 'account_type': 'asset_receivable', 'reconcile': True, 'ams_category': 'general'},
            {'code': '1210', 'name': 'Membership A/R', 'account_type': 'asset_receivable', 'reconcile': True, 'ams_category': 'membership'},
            
            # Liabilities
            {'code': '2000', 'name': 'Accounts Payable', 'account_type': 'liability_payable', 'reconcile': True, 'ams_category': 'general'},
            {'code': '2400', 'name': 'Deferred Revenue - Memberships', 'account_type': 'liability_deferred_revenue', 'ams_category': 'membership'},
            {'code': '2410', 'name': 'Deferred Revenue - Publications', 'account_type': 'liability_deferred_revenue', 'ams_category': 'publication'},
            {'code': '2420', 'name': 'Deferred Revenue - Chapters', 'account_type': 'liability_deferred_revenue', 'ams_category': 'chapter'},
            
            # Equity
            {'code': '3000', 'name': 'Retained Earnings', 'account_type': 'equity', 'ams_category': 'general'},
            
            # Revenue
            {'code': '4100', 'name': 'Individual Membership Revenue', 'account_type': 'income_membership', 'ams_category': 'membership'},
            {'code': '4110', 'name': 'Enterprise Membership Revenue', 'account_type': 'income_membership', 'ams_category': 'membership'},
            {'code': '4200', 'name': 'Chapter Revenue', 'account_type': 'income_chapter', 'ams_category': 'chapter'},
            {'code': '4300', 'name': 'Publication Revenue', 'account_type': 'income_publication', 'ams_category': 'publication'},
            
            # Expenses
            {'code': '5000', 'name': 'Operating Expenses', 'account_type': 'expense', 'ams_category': 'general'},
            {'code': '5100', 'name': 'Bad Debt Expense', 'account_type': 'expense', 'ams_category': 'general'},
        ]
        
        created_accounts = self.env['ams.account.account']
        
        for account_data in default_accounts:
            account_data['company_id'] = company_id
            
            # Check if account already exists
            existing = self.search([
                ('code', '=', account_data['code']),
                ('company_id', '=', company_id)
            ])
            
            if not existing:
                account = self.create(account_data)
                created_accounts |= account
        
        return created_accounts